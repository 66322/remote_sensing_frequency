"""Validation-only regional evaluation. Never uses GT for prediction/routing."""
import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
from rebuild_v1_b2_common import ROOT, fingerprint, region_masks, confusion, safe_output
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]


def write_csv(path, rows):
    if rows:
        with Path(path).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    import numpy as np
    import torch
    import train_rebuild_v1_r02_budget_pilot as r02
    from eval_rebuild_v1_d5_confidence_routing import specs, infer_scores, softmax_np
    from eval_rebuild_v1_d4_expert_complementarity import apply_condition

    out = safe_output(ROOT / args.out)
    cfg_path, run_dir = ROOT / args.config, ROOT / args.run_dir
    cfg = r02.read_json(cfg_path)
    summary = r02.read_json(run_dir / "summary.json")
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
    conditions = specs()
    if args.smoke:
        conditions = [s for s in conditions if s["name"] in ("clean", "dsm_local_zero_q1", "dsm_local_down8_q1")]
    out.mkdir(parents=True)
    (out / "confusion_matrices").mkdir()
    metadata = {
        "status": "RUNNING", "started_at": datetime.now().astimezone().isoformat(),
        "label": args.label, "config": cfg, "config_fingerprint": fingerprint(cfg_path),
        "checkpoint": fingerprint(checkpoint), "checkpoint_step": best["step"],
        "val_ids": ids, "smoke": args.smoke, "test6_loaded": False,
        "conditions": conditions, "boundary_radius_pixels": 8,
        "boundary_definition": "Synthetic corruption interface, +/-8 pixels, overlapping damaged/intact; not semantic class boundary",
        "inference": "Mean overlapping logits; argmax equivalent to original summed-logit predictions",
        "confidence_note": "T=1 softmax of mean tile logits; diagnostic only, no routing or selection",
        "high_confidence_thresholds": [0.7, 0.9, 0.95],
        "aggregation": "Pool int64 CMs over Val2, then calculate IoU; Clutter excluded from fg5",
        "source": fingerprint(Path(__file__)),
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    aggregate, region_rows, class_rows, confidence_rows = {}, [], [], []
    patch, stride, batch = cfg["patch"], cfg["validation"]["stride"], cfg["validation"]["inference_batch"]
    for tile in ids:
        item = r02.load_tile(Path(cfg["data_root"]), tile, need_nb=True)
        if args.smoke:
            # Fast execution smoke only: deterministic top-left crop, NOT formal Val2.
            item = {k: (v[:patch, :patch] if isinstance(v, np.ndarray) else v) for k, v in item.items()}
        for spec in conditions:
            print(args.label, tile, spec["name"], flush=True)
            treated, damage = apply_condition(item["dsm"], spec)
            if damage is None:
                damage = np.zeros(item["dsm"].shape, dtype=bool)
            masks = region_masks(damage)
            scores = infer_scores(net, item["optical"], treated, patch, stride, batch, False)
            probabilities = softmax_np(scores)
            pred = scores.argmax(0).astype(np.uint8)
            confidence = probabilities.max(0)
            del scores, probabilities
            for sp, gt in (("full", item["full_gt"]), ("noboundary", item["noboundary_gt"])):
                for region, mask in masks.items():
                    cm = confusion(gt, pred, mask)
                    key = (spec["name"], spec["family"], sp, region)
                    aggregate[key] = aggregate.get(key, np.zeros((6, 6), np.int64)) + cm
                    name = "__".join((tile, spec["name"], sp, region))
                    np.save(out / "confusion_matrices" / (name + ".npy"), cm, allow_pickle=False)
                    add_metrics(region_rows, class_rows, args.label, tile, key, cm, r02)
                    valid = mask & (gt >= 0) & (gt < 6)
                    n = int(valid.sum())
                    for threshold in (0.7, 0.9, 0.95):
                        accepted = valid & (confidence >= threshold)
                        selected = int(accepted.sum())
                        errors = int((accepted & (pred != gt)).sum())
                        confidence_rows.append({
                            "model": args.label, "tile": tile, "condition": spec["name"],
                            "family": spec["family"], "split": sp, "region": region,
                            "threshold": threshold, "valid_pixels": n,
                            "accepted_pixels": selected, "wrong_accepted_pixels": errors,
                            "coverage": selected / n if n else "",
                            "accepted_error_rate": errors / selected if selected else "",
                        })
            # Persist completed tile/condition rows even if a later condition crashes.
            write_csv(out / "region_metrics.csv", region_rows)
            write_csv(out / "per_class_counts.csv", class_rows)
            write_csv(out / "confidence_diagnostics.csv", confidence_rows)
            del pred, confidence, treated
        del item
    for key, cm in aggregate.items():
        name = "__".join(("ALL", key[0], key[2], key[3]))
        np.save(out / "confusion_matrices" / (name + ".npy"), cm, allow_pickle=False)
        add_metrics(region_rows, class_rows, args.label, "ALL", key, cm, r02)
    write_csv(out / "region_metrics.csv", region_rows)
    write_csv(out / "per_class_counts.csv", class_rows)
    metadata.update(status="COMPLETE", completed_at=datetime.now().astimezone().isoformat())
    (out / "summary.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print("REGIONAL_EVAL_COMPLETE", out, flush=True)


def add_metrics(rows, classes, label, tile, key, cm, r02):
    condition, family, sp, region = key
    base = dict(model=label, tile=tile, condition=condition, family=family, split=sp, region=region)
    total = int(cm.sum())
    # Empty regions are NA, never zero-score successes/failures.
    mt = r02.metrics_from_cm(cm) if total else {}
    rows.append(dict(base, valid_pixels=total, mIoU_fg5=mt.get("mIoU_fg5", ""),
                     mIoU_all6=mt.get("mIoU_all6", ""), OA=mt.get("OA", "")))
    for i, class_name in enumerate(r02.CLASS_NAMES):
        tp = int(cm[i, i])
        support, predicted = int(cm[i].sum()), int(cm[:, i].sum())
        union = support + predicted - tp
        classes.append(dict(base, class_index=i, class_name=class_name, TP=tp,
                            FP=predicted-tp, FN=support-tp, support=support, union=union,
                            IoU=tp/union if union else ""))


if __name__ == "__main__":
    main()

