"""Frozen-expert decision audit: safe entropy versus safe confidence routing."""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import torch

import eval_rebuild_v1_d9a_benefit as d9a
import train_rebuild_v1_r01_optical_only as r01
import train_rebuild_v1_r02_budget_pilot as r02
from d9_benefit_metrics import (apply_known_missing_fallback,
                                benefit_from_probabilities,
                                entropy_choose_dual, selected_harm)
from eval_rebuild_v1_d4_expert_complementarity import validate_run
from eval_rebuild_v1_d5_confidence_routing import infer_scores, softmax_np

ROOT = d9a.ROOT
METHODS = ("R01", "R05", "safe_confidence", "min_entropy", "safe_entropy")


def metric_rows(seed, condition, tile, split, gt, predictions, pooled):
    rows, classes = [], []
    for method, pred in predictions.items():
        cm = np.zeros((r02.N_CLASSES, r02.N_CLASSES), np.int64)
        r02.update_cm(cm, gt, pred)
        pooled[(split, method)] += cm
        m = r02.metrics_from_cm(cm)
        rows.append({"seed": seed, "condition": condition, "tile": tile,
                     "split": split, "method": method, "mIoU_fg5": m["mIoU_fg5"],
                     "OA": m["OA"], "valid_pixels": m["valid_pixels"]})
        for cls, iou in enumerate(m["per_class_iou"]):
            classes.append({"seed": seed, "condition": condition, "tile": tile,
                            "split": split, "method": method,
                            "class": r02.CLASS_NAMES[cls], "IoU": iou,
                            "gt_pixels": int(cm[cls].sum())})
    return rows, classes


