import os
import sys
import csv
import json
import time
import copy
import argparse
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

ROOT = Path(
    "/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
)

DATA_ROOT = Path(
    "/home/jovyan/zzx/projects_zys/raw_extract/Potsdam_unzipped"
)

RGB_ROOT = DATA_ROOT / "2_Ortho_RGB"
DSM_ROOT = DATA_ROOT / "1_DSM" / "1_DSM"
LABEL_ROOT = DATA_ROOT / "5_Labels_for_participants"
NOBOUNDARY_ROOT = (
    DATA_ROOT
    / "5_Labels_for_participants_no_Boundary"
)

OUT = (
    ROOT
    / "records"
    / "e51b_gsd_robustness_scale1_20260914"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)

sys.path.insert(
    0,
    str(ROOT),
)

import numpy as np
import torch
from skimage import io
from scipy.ndimage import gaussian_filter, zoom

from model.vitcross_seg_modeling_freq_ablation import (
    CONFIGS,
)

from model.vitcross_seg_modeling_adaptive_multiband_variants import (
    VisionTransformerMultiBandVariant,
)

from model.vitcross_seg_modeling_physical_dsm import (
    VisionTransformerPhysicalDSM,
)


# ============================================================
# CONFIG
# ============================================================

DEVICE = torch.device("cuda:0")

TEST_IDS = [
    "4_10",
    "5_11",
    "2_11",
    "3_10",
    "6_11",
    "7_12",
]

PATCH = 512
TEST_STRIDE = 64
INFER_BATCH = 8

N_CLASSES = 6
IGNORE_INDEX = 255

NATIVE_GSD_M = 0.05

TARGET_GSDS_M = [
    0.05,
    0.07,
    0.09,
    0.12,
]

PALETTE = {
    (255, 255, 255): 0,
    (0, 0, 255): 1,
    (0, 255, 255): 2,
    (0, 255, 0): 3,
    (255, 255, 0): 4,
    (255, 0, 0): 5,
}

BLACK = (
    0,
    0,
    0,
)

PP_CKPT = (
    ROOT
    / "runs"
    / "potsdam_multiband_modality_static_seed42"
    / "checkpoints"
    / "model_iter_010000.pth"
)

PH_CKPT = (
    ROOT
    / "runs"
    / "potsdam_physical_dsm_modality_static_seed42"
    / "checkpoints"
    / "model_iter_004000.pth"
)


# ============================================================
# REPRODUCIBILITY
# ============================================================

torch.manual_seed(42)
torch.cuda.manual_seed_all(42)

torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True

torch.use_deterministic_algorithms(
    True
)


# ============================================================
# LABEL CONVERSION
# ============================================================

def convert_full_gt(rgb):
    out = np.full(
        rgb.shape[:2],
        IGNORE_INDEX,
        dtype=np.uint8,
    )

    matched = np.zeros(
        rgb.shape[:2],
        dtype=bool,
    )

    for color, idx in PALETTE.items():
        mask = np.all(
            rgb[..., :3]
            == np.asarray(
                color,
                dtype=rgb.dtype,
            ),
            axis=-1,
        )

        out[mask] = idx
        matched |= mask

    if not matched.all():
        raise RuntimeError(
            "Full GT unknown pixels: "
            f"{int((~matched).sum())}"
        )

    return out


def convert_noboundary_gt(rgb):
    out = np.full(
        rgb.shape[:2],
        IGNORE_INDEX,
        dtype=np.uint8,
    )

    recognized = np.zeros(
        rgb.shape[:2],
        dtype=bool,
    )

    for color, idx in PALETTE.items():
        mask = np.all(
            rgb[..., :3]
            == np.asarray(
                color,
                dtype=rgb.dtype,
            ),
            axis=-1,
        )

        out[mask] = idx
        recognized |= mask

    black = np.all(
        rgb[..., :3]
        == np.asarray(
            BLACK,
            dtype=rgb.dtype,
        ),
        axis=-1,
    )

    recognized |= black

    if not recognized.all():
        raise RuntimeError(
            "noBoundary GT unknown pixels: "
            f"{int((~recognized).sum())}"
        )

    return out


# ============================================================
# DATA
# ============================================================

def potsdam_dsm_name(tile_id):
    a, b = tile_id.split("_")

    return (
        f"dsm_potsdam_"
        f"{int(a):02d}_{int(b):02d}.tif"
    )


