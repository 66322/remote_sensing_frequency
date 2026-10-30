import os
import sys
import csv
import json
import time
import copy
import gc
import argparse
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
DATA_ROOT = Path("/home/jovyan/zzx/projects_zys/raw_extract/Potsdam_unzipped")

RGB_ROOT = DATA_ROOT / "2_Ortho_RGB"
DSM_ROOT = DATA_ROOT / "1_DSM" / "1_DSM"
LABEL_ROOT = DATA_ROOT / "5_Labels_for_participants"
NOBOUNDARY_ROOT = DATA_ROOT / "5_Labels_for_participants_no_Boundary"

DEFAULT_OUT = ROOT / "records" / "e51c_fixed_grid_information_degradation_20260915"

sys.path.insert(0, str(ROOT))

import numpy as np
import torch
from skimage import io
from scipy.ndimage import gaussian_filter, zoom

from model.vitcross_seg_modeling_freq_ablation import CONFIGS
from model.vitcross_seg_modeling_adaptive_multiband_variants import (
    VisionTransformerMultiBandVariant,
)
from model.vitcross_seg_modeling_physical_dsm import (
    VisionTransformerPhysicalDSM,
)


# ============================================================
# Frozen historical checkpoint / inference protocol
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

CLASS_NAMES = [
    "Impervious",
    "Building",
    "LowVegetation",
    "Tree",
    "Car",
    "Clutter",
]

# Information-loss factors corresponding numerically to the old 5->6/7/8/9/10/12 cm
# grid-GSD ratios, but IMPORTANTLY these are NOT new GSD values here.
DEFAULT_FACTORS = [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.4]

PALETTE = {
    (255, 255, 255): 0,
    (0, 0, 255): 1,
    (0, 255, 255): 2,
    (0, 255, 0): 3,
    (255, 255, 0): 4,
    (255, 0, 0): 5,
}
BLACK = (0, 0, 0)

PP_CKPT = (
    ROOT
    / "runs"
    / "potsdam_r4_repro4k_modality_static_seed42"
    / "last_train_state.pth"
)

PH_CKPT = (
    ROOT
    / "runs"
    / "potsdam_physical_dsm_modality_static_seed42"
    / "checkpoints"
    / "model_iter_004000.pth"
)


torch.manual_seed(42)
torch.cuda.manual_seed_all(42)
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
torch.use_deterministic_algorithms(True)


# ============================================================
# Label / data loading
# ============================================================

def convert_full_gt(rgb):
    out = np.full(rgb.shape[:2], IGNORE_INDEX, dtype=np.uint8)
    matched = np.zeros(rgb.shape[:2], dtype=bool)

    for color, idx in PALETTE.items():
        mask = np.all(rgb[..., :3] == np.asarray(color, dtype=rgb.dtype), axis=-1)
        out[mask] = idx
        matched |= mask

    if not matched.all():
        raise RuntimeError(f"FullGT unknown pixels: {int((~matched).sum())}")

    return out


def convert_noboundary_gt(rgb):
    out = np.full(rgb.shape[:2], IGNORE_INDEX, dtype=np.uint8)
    recognized = np.zeros(rgb.shape[:2], dtype=bool)

    for color, idx in PALETTE.items():
        mask = np.all(rgb[..., :3] == np.asarray(color, dtype=rgb.dtype), axis=-1)
        out[mask] = idx
        recognized |= mask

    black = np.all(rgb[..., :3] == np.asarray(BLACK, dtype=rgb.dtype), axis=-1)
    recognized |= black

    if not recognized.all():
        raise RuntimeError(f"NoBoundary unknown pixels: {int((~recognized).sum())}")

    return out


def potsdam_dsm_name(tile_id):
    a, b = tile_id.split("_")
    return f"dsm_potsdam_{int(a):02d}_{int(b):02d}.tif"