def harm_row(seed, condition, tile, group, method, chosen, delta):
    h = selected_harm(chosen, delta)
    harmed = np.asarray(chosen, bool) & (np.asarray(delta) < -0.01)
    return {"seed": seed, "condition": condition, "tile": tile,
            "group": group, "method": method, "valid_sampled": len(delta),
            "selected_fraction": h["selected_dual"] / len(delta) if len(delta) else None,
            **h, "mean_harm_ce": float(np.mean(-delta[harmed])) if harmed.any() else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, choices=(17, 42), required=True)
    ap.add_argument("--condition", choices=tuple(d9a.CONDITIONS), required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    suffix = "_smoke" if args.smoke else ""
    out = ROOT / f"records/rebuild_v1_d9a_entropy_route_seed{args.seed}_{args.condition}_20260923{suffix}"
    if out.exists():
        raise FileExistsError(out)

    cfg1 = r02.read_json(ROOT / "configs/rebuild_v1/r01_optical_only_16k.json")
    cfg5 = r02.read_json(ROOT / "configs/rebuild_v1/r05_quality_plus_dropout_16k.json")
    split = r02.read_json(ROOT / cfg5["split_file"])
    ids = list(split["val2"][:1] if args.smoke else split["val2"])
    if not ids or set(ids) & set(split["historical_exposed_test6"]):
        raise RuntimeError("Val2 missing or overlaps historical TEST6")
    run1 = ROOT / f"runs/rebuild_v1/R01_optical_only_seed{args.seed}_sched16000_stop16000"
    run5 = ROOT / f"runs/rebuild_v1/R05_dual_f0_quality_plus_dropout_seed{args.seed}_sched16000_stop16000"
    _, ck1 = validate_run(run1)
    _, ck5 = validate_run(run5)
    state1, state5 = torch.load(ck1, map_location="cpu"), torch.load(ck5, map_location="cpu")
    net1, _, _ = r01.build_model(cfg1, Path(cfg1["pretrain"]), resume_state=state1)
    net5, _ = r02.build_model(cfg5, Path(cfg5["pretrain"]), resume_state=state5)
    net1.eval(); net5.eval()
    with (ROOT / "records/rebuild_v1_d7_data_sampling_20260922/component_area_quantiles.csv").open(newline="", encoding="utf-8") as f:
        thresholds = {row["class_name"]: (float(row["area_q25"]), float(row["area_q75"]))
                      for row in csv.DictReader(f)}
    patch = int(cfg5["patch"])
    stride = int(cfg5["validation"]["stride"])
    batch = int(cfg5["validation"]["inference_batch"])
    metrics, class_rows, harms, region_metrics = [], [], [], []
    pooled_cm = {(s, m): np.zeros((r02.N_CLASSES, r02.N_CLASSES), np.int64)
                 for s in ("full", "noboundary") for m in METHODS}
    pooled_region_cm = {}
    pooled_samples = {"delta": [], "labels": [], "sizes": [], "regions": [],
                      **{m: [] for m in METHODS}}
    family = d9a.CONDITIONS[args.condition]["family"]

    for tile in ids:
        print(f"D9A ENTROPY ROUTE seed={args.seed} condition={args.condition} tile={tile}", flush=True)
        data = r02.load_tile(Path(cfg5["data_root"]), tile, need_nb=True)
        treated, region = d9a.condition_dsm(data["dsm"], args.condition, tile)
        p1 = softmax_np(infer_scores(net1, data["optical"], data["dsm"], patch, stride, batch, True))
        p5 = softmax_np(infer_scores(net5, data["optical"], treated, patch, stride, batch, False))
        pred1, pred5 = p1.argmax(0).astype(np.uint8), p5.argmax(0).astype(np.uint8)
        conf = p5.max(0) > p1.max(0)
        ent = entropy_choose_dual(p1, p5)
        choices = {
            "R01": np.zeros(conf.shape, bool), "R05": np.ones(conf.shape, bool),
            "safe_confidence": apply_known_missing_fallback(conf, region, family),
            "min_entropy": ent,
            "safe_entropy": apply_known_missing_fallback(ent, region, family),
        }
        if family == "global_missing" and (choices["safe_confidence"].any() or choices["safe_entropy"].any()):
            raise RuntimeError("DSM-zero deterministic RGB fallback failed")
        predictions = {m: np.where(choices[m], pred5, pred1).astype(np.uint8) for m in METHODS}
        for s, gt in (("full", data["full_gt"]), ("noboundary", data["noboundary_gt"])):
            mr, cr = metric_rows(args.seed, args.condition, tile, s, gt, predictions, pooled_cm)
            metrics.extend(mr); class_rows.extend(cr)

        region_groups = ({"damaged": region, "undamaged": ~region} if region is not None
                         else {"undamaged": np.ones(data["noboundary_gt"].shape, bool)})
        for group, mask in region_groups.items():
            if not mask.any():
                continue
            gt_region = np.where(mask, data["noboundary_gt"], r02.IGNORE_INDEX)
            for method, pred in predictions.items():
                cm = np.zeros((r02.N_CLASSES, r02.N_CLASSES), np.int64)
                r02.update_cm(cm, gt_region, pred)
                key = (group, method)
                if key not in pooled_region_cm:
                    pooled_region_cm[key] = np.zeros_like(cm)
                pooled_region_cm[key] += cm
                m = r02.metrics_from_cm(cm)
                region_metrics.append({"seed": args.seed, "condition": args.condition,
                                       "tile": tile, "region": group, "method": method,
                                       "mIoU_fg5": m["mIoU_fg5"],
                                       "valid_pixels": m["valid_pixels"]})

        gt = data["noboundary_gt"]
        valid = (gt != r02.IGNORE_INDEX) & (gt < r02.N_CLASSES)
        indices = np.flatnonzero(valid)
        count = min(indices.size, 10000 if args.smoke else 200000)
        rng = np.random.default_rng(20260923 + int(tile.replace("_", "")))
        sample = rng.choice(indices, size=count, replace=False)
        yy, xx = np.unravel_index(sample, gt.shape)
        labels = gt[yy, xx]
        delta = benefit_from_probabilities(p1[labels, yy, xx], p5[labels, yy, xx])
        sizes = d9a.sample_size_bins(data["full_gt"], yy, xx, thresholds)
        regions = np.where(region[yy, xx], "damaged", "undamaged") if region is not None else np.full(count, "undamaged", dtype="<U9")
        sampled = {m: choices[m][yy, xx] for m in METHODS}
        groups = {"all": np.ones(count, bool)}
        groups.update({f"class:{r02.CLASS_NAMES[c]}": labels == c for c in range(5)})
        groups.update({f"size:{size}": sizes == size for size in ("small", "medium", "large")})
        groups.update({f"class_size:Car:{size}": (labels == 4) & (sizes == size)
                       for size in ("small", "medium", "large")})
        if region is not None:
            groups.update({f"region:{name}": regions == name for name in ("damaged", "undamaged")})
        for group, mask in groups.items():
            if not mask.any():
                continue
            for method in METHODS:
                harms.append(harm_row(args.seed, args.condition, tile, group, method,
                                      sampled[method][mask], delta[mask]))
        for key, value in (("delta", delta), ("labels", labels), ("sizes", sizes), ("regions", regions)):
            pooled_samples[key].append(value)
        for method in METHODS:
            pooled_samples[method].append(sampled[method])
        del data, treated, p1, p5

    for (s, method), cm in pooled_cm.items():
        m = r02.metrics_from_cm(cm)
        metrics.append({"seed": args.seed, "condition": args.condition, "tile": "ALL",
                        "split": s, "method": method, "mIoU_fg5": m["mIoU_fg5"],
                        "OA": m["OA"], "valid_pixels": m["valid_pixels"]})
        for cls, iou in enumerate(m["per_class_iou"]):
            class_rows.append({"seed": args.seed, "condition": args.condition,
                               "tile": "ALL", "split": s, "method": method,
                               "class": r02.CLASS_NAMES[cls], "IoU": iou,
                               "gt_pixels": int(cm[cls].sum())})
    for (group, method), cm in pooled_region_cm.items():
        m = r02.metrics_from_cm(cm)
        region_metrics.append({"seed": args.seed, "condition": args.condition,
                               "tile": "ALL", "region": group, "method": method,
                               "mIoU_fg5": m["mIoU_fg5"],
                               "valid_pixels": m["valid_pixels"]})
    pooled = {key: np.concatenate(parts) for key, parts in pooled_samples.items()}
    group_masks = {"all": np.ones(len(pooled["delta"]), bool)}
    group_masks.update({f"class:{r02.CLASS_NAMES[c]}": pooled["labels"] == c for c in range(5)})
    group_masks.update({f"size:{size}": pooled["sizes"] == size for size in ("small", "medium", "large")})
    group_masks.update({f"class_size:Car:{size}": (pooled["labels"] == 4) & (pooled["sizes"] == size)
                        for size in ("small", "medium", "large")})
    if family in ("global_missing", "local_missing", "local_downsampling", "misalignment"):
        group_masks.update({f"region:{name}": pooled["regions"] == name for name in ("damaged", "undamaged")})
    for group, mask in group_masks.items():
        if not mask.any():
            continue
        for method in METHODS:
            harms.append(harm_row(args.seed, args.condition, "ALL", group, method,
                                  pooled[method][mask], pooled["delta"][mask]))

    out.mkdir(parents=True, exist_ok=False)
    d9a.write_csv(out / "method_metrics.csv", metrics)
    d9a.write_csv(out / "class_iou.csv", class_rows)
    d9a.write_csv(out / "region_metrics.csv", region_metrics)
    d9a.write_csv(out / "selected_harm.csv", harms)
    summary = {"recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
               "experiment_id": "D9A_ENTROPY_ROUTING_AUDIT", "seed": args.seed,
               "condition": args.condition, "condition_spec": d9a.CONDITIONS[args.condition],
               "smoke": args.smoke, "val_ids": ids, "test6_loaded": False,
               "r01_checkpoint": str(ck1), "r05_checkpoint": str(ck5),
               "r01_checkpoint_step": int(state1.get("global_step", -1)),
               "r05_checkpoint_step": int(state5.get("global_step", -1)),
               "sample_pixels_per_tile": 10000 if args.smoke else 200000,
               "sample_design": "same fixed NoBoundary sample positions as D9A",
               "selected_harm_definition": "selected dual pixels with CE benefit below -0.01 / selected dual pixels",
               "interpretation": "exploratory Val2 route comparison; no new model or independent confirmation"}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("D9A ENTROPY ROUTE COMPLETE", out, flush=True)


if __name__ == "__main__":
    main()
