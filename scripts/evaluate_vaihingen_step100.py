import os
import sys
import json
import time
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")

DATA_ROOT = Path(
    "/home/jovyan/zzx/projects_zys/raw_extract/Vaihingen"
)

# 按历史 FTransUNet/毕业代码实际路径
NOBOUNDARY_ROOT = Path(
    "/home/jovyan/zzx/projects_zys/ISPRS_dataset/"
    "Vaihingen/gts_eroded_for_participants"
)

PRETRAIN = Path(
    "/home/jovyan/zzx/paper_rebuild/08_assets/pretrained/"
    "ftransunet/R50+ViT-B_16.npz"
)

CHECKPOINT = (
    ROOT
    / "runs"
    / "Vaihingen_100step_seed42_20260826"
    / "checkpoint_step100.pth"
)

OUT_DIR = (
    ROOT
    / "runs"
    / "Vaihingen_100step_seed42_20260826"
    / "evaluation_step100"
)

OUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT))

import numpy as np
import torch
from skimage import io

from model.vitcross_seg_modeling_freqfusion import (
    VisionTransformerFreqFusion,
    CONFIGS,
)

DEVICE = torch.device("cuda:0")

TEST_IDS = ["5", "15", "21", "30"]

PATCH = 256
STRIDE = 32
INFER_BATCH = 16
N_CLASSES = 6

CLASS_NAMES = [
    "Impervious",
    "Building",
    "LowVegetation",
    "Tree",
    "Car",
    "Clutter",
]

PALETTE = {
    (255, 255, 255): 0,
    (0, 0, 255): 1,
    (0, 255, 255): 2,
    (0, 255, 0): 3,
    (255, 255, 0): 4,
    (255, 0, 0): 5,
}

BLACK = (0, 0, 0)
IGNORE_INDEX = 255


def convert_full_gt(rgb):
    out = np.full(rgb.shape[:2], IGNORE_INDEX, dtype=np.uint8)

    matched = np.zeros(rgb.shape[:2], dtype=bool)

    for color, idx in PALETTE.items():
        mask = np.all(
            rgb[..., :3] == np.asarray(color, dtype=rgb.dtype),
            axis=-1,
        )
        out[mask] = idx
        matched |= mask

    if not matched.all():
        unknown = int((~matched).sum())
        raise RuntimeError(
            f"FullGT contains {unknown} pixels outside 6-class palette"
        )

    return out


def convert_noboundary_gt(rgb):
    # black = undefined / ignored boundary pixel
    out = np.full(rgb.shape[:2], IGNORE_INDEX, dtype=np.uint8)

    recognized = np.zeros(rgb.shape[:2], dtype=bool)

    for color, idx in PALETTE.items():
        mask = np.all(
            rgb[..., :3] == np.asarray(color, dtype=rgb.dtype),
            axis=-1,
        )
        out[mask] = idx
        recognized |= mask

    black_mask = np.all(
        rgb[..., :3] == np.asarray(BLACK, dtype=rgb.dtype),
        axis=-1,
    )

    recognized |= black_mask

    if not recognized.all():
        unknown = int((~recognized).sum())
        raise RuntimeError(
            f"noBoundary GT contains {unknown} unknown-color pixels"
        )

    return out


def make_positions(length, patch, stride):
    if length < patch:
        raise RuntimeError(
            f"Image dimension {length} smaller than patch {patch}"
        )

    positions = list(
        range(0, length - patch + 1, stride)
    )

    last = length - patch

    if positions[-1] != last:
        positions.append(last)

    return positions


def update_confusion(cm, gt, pred):
    valid = (
        (gt != IGNORE_INDEX)
        & (gt >= 0)
        & (gt < N_CLASSES)
    )

    gt_valid = gt[valid].astype(np.int64)
    pred_valid = pred[valid].astype(np.int64)

    idx = N_CLASSES * gt_valid + pred_valid

    hist = np.bincount(
        idx,
        minlength=N_CLASSES * N_CLASSES,
    ).reshape(N_CLASSES, N_CLASSES)

    cm += hist


def calculate_metrics(cm):
    cm = cm.astype(np.float64)

    tp = np.diag(cm)

    gt_count = cm.sum(axis=1)
    pred_count = cm.sum(axis=0)

    fp = pred_count - tp
    fn = gt_count - tp

    total = cm.sum()

    oa = (
        tp.sum() / total
        if total > 0
        else np.nan
    )

    precision = np.divide(
        tp,
        tp + fp,
        out=np.full_like(tp, np.nan),
        where=(tp + fp) > 0,
    )

    recall = np.divide(
        tp,
        tp + fn,
        out=np.full_like(tp, np.nan),
        where=(tp + fn) > 0,
    )

    f1 = np.divide(
        2 * tp,
        2 * tp + fp + fn,
        out=np.full_like(tp, np.nan),
        where=(2 * tp + fp + fn) > 0,
    )

    iou = np.divide(
        tp,
        tp + fp + fn,
        out=np.full_like(tp, np.nan),
        where=(tp + fp + fn) > 0,
    )

    result = {
        "OA": float(oa),
        "mF1_fg5": float(np.nanmean(f1[:5])),
        "mIoU_fg5": float(np.nanmean(iou[:5])),
        "mF1_all6": float(np.nanmean(f1)),
        "mIoU_all6": float(np.nanmean(iou)),
        "per_class": {},
    }

    for i, name in enumerate(CLASS_NAMES):
        result["per_class"][name] = {
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1": float(f1[i]),
            "iou": float(iou[i]),
            "support": int(gt_count[i]),
        }

    return result