def load_test_tile(tile_id):
    optical_path = RGB_ROOT / f"top_potsdam_{tile_id}_RGB.tif"
    dsm_path = DSM_ROOT / potsdam_dsm_name(tile_id)
    full_path = LABEL_ROOT / f"top_potsdam_{tile_id}_label.tif"
    nb_path = NOBOUNDARY_ROOT / f"top_potsdam_{tile_id}_label_noBoundary.tif"

    for p in (optical_path, dsm_path, full_path, nb_path):
        if not p.is_file():
            raise FileNotFoundError(p)

    optical = io.imread(str(optical_path))[..., :3].astype(np.float32) / 255.0

    dsm = io.imread(str(dsm_path)).astype(np.float32)
    dmin = float(dsm.min())
    dmax = float(dsm.max())
    if dmax <= dmin:
        raise RuntimeError(f"DSM zero range: {tile_id}")

    # Frozen historical preprocessing: normalize first, then synthetic degradation.
    dsm = ((dsm - dmin) / (dmax - dmin)).astype(np.float32)

    full_gt = convert_full_gt(io.imread(str(full_path)))
    nb_gt = convert_noboundary_gt(io.imread(str(nb_path)))

    if not (
        optical.shape[:2]
        == dsm.shape
        == full_gt.shape
        == nb_gt.shape
    ):
        raise RuntimeError(
            f"Shape mismatch {tile_id}: "
            f"opt={optical.shape} dsm={dsm.shape} "
            f"full={full_gt.shape} nb={nb_gt.shape}"
        )

    return {
        "optical": optical,
        "dsm": dsm,
        "full_gt": full_gt,
        "noboundary_gt": nb_gt,
    }


# ============================================================
# Fixed-grid information degradation
# ============================================================

def antialias_sigma_for_factor(factor):
    """
    Same anti-alias family used by E51-B when the numerical grid ratio is factor,
    but here the grid is restored and remains native after degradation.

    old E51-B: sigma = 0.5 * (target_gsd/native_gsd - 1)
    therefore sigma = 0.5 * (factor - 1).
    """
    if factor <= 1.0:
        return 0.0
    return max(0.0, 0.5 * (factor - 1.0))


def resize_continuous_exact(x, target_h, target_w, sigma=0.0):
    if x.shape[0] == target_h and x.shape[1] == target_w:
        return x.copy()

    work = x
    if sigma > 0.0:
        if work.ndim == 3:
            work = gaussian_filter(
                work,
                sigma=(sigma, sigma, 0.0),
                mode="reflect",
            )
        else:
            work = gaussian_filter(work, sigma=sigma, mode="reflect")

    fy = float(target_h) / float(work.shape[0])
    fx = float(target_w) / float(work.shape[1])

    if work.ndim == 3:
        y = zoom(
            work,
            zoom=(fy, fx, 1.0),
            order=1,
            mode="reflect",
            prefilter=False,
        )
    else:
        y = zoom(
            work,
            zoom=(fy, fx),
            order=1,
            mode="reflect",
            prefilter=False,
        )

    if y.shape[:2] != (target_h, target_w):
        raise RuntimeError(
            f"resize shape mismatch wanted={(target_h, target_w)} got={y.shape[:2]}"
        )

    return y.astype(np.float32, copy=False)


def degrade_then_restore(x, factor):
    """
    Native grid -> anti-aliased downsample -> bilinear restore to the SAME native grid.

    Labels are never passed through this function.
    """
    if abs(factor - 1.0) < 1e-12:
        return x.copy()

    if factor < 1.0:
        raise ValueError(f"information-loss factor must be >=1, got {factor}")

    H, W = x.shape[:2]
    small_h = max(1, int(round(H / factor)))
    small_w = max(1, int(round(W / factor)))

    sigma = antialias_sigma_for_factor(factor)

    small = resize_continuous_exact(
        x,
        small_h,
        small_w,
        sigma=sigma,
    )

    restored = resize_continuous_exact(
        small,
        H,
        W,
        sigma=0.0,
    )

    if restored.shape[:2] != (H, W):
        raise RuntimeError("fixed-grid restoration failed")

    return restored


def apply_fixed_grid_degradation(data, factor, modality):
    """
    modality:
      joint   -> degrade Optical and DSM
      dsm     -> degrade DSM only
      optical -> degrade Optical only

    FullGT / NoBoundary GT are unchanged in all cases.
    """
    if modality not in {"joint", "dsm", "optical"}:
        raise ValueError(modality)

    optical = data["optical"]
    dsm = data["dsm"]

    if modality in {"joint", "optical"}:
        optical = degrade_then_restore(optical, factor)
    else:
        optical = optical.copy()

    if modality in {"joint", "dsm"}:
        dsm = degrade_then_restore(dsm, factor)
    else:
        dsm = dsm.copy()

    return {
        "optical": optical,
        "dsm": dsm,
        # IMPORTANT: native labels remain unchanged.
        "full_gt": data["full_gt"],
        "noboundary_gt": data["noboundary_gt"],
    }


