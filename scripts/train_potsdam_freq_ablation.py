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
DATA_ROOT = Path(
    "/home/jovyan/zzx/projects_zys/raw_extract/Potsdam_unzipped"
)

RGB_ROOT = DATA_ROOT / "2_Ortho_RGB"
DSM_ROOT = DATA_ROOT / "1_DSM" / "1_DSM"
LABEL_ROOT = DATA_ROOT / "5_Labels_for_participants"
NOBOUNDARY_ROOT = (
    DATA_ROOT / "5_Labels_for_participants_no_Boundary"
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
    "6_10", "7_10", "2_12", "3_11", "2_10", "7_8",
    "5_10", "3_12", "5_12", "7_11", "7_9", "6_9",
    "7_7", "4_12", "6_8", "6_12", "6_7", "4_11",
]

TEST_IDS = [
    "4_10", "5_11", "2_11",
    "3_10", "6_11", "7_12",
]

PATCH = 256
TRAIN_BATCH = 8

EPOCHS = 50
STEPS_PER_EPOCH = 1000
TOTAL_STEPS = EPOCHS * STEPS_PER_EPOCH

EVAL_INTERVAL = 500
TEST_STRIDE = 128
INFER_BATCH = 16

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


def potsdam_dsm_name(tile_id):
    a, b = tile_id.split("_")
    return (
        f"dsm_potsdam_"
        f"{int(a):02d}_{int(b):02d}.tif"
    )


def load_train_tile(tile_id):
    optical_path = (
        RGB_ROOT
        / f"top_potsdam_{tile_id}_RGB.tif"
    )

    dsm_path = (
        DSM_ROOT
        / potsdam_dsm_name(tile_id)
    )

    label_path = (
        LABEL_ROOT
        / f"top_potsdam_{tile_id}_label.tif"
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

    # Thesis protocol:
    # independent tile-wise min-max normalization.
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
            f"Train shape mismatch "
            f"tile {tile_id}: "
            f"{optical.shape}, "
            f"{dsm.shape}, "
            f"{gt.shape}"
        )

    return optical, dsm, gt


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
        / f"top_potsdam_{tile_id}_label_noBoundary.tif"
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
            f"Test shape mismatch "
            f"tile {tile_id}: "
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


def preload_all():
    print("\n" + "=" * 100)
    print("PRELOAD POTSDAM TRAIN18 + TEST6 TO RAM")
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
    optical_batch = []
    dsm_batch = []
    gt_batch = []

    for _ in range(TRAIN_BATCH):
        tile_id = random.choice(TRAIN_IDS)

        optical, dsm, gt = train_cache[
            tile_id
        ]

        H, W = gt.shape

        y = random.randint(
            0,
            H - PATCH,
        )

        x = random.randint(
            0,
            W - PATCH,
        )

        op = optical[
            y:y+PATCH,
            x:x+PATCH,
            :
        ]

        ds = dsm[
            y:y+PATCH,
            x:x+PATCH
        ]

        label = gt[
            y:y+PATCH,
            x:x+PATCH
        ]

        # historical flip/mirror
        if random.random() < 0.5:
            op = op[::-1, :, :]
            ds = ds[::-1, :]
            label = label[::-1, :]

        if random.random() < 0.5:
            op = op[:, ::-1, :]
            ds = ds[:, ::-1]
            label = label[:, ::-1]

        optical_batch.append(
            np.ascontiguousarray(
                op.transpose(2, 0, 1)
            )
        )

        dsm_batch.append(
            np.ascontiguousarray(ds)
        )

        gt_batch.append(
            np.ascontiguousarray(label)
        )

    optical_tensor = torch.from_numpy(
        np.stack(
            optical_batch,
            axis=0,
        )
    ).to(
        DEVICE,
        non_blocking=True,
    )

    dsm_tensor = torch.from_numpy(
        np.stack(
            dsm_batch,
            axis=0,
        )
    ).to(
        DEVICE,
        non_blocking=True,
    )

    gt_tensor = torch.from_numpy(
        np.stack(
            gt_batch,
            axis=0,
        ).astype(np.int64)
    ).to(
        DEVICE,
        non_blocking=True,
    )

    return (
        optical_tensor,
        dsm_tensor,
        gt_tensor,
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
    choices=["F0", "F1", "F2", "F3"],
)

