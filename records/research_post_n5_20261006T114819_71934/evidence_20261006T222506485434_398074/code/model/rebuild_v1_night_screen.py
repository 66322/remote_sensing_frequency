"""One local interaction insertion and one frozen DINOv2 representation baseline."""
import os
from pathlib import Path

os.environ.setdefault('XFORMERS_DISABLED', '1')
import torch
from torch import nn
from torch.nn import functional as F


class LocalInteraction(nn.Module):
    def __init__(self, base, capacity=False, channels=64, window=8):
        super().__init__()
        self.base, self.capacity, self.window = base, capacity, window
        self.gate = nn.Conv2d(channels * 2, 32, 1)
        self.out = nn.Conv2d(32, channels, 1)
        self.alpha = nn.Parameter(torch.zeros(()))
        if capacity:
            self.local = nn.Conv2d(channels * 2, 32, 1)
        else:
            self.q = nn.Conv2d(channels, 16, 1)
            self.k = nn.Conv2d(channels, 16, 1)
            self.v = nn.Conv2d(channels, 32, 1)

    def windows(self, x):
        b, c, h, w = x.shape
        n = self.window
        return x.reshape(b, c, h//n, n, w//n, n).permute(0, 2, 4, 3, 5, 1).reshape(-1, n*n, c)

    def unwindow(self, x, shape):
        b, _, h, w = shape
        n = self.window
        return x.reshape(b, h//n, w//n, n, n, 32).permute(0, 5, 1, 3, 2, 4).reshape(b, 32, h, w)

    def forward(self, rgb, aux):
        baseline = self.base(rgb, aux)
        h, w = rgb.shape[-2:]
        pad = (0, (-w) % self.window, 0, (-h) % self.window)
        x, y = F.pad(rgb, pad), F.pad(aux, pad)
        pair = torch.cat((x, y), 1)
        gate = torch.sigmoid(self.gate(pair))
        if self.capacity:
            mixed = gate * torch.tanh(self.local(pair))
        else:
            q, k, v = self.windows(self.q(x)), self.windows(self.k(y)), self.windows(self.v(y))
            weights = torch.softmax(torch.bmm(q, k.transpose(1, 2)) / 4., -1)
            attended = self.unwindow(torch.bmm(weights, v), x.shape)
            mixed = gate * attended + (1-gate) * self.v(y)
        return baseline + torch.tanh(self.alpha) * self.out(mixed)[:, :, :h, :w]


class FrozenDinoSegmenter(nn.Module):
    def __init__(self, encoder, auxiliary):
        super().__init__()
        self.encoder, self.auxiliary = encoder, auxiliary
        for param in self.encoder.parameters():
            param.requires_grad_(False)
        self.encoder.eval()
        # Build common RGB/head modules before auxiliary modules: matched RGB initialization.
        self.rgb = nn.Sequential(nn.Conv2d(384, 128, 1), nn.GroupNorm(8, 128), nn.GELU())
        self.decoder = nn.Sequential(nn.Conv2d(128, 128, 3, padding=1), nn.GroupNorm(8, 128), nn.GELU(), nn.Conv2d(128, 6, 1))
        self.aux = None if not auxiliary else nn.Sequential(nn.Conv2d(1, 32, 3, padding=1), nn.GroupNorm(4, 32), nn.GELU(), nn.Conv2d(32, 128, 1))
        self.register_buffer('mean', torch.tensor([.485, .456, .406])[None, :, None, None])
        self.register_buffer('std', torch.tensor([.229, .224, .225])[None, :, None, None])

    def train(self, mode=True):
        super().train(mode)
        self.encoder.eval()
        return self

    def forward(self, rgb, aux):
        h, w = rgb.shape[-2:]
        image = F.pad((rgb-self.mean)/self.std, (0, (-w) % 14, 0, (-h) % 14), mode='replicate')
        with torch.no_grad():
            tokens = self.encoder.forward_features(image)['x_norm_patchtokens']
        features = tokens.transpose(1, 2).reshape(len(rgb), 384, image.shape[-2]//14, image.shape[-1]//14)
        features = self.rgb(features)
        if self.aux is not None:
            # Exact 14x14 patch pooling aligned with padded DINO tokens.
            secondary = F.avg_pool2d(F.pad(aux[:, None], (0, (-w) % 14, 0, (-h) % 14), mode='replicate'), 14, 14)
            features = features + self.aux(secondary)
        features = F.interpolate(features, size=((h+3)//4, (w+3)//4), mode='nearest')
        logits = self.decoder(features)
        return F.interpolate(logits, size=(h, w), mode='nearest')


def load_dino(repo, weights):
    encoder = torch.hub.load(str(Path(repo)), 'dinov2_vits14', source='local', pretrained=False)
    encoder.load_state_dict(torch.load(weights, map_location='cpu', weights_only=False), strict=True)
    return encoder
