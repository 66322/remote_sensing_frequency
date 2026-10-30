"""Matched small encoder-decoder for exploratory public-data mechanisms."""
import torch
from torch import nn
from torch.nn import functional as F


class Block(nn.Module):
    def __init__(self, cin, cout):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(cin, cout, 3, padding=1), nn.GroupNorm(8, cout), nn.GELU(),
            nn.Conv2d(cout, cout, 3, padding=1), nn.GroupNorm(8, cout), nn.GELU())

    def forward(self, x):
        return self.layers(x)


class SmallUNet(nn.Module):
    def __init__(self, channels, outputs):
        super().__init__()
        self.down1 = Block(channels, 32)
        self.down2 = Block(32, 64)
        self.mid = Block(64, 128)
        self.up2 = Block(128 + 64, 64)
        self.up1 = Block(64 + 32, 32)
        self.out = nn.Conv2d(32, outputs, 1)

    def forward(self, x):
        if x.ndim != 4 or min(x.shape[-2:]) < 16:
            raise ValueError("small public-data tile required")
        a = self.down1(x)
        b = self.down2(F.avg_pool2d(a, 2))
        c = self.mid(F.avg_pool2d(b, 2))
        y = self.up2(torch.cat((F.interpolate(c, size=b.shape[-2:], mode="bilinear",
                                               align_corners=False), b), 1))
        y = self.up1(torch.cat((F.interpolate(y, size=a.shape[-2:], mode="bilinear",
                                               align_corners=False), a), 1))
        return self.out(y)
