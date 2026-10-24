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

import train_rebuild_v1_r02_budget_pilot as r02
from eval_rebuild_v1_dual_robust_conditions import down_restore


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def quadrant_mask(shape, quadrant):
    h, w = shape
    hh, hw = h // 2, w // 2
    mask = np.zeros((h, w), dtype=bool)
    slices = {
        "q1": (slice(0, hh), slice(0, hw)),
        "q2": (slice(0, hh), slice(hw, w)),
        "q3": (slice(hh, h), slice(0, hw)),
        "q4": (slice(hh, h), slice(hw, w)),
    }
    mask[slices[quadrant]] = True
    return mask


def shift_zero_fill(x, dy, dx):
    out = np.zeros_like(x)
    h, w = x.shape[:2]
    sy0, sy1 = max(0, -dy), min(h, h - dy)
    sx0, sx1 = max(0, -dx), min(w, w - dx)
    dy0, dy1 = max(0, dy), min(h, h + dy)
    dx0, dx1 = max(0, dx), min(w, w + dx)
    out[dy0:dy1, dx0:dx1] = x[sy0:sy1, sx0:sx1]
    return out


def condition_specs():
    specs = [{"name": "clean", "family": "D0_clean"}]
    for q in ("q1", "q2", "q3", "q4"):
        specs.append({"name": f"dsm_local_zero_{q}", "family": "D1_local_missing", "quadrant": q})
    for pixels in (2, 4, 8):
        for direction, dy, dx in (
            ("up", -pixels, 0), ("down", pixels, 0),
            ("left", 0, -pixels), ("right", 0, pixels),
        ):
            specs.append({
                "name": f"dsm_shift_{direction}_{pixels}px",
                "family": "D2_misalignment",
                "pixels": pixels,
                "direction": direction,
                "dy": dy,
                "dx": dx,
            })
    for q in ("q1", "q2", "q3", "q4"):
        specs.append({"name": f"dsm_local_down8_{q}", "family": "D3_local_down8", "quadrant": q})
    return specs


def apply_condition(second, spec):
    out = np.array(second, copy=True)
    local_mask = None
    if spec["family"] == "D1_local_missing":
        local_mask = quadrant_mask(second.shape, spec["quadrant"])
        out[local_mask] = 0.0
    elif spec["family"] == "D2_misalignment":
        out = shift_zero_fill(second, spec["dy"], spec["dx"])
    elif spec["family"] == "D3_local_down8":
        local_mask = quadrant_mask(second.shape, spec["quadrant"])
        degraded = down_restore(second, 8)
        out[local_mask] = degraded[local_mask]
    return np.ascontiguousarray(out), local_mask


