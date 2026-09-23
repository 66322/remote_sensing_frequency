"""Fit/calibrate/freeze one D12 head, then evaluate pre-existing Val2 samples."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from d11_benefit_probe import targets, choose_threshold, routing_metrics, validate_roles
from d12_night_probe import (ROOT, CFG, BASE, MODELS, sample_and_semantic,
                             features, train_model, temperature, predict)


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def role_groups(cfg, seed, role, model):
    for tile in cfg[role]:
        for condition in cfg["development_conditions"]:
            sample, sem, meta = sample_and_semantic(seed, tile, condition, role)
            x = features(sample, sem, model, seed, tile, condition)
            target, eligible, _, _ = targets(sample)
            yield x, target, eligible, tile, condition, meta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, choices=(17, 42), required=True)
    parser.add_argument("--model", choices=MODELS, required=True)
    args = parser.parse_args()
    cfg = json.loads(CFG.read_text())
    split = json.loads((ROOT / "configs/rebuild_v1/potsdam_split_seed20260915.json").read_text())
    validate_roles(cfg, split)
    out = BASE / "models" / f"seed{args.seed}_{args.model}"
    out.resolve().relative_to(Path("/home/jovyan/zzx").resolve())
    if out.exists():
        raise FileExistsError(out)
    fit_x, fit_y = [], []
    identity = None
    for x, target, eligible, tile, condition, meta in role_groups(cfg, args.seed, "fit", args.model):
        if identity is None:
            identity = meta["checkpoint_identity"]
        elif identity != meta["checkpoint_identity"]:
            raise RuntimeError("D12 source experts changed within fit")
        fit_x.append(x[eligible])
        fit_y.append(target[eligible])
    artifact = train_model(np.concatenate(fit_x), np.concatenate(fit_y), args.model, args.seed, cfg)
    del fit_x, fit_y
    cal_x, cal_y = [], []
    for x, target, eligible, tile, condition, meta in role_groups(cfg, args.seed, "probability_calibration", args.model):
        if identity != meta["checkpoint_identity"]:
            raise RuntimeError("D12 calibration expert mismatch")
        cal_x.append(x[eligible]); cal_y.append(target[eligible])
    artifact["temperature"] = temperature(artifact, np.concatenate(cal_x), np.concatenate(cal_y))
    del cal_x, cal_y
    groups = []
    for x, target, eligible, tile, condition, meta in role_groups(cfg, args.seed, "threshold_calibration", args.model):
        if identity != meta["checkpoint_identity"]:
            raise RuntimeError("D12 threshold expert mismatch")
        prob = predict(artifact, x)
        groups.append((prob[:, 0] - prob[:, 1], target, eligible))
    selected, table = choose_threshold(groups, cfg["thresholds"], cfg["harm_budget"])
    artifact.update(threshold=selected["threshold"], calibration_selection=selected,
                    threshold_table=table, checkpoint_identity=identity,
                    config_sha256=hashlib.sha256(CFG.read_bytes()).hexdigest(),
                    test6_loaded=False, val2_used_for_fit_calibration=False)
    out.mkdir(parents=True, exist_ok=False)
    model_path = out / "model.json"
    model_path.write_text(json.dumps(artifact, indent=2) + "\n")
    model_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
    del groups
    metrics = []
    class_names = ("Impervious", "Building", "LowVegetation", "Tree", "Car", "Clutter")
    for condition in cfg["evaluation_conditions"]:
        parts = []
        for tile in cfg["evaluation"]:
            sample, sem, meta = sample_and_semantic(args.seed, tile, condition, "evaluation")
            if identity != meta["checkpoint_identity"]:
                raise RuntimeError("D12 evaluation expert mismatch")
            parts.append((tile, sample, sem))
        for tile, sample, sem in [*parts, ("ALL", None, None)]:
            if tile == "ALL":
                sample = {key: np.concatenate([p[key] for _, p, _ in parts],
                                  axis=1 if key in ("rgb_prob", "dual_prob") else 0)
                          for key in parts[0][1]}
                sem = {key: np.concatenate([s[key] for _, _, s in parts],
                               axis=1 if key in ("sem_rgb", "sem_dual") else 0)
                       for key in parts[0][2]}
            x = features(sample, sem, args.model, args.seed, tile, condition)
            prob = predict(artifact, x)
            target, eligible, rgb, dual = targets(sample)
            available = condition != "dsm_zero"
            choose = available & eligible & ((prob[:, 0] - prob[:, 1]) > artifact["threshold"])
            if not available and choose.any():
                raise RuntimeError("DSM-zero RGB fallback failed")
            labels = sample["labels"]
            masks = {"all": np.ones(len(labels), bool),
                     "interior": sample["interior"],
                     "smallCar": (labels == 4) & (sample["sizes"] == "small")}
            masks.update({name: labels == c for c, name in enumerate(class_names)})
            for group, mask in masks.items():
                if not mask.any():
                    continue
                for method, decision in (("probe", choose), ("RGB", np.zeros(len(labels), bool)),
                                         ("dual", np.ones(len(labels), bool))):
                    metrics.append(dict(seed=args.seed, model=args.model, condition=condition,
                                        tile=tile, group=group, method=method,
                                        **routing_metrics(labels[mask], rgb[mask], dual[mask], decision[mask])))
    if hashlib.sha256(model_path.read_bytes()).hexdigest() != model_hash:
        raise RuntimeError("frozen D12 model changed during evaluation")
    write_csv(out / "routing.csv", metrics)
    summary = dict(seed=args.seed, model=args.model, threshold=artifact["threshold"],
                   temperature=artifact["temperature"], model_sha256=model_hash,
                   parameter_count=artifact["parameter_count"], checkpoint_identity=identity,
                   rows=len(metrics), test6_loaded=False,
                   interpretation="exploratory sampled NoBoundary, Train16-exposed experts and reused Val2")
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("D12 PROBE COMPLETE", out, flush=True)


if __name__ == "__main__":
    main()
