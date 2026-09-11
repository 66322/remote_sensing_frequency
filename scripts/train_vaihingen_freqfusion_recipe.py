import os
import sys
import csv
import json
import time
import random
import argparse
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

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

from model.vitcross_seg_modeling_freq_ablation import (
    VisionTransformerFreqAblation,
    CONFIGS,
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
    choices=["F0", "F3"],
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
    "Thesis_Ch4_NoSR_Stage2_FreqRecipe_"
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

net = VisionTransformerFreqAblation(
    config,
    img_size=PATCH,
    num_classes=6,
    freq_variant=args.variant,
).to(DEVICE)

# Architecture-adapted differential LR.
#
# The transformer branch is treated as the pretrained trunk.
# Decoder and segmentation head are newly initialized in both
# F0 and F3 and receive the same 10x LR multiplier.
#
# This keeps F0/F3 comparison fair: F3 is not granted an LR
# advantage that F0 does not receive.
backbone_params = []
new_module_params = []

backbone_numel = 0
new_module_numel = 0

for name, param in net.named_parameters():
    if not param.requires_grad:
        continue

    if (
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
# Variant-specific structural gate
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

n_freq = len(freq_modules)
n_sgor = len(sgor_modules)
n_hfdc = len(hfdc_modules)

print(
    f"VARIANT STRUCTURE | "
    f"{args.variant} | "
    f"FreqFusion={n_freq} | "
    f"SGOR={n_sgor} | "
    f"HFDC={n_hfdc}"
)

if args.variant == "F0":
    if not (
        n_freq == 0
        and n_sgor == 0
        and n_hfdc == 0
    ):
        raise RuntimeError(
            f"F0 structure invalid: "
            f"FreqFusion={n_freq}, "
            f"SGOR={n_sgor}, "
            f"HFDC={n_hfdc}"
        )

elif args.variant == "F1":
    if not (
        n_freq > 0
        and n_sgor == 0
        and n_hfdc == 0
    ):
        raise RuntimeError(
            f"F1 structure invalid: "
            f"FreqFusion={n_freq}, "
            f"SGOR={n_sgor}, "
            f"HFDC={n_hfdc}"
        )

elif args.variant == "F2":
    if not (
        n_freq > 0
        and n_sgor > 0
        and n_hfdc == 0
    ):
        raise RuntimeError(
            f"F2 structure invalid: "
            f"FreqFusion={n_freq}, "
            f"SGOR={n_sgor}, "
            f"HFDC={n_hfdc}"
        )

elif args.variant == "F3":
    if not (
        n_freq > 0
        and n_sgor > 0
        and n_hfdc > 0
    ):
        raise RuntimeError(
            f"F3 structure invalid: "
            f"FreqFusion={n_freq}, "
            f"SGOR={n_sgor}, "
            f"HFDC={n_hfdc}"
        )

else:
    raise RuntimeError(
        f"Unknown variant: {args.variant}"
    )

print(
    f"[PASS] {args.variant} structural gate"
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
print("FORMAL ABLATION TRAINING START")
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

            raw_loss = F.cross_entropy(
                logits,
                gt,
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
                f"scale="
                f"{scale_mean:.3f}"
                f"[{scale_min:.3f},"
                f"{scale_max:.3f}] | "
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
