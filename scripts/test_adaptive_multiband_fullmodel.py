import copy
import random
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(
    "/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
)

PRETRAIN = Path(
    "/home/jovyan/zzx/paper_rebuild/08_assets/pretrained/"
    "ftransunet/R50+ViT-B_16.npz"
)

sys.path.insert(
    0,
    str(ROOT),
)

from model.vitcross_seg_modeling_freq_ablation import (
    VisionTransformerFreqAblation,
    CONFIGS,
)

from model.vitcross_seg_modeling_adaptive_multiband import (
    VisionTransformerAdaptiveMultiBand,
)


SEED = 42
IMG_SIZE = 128


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def make_config():
    config = copy.deepcopy(
        CONFIGS["R50-ViT-B_16"]
    )

    config.n_classes = 6
    config.n_skip = 3

    config.patches.grid = (
        IMG_SIZE // 16,
        IMG_SIZE // 16,
    )

    return config


torch.set_num_threads(8)

print("=" * 100)
print("FULL-MODEL ADAPTIVE MULTI-BAND INTEGRATION TEST")
print("=" * 100)
print("device   : CPU")
print("img_size :", IMG_SIZE)


# ============================================================
# 1. Build exact F0 reference
# ============================================================

set_seed(SEED)

base_config = make_config()

base = VisionTransformerFreqAblation(
    config=base_config,
    img_size=IMG_SIZE,
    num_classes=6,
    freq_variant="F0",
)

base.eval()


# ============================================================
# 2. Build adaptive model from same seed
# ============================================================

set_seed(SEED)

adaptive_config = make_config()

adaptive = VisionTransformerAdaptiveMultiBand(
    config=adaptive_config,
    img_size=IMG_SIZE,
    num_classes=6,
)

adaptive.eval()


# ============================================================
# 3. Parameter-count delta
# ============================================================

base_params = sum(
    p.numel()
    for p in base.parameters()
)

adaptive_params = sum(
    p.numel()
    for p in adaptive.parameters()
)

delta = (
    adaptive_params
    - base_params
)

print()
print("base parameters     =", base_params)
print("adaptive parameters =", adaptive_params)
print("parameter delta     =", delta)

assert delta == 2904, (
    f"Expected +2904 parameters, got {delta}"
)


# ============================================================
# 4. Confirm insertion point
# ============================================================

hybrid = (
    adaptive
    .transformer
    .embeddings
    .hybrid_model
)

assert hasattr(
    hybrid,
    "multiband0",
)

print()
print(
    "hybrid model class =",
    hybrid.__class__.__name__,
)

print(
    "multiband class    =",
    hybrid.multiband0.__class__.__name__,
)


# ============================================================
# 5. Compare every common parameter BEFORE pretrained load
#
# Since both models were initialized from the same seed and
# AdaptiveMultiBand constructs F0 first, every original
# parameter must be bit-identical.
# ============================================================

base_state = (
    base.state_dict()
)

adaptive_state = (
    adaptive.state_dict()
)

missing_common = []
mismatch_common = []

for name, tensor in base_state.items():

    if name not in adaptive_state:
        missing_common.append(name)
        continue

    other = adaptive_state[name]

    if not torch.equal(
        tensor,
        other,
    ):
        mismatch_common.append(
            name
        )

extra_keys = [
    name
    for name in adaptive_state
    if name not in base_state
]

print()
print(
    "common missing keys   =",
    len(missing_common),
)

print(
    "common mismatch keys  =",
    len(mismatch_common),
)

print(
    "adaptive extra keys   =",
    len(extra_keys),
)

for name in extra_keys:
    print(
        "  EXTRA:",
        name,
    )

assert not missing_common, (
    missing_common[:10]
)

assert not mismatch_common, (
    mismatch_common[:10]
)

assert extra_keys, (
    "Expected multiband0 parameters"
)

assert all(
    ".multiband0."
    in name
    for name in extra_keys
), extra_keys


# ============================================================
# 6. Pretrained-loader compatibility
# ============================================================

if not PRETRAIN.is_file():
    raise FileNotFoundError(
        PRETRAIN
    )

