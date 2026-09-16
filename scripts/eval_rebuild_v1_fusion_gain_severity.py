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

import train_rebuild_v1_r02_budget_pilot as r02
import train_rebuild_v1_r01_optical_only as r01

OUT_DEFAULT = ROOT / "records/rebuild_v1_r01_r02_fusion_gain_severity_20260916"
R02_RUN = ROOT / "runs/rebuild_v1/R02_dual_f0_seed42_sched16000_stop16000"
R01_RUN = ROOT / "runs/rebuild_v1/R01_optical_only_seed42_sched16000_stop16000"
R02_CONFIG = ROOT / "configs/rebuild_v1/r02_budget_pilot_16k.json"
R01_CONFIG = ROOT / "configs/rebuild_v1/r01_optical_only_16k.json"
CONDITIONS = ["clean", "dsm_down2", "dsm_down4", "dsm_down8", "dsm_zero"]


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def down_restore(x, factor):
    h, w = x.shape
    t = torch.from_numpy(np.ascontiguousarray(x)).float()[None, None]
    small = F.interpolate(
        t,
        size=(max(1, h // factor), max(1, w // factor)),
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
    return restored[0, 0].cpu().numpy().astype(np.float32, copy=False)


def corrupt_dsm(dsm, condition):
    if condition == "clean":
        return dsm
    if condition == "dsm_zero":
        return np.zeros_like(dsm, dtype=np.float32)
    if condition.startswith("dsm_down"):
        factor = int(condition.replace("dsm_down", ""))
        return down_restore(dsm, factor)
    raise ValueError(condition)


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def require_complete(run_dir, expected_step=16000, r01_expected=False):
    p = run_dir / "summary.json"
    if not p.is_file():
        raise FileNotFoundError(p)
    s = r02.read_json(p)
    if int(s.get("global_step", -1)) != expected_step:
        raise RuntimeError(f"incomplete run {run_dir}: {s}")
    if r01_expected and s.get("dsm_loaded") is not False:
        raise RuntimeError(f"R01 is not true Optical-only: {s}")
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    cfg02 = r02.read_json(R02_CONFIG)
    cfg01 = r02.read_json(R01_CONFIG)
    if cfg02["split_file"] != cfg01["split_file"]:
        raise RuntimeError("R01/R02 split mismatch")
    if int(cfg02["patch"]) != int(cfg01["patch"]):
        raise RuntimeError("R01/R02 patch mismatch")

    # Compare only scientific validation fields. Free-text notes are allowed to differ.
    for key in ("eval_interval_steps", "stride", "inference_batch", "selection_metric", "fullgt_also_reported"):
        if cfg02["validation"].get(key) != cfg01["validation"].get(key):
            raise RuntimeError(
                f"R01/R02 validation protocol mismatch for {key}: "
                f"{cfg01['validation'].get(key)} vs {cfg02['validation'].get(key)}"
            )

    split = r02.read_json(r02.resolve_root_relative(cfg02["split_file"]))
    val_ids = list(split["val2"])
    if set(val_ids) & set(split["historical_exposed_test6"]):
        raise RuntimeError("VAL2 overlaps historical TEST6")

    require_complete(R02_RUN)
    require_complete(R01_RUN, r01_expected=True)

    state02 = torch.load(R02_RUN / "best_model.pth", map_location="cpu")
    net02, _ = r02.build_model(cfg02, Path(cfg02["pretrain"]), resume_state=state02)
    net02.eval()
    state01 = torch.load(R01_RUN / "best_model.pth", map_location="cpu")
    net01, _, audit01 = r01.build_model(cfg01, Path(cfg01["pretrain"]), resume_state=state01)
    if not audit01["pass"]:
        raise RuntimeError(audit01)
    net01.eval()

    val02 = {
        tile: r02.load_tile(Path(cfg02["data_root"]), tile, need_nb=True)
        for tile in val_ids
    }
    val01 = {
        tile: r01.load_tile(Path(cfg01["data_root"]), tile, need_nb=True)
        for tile in val_ids
    }

    patch = int(cfg02["patch"])
    stride = int(cfg02["validation"]["stride"])
    infer_batch = int(cfg02["validation"]["inference_batch"])

    # R01 clean is the matched comparator for every DSM-only corruption.
    cm01_full = np.zeros((r02.N_CLASSES, r02.N_CLASSES), dtype=np.int64)
    cm01_nb = np.zeros_like(cm01_full)
    for tile in val_ids:
        d = val01[tile]
        pred = r01.infer_tile(net01, d["optical"], patch, stride, infer_batch)
        r02.update_cm(cm01_full, d["full_gt"], pred)
        r02.update_cm(cm01_nb, d["noboundary_gt"], pred)
    r01_metrics = {
        "full": r02.metrics_from_cm(cm01_full),
        "noboundary": r02.metrics_from_cm(cm01_nb),
        "cm_full": cm01_full.tolist(),
        "cm_noboundary": cm01_nb.tolist(),
    }

    rows, per_class_rows, raw = [], [], {}
    clean02 = None
    for condition in CONDITIONS:
        print(f"--- R02 {condition} ---", flush=True)
        cm_full = np.zeros((r02.N_CLASSES, r02.N_CLASSES), dtype=np.int64)
        cm_nb = np.zeros_like(cm_full)
        for tile in val_ids:
            d = val02[tile]
            ds = corrupt_dsm(d["dsm"], condition)
            pred = r02.infer_tile(net02, d["optical"], ds, patch, stride, infer_batch)
            r02.update_cm(cm_full, d["full_gt"], pred)
            r02.update_cm(cm_nb, d["noboundary_gt"], pred)
        full = r02.metrics_from_cm(cm_full)
        nb = r02.metrics_from_cm(cm_nb)
        if condition == "clean":
            clean02 = {"full": full, "noboundary": nb}
        raw[condition] = {
            "full": full,
            "noboundary": nb,
            "cm_full": cm_full.tolist(),
            "cm_noboundary": cm_nb.tolist(),
        }

        for split_name, metrics in (("full", full), ("noboundary", nb)):
            r01m = r01_metrics[split_name]
            clean_m = clean02[split_name]["mIoU_fg5"]
            rows.append({
                "condition": condition,
                "split": split_name,
                "R01_mIoU_fg5": r01m["mIoU_fg5"],
                "R02_mIoU_fg5": metrics["mIoU_fg5"],
                "R02_drop_from_clean_pp": 100.0 * (clean_m - metrics["mIoU_fg5"]),
                "Fusion_Gain_pp": 100.0 * (metrics["mIoU_fg5"] - r01m["mIoU_fg5"]),
                "R01_OA": r01m["OA"],
                "R02_OA": metrics["OA"],
            })
            for i, name in enumerate(r02.CLASS_NAMES):
                per_class_rows.append({
                    "condition": condition,
                    "split": split_name,
                    "class_index": i,
                    "class_name": name,
                    "R01_IoU": r01m["per_class_iou"][i],
                    "R02_IoU": metrics["per_class_iou"][i],
                    "R02_minus_R01_IoU_pp": 100.0 * (
                        metrics["per_class_iou"][i] - r01m["per_class_iou"][i]
                    ),
                })

    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "fusion_gain.csv", rows)
    write_csv(args.out / "per_class_fusion_gain.csv", per_class_rows)

    nb_clean_fg = next(x["Fusion_Gain_pp"] for x in rows if x["condition"] == "clean" and x["split"] == "noboundary")
    nb_degraded = {
        x["condition"]: x["Fusion_Gain_pp"]
        for x in rows if x["split"] == "noboundary" and x["condition"] != "clean"
    }
    harmful_supported = bool(
        nb_clean_fg > 0 and any(v < 0 for v in nb_degraded.values())
    )

    summary = {
        "recorded_at": now_iso(),
        "protocol": "REBUILD_V1 R01/R02 matched Val2 DSM-severity Fusion Gain",
        "val_ids": val_ids,
        "historical_test6_loaded": False,
        "r01_checkpoint_step": int(state01.get("global_step", -1)),
        "r02_checkpoint_step": int(state02.get("global_step", -1)),
        "conditions": CONDITIONS,
        "downsample": "anti-aliased bilinear downsample then bilinear restore on normalized DSM; labels/output grid unchanged",
        "r01": r01_metrics,
        "r02": raw,
        "noboundary_clean_fusion_gain_pp": nb_clean_fg,
        "noboundary_degraded_fusion_gain_pp": nb_degraded,
        "G1_harmful_fusion_supported_on_this_val2_screen": harmful_supported,
        "interpretation_rule": "G1 requires positive clean Fusion Gain and negative Fusion Gain under at least one controlled DSM degradation. Development Val2 evidence is not a sealed external final test.",
    }
    with open(args.out / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(json.dumps({
        "clean_nb_fusion_gain_pp": nb_clean_fg,
        "degraded_nb_fusion_gain_pp": nb_degraded,
        "G1_supported": harmful_supported,
    }, indent=2, ensure_ascii=False))
    print("FUSION-GAIN SEVERITY COMPLETE:", args.out)


if __name__ == "__main__":
    main()