def infer_tile(net, optical, dsm, tile_id):
    H, W = optical.shape[:2]

    ys = make_positions(H, PATCH, STRIDE)
    xs = make_positions(W, PATCH, STRIDE)

    coords = [
        (y, x)
        for y in ys
        for x in xs
    ]

    print(
        f"tile {tile_id}: "
        f"shape={H}x{W}, "
        f"windows={len(coords)}, "
        f"infer_batch={INFER_BATCH}"
    )

    # 与历史代码一致：重叠区域累加 logits
    score = np.zeros(
        (N_CLASSES, H, W),
        dtype=np.float32,
    )

    with torch.no_grad():
        for start in range(
            0,
            len(coords),
            INFER_BATCH,
        ):
            batch_coords = coords[
                start:start + INFER_BATCH
            ]

            optical_batch = np.stack(
                [
                    optical[
                        y:y+PATCH,
                        x:x+PATCH,
                        :
                    ].transpose(2, 0, 1)
                    for y, x in batch_coords
                ],
                axis=0,
            )

            dsm_batch = np.stack(
                [
                    dsm[
                        y:y+PATCH,
                        x:x+PATCH
                    ]
                    for y, x in batch_coords
                ],
                axis=0,
            )

            optical_tensor = torch.from_numpy(
                np.ascontiguousarray(optical_batch)
            ).to(
                DEVICE,
                non_blocking=True,
            )

            dsm_tensor = torch.from_numpy(
                np.ascontiguousarray(dsm_batch)
            ).to(
                DEVICE,
                non_blocking=True,
            )

            logits = net(
                optical_tensor,
                dsm_tensor,
            )

            logits = (
                logits
                .detach()
                .cpu()
                .numpy()
            )

            for output, (y, x) in zip(
                logits,
                batch_coords,
            ):
                score[
                    :,
                    y:y+PATCH,
                    x:x+PATCH,
                ] += output

            if (
                start == 0
                or start + INFER_BATCH >= len(coords)
                or (start // INFER_BATCH) % 50 == 0
            ):
                done = min(
                    start + INFER_BATCH,
                    len(coords),
                )

                print(
                    f"  {done}/{len(coords)} windows"
                )

    pred = np.argmax(
        score,
        axis=0,
    ).astype(np.uint8)

    return pred


print("=" * 100)
print("VAIHINGEN STEP100 EVALUATOR")
print("=" * 100)

print("checkpoint :", CHECKPOINT)
print("FullGT     :", DATA_ROOT / "gts_for_participants")
print("noBoundary :", NOBOUNDARY_ROOT)
print("test IDs   :", TEST_IDS)
print("patch      :", PATCH)
print("stride     :", STRIDE)
print("infer batch:", INFER_BATCH)

if not CHECKPOINT.is_file():
    raise FileNotFoundError(CHECKPOINT)

# ------------------------------------------------------------------
# PRELOAD TEST4 TO RAM
# ------------------------------------------------------------------

print("\nPRELOAD TEST DATA TO RAM")

test_data = {}

for tile_id in TEST_IDS:
    optical_path = (
        DATA_ROOT
        / "top"
        / f"top_mosaic_09cm_area{tile_id}.tif"
    )

    dsm_path = (
        DATA_ROOT
        / "dsm"
        / f"dsm_09cm_matching_area{tile_id}.tif"
    )

    full_gt_path = (
        DATA_ROOT
        / "gts_for_participants"
        / f"top_mosaic_09cm_area{tile_id}.tif"
    )

    noboundary_path = (
        NOBOUNDARY_ROOT
        / f"top_mosaic_09cm_area{tile_id}_noBoundary.tif"
    )

    for p in [
        optical_path,
        dsm_path,
        full_gt_path,
        noboundary_path,
    ]:
        if not p.is_file():
            raise FileNotFoundError(p)

    optical = (
        io.imread(str(optical_path))[..., :3]
        .astype(np.float32)
        / 255.0
    )

    dsm = io.imread(
        str(dsm_path)
    ).astype(np.float32)

    dmin = float(dsm.min())
    dmax = float(dsm.max())

    if dmax <= dmin:
        raise RuntimeError(
            f"DSM zero range: tile {tile_id}"
        )

    dsm = (
        (dsm - dmin)
        / (dmax - dmin)
    )

    full_gt = convert_full_gt(
        io.imread(str(full_gt_path))
    )

    noboundary_gt = convert_noboundary_gt(
        io.imread(str(noboundary_path))
    )

    if not (
        optical.shape[:2]
        == dsm.shape
        == full_gt.shape
        == noboundary_gt.shape
    ):
        raise RuntimeError(
            f"Shape mismatch at tile {tile_id}: "
            f"{optical.shape}, "
            f"{dsm.shape}, "
            f"{full_gt.shape}, "
            f"{noboundary_gt.shape}"
        )

    ignore_pixels = int(
        (noboundary_gt == IGNORE_INDEX).sum()
    )

    print(
        f" tile {tile_id}: "
        f"{optical.shape[:2]}, "
        f"DSM_raw=({dmin:.3f},{dmax:.3f}), "
        f"noBoundary_ignore={ignore_pixels}"
    )

    test_data[tile_id] = {
        "optical": optical,
        "dsm": dsm,
        "full_gt": full_gt,
        "noboundary_gt": noboundary_gt,
    }

print("[PASS] Test4 preloaded to RAM")

# ------------------------------------------------------------------
# MODEL
# ------------------------------------------------------------------

config = CONFIGS["R50-ViT-B_16"]
config.n_classes = 6
config.n_skip = 3
config.patches.grid = (16, 16)

net = VisionTransformerFreqFusion(
    config,
    img_size=256,
    num_classes=6,
).to(DEVICE)

checkpoint = torch.load(
    CHECKPOINT,
    map_location="cpu",
)

if "model" in checkpoint:
    state_dict = checkpoint["model"]
else:
    state_dict = checkpoint

net.load_state_dict(
    state_dict,
    strict=True,
)

net.eval()

print("[PASS] checkpoint loaded")

# Verify SGOR
sgor_modules = [
    n
    for n, _ in net.named_modules()
    if "dysampler" in n.lower()
]

print("SGOR modules:", len(sgor_modules))

if not sgor_modules:
    raise RuntimeError("SGOR absent")

# ------------------------------------------------------------------
# INFERENCE
# ------------------------------------------------------------------

cm_full = np.zeros(
    (N_CLASSES, N_CLASSES),
    dtype=np.int64,
)

cm_noboundary = np.zeros(
    (N_CLASSES, N_CLASSES),
    dtype=np.int64,
)

start_time = time.time()

for tile_id in TEST_IDS:
    data = test_data[tile_id]

    tile_start = time.time()

    pred = infer_tile(
        net,
        data["optical"],
        data["dsm"],
        tile_id,
    )

    update_confusion(
        cm_full,
        data["full_gt"],
        pred,
    )

    update_confusion(
        cm_noboundary,
        data["noboundary_gt"],
        pred,
    )

    np.save(
        OUT_DIR / f"prediction_area{tile_id}.npy",
        pred,
    )

    print(
        f"[PASS] tile {tile_id} complete, "
        f"{time.time() - tile_start:.2f}s"
    )

total_time = time.time() - start_time

# ------------------------------------------------------------------
# METRICS
# ------------------------------------------------------------------

metrics_full = calculate_metrics(
    cm_full
)

metrics_noboundary = calculate_metrics(
    cm_noboundary
)

result = {
    "checkpoint": str(CHECKPOINT),
    "test_ids": TEST_IDS,
    "patch": PATCH,
    "stride": STRIDE,
    "infer_batch": INFER_BATCH,
    "total_inference_seconds": total_time,
    "FullGT": metrics_full,
    "noBoundary": metrics_noboundary,
}

with open(
    OUT_DIR / "metrics.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(
        result,
        f,
        indent=2,
        ensure_ascii=False,
    )

np.savetxt(
    OUT_DIR / "confusion_fullgt.csv",
    cm_full,
    fmt="%d",
    delimiter=",",
)

np.savetxt(
    OUT_DIR / "confusion_noboundary.csv",
    cm_noboundary,
    fmt="%d",
    delimiter=",",
)


def print_metrics(title, cm, m):
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)

    print("Confusion matrix:")
    print(cm)

    print(
        f"\nOA         : {m['OA'] * 100:.4f}%"
    )

    print(
        f"mF1_fg5    : {m['mF1_fg5'] * 100:.4f}%"
    )

    print(
        f"mIoU_fg5   : {m['mIoU_fg5'] * 100:.4f}%"
    )

    print(
        f"mF1_all6   : {m['mF1_all6'] * 100:.4f}%"
    )

    print(
        f"mIoU_all6  : {m['mIoU_all6'] * 100:.4f}%"
    )

    print("\nPer-class:")

    for name in CLASS_NAMES:
        row = m["per_class"][name]

        print(
            f"  {name:14s} "
            f"P={row['precision'] * 100:8.4f}% "
            f"R={row['recall'] * 100:8.4f}% "
            f"F1={row['f1'] * 100:8.4f}% "
            f"IoU={row['iou'] * 100:8.4f}% "
            f"N={row['support']}"
        )


print_metrics(
    "FULL GT",
    cm_full,
    metrics_full,
)

print_metrics(
    "NOBOUNDARY GT",
    cm_noboundary,
    metrics_noboundary,
)

print("\n" + "=" * 100)
print("EVALUATION PASS")
print("total seconds :", total_time)
print("output dir    :", OUT_DIR)
print("=" * 100)
