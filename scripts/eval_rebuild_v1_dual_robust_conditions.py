import os
import sys
import csv
import json
import argparse
from datetime import datetime
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

CONDITIONS = [
    "clean",
    "dsm_blur5",
    "dsm_down2",
    "dsm_down4",
    "dsm_down8",
    "dsm_zero",
    "optical_blur5",
    "optical_down2",
    "optical_zero",
]


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def down_restore(x, factor):
    h, w = x.shape[:2]
    if x.ndim == 2:
        t = torch.from_numpy(np.ascontiguousarray(x)).float()[None, None]
    else:
        t = torch.from_numpy(np.ascontiguousarray(x.transpose(2, 0, 1))).float()[None]
    small = F.interpolate(
        t,
        size=(max(1, h // factor), max(1, w // factor)),
        mode="bilinear",
        align_corners=False,
        antialias=True,
    )
    restored = F.interpolate(small, size=(h, w), mode="bilinear", align_corners=False)
    y = restored.squeeze(0).cpu().numpy()
    if x.ndim == 2:
        y = y[0]
    else:
        y = y.transpose(1, 2, 0)
    return y.astype(np.float32, copy=False)


def apply_condition(optical, dsm, condition):
    op, ds = optical, dsm
    if condition == "clean":
        pass
    elif condition == "dsm_blur5":
        ds = uniform_filter(dsm, size=5, mode="reflect").astype(np.float32)
    elif condition.startswith("dsm_down"):
        ds = down_restore(dsm, int(condition.replace("dsm_down", "")))
    elif condition == "dsm_zero":
        ds = np.zeros_like(dsm, dtype=np.float32)
    elif condition == "optical_blur5":
        op = uniform_filter(optical, size=(5, 5, 1), mode="reflect").astype(np.float32)
    elif condition == "optical_down2":
        op = down_restore(optical, 2)
    elif condition == "optical_zero":
        op = np.zeros_like(optical, dtype=np.float32)
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
    ap.add_argument("--variant", choices=["R03", "R04"], required=True)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    if args.variant == "R03":
        config = ROOT / "configs/rebuild_v1/r03_quality_corruption_16k.json"
        run_dir = ROOT / "runs/rebuild_v1/R03_dual_f0_quality_corruption_seed42_sched16000_stop16000"
        default_out = ROOT / "records/rebuild_v1_r03_robust_eval_20260916"
    else:
        config = ROOT / "configs/rebuild_v1/r04_modality_dropout_16k.json"
        run_dir = ROOT / "runs/rebuild_v1/R04_dual_f0_modality_dropout_seed42_sched16000_stop16000"
        default_out = ROOT / "records/rebuild_v1_r04_robust_eval_20260916"

    cfg = r02.read_json(config)
    summary_path = run_dir / "summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(summary_path)
    run_summary = r02.read_json(summary_path)
    if int(run_summary.get("global_step", -1)) != 16000:
        raise RuntimeError(f"incomplete {args.variant}: {run_summary}")
    if run_summary.get("test6_loaded") is not False:
        raise RuntimeError("TEST6 safety flag failed")

    split = r02.read_json(r02.resolve_root_relative(cfg["split_file"]))
    val_ids = list(split["val2"])
    if set(val_ids) & set(split["historical_exposed_test6"]):
        raise RuntimeError("VAL2 overlaps TEST6")

    state = torch.load(run_dir / "best_model.pth", map_location="cpu")
    net, _ = r02.build_model(cfg, Path(cfg["pretrain"]), resume_state=state)
    net.eval()
    val_cache = {
        tile: r02.load_tile(Path(cfg["data_root"]), tile, need_nb=True)
        for tile in val_ids
    }

    patch = int(cfg["patch"])
    stride = int(cfg["validation"]["stride"])
    infer_batch = int(cfg["validation"]["inference_batch"])
    out = args.out or default_out
    out.mkdir(parents=True, exist_ok=True)

    dataset_rows, per_class_rows, per_tile_rows = [], [], []
    raw = {}
    clean = None
    for condition in CONDITIONS:
        print(f"--- {args.variant} {condition} ---", flush=True)
        cm_full = np.zeros((r02.N_CLASSES, r02.N_CLASSES), dtype=np.int64)
        cm_nb = np.zeros_like(cm_full)
        tile_raw = {}
        for tile in val_ids:
            d = val_cache[tile]
            op, ds = apply_condition(d["optical"], d["dsm"], condition)
            pred = r02.infer_tile(net, op, ds, patch, stride, infer_batch)
            tile_cm_full = np.zeros_like(cm_full)
            tile_cm_nb = np.zeros_like(cm_nb)
            r02.update_cm(tile_cm_full, d["full_gt"], pred)
            r02.update_cm(tile_cm_nb, d["noboundary_gt"], pred)
            cm_full += tile_cm_full
            cm_nb += tile_cm_nb
            tf = r02.metrics_from_cm(tile_cm_full)
            tn = r02.metrics_from_cm(tile_cm_nb)
            tile_raw[tile] = {
                "full": tf,
                "noboundary": tn,
                "cm_full": tile_cm_full.tolist(),
                "cm_noboundary": tile_cm_nb.tolist(),
            }
            for split_name, tm in (("full", tf), ("noboundary", tn)):
                per_tile_rows.append({
                    "condition": condition,
                    "tile": tile,
                    "split": split_name,
                    "OA": tm["OA"],
                    "mIoU_fg5": tm["mIoU_fg5"],
                })

        full = r02.metrics_from_cm(cm_full)
        nb = r02.metrics_from_cm(cm_nb)
        raw[condition] = {
            "full": full,
            "noboundary": nb,
            "cm_full": cm_full.tolist(),
            "cm_noboundary": cm_nb.tolist(),
            "per_tile": tile_raw,
        }
        if condition == "clean":
            clean = raw[condition]

        for split_name, metrics in (("full", full), ("noboundary", nb)):
            clean_m = clean[split_name]["mIoU_fg5"]
            dataset_rows.append({
                "condition": condition,
                "split": split_name,
                "OA": metrics["OA"],
                "mF1_fg5": metrics["mF1_fg5"],
                "mIoU_fg5": metrics["mIoU_fg5"],
                "mIoU_all6": metrics["mIoU_all6"],
                "drop_from_clean_mIoU_fg5_pp": 100.0 * (clean_m - metrics["mIoU_fg5"]),
            })
            for i, name in enumerate(r02.CLASS_NAMES):
                per_class_rows.append({
                    "condition": condition,
                    "split": split_name,
                    "class_index": i,
                    "class_name": name,
                    "IoU": metrics["per_class_iou"][i],
                })
        print(f"NB mIoU_fg5={100*nb['mIoU_fg5']:.4f}")

    write_csv(out / "dataset_metrics.csv", dataset_rows)
    write_csv(out / "per_class_iou.csv", per_class_rows)
    write_csv(out / "per_tile_metrics.csv", per_tile_rows)
    payload = {
        "recorded_at": now_iso(),
        "variant": args.variant,
        "checkpoint": str(run_dir / "best_model.pth"),
        "checkpoint_step": int(state.get("global_step", -1)),
        "val_ids": val_ids,
        "historical_test6_loaded": False,
        "conditions": CONDITIONS,
        "geometry": {"patch": patch, "stride": stride, "inference_batch": infer_batch},
        "results": raw,
    }
    with open(out / "summary.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"{args.variant} ROBUST EVAL COMPLETE: {out}")


if __name__ == "__main__":
    main()
