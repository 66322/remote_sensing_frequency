import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import numpy as np
import torch
from scipy import ndimage

import train_rebuild_v1_r01_optical_only as r01
import train_rebuild_v1_r02_budget_pilot as r02
from eval_rebuild_v1_dual_robust_conditions import down_restore


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def validate_run(run_dir):
    summary_path = run_dir / "summary.json"
    checkpoint = run_dir / "best_model.pth"
    if not summary_path.is_file() or not checkpoint.is_file():
        raise FileNotFoundError(f"incomplete run: {run_dir}")
    summary = r02.read_json(summary_path)
    if summary.get("test6_loaded") is not False or int(summary.get("global_step", -1)) != 16000:
        raise RuntimeError(f"run safety/completeness failed: {run_dir}")
    return checkpoint


def semantic_boundary(gt, radius):
    valid = gt != r01.IGNORE_INDEX
    edge = np.zeros(gt.shape, dtype=bool)
    edge[1:, :] |= valid[1:, :] & valid[:-1, :] & (gt[1:, :] != gt[:-1, :])
    edge[:-1, :] |= valid[:-1, :] & valid[1:, :] & (gt[:-1, :] != gt[1:, :])
    edge[:, 1:] |= valid[:, 1:] & valid[:, :-1] & (gt[:, 1:] != gt[:, :-1])
    edge[:, :-1] |= valid[:, :-1] & valid[:, 1:] & (gt[:, :-1] != gt[:, 1:])
    return ndimage.binary_dilation(edge, iterations=radius) & valid


def update_masked(cm, gt, pred, mask):
    masked = gt.copy()
    masked[~mask] = r01.IGNORE_INDEX
    r02.update_cm(cm, masked, pred)


def rows_from_cm(meta, cm):
    out = []
    for cls, name in enumerate(r02.CLASS_NAMES):
        tp = int(cm[cls, cls]); support = int(cm[cls].sum()); predicted = int(cm[:, cls].sum())
        precision = tp / predicted if predicted else float("nan")
        recall = tp / support if support else float("nan")
        union = support + predicted - tp
        iou = tp / union if union else float("nan")
        f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else float("nan")
        out.append({**meta, "class_index": cls, "class_name": name, "support": support,
                    "precision": precision, "recall": recall, "F1": f1, "IoU": iou})
    return out


