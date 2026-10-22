"""Frozen-expert J controls. Every trained head starts from the RGB prediction."""
import torch
from torch import nn
from torch.nn import functional as F

ARMS = ("J1", "J2", "J3", "J4", "J5", "J6", "J7")


def conv_head(channels, hidden):
    net = nn.Sequential(nn.Conv2d(channels, hidden, 1), nn.GELU(),
                        nn.Conv2d(hidden, hidden, 3, padding=1), nn.GELU(),
                        nn.Conv2d(hidden, 6, 1))
    nn.init.zeros_(net[-1].weight)
    nn.init.zeros_(net[-1].bias)
    return net


class FrozenExpertHead(nn.Module):
    def __init__(self, arm):
        super().__init__()
        if arm not in ARMS:
            raise ValueError(arm)
        self.arm = arm
        if arm == "J1":
            self.net = conv_head(12, 72)
        elif arm in ("J2", "J4"):
            self.net = conv_head(256, 64)
        elif arm == "J3":
            self.net = conv_head(128, 72)
        else:
            # J5 and J6 have identical architecture and initialization.
            self.condition = nn.Conv2d(128, 256, 1)
            self.body = conv_head(128, 72)
            self.net = None

    def forward(self, r_feature, d_feature, r_logits, d_logits,
                rgb_available=None, dsm_available=None, second_rgb=None):
        if r_feature.shape != d_feature.shape or r_feature.shape[1] != 128:
            raise ValueError("expert feature grid must be matched stride-4 128 channels")
        b, _, h, w = r_feature.shape
        if r_logits.shape != (b, 6, h, w) or d_logits.shape != (b, 6, h, w):
            raise ValueError("expert logit grid")
        if rgb_available is None:
            rgb_available = torch.ones((b, 1, h, w), dtype=torch.bool, device=r_feature.device)
        if dsm_available is None:
            dsm_available = torch.ones((b, 1, h, w), dtype=torch.bool, device=r_feature.device)
        if rgb_available.shape != (b, 1, h, w) or dsm_available.shape != (b, 1, h, w):
            raise ValueError("availability grid")
        if self.arm == "J5":
            # A fixed half-window displacement destroys correspondence, not class labels.
            d_feature = torch.roll(d_feature, (h // 2, w // 2), (-2, -1))
            d_logits = torch.roll(d_logits, (h // 2, w // 2), (-2, -1))
        if self.arm == "J1":
            delta = self.net(torch.cat((r_logits, d_logits), dim=1))
        elif self.arm == "J2":
            delta = self.net(torch.cat((r_feature, d_feature), dim=1))
        elif self.arm == "J3":
            delta = self.net(r_feature)
        elif self.arm == "J4":
            if second_rgb is None or second_rgb.shape != r_feature.shape:
                raise ValueError("J4 requires a second legitimate RGB expert")
            delta = self.net(torch.cat((r_feature, second_rgb), dim=1))
        else:
            # J7 uses the same parameterized operation with DSM-conditioned DSM;
            # it keeps RGB logits as the common starting prediction.
            source = d_feature if self.arm == "J7" else r_feature
            scale, bias = self.condition(source).chunk(2, dim=1)
            delta = self.body(d_feature * torch.tanh(scale) + bias)
        fused = r_logits + delta
        # Missing DSM must give the exact RGB decision, even for a learned bias.
        if self.arm not in ("J3", "J4"):
            fused = torch.where(dsm_available, fused, r_logits)
        # A missing RGB view is outside J's main panel but has an exact fallback.
        return torch.where(rgb_available, fused, d_logits).masked_fill(
            ~(rgb_available | dsm_available), 0)


def expert_grids(rgb_model, dsm_model, rgb, dsm, second_rgb_model=None):
    """Return detached, ordinary tensors; trainable heads may backprop through them."""
    with torch.no_grad():
        r_feature = rgb_model.encode(rgb)
        d_feature = dsm_model.encode(dsm[:, None].repeat(1, 3, 1, 1))
        r_logits = rgb_model.decoder(r_feature)
        d_logits = dsm_model.decoder(d_feature)
        second = None if second_rgb_model is None else second_rgb_model.encode(rgb)
    return r_feature, d_feature, r_logits, d_logits, second
