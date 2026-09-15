from pathlib import Path
import copy

import numpy as np
import torch

from model.vitcross_seg_modeling_freq_ablation import (
    VisionTransformerFreqAblation,
    CONFIGS,
)

from model.vitcross_seg_modeling_adaptive_multiband_variants import (
    VisionTransformerMultiBandVariant,
)


ROOT = Path(
    "/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
)

PRETRAIN = (
    ROOT
    / "../08_assets/pretrained/ftransunet/R50+ViT-B_16.npz"
).resolve()

IMG_SIZE = 128

MODES = [
    ("R1", "shared_spatial", 2324),
    ("R3", "modality_global", 2904),
    ("R4", "modality_static", 8),
]


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


def build_base():
    torch.manual_seed(42)

    return VisionTransformerFreqAblation(
        make_config(),
        img_size=IMG_SIZE,
        num_classes=6,
        freq_variant="F0",
    )


def build_variant(mode):
    torch.manual_seed(42)

    return VisionTransformerMultiBandVariant(
        make_config(),
        img_size=IMG_SIZE,
        num_classes=6,
        router_mode=mode,
    )


print("=" * 100)
print("MULTI-BAND VARIANTS FULL-MODEL INTEGRATION TEST")
print("device   : CPU")
print("img_size :", IMG_SIZE)
print("pretrain :", PRETRAIN)
print("=" * 100)

if not PRETRAIN.is_file():
    raise FileNotFoundError(
        PRETRAIN
    )

weights = np.load(
    str(PRETRAIN)
)

# Fixed input used by every test.
torch.manual_seed(20260914)

optical = torch.randn(
    1,
    3,
    IMG_SIZE,
    IMG_SIZE,
)

# IMPORTANT:
# Embeddings.forward() internally performs y.unsqueeze(1).
dsm = torch.randn(
    1,
    IMG_SIZE,
    IMG_SIZE,
)


