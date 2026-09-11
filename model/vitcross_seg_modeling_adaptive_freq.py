"""
Stage-3 F4:
Spatially Adaptive Frequency Decoder.

Core idea
---------
For every decoder block with a skip connection:

    Z_base = concat(bilinear_up(x), skip)
    Z_freq = concat(freq_x, freq_skip)

A spatial gate learns:

    Z = Z_base + G * (Z_freq - Z_base)

where G has shape [B, 1, H, W].

Therefore:
    G = 0 -> strict F0 path
    G = 1 -> strict F3 path

The original shared conv1 / conv2 are kept unchanged.
"""

import math

import numpy as np
import torch
import torch.nn as nn

from . import vitcross_seg_modeling_freqfusion as base


class SpatialFrequencyGate(nn.Module):
    """
    Lightweight spatial gate.

    Input:
        base feature : [B, C, H, W]
        freq feature : [B, C, H, W]

    Output:
        gate         : [B, 1, H, W]
    """

    def __init__(
        self,
        channels,
        hidden_channels=None,
        init_gate=0.10,
    ):
        super().__init__()

        if hidden_channels is None:
            hidden_channels = max(
                16,
                min(
                    64,
                    channels // 8,
                ),
            )

        if not (
            0.0 < init_gate < 1.0
        ):
            raise ValueError(
                "init_gate must be in (0, 1)"
            )

        # Input:
        # base, freq, abs(freq-base)
        gate_in_channels = (
            channels * 3
        )

        self.proj = nn.Conv2d(
            gate_in_channels,
            hidden_channels,
            kernel_size=1,
            bias=True,
        )

        self.act1 = nn.ReLU(
            inplace=True
        )

        self.context = nn.Conv2d(
            hidden_channels,
            hidden_channels,
            kernel_size=3,
            padding=1,
            bias=True,
        )

        self.act2 = nn.ReLU(
            inplace=True
        )

        self.out = nn.Conv2d(
            hidden_channels,
            1,
            kernel_size=1,
            bias=True,
        )

        # Make the initial gate spatially constant.
        nn.init.zeros_(
            self.out.weight
        )

        init_bias = math.log(
            init_gate
            / (1.0 - init_gate)
        )

        nn.init.constant_(
            self.out.bias,
            init_bias,
        )

        self.init_gate = float(
            init_gate
        )

    def forward(
        self,
        base_feat,
        freq_feat,
    ):
        diff = torch.abs(
            freq_feat - base_feat
        )

        z = torch.cat(
            [
                base_feat,
                freq_feat,
                diff,
            ],
            dim=1,
        )

        z = self.proj(z)
        z = self.act1(z)

        z = self.context(z)
        z = self.act2(z)

        z = self.out(z)

        return torch.sigmoid(z)


class DecoderBlockAdaptiveFreq(nn.Module):
    def __init__(
        self,
        in_channels,
        out_channels,
        skip_channels=0,
        use_batchnorm=True,
        compressed_channels=64,
        gate_init=0.10,
    ):
        super().__init__()

        self.in_channels = in_channels
        self.out_channels = out_channels
        self.skip_channels = (
            skip_channels
        )

        self.has_skip = (
            skip_channels > 0
        )

        if self.has_skip:
            # Exact F3 configuration used in
            # the verified Stage-2 model.
            self.freq_fusion = (
                base.FreqFusion(
                    hr_channels=
                        skip_channels,
                    lr_channels=
                        in_channels,
                    compressed_channels=
                        compressed_channels,
                    hr_residual=True,
                    semi_conv=True,
                    hamming_window=True,
                    feature_resample=True,
                    use_high_pass=True,
                    use_low_pass=True,
                    comp_feat_upsample=True,
                )
            )

            fused_channels = (
                in_channels
                + skip_channels
            )

            self.gate = (
                SpatialFrequencyGate(
                    channels=
                        fused_channels,
                    init_gate=
                        gate_init,
                )
            )

        self.conv1 = base.Conv2dReLU(
            in_channels + skip_channels,
            out_channels,
            kernel_size=3,
            padding=1,
            use_batchnorm=use_batchnorm,
        )

        self.conv2 = base.Conv2dReLU(
            out_channels,
            out_channels,
            kernel_size=3,
            padding=1,
            use_batchnorm=use_batchnorm,
        )

        self.up = (
            nn.UpsamplingBilinear2d(
                scale_factor=2
            )
        )

        # None = normal adaptive mode.
        # 0.0  = force strict F0.
        # 1.0  = force strict F3.
        self.gate_override = None

        # Filled only during eval.
        self.last_gate = None

    def set_gate_override(
        self,
        value,
    ):
        if value is None:
            self.gate_override = None
            return

        value = float(value)

        if value not in (
            0.0,
            1.0,
        ):
            raise ValueError(
                "gate_override must be "
                "None, 0.0, or 1.0"
            )

        self.gate_override = value

    def forward(
        self,
        x,
        skip=None,
    ):
        if skip is not None:
            if not self.has_skip:
                raise RuntimeError(
                    "skip supplied to a "
                    "zero-skip block"
                )

            # ------------------------------------------------
            # Strict F0 endpoint
            # ------------------------------------------------
            if (
                self.gate_override
                == 0.0
            ):
                base_x = self.up(x)

                z = torch.cat(
                    [
                        base_x,
                        skip,
                    ],
                    dim=1,
                )

                if not self.training:
                    self.last_gate = (
                        torch.zeros(
                            (
                                z.shape[0],
                                1,
                                z.shape[2],
                                z.shape[3],
                            ),
                            device=z.device,
                            dtype=z.dtype,
                        )
                    )

            # ------------------------------------------------
            # Strict F3 endpoint
            # ------------------------------------------------
            elif (
                self.gate_override
                == 1.0
            ):
                (
                    _,
                    freq_skip,
                    freq_x,
                ) = self.freq_fusion(
                    hr_feat=skip,
                    lr_feat=x,
                )

                z = torch.cat(
                    [
                        freq_x,
                        freq_skip,
                    ],
                    dim=1,
                )

                if not self.training:
                    self.last_gate = (
                        torch.ones(
                            (
                                z.shape[0],
                                1,
                                z.shape[2],
                                z.shape[3],
                            ),
                            device=z.device,
                            dtype=z.dtype,
                        )
                    )

            # ------------------------------------------------
            # F4 adaptive path
            # ------------------------------------------------
            else:
                base_x = self.up(x)

                z_base = torch.cat(
                    [
                        base_x,
                        skip,
                    ],
                    dim=1,
                )

                (
                    _,
                    freq_skip,
                    freq_x,
                ) = self.freq_fusion(
                    hr_feat=skip,
                    lr_feat=x,
                )

                z_freq = torch.cat(
                    [
                        freq_x,
                        freq_skip,
                    ],
                    dim=1,
                )

                gate = self.gate(
                    z_base,
                    z_freq,
                )

                z = (
                    z_base
                    + gate
                    * (
                        z_freq
                        - z_base
                    )
                )

                # Keep only a detached copy of the most recent
                # adaptive gate. This is used for Stage-3 logging
                # and does not retain the autograd graph.
                self.last_gate = (
                    gate.detach()
                )

        else:
            # Last decoder block:
            # no skip, same path as F0/F3.
            z = self.up(x)

            if not self.training:
                self.last_gate = None

        z = self.conv1(z)
        z = self.conv2(z)

        return z


