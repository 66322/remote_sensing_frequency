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

from model.vitcross_seg_modeling_shallow_detail import (
    VisionTransformerShallowDetail,
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

# ============================================================
# Screening experiment: Rare/Object-aware sampling
# ============================================================

RARE_PROB = 0.30

# Foreground classes:
# 2 = LowVegetation
# 3 = Tree
# 4 = Car
#
# Car receives a larger probability because it is rare and
# has shown the largest early per-class sensitivity.
RARE_CLASSES = (2, 3, 4)
RARE_WEIGHTS = (0.25, 0.25, 0.50)

# Avoid retaining millions of coordinates per tile/class.
RARE_CACHE_MAX_POINTS = 100000

RARE_COORD_CACHE = {}


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
    Deterministic capped coordinate cache for targeted sampling.
    """
    key = (
        str(tile_id),
        int(class_id),
    )

    cached = RARE_COORD_CACHE.get(key)

    if cached is not None:
        return cached

    flat = np.flatnonzero(
        gt.reshape(-1) == class_id
    )

    if flat.size > RARE_CACHE_MAX_POINTS:
        step = max(
            1,
            int(
                np.ceil(
                    flat.size
                    / RARE_CACHE_MAX_POINTS
                )
            ),
        )

        flat = flat[
            ::step
        ][:RARE_CACHE_MAX_POINTS]

    RARE_COORD_CACHE[key] = flat

    return flat



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
        # 70% original random crop
        # 30% rare/object-aware crop
        #
        # Rare branch selects a semantic pixel and places it
        # near the crop center with moderate spatial jitter.
        # ----------------------------------------------------
        use_rare = (
            random.random()
            < RARE_PROB
        )

        if use_rare:
            target_class = random.choices(
                RARE_CLASSES,
                weights=RARE_WEIGHTS,
                k=1,
            )[0]

            rare_flat = _rare_flat_indices(
                tile_id,
                gt,
                target_class,
            )

            # Very defensive fallback if this class does not
            # occur in the selected tile.
            if rare_flat.size == 0:
                use_rare = False

        if use_rare:
            pos = int(
                rare_flat[
                    random.randrange(
                        int(rare_flat.size)
                    )
                ]
            )

            cy = pos // W
            cx = pos % W

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
                        cy - source_size // 2,
                    ),
                )
            )

            x = int(
                max(
                    0,
                    min(
                        W - source_size,
                        cx - source_size // 2,
                    ),
                )
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
    choices=["P2H"],
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
    "Thesis_Ch4_NoSR_ScreenV4_Rare30_P2H_NormalDetail_"
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

net = VisionTransformerShallowDetail(
    config,
    img_size=PATCH,
    num_classes=6,
    detail_mode="NORMAL",
).to(DEVICE)

# Architecture-adapted differential LR.
#
# P1 keeps the exact F0 backbone and decoder.
#
# Groups:
#   backbone      : pretrained/common trunk, 1x LR
#   decoder/head  : existing new modules, 10x LR
#   hfrely0      : P1-only 738-parameter module, 10x LR
#
# Keeping hfrely0 separate makes its learning rate and
# parameter assignment explicitly auditable.
backbone_params = []
new_module_params = []
hfrely_params = []

backbone_numel = 0
new_module_numel = 0
hfrely_numel = 0

for name, param in net.named_parameters():
    if not param.requires_grad:
        continue

    if ".hfrely0." in name:
        hfrely_params.append(param)
        hfrely_numel += param.numel()

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
    + sum(p.numel() for p in hfrely_params)
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

if hfrely_numel != 738:
    raise RuntimeError(
        f"Unexpected hfrely0 parameter count: "
        f"{hfrely_numel}"
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
            "params": hfrely_params,
            "lr": (
                BASE_LR
                * NEW_MODULE_LR_MULT
            ),
            "lr_mult": NEW_MODULE_LR_MULT,
            "group_name": "hfrely",
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
    "[OPTIMIZER GROUP] hfrely0:",
    f"{hfrely_numel:,}",
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
# P2-H structural gate
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

hfrely_modules = [
    n
    for n, _ in net.named_modules()
    if n.endswith("hfrely0")
]

hfrely_param_names = [
    n
    for n, _ in net.named_parameters()
    if ".hfrely0." in n
]

n_freq = len(freq_modules)
n_sgor = len(sgor_modules)
n_hfdc = len(hfdc_modules)
n_hfrely = len(hfrely_modules)

print(
    "P2-H STRUCTURE | "
    f"FreqFusion={n_freq} | "
    f"SGOR={n_sgor} | "
    f"HFDC={n_hfdc} | "
    f"PreFreq={n_hfrely}"
)

print(
    "[PREFREQ PARAMETERS]",
    f"{hfrely_numel:,}",
    "parameters |",
    f"{len(hfrely_param_names)} tensors",
)

if not (
    n_freq == 0
    and n_sgor == 0
    and n_hfdc == 0
    and n_hfrely == 1
):
    raise RuntimeError(
        "P2-H structure invalid: "
        f"FreqFusion={n_freq}, "
        f"SGOR={n_sgor}, "
        f"HFDC={n_hfdc}, "
        f"PreFreq={n_hfrely}"
    )

if len(hfrely_param_names) != 4:
    raise RuntimeError(
        "Expected exactly 4 hfrely0 parameter tensors, "
        f"got {len(hfrely_param_names)}"
    )

hfrely_ids = {
    id(p)
    for p in hfrely_params
}

bad_group = [
    name
    for name, param in net.named_parameters()
    if (
        ".hfrely0." in name
        and id(param) not in hfrely_ids
    )
]

if bad_group:
    raise RuntimeError(
        f"hfrely0 optimizer assignment failed: "
        f"{bad_group}"
    )

print(
    "[PASS] all hfrely0 parameters use "
    "the dedicated 10x LR group"
)

print(
    "[PASS] P2-H structural gate"
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

p2h_diag_csv = (
    RUN_DIR
    / "p2h_diagnostics.csv"
)

# Dedicated mechanism log.
#
# This intentionally stays separate from train_history.csv so
# the frozen DetPair training-history schema remains unchanged.
if (
    not args.resume
    or not p2h_diag_csv.is_file()
):
    with open(
        p2h_diag_csv,
        "w",
        newline="",
    ) as f:
        csv.writer(f).writerow([
            "step",
            "epoch",
            "step_in_epoch",

            "wo_mean",
            "wo_p05",
            "wo_p50",
            "wo_p95",

            "wd_mean",
            "wd_p05",
            "wd_p50",
            "wd_p95",

            "So_mean",
            "So_min",
            "So_max",

            "Sd_mean",
            "Sd_min",
            "Sd_max",

            "opt_dominant_frac",
            "dsm_dominant_frac",

            "opt_dominant_005_frac",
            "dsm_dominant_005_frac",
            "neutral_005_frac",

            "wo_gt060_frac",
            "wd_gt060_frac",

            "reliability_gap_mean",

            "hf_disc_mean",
            "hf_disc_p95",
            "hf_disc_p99",
        ])

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
print("P2-H HF RELIABILITY TRAINING START")
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
print("shallow detail mode:", "NORMAL")
print("grid:", config.patches.grid)
print(
    "random scale:",
    RANDOM_SCALE_MIN,
    "to",
    RANDOM_SCALE_MAX,
)
print("rare sampling: 70% random + 30% targeted; ""target weights LowVeg/Tree/Car = ""0.25/0.25/0.50")
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
                net.get_hfrely_diagnostics()
            )

            pf_scale = diag["scale"]
            pf_disc = diag["discrepancy"]

            if (
                pf_scale is None
                or pf_disc is None
            ):
                raise RuntimeError(
                    "Missing P2-H diagnostics "
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

            # ==================================================
            # P2-H explicit cross-modal reliability diagnostics
            # ==================================================

            p2h_weights = diag["weights"]
            p2h_opt_scale = diag[
                "optical_scale"
            ]
            p2h_dsm_scale = diag[
                "dsm_scale"
            ]

            if (
                p2h_weights is None
                or p2h_opt_scale is None
                or p2h_dsm_scale is None
            ):
                raise RuntimeError(
                    "Missing explicit P2-H reliability "
                    "diagnostics after forward"
                )

            if (
                p2h_weights.ndim != 4
                or p2h_weights.shape[1] != 2
            ):
                raise RuntimeError(
                    "Unexpected P2-H reliability shape: "
                    f"{tuple(p2h_weights.shape)}"
                )

            wo = (
                p2h_weights[:, 0:1]
                .detach()
                .float()
                .reshape(-1)
            )

            wd = (
                p2h_weights[:, 1:2]
                .detach()
                .float()
                .reshape(-1)
            )

            so = (
                p2h_opt_scale
                .detach()
                .float()
                .reshape(-1)
            )

            sd = (
                p2h_dsm_scale
                .detach()
                .float()
                .reshape(-1)
            )

            # Strict structural consistency:
            # wo + wd = 1
            # So + Sd = 2
            weight_sum_err = float(
                (
                    wo + wd - 1.0
                )
                .abs()
                .max()
            )

            scale_sum_err = float(
                (
                    so + sd - 2.0
                )
                .abs()
                .max()
            )

            if weight_sum_err > 1e-6:
                raise RuntimeError(
                    "P2-H reliability weights no longer "
                    f"sum to 1: err={weight_sum_err}"
                )

            if scale_sum_err > 1e-6:
                raise RuntimeError(
                    "P2-H HF scales no longer sum to 2: "
                    f"err={scale_sum_err}"
                )

            wo_mean = float(
                wo.mean()
            )

            wd_mean = float(
                wd.mean()
            )

            wo_p05 = float(
                torch.quantile(
                    wo,
                    0.05,
                )
            )

            wo_p50 = float(
                torch.quantile(
                    wo,
                    0.50,
                )
            )

            wo_p95 = float(
                torch.quantile(
                    wo,
                    0.95,
                )
            )

            wd_p05 = float(
                torch.quantile(
                    wd,
                    0.05,
                )
            )

            wd_p50 = float(
                torch.quantile(
                    wd,
                    0.50,
                )
            )

            wd_p95 = float(
                torch.quantile(
                    wd,
                    0.95,
                )
            )

            so_mean = float(
                so.mean()
            )

            so_min = float(
                so.min()
            )

            so_max = float(
                so.max()
            )

            sd_mean = float(
                sd.mean()
            )

            sd_min = float(
                sd.min()
            )

            sd_max = float(
                sd.max()
            )

            opt_dominant = float(
                (
                    wo > wd
                )
                .float()
                .mean()
            )

            dsm_dominant = float(
                (
                    wd > wo
                )
                .float()
                .mean()
            )

            # Confidence-aware dominance.
            #
            # Raw wo>wd is extremely sensitive around the
            # neutral initialization wo=wd=0.5.  A 0.005
            # deadband distinguishes meaningful spatial
            # preference from numerical/small early drift.
            opt_dominant_005 = float(
                (
                    wo > 0.505
                )
                .float()
                .mean()
            )

            dsm_dominant_005 = float(
                (
                    wd > 0.505
                )
                .float()
                .mean()
            )

            neutral_005 = float(
                (
                    (wo - 0.5)
                    .abs()
                    <= 0.005
                )
                .float()
                .mean()
            )

            wo_gt060 = float(
                (
                    wo > 0.60
                )
                .float()
                .mean()
            )

            wd_gt060 = float(
                (
                    wd > 0.60
                )
                .float()
                .mean()
            )

            reliability_gap = float(
                (
                    wo - wd
                )
                .abs()
                .mean()
            )

            with open(
                p2h_diag_csv,
                "a",
                newline="",
            ) as f:
                csv.writer(f).writerow([
                    global_step,
                    epoch,
                    step_in_epoch,

                    f"{wo_mean:.8f}",
                    f"{wo_p05:.8f}",
                    f"{wo_p50:.8f}",
                    f"{wo_p95:.8f}",

                    f"{wd_mean:.8f}",
                    f"{wd_p05:.8f}",
                    f"{wd_p50:.8f}",
                    f"{wd_p95:.8f}",

                    f"{so_mean:.8f}",
                    f"{so_min:.8f}",
                    f"{so_max:.8f}",

                    f"{sd_mean:.8f}",
                    f"{sd_min:.8f}",
                    f"{sd_max:.8f}",

                    f"{opt_dominant:.8f}",
                    f"{dsm_dominant:.8f}",

                    f"{opt_dominant_005:.8f}",
                    f"{dsm_dominant_005:.8f}",
                    f"{neutral_005:.8f}",

                    f"{wo_gt060:.8f}",
                    f"{wd_gt060:.8f}",

                    f"{reliability_gap:.8f}",

                    f"{pf_disc_mean:.8f}",
                    f"{pf_disc_p95:.8f}",
                    f"{pf_disc_p99:.8f}",
                ])

            print(
                "[P2H-DIAG] "
                f"wo={wo_mean:.4f}"
                f"[{wo_p05:.4f},"
                f"{wo_p50:.4f},"
                f"{wo_p95:.4f}] | "
                f"wd={wd_mean:.4f}"
                f"[{wd_p05:.4f},"
                f"{wd_p50:.4f},"
                f"{wd_p95:.4f}] | "
                f"So/Sd="
                f"{so_mean:.4f}/"
                f"{sd_mean:.4f} | "
                f"OptDom="
                f"{opt_dominant*100:.2f}% | "
                f"DSMDom="
                f"{dsm_dominant*100:.2f}% | "
                f"OptDom005="
                f"{opt_dominant_005*100:.2f}% | "
                f"DSMDom005="
                f"{dsm_dominant_005*100:.2f}% | "
                f"Neutral005="
                f"{neutral_005*100:.2f}% | "
                f"wo>.60="
                f"{wo_gt060*100:.2f}% | "
                f"wd>.60="
                f"{wd_gt060*100:.2f}% | "
                f"gap="
                f"{reliability_gap:.4f} | "
                f"disc="
                f"{pf_disc_mean:.4f}"
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
                f"lr_hfrely="
                f"{lrs['hfrely']:.3e} | "
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
