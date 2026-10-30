"""Inference-only DSM content intervention on frozen D13 Stage 1 heads."""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]
import numpy as np
import torch

import eval_rebuild_v1_d13_residual as d13
import train_rebuild_v1_r01_optical_only as r01
import train_rebuild_v1_r02_budget_pilot as r02
from d13_residual import ResidualHead
from d14_intervention import CONDITIONS, intervene, changed_predictions
from train_rebuild_v1_d13_residual import CONFIG as D13_CONFIG, load_anchor, run_dir, sha256

D14_CONFIG = ROOT / "configs/rebuild_v1/d14_dsm_intervention_20260926.json"
BASE = ROOT / "records/rebuild_v1_d14_dsm_intervention_20260926"
SOURCE = ROOT / "records/rebuild_v1_d13_compact_20260925"


def source_summary(arm, seed):
    original = r02.read_json(SOURCE / f"server_{arm}_seed{seed}_summary.json")
    if (original["arm"] != arm or original["seed"] != seed or
            original["train_steps"] != 4000 or original["test6_loaded"] is not False or
            original["git_commit"] != "afea788fe15bf5b3656ad8e36f58da282eecd4b8" or
            original["config_sha256"] != sha256(D13_CONFIG) or
            original["evaluation_source_sha256"] != sha256(ROOT / "scripts/eval_rebuild_v1_d13_residual.py")):
        raise RuntimeError(f"D13 source summary mismatch for {arm}/{seed}")
    for name, expected in original["training_source_sha256"].items():
        if sha256(ROOT / name) != expected:
            raise RuntimeError(f"D13 training source changed: {name}")
    return original


def load_head(arm, seed, original):
    run = run_dir(arm, seed)
    if str(run / "final_model.pth") != original["checkpoint"]:
        raise RuntimeError("D13 checkpoint path mismatch")
    if sha256(run / "final_model.pth") != original["checkpoint_sha256"]:
        raise RuntimeError("D13 checkpoint digest mismatch")
    state = torch.load(run / "final_model.pth", map_location="cpu")
    if (state["arm"] != arm or state["seed"] != seed or state["global_step"] != 4000):
        raise RuntimeError("D13 checkpoint metadata mismatch")
    head = ResidualHead().to(r02.DEVICE)
    head.load_state_dict(state["model"], strict=True)
    head.eval().requires_grad_(False)
    return head


