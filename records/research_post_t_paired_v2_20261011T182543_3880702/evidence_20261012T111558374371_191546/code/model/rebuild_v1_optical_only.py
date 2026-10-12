# coding=utf-8
"""True Optical-only model for REBUILD_V1 R01.

This module intentionally contains no DSM input, DSM branch, depth branch, or
DSM-specific trainable parameters. It mirrors the R02 F0 depth/hidden/decoder
shape as closely as possible while removing multimodal processing.

Important fairness choice:
- the Optical ResNet root uses the same DynamicConv2d primitive used by the
  R02 Optical branch, so R01 does not gain an unmatched pretrained static root;
- the remaining ResNet body and ViT blocks load the same R50+ViT-B/16 weights;
- decoder is the verified F0 bilinear decoder (no frequency module).
"""

import copy
import math
from collections import OrderedDict
from os.path import join as pjoin

import numpy as np
import torch
import torch.nn as nn
from scipy import ndimage
from torch.nn import Conv2d, Dropout, LayerNorm, Linear, Softmax
from torch.nn.modules.utils import _pair

from model.dynamic_conv import DynamicConv2d
from model.vit_seg_modeling_resnet_skip import PreActBottleneck
from model import vitcross_seg_modeling_freqfusion as base
from model.vitcross_seg_modeling_freq_ablation import DecoderCupFreqAblation


class OpticalResNetV2(nn.Module):
    """R02-matched Optical backbone with the DSM stream removed."""

    def __init__(self, block_units, width_factor):
        super().__init__()
        width = int(64 * width_factor)
        self.width = width

        self.root = nn.Sequential(OrderedDict([
            ("conv", DynamicConv2d(3, width, k=7, stride=2, padding=3)),
            ("gn", nn.GroupNorm(32, width, eps=1e-6)),
            ("relu", nn.ReLU(inplace=True)),
        ]))

        self.body = nn.Sequential(OrderedDict([
            ("block1", nn.Sequential(OrderedDict(
                [("unit1", PreActBottleneck(cin=width, cout=width * 4, cmid=width))] +
                [(f"unit{i:d}", PreActBottleneck(cin=width * 4, cout=width * 4, cmid=width))
                 for i in range(2, block_units[0] + 1)]
            ))),
            ("block2", nn.Sequential(OrderedDict(
                [("unit1", PreActBottleneck(cin=width * 4, cout=width * 8, cmid=width * 2, stride=2))] +
                [(f"unit{i:d}", PreActBottleneck(cin=width * 8, cout=width * 8, cmid=width * 2))
                 for i in range(2, block_units[1] + 1)]
            ))),
            ("block3", nn.Sequential(OrderedDict(
                [("unit1", PreActBottleneck(cin=width * 8, cout=width * 16, cmid=width * 4, stride=2))] +
                [(f"unit{i:d}", PreActBottleneck(cin=width * 16, cout=width * 16, cmid=width * 4))
                 for i in range(2, block_units[2] + 1)]
            ))),
        ]))

    def forward(self, x):
        features = []
        b, _, in_size, _ = x.size()
        x = self.root(x)
        features.append(x)
        x = nn.MaxPool2d(kernel_size=3, stride=2, padding=0)(x)
        for i in range(len(self.body) - 1):
            x = self.body[i](x)
            right_size = int(in_size / 4 / (i + 1))
            if x.size(2) != right_size:
                pad = right_size - x.size(2)
                if not (0 < pad < 3):
                    raise RuntimeError(f"unexpected optical skip size {x.size()} vs {right_size}")
                feat = torch.zeros((b, x.size(1), right_size, right_size), device=x.device, dtype=x.dtype)
                feat[:, :, :x.size(2), :x.size(3)] = x
            else:
                feat = x
            features.append(feat)
        x = self.body[-1](x)
        return x, features[::-1]

    def load_from(self, weights):
        """Match R02 preload semantics: DynamicConv root is not weight-copied."""
        with torch.no_grad():
            gn_weight = base.np2th(weights["gn_root/scale"]).view(-1)
            gn_bias = base.np2th(weights["gn_root/bias"]).view(-1)
            self.root.gn.weight.copy_(gn_weight)
            self.root.gn.bias.copy_(gn_bias)
            for bname, block in self.body.named_children():
                for uname, unit in block.named_children():
                    unit.load_from(weights, n_block=bname, n_unit=uname)


