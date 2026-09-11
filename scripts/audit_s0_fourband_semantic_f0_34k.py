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
    "Thesis_Ch4_NoSR_DetPair_F0_"
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


# ============================================================
# S0 semantic-conditioned pre-fusion frequency audit
#
# Read-only:
#   Deterministic paired F0 @ 34k
#
# Capture:
#   Optical root feature BEFORE SE Fusion 0
#   DSM root feature BEFORE SE Fusion 0
#   fused feature AFTER SE Fusion 0
#
# Statistics:
#   - class-conditioned local HF ratio
#   - Optical/DSM spatial HF correlation
#   - Optical/DSM normalized HF discrepancy
#
# FullGT + noBoundary are reported separately.
# ============================================================

import csv
import math
from collections import defaultdict


AUDIT_ROOT = (
    ROOT
    / "records"
    / "fourband_frequency_audit_20260831"
)

AUDIT_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)


CKPT = (
    ROOT
    / "runs"
    / (
        "Thesis_Ch4_NoSR_DetPair_F0_"
        "Vaihingen_F0_seed42_formal160k"
    )
    / "checkpoints"
    / "model_iter_034000.pth"
)

if not CKPT.is_file():
    raise FileNotFoundError(
        CKPT
    )


# ------------------------------------------------------------
# Load exact trained F0
# ------------------------------------------------------------

state = torch.load(
    CKPT,
    map_location="cpu",
)

if (
    isinstance(state, dict)
    and "model" in state
):
    state = state["model"]

net.load_state_dict(
    state,
    strict=True,
)

net.eval()


print()
print("=" * 110)
print("S0 SEMANTIC-CONDITIONED FREQUENCY AUDIT")
print("=" * 110)
print("checkpoint:", CKPT)
print("variant   :", args.variant)


CLASS_NAMES = [
    "Impervious",
    "Building",
    "LowVegetation",
    "Tree",
    "Car",
    "Clutter",
]


# ============================================================
# Hook context
#
# The custom inference function places the current GT crops
# and inverse-overlap weights here immediately before forward.
# ============================================================

hook_context = {
    "full_gt": None,
    "nb_gt": None,
    "weight": None,
}


# ============================================================
# Accumulator
# ============================================================

FEATURE_NAMES = [
    "optical_pre",
    "dsm_pre",
    "fused",
]