def aggregate_flip(rows):
    count = sum(x["flip_count"] for x in rows)
    valid = sum(x["valid"] for x in rows)
    return dict(flip_count=count, valid=valid, flip_fraction=count / valid,
                flip_by_true_class=np.asarray([x["flip_by_true_class"] for x in rows],
                                              dtype=np.int64).sum(0).tolist(),
                support_by_true_class=np.asarray([x["support_by_true_class"] for x in rows],
                                                dtype=np.int64).sum(0).tolist())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=("rgb_ce", "dsm_ce", "rgb_risk", "dsm_risk"), required=True)
    ap.add_argument("--seed", type=int, choices=(42, 17), required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    cfg = r02.read_json(D14_CONFIG)
    if (args.arm not in cfg["arms"] or args.seed not in cfg["seeds"] or
            tuple(cfg["interventions"]) != CONDITIONS):
        raise RuntimeError("D14 frozen configuration mismatch")
    split = r02.read_json(ROOT / r02.read_json(D13_CONFIG)["split_file"])
    ids = list(split["val2"])
    if ids != ["3_11", "5_10"] or set(ids) & set(split["historical_exposed_test6"]):
        raise RuntimeError("Val2/Test6 boundary mismatch")
    original = source_summary(args.arm, args.seed)
    out = BASE / (f"smoke_{args.arm}_seed{args.seed}" if args.smoke else
                  f"{args.arm}_seed{args.seed}")
    out.resolve().relative_to(Path("/home/jovyan/zzx").resolve())
    if out.exists():
        raise FileExistsError(f"refusing to overwrite {out}")

    anchor, anchor_path, anchor_config = load_anchor(args.seed, r02.read_json(D13_CONFIG))
    if sha256(anchor_path) != original["anchor_sha256"]:
        raise RuntimeError("R01 anchor digest mismatch")
    head = load_head(args.arm, args.seed, original)
    patch = int(r02.read_json(D13_CONFIG)["training"]["patch"])
    stride = patch if args.smoke else int(r02.read_json(D13_CONFIG)["evaluation"]["stride"])
    batch = 1 if args.smoke else int(r02.read_json(D13_CONFIG)["evaluation"]["inference_batch"])
    tile_ids = ["6_7"] if args.smoke else ids
    rows = {condition: {} for condition in CONDITIONS}
    for tile in tile_ids:
        d = r02.load_tile(Path(anchor_config["data_root"]), tile, need_nb=not args.smoke)
        if args.smoke:
            d = {k: v[:patch, :patch] if getattr(v, "ndim", 0) >= 2 else v
                 for k, v in d.items()}
        optical = d["optical"]
        baseline = r01.infer_tile(anchor, optical, patch, stride, batch)
        clean_pred = None
        for condition in CONDITIONS:
            # RGB controls keep their original gray-Optical stream in every row.
            # DSM arms alter only content; missing=None keeps availability true.
            if args.arm.startswith("rgb_"):
                auxiliary = np.ascontiguousarray(optical.mean(axis=2).astype(np.float32))
                missing = None
            else:
                auxiliary, missing = intervene(d["dsm"], condition)
            if missing is not None:
                raise RuntimeError("D14 must never trigger missing-DSM fallback")
            pred = d13.infer_corrected(anchor, head, args.arm, optical, auxiliary,
                                       missing, patch, stride, batch)
            if clean_pred is None:
                clean_pred = pred
            by_scope = {}
            for scope, gt_key in (("full", "full_gt"), ("noboundary", "noboundary_gt")):
                if args.smoke and scope == "noboundary":
                    continue
                gt = d[gt_key]
                by_scope[scope] = dict(d13.metrics(gt, pred, baseline),
                                       comparison_to_clean=changed_predictions(gt, clean_pred, pred))
                if args.arm.startswith("rgb_") and by_scope[scope]["comparison_to_clean"]["flip_count"]:
                    raise RuntimeError("RGB negative control changed under a DSM-only intervention")
            rows[condition][tile] = by_scope
            print(f"D14 {args.arm} seed{args.seed} {tile} {condition} "
                  f"flips={by_scope['full']['comparison_to_clean']['flip_count']}", flush=True)

    data = {}
    for condition in CONDITIONS:
        entry = dict(tiles=rows[condition])
        for scope in (("full",) if args.smoke else ("full", "noboundary")):
            metrics = d13.aggregate([rows[condition][tile][scope] for tile in tile_ids])
            flips = aggregate_flip([rows[condition][tile][scope]["comparison_to_clean"]
                                    for tile in tile_ids])
            entry[scope] = dict(metrics, comparison_to_clean=flips)
        data[condition] = entry
    if not args.smoke:
        for scope in ("full", "noboundary"):
            clean = data["clean"][scope]
            expected = original["data"]["clean"][scope]
            for field in ("cm", "harm_count", "rescue_count"):
                if clean[field] != expected[field]:
                    raise RuntimeError(f"D13 clean reproduction mismatch: {scope}/{field}")
    result = dict(arm=args.arm, seed=args.seed, smoke=args.smoke, data=data,
                  d13_commit=original["git_commit"], d13_checkpoint=original["checkpoint"],
                  d13_checkpoint_sha256=original["checkpoint_sha256"],
                  d13_anchor_sha256=original["anchor_sha256"],
                  d13_config_sha256=original["config_sha256"],
                  d14_config_sha256=sha256(D14_CONFIG),
                  d14_source_sha256=sha256(ROOT / "scripts/eval_rebuild_v1_d14_intervention.py"),
                  run_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                                     text=True).strip(),
                  completed_at=datetime.now().astimezone().isoformat(timespec="seconds"),
                  availability_forced_present=True, val2_loaded=not args.smoke,
                  test6_loaded=False)
    out.mkdir(parents=True, exist_ok=False)
    (out / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("D14 COMPLETE", out, flush=True)


if __name__ == "__main__":
    main()
