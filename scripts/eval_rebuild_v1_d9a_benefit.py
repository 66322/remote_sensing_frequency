"""D9A: frozen-expert DSM benefit labels and unfitted score controls on Val2."""

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
from d9_benefit_metrics import benefit_from_probabilities, rank_metrics, selected_harm
from eval_rebuild_v1_d4_expert_complementarity import oracle_prediction, validate_run
from eval_rebuild_v1_d5_confidence_routing import infer_scores, softmax_np
from eval_rebuild_v1_dual_robust_conditions import apply_condition as apply_global
from eval_rebuild_v1_local_failure_diagnostics import apply_condition as apply_local


CONDITIONS = {
    "clean": {"family": "clean"},
    "dsm_zero": {"family": "global_missing"},
    "dsm_down8": {"family": "global_downsampling", "factor": 8},
    "dsm_blur5": {"family": "global_blur", "kernel": 5},
    "dsm_noise_std010": {"family": "global_noise", "sigma_normalized": 0.10},
    "dsm_shift_right_4px": {"family": "misalignment", "dx": 4, "dy": 0},
    "dsm_local_zero_q1": {"family": "local_missing", "quadrant": "q1"},
    "dsm_local_down8_q1": {"family": "local_downsampling", "quadrant": "q1", "factor": 8},
}
SCORES = ("confidence_margin", "entropy_margin", "confidence_times_js", "class_agreement_margin")


def write_csv(path, rows):
    if not rows:
        raise RuntimeError(f"no rows for {path}")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def condition_dsm(dsm, name, tile):
    spec = CONDITIONS[name]
    family = spec["family"]
    if family in ("clean", "global_missing", "global_downsampling", "global_blur"):
        _, treated = apply_global(np.empty((1, 1, 3), np.float32), dsm,
                                  {"global_missing": "dsm_zero",
                                   "global_downsampling": "dsm_down8",
                                   "global_blur": "dsm_blur5"}.get(family, "clean"))
        mask = np.ones(dsm.shape, bool) if family == "global_missing" else None
    elif family == "global_noise":
        rng = np.random.default_rng(20260923 + int(tile.replace("_", "")))
        treated = np.clip(dsm + rng.normal(0, 0.10, dsm.shape), 0, 1).astype(np.float32)
        mask = None
    else:
        local_spec = {**spec, "family": {"misalignment": "D2_misalignment",
                                         "local_missing": "D1_local_missing",
                                         "local_downsampling": "D3_local_down8"}[family]}
        treated, mask = apply_local(dsm, local_spec)
    return np.ascontiguousarray(treated), mask


def sample_size_bins(full_gt, rows, cols, thresholds):
    bins = np.full(rows.size, "unknown", dtype="<U7")
    for cls, name in enumerate(r02.CLASS_NAMES[:5]):
        subset = full_gt[rows, cols] == cls
        if not subset.any():
            continue
        labels, _ = ndimage.label(full_gt == cls,
                                  structure=np.ones((3, 3), dtype=np.uint8))
        areas = np.bincount(labels.ravel())
        observed = areas[labels[rows[subset], cols[subset]]]
        q25, q75 = thresholds[name]
        bins[subset] = np.where(observed <= q25, "small",
                                np.where(observed >= q75, "large", "medium"))
        del labels, areas
    return bins


def score_samples(rgb, dual):
    c1, c5 = rgb.max(axis=0), dual.max(axis=0)
    eps = 1e-8
    e1 = -(rgb * np.log(rgb + eps)).sum(axis=0)
    e5 = -(dual * np.log(dual + eps)).sum(axis=0)
    mid = (rgb + dual) / 2
    js = 0.5 * ((rgb * np.log((rgb + eps) / (mid + eps))).sum(axis=0)
                + (dual * np.log((dual + eps) / (mid + eps))).sum(axis=0))
    margin = c5 - c1
    agree = rgb.argmax(axis=0) == dual.argmax(axis=0)
    return {
        "confidence_margin": margin,
        "entropy_margin": e1 - e5,
        "confidence_times_js": margin * js,
        "class_agreement_margin": margin * np.where(agree, 0.5, 1.0),
    }, {"mean_js": float(np.mean(js)), "class_disagreement_rate": float(np.mean(~agree))}