class OpticalEmbeddings(nn.Module):
    def __init__(self, config, img_size, in_channels=3):
        super().__init__()
        self.hybrid = None
        self.config = config
        img_size = _pair(img_size)

        if config.patches.get("grid") is not None:
            grid_size = config.patches["grid"]
            patch_size = (
                img_size[0] // 16 // grid_size[0],
                img_size[1] // 16 // grid_size[1],
            )
            patch_size_real = (patch_size[0] * 16, patch_size[1] * 16)
            n_patches = (
                (img_size[0] // patch_size_real[0]) *
                (img_size[1] // patch_size_real[1])
            )
            self.hybrid = True
        else:
            patch_size = _pair(config.patches["size"])
            n_patches = (
                (img_size[0] // patch_size[0]) *
                (img_size[1] // patch_size[1])
            )
            self.hybrid = False

        if self.hybrid:
            self.hybrid_model = OpticalResNetV2(
                block_units=config.resnet.num_layers,
                width_factor=config.resnet.width_factor,
            )
            in_channels = self.hybrid_model.width * 16

        self.patch_embeddings = Conv2d(
            in_channels=in_channels,
            out_channels=config.hidden_size,
            kernel_size=patch_size,
            stride=patch_size,
        )
        self.position_embeddings = nn.Parameter(
            torch.zeros(1, n_patches, config.hidden_size)
        )
        self.dropout = Dropout(config.transformer["dropout_rate"])

    def forward(self, x):
        if self.hybrid:
            x, features = self.hybrid_model(x)
        else:
            features = None
        x = self.patch_embeddings(x)
        x = x.flatten(2).transpose(-1, -2)
        x = self.dropout(x + self.position_embeddings)
        return x, features


class OpticalAttention(nn.Module):
    def __init__(self, config, vis=False):
        super().__init__()
        self.vis = vis
        self.num_attention_heads = config.transformer["num_heads"]
        self.attention_head_size = int(config.hidden_size / self.num_attention_heads)
        self.all_head_size = self.num_attention_heads * self.attention_head_size
        self.query = Linear(config.hidden_size, self.all_head_size)
        self.key = Linear(config.hidden_size, self.all_head_size)
        self.value = Linear(config.hidden_size, self.all_head_size)
        self.out = Linear(config.hidden_size, config.hidden_size)
        self.attn_dropout = Dropout(config.transformer["attention_dropout_rate"])
        self.proj_dropout = Dropout(config.transformer["attention_dropout_rate"])
        self.softmax = Softmax(dim=-1)

    def transpose_for_scores(self, x):
        shape = x.size()[:-1] + (self.num_attention_heads, self.attention_head_size)
        return x.view(*shape).permute(0, 2, 1, 3)

    def forward(self, hidden_states):
        query = self.transpose_for_scores(self.query(hidden_states))
        key = self.transpose_for_scores(self.key(hidden_states))
        value = self.transpose_for_scores(self.value(hidden_states))
        scores = torch.matmul(query, key.transpose(-1, -2))
        scores = scores / math.sqrt(self.attention_head_size)
        probs = self.softmax(scores)
        weights = probs if self.vis else None
        probs = self.attn_dropout(probs)
        context = torch.matmul(probs, value)
        context = context.permute(0, 2, 1, 3).contiguous()
        context = context.view(*(context.size()[:-2] + (self.all_head_size,)))
        out = self.proj_dropout(self.out(context))
        return out, weights


class OpticalBlock(nn.Module):
    def __init__(self, config, vis=False):
        super().__init__()
        self.hidden_size = config.hidden_size
        self.attention_norm = LayerNorm(config.hidden_size, eps=1e-6)
        self.ffn_norm = LayerNorm(config.hidden_size, eps=1e-6)
        self.ffn = base.Mlp(config)
        self.attn = OpticalAttention(config, vis=vis)

    def forward(self, x):
        h = x
        x, weights = self.attn(self.attention_norm(x))
        x = x + h
        h = x
        x = self.ffn(self.ffn_norm(x))
        x = x + h
        return x, weights

    def load_from(self, weights, n_block):
        root = f"Transformer/encoderblock_{n_block}"
        with torch.no_grad():
            q_w = base.np2th(weights[pjoin(root, base.ATTENTION_Q, "kernel")]).view(self.hidden_size, self.hidden_size).t()
            k_w = base.np2th(weights[pjoin(root, base.ATTENTION_K, "kernel")]).view(self.hidden_size, self.hidden_size).t()
            v_w = base.np2th(weights[pjoin(root, base.ATTENTION_V, "kernel")]).view(self.hidden_size, self.hidden_size).t()
            o_w = base.np2th(weights[pjoin(root, base.ATTENTION_OUT, "kernel")]).view(self.hidden_size, self.hidden_size).t()
            self.attn.query.weight.copy_(q_w)
            self.attn.key.weight.copy_(k_w)
            self.attn.value.weight.copy_(v_w)
            self.attn.out.weight.copy_(o_w)
            self.attn.query.bias.copy_(base.np2th(weights[pjoin(root, base.ATTENTION_Q, "bias")]).view(-1))
            self.attn.key.bias.copy_(base.np2th(weights[pjoin(root, base.ATTENTION_K, "bias")]).view(-1))
            self.attn.value.bias.copy_(base.np2th(weights[pjoin(root, base.ATTENTION_V, "bias")]).view(-1))
            self.attn.out.bias.copy_(base.np2th(weights[pjoin(root, base.ATTENTION_OUT, "bias")]).view(-1))

            self.ffn.fc1.weight.copy_(base.np2th(weights[pjoin(root, base.FC_0, "kernel")]).t())
            self.ffn.fc2.weight.copy_(base.np2th(weights[pjoin(root, base.FC_1, "kernel")]).t())
            self.ffn.fc1.bias.copy_(base.np2th(weights[pjoin(root, base.FC_0, "bias")]).view(-1))
            self.ffn.fc2.bias.copy_(base.np2th(weights[pjoin(root, base.FC_1, "bias")]).view(-1))
            self.attention_norm.weight.copy_(base.np2th(weights[pjoin(root, base.ATTENTION_NORM, "scale")]))
            self.attention_norm.bias.copy_(base.np2th(weights[pjoin(root, base.ATTENTION_NORM, "bias")]))
            self.ffn_norm.weight.copy_(base.np2th(weights[pjoin(root, base.MLP_NORM, "scale")]))
            self.ffn_norm.bias.copy_(base.np2th(weights[pjoin(root, base.MLP_NORM, "bias")]))


class OpticalEncoder(nn.Module):
    def __init__(self, config, vis=False):
        super().__init__()
        self.vis = vis
        self.layer = nn.ModuleList([
            copy.deepcopy(OpticalBlock(config, vis=vis))
            for _ in range(config.transformer["num_layers"])
        ])
        self.encoder_norm = LayerNorm(config.hidden_size, eps=1e-6)

    def forward(self, x):
        attn_weights = []
        for block in self.layer:
            x, weights = block(x)
            if self.vis:
                attn_weights.append(weights)
        return self.encoder_norm(x), attn_weights


class OpticalTransformer(nn.Module):
    def __init__(self, config, img_size, vis=False):
        super().__init__()
        self.embeddings = OpticalEmbeddings(config, img_size=img_size)
        self.encoder = OpticalEncoder(config, vis=vis)

    def forward(self, x):
        x, features = self.embeddings(x)
        x, attn_weights = self.encoder(x)
        return x, attn_weights, features


class VisionTransformerOpticalOnly(nn.Module):
    def __init__(self, config, img_size=224, num_classes=6, zero_head=False, vis=False):
        super().__init__()
        self.num_classes = num_classes
        self.zero_head = zero_head
        self.classifier = config.classifier
        self.transformer = OpticalTransformer(config, img_size, vis=vis)
        self.decoder = DecoderCupFreqAblation(config, freq_variant="F0")
        self.segmentation_head = base.SegmentationHead(
            in_channels=config["decoder_channels"][-1],
            out_channels=config["n_classes"],
            kernel_size=3,
        )
        self.config = config

    def forward(self, x):
        x, _, features = self.transformer(x)
        x = self.decoder(x, features)
        return self.segmentation_head(x)

    def load_from(self, weights):
        with torch.no_grad():
            emb = self.transformer.embeddings
            emb.patch_embeddings.weight.copy_(base.np2th(weights["embedding/kernel"], conv=True))
            emb.patch_embeddings.bias.copy_(base.np2th(weights["embedding/bias"]))
            self.transformer.encoder.encoder_norm.weight.copy_(base.np2th(weights["Transformer/encoder_norm/scale"]))
            self.transformer.encoder.encoder_norm.bias.copy_(base.np2th(weights["Transformer/encoder_norm/bias"]))

            posemb = base.np2th(weights["Transformer/posembed_input/pos_embedding"])
            posemb_new = emb.position_embeddings
            if posemb.size() == posemb_new.size():
                emb.position_embeddings.copy_(posemb)
            elif posemb.size(1) - 1 == posemb_new.size(1):
                emb.position_embeddings.copy_(posemb[:, 1:])
            else:
                ntok_new = posemb_new.size(1)
                if self.classifier == "seg":
                    posemb_grid = posemb[0, 1:]
                else:
                    posemb_grid = posemb[0]
                gs_old = int(np.sqrt(len(posemb_grid)))
                gs_new = int(np.sqrt(ntok_new))
                print(f"load_pretrained optical posemb grid {gs_old} -> {gs_new}")
                posemb_grid = posemb_grid.reshape(gs_old, gs_old, -1)
                posemb_grid = ndimage.zoom(
                    posemb_grid,
                    (gs_new / gs_old, gs_new / gs_old, 1),
                    order=1,
                )
                posemb_grid = posemb_grid.reshape(1, gs_new * gs_new, -1)
                emb.position_embeddings.copy_(base.np2th(posemb_grid))

            for idx, block in enumerate(self.transformer.encoder.layer):
                block.load_from(weights, n_block=idx)

            if emb.hybrid:
                emb.hybrid_model.load_from(weights)

        print("Load Optical-only pretrained done.")


def structural_audit(model):
    """Return a machine-readable proof that no DSM branch is instantiated."""
    names = [name.lower() for name, _ in model.named_parameters()]
    forbidden_tokens = ("rootd", "bodyd", "queryd", "keyd", "valued", "outd", "patch_embeddingsd", "dsm", "depth")
    offenders = [name for name in names if any(tok in name for tok in forbidden_tokens)]
    return {
        "forward_inputs": 1,
        "forbidden_parameter_names": offenders,
        "pass": len(offenders) == 0,
        "total_parameters": int(sum(p.numel() for p in model.parameters())),
        "trainable_parameters": int(sum(p.numel() for p in model.parameters() if p.requires_grad)),
    }


CONFIGS = base.CONFIGS