class DecoderCupAdaptiveFreq(nn.Module):
    def __init__(
        self,
        config,
        gate_init=0.10,
    ):
        super().__init__()

        self.config = config

        head_channels = 512

        self.conv_more = (
            base.Conv2dReLU(
                config.hidden_size,
                head_channels,
                kernel_size=3,
                padding=1,
                use_batchnorm=True,
            )
        )

        decoder_channels = list(
            config.decoder_channels
        )

        in_channels = (
            [head_channels]
            + decoder_channels[:-1]
        )

        out_channels = (
            decoder_channels
        )

        if config.n_skip != 0:
            skip_channels = list(
                config.skip_channels
            )

            for i in range(
                4 - config.n_skip
            ):
                skip_channels[
                    3 - i
                ] = 0
        else:
            skip_channels = [
                0,
                0,
                0,
                0,
            ]

        blocks = []

        for (
            in_ch,
            out_ch,
            sk_ch,
        ) in zip(
            in_channels,
            out_channels,
            skip_channels,
        ):
            blocks.append(
                DecoderBlockAdaptiveFreq(
                    in_channels=in_ch,
                    out_channels=out_ch,
                    skip_channels=sk_ch,
                    use_batchnorm=True,
                    compressed_channels=64,
                    gate_init=gate_init,
                )
            )

        self.blocks = nn.ModuleList(
            blocks
        )

    def set_gate_override(
        self,
        value,
    ):
        for block in self.blocks:
            block.set_gate_override(
                value
            )

    def get_last_gates(self):
        gates = []

        for i, block in enumerate(
            self.blocks
        ):
            if (
                block.last_gate
                is not None
            ):
                gates.append(
                    (
                        i,
                        block.last_gate,
                    )
                )

        return gates

    def forward(
        self,
        hidden_states,
        features=None,
    ):
        B, n_patch, hidden = (
            hidden_states.size()
        )

        h = int(
            np.sqrt(n_patch)
        )

        w = int(
            np.sqrt(n_patch)
        )

        x = hidden_states.permute(
            0,
            2,
            1,
        )

        x = x.contiguous().view(
            B,
            hidden,
            h,
            w,
        )

        x = self.conv_more(x)

        for (
            i,
            decoder_block,
        ) in enumerate(
            self.blocks
        ):
            if features is not None:
                skip = (
                    features[i]
                    if (
                        i
                        < self.config.n_skip
                    )
                    else None
                )
            else:
                skip = None

            x = decoder_block(
                x,
                skip=skip,
            )

        return x


class VisionTransformerAdaptiveFreq(
    nn.Module
):
    def __init__(
        self,
        config,
        img_size=224,
        num_classes=21843,
        zero_head=False,
        vis=False,
        gate_init=0.10,
    ):
        super().__init__()

        self.num_classes = num_classes
        self.zero_head = zero_head
        self.classifier = (
            config.classifier
        )

        self.transformer = (
            base.Transformer(
                config,
                img_size,
                vis,
            )
        )

        self.decoder = (
            DecoderCupAdaptiveFreq(
                config,
                gate_init=gate_init,
            )
        )

        self.segmentation_head = (
            base.SegmentationHead(
                in_channels=
                    config[
                        "decoder_channels"
                    ][-1],
                out_channels=
                    config["n_classes"],
                kernel_size=3,
            )
        )

        self.config = config

    def set_gate_override(
        self,
        value,
    ):
        self.decoder.set_gate_override(
            value
        )

    def get_last_gates(self):
        return (
            self.decoder
            .get_last_gates()
        )

    def forward(
        self,
        x,
        y,
    ):
        (
            x,
            y,
            attn_weights,
            features,
        ) = self.transformer(
            x,
            y,
        )

        x = x + y

        x = self.decoder(
            x,
            features,
        )

        logits = (
            self.segmentation_head(x)
        )

        return logits

    load_from = (
        base
        .VisionTransformerFreqFusion
        .load_from
    )
