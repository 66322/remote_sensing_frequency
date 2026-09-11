# model/
import torch, torch.nn as nn, torch.nn.functional as F

class DynamicConv2d(nn.Module):
    def __init__(self, in_c, out_c, k=3, stride=1, padding=1, groups=1, r=16):
        super().__init__()
        self.k, self.stride, self.padding, self.groups = k, stride, padding, groups
        hidden = max(in_c // r, 4)
        self.fc = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),          # B×C×1×1
            nn.Conv2d(in_c, hidden, 1, bias=True),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden, out_c * in_c // groups * k * k, 1, bias=True)
        )
    def forward(self, x):
        b, c, h, w = x.shape
        weight = self.fc(x).view(b * self.out_c,
                                 self.in_c // self.groups,
                                 self.k, self.k)
        x = x.view(1, b * c, h, w)          # depth-wise trick
        out = F.conv2d(x, weight, None,
                       stride=self.stride,
                       padding=self.padding,
                       groups=b * self.groups)
        out = out.view(b, self.out_c, out.shape[-2], out.shape[-1])
        return out
