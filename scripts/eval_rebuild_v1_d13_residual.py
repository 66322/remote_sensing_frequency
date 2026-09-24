"""Evaluate a completed D13 final checkpoint on complete Val2 images."""
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

import eval_rebuild_v1_d9a_benefit as d9a
import train_rebuild_v1_r01_optical_only as r01
import train_rebuild_v1_r02_budget_pilot as r02
from d13_residual import ARMS, ResidualHead, features_for_arm, apply_residual, known_missing_mask
from train_rebuild_v1_d13_residual import CONFIG, RUN_LABEL, load_anchor, run_dir, sha256

BASE = ROOT / f"records/rebuild_v1_d13_residual_{RUN_LABEL}"


def conditioned_auxiliary(source, condition, tile):
    if condition == "roll16":
        return np.ascontiguousarray(np.roll(source, 16, axis=1)), None
    treated, region_mask = d9a.condition_dsm(source, condition, tile)
    # The D9A helper also returns the *damaged* region for local downsampling.
    # Downsampled DSM is available; only actual absence may force RGB fallback.
    missing = known_missing_mask(condition, region_mask)
    return np.ascontiguousarray(treated), missing


def infer_corrected(anchor, head, arm, optical, auxiliary, missing, patch, stride, batch):
    h, w = auxiliary.shape
    if optical.shape[:2] != (h, w):
        raise ValueError("misaligned input")
    if missing is not None and np.shape(missing) != (h, w):
        raise ValueError("misaligned missingness mask")
    scores = np.zeros((6, h, w), np.float32)
    decoder = []
    handle = anchor.decoder.register_forward_hook(lambda _m, _i, x: decoder.append(x))
    coords = [(y, x) for y in r02.positions(h, patch, stride)
                    for x in r02.positions(w, patch, stride)]
    try:
        with torch.inference_mode():
            for start in range(0, len(coords), batch):
                bc = coords[start:start+batch]
                op = np.stack([optical[y:y+patch, x:x+patch].transpose(2, 0, 1)
                               for y, x in bc])
                au = np.stack([auxiliary[y:y+patch, x:x+patch] for y, x in bc])
                if missing is None:
                    av = np.ones((len(bc), patch, patch), bool)
                else:
                    av = np.stack([~missing[y:y+patch, x:x+patch] for y, x in bc])
                op_t = torch.from_numpy(np.ascontiguousarray(op)).to(r02.DEVICE)
                au_t = torch.from_numpy(np.ascontiguousarray(au)).to(r02.DEVICE)
                av_t = torch.from_numpy(np.ascontiguousarray(av)).to(r02.DEVICE)
                decoder.clear()
                z0 = anchor(op_t)
                if len(decoder) != 1:
                    raise RuntimeError("R01 decoder hook returned unexpected count")
                feat = features_for_arm(arm, z0, op_t, au_t[:, None], decoder.pop())
                z = apply_residual(z0, head(feat), av_t)
                if not bool(torch.isfinite(z).all()):
                    raise RuntimeError("nonfinite D13 inference logits")
                if not torch.equal(z.masked_select(~av_t[:, None].expand_as(z)),
                                   z0.masked_select(~av_t[:, None].expand_as(z))):
                    raise RuntimeError("known-missing RGB fallback mismatch")
                values = z.cpu().numpy()
                for value, (y, x) in zip(values, bc):
                    scores[:, y:y+patch, x:x+patch] += value
    finally:
        handle.remove()
    return scores.argmax(axis=0).astype(np.uint8)


def metrics(gt, pred, baseline):
    cm = np.zeros((6, 6), np.int64)
    r02.update_cm(cm, gt, pred)
    valid = (gt != 255) & (gt < 6)
    correct0 = baseline == gt
    correct = pred == gt
    harm = np.bincount(gt[valid & correct0 & ~correct], minlength=6).astype(np.int64)
    rescue = np.bincount(gt[valid & ~correct0 & correct], minlength=6).astype(np.int64)
    support = np.bincount(gt[valid], minlength=6).astype(np.int64)
    return dict(cm=cm.tolist(), metrics=r02.metrics_from_cm(cm), valid=int(valid.sum()),
                harm_count=int(harm.sum()), rescue_count=int(rescue.sum()),
                harm_by_true_class=harm.tolist(), rescue_by_true_class=rescue.tolist(),
                support_by_true_class=support.tolist(),
                H=float(harm.sum()/valid.sum()), R=float(rescue.sum()/valid.sum()))