def load_test_tile(tile_id):
    optical_path = (
        RGB_ROOT
        / f"top_potsdam_{tile_id}_RGB.tif"
    )

    dsm_path = (
        DSM_ROOT
        / potsdam_dsm_name(tile_id)
    )

    full_path = (
        LABEL_ROOT
        / f"top_potsdam_{tile_id}_label.tif"
    )

    nb_path = (
        NOBOUNDARY_ROOT
        / (
            f"top_potsdam_{tile_id}_"
            "label_noBoundary.tif"
        )
    )

    for p in (
        optical_path,
        dsm_path,
        full_path,
        nb_path,
    ):
        if not p.is_file():
            raise FileNotFoundError(
                p
            )

    # Exact formal-training preprocessing.
    optical = (
        io.imread(
            str(optical_path)
        )[..., :3]
        .astype(np.float32)
        / 255.0
    )

    dsm = io.imread(
        str(dsm_path)
    ).astype(
        np.float32
    )

    dmin = float(
        dsm.min()
    )

    dmax = float(
        dsm.max()
    )

    if dmax <= dmin:
        raise RuntimeError(
            f"DSM zero range: {tile_id}"
        )

    # Exact formal protocol:
    # tile-wise DSM min-max normalization.
    dsm = (
        (dsm - dmin)
        / (dmax - dmin)
    ).astype(
        np.float32
    )

    full_gt = convert_full_gt(
        io.imread(
            str(full_path)
        )
    )

    nb_gt = convert_noboundary_gt(
        io.imread(
            str(nb_path)
        )
    )

    if not (
        optical.shape[:2]
        == dsm.shape
        == full_gt.shape
        == nb_gt.shape
    ):
        raise RuntimeError(
            f"Shape mismatch {tile_id}: "
            f"{optical.shape}, "
            f"{dsm.shape}, "
            f"{full_gt.shape}, "
            f"{nb_gt.shape}"
        )

    return {
        "optical": optical,
        "dsm": dsm,
        "full_gt": full_gt,
        "noboundary_gt": nb_gt,
    }


# ============================================================
# SYNTHETIC GSD
# ============================================================

def antialias_sigma(
    native_gsd,
    target_gsd,
):
    if target_gsd <= native_gsd:
        return 0.0

    ratio = (
        native_gsd
        / target_gsd
    )

    # Same E51-A2 definition.
    return max(
        0.0,
        0.5
        * (
            1.0 / ratio
            - 1.0
        ),
    )


def resize_continuous(
    x,
    target_h,
    target_w,
    sigma,
):
    """
    Optical / DSM:
        anti-alias Gaussian
        + bilinear-equivalent order=1 resampling.

    Returns exact requested target grid.
    """

    if (
        x.shape[0] == target_h
        and x.shape[1] == target_w
    ):
        return x.copy()

    if sigma > 0.0:
        if x.ndim == 3:
            x = gaussian_filter(
                x,
                sigma=(
                    sigma,
                    sigma,
                    0.0,
                ),
                mode="reflect",
            )
        else:
            x = gaussian_filter(
                x,
                sigma=sigma,
                mode="reflect",
            )

    fy = (
        float(target_h)
        / float(x.shape[0])
    )

    fx = (
        float(target_w)
        / float(x.shape[1])
    )

    if x.ndim == 3:
        y = zoom(
            x,
            zoom=(
                fy,
                fx,
                1.0,
            ),
            order=1,
            mode="reflect",
            prefilter=False,
        )
    else:
        y = zoom(
            x,
            zoom=(
                fy,
                fx,
            ),
            order=1,
            mode="reflect",
            prefilter=False,
        )

    if y.shape[:2] != (
        target_h,
        target_w,
    ):
        raise RuntimeError(
            "Continuous resampling shape mismatch: "
            f"wanted {(target_h, target_w)}, "
            f"got {y.shape[:2]}"
        )

    return y.astype(
        np.float32,
        copy=False,
    )


