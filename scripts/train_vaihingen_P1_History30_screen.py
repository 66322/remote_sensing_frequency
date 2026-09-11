import os
import sys
import csv
import json
import time
import random
import argparse
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

# Strict deterministic paired diagnostic.
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
DATA_ROOT = Path("/home/jovyan/zzx/projects_zys/raw_extract/Vaihingen")
NOBOUNDARY_ROOT = Path(
    "/home/jovyan/zzx/projects_zys/ISPRS_dataset/"
    "Vaihingen/gts_eroded_for_participants"
)
PRETRAIN = Path(
    "/home/jovyan/zzx/paper_rebuild/08_assets/pretrained/"
    "ftransunet/R50+ViT-B_16.npz"
)

sys.path.insert(0, str(ROOT))

import numpy as np
import torch
import torch.nn.functional as F
from skimage import io

from model.vitcross_seg_modeling_freqfusion import (
    CONFIGS,
)

from model.vitcross_seg_modeling_prefusion_freq_detpair import (
    VisionTransformerPreFusionFreq,
)

# ============================================================
# Frozen reproduction protocol
# ============================================================

SEED = 42

TRAIN_IDS = [
    "1", "3", "7", "11", "13", "17",
    "23", "26", "28", "32", "34", "37",
]

TEST_IDS = ["5", "15", "21", "30"]

PATCH = 512

# ------------------------------------------------------------
# Persistent Hard Region Audit
# Observation only:
# - does NOT alter the training sampler
# - does NOT use random numbers
# - fixed 512x512 windows, 50% overlap
# ------------------------------------------------------------
HISTORY_AUDIT_STRIDE = 256
HISTORY_TOP_FRACTION = 0.20

# ============================================================
# Online History Sampling
# ============================================================

# Fraction of all sampled crops redirected to history.
HISTORY_PROB = 0.30

# Rare/Object-aware settings retained from the validated
# Rare30 screening experiment.
RARE_PROB = 0.30
RARE_CLASSES = (2, 3, 4)
RARE_WEIGHTS = (0.25, 0.25, 0.50)

RARE_CACHE_MAX_POINTS = 100000
RARE_COORD_CACHE = {}

# For the hybrid experiment after history becomes available.
HYBRID_RARE_PROB = 0.15
HYBRID_HISTORY_PROB = 0.15

# Online state.
ACTIVE_HISTORY_POOL = []
ONLINE_HISTORY_STATS = {}
ONLINE_HISTORY_PROCESSED_STEPS = set()
ONLINE_HISTORY_LOAD_ATTEMPTED = False

SAMPLER_COUNTS = {
    "random": 0,
    "rare": 0,
    "history": 0,
}

# Keep the same target budget as Rare30:
# 20% of 780 fixed regions = 156 history candidates.
ONLINE_HISTORY_POOL_FRACTION = 0.20
TRAIN_BATCH = 4

# One optimizer update accumulates four physical batches:
# 4 images/micro-batch x 4 = 16 sampled crops/update.
ACCUM_STEPS = 4
EFFECTIVE_BATCH = TRAIN_BATCH * ACCUM_STEPS

# Keep the existing bookkeeping convention of
# 1000 optimizer updates per pseudo-epoch.
EPOCHS = 160
STEPS_PER_EPOCH = 1000
TOTAL_STEPS = EPOCHS * STEPS_PER_EPOCH

EVAL_INTERVAL = 2000
TEST_STRIDE = 64

# Inference does not affect the trained parameters.
# 8 is deliberately conservative for 512x512 F3.
INFER_BATCH = 8

# FreqFusion-like single-GPU adapted recipe.
BASE_LR = 6e-5
NEW_MODULE_LR_MULT = 10.0
WEIGHT_DECAY = 0.01

WARMUP_STEPS = 1500
WARMUP_RATIO = 1e-6

POLY_POWER = 1.0

RANDOM_SCALE_MIN = 0.5
RANDOM_SCALE_MAX = 2.0

N_CLASSES = 6
IGNORE_INDEX = 255

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

DEVICE = torch.device("cuda:0")


# ============================================================
# Utility
# ============================================================

def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True

    torch.use_deterministic_algorithms(
        True
    )


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
            == np.asarray(color, dtype=rgb.dtype),
            axis=-1,
        )
        out[mask] = idx
        matched |= mask

    if not matched.all():
        raise RuntimeError(
            f"FullGT unknown pixels: {(~matched).sum()}"
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
            == np.asarray(color, dtype=rgb.dtype),
            axis=-1,
        )
        out[mask] = idx
        recognized |= mask

    black = np.all(
        rgb[..., :3]
        == np.asarray(BLACK, dtype=rgb.dtype),
        axis=-1,
    )

    recognized |= black

    if not recognized.all():
        raise RuntimeError(
            f"noBoundary unknown pixels: {(~recognized).sum()}"
        )

    return out


def load_train_tile(tile_id):
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

    label_path = (
        DATA_ROOT
        / "gts_for_participants"
        / f"top_mosaic_09cm_area{tile_id}.tif"
    )

    for p in (
        optical_path,
        dsm_path,
        label_path,
    ):
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
            f"DSM zero range: {tile_id}"
        )

    dsm = (
        (dsm - dmin)
        / (dmax - dmin)
    )

    gt = convert_full_gt(
        io.imread(str(label_path))
    )

    if not (
        optical.shape[:2]
        == dsm.shape
        == gt.shape
    ):
        raise RuntimeError(
            f"Train shape mismatch tile {tile_id}"
        )

    return optical, dsm, gt


def load_test_tile(tile_id):
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

    full_path = (
        DATA_ROOT
        / "gts_for_participants"
        / f"top_mosaic_09cm_area{tile_id}.tif"
    )

    nb_path = (
        NOBOUNDARY_ROOT
        / f"top_mosaic_09cm_area{tile_id}_noBoundary.tif"
    )

    for p in (
        optical_path,
        dsm_path,
        full_path,
        nb_path,
    ):
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
            f"DSM zero range: {tile_id}"
        )

    dsm = (
        (dsm - dmin)
        / (dmax - dmin)
    )

    full_gt = convert_full_gt(
        io.imread(str(full_path))
    )

    nb_gt = convert_noboundary_gt(
        io.imread(str(nb_path))
    )

    if not (
        optical.shape[:2]
        == dsm.shape
        == full_gt.shape
        == nb_gt.shape
    ):
        raise RuntimeError(
            f"Test shape mismatch tile {tile_id}"
        )

    return {
        "optical": optical,
        "dsm": dsm,
        "full_gt": full_gt,
        "noboundary_gt": nb_gt,
    }


def preload_all():
    print("\n" + "=" * 100)
    print("PRELOAD TRAIN12 + TEST4 TO RAM")
    print("=" * 100)

    train_cache = {}

    start = time.time()

    for tile_id in TRAIN_IDS:
        train_cache[tile_id] = load_train_tile(
            tile_id
        )

        op, ds, gt = train_cache[tile_id]

        print(
            f"train {tile_id:>2s}: "
            f"{gt.shape}, "
            f"opt={op.dtype}, "
            f"dsm={ds.dtype}"
        )

    test_cache = {}

    for tile_id in TEST_IDS:
        test_cache[tile_id] = load_test_tile(
            tile_id
        )

        data = test_cache[tile_id]

        ignored = int(
            (
                data["noboundary_gt"]
                == IGNORE_INDEX
            ).sum()
        )

        print(
            f"test  {tile_id:>2s}: "
            f"{data['full_gt'].shape}, "
            f"ignored={ignored}"
        )

    print(
        f"[PASS] preload completed "
        f"in {time.time() - start:.2f}s"
    )

    return train_cache, test_cache


