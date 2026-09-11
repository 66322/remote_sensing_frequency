import copy
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model.vitcross_seg_modeling_freqfusion import (
    CONFIGS,
)

from model.vitcross_seg_modeling_freq_ablation import (
    VisionTransformerFreqAblation,
)

from model.vitcross_seg_modeling_prefusion_freq import (
    VisionTransformerPreFusionFreq,
)


device = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)

torch.manual_seed(42)


config0 = copy.deepcopy(
    CONFIGS["R50-ViT-B_16"]
)

config0.n_classes = 6
config0.n_skip = 3
config0.patches.grid = (
    16,
    16,
)


config1 = copy.deepcopy(
    config0
)


f0 = VisionTransformerFreqAblation(
    config0,
    img_size=256,
    num_classes=6,
    freq_variant="F0",
).to(device)


p1 = VisionTransformerPreFusionFreq(
    config1,
    img_size=256,
    num_classes=6,
).to(device)


# Copy every common F0 parameter into P1.
result = p1.load_state_dict(
    f0.state_dict(),
    strict=False,
)

print(
    "missing:",
    result.missing_keys,
)

print(
    "unexpected:",
    result.unexpected_keys,
)


# All missing parameters must belong to prefreq0.
bad_missing = [
    k
    for k in result.missing_keys
    if ".prefreq0." not in k
]

if bad_missing:
    raise RuntimeError(
        f"Unexpected missing keys: "
        f"{bad_missing}"
    )


f0.eval()
p1.eval()


optical = torch.randn(
    1,
    3,
    256,
    256,
    device=device,
)

dsm = torch.randn(
    1,
    256,
    256,
    device=device,
)


with torch.no_grad():
    y0 = f0(
        optical,
        dsm,
    )

    y1 = p1(
        optical,
        dsm,
    )


diff = (
    y0 - y1
).abs()


print(
    "output max_abs_diff:",
    float(diff.max()),
)

print(
    "output mean_abs_diff:",
    float(diff.mean()),
)


diag = (
    p1
    .get_prefreq_diagnostics()
)

scale = diag["scale"]

print(
    "scale shape:",
    tuple(scale.shape),
)

print(
    "scale mean/min/max:",
    float(scale.mean()),
    float(scale.min()),
    float(scale.max()),
)


if (
    float(diff.max())
    > 1e-5
):
    raise RuntimeError(
        "Identity endpoint failed"
    )


if (
    abs(
        float(scale.mean())
        - 1.0
    )
    > 1e-7
):
    raise RuntimeError(
        "Initial scale is not 1"
    )


print(
    "[PASS] P1 initialization "
    "is F0-equivalent"
)