def resize_label(
    x,
    target_h,
    target_w,
):
    """
    Semantic labels:
        nearest-neighbor only.
    """

    if (
        x.shape[0] == target_h
        and x.shape[1] == target_w
    ):
        return x.copy()

    fy = (
        float(target_h)
        / float(x.shape[0])
    )

    fx = (
        float(target_w)
        / float(x.shape[1])
    )

    y = zoom(
        x,
        zoom=(
            fy,
            fx,
        ),
        order=0,
        mode="nearest",
        prefilter=False,
    )

    if y.shape != (
        target_h,
        target_w,
    ):
        raise RuntimeError(
            "Label resampling shape mismatch: "
            f"wanted {(target_h, target_w)}, "
            f"got {y.shape}"
        )

    return y.astype(
        np.uint8,
        copy=False,
    )


def resample_tile_to_gsd(
    data,
    target_gsd,
):
    H, W = data[
        "dsm"
    ].shape

    if abs(
        target_gsd
        - NATIVE_GSD_M
    ) < 1e-12:
        return (
            {
                k: v.copy()
                for k, v
                in data.items()
            },
            1.0,
            NATIVE_GSD_M,
        )

    ideal_factor = (
        NATIVE_GSD_M
        / target_gsd
    )

    target_h = int(
        round(
            H * ideal_factor
        )
    )

    target_w = int(
        round(
            W * ideal_factor
        )
    )

    if (
        target_h < PATCH
        or target_w < PATCH
    ):
        raise RuntimeError(
            "Target GSD makes tile smaller "
            "than inference patch"
        )

    sigma = antialias_sigma(
        NATIVE_GSD_M,
        target_gsd,
    )

    optical = resize_continuous(
        data["optical"],
        target_h,
        target_w,
        sigma,
    )

    dsm = resize_continuous(
        data["dsm"],
        target_h,
        target_w,
        sigma,
    )

    full_gt = resize_label(
        data["full_gt"],
        target_h,
        target_w,
    )

    nb_gt = resize_label(
        data["noboundary_gt"],
        target_h,
        target_w,
    )

    # Important:
    # use ACTUAL resampled grid ratio, consistent with
    # E51-B training's effective_scale = PATCH/source_size.
    scale_y = (
        float(target_h)
        / float(H)
    )

    scale_x = (
        float(target_w)
        / float(W)
    )

    if abs(
        scale_y
        - scale_x
    ) > 1e-9:
        raise RuntimeError(
            "Non-square scale encountered"
        )

    actual_scale = (
        0.5
        * (
            scale_y
            + scale_x
        )
    )

    actual_gsd = (
        NATIVE_GSD_M
        / actual_scale
    )

    return (
        {
            "optical": optical,
            "dsm": dsm,
            "full_gt": full_gt,
            "noboundary_gt": nb_gt,
        },
        actual_scale,
        actual_gsd,
    )


# ============================================================
# MODEL
# ============================================================

def make_config():
    config = copy.deepcopy(
        CONFIGS[
            "R50-ViT-B_16"
        ]
    )

    config.n_classes = 6
    config.n_skip = 3

    config.patches.grid = (
        PATCH // 16,
        PATCH // 16,
    )

    return config


def build_model(
    model_name,
    checkpoint_path,
):
    config = make_config()

    if model_name == "PP10k":
        net = VisionTransformerMultiBandVariant(
            config,
            img_size=PATCH,
            num_classes=N_CLASSES,
            router_mode="modality_static",
        )

    elif model_name == "PH4k":
        net = VisionTransformerPhysicalDSM(
            config,
            img_size=PATCH,
            num_classes=N_CLASSES,
            router_mode="modality_static",
        )

    else:
        raise ValueError(
            model_name
        )

    if not checkpoint_path.is_file():
        raise FileNotFoundError(
            checkpoint_path
        )

    state = torch.load(
        checkpoint_path,
        map_location="cpu",
    )

    missing, unexpected = (
        net.load_state_dict(
            state["model"],
            strict=True,
        )
    )

    if (
        len(missing) != 0
        or len(unexpected) != 0
    ):
        raise RuntimeError(
            f"State mismatch {model_name}: "
            f"missing={missing}, "
            f"unexpected={unexpected}"
        )

    net = (
        net
        .to(DEVICE)
        .eval()
    )

    expected_metrics = state[
        "metrics"
    ]

    print(
        f"[PASS] loaded {model_name} | "
        f"step={state['global_step']} | "
        f"epoch={state['epoch']}"
    )

    return (
        net,
        expected_metrics,
        int(
            state[
                "global_step"
            ]
        ),
    )