args = parser.parse_args()

run_name = (
    "Thesis_Ch4_NoSR_Ablation_"
    f"Potsdam_{args.variant}_seed42"
)

RUN_DIR = (
    ROOT
    / "runs"
    / run_name
)

(RUN_DIR / "checkpoints").mkdir(
    parents=True,
    exist_ok=True,
)

set_seed(SEED)

train_cache, test_cache = preload_all()

print("\nBUILD MODEL")

config = CONFIGS["R50-ViT-B_16"]
config.n_classes = 6
config.n_skip = 3
config.patches.grid = (16, 16)

net = VisionTransformerFreqAblation(
    config,
    img_size=256,
    num_classes=6,
    freq_variant=args.variant,
).to(DEVICE)

optimizer = torch.optim.SGD(
    net.parameters(),
    lr=0.01,
    momentum=0.9,
    weight_decay=5e-4,
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


loss_buffer = []

print("\n" + "=" * 100)
print("FORMAL ABLATION TRAINING START")
print("variant:", args.variant)
print("run:", RUN_DIR)
print("epochs:", EPOCHS)
print("steps/epoch:", STEPS_PER_EPOCH)
print("total steps:", TOTAL_STEPS)
print("eval interval:", EVAL_INTERVAL)
print("=" * 100)

torch.cuda.reset_peak_memory_stats()

training_start = time.time()

for epoch in range(
    start_epoch,
    EPOCHS + 1,
):
    # Explicit implementation of thesis/FTransUNet schedule:
    # epochs 1-24: 1e-2
    # epochs 25-34: 1e-3
    # epochs 35-44: 1e-4
    # epochs 45-50: 1e-5

    if epoch < 25:
        lr = 1e-2
    elif epoch < 35:
        lr = 1e-3
    elif epoch < 45:
        lr = 1e-4
    else:
        lr = 1e-5

    for group in optimizer.param_groups:
        group["lr"] = lr

    print(
        f"\n===== EPOCH "
        f"{epoch:02d}/{EPOCHS} "
        f"LR={lr:.1e} ====="
    )

    net.train()

    for step_in_epoch in range(
        1,
        STEPS_PER_EPOCH + 1,
    ):
        global_step += 1

        step_start = time.time()

        optical, dsm, gt = (
            sample_train_batch(
                train_cache
            )
        )

        optimizer.zero_grad(
            set_to_none=True
        )

        logits = net(
            optical,
            dsm,
        )

        loss = F.cross_entropy(
            logits,
            gt,
        )

        if not torch.isfinite(loss):
            raise RuntimeError(
                f"Non-finite loss "
                f"at {global_step}"
            )

        loss.backward()

        optimizer.step()

        torch.cuda.synchronize()

        loss_value = float(
            loss.detach()
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
            or global_step % 100 == 0
        ):
            allocated = (
                torch.cuda
                .memory_allocated()
                / 1024**3
            )

            print(
                f"step "
                f"{global_step:05d}/"
                f"{TOTAL_STEPS} | "
                f"loss={loss_value:.6f} | "
                f"mean50={mean50:.6f} | "
                f"lr={lr:.1e} | "
                f"GPU={allocated:.2f}G | "
                f"{sec_step:.3f}s"
            )

        # ====================================================
        # Periodic historical evaluation
        # ====================================================

        if (
            global_step
            % EVAL_INTERVAL
            == 0
        ):
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

    # End of epoch:
    # overwrite one resume state only.
    print(
        f"[SAVE] resume state "
        f"after epoch {epoch}"
    )

    save_resume_state(
        net,
        optimizer,
        RUN_DIR,
        epoch,
        global_step,
        registry,
    )


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
