"""Paired clean-vs-local-DSM validation diagnostics on exactly the same pixels.

This is a read-only checkpoint evaluation. Ground truth is used only for metrics;
it never changes inputs, predictions, routing, or checkpoint selection.
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

from rebuild_v1_b2_common import ROOT, confusion, fingerprint, region_masks, safe_output

sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]


def write_csv(path, rows):
    if not rows:
        return
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def paired_outcomes(gt, clean_pred, corrupt_pred, mask, classes=6):
    """Return pixel transitions on one fixed mask; pixels are measurements, not replicates."""
    import numpy as np
    valid = mask & (gt >= 0) & (gt < classes)
    clean_ok = clean_pred == gt
    corrupt_ok = corrupt_pred == gt
    return {
        "valid_pixels": int(valid.sum()),
        "clean_correct_corrupt_wrong": int((valid & clean_ok & ~corrupt_ok).sum()),
        "clean_wrong_corrupt_correct": int((valid & ~clean_ok & corrupt_ok).sum()),
        "both_correct": int((valid & clean_ok & corrupt_ok).sum()),
        "both_wrong": int((valid & ~clean_ok & ~corrupt_ok).sum()),
        "prediction_changed": int((valid & (clean_pred != corrupt_pred)).sum()),
    }


def metric_values(cm, r02):
    if int(cm.sum()) == 0:
        return {"mIoU_fg5": "", "mIoU_all6": "", "OA": ""}
    metrics = r02.metrics_from_cm(cm)
    return {name: float(metrics[name]) for name in ("mIoU_fg5", "mIoU_all6", "OA")}


def add_pair(rows, class_rows, outcomes, base, clean_cm, corrupt_cm, r02):
    clean = metric_values(clean_cm, r02)
    corrupt = metric_values(corrupt_cm, r02)
    row = dict(base, **outcomes)
    for name in ("mIoU_fg5", "mIoU_all6", "OA"):
        row["clean_" + name] = clean[name]
        row["corrupt_" + name] = corrupt[name]
        row["delta_" + name] = (corrupt[name] - clean[name]) if clean[name] != "" else ""
    rows.append(row)
    for i, class_name in enumerate(r02.CLASS_NAMES):
        item = dict(base, class_index=i, class_name=class_name)
        for state, cm in (("clean", clean_cm), ("corrupt", corrupt_cm)):
            tp = int(cm[i, i])
            support, predicted = int(cm[i].sum()), int(cm[:, i].sum())
            union = support + predicted - tp
            item[state + "_TP"] = tp
            item[state + "_FP"] = predicted - tp
            item[state + "_FN"] = support - tp
            item[state + "_support"] = support
            item[state + "_union"] = union
            item[state + "_IoU"] = tp / union if union else ""
        item["delta_IoU"] = (item["corrupt_IoU"] - item["clean_IoU"] \
                             if item["clean_IoU"] != "" and item["corrupt_IoU"] != "" else "")
        class_rows.append(item)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    import numpy as np
    import torch
    import train_rebuild_v1_r02_budget_pilot as r02
    from eval_rebuild_v1_d5_confidence_routing import infer_scores
    from eval_rebuild_v1_local_failure_diagnostics import apply_condition, condition_specs

    output = safe_output(ROOT / args.out)
    cfg_path, run_dir = ROOT / args.config, ROOT / args.run_dir
    cfg = r02.read_json(cfg_path)
    summary = r02.read_json(run_dir / "summary.json")
    run_metadata = r02.read_json(run_dir / "run_metadata.json")
    if run_metadata.get("config") != cfg:
        raise RuntimeError("Run/config binding mismatch")
    expected = int(cfg["schedule"]["stop_at_step"])
    if summary.get("test6_loaded") is not False or summary.get("global_step") != expected:
        raise RuntimeError("Run incomplete or TEST6 flag invalid")

    split = r02.read_json(ROOT / cfg["split_file"])
    ids = split["val2"]
    if len(ids) != 2 or len(set(ids)) != 2 or set(ids) & (set(split["train16"]) | set(split["historical_exposed_test6"])):
        raise RuntimeError("Unsafe validation split")
    if args.smoke:
        ids = ids[:1]

    checkpoint = run_dir / "best_model.pth"
    state = torch.load(checkpoint, map_location="cpu")
    best = summary["best"]
    if best["metric"] != "val2_noboundary_mIoU_fg5" or int(state["global_step"]) != int(best["step"]):
        raise RuntimeError("Checkpoint/clean selection mismatch")
    net, _ = r02.build_model(cfg, Path(cfg["pretrain"]), resume_state=state)
    del state
    net.eval()

    specs = [s for s in condition_specs() if s["family"] in ("D1_local_missing", "D3_local_down8")]
    if args.smoke:
        specs = [s for s in specs if s["name"] in ("dsm_local_zero_q1", "dsm_local_down8_q1")]

    output.mkdir(parents=True)
    (output / "confusion_matrices").mkdir()
    metadata = {
        "status": "RUNNING", "started_at": datetime.now().astimezone().isoformat(),
        "label": args.label, "config": cfg, "config_fingerprint": fingerprint(cfg_path),
        "checkpoint": fingerprint(checkpoint), "checkpoint_step": best["step"],
        "val_ids": ids, "conditions": specs, "smoke": args.smoke, "test6_loaded": False,
        "pairing": "Same model, tile, split, corruption-defined region and GT pixels; corrupt minus clean",
        "independent_unit_note": "Tile is the independent validation unit. Quadrants and pixels are repeated measurements, not independent replicates.",
        "boundary_radius_pixels": 8,
        "boundary_definition": "Synthetic corruption interface +/-8 px, Chebyshev; overlaps damaged/intact; not semantic boundary",
        "aggregation": "Pool int64 6x6 CMs across the two Val2 tiles within each condition; do not pool quadrants as independent replicates",
        "source": fingerprint(Path(__file__)),
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    pair_rows, class_rows = [], []
    aggregate = {}
    patch = cfg["patch"]
    stride = cfg["validation"]["stride"]
    batch = cfg["validation"]["inference_batch"]

    for tile in ids:
        item = r02.load_tile(Path(cfg["data_root"]), tile, need_nb=True)
        if args.smoke:
            item = {k: (v[:patch, :patch] if isinstance(v, np.ndarray) else v) for k, v in item.items()}
        print(args.label, tile, "clean_reference", flush=True)
        clean_scores = infer_scores(net, item["optical"], item["dsm"], patch, stride, batch, False)
        clean_pred = clean_scores.argmax(0).astype(np.uint8)
        del clean_scores

        for spec in specs:
            print(args.label, tile, spec["name"], flush=True)
            treated, damage = apply_condition(item["dsm"], spec)
            if damage is None or not np.any(damage) or np.all(damage):
                raise RuntimeError("Expected a non-empty local damage mask: " + spec["name"])
            masks = region_masks(damage)
            corrupt_scores = infer_scores(net, item["optical"], treated, patch, stride, batch, False)
            corrupt_pred = corrupt_scores.argmax(0).astype(np.uint8)
            del corrupt_scores, treated
            for split_name, gt in (("full", item["full_gt"]), ("noboundary", item["noboundary_gt"])):
                for region, mask in masks.items():
                    clean_cm = confusion(gt, clean_pred, mask)
                    corrupt_cm = confusion(gt, corrupt_pred, mask)
                    base = dict(model=args.label, tile=tile, condition=spec["name"],
                                family=spec["family"], split=split_name, region=region)
                    add_pair(pair_rows, class_rows,
                             paired_outcomes(gt, clean_pred, corrupt_pred, mask),
                             base, clean_cm, corrupt_cm, r02)
                    key = (spec["name"], spec["family"], split_name, region)
                    if key not in aggregate:
                        aggregate[key] = [np.zeros((6, 6), np.int64), np.zeros((6, 6), np.int64)]
                    aggregate[key][0] += clean_cm
                    aggregate[key][1] += corrupt_cm
                    stem = "__".join((tile, spec["name"], split_name, region))
                    np.save(output / "confusion_matrices" / (stem + "__clean.npy"), clean_cm, allow_pickle=False)
                    np.save(output / "confusion_matrices" / (stem + "__corrupt.npy"), corrupt_cm, allow_pickle=False)
            write_csv(output / "paired_metrics.csv", pair_rows)
            write_csv(output / "paired_per_class_counts.csv", class_rows)
            del corrupt_pred
        del clean_pred, item

    for key, (clean_cm, corrupt_cm) in aggregate.items():
        condition, family, split_name, region = key
        base = dict(model=args.label, tile="ALL", condition=condition, family=family,
                    split=split_name, region=region)
        # Transition counts cannot be reconstructed from pooled CMs; leave them explicitly unavailable.
        empty_outcomes = {name: "" for name in paired_outcomes(
            np.array([[0]]), np.array([[0]]), np.array([[0]]), np.array([[True]])).keys()}
        empty_outcomes["valid_pixels"] = int(clean_cm.sum())
        add_pair(pair_rows, class_rows, empty_outcomes, base, clean_cm, corrupt_cm, r02)
        stem = "__".join(("ALL", condition, split_name, region))
        np.save(output / "confusion_matrices" / (stem + "__clean.npy"), clean_cm, allow_pickle=False)
        np.save(output / "confusion_matrices" / (stem + "__corrupt.npy"), corrupt_cm, allow_pickle=False)

    write_csv(output / "paired_metrics.csv", pair_rows)
    write_csv(output / "paired_per_class_counts.csv", class_rows)
    metadata.update(status="COMPLETE", completed_at=datetime.now().astimezone().isoformat())
    (output / "summary.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print("PAIRED_REGIONAL_EVAL_COMPLETE", output, flush=True)


if __name__ == "__main__":
    main()
