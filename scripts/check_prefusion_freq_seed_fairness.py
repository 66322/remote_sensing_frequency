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


DEVICE = torch.device(
    "cuda"
    if torch.cuda.is_available()
    else "cpu"
)


def make_config():
    config = copy.deepcopy(
        CONFIGS["R50-ViT-B_16"]
    )

    config.n_classes = 6
    config.n_skip = 3
    config.patches.grid = (
        16,
        16,
    )

    return config


# ============================================================
# Construct F0
# ============================================================

torch.manual_seed(42)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(42)

f0 = VisionTransformerFreqAblation(
    make_config(),
    img_size=256,
    num_classes=6,
    freq_variant="F0",
).to(DEVICE)


# ============================================================
# Reset seed and construct P1 independently.
#
# No state_dict transfer is allowed here.
# ============================================================

torch.manual_seed(42)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(42)

p1 = VisionTransformerPreFusionFreq(
    make_config(),
    img_size=256,
    num_classes=6,
).to(DEVICE)


f0_sd = f0.state_dict()
p1_sd = p1.state_dict()


f0_keys = set(f0_sd)
p1_keys = set(p1_sd)

missing_from_p1 = sorted(
    f0_keys - p1_keys
)

extra_in_p1 = sorted(
    p1_keys - f0_keys
)


print(
    "missing common keys:",
    missing_from_p1,
)

print(
    "P1-only keys:",
    extra_in_p1,
)


if missing_from_p1:
    raise RuntimeError(
        "P1 lost F0 state_dict keys"
    )


bad_extra = [
    k
    for k in extra_in_p1
    if ".prefreq0." not in k
]

if bad_extra:
    raise RuntimeError(
        f"Unexpected P1-only keys: "
        f"{bad_extra}"
    )


# ============================================================
# Every common tensor must be bitwise identical.
# ============================================================

mismatched = []

max_common_diff = 0.0


for key in sorted(f0_keys):
    a = f0_sd[key]
    b = p1_sd[key]

    if a.shape != b.shape:
        mismatched.append(
            (
                key,
                "shape",
                tuple(a.shape),
                tuple(b.shape),
            )
        )
        continue

    if not torch.equal(
        a.cpu(),
        b.cpu(),
    ):
        if (
            a.is_floating_point()
            or a.is_complex()
        ):
            diff = float(
                (
                    a.detach().float().cpu()
                    - b.detach().float().cpu()
                )
                .abs()
                .max()
            )

            max_common_diff = max(
                max_common_diff,
                diff,
            )
        else:
            diff = "nonfloat"

        mismatched.append(
            (
                key,
                diff,
            )
        )


print(
    "common tensor mismatches:",
    len(mismatched),
)

print(
    "max common tensor diff:",
    max_common_diff,
)


if mismatched:
    print(
        "first mismatches:"
    )

    for item in mismatched[:20]:
        print(
            "  ",
            item,
        )

    raise RuntimeError(
        "Seed-fair common initialization failed"
    )


# ============================================================
# Forward identity WITHOUT copying F0 state into P1.
# ============================================================

f0.eval()
p1.eval()


torch.manual_seed(12345)

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

    out_p1 = p1(
        optical,
        dsm,
    )


diff = (
    out_f0
    - out_p1
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


if float(diff.max()) != 0.0:
    raise RuntimeError(
        "Independent-construction "
        "identity failed"
    )


if not (
    float(scale.mean()) == 1.0
    and float(scale.min()) == 1.0
    and float(scale.max()) == 1.0
):
    raise RuntimeError(
        "Initial P1 scale is not exactly 1"
    )


prefreq_numel = sum(
    p.numel()
    for name, p
    in p1.named_parameters()
    if ".prefreq0." in name
)


print(
    "prefreq parameters:",
    prefreq_numel,
)


if prefreq_numel != 593:
    raise RuntimeError(
        f"Unexpected prefreq parameter count: "
        f"{prefreq_numel}"
    )


print()
print(
    "[PASS] P1 is seed-fair and "
    "exactly F0-equivalent at initialization"
)