# ============================================================
# Model loading
# ============================================================

def make_config():
    config = copy.deepcopy(CONFIGS["R50-ViT-B_16"])
    config.n_classes = 6
    config.n_skip = 3
    config.patches.grid = (PATCH // 16, PATCH // 16)
    return config


def build_model(model_name, checkpoint_path):
    config = make_config()

    if model_name == "PP4k":
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
        raise ValueError(model_name)

    if not checkpoint_path.is_file():
        raise FileNotFoundError(checkpoint_path)

    state = torch.load(checkpoint_path, map_location="cpu")
    missing, unexpected = net.load_state_dict(state["model"], strict=True)
    if missing or unexpected:
        raise RuntimeError(
            f"State mismatch {model_name}: missing={missing}, unexpected={unexpected}"
        )

    net = net.to(DEVICE).eval()

    if "metrics" in state:
        expected = state["metrics"]
    elif model_name == "PP4k":
        history_path = (
            ROOT
            / "runs"
            / "potsdam_r4_repro4k_modality_static_seed42"
            / "metrics_history.csv"
        )
        with open(history_path, "r", encoding="utf-8") as f:
            history = list(csv.DictReader(f))
        row = next(r for r in history if int(r["step"]) == 4000)
        expected = {
            "full": {
                "OA": float(row["full_OA"]),
                "mF1_fg5": float(row["full_mF1_fg5"]),
                "mIoU_fg5": float(row["full_mIoU_fg5"]),
                "mF1_all6": float(row["full_mF1_all6"]),
                "mIoU_all6": float(row["full_mIoU_all6"]),
            },
            "noboundary": {
                "OA": float(row["nb_OA"]),
                "mF1_fg5": float(row["nb_mF1_fg5"]),
                "mIoU_fg5": float(row["nb_mIoU_fg5"]),
                "mF1_all6": float(row["nb_mF1_all6"]),
                "mIoU_all6": float(row["nb_mIoU_all6"]),
            },
        }
    else:
        raise RuntimeError(f"No expected metrics stored for {model_name}")

    step = int(state["global_step"])
    if step != 4000:
        raise RuntimeError(f"Expected step 4000 for {model_name}, got {step}")

    print(f"[PASS] loaded {model_name} step={step}")
    return net, expected, step


# ============================================================
# Sliding-window inference
# ============================================================

def make_positions(length):
    positions = list(range(0, length - PATCH + 1, TEST_STRIDE))
    last = length - PATCH
    if positions[-1] != last:
        positions.append(last)
    return positions


def infer_tile(net, model_name, optical, dsm):
    H, W = optical.shape[:2]
    ys = make_positions(H)
    xs = make_positions(W)
    coords = [(y, x) for y in ys for x in xs]

    score = np.zeros((N_CLASSES, H, W), dtype=np.float32)

    with torch.inference_mode():
        for start in range(0, len(coords), INFER_BATCH):
            batch_coords = coords[start : start + INFER_BATCH]

            op = np.stack(
                [
                    optical[y : y + PATCH, x : x + PATCH, :].transpose(2, 0, 1)
                    for y, x in batch_coords
                ],
                axis=0,
            )
            ds = np.stack(
                [dsm[y : y + PATCH, x : x + PATCH] for y, x in batch_coords],
                axis=0,
            )

            op = torch.from_numpy(np.ascontiguousarray(op)).to(
                DEVICE, non_blocking=True
            )
            ds = torch.from_numpy(np.ascontiguousarray(ds)).to(
                DEVICE, non_blocking=True
            )

            # CRITICAL FIXED-GRID RULE:
            # inputs may lose information, but the Potsdam output grid is still native 5 cm.
            # Therefore PH always receives native scale=1.0 in this experiment.
            if model_name == "PH4k":
                net.set_sample_scales([1.0] * len(batch_coords))

            logits = net(op, ds).detach().cpu().numpy()

            for output, (y, x) in zip(logits, batch_coords):
                score[:, y : y + PATCH, x : x + PATCH] += output

            del op, ds, logits

    return np.argmax(score, axis=0).astype(np.uint8)


# ============================================================
# Metrics
# ============================================================

def update_cm(cm, gt, pred):
    valid = (gt != IGNORE_INDEX) & (gt < N_CLASSES)
    g = gt[valid].astype(np.int64)
    p = pred[valid].astype(np.int64)
    index = N_CLASSES * g + p
    cm += np.bincount(index, minlength=N_CLASSES * N_CLASSES).reshape(
        N_CLASSES, N_CLASSES
    )


def metrics_from_cm(cm):
    x = cm.astype(np.float64)
    tp = np.diag(x)
    row = x.sum(axis=1)
    col = x.sum(axis=0)
    fp = col - tp
    fn = row - tp
    union = tp + fp + fn
    total = x.sum()

    oa = tp.sum() / total if total > 0 else np.nan

    f1_denom = 2 * tp + fp + fn
    f1 = np.divide(
        2 * tp,
        f1_denom,
        out=np.full_like(tp, np.nan),
        where=f1_denom > 0,
    )
    iou = np.divide(
        tp,
        union,
        out=np.full_like(tp, np.nan),
        where=union > 0,
    )

    fg_available = np.isfinite(iou[:5])
    all_available = np.isfinite(iou)

    return {
        "OA": float(oa),
        "mF1_fg5": float(np.nanmean(f1[:5])),
        "mIoU_fg5": float(np.nanmean(iou[:5])),
        "mF1_all6": float(np.nanmean(f1)),
        "mIoU_all6": float(np.nanmean(iou)),
        "n_available_fg5": int(fg_available.sum()),
        "n_available_all6": int(all_available.sum()),
        "valid_pixels": int(total),
        "per_class_f1": [None if not np.isfinite(v) else float(v) for v in f1],
        "per_class_iou": [None if not np.isfinite(v) else float(v) for v in iou],
        "per_class_union": [int(v) for v in union],
    }


def native_gate(model_name, result, expected):
    keys = ["OA", "mF1_fg5", "mIoU_fg5", "mF1_all6", "mIoU_all6"]
    max_diff = 0.0

    for split in ("full", "noboundary"):
        for key in keys:
            got = float(result[split][key])
            exp = float(expected[split][key])
            max_diff = max(max_diff, abs(got - exp))

    if max_diff > 1e-7:
        raise RuntimeError(
            f"NATIVE GATE FAIL {model_name}: max_diff={max_diff:.3e}"
        )

    print(f"[PASS] {model_name} native fixed-grid gate max_diff={max_diff:.3e}")


# ============================================================
# One model / one degradation factor
# ============================================================

def evaluate_one(net, model_name, factor, modality):
    cm_full = np.zeros((N_CLASSES, N_CLASSES), dtype=np.int64)
    cm_nb = np.zeros((N_CLASSES, N_CLASSES), dtype=np.int64)
    per_tile = []

    t0 = time.time()

    for tile_index, tile_id in enumerate(TEST_IDS, start=1):
        print(
            f"  [{tile_index}/{len(TEST_IDS)}] {model_name} "
            f"modality={modality} info_factor=x{factor:.2f} tile={tile_id}",
            flush=True,
        )

        native = load_test_tile(tile_id)
        data = apply_fixed_grid_degradation(native, factor, modality)

        # Fixed-grid invariant checks.
        if not (
            data["optical"].shape[:2]
            == native["optical"].shape[:2]
            == data["dsm"].shape
            == native["dsm"].shape
            == data["full_gt"].shape
            == data["noboundary_gt"].shape
        ):
            raise RuntimeError(f"Fixed-grid invariant failed for tile {tile_id}")

        pred = infer_tile(net, model_name, data["optical"], data["dsm"])

        tile_cm_full = np.zeros((N_CLASSES, N_CLASSES), dtype=np.int64)
        tile_cm_nb = np.zeros((N_CLASSES, N_CLASSES), dtype=np.int64)

        update_cm(tile_cm_full, data["full_gt"], pred)
        update_cm(tile_cm_nb, data["noboundary_gt"], pred)

        cm_full += tile_cm_full
        cm_nb += tile_cm_nb

        per_tile.append(
            {
                "tile_id": tile_id,
                "full": metrics_from_cm(tile_cm_full),
                "noboundary": metrics_from_cm(tile_cm_nb),
                "cm_full": tile_cm_full.tolist(),
                "cm_noboundary": tile_cm_nb.tolist(),
            }
        )

        del native, data, pred, tile_cm_full, tile_cm_nb
        gc.collect()

    elapsed = time.time() - t0

    return {
        "model": model_name,
        "checkpoint_step": 4000,
        "modality": modality,
        "information_loss_factor": float(factor),
        "native_grid_gsd_m": NATIVE_GSD_M,
        "ph_inference_scale": 1.0 if model_name == "PH4k" else None,
        "full": metrics_from_cm(cm_full),
        "noboundary": metrics_from_cm(cm_nb),
        "cm_full": cm_full.tolist(),
        "cm_noboundary": cm_nb.tolist(),
        "per_tile": per_tile,
        "seconds": float(elapsed),
    }


# ============================================================
# Output tables
# ============================================================

def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_tables(progress, out_dir):
    dataset_rows = []
    per_tile_rows = []
    per_class_rows = []

    ordered = sorted(
        progress.values(),
        key=lambda r: (
            r["modality"],
            float(r["information_loss_factor"]),
            r["model"],
        ),
    )

    for r in ordered:
        for split in ("full", "noboundary"):
            m = r[split]
            dataset_rows.append(
                {
                    "modality": r["modality"],
                    "information_loss_factor": r["information_loss_factor"],
                    "model": r["model"],
                    "checkpoint_step": r["checkpoint_step"],
                    "split": split,
                    "native_grid_gsd_m": r["native_grid_gsd_m"],
                    "ph_inference_scale": r["ph_inference_scale"],
                    "OA": m["OA"],
                    "mF1_fg5": m["mF1_fg5"],
                    "mIoU_fg5": m["mIoU_fg5"],
                    "mF1_all6": m["mF1_all6"],
                    "mIoU_all6": m["mIoU_all6"],
                    "valid_pixels": m["valid_pixels"],
                    "seconds": r["seconds"],
                }
            )

            for class_idx, class_name in enumerate(CLASS_NAMES):
                per_class_rows.append(
                    {
                        "modality": r["modality"],
                        "information_loss_factor": r["information_loss_factor"],
                        "model": r["model"],
                        "split": split,
                        "class_index": class_idx,
                        "class_name": class_name,
                        "IoU": m["per_class_iou"][class_idx],
                        "F1": m["per_class_f1"][class_idx],
                        "union_pixels": m["per_class_union"][class_idx],
                    }
                )

        for tile in r["per_tile"]:
            for split in ("full", "noboundary"):
                m = tile[split]
                per_tile_rows.append(
                    {
                        "modality": r["modality"],
                        "information_loss_factor": r["information_loss_factor"],
                        "model": r["model"],
                        "tile_id": tile["tile_id"],
                        "split": split,
                        "OA": m["OA"],
                        "mIoU_fg5": m["mIoU_fg5"],
                        "mIoU_all6": m["mIoU_all6"],
                        "n_available_fg5": m["n_available_fg5"],
                        "n_available_all6": m["n_available_all6"],
                        "valid_pixels": m["valid_pixels"],
                    }
                )

    write_csv(out_dir / "dataset_metrics.csv", dataset_rows)
    write_csv(out_dir / "per_tile_metrics.csv", per_tile_rows)
    write_csv(out_dir / "per_class_metrics.csv", per_class_rows)

    # Paired PP4k vs PH4k dataset comparison where both are available.
    paired_rows = []
    groups = sorted(
        {
            (r["modality"], float(r["information_loss_factor"]))
            for r in progress.values()
        }
    )

    for modality, factor in groups:
        key_pp = f"PP4k__{modality}__x{factor:.4f}"
        key_ph = f"PH4k__{modality}__x{factor:.4f}"
        if key_pp not in progress or key_ph not in progress:
            continue

        pp = progress[key_pp]
        ph = progress[key_ph]

        for split in ("full", "noboundary"):
            ppm = pp[split]
            phm = ph[split]
            paired_rows.append(
                {
                    "modality": modality,
                    "information_loss_factor": factor,
                    "split": split,
                    "PP4k_mIoU_fg5": ppm["mIoU_fg5"],
                    "PH4k_mIoU_fg5": phm["mIoU_fg5"],
                    "PH_minus_PP_mIoU_fg5_pp": 100.0
                    * (phm["mIoU_fg5"] - ppm["mIoU_fg5"]),
                    "PP4k_OA": ppm["OA"],
                    "PH4k_OA": phm["OA"],
                    "PH_minus_PP_OA_pp": 100.0 * (phm["OA"] - ppm["OA"]),
                }
            )

    write_csv(out_dir / "paired_pp4k_ph4k.csv", paired_rows)


# ============================================================
# Main / resumable execution
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--modality",
        choices=["joint", "dsm", "optical"],
        default="joint",
        help="which input modality receives fixed-grid information degradation",
    )
    parser.add_argument(
        "--factors",
        type=float,
        nargs="+",
        default=DEFAULT_FACTORS,
        help=(
            "information-loss factors >=1. These are downsample/restore factors, "
            "NOT new GSD values"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="recompute keys already present in progress.json",
    )
    args = parser.parse_args()

    factors = [float(x) for x in args.factors]
    if any(x < 1.0 for x in factors):
        raise ValueError(f"all factors must be >=1: {factors}")

    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    progress_path = out_dir / "progress.json"

    if progress_path.is_file():
        with open(progress_path, "r", encoding="utf-8") as f:
            progress = json.load(f)
        print(f"[RESUME] loaded {len(progress)} completed evaluations from {progress_path}")
    else:
        progress = {}

    print("=" * 100)
    print("E51-C FIXED-GRID INFORMATION DEGRADATION")
    print("=" * 100)
    print("modality:", args.modality)
    print("factors:", factors)
    print("native grid GSD remains:", NATIVE_GSD_M)
    print("PH inference scale is fixed at 1.0 for every degradation factor")
    print("labels/output/sliding-window grid remain unchanged")
    print("output:", out_dir)

    pp_net, pp_expected, pp_step = build_model("PP4k", PP_CKPT)
    ph_net, ph_expected, ph_step = build_model("PH4k", PH_CKPT)

    models = [
        ("PP4k", pp_net, pp_expected, pp_step),
        ("PH4k", ph_net, ph_expected, ph_step),
    ]

    for factor in factors:
        for model_name, net, expected, step in models:
            key = f"{model_name}__{args.modality}__x{factor:.4f}"

            if key in progress and not args.force:
                print(f"[SKIP] {key} already complete")
                continue

            print()
            print("#" * 100)
            print(f"RUN {key}")
            print("#" * 100)

            result = evaluate_one(
                net=net,
                model_name=model_name,
                factor=factor,
                modality=args.modality,
            )

            if abs(factor - 1.0) < 1e-12:
                native_gate(model_name, result, expected)

            if int(result["checkpoint_step"]) != int(step):
                raise RuntimeError("checkpoint step bookkeeping mismatch")

            progress[key] = result

            # Save after EVERY expensive model/factor evaluation.
            with open(progress_path, "w", encoding="utf-8") as f:
                json.dump(progress, f, indent=2, ensure_ascii=False)

            build_tables(progress, out_dir)

            nb = result["noboundary"]
            full = result["full"]
            print(
                f"[DONE] {key} | "
                f"FULL mIoU_fg5={100*full['mIoU_fg5']:.4f} | "
                f"NB mIoU_fg5={100*nb['mIoU_fg5']:.4f} | "
                f"{result['seconds']:.1f}s"
            )

    build_tables(progress, out_dir)

    metadata = {
        "protocol": "E51-C fixed-grid information degradation",
        "warning": (
            "information_loss_factor is a downsample-restore factor on the native grid; "
            "it must not be reported as a new GSD"
        ),
        "native_grid_gsd_m": NATIVE_GSD_M,
        "labels_resampled": False,
        "output_grid_changed": False,
        "sliding_window_grid_changed": False,
        "ph_inference_scale_rule": "always 1.0 on native Potsdam grid",
        "degradation_order": (
            "raw DSM -> tile min-max normalization -> fixed-grid degradation -> network"
        ),
        "modality": args.modality,
        "requested_factors": factors,
        "pp_checkpoint": str(PP_CKPT),
        "ph_checkpoint": str(PH_CKPT),
        "pp_checkpoint_step": pp_step,
        "ph_checkpoint_step": ph_step,
        "test_ids": TEST_IDS,
        "patch": PATCH,
        "stride": TEST_STRIDE,
        "infer_batch": INFER_BATCH,
    }
    with open(out_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 100)
    print("E51-C COMPLETE FOR REQUESTED KEYS")
    print("progress:", progress_path)
    print("dataset table:", out_dir / "dataset_metrics.csv")
    print("paired table:", out_dir / "paired_pp4k_ph4k.csv")
    print("per-tile table:", out_dir / "per_tile_metrics.csv")
    print("per-class table:", out_dir / "per_class_metrics.csv")
    print("=" * 100)


if __name__ == "__main__":
    main()