# ============================================================
# RAM-only training batch sampler
# ============================================================


def _rare_flat_indices(
    tile_id,
    gt,
    class_id,
):
    """
    Same deterministic rare-coordinate cache used by Rare30.
    """
    key = (
        str(tile_id),
        int(class_id),
    )

    cached = (
        RARE_COORD_CACHE.get(key)
    )

    if cached is not None:
        return cached

    flat = np.flatnonzero(
        gt.reshape(-1) == class_id
    )

    if (
        flat.size
        > RARE_CACHE_MAX_POINTS
    ):
        stride = max(
            1,
            int(
                np.ceil(
                    flat.size
                    / RARE_CACHE_MAX_POINTS
                )
            ),
        )

        flat = flat[
            ::stride
        ][:RARE_CACHE_MAX_POINTS]

    RARE_COORD_CACHE[key] = flat

    return flat


def _record_sampler_branch(name):
    SAMPLER_COUNTS[name] += 1

    total = sum(
        SAMPLER_COUNTS.values()
    )

    # 16 sampled crops / optimizer step.
    # Print approximately every 100 optimizer steps.
    if (
        total > 0
        and total % 1600 == 0
    ):
        print(
            "[SAMPLER-COUNTS] "
            f"total={total} | "
            f"random={SAMPLER_COUNTS['random']} | "
            f"rare={SAMPLER_COUNTS['rare']} | "
            f"history={SAMPLER_COUNTS['history']}"
        )


def _ensure_online_history_loaded(
    run_dir,
):
    """
    Restore history pool from its sidecar state after --resume.

    This contains TRAIN-set sampling information only.
    Test4 metrics are never used by the sampler.
    """
    global ONLINE_HISTORY_LOAD_ATTEMPTED
    global ACTIVE_HISTORY_POOL
    global ONLINE_HISTORY_STATS
    global ONLINE_HISTORY_PROCESSED_STEPS

    if ONLINE_HISTORY_LOAD_ATTEMPTED:
        return

    ONLINE_HISTORY_LOAD_ATTEMPTED = True

    if not args.resume:
        return

    path = (
        run_dir
        / "online_history_state.json"
    )

    if not path.is_file():
        print(
            "[ONLINE-HISTORY] "
            "resume sidecar not found; "
            "pool remains empty."
        )
        return

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        state = json.load(f)

    ACTIVE_HISTORY_POOL[:] = (
        state.get(
            "active_pool",
            [],
        )
    )

    ONLINE_HISTORY_STATS.clear()
    ONLINE_HISTORY_STATS.update(
        state.get(
            "stats",
            {},
        )
    )

    ONLINE_HISTORY_PROCESSED_STEPS.clear()
    ONLINE_HISTORY_PROCESSED_STEPS.update(
        int(x)
        for x in state.get(
            "processed_steps",
            [],
        )
    )

    counts = state.get(
        "sampler_counts",
        {},
    )

    for k in SAMPLER_COUNTS:
        SAMPLER_COUNTS[k] = int(
            counts.get(k, 0)
        )

    print(
        "[ONLINE-HISTORY] restored | "
        f"pool={len(ACTIVE_HISTORY_POOL)} | "
        f"processed="
        f"{sorted(ONLINE_HISTORY_PROCESSED_STEPS)}"
    )


def sample_train_batch(train_cache):
    """
    Stage-2 training sampler.

    Random scale convention:
        scale < 1:
            crop a larger native region and resize it to PATCH,
            therefore objects appear smaller.

        scale > 1:
            crop a smaller native region and resize it to PATCH,
            therefore objects appear larger.

    Optical / DSM:
        bilinear interpolation.

    Semantic GT:
        nearest-neighbor interpolation only.
    """

    optical_batch = []
    dsm_batch = []
    gt_batch = []

    sampled_scales = []

    _ensure_online_history_loaded(
        RUN_DIR
    )

    for _ in range(TRAIN_BATCH):
        tile_id = random.choice(TRAIN_IDS)

        optical, dsm, gt = train_cache[
            tile_id
        ]

        H, W = gt.shape

        scale = random.uniform(
            RANDOM_SCALE_MIN,
            RANDOM_SCALE_MAX,
        )

        # Example:
        # scale=0.5 -> source crop ~=1024 -> resize to512
        # scale=2.0 -> source crop ~=256  -> resize to512
        source_size = int(
            round(PATCH / scale)
        )

        source_size = max(
            1,
            min(
                source_size,
                H,
                W,
            ),
        )

        # ----------------------------------------------------
        # Online History30
        #
        # Before the first 2k audit ACTIVE_HISTORY_POOL is
        # empty, so this path is EXACTLY original P1 Random.
        #
        # After history becomes available:
        #   70% random
        #   30% history-centered
        # ----------------------------------------------------
        history_item = None

        if ACTIVE_HISTORY_POOL:
            use_history = (
                random.random()
                < HISTORY_PROB
            )

            if use_history:
                history_item = random.choice(
                    ACTIVE_HISTORY_POOL
                )

                tile_id = str(
                    history_item[
                        "tile_id"
                    ]
                )

                optical, dsm, gt = (
                    train_cache[
                        tile_id
                    ]
                )

                H, W = gt.shape

                # Recompute using the SAME sampled scale.
                source_size = int(
                    round(
                        PATCH / scale
                    )
                )

                source_size = max(
                    1,
                    min(
                        source_size,
                        H,
                        W,
                    ),
                )

        if history_item is not None:
            cy = (
                int(
                    history_item["y"]
                )
                + PATCH // 2
            )

            cx = (
                int(
                    history_item["x"]
                )
                + PATCH // 2
            )

            jitter = max(
                1,
                source_size // 4,
            )

            cy += random.randint(
                -jitter,
                jitter,
            )

            cx += random.randint(
                -jitter,
                jitter,
            )

            y = int(
                max(
                    0,
                    min(
                        H - source_size,
                        cy
                        - source_size // 2,
                    ),
                )
            )

            x = int(
                max(
                    0,
                    min(
                        W - source_size,
                        cx
                        - source_size // 2,
                    ),
                )
            )

            _record_sampler_branch(
                "history"
            )

        else:
            y = random.randint(
                0,
                H - source_size,
            )

            x = random.randint(
                0,
                W - source_size,
            )

            _record_sampler_branch(
                "random"
            )

        op = optical[
            y:y+source_size,
            x:x+source_size,
            :
        ]

        ds = dsm[
            y:y+source_size,
            x:x+source_size
        ]

        label = gt[
            y:y+source_size,
            x:x+source_size
        ]

        # Historical vertical / horizontal flipping.
        if random.random() < 0.5:
            op = op[::-1, :, :]
            ds = ds[::-1, :]
            label = label[::-1, :]

        if random.random() < 0.5:
            op = op[:, ::-1, :]
            ds = ds[:, ::-1]
            label = label[:, ::-1]

        op = np.ascontiguousarray(
            op.transpose(2, 0, 1)
        )

        ds = np.ascontiguousarray(ds)
        label = np.ascontiguousarray(label)

        # Resize each sample on CPU before stacking.
        op_t = torch.from_numpy(
            op
        ).float().unsqueeze(0)

        ds_t = torch.from_numpy(
            ds
        ).float().unsqueeze(0).unsqueeze(0)

        gt_t = torch.from_numpy(
            label.astype(np.int64)
        ).unsqueeze(0).unsqueeze(0).float()

        if source_size != PATCH:
            op_t = F.interpolate(
                op_t,
                size=(PATCH, PATCH),
                mode="bilinear",
                align_corners=False,
            )

            ds_t = F.interpolate(
                ds_t,
                size=(PATCH, PATCH),
                mode="bilinear",
                align_corners=False,
            )

            gt_t = F.interpolate(
                gt_t,
                size=(PATCH, PATCH),
                mode="nearest",
            )

        optical_batch.append(
            op_t.squeeze(0)
        )

        dsm_batch.append(
            ds_t.squeeze(0).squeeze(0)
        )

        gt_batch.append(
            gt_t.squeeze(0).squeeze(0).long()
        )

        sampled_scales.append(scale)

    optical_tensor = torch.stack(
        optical_batch,
        dim=0,
    ).to(
        DEVICE,
        non_blocking=True,
    )

    dsm_tensor = torch.stack(
        dsm_batch,
        dim=0,
    ).to(
        DEVICE,
        non_blocking=True,
    )

    gt_tensor = torch.stack(
        gt_batch,
        dim=0,
    ).to(
        DEVICE,
        non_blocking=True,
    )

    return (
        optical_tensor,
        dsm_tensor,
        gt_tensor,
        sampled_scales,
    )