def metric_rows(seed, condition, tile, gt, pred1, pred5, routed, pooled_cms):
    rows = []
    for split, label in (("full", gt["full_gt"]), ("noboundary", gt["noboundary_gt"])):
        preds = {"R01": pred1, "R05": pred5, "D5_safe_confidence": routed,
                 "correctness_oracle": oracle_prediction(label, pred1, pred5)}
        for method, pred in preds.items():
            cm = np.zeros((r02.N_CLASSES, r02.N_CLASSES), np.int64)
            r02.update_cm(cm, label, pred)
            pooled_cms[(split, method)] += cm
            m = r02.metrics_from_cm(cm)
            rows.append({"seed": seed, "condition": condition, "tile": tile,
                         "split": split, "method": method,
                         "mIoU_fg5": m["mIoU_fg5"], "valid_pixels": int(cm.sum())})
    return rows


def sampled_ranking_rows(seed, condition, tile, labels, sizes, regions, scores, benefit):
    rows = []
    groups = [("all", np.ones(labels.size, bool))]
    groups += [(f"class:{r02.CLASS_NAMES[c]}", labels == c) for c in range(r02.N_CLASSES)]
    groups += [(f"size:{size}", sizes == size) for size in ("small", "medium", "large")]
    groups += [(f"class_size:{r02.CLASS_NAMES[c]}:{size}",
                (labels == c) & (sizes == size))
               for c in range(5) for size in ("small", "medium", "large")]
    if np.any(regions == "damaged") and np.any(regions == "undamaged"):
        groups += [(f"region:{region}", regions == region)
                   for region in ("damaged", "undamaged")]
    for group, mask in groups:
        if not mask.any():
            continue
        for name, score in scores.items():
            for neutral in (0.0, 0.01):
                m = rank_metrics(score[mask], benefit[mask], neutral)
                rows.append({"seed": seed, "condition": condition, "tile": tile,
                             "group": group, "score": name, "neutral_ce": neutral,
                             **m})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, choices=(17, 42), required=True)
    ap.add_argument("--condition", choices=tuple(CONDITIONS), required=True)
    ap.add_argument("--sample-pixels-per-tile", type=int, default=200000)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    if args.sample_pixels_per_tile < 1000:
        raise ValueError("sample size must be at least 1000")
    suffix = "_smoke" if args.smoke else ""
    out = args.out or ROOT / f"records/rebuild_v1_d9a_seed{args.seed}_{args.condition}_20260923{suffix}"
    out = out.resolve()
    if not out.is_relative_to((ROOT / "records").resolve()):
        raise RuntimeError(f"output outside project records: {out}")
    if out.exists():
        raise FileExistsError(out)

    cfg1 = r02.read_json(ROOT / "configs/rebuild_v1/r01_optical_only_16k.json")
    cfg5 = r02.read_json(ROOT / "configs/rebuild_v1/r05_quality_plus_dropout_16k.json")
    split = r02.read_json(ROOT / cfg5["split_file"])
    ids = list(split["val2"][:1] if args.smoke else split["val2"])
    if set(ids) & set(split["historical_exposed_test6"]):
        raise RuntimeError("Val2/Test6 overlap")
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
    method_rows, ranking_rows, harm_rows, tile_summaries = [], [], [], []
    pooled_cms = {(split, method): np.zeros((r02.N_CLASSES, r02.N_CLASSES), np.int64)
                  for split in ("full", "noboundary")
                  for method in ("R01", "R05", "D5_safe_confidence", "correctness_oracle")}
    pooled_samples = {"labels": [], "sizes": [], "regions": [], "benefit": [],
                      **{name: [] for name in SCORES}, "selected_d5": []}

    for tile in ids:
        print(f"D9A seed={args.seed} condition={args.condition} tile={tile}", flush=True)
        d = r02.load_tile(Path(cfg5["data_root"]), tile, need_nb=True)
        treated, missing_mask = condition_dsm(d["dsm"], args.condition, tile)
        p1 = softmax_np(infer_scores(net1, d["optical"], d["dsm"], patch, stride, batch, True))
        p5 = softmax_np(infer_scores(net5, d["optical"], treated, patch, stride, batch, False))
        pred1, pred5 = p1.argmax(0).astype(np.uint8), p5.argmax(0).astype(np.uint8)
        choose5 = p5.max(0) > p1.max(0)
        if missing_mask is not None:
            choose5 &= ~missing_mask
        routed = np.where(choose5, pred5, pred1).astype(np.uint8)
        if args.condition == "dsm_zero" and not np.array_equal(routed, pred1):
            raise RuntimeError("DSM-zero deterministic RGB fallback failed")
        method_rows.extend(metric_rows(args.seed, args.condition, tile, d, pred1,
                                       pred5, routed, pooled_cms))

        gt = d["noboundary_gt"]
        valid = (gt != r02.IGNORE_INDEX) & (gt < r02.N_CLASSES)
        indices = np.flatnonzero(valid)
        sample_size = min(indices.size, 10000 if args.smoke else args.sample_pixels_per_tile)
        rng = np.random.default_rng(20260923 + int(tile.replace("_", "")))
        sample = rng.choice(indices, size=sample_size, replace=False)
        yy, xx = np.unravel_index(sample, gt.shape)
        labels = gt[yy, xx]
        rgb = p1[:, yy, xx]
        dual = p5[:, yy, xx]
        delta = benefit_from_probabilities(rgb[labels, np.arange(sample_size)],
                                           dual[labels, np.arange(sample_size)])
        scores, extra = score_samples(rgb, dual)
        sizes = sample_size_bins(d["full_gt"], yy, xx, thresholds)
        regions = np.where(missing_mask[yy, xx], "damaged", "undamaged") if missing_mask is not None else np.full(sample_size, "undamaged", dtype="<U9")
        ranking_rows.extend(sampled_ranking_rows(args.seed, args.condition, tile,
                                                 labels, sizes, regions, scores, delta))
        for key, value in (("labels", labels), ("sizes", sizes), ("regions", regions),
                           ("benefit", delta), ("selected_d5", choose5[yy, xx])):
            pooled_samples[key].append(value)
        for name in SCORES:
            pooled_samples[name].append(scores[name])
        for method, selected in (("R05", np.ones(sample_size, bool)),
                                 ("D5_safe_confidence", choose5[yy, xx])):
            harm_rows.append({"seed": args.seed, "condition": args.condition,
                              "tile": tile, "method": method,
                              **selected_harm(selected, delta)})
        tile_summaries.append({"tile": tile, "valid_pixels": int(valid.sum()),
                               "sample_pixels": int(sample_size),
                               "mean_ce_benefit": float(np.mean(delta)),
                               "benefit_prevalence_001": float(np.mean(delta > 0.01)),
                               "harm_prevalence_001": float(np.mean(delta < -0.01)),
                               **extra})
        del d, treated, p1, p5

    for (split, method), cm in pooled_cms.items():
        m = r02.metrics_from_cm(cm)
        method_rows.append({"seed": args.seed, "condition": args.condition,
                            "tile": "ALL", "split": split, "method": method,
                            "mIoU_fg5": m["mIoU_fg5"], "valid_pixels": int(cm.sum())})
    pooled = {name: np.concatenate(parts) for name, parts in pooled_samples.items()}
    pooled_scores = {name: pooled[name] for name in SCORES}
    ranking_rows.extend(sampled_ranking_rows(args.seed, args.condition, "ALL",
                                             pooled["labels"], pooled["sizes"],
                                             pooled["regions"], pooled_scores,
                                             pooled["benefit"]))
    for method, selected in (("R05", np.ones(pooled["benefit"].size, bool)),
                             ("D5_safe_confidence", pooled["selected_d5"])):
        harm_rows.append({"seed": args.seed, "condition": args.condition,
                          "tile": "ALL", "method": method,
                          **selected_harm(selected, pooled["benefit"])})

    out.mkdir(parents=True, exist_ok=False)
    write_csv(out / "method_metrics.csv", method_rows)
    write_csv(out / "ranking_metrics.csv", ranking_rows)
    write_csv(out / "selected_harm.csv", harm_rows)
    payload = {"recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
               "experiment_id": "D9A_FROZEN_EXPERT_BENEFIT_AUDIT", "seed": args.seed,
               "condition": args.condition, "condition_spec": CONDITIONS[args.condition],
               "smoke": args.smoke, "val_ids": ids, "test6_loaded": False,
               "r01_checkpoint": str(ck1), "r05_checkpoint": str(ck5),
               "r01_checkpoint_step": int(state1.get("global_step", -1)),
               "r05_checkpoint_step": int(state5.get("global_step", -1)),
               "sample_design": "uniform without replacement among valid NoBoundary pixels; same tile sample across seeds/conditions",
               "sample_pixels_per_tile_requested": args.sample_pixels_per_tile,
               "neutral_ce": [0.0, 0.01], "scores": list(SCORES),
               "ece_status": "not computed: direct scores are uncalibrated, not benefit probabilities",
               "semantic_frequency_status": "deferred until independent fitting/calibration source is frozen",
               "tile_summaries": tile_summaries}
    (out / "summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("D9A COMPLETE", out, flush=True)


if __name__ == "__main__":
    main()
