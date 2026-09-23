"""D10M: fixed-expert spatial/frequency mechanism experiment; no fitting."""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path
import numpy as np
import torch
import eval_rebuild_v1_d9a_benefit as d9a
import train_rebuild_v1_r01_optical_only as r01
import train_rebuild_v1_r02_budget_pilot as r02
from eval_rebuild_v1_d4_expert_complementarity import validate_run
from eval_rebuild_v1_d5_confidence_routing import infer_scores, softmax_np
from d9_benefit_metrics import benefit_from_probabilities, rank_metrics
from d10m_mechanism import CONDITIONS, RADII, amplitude_error, translate, sampled_structure, rescue_at_harm

ROOT = d9a.ROOT
BASE = ROOT / "records/rebuild_v1_d10m_mechanism_20260923"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, choices=(42, 17), required=True)
    ap.add_argument("--condition", choices=CONDITIONS, required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    out = BASE / (f"seed{args.seed}_{args.condition}" + ("_smoke" if args.smoke else ""))
    out.resolve().relative_to(Path("/home/jovyan/zzx").resolve())
    if out.exists():
        raise FileExistsError(f"Do not overwrite existing run: {out}")
    cfg1 = r02.read_json(ROOT / "configs/rebuild_v1/r01_optical_only_16k.json")
    cfg5 = r02.read_json(ROOT / "configs/rebuild_v1/r05_quality_plus_dropout_16k.json")
    split = r02.read_json(ROOT / cfg5["split_file"])
    ids = list(split["val2"][:1] if args.smoke else split["val2"])
    if set(split["val2"]) != {"3_11", "5_10"} or set(ids) & set(split["historical_exposed_test6"]):
        raise RuntimeError("Frozen Val2-only experiment")
    _, ck1 = validate_run(ROOT / f"runs/rebuild_v1/R01_optical_only_seed{args.seed}_sched16000_stop16000")
    _, ck5 = validate_run(ROOT / f"runs/rebuild_v1/R05_dual_f0_quality_plus_dropout_seed{args.seed}_sched16000_stop16000")
    state1, state5 = torch.load(ck1, map_location="cpu"), torch.load(ck5, map_location="cpu")
    net1, _, _ = r01.build_model(cfg1, Path(cfg1["pretrain"]), resume_state=state1)
    net5, _ = r02.build_model(cfg5, Path(cfg5["pretrain"]), resume_state=state5)
    net1.eval(); net5.eval()
    with (ROOT / "records/rebuild_v1_d7_data_sampling_20260922/component_area_quantiles.csv").open(newline="", encoding="utf-8") as f:
        thresholds = {r["class_name"]: (float(r["area_q25"]), float(r["area_q75"])) for r in csv.DictReader(f)}
    out.mkdir(parents=True, exist_ok=False)
    patch, stride, batch = int(cfg5["patch"]), int(cfg5["validation"]["stride"]), int(cfg5["validation"]["inference_batch"])
    metrics, ranks, curves, spectra, pooled = [], [], [], [], {}
    for tile in ids:
        print(f"D10M seed={args.seed} condition={args.condition} tile={tile}", flush=True)
        d = r02.load_tile(Path(cfg5["data_root"]), tile, need_nb=True)
        if args.condition.startswith(("roll", "edge")):
            treated = translate(d["dsm"], int(args.condition[4:]), args.condition.startswith("roll"))
        else:
            treated, _ = d9a.condition_dsm(d["dsm"], args.condition, tile)
        err = amplitude_error(d["dsm"], treated)
        if args.condition.startswith("roll") and err > 1e-6:
            raise RuntimeError(f"Fourier-amplitude invariance failed: {err}")
        spectra.append(dict(seed=args.seed, condition=args.condition, tile=tile, amplitude_relative_l2=err))
        p1 = softmax_np(infer_scores(net1, d["optical"], d["dsm"], patch, stride, batch, True))
        p5 = softmax_np(infer_scores(net5, d["optical"], treated, patch, stride, batch, False))
        pred1, pred5 = p1.argmax(0).astype(np.uint8), p5.argmax(0).astype(np.uint8)
        entropy1 = -(p1 * np.log(p1 + 1e-8)).sum(0)
        entropy5 = -(p5 * np.log(p5 + 1e-8)).sum(0)
        available = args.condition != "dsm_zero"
        choices = {"safe_confidence": available & (p5.max(0) > p1.max(0)),
                   "safe_entropy": available & (entropy5 < entropy1)}
        predictions = {"R01": pred1, "R05": pred5,
                       **{k: np.where(v, pred5, pred1) for k, v in choices.items()}}
        gt = d["noboundary_gt"]
        # Exclude wrap seam and inference-window edge effects from primary comparison.
        margin = patch + 32
        interior = np.zeros(gt.shape, bool)
        interior[margin:-margin, margin:-margin] = True
        predictions["available_correctness_oracle"] = np.where(available & (pred5 == gt), pred5, pred1)
        for region, region_mask in (("all", np.ones(gt.shape, bool)), ("interior", interior)):
            valid = region_mask & (gt != r02.IGNORE_INDEX) & (gt < r02.N_CLASSES)
            if not valid.any():
                raise RuntimeError("Empty evaluation region")
            for method, pred in predictions.items():
                cm = np.zeros((r02.N_CLASSES, r02.N_CLASSES), np.int64)
                r02.update_cm(cm, np.where(valid, gt, r02.IGNORE_INDEX), pred)
                key = (region, method)
                pooled[key] = pooled.get(key, np.zeros_like(cm)) + cm
                m = r02.metrics_from_cm(cm)
                harm = float(np.mean(((pred1 == gt) & (pred != gt))[valid]))
                rescue = float(np.mean(((pred1 != gt) & (pred == gt))[valid]))
                metrics.append(dict(seed=args.seed, condition=args.condition, tile=tile, region=region,
                                    method=method, mIoU_fg5=m["mIoU_fg5"], valid_pixels=int(valid.sum()),
                                    harm=harm, rescue=rescue, accuracy_gain=rescue-harm,
                                    Car_IoU=m["per_class_iou"][4], Building_IoU=m["per_class_iou"][1]))
        valid_indices = np.flatnonzero((gt != r02.IGNORE_INDEX) & (gt < r02.N_CLASSES))
        rng = np.random.default_rng(20260923 + int(tile.replace("_", "")))
        sample = rng.choice(valid_indices, size=min(len(valid_indices), 10000 if args.smoke else 200000), replace=False)
        yy, xx = np.unravel_index(sample, gt.shape)
        labels, rgb, dual = gt[yy, xx], p1[:, yy, xx], p5[:, yy, xx]
        delta = benefit_from_probabilities(rgb[labels, np.arange(len(labels))], dual[labels, np.arange(len(labels))])
        spectra[-1].update(mean_sampled_ce_benefit=float(delta.mean()),
                           ce_benefit_fraction=float(np.mean(delta > .01)),
                           ce_harm_fraction=float(np.mean(delta < -.01)))
        features = sampled_structure(d["optical"], treated, yy, xx)
        mid = (rgb + dual) / 2
        features.update(confidence_margin=dual.max(0)-rgb.max(0),
                        entropy_margin=entropy1[yy, xx]-entropy5[yy, xx],
                        js_disagreement=.5*((rgb*np.log((rgb+1e-8)/(mid+1e-8))).sum(0)
                                             +(dual*np.log((dual+1e-8)/(mid+1e-8))).sum(0)))
        sizes = d9a.sample_size_bins(d["full_gt"], yy, xx, thresholds)
        rc, dc = rgb.argmax(0) == labels, dual.argmax(0) == labels
        groups = {"all": np.ones(len(labels), bool), "interior": interior[yy, xx],
                  "smallCar": (labels == 4) & (sizes == "small")}
        groups.update({name: labels == c for c, name in enumerate(r02.CLASS_NAMES)})
        np.savez_compressed(out / f"samples_{tile}.npz", yy=yy, xx=xx, labels=labels,
                            sizes=sizes, interior=interior[yy, xx], rgb_prob=rgb, dual_prob=dual,
                            ce_benefit=delta, **features)
        # Energy and unsigned JS are weak controls, not asserted signed benefit estimates.
        for group, mask in groups.items():
            if not mask.any():
                continue
            for name, values in features.items():
                flip = mask & (rc != dc)
                ranking = rank_metrics(values[flip], np.where(dc[flip], 1., -1.), 0.)
                ranks.append(dict(seed=args.seed, condition=args.condition, tile=tile, group=group,
                                  score=name, **ranking))
                for row in rescue_at_harm(values[mask], rc[mask], dc[mask], np.full(mask.sum(), available)):
                    curves.append(dict(seed=args.seed, condition=args.condition, tile=tile, group=group,
                                       score=name, support=int(mask.sum()), **row))
            # Label-using upper bound, explicitly separated from all observable scores.
            oracle = dc.astype(np.int8) - rc.astype(np.int8)
            for row in rescue_at_harm(oracle[mask], rc[mask], dc[mask], np.full(mask.sum(), available)):
                curves.append(dict(seed=args.seed, condition=args.condition, tile=tile, group=group,
                                   score="oracle", support=int(mask.sum()), **row))
        del d, p1, p5, predictions, treated
    for (region, method), cm in pooled.items():
        m = r02.metrics_from_cm(cm)
        matching = [r for r in metrics if r["region"] == region and r["method"] == method and r["tile"] != "ALL"]
        n = sum(r["valid_pixels"] for r in matching)
        h, r = [sum(row[k]*row["valid_pixels"] for row in matching)/n for k in ("harm", "rescue")]
        metrics.append(dict(seed=args.seed, condition=args.condition, tile="ALL", region=region, method=method,
                            mIoU_fg5=m["mIoU_fg5"], valid_pixels=n, harm=h, rescue=r, accuracy_gain=r-h,
                            Car_IoU=m["per_class_iou"][4], Building_IoU=m["per_class_iou"][1]))
    for filename, rows in (("metrics", metrics), ("ranking", ranks), ("harm_rescue", curves), ("spectra", spectra)):
        d9a.write_csv(out / f"{filename}.csv", rows)
    summary = dict(experiment="D10M", seed=args.seed, condition=args.condition, smoke=args.smoke,
                   val_ids=ids, test6_loaded=False, fitting_performed=False,
                   checkpoint_rgb=str(ck1), checkpoint_dual=str(ck5),
                   checkpoint_steps=[int(s.get("global_step", -1)) for s in (state1, state5)],
                   commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                   source_sha256={name: hashlib.sha256((ROOT / "scripts" / name).read_bytes()).hexdigest()
                                  for name in ("d10m_mechanism.py", "eval_rebuild_v1_d10m_mechanism.py")},
                   interior_margin=margin, feature_names=list(features), radii=list(RADII),
                   cache_sampling="matched uniform NoBoundary 200k/tile; no independent pixel significance tests",
                   interpretation="Exploratory fixed-expert association; not causal DSM effect or independent generalization",
                   curve_interpretation="Post-hoc ranking envelope using labels; not deployable calibrated thresholds")
    (out / "summary.json").write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8")
    print("D10M COMPLETE", out, flush=True)


if __name__ == "__main__":
    main()
