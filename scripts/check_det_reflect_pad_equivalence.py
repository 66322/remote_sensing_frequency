import sys
from pathlib import Path

import torch
import torch.nn.functional as F


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from model.vitcross_seg_modeling_prefusion_freq_detpair import (
    CrossModalHFCalibration,
)


device = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


torch.manual_seed(42)

x = torch.randn(
    2,
    64,
    17,
    23,
    device=device,
)


reference = F.pad(
    x,
    (1, 1, 1, 1),
    mode="reflect",
)

deterministic = (
    CrossModalHFCalibration
    .deterministic_reflect_pad1(
        x
    )
)


diff = (
    reference
    - deterministic
).abs()


print(
    "input shape:",
    tuple(x.shape),
)

print(
    "output shape:",
    tuple(reference.shape),
)

print(
    "pad max_abs_diff:",
    float(diff.max()),
)

print(
    "pad mean_abs_diff:",
    float(diff.mean()),
)

print(
    "torch.equal:",
    torch.equal(
        reference,
        deterministic,
    ),
)


if not torch.equal(
    reference,
    deterministic,
):
    raise RuntimeError(
        "Manual reflect padding is not "
        "exactly equivalent"
    )


# ------------------------------------------------------------
# Also verify local decomposition.
# ------------------------------------------------------------

ref_smooth = F.avg_pool2d(
    reference,
    kernel_size=3,
    stride=1,
    padding=0,
)

ref_high = (
    x
    - ref_smooth
)

det_smooth, det_high = (
    CrossModalHFCalibration
    .local_decompose(
        x
    )
)


smooth_diff = (
    ref_smooth
    - det_smooth
).abs()

high_diff = (
    ref_high
    - det_high
).abs()


print()
print(
    "smooth max_abs_diff:",
    float(smooth_diff.max()),
)

print(
    "high max_abs_diff:",
    float(high_diff.max()),
)


if not torch.equal(
    ref_smooth,
    det_smooth,
):
    raise RuntimeError(
        "Smooth decomposition differs"
    )


if not torch.equal(
    ref_high,
    det_high,
):
    raise RuntimeError(
        "High-frequency decomposition differs"
    )


print()
print(
    "[PASS] deterministic reflect-pad "
    "is forward-exact"
)