def masked_metrics(gt, pred, mask):
    masked_gt = np.where(mask, gt, r02.IGNORE_INDEX)
    cm = np.zeros((r02.N_CLASSES, r02.N_CLASSES), dtype=np.int64)
    r02.update_cm(cm, masked_gt, pred)
    return cm, r02.metrics_from_cm(cm)


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def resolve_variant(variant):
    if variant == "R05":
        return (
            ROOT / "configs/rebuild_v1/r05_quality_plus_dropout_16k.json",
            ROOT / "runs/rebuild_v1/R05_dual_f0_quality_plus_dropout_seed42_sched16000_stop16000",
            ROOT / "records/rebuild_v1_r05_local_failure_diagnostics_20260918",
        )
    return (
        ROOT / "configs/rebuild_v1/c_oo_qd_optical_gray_16k.json",
        ROOT / "runs/rebuild_v1/C_OO_QD_dual_optical_gray_quality_plus_dropout_seed42_sched16000_stop16000",
        ROOT / "records/rebuild_v1_c_oo_qd_local_failure_diagnostics_20260918",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["R05", "C-OO-QD"], required=True)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    config_path, run_dir, default_out = resolve_variant(args.variant)
    out = args.out or (Path(str(default_out) + "_smoke") if args.smoke else default_out)
    cfg = r02.read_json(config_path)
    summary = r02.read_json(run_dir / "summary.json")
    expected_step = int(cfg["schedule"]["stop_at_step"])
    if int(summary.get("global_step", -1)) != expected_step:
        raise RuntimeError(f"incomplete checkpoint: {summary}")
    if summary.get("test6_loaded") is not False:
        raise RuntimeError("TEST6 safety flag failed")

    split = r02.read_json(r02.resolve_root_relative(cfg["split_file"]))
    val_ids = list(split["val2"])
    if set(val_ids) & set(split["historical_exposed_test6"]):
        raise RuntimeError("VAL2 overlaps TEST6")
    if args.smoke:
        val_ids = val_ids[:1]

    state = torch.load(run_dir / "best_model.pth", map_location="cpu")
    net, _ = r02.build_model(cfg, Path(cfg["pretrain"]), resume_state=state)
    net.eval()
    cache = {
        tile: r02.load_tile(Path(cfg["data_root"]), tile, need_nb=True)
        for tile in val_ids
    }
    out.mkdir(parents=True, exist_ok=True)

    patch = int(cfg["patch"])
    stride = int(cfg["validation"]["stride"])
    infer_batch = int(cfg["validation"]["inference_batch"])
    specs = condition_specs()
    if args.smoke:
        wanted = {"clean", "dsm_local_zero_q1", "dsm_shift_right_4px", "dsm_local_down8_q1"}
        specs = [spec for spec in specs if spec["name"] in wanted]
    dataset_rows, region_rows, tile_rows, raw = [], [], [], {}
    clean_scores = {}

    for spec in specs:
        name = spec["name"]
        print(f"--- {args.variant} {name} ---", flush=True)
        cms = {
            split_name: np.zeros((r02.N_CLASSES, r02.N_CLASSES), dtype=np.int64)
            for split_name in ("full", "noboundary")
        }
        region_cms = {
            (split_name, region): np.zeros((r02.N_CLASSES, r02.N_CLASSES), dtype=np.int64)
            for split_name in ("full", "noboundary")
            for region in ("damaged", "undamaged")
        }
        tile_payload = {}
        for tile in val_ids:
            item = cache[tile]
            second = (
                item["optical"].mean(axis=2).astype(np.float32, copy=False)
                if args.variant == "C-OO-QD" else item["dsm"]
            )
            treated, local_mask = apply_condition(second, spec)
            pred = r02.infer_tile(net, item["optical"], treated, patch, stride, infer_batch)
            tile_payload[tile] = {}
            for split_name, gt in (("full", item["full_gt"]), ("noboundary", item["noboundary_gt"])):
                tile_cm = np.zeros_like(cms[split_name])
                r02.update_cm(tile_cm, gt, pred)
                cms[split_name] += tile_cm
                metrics = r02.metrics_from_cm(tile_cm)
                tile_payload[tile][split_name] = metrics
                tile_rows.append({
                    "condition": name, "family": spec["family"], "tile": tile,
                    "split": split_name, "mIoU_fg5": metrics["mIoU_fg5"], "OA": metrics["OA"],
                })
                if local_mask is not None:
                    for region, mask in (("damaged", local_mask), ("undamaged", ~local_mask)):
                        cm, _ = masked_metrics(gt, pred, mask)
                        region_cms[(split_name, region)] += cm

        condition_raw = {"spec": spec, "per_tile": tile_payload}
        for split_name in ("full", "noboundary"):
            metrics = r02.metrics_from_cm(cms[split_name])
            condition_raw[split_name] = metrics
            if name == "clean":
                clean_scores[split_name] = metrics["mIoU_fg5"]
            dataset_rows.append({
                "condition": name, "family": spec["family"], "split": split_name,
                "OA": metrics["OA"], "mF1_fg5": metrics["mF1_fg5"],
                "mIoU_fg5": metrics["mIoU_fg5"], "mIoU_all6": metrics["mIoU_all6"],
                "drop_from_clean_mIoU_fg5_pp": 100.0 * (clean_scores[split_name] - metrics["mIoU_fg5"]),
            })
            if spec["family"] in ("D1_local_missing", "D3_local_down8"):
                for region in ("damaged", "undamaged"):
                    rm = r02.metrics_from_cm(region_cms[(split_name, region)])
                    region_rows.append({
                        "condition": name, "family": spec["family"], "split": split_name,
                        "region": region, "OA": rm["OA"], "mIoU_fg5": rm["mIoU_fg5"],
                    })
        raw[name] = condition_raw
        print(f"NB mIoU_fg5={100.0 * condition_raw['noboundary']['mIoU_fg5']:.4f}", flush=True)

    write_csv(out / "dataset_metrics.csv", dataset_rows)
    write_csv(out / "region_metrics.csv", region_rows)
    write_csv(out / "per_tile_metrics.csv", tile_rows)
    payload = {
        "recorded_at": now_iso(), "variant": args.variant,
        "second_stream": "fixed_optical_channel_mean" if args.variant == "C-OO-QD" else "DSM",
        "checkpoint": str(run_dir / "best_model.pth"),
        "checkpoint_step": int(state.get("global_step", -1)),
        "val_ids": val_ids, "historical_test6_loaded": False,
        "condition_count": len(specs), "conditions": specs, "smoke": args.smoke,
        "geometry": {"patch": patch, "stride": stride, "inference_batch": infer_batch},
        "results": raw,
    }
    with open(out / "summary.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"{args.variant} LOCAL FAILURE DIAGNOSTICS COMPLETE: {out}")


if __name__ == "__main__":
    main()
