import copy
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

from model.vitcross_seg_modeling_prefusion_freq import (
    VisionTransformerPreFusionFreq as OriginalP1,
)

from model.vitcross_seg_modeling_prefusion_freq_detpair import (
    VisionTransformerPreFusionFreq as DetP1,
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


# ------------------------------------------------------------
# Build original P1.
# ------------------------------------------------------------

torch.manual_seed(42)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(42)

original = OriginalP1(
    make_config(),
    img_size=256,
    num_classes=6,
).to(DEVICE)


# ------------------------------------------------------------
# Build deterministic P1 and copy exact state.
# ------------------------------------------------------------

torch.manual_seed(999)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(999)

det = DetP1(
    make_config(),
    img_size=256,
    num_classes=6,
).to(DEVICE)


load_result = det.load_state_dict(
    original.state_dict(),
    strict=True,
)

print(
    "missing:",
    load_result.missing_keys,
)

print(
    "unexpected:",
    load_result.unexpected_keys,
)


original.eval()
det.eval()


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

    out_original = original(
        optical,
        dsm,
    )

    out_det = det(
        optical,
        dsm,
    )


diff = (
    out_original
    - out_det
).abs()


print(
    "output max_abs_diff:",
    float(diff.max()),
)

print(
    "output mean_abs_diff:",
    float(diff.mean()),
)


diag_o = (
    original
    .get_prefreq_diagnostics()
)

diag_d = (
    det
    .get_prefreq_diagnostics()
)


scale_diff = (
    diag_o["scale"]
    - diag_d["scale"]
).abs()

disc_diff = (
    diag_o["discrepancy"]
    - diag_d["discrepancy"]
).abs()


print(
    "scale max_abs_diff:",
    float(scale_diff.max()),
)

print(
    "discrepancy max_abs_diff:",
    float(disc_diff.max()),
)


if float(diff.max()) != 0.0:
    raise RuntimeError(
        "Whole-model output differs"
    )

if float(scale_diff.max()) != 0.0:
    raise RuntimeError(
        "Scale diagnostic differs"
    )

if float(disc_diff.max()) != 0.0:
    raise RuntimeError(
        "Discrepancy diagnostic differs"
    )


print()
print(
    "[PASS] deterministic P1 is "
    "forward-identical to original P1"
)
