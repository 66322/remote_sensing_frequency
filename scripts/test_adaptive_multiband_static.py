import sys
from pathlib import Path

ROOT = Path(
    "/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
)

sys.path.insert(
    0,
    str(ROOT),
)

import torch

from model.vitcross_seg_modeling_adaptive_multiband import (
    ModalitySpecificAdaptiveMultiBandRouter,
)


torch.manual_seed(
    42
)

module = (
    ModalitySpecificAdaptiveMultiBandRouter(
        hidden_channels=16,
        kernel_sizes=(
            3,
            7,
            15,
            31,
        ),
    )
)

module.train()


# ============================================================
# Parameter count
# ============================================================

params = sum(
    p.numel()
    for p in module.parameters()
)

print(
    "parameter_count =",
    params,
)

assert params == 2904, (
    f"Unexpected parameter count: {params}"
)


# ============================================================
# Zero initialization
# ============================================================

last = module.context[-1]

print(
    "final_weight_absmax =",
    float(
        last.weight.abs().max()
    ),
)

print(
    "final_bias_absmax =",
    float(
        last.bias.abs().max()
    ),
)

assert (
    float(
        last.weight.abs().max()
    )
    == 0.0
)

assert (
    float(
        last.bias.abs().max()
    )
    == 0.0
)


# ============================================================
# Exact identity initialization
# ============================================================

optical = torch.randn(
    2,
    64,
    64,
    64,
)

dsm = torch.randn(
    2,
    64,
    64,
    64,
)

with torch.no_grad():

    out_o, out_d = module(
        optical,
        dsm,
    )

    err_o = float(
        (
            out_o
            - optical
        )
        .abs()
        .max()
    )

    err_d = float(
        (
            out_d
            - dsm
        )
        .abs()
        .max()
    )

print(
    "identity_optical_maxerr =",
    err_o,
)

print(
    "identity_dsm_maxerr =",
    err_d,
)

assert err_o == 0.0
assert err_d == 0.0


# ============================================================
# Diagnostics shape
# ============================================================

w = module.last_weights

print(
    "weights_shape =",
    tuple(
        w.shape
    ),
)

assert (
    tuple(w.shape)
    == (
        2,
        2,
        4,
        64,
        64,
    )
)


# ============================================================
# Weight normalization
# ============================================================

wo = (
    module
    .last_optical_weights
)

wd = (
    module
    .last_dsm_weights
)

wo_sum_err = float(
    (
        wo.sum(
            dim=1
        )
        - 1.0
    )
    .abs()
    .max()
)

wd_sum_err = float(
    (
        wd.sum(
            dim=1
        )
        - 1.0
    )
    .abs()
    .max()
)

print(
    "optical_weight_sum_maxerr =",
    wo_sum_err,
)

print(
    "dsm_weight_sum_maxerr =",
    wd_sum_err,
)

assert wo_sum_err < 1e-7
assert wd_sum_err < 1e-7


# ============================================================
# Neutral scales
# ============================================================

so = (
    module
    .last_optical_scales
)

sd = (
    module
    .last_dsm_scales
)

so_err = float(
    (
        so - 1.0
    )
    .abs()
    .max()
)

sd_err = float(
    (
        sd - 1.0
    )
    .abs()
    .max()
)

print(
    "optical_scale_one_maxerr =",
    so_err,
)

print(
    "dsm_scale_one_maxerr =",
    sd_err,
)

assert so_err == 0.0
assert sd_err == 0.0


# ============================================================
# Gradient path
#
# At identity initialization the final routing layer must
# already receive gradients.
#
# The first context layer may initially have zero gradient,
# because the final conv is zero initialized. That is expected.
# ============================================================

module.zero_grad(
    set_to_none=True
)

out_o, out_d = module(
    optical,
    dsm,
)

loss = (
    out_o.square().mean()
    + out_d.square().mean()
)

loss.backward()

final_grad = (
    module
    .context[-1]
    .weight
    .grad
)

assert final_grad is not None

final_grad_max = float(
    final_grad
    .abs()
    .max()
)

print(
    "final_router_grad_absmax =",
    final_grad_max,
)

assert final_grad_max > 0.0


# ============================================================
# Frequency-band shapes
# ============================================================

with torch.no_grad():

    bands_o, low_o = (
        module.decompose(
            optical
        )
    )

print(
    "bands_shape =",
    tuple(
        bands_o.shape
    ),
)

print(
    "low_base_shape =",
    tuple(
        low_o.shape
    ),
)

assert (
    tuple(
        bands_o.shape
    )
    == (
        2,
        4,
        64,
        64,
        64,
    )
)

assert (
    tuple(
        low_o.shape
    )
    == (
        2,
        64,
        64,
        64,
    )
)


print()
print("=" * 80)
print("ADAPTIVE MULTI-BAND STATIC TEST: PASS")
print("=" * 80)
