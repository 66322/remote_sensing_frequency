import os
import sys
import csv
import json
import argparse
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import numpy as np
import torch
import torch.nn.functional as F
from scipy.ndimage import uniform_filter

import train_rebuild_v1_r02_budget_pilot as r02

OUT_DEFAULT = ROOT / "records" / "rebuild_v1_r02_corruption_screen_20260915"
RUN_DEFAULT = ROOT / "runs" / "rebuild_v1" / "R02_dual_f0_seed42_sched12000_stop12000"
CONFIG_DEFAULT = ROOT / "configs" / "rebuild_v1" / "r02_budget_pilot_12k.json"

CONDITIONS = [
    "clean",
    "dsm_blur5",
    "dsm_down2",
    "dsm_zero",
    "optical_blur5",
    "optical_down2",
]


def down2_restore(x):
    """AA bilinear downsample x2 then bilinear restore to the original grid."""
    h, w = x.shape[:2]
    if x.ndim == 2:
        t = torch.from_numpy(np.ascontiguousarray(x)).float()[None, None]
    elif x.ndim == 3:
        t = torch.from_numpy(np.ascontiguousarray(x.transpose(2, 0, 1))).float()[None]
    else:
        raise ValueError(x.shape)

    small = F.interpolate(
        t,
        size=(max(1, h // 2), max(1, w // 2)),
        mode="bilinear",
        align_corners=False,
        antialias=True,
    )
    restored = F.interpolate(
        small,
        size=(h, w),
        mode="bilinear",
        align_corners=False,
    )
    y = restored.squeeze(0).cpu().numpy()
    if x.ndim == 2:
        y = y[0]
    else:
        y = y.transpose(1, 2, 0)
    return y.astype(np.float32, copy=False)


def apply_condition(optical, dsm, condition):
    op = optical
    ds = dsm

    if condition == "clean":
        pass
    elif condition == "dsm_blur5":
        ds = uniform_filter(dsm, size=5, mode="reflect").astype(np.float32)
    elif condition == "dsm_down2":
        ds = down2_restore(dsm)
    elif condition == "dsm_zero":
        ds = np.zeros_like(dsm, dtype=np.float32)
    elif condition == "optical_blur5":
        op = uniform_filter(optical, size=(5, 5, 1), mode="reflect").astype(np.float32)
    elif condition == "optical_down2":
        op = down2_restore(optical)
    else:
        raise ValueError(condition)

    return np.ascontiguousarray(op), np.ascontiguousarray(ds)


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=CONFIG_DEFAULT)
    ap.add_argument("--run-dir", type=Path, default=RUN_DEFAULT)
    ap.add_argument("--checkpoint", choices=["best", "final"], default="best")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    cfg = r02.read_json(args.config)
    split = r02.read_json(r02.resolve_root_relative(cfg["split_file"]))
    val_ids = list(split["val2"])
    exposed = set(split["historical_exposed_test6"])
    if set(val_ids) & exposed:
        raise RuntimeError("VAL2 overlaps historical TEST6")

    summary_path = args.run_dir / "summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"R02 run not complete: {summary_path}")
    run_summary = r02.read_json(summary_path)
    if int(run_summary.get("global_step", -1)) != int(cfg["schedule"]["stop_at_step"]):
        raise RuntimeError(f"R02 run incomplete: {run_summary}")

    ckpt_path = (
        args.run_dir / "best_model.pth"
        if args.checkpoint == "best"
        else args.run_dir / "last_train_state.pth"
    )
    if not ckpt_path.is_file():
        raise FileNotFoundError(ckpt_path)

    r02.set_seed(int(cfg["seed"]))
    state = torch.load(ckpt_path, map_location="cpu")
    net, _ = r02.build_model(cfg, Path(cfg["pretrain"]), resume_state=state)
    net.eval()

    val_cache = {
        tile_id: r02.load_tile(Path(cfg["data_root"]), tile_id, need_nb=True)
        for tile_id in val_ids
    }

    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    dataset_rows = []
    per_class_rows = []
    raw = {}

    clean_metrics = None
    patch = int(cfg["patch"])
    stride = int(cfg["validation"]["stride"])
    infer_batch = int(cfg["validation"]["inference_batch"])

    print("=" * 100)
    print("REBUILD_V1 R02 VAL2 CORRUPTION SCREEN")
    print("checkpoint:", ckpt_path)
    print("checkpoint_step:", state.get("global_step"))
    print("val2:", val_ids)
    print("TEST6 loaded: False")
    print("conditions:", CONDITIONS)
    print("geometry:", f"patch={patch} stride={stride} batch={infer_batch}")
    print("=" * 100)

    for condition in CONDITIONS:
        print(f"\n--- {condition} ---", flush=True)
        cm_full = np.zeros((r02.N_CLASSES, r02.N_CLASSES), dtype=np.int64)
        cm_nb = np.zeros((r02.N_CLASSES, r02.N_CLASSES), dtype=np.int64)

        for tile_id in val_ids:
            print(" ", tile_id, flush=True)
            d = val_cache[tile_id]
            op, ds = apply_condition(d["optical"], d["dsm"], condition)
            pred = r02.infer_tile(net, op, ds, patch, stride, infer_batch)
            r02.update_cm(cm_full, d["full_gt"], pred)
            r02.update_cm(cm_nb, d["noboundary_gt"], pred)

        full = r02.metrics_from_cm(cm_full)
        nb = r02.metrics_from_cm(cm_nb)
        raw[condition] = {
            "full": full,
            "noboundary": nb,
            "cm_full": cm_full.tolist(),
            "cm_noboundary": cm_nb.tolist(),
        }
        if condition == "clean":
            clean_metrics = raw[condition]

        for split_name, metrics in (("full", full), ("noboundary", nb)):
            clean_miou = clean_metrics[split_name]["mIoU_fg5"] if clean_metrics else metrics["mIoU_fg5"]
            drop_pp = 100.0 * (clean_miou - metrics["mIoU_fg5"])
            dataset_rows.append({
                "condition": condition,
                "split": split_name,
                "OA": metrics["OA"],
                "mF1_fg5": metrics["mF1_fg5"],
                "mIoU_fg5": metrics["mIoU_fg5"],
                "mF1_all6": metrics["mF1_all6"],
                "mIoU_all6": metrics["mIoU_all6"],
                "drop_from_clean_mIoU_fg5_pp": drop_pp,
            })
            for i, class_name in enumerate(r02.CLASS_NAMES):
                per_class_rows.append({
                    "condition": condition,
                    "split": split_name,
                    "class_index": i,
                    "class_name": class_name,
                    "IoU": metrics["per_class_iou"][i],
                })

        print(
            f"FULL mIoU_fg5={100*full['mIoU_fg5']:.4f} | "
            f"NB mIoU_fg5={100*nb['mIoU_fg5']:.4f}"
        )

    write_csv(out_dir / "dataset_metrics.csv", dataset_rows)
    write_csv(out_dir / "per_class_iou.csv", per_class_rows)

    metadata = {
        "protocol": "REBUILD_V1 R02 VAL2 corruption screening",
        "purpose": (
            "Development-only diagnostic of R02 sensitivity to modality degradation. "
            "This cannot establish harmful fusion without matched R01 Optical-only Fusion Gain."
        ),
        "checkpoint": str(ckpt_path),
        "checkpoint_step": int(state.get("global_step", -1)),
        "val_ids": val_ids,
        "historical_test6_loaded": False,
        "conditions": CONDITIONS,
        "blur5": "5x5 mean filter, scipy uniform_filter mode=reflect",
        "down2": "bilinear x2 downsample with antialias=True, then bilinear restore; labels unchanged",
        "patch": patch,
        "stride": stride,
        "infer_batch": infer_batch,
    }
    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump({"metadata": metadata, "results": raw}, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 100)
    print("R02 CORRUPTION SCREEN COMPLETE")
    print("dataset:", out_dir / "dataset_metrics.csv")
    print("per-class:", out_dir / "per_class_iou.csv")
    print("summary:", out_dir / "summary.json")
    print("IMPORTANT: no harmful-fusion claim until matched R01 exists.")
    print("=" * 100)


if __name__ == "__main__":
    main()