# ============================================================
# Evaluation
# ============================================================

def make_positions(length):
    positions = list(
        range(
            0,
            length - PATCH + 1,
            TEST_STRIDE,
        )
    )

    last = length - PATCH

    if positions[-1] != last:
        positions.append(last)

    return positions


def infer_tile(net, optical, dsm):
    H, W = optical.shape[:2]

    ys = make_positions(H)
    xs = make_positions(W)

    coords = [
        (y, x)
        for y in ys
        for x in xs
    ]

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
                start:start+INFER_BATCH
            ]

            op = np.stack(
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

            ds = np.stack(
                [
                    dsm[
                        y:y+PATCH,
                        x:x+PATCH
                    ]
                    for y, x in batch_coords
                ],
                axis=0,
            )

            op = torch.from_numpy(
                np.ascontiguousarray(op)
            ).to(
                DEVICE,
                non_blocking=True,
            )

            ds = torch.from_numpy(
                np.ascontiguousarray(ds)
            ).to(
                DEVICE,
                non_blocking=True,
            )

            logits = net(op, ds)

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

    return np.argmax(
        score,
        axis=0,
    ).astype(np.uint8)


def update_cm(cm, gt, pred):
    valid = (
        (gt != IGNORE_INDEX)
        & (gt < N_CLASSES)
    )

    g = gt[valid].astype(np.int64)
    p = pred[valid].astype(np.int64)

    index = (
        N_CLASSES * g + p
    )

    cm += np.bincount(
        index,
        minlength=N_CLASSES*N_CLASSES,
    ).reshape(
        N_CLASSES,
        N_CLASSES,
    )


def metrics_from_cm(cm):
    x = cm.astype(np.float64)

    tp = np.diag(x)
    row = x.sum(axis=1)
    col = x.sum(axis=0)

    fp = col - tp
    fn = row - tp

    total = x.sum()

    oa = (
        tp.sum() / total
        if total > 0
        else np.nan
    )

    f1 = np.divide(
        2*tp,
        2*tp + fp + fn,
        out=np.zeros_like(tp),
        where=(2*tp + fp + fn) > 0,
    )

    iou = np.divide(
        tp,
        tp + fp + fn,
        out=np.zeros_like(tp),
        where=(tp + fp + fn) > 0,
    )

    return {
        "OA": float(oa),
        "mF1_fg5": float(
            np.mean(f1[:5])
        ),
        "mIoU_fg5": float(
            np.mean(iou[:5])
        ),
        "mF1_all6": float(
            np.mean(f1)
        ),
        "mIoU_all6": float(
            np.mean(iou)
        ),
        "per_class_f1": f1.tolist(),
        "per_class_iou": iou.tolist(),
    }


def evaluate(net, test_cache):
    net.eval()

    cm_full = np.zeros(
        (N_CLASSES, N_CLASSES),
        dtype=np.int64,
    )

    cm_nb = np.zeros(
        (N_CLASSES, N_CLASSES),
        dtype=np.int64,
    )

    start = time.time()

    for tile_id in TEST_IDS:
        data = test_cache[tile_id]

        pred = infer_tile(
            net,
            data["optical"],
            data["dsm"],
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

    result = {
        "full": metrics_from_cm(
            cm_full
        ),
        "noboundary": metrics_from_cm(
            cm_nb
        ),
        "cm_full": cm_full,
        "cm_noboundary": cm_nb,
        "seconds": (
            time.time() - start
        ),
    }

    net.train()

    return result



# ============================================================
# Persistent Hard Region Audit
# ============================================================

def history_audit_positions(length):
    """
    Deterministic fixed-window positions.

    No random calls are used so this audit must not change
    the training sampling RNG stream.
    """
    if length <= PATCH:
        return [0]

    positions = list(
        range(
            0,
            length - PATCH + 1,
            HISTORY_AUDIT_STRIDE,
        )
    )

    last = length - PATCH

    if positions[-1] != last:
        positions.append(last)

    return positions


def history_window_metrics(gt, pred):
    """
    Region difficulty.

    Main score:
        hard_score = 1 - mean IoU over fg5 classes
                     that are actually present in GT.

    Classes absent from this region's GT are NOT forced to
    contribute zero IoU.
    """
    cm = np.zeros(
        (N_CLASSES, N_CLASSES),
        dtype=np.int64,
    )

    update_cm(
        cm,
        gt,
        pred,
    )

    x = cm.astype(np.float64)

    tp = np.diag(x)
    row = x.sum(axis=1)
    col = x.sum(axis=0)

    fp = col - tp
    fn = row - tp

    denom = tp + fp + fn

    iou = np.divide(
        tp,
        denom,
        out=np.zeros_like(tp),
        where=denom > 0,
    )

    total = x.sum()

    pixel_acc = (
        float(tp.sum() / total)
        if total > 0
        else float("nan")
    )

    present_fg5 = [
        c
        for c in range(5)
        if row[c] > 0
    ]

    if present_fg5:
        miou_present = float(
            np.mean(
                iou[present_fg5]
            )
        )
        hard_score = (
            1.0 - miou_present
        )
    else:
        miou_present = float("nan")
        hard_score = float("nan")

    valid = (
        (gt != IGNORE_INDEX)
        & (gt < N_CLASSES)
    )

    valid_n = int(valid.sum())

    fractions = []

    for c in range(N_CLASSES):
        if valid_n > 0:
            fractions.append(
                float(
                    np.sum(
                        gt[valid] == c
                    )
                    / valid_n
                )
            )
        else:
            fractions.append(
                float("nan")
            )

    return {
        "hard_score": hard_score,
        "pixel_accuracy": pixel_acc,
        "error_rate": (
            1.0 - pixel_acc
            if np.isfinite(pixel_acc)
            else float("nan")
        ),
        "mIoU_present_fg5": miou_present,
        "n_present_fg5": len(
            present_fg5
        ),
        "fractions": fractions,
        "iou": iou.tolist(),
    }


def run_history_audit(
    net,
    train_cache,
    global_step,
    run_dir,
    max_windows=None,
):
    """
    Fixed-window training-set audit.

    IMPORTANT:
    This function is observational only.
    It never:
      - changes sampling weights
      - calls random / numpy.random
      - performs backward()
      - updates optimizer
      - updates BatchNorm running statistics
    """
    print(
        "\n"
        + "=" * 100
    )

    print(
        f"HISTORY AUDIT @ ITER "
        f"{global_step}"
    )

    print(
        f"window={PATCH} "
        f"stride={HISTORY_AUDIT_STRIDE}"
    )

    start_time = time.time()

    coords = []

    for tile_id in TRAIN_IDS:
        optical, dsm, gt = (
            train_cache[tile_id]
        )

        H, W = gt.shape

        ys = history_audit_positions(
            H
        )
        xs = history_audit_positions(
            W
        )

        for y in ys:
            for x in xs:
                coords.append(
                    (
                        tile_id,
                        y,
                        x,
                    )
                )

    total_possible = len(coords)

    if (
        max_windows is not None
        and len(coords) > max_windows
    ):
        coords = coords[:max_windows]

    csv_path = (
        run_dir
        / "history_audit_windows.csv"
    )

    summary_path = (
        run_dir
        / "history_audit_summary.csv"
    )

    if not csv_path.is_file():
        with open(
            csv_path,
            "w",
            newline="",
        ) as f:
            csv.writer(f).writerow([
                "step",
                "window_id",
                "tile_id",
                "y",
                "x",
                "hard_score",
                "pixel_accuracy",
                "error_rate",
                "mIoU_present_fg5",
                "n_present_fg5",
                "frac_impervious",
                "frac_building",
                "frac_lowveg",
                "frac_tree",
                "frac_car",
                "frac_clutter",
                "iou_impervious",
                "iou_building",
                "iou_lowveg",
                "iou_tree",
                "iou_car",
            ])

    if not summary_path.is_file():
        with open(
            summary_path,
            "w",
            newline="",
        ) as f:
            csv.writer(f).writerow([
                "step",
                "n_windows",
                "n_total_possible",
                "hard_mean",
                "hard_median",
                "hard_p80",
                "hard_p90",
                "top20_count",
                "seconds",
            ])

    records = []

    was_training = net.training
    net.eval()

    try:
        with torch.no_grad():
            for start in range(
                0,
                len(coords),
                INFER_BATCH,
            ):
                batch_coords = coords[
                    start:start + INFER_BATCH
                ]

                optical_batch = []
                dsm_batch = []
                gt_batch = []

                for tile_id, y, x in batch_coords:
                    optical, dsm, gt = (
                        train_cache[tile_id]
                    )

                    op = optical[
                        y:y + PATCH,
                        x:x + PATCH,
                        :
                    ]

                    ds = dsm[
                        y:y + PATCH,
                        x:x + PATCH
                    ]

                    label = gt[
                        y:y + PATCH,
                        x:x + PATCH
                    ]

                    optical_batch.append(
                        np.ascontiguousarray(
                            op.transpose(
                                2, 0, 1
                            )
                        )
                    )

                    dsm_batch.append(
                        np.ascontiguousarray(
                            ds
                        )
                    )

                    gt_batch.append(
                        np.ascontiguousarray(
                            label
                        )
                    )

                optical_tensor = (
                    torch.from_numpy(
                        np.stack(
                            optical_batch,
                            axis=0,
                        )
                    )
                    .to(
                        DEVICE,
                        non_blocking=True,
                    )
                )

                dsm_tensor = (
                    torch.from_numpy(
                        np.stack(
                            dsm_batch,
                            axis=0,
                        )
                    )
                    .to(
                        DEVICE,
                        non_blocking=True,
                    )
                )

                logits = net(
                    optical_tensor,
                    dsm_tensor,
                )

                preds = (
                    torch.argmax(
                        logits,
                        dim=1,
                    )
                    .detach()
                    .cpu()
                    .numpy()
                    .astype(np.uint8)
                )

                for (
                    tile_id,
                    y,
                    x,
                ), gt_np, pred_np in zip(
                    batch_coords,
                    gt_batch,
                    preds,
                ):
                    m = (
                        history_window_metrics(
                            gt_np,
                            pred_np,
                        )
                    )

                    window_id = (
                        f"{tile_id}"
                        f"_y{y:04d}"
                        f"_x{x:04d}"
                    )

                    records.append({
                        "step": global_step,
                        "window_id": window_id,
                        "tile_id": tile_id,
                        "y": y,
                        "x": x,
                        **m,
                    })

                del optical_tensor
                del dsm_tensor
                del logits
                del preds

    finally:
        if was_training:
            net.train()

    with open(
        csv_path,
        "a",
        newline="",
    ) as f:
        writer = csv.writer(f)

        for r in records:
            writer.writerow([
                r["step"],
                r["window_id"],
                r["tile_id"],
                r["y"],
                r["x"],
                r["hard_score"],
                r["pixel_accuracy"],
                r["error_rate"],
                r["mIoU_present_fg5"],
                r["n_present_fg5"],
                *r["fractions"],
                *r["iou"][:5],
            ])

    hard_values = np.array(
        [
            r["hard_score"]
            for r in records
            if np.isfinite(
                r["hard_score"]
            )
        ],
        dtype=np.float64,
    )

    if len(hard_values) > 0:
        hard_mean = float(
            np.mean(hard_values)
        )

        hard_median = float(
            np.median(hard_values)
        )

        hard_p80 = float(
            np.percentile(
                hard_values,
                80,
            )
        )

        hard_p90 = float(
            np.percentile(
                hard_values,
                90,
            )
        )

        top20_count = int(
            np.ceil(
                len(hard_values)
                * HISTORY_TOP_FRACTION
            )
        )
    else:
        hard_mean = float("nan")
        hard_median = float("nan")
        hard_p80 = float("nan")
        hard_p90 = float("nan")
        top20_count = 0

    seconds = (
        time.time()
        - start_time
    )

    with open(
        summary_path,
        "a",
        newline="",
    ) as f:
        csv.writer(f).writerow([
            global_step,
            len(records),
            total_possible,
            hard_mean,
            hard_median,
            hard_p80,
            hard_p90,
            top20_count,
            seconds,
        ])

    print(
        "[HISTORY-AUDIT] "
        f"windows={len(records)}/"
        f"{total_possible} | "
        f"hard_mean="
        f"{hard_mean:.6f} | "
        f"median="
        f"{hard_median:.6f} | "
        f"p80="
        f"{hard_p80:.6f} | "
        f"p90="
        f"{hard_p90:.6f} | "
        f"seconds="
        f"{seconds:.2f}"
    )

    print(
        "=" * 100
        + "\n"
    )

    return records



# ============================================================
# Online history pool construction
# ============================================================

def update_online_history_pool(
    records,
    run_dir,
    global_step,
):
    """
    Update online persistent-hard history using ONLY audits
    observed up to the current training step.

    Ranking:
      1. number of times the window entered current Top20%
      2. mean historical hard_score
      3. window_id for deterministic tie-breaking
    """
    global ACTIVE_HISTORY_POOL

    global ONLINE_HISTORY_STATS

    if (
        global_step
        in ONLINE_HISTORY_PROCESSED_STEPS
    ):
        print(
            "[ONLINE-HISTORY] "
            f"step {global_step} already processed; "
            "skip duplicate update."
        )
        return

    finite = [
        r
        for r in records
        if np.isfinite(
            float(
                r["hard_score"]
            )
        )
    ]

    finite = sorted(
        finite,
        key=lambda r: (
            -float(
                r["hard_score"]
            ),
            str(
                r["window_id"]
            ),
        ),
    )

    n_top = int(
        np.ceil(
            len(finite)
            * ONLINE_HISTORY_POOL_FRACTION
        )
    )

    current_top = {
        str(
            r["window_id"]
        )
        for r in finite[:n_top]
    }

    for r in finite:
        wid = str(
            r["window_id"]
        )

        score = float(
            r["hard_score"]
        )

        if wid not in ONLINE_HISTORY_STATS:
            ONLINE_HISTORY_STATS[wid] = {
                "window_id": wid,
                "tile_id": str(
                    r["tile_id"]
                ),
                "y": int(r["y"]),
                "x": int(r["x"]),
                "n_obs": 0,
                "top20_count": 0,
                "hard_sum": 0.0,
                "last_hard": score,
            }

        s = ONLINE_HISTORY_STATS[
            wid
        ]

        s["n_obs"] += 1
        s["hard_sum"] += score
        s["last_hard"] = score

        if wid in current_top:
            s["top20_count"] += 1

    ranked = []

    for wid, s in (
        ONLINE_HISTORY_STATS.items()
    ):
        n_obs = max(
            1,
            int(s["n_obs"]),
        )

        hard_mean = (
            float(s["hard_sum"])
            / n_obs
        )

        ranked.append(
            {
                "window_id": wid,
                "tile_id": str(
                    s["tile_id"]
                ),
                "y": int(s["y"]),
                "x": int(s["x"]),
                "top20_count": int(
                    s["top20_count"]
                ),
                "n_obs": int(
                    s["n_obs"]
                ),
                "hard_mean": float(
                    hard_mean
                ),
                "last_hard": float(
                    s["last_hard"]
                ),
            }
        )

    ranked.sort(
        key=lambda r: (
            -r["top20_count"],
            -r["hard_mean"],
            r["window_id"],
        )
    )

    pool_n = int(
        np.ceil(
            len(finite)
            * ONLINE_HISTORY_POOL_FRACTION
        )
    )

    ACTIVE_HISTORY_POOL[:] = (
        ranked[:pool_n]
    )

    ONLINE_HISTORY_PROCESSED_STEPS.add(
        int(global_step)
    )

    state_path = (
        run_dir
        / "online_history_state.json"
    )

    with open(
        state_path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            {
                "global_step": int(
                    global_step
                ),
                "processed_steps": sorted(
                    ONLINE_HISTORY_PROCESSED_STEPS
                ),
                "active_pool": (
                    ACTIVE_HISTORY_POOL
                ),
                "stats": (
                    ONLINE_HISTORY_STATS
                ),
                "sampler_counts": (
                    SAMPLER_COUNTS
                ),
            },
            f,
            indent=2,
        )

    pool_csv = (
        run_dir
        / "online_history_pool.csv"
    )

    new_file = (
        not pool_csv.is_file()
    )

    with open(
        pool_csv,
        "a",
        newline="",
    ) as f:
        writer = csv.writer(f)

        if new_file:
            writer.writerow([
                "step",
                "rank",
                "window_id",
                "tile_id",
                "y",
                "x",
                "top20_count",
                "n_obs",
                "hard_mean",
                "last_hard",
            ])

        for rank, r in enumerate(
            ACTIVE_HISTORY_POOL,
            start=1,
        ):
            writer.writerow([
                global_step,
                rank,
                r["window_id"],
                r["tile_id"],
                r["y"],
                r["x"],
                r["top20_count"],
                r["n_obs"],
                r["hard_mean"],
                r["last_hard"],
            ])

    if ACTIVE_HISTORY_POOL:
        counts = [
            r["top20_count"]
            for r in ACTIVE_HISTORY_POOL
        ]

        print(
            "[ONLINE-HISTORY] "
            f"step={global_step} | "
            f"pool={len(ACTIVE_HISTORY_POOL)} | "
            f"top20count="
            f"{min(counts)}..{max(counts)}"
        )

        print(
            "[ONLINE-HISTORY] "
            "top5:"
        )

        for r in (
            ACTIVE_HISTORY_POOL[:5]
        ):
            print(
                "  "
                f"{r['window_id']} | "
                f"count="
                f"{r['top20_count']}/"
                f"{r['n_obs']} | "
                f"mean="
                f"{r['hard_mean']:.4f}"
            )

    print(
        "[SAMPLER-COUNTS] "
        f"random="
        f"{SAMPLER_COUNTS['random']} | "
        f"rare="
        f"{SAMPLER_COUNTS['rare']} | "
        f"history="
        f"{SAMPLER_COUNTS['history']}"
    )


# ============================================================
# Checkpoint registry
# ============================================================

BEST_KEYS = [
    "OA",
    "mF1_fg5",
    "mIoU_fg5",
]


def save_model_for_iter(
    net,
    run_dir,
    global_step,
    epoch,
    result,
):
    path = (
        run_dir
        / "checkpoints"
        / f"model_iter_{global_step:06d}.pth"
    )

    if not path.is_file():
        torch.save(
            {
                "model": net.state_dict(),
                "global_step": global_step,
                "epoch": epoch,
                "metrics": {
                    "full": result["full"],
                    "noboundary": result[
                        "noboundary"
                    ],
                },
            },
            path,
        )

    return path


def update_best_registry(
    net,
    run_dir,
    registry,
    global_step,
    epoch,
    result,
):
    # Historical source-code-compatible selection:
    # use noBoundary metrics.
    current = result["noboundary"]

    improved = []

    for key in BEST_KEYS:
        old = registry.get(key)

        value = current[key]

        if (
            old is None
            or value > old["value"]
        ):
            improved.append(key)

    if not improved:
        return registry

    model_path = save_model_for_iter(
        net,
        run_dir,
        global_step,
        epoch,
        result,
    )

    for key in improved:
        registry[key] = {
            "value": current[key],
            "iter": global_step,
            "epoch": epoch,
            "model": model_path.name,
        }

    # Delete model checkpoints no longer referenced by any best metric.
    referenced = {
        entry["model"]
        for entry in registry.values()
    }

    checkpoint_dir = (
        run_dir / "checkpoints"
    )

    for p in checkpoint_dir.glob(
        "model_iter_*.pth"
    ):
        if p.name not in referenced:
            print(
                "[CLEANUP] delete old "
                f"non-best checkpoint: "
                f"{p.name}"
            )
            p.unlink()

    registry_path = (
        run_dir
        / "best_registry.json"
    )

    with open(
        registry_path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            registry,
            f,
            indent=2,
        )

    return registry


# ============================================================
# Resume
# ============================================================

def save_resume_state(
    net,
    optimizer,
    run_dir,
    epoch,
    global_step,
    registry,
):
    path = (
        run_dir
        / "last_train_state.pth"
    )

    torch.save(
        {
            "model": net.state_dict(),
            "optimizer": (
                optimizer.state_dict()
            ),
            "epoch": epoch,
            "global_step": global_step,
            "registry": registry,
            "python_rng": random.getstate(),
            "numpy_rng": np.random.get_state(),
            "torch_rng": torch.get_rng_state(),
            "cuda_rng": (
                torch.cuda.get_rng_state_all()
            ),
        },
        path,
    )


# ============================================================
# Main
# ============================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--resume",
    action="store_true",
)

parser.add_argument(
    "--variant",
    type=str,
    required=True,
    choices=["P1"],
)

parser.add_argument(
    "--smoke-steps",
    type=int,
    default=0,
    help=(
        "If >0, run only this many optimizer updates "
        "in a separate smoke directory."
    ),
)

parser.add_argument(
    "--smoke-eval",
    action="store_true",
    help=(
        "Run one full evaluation at the end of a smoke run. "
        "This is only for validating the inference/evaluation path."
    ),
)

parser.add_argument(
    "--max-steps",
    type=int,
    default=0,
    help=(
        "For a formal run, stop at this optimizer step. "
        "Use 0 for the full 160000-step schedule. "
        "A stopped formal run can later continue with --resume."
    ),
)

args = parser.parse_args()

if args.smoke_steps < 0:
    raise ValueError("--smoke-steps must be >= 0")

if args.max_steps < 0:
    raise ValueError("--max-steps must be >= 0")

if (
    args.max_steps > TOTAL_STEPS
):
    raise ValueError(
        f"--max-steps cannot exceed "
        f"{TOTAL_STEPS}"
    )

if (
    args.smoke_steps > 0
    and args.max_steps > 0
):
    raise ValueError(
        "--smoke-steps and --max-steps "
        "cannot be used together"
    )

if (
    args.smoke_eval
    and args.smoke_steps == 0
):
    raise ValueError(
        "--smoke-eval requires "
        "--smoke-steps > 0"
    )

run_mode = (
    f"smoke{args.smoke_steps}"
    if args.smoke_steps > 0
    else "formal160k"
)

run_name = (
    "Thesis_Ch4_NoSR_ScreenV3_History30_P1_"
    f"Vaihingen_{args.variant}_seed42_"
    f"{run_mode}"
)

RUN_DIR = (
    ROOT
    / "runs"
    / run_name
)

if RUN_DIR.exists() and not args.resume:
    raise FileExistsError(
        "Run directory already exists. "
        "Refusing to overwrite: "
        f"{RUN_DIR}"
    )

(RUN_DIR / "checkpoints").mkdir(
    parents=True,
    exist_ok=True,
)

set_seed(SEED)

train_cache, test_cache = preload_all()

print("\nBUILD MODEL")

# Deep-copy is important because CONFIGS is global.
import copy

config = copy.deepcopy(
    CONFIGS["R50-ViT-B_16"]
)

config.n_classes = 6
config.n_skip = 3

# Preserve the original 16-pixel effective token stride:
# 256 -> 16x16
# 512 -> 32x32
config.patches.grid = (
    PATCH // 16,
    PATCH // 16,
)

net = VisionTransformerPreFusionFreq(
    config,
    img_size=PATCH,
    num_classes=6,
).to(DEVICE)

# Architecture-adapted differential LR.
#
# P1 keeps the exact F0 backbone and decoder.
#
# Groups:
#   backbone      : pretrained/common trunk, 1x LR
#   decoder/head  : existing new modules, 10x LR
#   prefreq0      : P1-only 593-parameter module, 10x LR
#
# Keeping prefreq0 separate makes its learning rate and
# parameter assignment explicitly auditable.
backbone_params = []
new_module_params = []
prefreq_params = []

backbone_numel = 0
new_module_numel = 0
prefreq_numel = 0

for name, param in net.named_parameters():
    if not param.requires_grad:
        continue

    if ".prefreq0." in name:
        prefreq_params.append(param)
        prefreq_numel += param.numel()

    elif (
        name.startswith("decoder.")
        or name.startswith("segmentation_head.")
    ):
        new_module_params.append(param)
        new_module_numel += param.numel()

    else:
        backbone_params.append(param)
        backbone_numel += param.numel()


assigned = (
    sum(p.numel() for p in backbone_params)
    + sum(p.numel() for p in new_module_params)
    + sum(p.numel() for p in prefreq_params)
)

trainable = sum(
    p.numel()
    for p in net.parameters()
    if p.requires_grad
)

if assigned != trainable:
    raise RuntimeError(
        f"Optimizer grouping mismatch: "
        f"assigned={assigned}, "
        f"trainable={trainable}"
    )

if prefreq_numel != 593:
    raise RuntimeError(
        f"Unexpected prefreq0 parameter count: "
        f"{prefreq_numel}"
    )

optimizer = torch.optim.AdamW(
    [
        {
            "params": backbone_params,
            "lr": BASE_LR,
            "lr_mult": 1.0,
            "group_name": "backbone",
        },
        {
            "params": new_module_params,
            "lr": (
                BASE_LR
                * NEW_MODULE_LR_MULT
            ),
            "lr_mult": NEW_MODULE_LR_MULT,
            "group_name": "decoder_head",
        },
        {
            "params": prefreq_params,
            "lr": (
                BASE_LR
                * NEW_MODULE_LR_MULT
            ),
            "lr_mult": NEW_MODULE_LR_MULT,
            "group_name": "prefreq",
        },
    ],
    betas=(0.9, 0.999),
    weight_decay=WEIGHT_DECAY,
)

print(
    "[OPTIMIZER GROUP] backbone:",
    f"{backbone_numel:,}",
    "parameters",
)

print(
    "[OPTIMIZER GROUP] decoder/head:",
    f"{new_module_numel:,}",
    "parameters",
)

print(
    "[OPTIMIZER GROUP] prefreq0:",
    f"{prefreq_numel:,}",
    "parameters",
)

resume_path = (
    RUN_DIR
    / "last_train_state.pth"
)

registry = {}

start_epoch = 1
global_step = 0

if args.resume:
    if not resume_path.is_file():
        raise FileNotFoundError(
            resume_path
        )

    state = torch.load(
        resume_path,
        map_location="cpu",
    )

    net.load_state_dict(
        state["model"],
        strict=True,
    )

    optimizer.load_state_dict(
        state["optimizer"]
    )

    start_epoch = (
        int(state["epoch"]) + 1
    )

    global_step = int(
        state["global_step"]
    )

    registry = state.get(
        "registry",
        {},
    )

    random.setstate(
        state["python_rng"]
    )

    np.random.set_state(
        state["numpy_rng"]
    )

    torch.set_rng_state(
        state["torch_rng"]
    )

    torch.cuda.set_rng_state_all(
        state["cuda_rng"]
    )

    print(
        "[RESUME]",
        "epoch=", start_epoch,
        "global_step=", global_step,
    )

else:
    weights = np.load(
        str(PRETRAIN)
    )

    net.load_from(
        weights=weights
    )

    print(
        "[PASS] pretrained weights loaded"
    )


# ------------------------------------------------------------
# P1 structural gate
# ------------------------------------------------------------

freq_modules = [
    n
    for n, _ in net.named_modules()
    if "freq_fusion" in n.lower()
]

sgor_modules = [
    n
    for n, _ in net.named_modules()
    if "dysampler" in n.lower()
]

hfdc_modules = [
    n
    for n, _ in net.named_modules()
    if "content_encoder2" in n.lower()
]

prefreq_modules = [
    n
    for n, _ in net.named_modules()
    if n.endswith("prefreq0")
]

prefreq_param_names = [
    n
    for n, _ in net.named_parameters()
    if ".prefreq0." in n
]

n_freq = len(freq_modules)
n_sgor = len(sgor_modules)
n_hfdc = len(hfdc_modules)
n_prefreq = len(prefreq_modules)

print(
    "P1 STRUCTURE | "
    f"FreqFusion={n_freq} | "
    f"SGOR={n_sgor} | "
    f"HFDC={n_hfdc} | "
    f"PreFreq={n_prefreq}"
)

print(
    "[PREFREQ PARAMETERS]",
    f"{prefreq_numel:,}",
    "parameters |",
    f"{len(prefreq_param_names)} tensors",
)

if not (
    n_freq == 0
    and n_sgor == 0
    and n_hfdc == 0
    and n_prefreq == 1
):
    raise RuntimeError(
        "P1 structure invalid: "
        f"FreqFusion={n_freq}, "
        f"SGOR={n_sgor}, "
        f"HFDC={n_hfdc}, "
        f"PreFreq={n_prefreq}"
    )

if len(prefreq_param_names) != 4:
    raise RuntimeError(
        "Expected exactly 4 prefreq0 parameter tensors, "
        f"got {len(prefreq_param_names)}"
    )

prefreq_ids = {
    id(p)
    for p in prefreq_params
}

bad_group = [
    name
    for name, param in net.named_parameters()
    if (
        ".prefreq0." in name
        and id(param) not in prefreq_ids
    )
]

if bad_group:
    raise RuntimeError(
        f"prefreq0 optimizer assignment failed: "
        f"{bad_group}"
    )

print(
    "[PASS] all prefreq0 parameters use "
    "the dedicated 10x LR group"
)

print(
    "[PASS] P1 structural gate"
)

# ------------------------------------------------------------------
# Logs
# ------------------------------------------------------------------

train_csv = (
    RUN_DIR
    / "train_history.csv"
)

metric_csv = (
    RUN_DIR
    / "metrics_history.csv"
)

if not args.resume:
    with open(
        train_csv,
        "w",
        newline="",
    ) as f:
        csv.writer(f).writerow([
            "step",
            "epoch",
            "step_in_epoch",
            "lr",
            "loss",
            "mean_loss_50",
            "sec_per_step",
        ])

    with open(
        metric_csv,
        "w",
        newline="",
    ) as f:
        csv.writer(f).writerow([
            "step",
            "epoch",

            "full_OA",
            "full_mF1_fg5",
            "full_mIoU_fg5",
            "full_mF1_all6",
            "full_mIoU_all6",

            "nb_OA",
            "nb_mF1_fg5",
            "nb_mIoU_fg5",
            "nb_mF1_all6",
            "nb_mIoU_all6",

            "eval_seconds",
        ])


def lr_factor_for_step(step):
    """
    Linear warmup followed by polynomial decay.

    `step` is an optimizer-update count, not a micro-batch count.
    """

    if step <= WARMUP_STEPS:
        alpha = (
            step / WARMUP_STEPS
        )

        return (
            WARMUP_RATIO
            + alpha
            * (1.0 - WARMUP_RATIO)
        )

    progress = (
        (step - WARMUP_STEPS)
        / (TOTAL_STEPS - WARMUP_STEPS)
    )

    progress = min(
        max(progress, 0.0),
        1.0,
    )

    return (
        (1.0 - progress)
        ** POLY_POWER
    )


def set_optimizer_lr(step):
    factor = lr_factor_for_step(step)

    for group in optimizer.param_groups:
        group["lr"] = (
            BASE_LR
            * float(group["lr_mult"])
            * factor
        )

    return {
        group["group_name"]:
            group["lr"]
        for group in optimizer.param_groups
    }


if args.smoke_steps > 0:
    target_total_steps = (
        args.smoke_steps
    )
elif args.max_steps > 0:
    target_total_steps = (
        args.max_steps
    )
else:
    target_total_steps = (
        TOTAL_STEPS
    )

loss_buffer = []

print("\n" + "=" * 100)
print("P1 PRE-FUSION FREQUENCY TRAINING START")
print("variant:", args.variant)
print("run:", RUN_DIR)
print("pseudo epochs:", EPOCHS)
print("optimizer steps/pseudo-epoch:", STEPS_PER_EPOCH)
print("formal optimizer steps:", TOTAL_STEPS)
print("requested smoke steps:", args.smoke_steps)
print("formal max steps:", args.max_steps)
print("actual target optimizer steps:", target_total_steps)
print("physical batch:", TRAIN_BATCH)
print("gradient accumulation:", ACCUM_STEPS)
print("effective sampled batch:", EFFECTIVE_BATCH)
print("crop:", PATCH)
print("sampling policy:", "history30")
print("online history pool fraction:", ONLINE_HISTORY_POOL_FRACTION)
print("grid:", config.patches.grid)
print(
    "random scale:",
    RANDOM_SCALE_MIN,
    "to",
    RANDOM_SCALE_MAX,
)
print("optimizer: AdamW")
print("base LR:", BASE_LR)
print("decoder/head LR multiplier:", NEW_MODULE_LR_MULT)
print("warmup optimizer steps:", WARMUP_STEPS)
print("poly power:", POLY_POWER)
print("eval interval:", EVAL_INTERVAL)
print("=" * 100)

torch.cuda.reset_peak_memory_stats()

training_start = time.time()


stop_training = False

for epoch in range(
    start_epoch,
    EPOCHS + 1,
):
    if global_step >= target_total_steps:
        break

    print(
        f"\n===== PSEUDO-EPOCH "
        f"{epoch:03d}/{EPOCHS} ====="
    )

    net.train()

    for step_in_epoch in range(
        1,
        STEPS_PER_EPOCH + 1,
    ):
        if global_step >= target_total_steps:
            stop_training = True
            break

        step_start = time.time()

        # global_step counts optimizer updates.
        next_global_step = (
            global_step + 1
        )

        lrs = set_optimizer_lr(
            next_global_step
        )

        optimizer.zero_grad(
            set_to_none=True
        )

        micro_losses = []
        micro_scales = []

        for micro_idx in range(
            ACCUM_STEPS
        ):
            (
                optical,
                dsm,
                gt,
                sampled_scales,
            ) = sample_train_batch(
                train_cache
            )

            logits = net(
                optical,
                dsm,
            )

            # Deterministic paired-protocol CE.
            #
            # Mathematically identical pixel-wise CE:
            # [B,C,H,W] -> [B*H*W,C]
            # [B,H,W]   -> [B*H*W]
            #
            # This avoids CUDA nll_loss2d, which has no
            # deterministic implementation in PyTorch 2.1.2.
            flat_logits = (
                logits
                .permute(0, 2, 3, 1)
                .contiguous()
                .view(-1, logits.shape[1])
            )

            flat_gt = (
                gt
                .contiguous()
                .view(-1)
            )

            raw_loss = F.cross_entropy(
                flat_logits,
                flat_gt,
            )

            if not torch.isfinite(raw_loss):
                raise RuntimeError(
                    f"Non-finite loss "
                    f"before optimizer step "
                    f"{next_global_step}, "
                    f"micro={micro_idx}"
                )

            # Average gradients across the accumulated
            # micro-batches.
            (
                raw_loss / ACCUM_STEPS
            ).backward()

            micro_losses.append(
                float(
                    raw_loss.detach()
                )
            )

            micro_scales.extend(
                sampled_scales
            )

            del optical
            del dsm
            del gt
            del logits
            del raw_loss

        optimizer.step()

        global_step = next_global_step

        torch.cuda.synchronize()

        loss_value = float(
            np.mean(micro_losses)
        )

        scale_mean = float(
            np.mean(micro_scales)
        )

        scale_min = float(
            np.min(micro_scales)
        )

        scale_max = float(
            np.max(micro_scales)
        )

        loss_buffer.append(
            loss_value
        )

        mean50 = float(
            np.mean(
                loss_buffer[-50:]
            )
        )

        sec_step = (
            time.time()
            - step_start
        )

        # Keep the legacy CSV column layout.
        # `lr` records backbone LR; decoder/head LR is always 10x.
        lr = lrs["backbone"]

        with open(
            train_csv,
            "a",
            newline="",
        ) as f:
            csv.writer(f).writerow([
                global_step,
                epoch,
                step_in_epoch,
                lr,
                f"{loss_value:.8f}",
                f"{mean50:.8f}",
                f"{sec_step:.4f}",
            ])

        if (
            global_step == 1
            or global_step % 20 == 0
        ):
            allocated = (
                torch.cuda
                .memory_allocated()
                / 1024**3
            )

            reserved = (
                torch.cuda
                .memory_reserved()
                / 1024**3
            )

            diag = (
                net.get_prefreq_diagnostics()
            )

            pf_scale = diag["scale"]
            pf_disc = diag["discrepancy"]

            if (
                pf_scale is None
                or pf_disc is None
            ):
                raise RuntimeError(
                    "Missing P1 diagnostics "
                    "after forward"
                )

            pf_scale_mean = float(
                pf_scale.mean()
            )

            pf_scale_min = float(
                pf_scale.min()
            )

            pf_scale_max = float(
                pf_scale.max()
            )

            pf_delta_abs = float(
                (
                    pf_scale - 1.0
                )
                .abs()
                .mean()
            )

            pf_disc_mean = float(
                pf_disc.mean()
            )

            pf_disc_min = float(
                pf_disc.min()
            )

            pf_disc_max = float(
                pf_disc.max()
            )

            # Distribution diagnostics.
            #
            # These help distinguish:
            #   1) global gate drift,
            #   2) localized frequency calibration,
            #   3) saturation/collapse.
            pf_scale_lt095 = float(
                (pf_scale < 0.95)
                .float()
                .mean()
            )

            pf_scale_gt105 = float(
                (pf_scale > 1.05)
                .float()
                .mean()
            )

            pf_scale_lt050 = float(
                (pf_scale < 0.50)
                .float()
                .mean()
            )

            pf_scale_gt150 = float(
                (pf_scale > 1.50)
                .float()
                .mean()
            )

            pf_disc_flat = (
                pf_disc
                .detach()
                .float()
                .reshape(-1)
            )

            pf_disc_p95 = float(
                torch.quantile(
                    pf_disc_flat,
                    0.95,
                )
            )

            pf_disc_p99 = float(
                torch.quantile(
                    pf_disc_flat,
                    0.99,
                )
            )

            print(
                f"step "
                f"{global_step:06d}/"
                f"{target_total_steps} | "
                f"loss={loss_value:.6f} | "
                f"mean50={mean50:.6f} | "
                f"lr_backbone="
                f"{lrs['backbone']:.3e} | "
                f"lr_head="
                f"{lrs['decoder_head']:.3e} | "
                f"lr_prefreq="
                f"{lrs['prefreq']:.3e} | "
                f"aug_scale="
                f"{scale_mean:.3f}"
                f"[{scale_min:.3f},"
                f"{scale_max:.3f}] | "
                f"hf_scale="
                f"{pf_scale_mean:.6f}"
                f"[{pf_scale_min:.6f},"
                f"{pf_scale_max:.6f}] | "
                f"hf_delta="
                f"{pf_delta_abs:.6f} | "
                f"hf_disc="
                f"{pf_disc_mean:.6f}"
                f"[{pf_disc_min:.6f},"
                f"{pf_disc_max:.6f}] | "
                f"disc_p95/p99="
                f"{pf_disc_p95:.4f}/"
                f"{pf_disc_p99:.4f} | "
                f"S<.95="
                f"{pf_scale_lt095*100:.2f}% | "
                f"S>1.05="
                f"{pf_scale_gt105*100:.2f}% | "
                f"S<.5="
                f"{pf_scale_lt050*100:.2f}% | "
                f"S>1.5="
                f"{pf_scale_gt150*100:.2f}% | "
                f"GPU="
                f"{allocated:.2f}/"
                f"{reserved:.2f}G | "
                f"{sec_step:.3f}s"
            )

        # No expensive test-set evaluation during smoke.
        do_eval = (
            (
                args.smoke_steps == 0
                and global_step % EVAL_INTERVAL == 0
            )
            or
            (
                args.smoke_steps > 0
                and args.smoke_eval
                and global_step == target_total_steps
            )
        )

        if do_eval:
            print(
                "\n"
                + "-" * 100
            )

            print(
                f"EVALUATION "
                f"@ ITER {global_step}"
            )

            result = evaluate(
                net,
                test_cache,
            )

            full = result["full"]
            nb = result["noboundary"]

            # ------------------------------------------------
            # Observation-only persistent hard-region audit.
            #
            # For smoke tests only 16 fixed windows are used.
            # Formal runs audit every fixed training window.
            # ------------------------------------------------
            audit_records = run_history_audit(
                net,
                train_cache,
                global_step,
                RUN_DIR,
                max_windows=(
                    16
                    if args.smoke_steps > 0
                    else None
                ),
            )

            update_online_history_pool(
                audit_records,
                RUN_DIR,
                global_step,
            )

            print(
                "FULL | "
                f"OA={full['OA']*100:.4f} "
                f"mF1fg5="
                f"{full['mF1_fg5']*100:.4f} "
                f"mIoUfg5="
                f"{full['mIoU_fg5']*100:.4f}"
            )

            print(
                "NB   | "
                f"OA={nb['OA']*100:.4f} "
                f"mF1fg5="
                f"{nb['mF1_fg5']*100:.4f} "
                f"mIoUfg5="
                f"{nb['mIoU_fg5']*100:.4f}"
            )

            with open(
                metric_csv,
                "a",
                newline="",
            ) as f:
                csv.writer(f).writerow([
                    global_step,
                    epoch,

                    full["OA"],
                    full["mF1_fg5"],
                    full["mIoU_fg5"],
                    full["mF1_all6"],
                    full["mIoU_all6"],

                    nb["OA"],
                    nb["mF1_fg5"],
                    nb["mIoU_fg5"],
                    nb["mF1_all6"],
                    nb["mIoU_all6"],

                    result["seconds"],
                ])

            registry = (
                update_best_registry(
                    net,
                    RUN_DIR,
                    registry,
                    global_step,
                    epoch,
                    result,
                )
            )

            print(
                "CURRENT BEST:"
            )

            for key in BEST_KEYS:
                b = registry.get(key)

                if b:
                    print(
                        f"  {key:10s}: "
                        f"{b['value']*100:.4f}% "
                        f"@ iter "
                        f"{b['iter']}"
                    )

            print(
                "-" * 100
                + "\n"
            )

            # evaluate() switches net to eval().
            net.train()

    # Formal run keeps one resumable state per pseudo-epoch.
    if args.smoke_steps == 0:
        print(
            f"[SAVE] resume state "
            f"after pseudo-epoch {epoch}"
        )

        save_resume_state(
            net,
            optimizer,
            RUN_DIR,
            epoch,
            global_step,
            registry,
        )

    if stop_training:
        break

total_seconds = (
    time.time()
    - training_start
)

peak_allocated = (
    torch.cuda
    .max_memory_allocated()
    / 1024**3
)

print("\n" + "=" * 100)
print("FORMAL TRAINING COMPLETE")
print("total steps       :", global_step)
print("total seconds     :", total_seconds)
print("peak allocated GB :", peak_allocated)
print("best registry     :", registry)
print("run dir           :", RUN_DIR)
print("=" * 100)
