"""D9B exploratory, unfitted decision-benefit screen on frozen Val2 experts."""

import argparse
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import torch

import eval_rebuild_v1_d9a_benefit as d9a
import train_rebuild_v1_r01_optical_only as r01
import train_rebuild_v1_r02_budget_pilot as r02
from d9_benefit_metrics import benefit_from_probabilities, rank_metrics
from d9b_observable_features import sampled_observables, screen_scores
from eval_rebuild_v1_d4_expert_complementarity import validate_run
from eval_rebuild_v1_d5_confidence_routing import infer_scores, softmax_np

ROOT = d9a.ROOT
PROTOTYPE = ROOT / "records/rebuild_v1_d9b_train16_prototypes_20260923/prototypes.json"
SCORES = ("confidence_margin", "entropy_margin", "semantic_prototype",
          "frequency_alignment", "semantic_plus_frequency", "semantic_frequency_expert")


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def observations(labels, pred1, pred5):
    disagree = pred1 != pred5
    out = np.full(labels.shape, "agreement", dtype="<U17")
    out[disagree] = "both_wrong"
    out[disagree & (pred5 == labels)] = "dual_only_correct"
    out[disagree & (pred1 == labels)] = "rgb_only_correct"
    return out


def metric_rows(seed, condition, tile, labels, sizes, regions, outcome, delta, scores):
    groups = {"all": np.ones(labels.size, bool)}
    groups.update({f"class:{r02.CLASS_NAMES[c]}": labels == c for c in range(r02.N_CLASSES)})
    groups.update({f"class_size:Car:{size}": (labels == 4) & (sizes == size)
                   for size in ("small", "medium", "large")})
    if np.any(regions == "damaged"):
        groups.update({f"region:{name}": regions == name
                       for name in ("damaged", "undamaged")})
    rows = []
    for group, mask in groups.items():
        if not mask.any():
            continue
        counts = {name: int(np.count_nonzero(mask & (outcome == name)))
                  for name in ("agreement", "dual_only_correct", "rgb_only_correct", "both_wrong")}
        flip = mask & ((outcome == "dual_only_correct") | (outcome == "rgb_only_correct"))
        for name in SCORES:
            decision = rank_metrics(scores[name][flip],
                                    np.where(outcome[flip] == "dual_only_correct", 1., -1.), 0.)
            ce = rank_metrics(scores[name][mask], delta[mask], 0.01)
            rows.append({"seed": seed, "condition": condition, "tile": tile,
                         "group": group, "score": name, "sample_count": int(mask.sum()),
                         **counts, "flip_auroc": decision["benefit_auroc"],
                         "flip_auprc": decision["benefit_auprc"],
                         "ce_auroc": ce["benefit_auroc"],
                         "ce_auprc": ce["benefit_auprc"],
                         "ce_support": ce["count"],
                         "ce_benefit": ce["benefit_count"],
                         "ce_harm": ce["harm_count"]})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, choices=(17, 42), required=True)
    ap.add_argument("--condition", choices=tuple(d9a.CONDITIONS), required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    out = ROOT / (f"records/rebuild_v1_d9b_seed{args.seed}_{args.condition}_20260923"
                  + ("_smoke" if args.smoke else ""))
    if out.exists():
        raise FileExistsError(out)
    stats = json.loads(PROTOTYPE.read_text(encoding="utf-8"))
    if stats["source_split"] != "train16" or stats["val2_loaded"] or stats["test6_loaded"]:
        raise RuntimeError("prototype source isolation failed")
    cfg1 = r02.read_json(ROOT / "configs/rebuild_v1/r01_optical_only_16k.json")
    cfg5 = r02.read_json(ROOT / "configs/rebuild_v1/r05_quality_plus_dropout_16k.json")
    split = r02.read_json(ROOT / cfg5["split_file"])
    ids = list(split["val2"][:1] if args.smoke else split["val2"])
    if not ids or set(ids) & set(split["historical_exposed_test6"]):
        raise RuntimeError("Val2/Test6 split failure")
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
    rows, pooled = [], {key: [] for key in ("labels", "sizes", "regions", "outcome", "delta", *SCORES)}
    for tile in ids:
        print(f"D9B seed={args.seed} condition={args.condition} tile={tile}", flush=True)
        d = r02.load_tile(Path(cfg5["data_root"]), tile, need_nb=True)
        treated, missing_mask = d9a.condition_dsm(d["dsm"], args.condition, tile)
        p1 = softmax_np(infer_scores(net1, d["optical"], d["dsm"], patch, stride, batch, True))
        p5 = softmax_np(infer_scores(net5, d["optical"], treated, patch, stride, batch, False))
        gt = d["noboundary_gt"]
        valid = np.flatnonzero((gt != r02.IGNORE_INDEX) & (gt < r02.N_CLASSES))
        n = min(valid.size, 10000 if args.smoke else 200000)
        if n == 0:
            raise RuntimeError(f"no valid NoBoundary pixels in {tile}")
        rng = np.random.default_rng(20260923 + int(tile.replace("_", "")))
        sample = rng.choice(valid, size=n, replace=False)
        yy, xx = np.unravel_index(sample, gt.shape)
        labels = gt[yy, xx]
        rgb, dual = p1[:, yy, xx], p5[:, yy, xx]
        rgb_feat, dsm_feat, alignment = sampled_observables(d["optical"], treated, yy, xx)
        scores, pred1, pred5 = screen_scores(rgb, dual, rgb_feat, dsm_feat, alignment, stats)
        outcome = observations(labels, pred1, pred5)
        delta = benefit_from_probabilities(rgb[labels, np.arange(n)], dual[labels, np.arange(n)])
        sizes = d9a.sample_size_bins(d["full_gt"], yy, xx, thresholds)
        regions = (np.where(missing_mask[yy, xx], "damaged", "undamaged")
                   if missing_mask is not None else np.full(n, "undamaged", dtype="<U9"))
        rows.extend(metric_rows(args.seed, args.condition, tile, labels, sizes, regions, outcome, delta, scores))
        for key, value in {"labels": labels, "sizes": sizes, "regions": regions,
                           "outcome": outcome, "delta": delta, **scores}.items():
            pooled[key].append(value)
        del d, treated, p1, p5
    all_data = {key: np.concatenate(value) for key, value in pooled.items()}
    rows.extend(metric_rows(args.seed, args.condition, "ALL", all_data["labels"],
                            all_data["sizes"], all_data["regions"], all_data["outcome"],
                            all_data["delta"], {key: all_data[key] for key in SCORES}))
    out.mkdir(parents=True, exist_ok=False)
    write_csv(out / "decision_metrics.csv", rows)
    summary = {"experiment_id": "D9B_UNFITTED_DECISION_SCREEN", "seed": args.seed,
               "condition": args.condition, "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
               "smoke": args.smoke, "val_ids": ids, "test6_loaded": False,
               "r01_checkpoint": str(ck1), "r05_checkpoint": str(ck5),
               "r01_checkpoint_step": int(state1.get("global_step", -1)),
               "r05_checkpoint_step": int(state5.get("global_step", -1)),
               "prototype_sha256": hashlib.sha256(PROTOTYPE.read_bytes()).hexdigest(),
               "sample_design": "D9A matched uniform NoBoundary 200k per Val2 tile; same coordinates across seeds and conditions",
               "scores": list(SCORES), "routing_or_calibration_performed": False,
               "ground_truth_used_as_feature": False,
               "hard_missing_override_required_for_future_routing": d9a.CONDITIONS[args.condition]["family"] in ("global_missing", "local_missing"),
               "interpretation": "exploratory Val2 discrimination only; no fitted method or independent generalization claim"}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("D9B COMPLETE", out, flush=True)


if __name__ == "__main__":
    main()
