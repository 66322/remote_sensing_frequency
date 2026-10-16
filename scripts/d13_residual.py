"""D13 residual model and losses. Pure functions support CPU checks."""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

ARMS = (
    "rgb_ce", "dsm_ce", "rgb_risk", "dsm_risk",
    "dsm_capacity", "dsm_semantic", "dsm_frequency", "dsm_semantic_frequency",
)
SEMANTIC_CHANNELS = 16
INPUT_CHANNELS = 6 + 3 + 1 + SEMANTIC_CHANNELS + 2


def known_missing_mask(condition, region_mask):
    """Only absence, never degradation, can force exact RGB fallback."""
    if condition in ("dsm_zero", "dsm_local_zero_q1"):
        if region_mask is None:
            raise ValueError(f"{condition} requires an explicit missingness mask")
        return region_mask
    return None


class ResidualHead(nn.Module):
    def __init__(self, hidden=32):
        super().__init__()
        self.body = nn.Sequential(
            nn.Conv2d(INPUT_CHANNELS, hidden, 3, padding=1),
            nn.GroupNorm(8, hidden), nn.GELU(),
            nn.Conv2d(hidden, hidden, 3, padding=1),
            nn.GroupNorm(8, hidden), nn.GELU(),
        )
        self.output = nn.Conv2d(hidden, 6, 1)
        nn.init.zeros_(self.output.weight)
        nn.init.zeros_(self.output.bias)

    def forward(self, features):
        return self.output(self.body(features))


def highpass(x):
    return x - F.avg_pool2d(F.pad(x, (2, 2, 2, 2), mode="reflect"), 5, 1)


def features_for_arm(arm, anchor_logits, optical, auxiliary, decoder):
    """Every arm has identical model parameters and input dimensions."""
    if arm not in ARMS:
        raise ValueError(arm)
    if decoder is None:
        decoder = anchor_logits.new_zeros((anchor_logits.shape[0], SEMANTIC_CHANNELS,
                                          *anchor_logits.shape[-2:]))
    if decoder.shape[1] != SEMANTIC_CHANNELS:
        raise ValueError(f"R01 decoder has {decoder.shape[1]} channels")
    sem = torch.zeros_like(decoder)
    freq = anchor_logits.new_zeros((anchor_logits.shape[0], 2, *anchor_logits.shape[-2:]))
    if arm in ("dsm_semantic", "dsm_semantic_frequency"):
        sem = decoder
    elif arm == "dsm_capacity":
        sem = torch.cat((anchor_logits, anchor_logits, optical, optical[:, :1]), dim=1)
    if arm in ("dsm_frequency", "dsm_semantic_frequency"):
        freq = torch.cat((highpass(auxiliary), highpass(optical.mean(dim=1, keepdim=True))), dim=1)
    elif arm == "dsm_capacity":
        freq = torch.cat((optical.mean(dim=1, keepdim=True), auxiliary), dim=1)
    result = torch.cat((anchor_logits, optical, auxiliary, sem, freq), dim=1)
    if result.shape[1] != INPUT_CHANNELS:
        raise RuntimeError(f"feature width {result.shape[1]} != {INPUT_CHANNELS}")
    return result


def apply_residual(anchor_logits, correction, available):
    if available.dtype != torch.bool or available.ndim != 3:
        raise ValueError("availability must be BHW bool")
    if anchor_logits.shape != correction.shape:
        raise ValueError("correction shape mismatch")
    # torch.where also prevents 0 * NaN from contaminating known-missing pixels.
    return torch.where(available[:, None], anchor_logits + correction, anchor_logits)


def risk_loss(logits, anchor_logits, target, available, use_risk, risk_lambda=1.0):
    """Flattened CE uses the deterministic CUDA kernel in the server build."""
    if logits.shape != anchor_logits.shape or logits.shape[0] != target.shape[0]:
        raise ValueError("logit/label shape mismatch")
    c = logits.shape[1]
    ce_map = F.cross_entropy(logits.permute(0, 2, 3, 1).contiguous().view(-1, c),
                             target.reshape(-1), reduction="none").reshape_as(target)
    ce = ce_map.mean()
    if not use_risk:
        return ce, ce.detach(), ce.new_zeros(())
    with torch.no_grad():
        anchor_ce = F.cross_entropy(anchor_logits.permute(0, 2, 3, 1).contiguous().view(-1, c),
                                    target.reshape(-1), reduction="none").reshape_as(target)
        correct = anchor_logits.argmax(dim=1) == target
    penalty = torch.relu(ce_map - anchor_ce) * (correct & available).to(ce_map.dtype)
    risk = penalty.mean()
    return ce + risk_lambda * risk, ce.detach(), risk.detach()