class SemanticAccumulator:
    def __init__(self):
        self.energy = defaultdict(
            lambda: {
                "hf": 0.0,
                "base": 0.0,
                "weight": 0.0,
            }
        )

        self.cross = defaultdict(
            lambda: {
                "w": 0.0,
                "x": 0.0,
                "y": 0.0,
                "x2": 0.0,
                "y2": 0.0,
                "xy": 0.0,
                "absdiff": 0.0,
            }
        )

    @staticmethod
    def feature_energy_maps(
        feat,
    ):
        """
        feat:
            [B,C,H,W]

        Returns:
            local HF energy map
            centered base energy map

        Shape:
            [B,1,H,W]
        """

        x = feat.detach().float()

        # Remove per-channel spatial mean.
        centered = (
            x
            - x.mean(
                dim=(-2, -1),
                keepdim=True,
            )
        )

        # Reflect padding avoids artificial zero-padding
        # high-frequency responses around feature borders.
        smooth = F.avg_pool2d(
            F.pad(
                centered,
                (1, 1, 1, 1),
                mode="reflect",
            ),
            kernel_size=3,
            stride=1,
            padding=0,
        )

        hp = (
            centered - smooth
        )

        hf_energy = (
            hp.square()
            .mean(
                dim=1,
                keepdim=True,
            )
        )

        base_energy = (
            centered.square()
            .mean(
                dim=1,
                keepdim=True,
            )
        )

        return (
            hf_energy,
            base_energy,
        )

    @staticmethod
    def resize_to_gt(
        x,
        size,
    ):
        return F.interpolate(
            x,
            size=size,
            mode="bilinear",
            align_corners=False,
        )[:, 0]

    def add_feature(
        self,
        gt_name,
        gt,
        weight,
        feature_name,
        hf_map,
        base_map,
    ):
        H, W = gt.shape[-2:]

        hf = self.resize_to_gt(
            hf_map,
            (H, W),
        )

        base = self.resize_to_gt(
            base_map,
            (H, W),
        )

        for cls in range(N_CLASSES):
            valid = (
                gt == cls
            )

            if not valid.any():
                continue

            w = (
                weight[valid]
                .double()
            )

            hf_v = (
                hf[valid]
                .double()
            )

            base_v = (
                base[valid]
                .double()
            )

            key = (
                gt_name,
                cls,
                feature_name,
            )

            d = self.energy[key]

            d["hf"] += float(
                (hf_v * w).sum().cpu()
            )

            d["base"] += float(
                (base_v * w).sum().cpu()
            )

            d["weight"] += float(
                w.sum().cpu()
            )

    def add_cross_modal(
        self,
        gt_name,
        gt,
        weight,
        optical_hf,
        dsm_hf,
    ):
        """
        Spatial agreement diagnostic.

        Important:
        We do NOT compare Optical/DSM feature channels
        directly, because their channel bases are learned
        independently.

        Instead we compare scalar local-HF energy maps.

        Each modality's HF map is normalized by its own
        patch-wise spatial mean first. Therefore correlation
        and discrepancy describe WHERE HF occurs, not merely
        which modality has the larger absolute magnitude.
        """

        eps = 1e-12

        # Convert energy -> magnitude-like quantity.
        xo = torch.sqrt(
            optical_hf + eps
        )

        xd = torch.sqrt(
            dsm_hf + eps
        )

        xo = (
            xo
            / (
                xo.mean(
                    dim=(-2, -1),
                    keepdim=True,
                )
                + eps
            )
        )

        xd = (
            xd
            / (
                xd.mean(
                    dim=(-2, -1),
                    keepdim=True,
                )
                + eps
            )
        )

        H, W = gt.shape[-2:]

        xo = self.resize_to_gt(
            xo,
            (H, W),
        )

        xd = self.resize_to_gt(
            xd,
            (H, W),
        )

        for cls in range(N_CLASSES):
            valid = (
                gt == cls
            )

            if not valid.any():
                continue

            w = (
                weight[valid]
                .double()
            )

            x = (
                xo[valid]
                .double()
            )

            y = (
                xd[valid]
                .double()
            )

            key = (
                gt_name,
                cls,
            )

            d = self.cross[key]

            d["w"] += float(
                w.sum().cpu()
            )

            d["x"] += float(
                (w * x).sum().cpu()
            )

            d["y"] += float(
                (w * y).sum().cpu()
            )

            d["x2"] += float(
                (w * x * x).sum().cpu()
            )

            d["y2"] += float(
                (w * y * y).sum().cpu()
            )

            d["xy"] += float(
                (w * x * y).sum().cpu()
            )

            d["absdiff"] += float(
                (
                    w
                    * torch.abs(x - y)
                ).sum().cpu()
            )

    @staticmethod
    def weighted_corr(
        d,
    ):
        w = d["w"]

        if w <= 0:
            return float("nan")

        mx = d["x"] / w
        my = d["y"] / w

        vx = (
            d["x2"] / w
            - mx * mx
        )

        vy = (
            d["y2"] / w
            - my * my
        )

        cov = (
            d["xy"] / w
            - mx * my
        )

        if (
            vx <= 1e-12
            or vy <= 1e-12
        ):
            return float("nan")

        return (
            cov
            / math.sqrt(vx * vy)
        )


acc = SemanticAccumulator()


# ============================================================
# Hook SE layer 0
# ============================================================

hybrid = (
    net
    .transformer
    .embeddings
    .hybrid_model
)

se0 = hybrid.se_layer0


