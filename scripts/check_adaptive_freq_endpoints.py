from copy import deepcopy

import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )

from model.vitcross_seg_modeling_freqfusion import (
    CONFIGS,
)
from model.vitcross_seg_modeling_freq_ablation import (
    VisionTransformerFreqAblation,
)
from model.vitcross_seg_modeling_adaptive_freq import (
    VisionTransformerAdaptiveFreq,
)


DEVICE = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

IMG_SIZE = 256
GRID = (16, 16)
NUM_CLASSES = 6


def make_config():
    config = deepcopy(
        CONFIGS["R50-ViT-B_16"]
    )

    config.n_classes = (
        NUM_CLASSES
    )

    config.n_skip = 3

    config.patches.grid = GRID

    return config


torch.manual_seed(42)

f3 = VisionTransformerFreqAblation(
    make_config(),
    img_size=IMG_SIZE,
    num_classes=NUM_CLASSES,
    freq_variant="F3",
).to(DEVICE)

f0 = VisionTransformerFreqAblation(
    make_config(),
    img_size=IMG_SIZE,
    num_classes=NUM_CLASSES,
    freq_variant="F0",
).to(DEVICE)

f4 = VisionTransformerAdaptiveFreq(
    make_config(),
    img_size=IMG_SIZE,
    num_classes=NUM_CLASSES,
    gate_init=0.10,
).to(DEVICE)


# ------------------------------------------------------------
# Use F3 as the source for all common/FreqFusion parameters.
# ------------------------------------------------------------

f3_state = f3.state_dict()

r0 = f0.load_state_dict(
    f3_state,
    strict=False,
)

r4 = f4.load_state_dict(
    f3_state,
    strict=False,
)


print("=" * 100)
print("LOAD CHECK")
print("=" * 100)

print(
    "F0 missing:",
    len(r0.missing_keys),
)

print(
    "F0 unexpected:",
    len(r0.unexpected_keys),
)

print(
    "F4 missing:",
    len(r4.missing_keys),
)

print(
    "F4 unexpected:",
    len(r4.unexpected_keys),
)

print()

print(
    "F4 missing keys "
    "(should be gate-only):"
)

for k in r4.missing_keys:
    print("  ", k)


# ------------------------------------------------------------
# Parameter counts
# ------------------------------------------------------------

def nparams(model):
    return sum(
        p.numel()
        for p in model.parameters()
    )


p0 = nparams(f0)
p3 = nparams(f3)
p4 = nparams(f4)

print()
print("=" * 100)
print("PARAMETERS")
print("=" * 100)

print(
    f"F0: {p0:,}"
)

print(
    f"F3: {p3:,}"
)

print(
    f"F4: {p4:,}"
)

print(
    f"F4-F3: {p4-p3:,}"
)


# ------------------------------------------------------------
# Endpoint equivalence
# ------------------------------------------------------------

f0.eval()
f3.eval()
f4.eval()

x = torch.randn(
    1,
    3,
    IMG_SIZE,
    IMG_SIZE,
    device=DEVICE,
)

# DSM input follows the real training interface:
# [B, H, W].
# The model itself adds the single channel dimension.
y = torch.randn(
    1,
    IMG_SIZE,
    IMG_SIZE,
    device=DEVICE,
)

with torch.no_grad():
    out0 = f0(x, y)
    out3 = f3(x, y)

    f4.set_gate_override(
        0.0
    )

    out4_as_f0 = f4(
        x,
        y,
    )

    f4.set_gate_override(
        1.0
    )

    out4_as_f3 = f4(
        x,
        y,
    )


d0 = (
    out4_as_f0
    - out0
).abs().max().item()

d3 = (
    out4_as_f3
    - out3
).abs().max().item()


print()
print("=" * 100)
print("STRICT ENDPOINT CHECK")
print("=" * 100)

print(
    "F4 gate=0 vs F0 "
    f"max_abs_diff = {d0:.12g}"
)

print(
    "F4 gate=1 vs F3 "
    f"max_abs_diff = {d3:.12g}"
)


if d0 > 1e-6:
    raise RuntimeError(
        "F4 gate=0 does not "
        "match F0"
    )

if d3 > 1e-6:
    raise RuntimeError(
        "F4 gate=1 does not "
        "match F3"
    )

print(
    "[PASS] strict endpoint "
    "equivalence"
)


# ------------------------------------------------------------
# Normal adaptive initialization
# ------------------------------------------------------------

f4.set_gate_override(
    None
)

with torch.no_grad():
    _ = f4(
        x,
        y,
    )


gates = (
    f4.get_last_gates()
)

print()
print("=" * 100)
print("INITIAL GATES")
print("=" * 100)

for stage, gate in gates:
    print(
        f"stage={stage} | "
        f"shape={tuple(gate.shape)} | "
        f"mean={gate.mean().item():.6f} | "
        f"min={gate.min().item():.6f} | "
        f"max={gate.max().item():.6f}"
    )


if len(gates) != 3:
    raise RuntimeError(
        f"Expected 3 gated stages, "
        f"got {len(gates)}"
    )

for _, gate in gates:
    m = gate.mean().item()

    if abs(
        m - 0.10
    ) > 1e-4:
        raise RuntimeError(
            f"Unexpected initial "
            f"gate mean {m}"
        )


print()
print(
    "[PASS] three adaptive "
    "decoder stages"
)

print(
    "[PASS] initial gate "
    "is approximately 0.10"
)

print()
print(
    "ALL F4 STRUCTURAL "
    "CHECKS PASSED"
)
