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

import train_rebuild_v1_r01_optical_only as r01
import train_rebuild_v1_r02_budget_pilot as r02
from eval_rebuild_v1_dual_robust_conditions import down_restore
from eval_rebuild_v1_local_failure_diagnostics import (
    apply_condition as apply_local_condition,
    condition_specs as local_condition_specs,
)


METHODS = ("R01_optical", "R05_dual", "condition_rule", "pixel_oracle")
SPLITS = ("full", "noboundary")


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def condition_specs():
    local = local_condition_specs()
    clean = local[0]
    return [
        clean,
        {"name": "dsm_zero", "family": "D4_global_missing"},
        {"name": "dsm_down8", "family": "D4_global_down8"},
        *local[1:],
    ]


def apply_condition(dsm, spec):
    if spec["family"] == "D4_global_missing":
        return np.zeros_like(dsm, dtype=np.float32), np.ones(dsm.shape, dtype=bool)
    if spec["family"] == "D4_global_down8":
        return down_restore(dsm, 8), np.ones(dsm.shape, dtype=bool)
    return apply_local_condition(dsm, spec)


def update(cm, gt, pred, mask=None):
    if mask is not None:
        gt = np.where(mask, gt, r02.IGNORE_INDEX)
    r02.update_cm(cm, gt, pred)


def select_prediction(optical_pred, dual_pred, spec, local_mask):
    if spec["family"] == "D4_global_missing":
        return optical_pred
    if spec["family"] == "D1_local_missing":
        return np.where(local_mask, optical_pred, dual_pred).astype(np.uint8)
    return dual_pred


def oracle_prediction(gt, optical_pred, dual_pred):
    return np.where(
        dual_pred == gt,
        dual_pred,
        np.where(optical_pred == gt, optical_pred, dual_pred),
    ).astype(np.uint8)


def run_paths(seed):
    return {
        "R01": ROOT / "runs/rebuild_v1" / f"R01_optical_only_seed{seed}_sched16000_stop16000",
        "R05": ROOT / "runs/rebuild_v1" / f"R05_dual_f0_quality_plus_dropout_seed{seed}_sched16000_stop16000",
    }