def se0_hook(
    module,
    inputs,
    output,
):
    optical = inputs[0]
    dsm = inputs[1]
    fused = output

    full_gt = (
        hook_context["full_gt"]
    )

    nb_gt = (
        hook_context["nb_gt"]
    )

    weight = (
        hook_context["weight"]
    )

    if (
        full_gt is None
        or nb_gt is None
        or weight is None
    ):
        raise RuntimeError(
            "SE0 hook has no GT context"
        )

    o_hf, o_base = (
        acc.feature_energy_maps(
            optical
        )
    )

    d_hf, d_base = (
        acc.feature_energy_maps(
            dsm
        )
    )

    f_hf, f_base = (
        acc.feature_energy_maps(
            fused
        )
    )

    for gt_name, gt in [
        ("FullGT", full_gt),
        ("NB", nb_gt),
    ]:
        acc.add_feature(
            gt_name,
            gt,
            weight,
            "optical_pre",
            o_hf,
            o_base,
        )

        acc.add_feature(
            gt_name,
            gt,
            weight,
            "dsm_pre",
            d_hf,
            d_base,
        )

        acc.add_feature(
            gt_name,
            gt,
            weight,
            "fused",
            f_hf,
            f_base,
        )

        acc.add_cross_modal(
            gt_name,
            gt,
            weight,
            o_hf,
            d_hf,
        )


handle = (
    se0.register_forward_hook(
        se0_hook
    )
)


# ============================================================
# Parallel S0 four-band audit
#
# Decomposition:
#     L = LP(F)
#     H = F - L
#
# LP:
#     3x3 average filter with reflect padding.
#
# This follows the same local-frequency convention used by
# the pre-fusion P1 analysis, while preserving the original
# HF-only audit above as an independent consistency path.
# ============================================================

class FourBandAccumulator:
    def __init__(self):
        # Energy statistics:
        # key = (GT type, class, modality, band)
        self.energy = defaultdict(
            lambda: {
                "sum": 0.0,
                "weight": 0.0,
            }
        )

        # Cross-modal spatial agreement:
        # key = (GT type, class, band)
        self.cross = defaultdict(
            lambda: {
                "w": 0.0,
                "x": 0.0,
                "y": 0.0,
                "x2": 0.0,
                "y2": 0.0,
                "xy": 0.0,
                "absdiff": 0.0,
            }
        )

    @staticmethod
    def band_energy_maps(feat):
        """
        feat:
            [B,C,H,W]

        Returns:
            low_energy  [B,1,H,W]
            high_energy [B,1,H,W]

        Low-frequency component:
            L = AvgPool3x3_reflect(F)

        High-frequency residual:
            H = F - L
        """

        x = feat.detach().float()

        low = F.avg_pool2d(
            F.pad(
                x,
                (1, 1, 1, 1),
                mode="reflect",
            ),
            kernel_size=3,
            stride=1,
            padding=0,
        )

        high = x - low

        low_energy = (
            low.square()
            .mean(
                dim=1,
                keepdim=True,
            )
        )

        high_energy = (
            high.square()
            .mean(
                dim=1,
                keepdim=True,
            )
        )

        return (
            low_energy,
            high_energy,
        )

    @staticmethod
    def resize_to_gt(
        x,
        size,
    ):
        return F.interpolate(
            x,
            size=size,
            mode="bilinear",
            align_corners=False,
        )[:, 0]

    def add_energy(
        self,
        gt_name,
        gt,
        weight,
        modality,
        band,
        energy_map,
    ):
        H, W = gt.shape[-2:]

        e = self.resize_to_gt(
            energy_map,
            (H, W),
        )

        for cls in range(N_CLASSES):
            valid = (
                gt == cls
            )

            if not valid.any():
                continue

            w = (
                weight[valid]
                .double()
            )

            ev = (
                e[valid]
                .double()
            )

            key = (
                gt_name,
                cls,
                modality,
                band,
            )

            d = self.energy[key]

            d["sum"] += float(
                (ev * w).sum().cpu()
            )

            d["weight"] += float(
                w.sum().cpu()
            )

    def add_cross(
        self,
        gt_name,
        gt,
        weight,
        band,
        optical_energy,
        dsm_energy,
    ):
        """
        Compare WHERE frequency-band energy occurs.

        Optical and DSM learned channels have independent
        channel bases, therefore channels are not compared
        directly.

        Energy maps are converted to RMS-like magnitudes and
        normalized by each patch's spatial mean before
        correlation/discrepancy calculation.
        """

        eps = 1e-12

        xo = torch.sqrt(
            optical_energy + eps
        )

        xd = torch.sqrt(
            dsm_energy + eps
        )

        xo = (
            xo
            / (
                xo.mean(
                    dim=(-2, -1),
                    keepdim=True,
                )
                + eps
            )
        )

        xd = (
            xd
            / (
                xd.mean(
                    dim=(-2, -1),
                    keepdim=True,
                )
                + eps
            )
        )

        H, W = gt.shape[-2:]

        xo = self.resize_to_gt(
            xo,
            (H, W),
        )

        xd = self.resize_to_gt(
            xd,
            (H, W),
        )

        for cls in range(N_CLASSES):
            valid = (
                gt == cls
            )

            if not valid.any():
                continue

            w = (
                weight[valid]
                .double()
            )

            x = (
                xo[valid]
                .double()
            )

            y = (
                xd[valid]
                .double()
            )

            key = (
                gt_name,
                cls,
                band,
            )

            d = self.cross[key]

            d["w"] += float(
                w.sum().cpu()
            )

            d["x"] += float(
                (w * x).sum().cpu()
            )

            d["y"] += float(
                (w * y).sum().cpu()
            )

            d["x2"] += float(
                (w * x * x).sum().cpu()
            )

            d["y2"] += float(
                (w * y * y).sum().cpu()
            )

            d["xy"] += float(
                (w * x * y).sum().cpu()
            )

            d["absdiff"] += float(
                (
                    w
                    * torch.abs(x - y)
                ).sum().cpu()
            )

    @staticmethod
    def weighted_corr(d):
        w = d["w"]

        if w <= 0:
            return float("nan")

        mx = d["x"] / w
        my = d["y"] / w

        vx = (
            d["x2"] / w
            - mx * mx
        )

        vy = (
            d["y2"] / w
            - my * my
        )

        cov = (
            d["xy"] / w
            - mx * my
        )

        if (
            vx <= 1e-12
            or vy <= 1e-12
        ):
            return float("nan")

        return (
            cov
            / math.sqrt(
                vx * vy
            )
        )