# ============================================================
# FORMAL SLIDING-WINDOW INFERENCE
# ============================================================

def make_positions(length):
    positions = list(
        range(
            0,
            length - PATCH + 1,
            TEST_STRIDE,
        )
    )

    last = (
        length
        - PATCH
    )

    if positions[-1] != last:
        positions.append(
            last
        )

    return positions


def infer_tile(
    net,
    model_name,
    optical,
    dsm,
    physical_scale,
):
    H, W = optical.shape[:2]

    ys = make_positions(
        H
    )

    xs = make_positions(
        W
    )

    coords = [
        (
            y,
            x,
        )
        for y in ys
        for x in xs
    ]

    score = np.zeros(
        (
            N_CLASSES,
            H,
            W,
        ),
        dtype=np.float32,
    )

    with torch.inference_mode():

        for start in range(
            0,
            len(coords),
            INFER_BATCH,
        ):
            batch_coords = coords[
                start:
                start + INFER_BATCH
            ]

            op = np.stack(
                [
                    optical[
                        y:y+PATCH,
                        x:x+PATCH,
                        :
                    ].transpose(
                        2,
                        0,
                        1,
                    )
                    for y, x
                    in batch_coords
                ],
                axis=0,
            )

            ds = np.stack(
                [
                    dsm[
                        y:y+PATCH,
                        x:x+PATCH
                    ]
                    for y, x
                    in batch_coords
                ],
                axis=0,
            )

            op = torch.from_numpy(
                np.ascontiguousarray(
                    op
                )
            ).to(
                DEVICE,
                non_blocking=True,
            )

            ds = torch.from_numpy(
                np.ascontiguousarray(
                    ds
                )
            ).to(
                DEVICE,
                non_blocking=True,
            )

            # E51-B physical DSM must know the actual
            # per-sample GSD scale.
            if model_name == "PH4k":
                # V2 SCALE-BLIND CONTROL:
                # input GSD changes, but PH is always told s=1.
                net.set_sample_scales(
                    [
                        1.0
                    ]
                    * len(
                        batch_coords
                    )
                )

            logits = net(
                op,
                ds,
            )

            logits = (
                logits
                .detach()
                .cpu()
                .numpy()
            )

            for output, (
                y,
                x,
            ) in zip(
                logits,
                batch_coords,
            ):
                score[
                    :,
                    y:y+PATCH,
                    x:x+PATCH,
                ] += output

            del (
                op,
                ds,
                logits,
            )

    return np.argmax(
        score,
        axis=0,
    ).astype(
        np.uint8
    )


# ============================================================
# METRICS
# ============================================================

def update_cm(
    cm,
    gt,
    pred,
):
    valid = (
        (gt != IGNORE_INDEX)
        & (gt < N_CLASSES)
    )

    g = gt[
        valid
    ].astype(
        np.int64
    )

    p = pred[
        valid
    ].astype(
        np.int64
    )

    index = (
        N_CLASSES * g
        + p
    )

    cm += np.bincount(
        index,
        minlength=(
            N_CLASSES
            * N_CLASSES
        ),
    ).reshape(
        N_CLASSES,
        N_CLASSES,
    )


def metrics_from_cm(cm):
    x = cm.astype(
        np.float64
    )

    tp = np.diag(
        x
    )

    row = x.sum(
        axis=1
    )

    col = x.sum(
        axis=0
    )

    fp = (
        col - tp
    )

    fn = (
        row - tp
    )

    total = x.sum()

    oa = (
        tp.sum()
        / total
        if total > 0
        else np.nan
    )

    f1 = np.divide(
        2 * tp,
        (
            2 * tp
            + fp
            + fn
        ),
        out=np.zeros_like(
            tp
        ),
        where=(
            2 * tp
            + fp
            + fn
        ) > 0,
    )

    iou = np.divide(
        tp,
        (
            tp
            + fp
            + fn
        ),
        out=np.zeros_like(
            tp
        ),
        where=(
            tp
            + fp
            + fn
        ) > 0,
    )

    return {
        "OA":
            float(oa),

        "mF1_fg5":
            float(
                np.mean(
                    f1[:5]
                )
            ),

        "mIoU_fg5":
            float(
                np.mean(
                    iou[:5]
                )
            ),

        "mF1_all6":
            float(
                np.mean(
                    f1
                )
            ),

        "mIoU_all6":
            float(
                np.mean(
                    iou
                )
            ),

        "per_class_f1":
            f1.tolist(),

        "per_class_iou":
            iou.tolist(),
    }


