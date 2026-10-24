"""D21: matched fine-scale height channels, using spatial box-filter decomposition.

The encoder and segmentation head follow D18. These are hypotheses, not a claim
that box filtering itself is new. No ground-truth or corruption ID enters forward.
"""
import torch
from torch import nn
from torch.nn import functional as F
from model.rebuild_v1_night_screen import FrozenDinoSegmenter

ARMS = ('R0', 'R1', 'M0', 'M1', 'F0', 'F1', 'F2', 'F3')


def detail_channels(aux, arm):
    """All six detail arms have identical input width and trainable architecture."""
    h, w = aux.shape[-2:]
    raw = F.avg_pool2d(F.pad(aux[:, None], (0, (-w) % 4, 0, (-h) % 4), mode='replicate'), 4, 4)
    low = F.avg_pool2d(F.pad(raw, (2, 2, 2, 2), mode='replicate'), 5, 1)
    high = raw - low
    zero = torch.zeros_like(raw)
    pairs = {
        'M0': (raw, zero), 'M1': (raw, zero),
        'F0': (low, zero), 'F1': (zero, high), 'F2': (low, high),
        # Deterministic alignment ablation; preserves high-channel value histogram.
        'F3': (low, torch.roll(high, (high.shape[-2] // 2, high.shape[-1] // 2), (-2, -1))),
    }
    return torch.cat(pairs[arm], dim=1)


class DetailDinoSegmenter(FrozenDinoSegmenter):
    def __init__(self, encoder, arm):
        if arm not in ARMS:
            raise ValueError(arm)
        super().__init__(encoder, auxiliary=arm == 'R1')
        self.arm = arm
        self.detail = None if arm in ('R0', 'R1') else nn.Sequential(
            nn.Conv2d(2, 32, 3, padding=1), nn.GroupNorm(4, 32), nn.GELU(),
            nn.Conv2d(32, 128, 1))

    def forward(self, rgb, aux):
        if self.detail is None:
            return super().forward(rgb, aux)
        h, w = rgb.shape[-2:]
        image = F.pad((rgb - self.mean) / self.std,
                      (0, (-w) % 14, 0, (-h) % 14), mode='replicate')
        with torch.no_grad():
            tokens = self.encoder.forward_features(image)['x_norm_patchtokens']
        features = tokens.transpose(1, 2).reshape(len(rgb), 384,
                    image.shape[-2] // 14, image.shape[-1] // 14)
        features = F.interpolate(self.rgb(features), size=((h+3)//4, (w+3)//4), mode='nearest')
        features = features + self.detail(detail_channels(aux, self.arm))
        return F.interpolate(self.decoder(features), size=(h, w), mode='nearest')