fourband_acc = FourBandAccumulator()


def se0_fourband_hook(
    module,
    inputs,
    output,
):
    optical = inputs[0]
    dsm = inputs[1]

    full_gt = (
        hook_context["full_gt"]
    )

    nb_gt = (
        hook_context["nb_gt"]
    )

    weight = (
        hook_context["weight"]
    )

    if (
        full_gt is None
        or nb_gt is None
        or weight is None
    ):
        raise RuntimeError(
            "Four-band SE0 hook has no GT context"
        )

    o_lf, o_hf = (
        fourband_acc.band_energy_maps(
            optical
        )
    )

    d_lf, d_hf = (
        fourband_acc.band_energy_maps(
            dsm
        )
    )

    for gt_name, gt in [
        ("FullGT", full_gt),
        ("NB", nb_gt),
    ]:
        fourband_acc.add_energy(
            gt_name,
            gt,
            weight,
            "optical",
            "LF",
            o_lf,
        )

        fourband_acc.add_energy(
            gt_name,
            gt,
            weight,
            "optical",
            "HF",
            o_hf,
        )

        fourband_acc.add_energy(
            gt_name,
            gt,
            weight,
            "dsm",
            "LF",
            d_lf,
        )

        fourband_acc.add_energy(
            gt_name,
            gt,
            weight,
            "dsm",
            "HF",
            d_hf,
        )

        fourband_acc.add_cross(
            gt_name,
            gt,
            weight,
            "LF",
            o_lf,
            d_lf,
        )

        fourband_acc.add_cross(
            gt_name,
            gt,
            weight,
            "HF",
            o_hf,
            d_hf,
        )


handle_fourband = (
    se0.register_forward_hook(
        se0_fourband_hook
    )
)


# ============================================================
# Exact sliding inference + aligned semantic audit
# ============================================================