for label, mode, expected_delta in MODES:

    print()
    print("=" * 100)
    print(label, mode)
    print("=" * 100)

    base = build_base()
    model = build_variant(
        mode
    )

    base_params = sum(
        p.numel()
        for p in base.parameters()
    )

    model_params = sum(
        p.numel()
        for p in model.parameters()
    )

    delta = (
        model_params
        - base_params
    )

    print(
        "base parameters     =",
        base_params,
    )

    print(
        "variant parameters  =",
        model_params,
    )

    print(
        "parameter delta     =",
        delta,
    )

    if delta != expected_delta:
        raise RuntimeError(
            f"{mode}: expected parameter delta "
            f"{expected_delta}, got {delta}"
        )

    # --------------------------------------------------------
    # Common-state equality before pretrained loading
    # --------------------------------------------------------

    sb = base.state_dict()
    sv = model.state_dict()

    common = (
        set(sb.keys())
        & set(sv.keys())
    )

    mismatch = []

    for k in sorted(common):

        if sb[k].shape != sv[k].shape:
            mismatch.append(
                (
                    k,
                    "shape",
                    tuple(sb[k].shape),
                    tuple(sv[k].shape),
                )
            )
            continue

        if not torch.equal(
            sb[k],
            sv[k],
        ):
            mismatch.append(
                (
                    k,
                    "value",
                )
            )

    extra = sorted(
        set(sv.keys())
        - set(sb.keys())
    )

    print(
        "common mismatch keys =",
        len(mismatch),
    )

    print(
        "variant extra keys   =",
        len(extra),
    )

    for k in extra:
        print(
            "  EXTRA:",
            k,
        )

    if mismatch:
        print(
            "First mismatches:"
        )

        for x in mismatch[:20]:
            print(x)

        raise RuntimeError(
            f"{mode}: common initial state differs"
        )

    # --------------------------------------------------------
    # Same pretrained loader
    # --------------------------------------------------------

    print(
        "loading pretrained base..."
    )

    base.load_from(
        weights=weights
    )

    print(
        "loading pretrained variant..."
    )

    model.load_from(
        weights=weights
    )

    sb = base.state_dict()
    sv = model.state_dict()

    mismatch_after = []

    for k in sorted(common):

        if sb[k].shape != sv[k].shape:
            continue

        if not torch.equal(
            sb[k],
            sv[k],
        ):
            mismatch_after.append(
                k
            )

    print(
        "postload common mismatch keys =",
        len(mismatch_after),
    )

    if mismatch_after:
        print(
            mismatch_after[:20]
        )

        raise RuntimeError(
            f"{mode}: common pretrained state differs"
        )

    # --------------------------------------------------------
    # Full forward exact identity check
    # --------------------------------------------------------

    base.eval()
    model.eval()

    with torch.inference_mode():

        out_base = base(
            optical,
            dsm,
        )

        out_var = model(
            optical,
            dsm,
        )

    print(
        "base output shape    =",
        tuple(out_base.shape),
    )

    print(
        "variant output shape =",
        tuple(out_var.shape),
    )

    max_diff = (
        out_base
        - out_var
    ).abs().max().item()

    mean_diff = (
        out_base
        - out_var
    ).abs().mean().item()

    print(
        "fullmodel max_abs_diff  =",
        max_diff,
    )

    print(
        "fullmodel mean_abs_diff =",
        mean_diff,
    )

    if max_diff != 0.0:
        raise RuntimeError(
            f"{mode}: full model is not exact "
            "F0 identity at initialization"
        )

    # --------------------------------------------------------
    # Diagnostics shape check
    # --------------------------------------------------------

    diag = (
        model
        .get_multiband_diagnostics()
    )

    ow = diag[
        "optical_weights"
    ]

    dw = diag[
        "dsm_weights"
    ]

    os = diag[
        "optical_scales"
    ]

    ds = diag[
        "dsm_scales"
    ]

    print(
        "optical weights shape =",
        tuple(ow.shape),
    )

    print(
        "dsm weights shape     =",
        tuple(dw.shape),
    )

    print(
        "optical weight mean   =",
        float(
            ow.mean()
        ),
    )

    print(
        "dsm weight mean       =",
        float(
            dw.mean()
        ),
    )

    print(
        "optical scale mean    =",
        float(
            os.mean()
        ),
    )

    print(
        "dsm scale mean        =",
        float(
            ds.mean()
        ),
    )

    if (
        float(
            (
                ow.sum(dim=1)
                - 1.0
            ).abs().max()
        )
        != 0.0
    ):
        raise RuntimeError(
            f"{mode}: Optical weight sum invalid"
        )

    if (
        float(
            (
                dw.sum(dim=1)
                - 1.0
            ).abs().max()
        )
        != 0.0
    ):
        raise RuntimeError(
            f"{mode}: DSM weight sum invalid"
        )

    if (
        float(
            (
                os - 1.0
            ).abs().max()
        )
        != 0.0
    ):
        raise RuntimeError(
            f"{mode}: Optical scale not neutral"
        )

    if (
        float(
            (
                ds - 1.0
            ).abs().max()
        )
        != 0.0
    ):
        raise RuntimeError(
            f"{mode}: DSM scale not neutral"
        )

    if mode == "shared_spatial":

        if ow.shape[-2:] == (
            1,
            1,
        ):
            raise RuntimeError(
                "R1 unexpectedly lost spatial routing"
            )

        if (
            ow - dw
        ).abs().max().item() != 0.0:
            raise RuntimeError(
                "R1 Optical/DSM routing is not shared"
            )

    if mode in (
        "modality_global",
        "modality_static",
    ):
        if ow.shape[-2:] != (
            1,
            1,
        ):
            raise RuntimeError(
                f"{mode}: expected global weights"
            )

    print()
    print(
        f"[PASS] {label} {mode}"
    )

    del base
    del model


print()
print("=" * 100)
print(
    "ALL MULTI-BAND FULL-MODEL INTEGRATION TESTS: PASS"
)
print("=" * 100)