# ============================================================
# ONE MODEL / ONE GSD
# ============================================================

def evaluate_one(
    net,
    model_name,
    target_gsd,
):
    cm_full = np.zeros(
        (
            N_CLASSES,
            N_CLASSES,
        ),
        dtype=np.int64,
    )

    cm_nb = np.zeros(
        (
            N_CLASSES,
            N_CLASSES,
        ),
        dtype=np.int64,
    )

    actual_scales = []
    actual_gsds = []

    start_time = time.time()

    for tile_index, tile_id in enumerate(
        TEST_IDS,
        start=1,
    ):
        print(
            f"  [{tile_index}/{len(TEST_IDS)}] "
            f"{model_name} "
            f"GSD={target_gsd*100:.0f}cm "
            f"tile={tile_id}",
            flush=True,
        )

        native = load_test_tile(
            tile_id
        )

        (
            data,
            actual_scale,
            actual_gsd,
        ) = resample_tile_to_gsd(
            native,
            target_gsd,
        )

        actual_scales.append(
            actual_scale
        )

        actual_gsds.append(
            actual_gsd
        )

        print(
            "      grid:",
            native["dsm"].shape,
            "->",
            data["dsm"].shape,
            "| scale=",
            f"{actual_scale:.9f}",
            "| actual_gsd=",
            f"{actual_gsd:.9f}",
            flush=True,
        )

        pred = infer_tile(
            net,
            model_name,
            data["optical"],
            data["dsm"],
            actual_scale,
        )

        update_cm(
            cm_full,
            data["full_gt"],
            pred,
        )

        update_cm(
            cm_nb,
            data["noboundary_gt"],
            pred,
        )

        del (
            native,
            data,
            pred,
        )

    elapsed = (
        time.time()
        - start_time
    )

    return {
        "full":
            metrics_from_cm(
                cm_full
            ),

        "noboundary":
            metrics_from_cm(
                cm_nb
            ),

        "cm_full":
            cm_full,

        "cm_noboundary":
            cm_nb,

        "seconds":
            elapsed,

        "actual_scale":
            float(
                np.mean(
                    actual_scales
                )
            ),

        "actual_gsd_m":
            float(
                np.mean(
                    actual_gsds
                )
            ),
    }


# ============================================================
# NATIVE REPRODUCTION GATE
# ============================================================

def native_gate(
    model_name,
    result,
    expected,
):
    print()
    print(
        "=" * 100
    )
    print(
        f"NATIVE 5CM GATE: {model_name}"
    )
    print(
        "=" * 100
    )

    keys = [
        "OA",
        "mF1_fg5",
        "mIoU_fg5",
        "mF1_all6",
        "mIoU_all6",
    ]

    max_diff = 0.0

    for split in (
        "full",
        "noboundary",
    ):
        print(
            split.upper()
        )

        for key in keys:
            got = float(
                result[
                    split
                ][
                    key
                ]
            )

            exp = float(
                expected[
                    split
                ][
                    key
                ]
            )

            diff = abs(
                got - exp
            )

            max_diff = max(
                max_diff,
                diff,
            )

            print(
                f"  {key:12s} "
                f"expected={exp:.12f} "
                f"got={got:.12f} "
                f"diff={diff:.3e}"
            )

    # Same model, data, sliding-window geometry and score
    # accumulation should reproduce extremely closely.
    if max_diff > 1e-7:
        raise RuntimeError(
            f"NATIVE GATE FAIL for {model_name}: "
            f"max_diff={max_diff}"
        )

    print(
        f"[PASS] {model_name} native 5cm "
        f"reproduction | max_diff={max_diff:.3e}"
    )


# ============================================================
# OUTPUT
# ============================================================