def object_rows(seed, model, condition, tile, gt, pred, thresholds):
    rows = []
    for cls, name in enumerate(r02.CLASS_NAMES[:5]):
        labels, count = ndimage.label(gt == cls, structure=np.ones((3, 3), dtype=np.uint8))
        if not count:
            continue
        areas = np.bincount(labels.ravel())[1:]
        boxes = ndimage.find_objects(labels)
        q25, q75 = thresholds[name]
        for obj_id, area in enumerate(areas, 1):
            box = boxes[obj_id - 1]
            if box is None:
                continue
            local_object = labels[box] == obj_id
            correct_fraction = float(np.mean(pred[box][local_object] == cls))
            size = "small" if area <= q25 else "large" if area >= q75 else "medium"
            rows.append({"seed": seed, "model": model, "condition": condition, "tile": tile,
                         "class_name": name, "object_id": obj_id, "area": int(area), "size_bin": size,
                         "correct_fraction": correct_fraction, "recalled_at_50pct": int(correct_fraction >= 0.5)})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, choices=[17, 42], required=True)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    cfg1 = r02.read_json(ROOT / "configs/rebuild_v1/r01_optical_only_16k.json")
    cfg5 = r02.read_json(ROOT / "configs/rebuild_v1/r05_quality_plus_dropout_16k.json")
    split = r02.read_json(ROOT / cfg5["split_file"])
    ids = list(split["val2"][:1] if args.smoke else split["val2"])
    if set(ids) & set(split["historical_exposed_test6"]):
        raise RuntimeError("Val2/Test6 overlap")
    run1 = ROOT / f"runs/rebuild_v1/R01_optical_only_seed{args.seed}_sched16000_stop16000"
    run5 = ROOT / f"runs/rebuild_v1/R05_dual_f0_quality_plus_dropout_seed{args.seed}_sched16000_stop16000"
    c1, c5 = validate_run(run1), validate_run(run5)
    s1, s5 = torch.load(c1, map_location="cpu"), torch.load(c5, map_location="cpu")
    n1, _, _ = r01.build_model(cfg1, Path(cfg1["pretrain"]), resume_state=s1)
    n5, _ = r02.build_model(cfg5, Path(cfg5["pretrain"]), resume_state=s5)
    n1.eval(); n5.eval()

    bins_path = ROOT / "records/rebuild_v1_d7_data_sampling_20260922/component_area_quantiles.csv"
    if not bins_path.is_file():
        raise FileNotFoundError("Run D7 data audit before semantic error audit")
    with bins_path.open(newline="", encoding="utf-8") as f:
        thresholds = {r["class_name"]: (float(r["area_q25"]), float(r["area_q75"])) for r in csv.DictReader(f)}

    patch = int(cfg5["patch"]); stride = int(cfg5["validation"]["stride"])
    batch = int(cfg5["validation"]["inference_batch"])
    cms = {}; per_class_rows = []; object_detail = []
    per_tile_dataset_rows = []; per_tile_class_rows = []
    conditions = ("clean",) if args.smoke else ("clean", "dsm_down8", "dsm_zero")
    for tile in ids:
        d = r02.load_tile(Path(cfg5["data_root"]), tile, need_nb=True)
        pred1 = r01.infer_tile(n1, d["optical"], patch, stride, batch)
        predictions = {("R01", condition): pred1 for condition in conditions}
        for condition in conditions:
            dsm = d["dsm"] if condition == "clean" else (
                down_restore(d["dsm"], 8) if condition == "dsm_down8" else np.zeros_like(d["dsm"])
            )
            predictions[("R05", condition)] = r02.infer_tile(n5, d["optical"], dsm, patch, stride, batch)
        for (model, condition), pred in predictions.items():
            regions = {"full": d["full_gt"] != r01.IGNORE_INDEX,
                       "noboundary": d["noboundary_gt"] != r01.IGNORE_INDEX}
            for radius in (1, 3, 5):
                regions[f"semantic_boundary_r{radius}"] = semantic_boundary(d["full_gt"], radius)
                regions[f"semantic_interior_r{radius}"] = (d["full_gt"] != r01.IGNORE_INDEX) & ~regions[f"semantic_boundary_r{radius}"]
            for region, mask in regions.items():
                gt = d["noboundary_gt"] if region == "noboundary" else d["full_gt"]
                key = (model, condition, region)
                cms.setdefault(key, np.zeros((r02.N_CLASSES, r02.N_CLASSES), dtype=np.int64))
                tile_cm = np.zeros((r02.N_CLASSES, r02.N_CLASSES), dtype=np.int64)
                update_masked(tile_cm, gt, pred, mask)
                cms[key] += tile_cm
                tm = r02.metrics_from_cm(tile_cm)
                tile_meta = {"seed": args.seed, "model": model, "condition": condition,
                             "region": region, "tile": tile}
                per_tile_dataset_rows.append({**tile_meta, "OA": tm["OA"],
                                              "mF1_fg5": tm["mF1_fg5"],
                                              "mIoU_fg5": tm["mIoU_fg5"],
                                              "pixels": int(tile_cm.sum())})
                per_tile_class_rows.extend(rows_from_cm(tile_meta, tile_cm))
            object_detail.extend(object_rows(args.seed, model, condition, tile, d["full_gt"], pred, thresholds))

    dataset_rows = []
    for (model, condition, region), cm in sorted(cms.items()):
        m = r02.metrics_from_cm(cm)
        meta = {"seed": args.seed, "model": model, "condition": condition, "region": region}
        dataset_rows.append({**meta, "OA": m["OA"], "mF1_fg5": m["mF1_fg5"], "mIoU_fg5": m["mIoU_fg5"], "pixels": int(cm.sum())})
        per_class_rows.extend(rows_from_cm(meta, cm))
    grouped = {}
    for row in object_detail:
        key = tuple(row[k] for k in ("seed", "model", "condition", "class_name", "size_bin"))
        grouped.setdefault(key, []).append(row)
    object_summary = []
    for key, rows in grouped.items():
        seed, model, condition, cls, size = key
        object_summary.append({"seed": seed, "model": model, "condition": condition, "class_name": cls,
                               "size_bin": size, "objects": len(rows),
                               "mean_correct_fraction": float(np.mean([r["correct_fraction"] for r in rows])),
                               "recall_at_50pct": float(np.mean([r["recalled_at_50pct"] for r in rows]))})
    out = args.out or ROOT / (f"records/rebuild_v1_d7_semantic_errors_seed{args.seed}_smoke_20260922" if args.smoke else f"records/rebuild_v1_d7_semantic_errors_seed{args.seed}_20260922")
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "dataset_region_metrics.csv", dataset_rows)
    write_csv(out / "per_class_metrics.csv", per_class_rows)
    write_csv(out / "per_tile_region_metrics.csv", per_tile_dataset_rows)
    write_csv(out / "per_tile_class_metrics.csv", per_tile_class_rows)
    write_csv(out / "object_size_summary.csv", object_summary)
    write_csv(out / "object_detail.csv", object_detail)
    (out / "summary.json").write_text(json.dumps({"recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "experiment_id": "D7_SEMANTIC_ERROR_AUDIT", "seed": args.seed, "smoke": args.smoke,
        "val_ids": ids, "historical_test6_loaded": False, "conditions": conditions,
        "semantic_boundary_radii_pixels": [1, 3, 5], "object_size_bins": "Train16 per-class q25/q75"}, indent=2) + "\n", encoding="utf-8")
    print("D7 SEMANTIC ERROR AUDIT COMPLETE", out)


if __name__ == "__main__":
    main()
