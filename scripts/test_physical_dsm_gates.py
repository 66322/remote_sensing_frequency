import os
import sys
from pathlib import Path

os.environ[
    "CUBLAS_WORKSPACE_CONFIG"
] = ":4096:8"

ROOT = Path(
    "/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
)

sys.path.insert(
    0,
    str(ROOT),
)

import torch

from model.vitcross_seg_modeling_adaptive_multiband_variants import (
    ModalitySpecificStaticMultiBandRouter,
)

from model.vitcross_seg_modeling_physical_dsm import (
    PhysicalDSMStaticMultiBandRouter,
)


torch.manual_seed(42)

device = torch.device(
    "cuda:0"
)


# ============================================================
# Gate 1
# s=1 physical DSM bands == original R4 bands
# ============================================================

pp = (
    ModalitySpecificStaticMultiBandRouter(
        hidden_channels=16,
        kernel_sizes=(
            3,
            7,
            15,
            31,
        ),
    )
    .to(device)
    .eval()
)

ph = (
    PhysicalDSMStaticMultiBandRouter(
        hidden_channels=16,
        kernel_sizes=(
            3,
            7,
            15,
            31,
        ),
    )
    .to(device)
    .eval()
)

ph.load_state_dict(
    pp.state_dict(),
    strict=True,
)

dsm = torch.randn(
    1,
    64,
    256,
    256,
    device=device,
)

with torch.no_grad():

    pp_bands, _ = (
        pp.decompose(
            dsm
        )
    )

    ph_bands = (
        ph.physical_dsm_decompose(
            dsm,
            [1.0],
        )
    )

diff = (
    pp_bands
    - ph_bands
).abs().max().item()

print(
    "GATE1 max band diff:",
    diff
)

if diff != 0.0:
    raise RuntimeError(
        f"GATE1 FAIL: diff={diff}"
    )

print(
    "[PASS] GATE1 scale=1 exact decomposition equivalence"
)


# ============================================================
# Gate 2
# zero static logits -> exact identity
# even when physical scales differ
# ============================================================

opt = torch.randn(
    4,
    64,
    256,
    256,
    device=device,
)

dsm = torch.randn(
    4,
    64,
    256,
    256,
    device=device,
)

ph.set_sample_scales(
    [
        0.5,
        0.75,
        1.5,
        2.0,
    ]
)

with torch.no_grad():

    out_o, out_d = ph(
        opt,
        dsm,
    )

opt_diff = (
    out_o - opt
).abs().max().item()

dsm_diff = (
    out_d - dsm
).abs().max().item()

print(
    "GATE2 optical identity diff:",
    opt_diff
)

print(
    "GATE2 DSM identity diff:",
    dsm_diff
)

if (
    opt_diff != 0.0
    or dsm_diff != 0.0
):
    raise RuntimeError(
        "GATE2 FAIL"
    )

print(
    "[PASS] GATE2 zero-init exact identity"
)


# ============================================================
# Gate 3
# each sample receives its own canonical resolution
# ============================================================

sizes = (
    ph.last_canonical_sizes
)

scales = (
    ph.last_sample_scales
)

print(
    "GATE3 scales:",
    scales
)

print(
    "GATE3 canonical sizes:",
    sizes
)

expected = (
    (512, 512),
    (341, 341),
    (171, 171),
    (128, 128),
)

if sizes != expected:
    raise RuntimeError(
        "GATE3 FAIL: "
        f"expected={expected}, got={sizes}"
    )

print(
    "[PASS] GATE3 per-sample canonical grids"
)


# ============================================================
# Gate 4
# backward smoke:
# verifies interpolation + pooling path is compatible with
# current deterministic CUDA setup.
# ============================================================

ph.train()

opt = torch.randn(
    2,
    64,
    128,
    128,
    device=device,
    requires_grad=True,
)

dsm = torch.randn(
    2,
    64,
    128,
    128,
    device=device,
    requires_grad=True,
)

ph.set_sample_scales(
    [
        0.7,
        1.6,
    ]
)

out_o, out_d = ph(
    opt,
    dsm,
)

loss = (
    out_o.square().mean()
    +
    out_d.square().mean()
)

loss.backward()

if (
    opt.grad is None
    or dsm.grad is None
):
    raise RuntimeError(
        "GATE4 FAIL: missing gradient"
    )

if not torch.isfinite(
    opt.grad
).all():
    raise RuntimeError(
        "GATE4 FAIL: non-finite optical gradient"
    )

if not torch.isfinite(
    dsm.grad
).all():
    raise RuntimeError(
        "GATE4 FAIL: non-finite DSM gradient"
    )

print(
    "[PASS] GATE4 backward path"
)

print()
print(
    "ALL PHYSICAL DSM GATES PASS"
)