def infer_tile_semantic(
    net,
    optical,
    dsm,
    full_gt,
    nb_gt,
):
    H, W = optical.shape[:2]

    ys = make_positions(H)
    xs = make_positions(W)

    coords = [
        (y, x)
        for y in ys
        for x in xs
    ]

    # Inverse-overlap weighting:
    # each image pixel contributes approximately once to
    # the semantic feature audit despite sliding-window overlap.
    coverage = np.zeros(
        (H, W),
        dtype=np.float32,
    )

    for y, x in coords:
        coverage[
            y:y+PATCH,
            x:x+PATCH,
        ] += 1.0

    if np.any(
        coverage <= 0
    ):
        raise RuntimeError(
            "Sliding coverage contains zero pixels"
        )

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

            fg = np.stack(
                [
                    full_gt[
                        y:y+PATCH,
                        x:x+PATCH
                    ]
                    for y, x
                    in batch_coords
                ],
                axis=0,
            )

            ng = np.stack(
                [
                    nb_gt[
                        y:y+PATCH,
                        x:x+PATCH
                    ]
                    for y, x
                    in batch_coords
                ],
                axis=0,
            )

            wt = np.stack(
                [
                    1.0
                    / coverage[
                        y:y+PATCH,
                        x:x+PATCH
                    ]
                    for y, x
                    in batch_coords
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

            hook_context[
                "full_gt"
            ] = torch.from_numpy(
                np.ascontiguousarray(fg)
            ).to(
                DEVICE,
                non_blocking=True,
            ).long()

            hook_context[
                "nb_gt"
            ] = torch.from_numpy(
                np.ascontiguousarray(ng)
            ).to(
                DEVICE,
                non_blocking=True,
            ).long()

            hook_context[
                "weight"
            ] = torch.from_numpy(
                np.ascontiguousarray(wt)
            ).to(
                DEVICE,
                non_blocking=True,
            ).float()

            logits = net(
                op,
                ds,
            )

            logits_np = (
                logits
                .detach()
                .cpu()
                .numpy()
            )

            for output, (
                y,
                x,
            ) in zip(
                logits_np,
                batch_coords,
            ):
                score[
                    :,
                    y:y+PATCH,
                    x:x+PATCH,
                ] += output

            del op
            del ds
            del logits

    hook_context[
        "full_gt"
    ] = None

    hook_context[
        "nb_gt"
    ] = None

    hook_context[
        "weight"
    ] = None

    return np.argmax(
        score,
        axis=0,
    ).astype(
        np.uint8
    )


# ============================================================
# Run Test4
# ============================================================

cm_full = np.zeros(
    (N_CLASSES, N_CLASSES),
    dtype=np.int64,
)

cm_nb = np.zeros(
    (N_CLASSES, N_CLASSES),
    dtype=np.int64,
)


print()
print(
    "[RUN] exact Test4 sliding inference "
    "+ S0 semantic frequency audit"
)


for tile_id in TEST_IDS:
    data = test_cache[
        tile_id
    ]

    print(
        "[TILE]",
        tile_id,
    )

    pred = infer_tile_semantic(
        net,
        data["optical"],
        data["dsm"],
        data["full_gt"],
        data["noboundary_gt"],
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


handle.remove()
handle_fourband.remove()


# ============================================================
# Build tables
# ============================================================

rows = []


for gt_name in [
    "FullGT",
    "NB",
]:
    for cls in range(
        N_CLASSES
    ):
        feature_stats = {}

        for feature_name in (
            FEATURE_NAMES
        ):
            d = acc.energy[
                (
                    gt_name,
                    cls,
                    feature_name,
                )
            ]

            ratio = (
                d["hf"]
                / max(
                    d["base"],
                    1e-12,
                )
            )

            feature_stats[
                feature_name
            ] = ratio

        c = acc.cross[
            (
                gt_name,
                cls,
            )
        ]

        corr = (
            acc.weighted_corr(c)
        )

        discrepancy = (
            c["absdiff"]
            / max(
                c["w"],
                1e-12,
            )
        )

        rows.append({
            "gt": gt_name,
            "class_id": cls,
            "class_name": (
                CLASS_NAMES[cls]
            ),
            "optical_hp_ratio": (
                feature_stats[
                    "optical_pre"
                ]
            ),
            "dsm_hp_ratio": (
                feature_stats[
                    "dsm_pre"
                ]
            ),
            "fused_hp_ratio": (
                feature_stats[
                    "fused"
                ]
            ),
            "fusion_minus_optical_pp": (
                (
                    feature_stats[
                        "fused"
                    ]
                    - feature_stats[
                        "optical_pre"
                    ]
                )
                * 100
            ),
            "fusion_minus_dsm_pp": (
                (
                    feature_stats[
                        "fused"
                    ]
                    - feature_stats[
                        "dsm_pre"
                    ]
                )
                * 100
            ),
            "optical_dsm_hf_corr": (
                corr
            ),
            "optical_dsm_hf_discrepancy": (
                discrepancy
            ),
            "effective_weight": (
                c["w"]
            ),
        })


out_csv = (
    AUDIT_ROOT
    / "DetPair_F0_34k_S0_semantic_frequency_legacy_hf.csv"
)


with out_csv.open(
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
    writer.writerows(rows)


# ============================================================
# Print results
# ============================================================

print()
print("=" * 132)
print("S0 SEMANTIC FREQUENCY RESULTS")
print("=" * 132)

for gt_name in [
    "FullGT",
    "NB",
]:
    print()
    print(
        f"--- {gt_name} ---"
    )

    print(
        f"{'Class':16s} "
        f"{'Opt-HF':>10s} "
        f"{'DSM-HF':>10s} "
        f"{'Fused-HF':>10s} "
        f"{'F-O':>9s} "
        f"{'F-D':>9s} "
        f"{'HF-corr':>10s} "
        f"{'HF-disc':>10s}"
    )

    for r in rows:
        if (
            r["gt"]
            != gt_name
        ):
            continue

        print(
            f"{r['class_name']:16s} "
            f"{r['optical_hp_ratio']*100:9.3f}% "
            f"{r['dsm_hp_ratio']*100:9.3f}% "
            f"{r['fused_hp_ratio']*100:9.3f}% "
            f"{r['fusion_minus_optical_pp']:+8.3f} "
            f"{r['fusion_minus_dsm_pp']:+8.3f} "
            f"{r['optical_dsm_hf_corr']:10.4f} "
            f"{r['optical_dsm_hf_discrepancy']:10.4f}"
        )


# ============================================================
# Evaluation consistency
# ============================================================

full = metrics_from_cm(
    cm_full
)

nb = metrics_from_cm(
    cm_nb
)


print()
print("=" * 110)
print("EVALUATION CONSISTENCY GATE")
print("=" * 110)

print(
    "FULL | "
    f"OA={full['OA']*100:.4f} | "
    f"mF1_fg5={full['mF1_fg5']*100:.4f} | "
    f"mIoU_fg5={full['mIoU_fg5']*100:.4f}"
)

print(
    "NB   | "
    f"OA={nb['OA']*100:.4f} | "
    f"mF1_fg5={nb['mF1_fg5']*100:.4f} | "
    f"mIoU_fg5={nb['mIoU_fg5']*100:.4f}"
)

print()
print(
    "[SAVED]",
    out_csv,
)

print(
    "SEMANTIC FREQUENCY AUDIT COMPLETE"
)



# ============================================================
# Four-band semantic result table
# ============================================================

fourband_rows = []

for gt_name in [
    "FullGT",
    "NB",
]:
    for cls in range(
        N_CLASSES
    ):
        values = {}

        for modality in [
            "optical",
            "dsm",
        ]:
            for band in [
                "LF",
                "HF",
            ]:
                d = fourband_acc.energy[
                    (
                        gt_name,
                        cls,
                        modality,
                        band,
                    )
                ]

                values[
                    (
                        modality,
                        band,
                    )
                ] = (
                    d["sum"]
                    / max(
                        d["weight"],
                        1e-12,
                    )
                )

        lf_cross = (
            fourband_acc.cross[
                (
                    gt_name,
                    cls,
                    "LF",
                )
            ]
        )

        hf_cross = (
            fourband_acc.cross[
                (
                    gt_name,
                    cls,
                    "HF",
                )
            ]
        )

        lf_corr = (
            fourband_acc.weighted_corr(
                lf_cross
            )
        )

        hf_corr = (
            fourband_acc.weighted_corr(
                hf_cross
            )
        )

        lf_disc = (
            lf_cross["absdiff"]
            / max(
                lf_cross["w"],
                1e-12,
            )
        )

        hf_disc = (
            hf_cross["absdiff"]
            / max(
                hf_cross["w"],
                1e-12,
            )
        )

        opt_lf = values[
            ("optical", "LF")
        ]

        opt_hf = values[
            ("optical", "HF")
        ]

        dsm_lf = values[
            ("dsm", "LF")
        ]

        dsm_hf = values[
            ("dsm", "HF")
        ]

        fourband_rows.append({
            "gt": gt_name,
            "class_id": cls,
            "class_name": (
                CLASS_NAMES[cls]
            ),

            "optical_lf_energy": (
                opt_lf
            ),
            "optical_hf_energy": (
                opt_hf
            ),
            "optical_hf_lf_ratio": (
                opt_hf
                / max(
                    opt_lf,
                    1e-12,
                )
            ),

            "dsm_lf_energy": (
                dsm_lf
            ),
            "dsm_hf_energy": (
                dsm_hf
            ),
            "dsm_hf_lf_ratio": (
                dsm_hf
                / max(
                    dsm_lf,
                    1e-12,
                )
            ),

            "optical_dsm_lf_corr": (
                lf_corr
            ),
            "optical_dsm_lf_discrepancy": (
                lf_disc
            ),

            "optical_dsm_hf_corr": (
                hf_corr
            ),
            "optical_dsm_hf_discrepancy": (
                hf_disc
            ),

            "effective_weight": (
                hf_cross["w"]
            ),
        })


fourband_csv = (
    AUDIT_ROOT
    / (
        "DetPair_F0_34k_"
        "S0_fourband_semantic_frequency.csv"
    )
)

with fourband_csv.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=list(
            fourband_rows[0].keys()
        ),
    )

    writer.writeheader()

    writer.writerows(
        fourband_rows
    )


print()
print("=" * 178)
print(
    "S0 FOUR-BAND SEMANTIC FREQUENCY RESULTS"
)
print("=" * 178)

for gt_name in [
    "FullGT",
    "NB",
]:
    print()
    print(
        f"--- {gt_name} ---"
    )

    print(
        f"{'Class':16s} "
        f"{'Opt-LF':>11s} "
        f"{'Opt-HF':>11s} "
        f"{'O-H/L':>9s} "
        f"{'DSM-LF':>11s} "
        f"{'DSM-HF':>11s} "
        f"{'D-H/L':>9s} "
        f"{'LF-corr':>9s} "
        f"{'LF-disc':>9s} "
        f"{'HF-corr':>9s} "
        f"{'HF-disc':>9s}"
    )

    for r in fourband_rows:
        if (
            r["gt"]
            != gt_name
        ):
            continue

        print(
            f"{r['class_name']:16s} "
            f"{r['optical_lf_energy']:11.4e} "
            f"{r['optical_hf_energy']:11.4e} "
            f"{r['optical_hf_lf_ratio']:9.4f} "
            f"{r['dsm_lf_energy']:11.4e} "
            f"{r['dsm_hf_energy']:11.4e} "
            f"{r['dsm_hf_lf_ratio']:9.4f} "
            f"{r['optical_dsm_lf_corr']:9.4f} "
            f"{r['optical_dsm_lf_discrepancy']:9.4f} "
            f"{r['optical_dsm_hf_corr']:9.4f} "
            f"{r['optical_dsm_hf_discrepancy']:9.4f}"
        )


print()
print(
    "[SAVED FOUR-BAND CSV]",
    fourband_csv,
)