def validate_run(run_dir, expected_step=16000):
    summary_path = run_dir / "summary.json"
    checkpoint = run_dir / "best_model.pth"
    if not summary_path.is_file() or not checkpoint.is_file():
        raise FileNotFoundError(f"missing completed run artifacts: {run_dir}")
    summary = r02.read_json(summary_path)
    if int(summary.get("global_step", -1)) != expected_step:
        raise RuntimeError(f"incomplete run: {summary_path}")
    if summary.get("test6_loaded") is not False:
        raise RuntimeError(f"TEST6 safety flag failed: {summary_path}")
    return summary, checkpoint


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, choices=[17, 42], required=True)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    paths = run_paths(args.seed)
    r01_summary, r01_checkpoint = validate_run(paths["R01"])
    r05_summary, r05_checkpoint = validate_run(paths["R05"])
    r01_cfg = r02.read_json(ROOT / "configs/rebuild_v1/r01_optical_only_16k.json")
    r05_cfg = r02.read_json(ROOT / "configs/rebuild_v1/r05_quality_plus_dropout_16k.json")
    split = r02.read_json(r02.resolve_root_relative(r05_cfg["split_file"]))
    val_ids = list(split["val2"])
    if set(val_ids) & set(split["historical_exposed_test6"]):
        raise RuntimeError("VAL2 overlaps historical TEST6")
    if args.smoke:
        val_ids = val_ids[:1]

    r01_state = torch.load(r01_checkpoint, map_location="cpu")
    optical_net, _, _ = r01.build_model(
        r01_cfg, Path(r01_cfg["pretrain"]), resume_state=r01_state
    )
    r05_state = torch.load(r05_checkpoint, map_location="cpu")
    dual_net, _ = r02.build_model(
        r05_cfg, Path(r05_cfg["pretrain"]), resume_state=r05_state
    )
    optical_net.eval()
    dual_net.eval()

    cache = {
        tile: r02.load_tile(Path(r05_cfg["data_root"]), tile, need_nb=True)
        for tile in val_ids
    }
    patch = int(r05_cfg["patch"])
    stride = int(r05_cfg["validation"]["stride"])
    infer_batch = int(r05_cfg["validation"]["inference_batch"])
    optical_predictions = {}
    for tile, item in cache.items():
        print(f"--- R01 cached inference tile={tile} ---", flush=True)
        optical_predictions[tile] = r01.infer_tile(
            optical_net, item["optical"], patch, stride, infer_batch
        )

    specs = condition_specs()
    if args.smoke:
        wanted = {"clean", "dsm_zero", "dsm_local_zero_q1", "dsm_local_down8_q1"}
        specs = [spec for spec in specs if spec["name"] in wanted]
    suffix = "_smoke" if args.smoke else ""
    out = args.out or ROOT / f"records/rebuild_v1_d4_expert_complementarity_seed{args.seed}_20260920{suffix}"
    out.mkdir(parents=True, exist_ok=True)

    metric_rows = []
    region_rows = []
    agreement_rows = []
    clean_scores = {}
    raw = {}

    for spec in specs:
        name = spec["name"]
        print(f"--- D4 seed={args.seed} condition={name} ---", flush=True)
        cms = {
            (method, split_name): np.zeros((r02.N_CLASSES, r02.N_CLASSES), dtype=np.int64)
            for method in METHODS for split_name in SPLITS
        }
        region_cms = {
            (method, split_name, region): np.zeros((r02.N_CLASSES, r02.N_CLASSES), dtype=np.int64)
            for method in METHODS for split_name in SPLITS for region in ("damaged", "undamaged")
        }
        agreement = {"valid": 0, "both_correct": 0, "only_r01_correct": 0, "only_r05_correct": 0, "both_wrong": 0}

        for tile, item in cache.items():
            optical_pred = optical_predictions[tile]
            treated, local_mask = apply_condition(item["dsm"], spec)
            dual_pred = r02.infer_tile(
                dual_net, item["optical"], treated, patch, stride, infer_batch
            )
            rule_pred = select_prediction(optical_pred, dual_pred, spec, local_mask)

            nb_gt = item["noboundary_gt"]
            valid = (nb_gt != r02.IGNORE_INDEX) & (nb_gt < r02.N_CLASSES)
            r01_ok = optical_pred == nb_gt
            r05_ok = dual_pred == nb_gt
            agreement["valid"] += int(valid.sum())
            agreement["both_correct"] += int((valid & r01_ok & r05_ok).sum())
            agreement["only_r01_correct"] += int((valid & r01_ok & ~r05_ok).sum())
            agreement["only_r05_correct"] += int((valid & ~r01_ok & r05_ok).sum())
            agreement["both_wrong"] += int((valid & ~r01_ok & ~r05_ok).sum())

            for split_name, gt in (("full", item["full_gt"]), ("noboundary", nb_gt)):
                predictions = {
                    "R01_optical": optical_pred,
                    "R05_dual": dual_pred,
                    "condition_rule": rule_pred,
                    "pixel_oracle": oracle_prediction(gt, optical_pred, dual_pred),
                }
                for method, pred in predictions.items():
                    update(cms[(method, split_name)], gt, pred)
                    if local_mask is not None and spec["family"] in ("D1_local_missing", "D3_local_down8"):
                        update(region_cms[(method, split_name, "damaged")], gt, pred, local_mask)
                        update(region_cms[(method, split_name, "undamaged")], gt, pred, ~local_mask)

        condition_raw = {"spec": spec, "agreement": agreement, "metrics": {}}
        total = max(1, agreement["valid"])
        agreement_rows.append({
            "condition": name,
            "family": spec["family"],
            **{key + "_fraction": agreement[key] / total for key in ("both_correct", "only_r01_correct", "only_r05_correct", "both_wrong")},
            "valid_pixels": agreement["valid"],
        })
        for method in METHODS:
            condition_raw["metrics"][method] = {}
            for split_name in SPLITS:
                metrics = r02.metrics_from_cm(cms[(method, split_name)])
                condition_raw["metrics"][method][split_name] = metrics
                if name == "clean":
                    clean_scores[(method, split_name)] = metrics["mIoU_fg5"]
                metric_rows.append({
                    "condition": name,
                    "family": spec["family"],
                    "method": method,
                    "split": split_name,
                    "OA": metrics["OA"],
                    "mF1_fg5": metrics["mF1_fg5"],
                    "mIoU_fg5": metrics["mIoU_fg5"],
                    "mIoU_all6": metrics["mIoU_all6"],
                    "drop_from_method_clean_mIoU_fg5_pp": 100.0 * (clean_scores[(method, split_name)] - metrics["mIoU_fg5"]),
                })
                if spec["family"] in ("D1_local_missing", "D3_local_down8"):
                    for region in ("damaged", "undamaged"):
                        rm = r02.metrics_from_cm(region_cms[(method, split_name, region)])
                        region_rows.append({
                            "condition": name,
                            "family": spec["family"],
                            "method": method,
                            "split": split_name,
                            "region": region,
                            "OA": rm["OA"],
                            "mIoU_fg5": rm["mIoU_fg5"],
                        })
        raw[name] = condition_raw
        nb = condition_raw["metrics"]
        print(
            "NB mIoU: " + ", ".join(
                f"{method}={100.0 * nb[method]['noboundary']['mIoU_fg5']:.4f}"
                for method in METHODS
            ),
            flush=True,
        )

    write_csv(out / "method_metrics.csv", metric_rows)
    write_csv(out / "region_metrics.csv", region_rows)
    write_csv(out / "prediction_agreement.csv", agreement_rows)
    payload = {
        "recorded_at": now_iso(),
        "experiment_id": "D4_EXPERT_COMPLEMENTARITY",
        "seed": args.seed,
        "smoke": args.smoke,
        "val_ids": val_ids,
        "historical_test6_loaded": False,
        "r01_checkpoint": str(r01_checkpoint),
        "r05_checkpoint": str(r05_checkpoint),
        "r01_checkpoint_step": int(r01_state.get("global_step", -1)),
        "r05_checkpoint_step": int(r05_state.get("global_step", -1)),
        "r01_completed_step": int(r01_summary["global_step"]),
        "r05_completed_step": int(r05_summary["global_step"]),
        "conditions": specs,
        "methods": METHODS,
        "condition_rule": "R01 for global/local DSM missing regions; R05 otherwise",
        "pixel_oracle_note": "Label-informed upper bound only; not a deployable method.",
        "results": raw,
    }
    with open(out / "summary.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"D4 COMPLETE seed={args.seed}: {out}")


if __name__ == "__main__":
    main()
