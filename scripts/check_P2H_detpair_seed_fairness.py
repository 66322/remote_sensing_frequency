import copy
import random
import sys
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from model.vitcross_seg_modeling_freq_ablation import (
    VisionTransformerFreqAblation,
    CONFIGS,
)

from model.vitcross_seg_modeling_hf_reliability_detpair import (
    VisionTransformerHFReliability,
)


SEED = 42

DEVICE = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def make_config():
    config = copy.deepcopy(
        CONFIGS["R50-ViT-B_16"]
    )

    config.n_classes = 6
    config.n_skip = 3

    # Fairness test only:
    # use 256 input to reduce cost.
    config.patches.grid = (
        16,
        16,
    )

    return config


# ============================================================
# Build F0.
# ============================================================

set_seed(SEED)

f0 = VisionTransformerFreqAblation(
    make_config(),
    img_size=256,
    num_classes=6,
    freq_variant="F0",
).to(
    DEVICE
)


# ============================================================
# Build P2-H from exactly the same seed.
# ============================================================

set_seed(SEED)

p2h = VisionTransformerHFReliability(
    make_config(),
    img_size=256,
    num_classes=6,
).to(
    DEVICE
)


# ============================================================
# Common state_dict equality.
# ============================================================

f0_sd = f0.state_dict()
p2_sd = p2h.state_dict()

extra_keys = sorted(
    k
    for k in p2_sd
    if ".hfrely0." in k
)

common_p2_keys = sorted(
    k
    for k in p2_sd
    if ".hfrely0." not in k
)

f0_keys = sorted(
    f0_sd.keys()
)

missing = sorted(
    set(f0_keys)
    - set(common_p2_keys)
)

unexpected_common = sorted(
    set(common_p2_keys)
    - set(f0_keys)
)

mismatch = []

max_common_diff = 0.0

for k in f0_keys:
    if k not in p2_sd:
        continue

    a = f0_sd[k]
    b = p2_sd[k]

    if a.shape != b.shape:
        mismatch.append(
            (
                k,
                "shape",
                tuple(a.shape),
                tuple(b.shape),
            )
        )
        continue

    if not torch.equal(
        a,
        b,
    ):
        diff = (
            a.float()
            - b.float()
        ).abs().max().item()

        max_common_diff = max(
            max_common_diff,
            diff,
        )

        mismatch.append(
            (
                k,
                "value",
                diff,
            )
        )


# ============================================================
# P2-H-only parameter audit.
# ============================================================

p2h_named = [
    (n, p)
    for n, p in p2h.named_parameters()
    if ".hfrely0." in n
]

p2h_numel = sum(
    p.numel()
    for _, p in p2h_named
)


# ============================================================
# Exact output identity gate.
# ============================================================

f0.eval()
p2h.eval()

set_seed(123456)

optical = torch.randn(
    1,
    3,
    256,
    256,
    device=DEVICE,
)

dsm = torch.randn(
    1,
    256,
    256,
    device=DEVICE,
)

with torch.no_grad():
    out_f0 = f0(
        optical,
        dsm,
    )

    out_p2 = p2h(
        optical,
        dsm,
    )


output_diff = (
    out_f0
    - out_p2
).abs()

max_output_diff = (
    output_diff.max().item()
)

mean_output_diff = (
    output_diff.mean().item()
)

hybrid = (
    p2h
    .transformer
    .embeddings
    .hybrid_model
)

module = hybrid.hfrely0

wo = (
    module
    .last_weights[:, 0]
)

wd = (
    module
    .last_weights[:, 1]
)

so = (
    module
    .last_optical_scale
)

sd = (
    module
    .last_dsm_scale
)


print("=" * 100)
print("P2-H STRICT SEED FAIRNESS / IDENTITY GATE")
print("=" * 100)

print(
    "missing common keys:",
    missing,
)

print(
    "unexpected common keys:",
    unexpected_common,
)

print(
    "common value mismatches:",
    len(mismatch),
)

print(
    "max common parameter diff:",
    max_common_diff,
)

print(
    "P2-H extra tensors:",
    len(p2h_named),
)

print(
    "P2-H extra parameters:",
    p2h_numel,
)

print(
    "P2-H extra keys:",
)

for k in extra_keys:
    print(
        "  ",
        k,
    )

print()
print(
    "output max_abs_diff:",
    max_output_diff,
)

print(
    "output mean_abs_diff:",
    mean_output_diff,
)

print()
print(
    "wo mean/min/max:",
    float(wo.mean()),
    float(wo.min()),
    float(wo.max()),
)

print(
    "wd mean/min/max:",
    float(wd.mean()),
    float(wd.min()),
    float(wd.max()),
)

print(
    "optical scale mean/min/max:",
    float(so.mean()),
    float(so.min()),
    float(so.max()),
)

print(
    "DSM scale mean/min/max:",
    float(sd.mean()),
    float(sd.min()),
    float(sd.max()),
)

print(
    "scale-sum max error:",
    float(
        (
            so + sd - 2.0
        ).abs().max()
    ),
)

print(
    "HF discrepancy mean:",
    float(
        module
        .last_discrepancy
        .mean()
    ),
)


if missing:
    raise RuntimeError(
        "F0 common keys missing in P2-H"
    )

if unexpected_common:
    raise RuntimeError(
        "P2-H has unexpected common keys"
    )

if mismatch:
    print(
        "first mismatches:",
        mismatch[:10],
    )

    raise RuntimeError(
        "Common F0/P2-H initialization differs"
    )

if p2h_numel != 738:
    raise RuntimeError(
        f"Expected 738 P2-H parameters, "
        f"got {p2h_numel}"
    )

if len(p2h_named) != 4:
    raise RuntimeError(
        f"Expected 4 P2-H parameter tensors, "
        f"got {len(p2h_named)}"
    )

if max_output_diff != 0.0:
    raise RuntimeError(
        f"P2-H initialization is not "
        f"exactly F0: {max_output_diff}"
    )

if not torch.all(
    wo == 0.5
):
    raise RuntimeError(
        "Initial optical reliability != 0.5"
    )

if not torch.all(
    wd == 0.5
):
    raise RuntimeError(
        "Initial DSM reliability != 0.5"
    )

if not torch.all(
    so == 1.0
):
    raise RuntimeError(
        "Initial optical HF scale != 1"
    )

if not torch.all(
    sd == 1.0
):
    raise RuntimeError(
        "Initial DSM HF scale != 1"
    )

print()
print(
    "[PASS] P2-H common initialization "
    "is exactly seed-matched to F0"
)

print(
    "[PASS] P2-H output is exactly F0 "
    "at neutral reliability"
)

print(
    "[PASS] wo=wd=0.5 and "
    "So=Sd=1 exactly"
)
