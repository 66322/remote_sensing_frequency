"""D24 continuation and matched semantic-memory models; labels never enter forward."""
import torch
from torch import nn
from torch.nn import functional as F
from model.rebuild_v1_d21_detail import DetailDinoSegmenter, detail_channels


class PrototypeMemory(nn.Module):
    def __init__(self):
        super().__init__()
        self.q = nn.Conv2d(256, 32, 1)
        self.k = nn.Linear(256, 32)
        self.v = nn.Linear(256, 128)
        self.out = nn.Conv2d(128, 128, 1)
        nn.init.zeros_(self.out.weight)
        nn.init.zeros_(self.out.bias)
        self.register_buffer('bank', torch.zeros(6, 256))
        self.register_buffer('support', torch.zeros(6, dtype=torch.int64))
        self.register_buffer('initialized', torch.tensor(False))

    def forward(self, rgb_feature, aux_feature):
        pair = torch.cat((rgb_feature, aux_feature), 1)
        if not bool(self.initialized):
            if not self.training:
                raise RuntimeError('prototype bank not initialized from training')
            with torch.no_grad():
                self.bank.copy_(pair.detach().float().mean((0, 2, 3))[None].expand(6, -1))
                self.initialized.fill_(True)
        bank = self.bank.detach().clone()
        query = self.q(pair).permute(0, 2, 3, 1)
        weights = torch.softmax(query @ self.k(bank).T / (32 ** .5), -1)
        value = (weights @ self.v(bank)).permute(0, 3, 1, 2).contiguous()
        return self.out(value)

    @torch.no_grad()
    def update(self, rgb_feature, aux_feature, label, semantic, seed_tokens):
        pair = torch.cat((rgb_feature, aux_feature), 1).detach().float()
        b, _, h, w = pair.shape
        target = F.interpolate(label[:, None].float(), (h, w), mode='nearest')[:, 0].long()
        valid = (target >= 0) & (target < 6)
        if semantic:
            buckets = target
        else:
            y = torch.arange(h, device=pair.device)[None, :, None]
            x = torch.arange(w, device=pair.device)[None, None, :]
            seed_tokens = seed_tokens.to(pair.device)[:, None, None]
            buckets = (y * 1009 + x * 9176 + seed_tokens) % 6
        for c in range(6):
            keep = valid & (buckets == c)
            count = keep.sum()
            if int(count):
                mean = (pair * keep[:, None]).sum((0, 2, 3)) / count
                self.bank[c].lerp_(mean, .01)
                self.support[c].add_(count)


class D24Segmenter(DetailDinoSegmenter):
    def __init__(self, encoder, optical_only=False, last4=False, prototype=False):
        super().__init__(encoder, 'R0' if optical_only else 'M0')
        self.optical_only = optical_only
        self.last4 = last4
        if last4:
            if not hasattr(encoder, 'blocks') or len(encoder.blocks) < 4:
                raise RuntimeError('encoder has fewer than four blocks')
            for block in encoder.blocks[-4:]:
                for param in block.parameters():
                    param.requires_grad_(True)
        self.prototype = PrototypeMemory() if prototype else None

    def encode(self, rgb):
        h, w = rgb.shape[-2:]
        image = F.pad((rgb - self.mean) / self.std,
                      (0, (-w) % 14, 0, (-h) % 14), mode='replicate')
        # Early blocks have frozen weights and the input has no gradient.
        # The last four blocks must not be inside no_grad when trainable.
        if self.last4:
            tokens = self.encoder.forward_features(image)['x_norm_patchtokens']
        else:
            with torch.no_grad():
                tokens = self.encoder.forward_features(image)['x_norm_patchtokens']
        features = tokens.transpose(1, 2).reshape(len(rgb), 384,
                    image.shape[-2] // 14, image.shape[-1] // 14)
        return F.interpolate(self.rgb(features), ((h + 3) // 4, (w + 3) // 4), mode='nearest')

    def forward(self, rgb, aux, available=None, return_parts=False):
        h, w = rgb.shape[-2:]
        feature = self.encode(rgb)
        optical = F.interpolate(self.decoder(feature), (h, w), mode='nearest')
        if self.optical_only:
            return (optical, optical, feature, torch.zeros_like(feature)) if return_parts else optical
        if available is None:
            raise ValueError('explicit auxiliary availability is required')
        if available.shape != aux.shape or available.dtype != torch.bool:
            raise ValueError('invalid availability mask')
        # A stride4 cell touching a missing pixel is masked conservatively.
        pad = (0, (-w) % 4, 0, (-h) % 4)
        low_mask = F.avg_pool2d(F.pad(available[:, None].float(), pad, mode='replicate'), 4, 4) == 1
        aux_feature = self.detail(detail_channels(aux.masked_fill(~available, 0), 'M0')) * low_mask
        mixed = feature + aux_feature
        if self.prototype is not None:
            mixed = mixed + self.prototype(feature, aux_feature) * low_mask
        fused = F.interpolate(self.decoder(mixed), (h, w), mode='nearest')
        # Decoder neighborhoods may cross the missing region, so masking only
        # features is insufficient for exact pixel-level optical fallback.
        result = torch.where(available[:, None], fused, optical)
        return (result, optical, feature, aux_feature) if return_parts else result