print()
print(
    "loading pretrained:",
    PRETRAIN,
)

weights = np.load(
    str(PRETRAIN)
)

base.load_from(
    weights=weights
)

adaptive.load_from(
    weights=weights
)

print(
    "[PASS] pretrained loader"
)


# ============================================================
# 7. Compare common parameters AFTER pretrained load
# ============================================================

base_state = (
    base.state_dict()
)

adaptive_state = (
    adaptive.state_dict()
)

postload_mismatch = []

for name, tensor in base_state.items():

    if not torch.equal(
        tensor,
        adaptive_state[name],
    ):
        postload_mismatch.append(
            name
        )

print(
    "postload common mismatch keys =",
    len(postload_mismatch),
)

assert not postload_mismatch, (
    postload_mismatch[:10]
)


# ============================================================
# 8. Full-model identity forward
# ============================================================

set_seed(
    SEED + 1000
)

optical = torch.randn(
    1,
    3,
    IMG_SIZE,
    IMG_SIZE,
)

# IMPORTANT:
# Embeddings.forward() internally executes:
#     y = y.unsqueeze(1)
#
# Therefore DSM enters the full model as [B,H,W],
# not [B,1,H,W].
dsm = torch.randn(
    1,
    IMG_SIZE,
    IMG_SIZE,
)

with torch.inference_mode():

    out_base = base(
        optical,
        dsm,
    )

    out_adaptive = adaptive(
        optical,
        dsm,
    )


print()
print(
    "base output shape     =",
    tuple(
        out_base.shape
    ),
)

print(
    "adaptive output shape =",
    tuple(
        out_adaptive.shape
    ),
)

assert (
    out_base.shape
    == out_adaptive.shape
)

assert tuple(
    out_base.shape
) == (
    1,
    6,
    IMG_SIZE,
    IMG_SIZE,
)


max_abs_diff = float(
    (
        out_base
        - out_adaptive
    )
    .abs()
    .max()
)

mean_abs_diff = float(
    (
        out_base
        - out_adaptive
    )
    .abs()
    .mean()
)

print(
    "fullmodel max_abs_diff  =",
    max_abs_diff,
)

print(
    "fullmodel mean_abs_diff =",
    mean_abs_diff,
)

assert max_abs_diff == 0.0, (
    "Adaptive model is not exact F0 "
    "at identity initialization"
)


# ============================================================
# 9. Full-model diagnostics
# ============================================================

diag = (
    adaptive
    .get_multiband_diagnostics()
)

wo = diag[
    "optical_weights"
]

wd = diag[
    "dsm_weights"
]

so = diag[
    "optical_scales"
]

sd = diag[
    "dsm_scales"
]

print()
print(
    "optical weights shape =",
    tuple(
        wo.shape
    ),
)

print(
    "dsm weights shape     =",
    tuple(
        wd.shape
    ),
)

print(
    "optical weight mean   =",
    float(
        wo.mean()
    ),
)

print(
    "dsm weight mean       =",
    float(
        wd.mean()
    ),
)

print(
    "optical scale mean    =",
    float(
        so.mean()
    ),
)

print(
    "dsm scale mean        =",
    float(
        sd.mean()
    ),
)

assert (
    wo.shape[1]
    == 4
)

assert (
    wd.shape[1]
    == 4
)

assert float(
    (
        wo - 0.25
    )
    .abs()
    .max()
) == 0.0

assert float(
    (
        wd - 0.25
    )
    .abs()
    .max()
) == 0.0

assert float(
    (
        so - 1.0
    )
    .abs()
    .max()
) == 0.0

assert float(
    (
        sd - 1.0
    )
    .abs()
    .max()
) == 0.0


# ============================================================
# 10. New-module parameter count inside full model
# ============================================================

new_numel = sum(
    p.numel()
    for name, p
    in adaptive.named_parameters()
    if ".multiband0." in name
)

print()
print(
    "fullmodel multiband0 parameters =",
    new_numel,
)

assert (
    new_numel
    == 2904
)


print()
print("=" * 100)
print(
    "ADAPTIVE MULTI-BAND FULL-MODEL INTEGRATION: PASS"
)
print("=" * 100)