def aggregate(rows):
    cm = sum((np.asarray(x["cm"], np.int64) for x in rows), np.zeros((6, 6), np.int64))
    valid = sum(x["valid"] for x in rows)
    harm = sum(x["harm_count"] for x in rows)
    rescue = sum(x["rescue_count"] for x in rows)
    return dict(cm=cm.tolist(), metrics=r02.metrics_from_cm(cm), valid=valid,
                harm_count=harm, rescue_count=rescue, H=harm/valid, R=rescue/valid,
                harm_by_true_class=np.asarray([x["harm_by_true_class"] for x in rows]).sum(0).tolist(),
                rescue_by_true_class=np.asarray([x["rescue_by_true_class"] for x in rows]).sum(0).tolist(),
                support_by_true_class=np.asarray([x["support_by_true_class"] for x in rows]).sum(0).tolist())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--seed", type=int, choices=(42, 17), required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    cfg = r02.read_json(CONFIG)
    split = r02.read_json(ROOT / cfg["split_file"])
    ids = list(split["val2"])
    if ids != ["3_11", "5_10"] or set(ids) & set(split["historical_exposed_test6"]):
        raise RuntimeError("D13 evaluation split mismatch")
    training = run_dir(args.arm, args.seed, 2 if args.smoke else 0)
    summary = r02.read_json(training / "summary.json")
    expected_steps = 2 if args.smoke else int(cfg["training"]["steps"])
    if summary["global_step"] != expected_steps or summary["test6_loaded"] is not False:
        raise RuntimeError("D13 training incomplete")
    if summary["config_sha256"] != sha256(CONFIG):
        raise RuntimeError("D13 config changed since training")
    anchor, anchor_path, anchor_config = load_anchor(args.seed, cfg)
    if summary["anchor_sha256"] != sha256(anchor_path):
        raise RuntimeError("D13 R01 checkpoint changed since training")
    for name, expected in summary["source_sha256"].items():
        if sha256(ROOT / name) != expected:
            raise RuntimeError(f"D13 training source changed since run: {name}")
    checkpoint = training / "final_model.pth"
    state = torch.load(checkpoint, map_location="cpu")
    if state["arm"] != args.arm or state["seed"] != args.seed or state["global_step"] != summary["global_step"]:
        raise RuntimeError("D13 final checkpoint mismatch")
    head = ResidualHead().to(r02.DEVICE)
    head.load_state_dict(state["model"], strict=True)
    head.eval()
    if args.smoke:
        d = r02.load_tile(Path(anchor_config["data_root"]), "6_7", need_nb=False)
        patch = int(cfg["training"]["patch"])
        optical = d["optical"][:patch, :patch]
        source = d["dsm"][:patch, :patch]
        truth = d["full_gt"][:patch, :patch]
        anchor_pred = r01.infer_tile(anchor, optical, patch, patch, 1)
        smoke_rows = {}
        for condition in cfg["evaluation"]["conditions"]:
            auxiliary, missing = conditioned_auxiliary(source, condition, "6_7")
            pred = infer_corrected(anchor, head, args.arm, optical, auxiliary,
                                   missing, patch, patch, 1)
            if missing is not None and not np.array_equal(pred[missing], anchor_pred[missing]):
                raise RuntimeError("D13 smoke fallback mismatch")
            smoke_rows[condition] = dict(metrics(truth, pred, anchor_pred))
        smoke_out = BASE / "smoke_eval_seed42"
        if smoke_out.exists():
            raise FileExistsError(smoke_out)
        smoke_out.mkdir(parents=True, exist_ok=False)
        (smoke_out / "summary.json").write_text(json.dumps(dict(smoke=True, tile="6_7",
            arm=args.arm, seed=args.seed, conditions=smoke_rows, val2_loaded=False,
            test6_loaded=False), indent=2, allow_nan=False)+"\n")
        print("D13 EVAL SMOKE COMPLETE", smoke_out, flush=True)
        return
    out = BASE / f"{args.arm}_seed{args.seed}"
    out.resolve().relative_to(Path("/home/jovyan/zzx").resolve())
    if out.exists():
        raise FileExistsError(f"refusing to overwrite {out}")
    out.mkdir(parents=True, exist_ok=False)
    patch = int(cfg["training"]["patch"])
    stride = int(cfg["evaluation"]["stride"])
    batch = int(cfg["evaluation"]["inference_batch"])
    tiles = {tile: r02.load_tile(Path(anchor_config["data_root"]), tile, need_nb=True)
             for tile in ids}
    baseline = {tile: r01.infer_tile(anchor, d["optical"], patch, stride, batch)
                for tile, d in tiles.items()}
    data = {}
    for condition in cfg["evaluation"]["conditions"]:
        print(f"D13 EVAL {args.arm} seed{args.seed} {condition}", flush=True)
        by_tile = {}
        for tile, d in tiles.items():
            source = d["optical"].mean(axis=2).astype(np.float32) if args.arm.startswith("rgb_") else d["dsm"]
            auxiliary, missing = conditioned_auxiliary(source, condition, tile)
            pred = infer_corrected(anchor, head, args.arm, d["optical"], auxiliary,
                                   missing, patch, stride, batch)
            if missing is not None and not np.array_equal(pred[missing], baseline[tile][missing]):
                raise RuntimeError("missing-region prediction differs from R01")
            by_tile[tile] = dict(full=metrics(d["full_gt"], pred, baseline[tile]),
                                 noboundary=metrics(d["noboundary_gt"], pred, baseline[tile]))
        data[condition] = dict(tiles=by_tile,
                               full=aggregate([by_tile[t]["full"] for t in ids]),
                               noboundary=aggregate([by_tile[t]["noboundary"] for t in ids]))
        print(f"  NB={100*data[condition]['noboundary']['metrics']['mIoU_fg5']:.4f} "
              f"H={100*data[condition]['noboundary']['H']:.4f} "
              f"R={100*data[condition]['noboundary']['R']:.4f}", flush=True)
    baseline_by_tile = {tile: dict(full=metrics(d["full_gt"], baseline[tile], baseline[tile]),
                                   noboundary=metrics(d["noboundary_gt"], baseline[tile], baseline[tile]))
                        for tile, d in tiles.items()}
    baseline_pooled = {kind: aggregate([baseline_by_tile[t][kind] for t in ids])
                       for kind in ("full", "noboundary")}
    result = dict(arm=args.arm, seed=args.seed, data=data, baseline=baseline_pooled,
                  baseline_per_tile=baseline_by_tile, train_summary=str(training / "summary.json"),
                  train_steps=summary["global_step"],
                  initial_head_sha256=summary["initial_head_sha256"],
                  treatment_counts=summary["treatment_counts"],
                  training_source_sha256=summary["source_sha256"],
                  evaluation_source_sha256=sha256(ROOT / "scripts/eval_rebuild_v1_d13_residual.py"),
                  checkpoint=str(checkpoint), checkpoint_sha256=sha256(checkpoint),
                  anchor_checkpoint=str(anchor_path), anchor_sha256=sha256(anchor_path),
                  config_sha256=sha256(CONFIG),
                  git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                                     text=True).strip(),
                  completed_at=datetime.now().astimezone().isoformat(timespec="seconds"),
                  val2_only=True, test6_loaded=False,
                  second_stream="optical_gray" if args.arm.startswith("rgb_") else "DSM")
    (out / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("D13 EVAL COMPLETE", out, flush=True)


if __name__ == "__main__":
    main()