def flatten_row(
    model_name,
    checkpoint_step,
    target_gsd,
    result,
):
    return {
        "model":
            model_name,

        "checkpoint_step":
            checkpoint_step,

        "target_gsd_cm":
            target_gsd
            * 100.0,

        "requested_gsd_m":
            target_gsd,

        "actual_gsd_m":
            result[
                "actual_gsd_m"
            ],

        "physical_scale":
            result[
                "actual_scale"
            ],

        "full_OA":
            result[
                "full"
            ][
                "OA"
            ],

        "full_mF1_fg5":
            result[
                "full"
            ][
                "mF1_fg5"
            ],

        "full_mIoU_fg5":
            result[
                "full"
            ][
                "mIoU_fg5"
            ],

        "nb_OA":
            result[
                "noboundary"
            ][
                "OA"
            ],

        "nb_mF1_fg5":
            result[
                "noboundary"
            ][
                "mF1_fg5"
            ],

        "nb_mIoU_fg5":
            result[
                "noboundary"
            ][
                "mIoU_fg5"
            ],

        "seconds":
            result[
                "seconds"
            ],
    }


def save_csv(
    path,
    rows,
):
    if not rows:
        return

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(
                rows[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(
            rows
        )


# ============================================================
# MAIN
# ============================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--native-only",
    action="store_true",
)

args = parser.parse_args()


print(
    "=" * 100
)
print(
    "E51-B V2 SCALE-BLIND ROBUSTNESS"
)
print(
    "=" * 100
)

print(
    "PP checkpoint:",
    PP_CKPT,
)

print(
    "PH checkpoint:",
    PH_CKPT,
)

print(
    "native GSD:",
    NATIVE_GSD_M,
)

print(
    "target GSDs:",
    (
        [NATIVE_GSD_M]
        if args.native_only
        else TARGET_GSDS_M
    ),
)

print(
    "Important:"
    " full tiles and GT are jointly resampled to target GSD;"
    " PH receives actual grid scale."
)


(
    pp_net,
    pp_expected,
    pp_step,
) = build_model(
    "PP10k",
    PP_CKPT,
)

(
    ph_net,
    ph_expected,
    ph_step,
) = build_model(
    "PH4k",
    PH_CKPT,
)


rows = []
raw_summary = {}


target_gsds = (
    [NATIVE_GSD_M]
    if args.native_only
    else TARGET_GSDS_M
)


for target_gsd in target_gsds:

    print()
    print(
        "#" * 100
    )
    print(
        "TARGET GSD:",
        f"{target_gsd*100:.0f} cm"
    )
    print(
        "#" * 100
    )

    for (
        model_name,
        net,
        expected,
        checkpoint_step,
    ) in [
        (
            "PP10k",
            pp_net,
            pp_expected,
            pp_step,
        ),
        (
            "PH4k",
            ph_net,
            ph_expected,
            ph_step,
        ),
    ]:

        result = evaluate_one(
            net,
            model_name,
            target_gsd,
        )

        nb = result[
            "noboundary"
        ]

        full = result[
            "full"
        ]

        print(
            f"{model_name} "
            f"{target_gsd*100:.0f}cm | "
            f"FULL mIoU={100*full['mIoU_fg5']:.4f} | "
            f"NB OA={100*nb['OA']:.4f} "
            f"mF1={100*nb['mF1_fg5']:.4f} "
            f"mIoU={100*nb['mIoU_fg5']:.4f} | "
            f"{result['seconds']:.1f}s",
            flush=True,
        )

        if abs(
            target_gsd
            - NATIVE_GSD_M
        ) < 1e-12:
            native_gate(
                model_name,
                result,
                expected,
            )

        row = flatten_row(
            model_name,
            checkpoint_step,
            target_gsd,
            result,
        )

        rows.append(
            row
        )

        raw_summary[
            f"{model_name}_"
            f"{target_gsd:.2f}"
        ] = {
            "checkpoint_step":
                checkpoint_step,

            "requested_gsd_m":
                target_gsd,

            "actual_gsd_m":
                result[
                    "actual_gsd_m"
                ],

            "physical_scale":
                result[
                    "actual_scale"
                ],

            "full":
                result[
                    "full"
                ],

            "noboundary":
                result[
                    "noboundary"
                ],

            "seconds":
                result[
                    "seconds"
                ],
        }


metrics_path = (
    OUT
    / (
        "native_gate_metrics.csv"
        if args.native_only
        else "metrics.csv"
    )
)

save_csv(
    metrics_path,
    rows,
)


if args.native_only:

    with open(
        OUT
        / "native_gate_summary.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            raw_summary,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print(
        "=" * 100
    )
    print(
        "ALL NATIVE 5CM GATES PASS"
    )
    print(
        "OUTPUT:",
        OUT
    )
    print(
        "=" * 100
    )

    raise SystemExit(
        0
    )


# ============================================================
# RELATIVE ROBUSTNESS
# ============================================================

baseline = {}

for row in rows:
    if abs(
        row["requested_gsd_m"]
        - NATIVE_GSD_M
    ) < 1e-12:
        baseline[
            row["model"]
        ] = row


relative_rows = []

for row in rows:

    b = baseline[
        row["model"]
    ]

    nb_drop_pp = (
        b["nb_mIoU_fg5"]
        - row["nb_mIoU_fg5"]
    ) * 100.0

    full_drop_pp = (
        b["full_mIoU_fg5"]
        - row["full_mIoU_fg5"]
    ) * 100.0

    relative_rows.append({
        "model":
            row[
                "model"
            ],

        "checkpoint_step":
            row[
                "checkpoint_step"
            ],

        "target_gsd_cm":
            row[
                "target_gsd_cm"
            ],

        "physical_scale":
            row[
                "physical_scale"
            ],

        "nb_mIoU":
            row[
                "nb_mIoU_fg5"
            ],

        "nb_mIoU_drop_pp":
            nb_drop_pp,

        "full_mIoU":
            row[
                "full_mIoU_fg5"
            ],

        "full_mIoU_drop_pp":
            full_drop_pp,
    })


save_csv(
    OUT
    / "relative_drop.csv",
    relative_rows,
)


# Pair PP and PH drop curves.
comparison_rows = []

for target_gsd in TARGET_GSDS_M:

    pp = next(
        r
        for r in relative_rows
        if (
            r["model"] == "PP10k"
            and abs(
                r["target_gsd_cm"]
                - target_gsd * 100.0
            ) < 1e-9
        )
    )

    ph = next(
        r
        for r in relative_rows
        if (
            r["model"] == "PH4k"
            and abs(
                r["target_gsd_cm"]
                - target_gsd * 100.0
            ) < 1e-9
        )
    )

    # Positive:
    # PH loses fewer mIoU percentage points than PP.
    advantage = (
        pp[
            "nb_mIoU_drop_pp"
        ]
        - ph[
            "nb_mIoU_drop_pp"
        ]
    )

    comparison_rows.append({
        "target_gsd_cm":
            target_gsd
            * 100.0,

        "PP10k_nb_mIoU":
            pp[
                "nb_mIoU"
            ],

        "PH4k_nb_mIoU":
            ph[
                "nb_mIoU"
            ],

        "PP10k_drop_pp":
            pp[
                "nb_mIoU_drop_pp"
            ],

        "PH4k_drop_pp":
            ph[
                "nb_mIoU_drop_pp"
            ],

        "PH_robustness_advantage_pp":
            advantage,
    })


save_csv(
    OUT
    / "pp_vs_ph_relative_robustness.csv",
    comparison_rows,
)


with open(
    OUT
    / "summary.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(
        {
            "native_gsd_m":
                NATIVE_GSD_M,

            "target_gsds_m":
                TARGET_GSDS_M,

            "comparison_note":
                (
                    "Preliminary robustness screen. "
                    "PP uses its 10k best checkpoint; "
                    "PH uses its 4k best checkpoint. "
                    "Interpret relative degradation from "
                    "each model's own native 5cm baseline, "
                    "not absolute PP-vs-PH accuracy."
                ),

            "results":
                raw_summary,

            "relative_comparison":
                comparison_rows,
        },
        f,
        indent=2,
        ensure_ascii=False,
    )


print()
print(
    "=" * 100
)
print(
    "RELATIVE ROBUSTNESS SUMMARY"
)
print(
    "=" * 100
)

for row in comparison_rows:
    print(
        f"{row['target_gsd_cm']:>4.0f}cm | "
        f"PP drop={row['PP10k_drop_pp']:+.4f} pp | "
        f"PH drop={row['PH4k_drop_pp']:+.4f} pp | "
        f"PH advantage="
        f"{row['PH_robustness_advantage_pp']:+.4f} pp"
    )

print()
print(
    "OUTPUT:",
    OUT
)

print(
    "E51-B V2 SCALE-BLIND ROBUSTNESS COMPLETE"
)
