"""Paired RGB degradation evaluation on frozen experts and the D15 DSM baseline."""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import numpy as np
import torch
import train_rebuild_v1_r01_optical_only as r01
import train_rebuild_v1_r02_budget_pilot as r02
import train_rebuild_v1_d15_dsm_only as d15
from d15_capability import as_three_channels, condition_data, joint, second_stream

CONFIG = ROOT / "configs/rebuild_v1/d15_capability_20260926.json"


def run_for(model, seed):
    runs = ROOT / "runs/rebuild_v1"
    if model == "R01":
        name, cfg = f"R01_optical_only_seed{seed}_sched16000_stop16000", "r01_optical_only_16k.json"
    elif model == "R05":
        name, cfg = f"R05_dual_f0_quality_plus_dropout_seed{seed}_sched16000_stop16000", "r05_quality_plus_dropout_16k.json"
    elif model == "C-OO-QD":
        name, cfg = f"C_OO_QD_dual_optical_gray_quality_plus_dropout_seed{seed}_sched16000_stop16000", "c_oo_qd_optical_gray_16k.json"
    elif model == "D15_DSM_ONLY":
        return d15.run_dir(seed), ROOT / "configs/rebuild_v1/r01_optical_only_16k.json"
    else:
        raise ValueError(model)
    return runs / name, ROOT / "configs/rebuild_v1" / cfg


def load_model(model, seed):
    path, config_path = run_for(model, seed)
    cfg = r02.read_json(config_path)
    summary = r02.read_json(path / "summary.json")
    if int(summary.get("global_step", -1)) != 16000 or summary.get("test6_loaded") is not False:
        raise RuntimeError(f"incomplete or unsafe model: {path}")
    ck = path / "best_model.pth"
    state = torch.load(ck, map_location="cpu")
    if model in ("R01", "D15_DSM_ONLY"):
        net, _, _ = r01.build_model(cfg, Path(cfg["pretrain"]), resume_state=state)
    else:
        net, _ = r02.build_model(cfg, Path(cfg["pretrain"]), resume_state=state)
    net.eval()
    if model == "D15_DSM_ONLY" and state.get("signature", {}).get("experiment") != "D15_DSM_ONLY":
        raise RuntimeError("D15 checkpoint signature mismatch")
    return net, cfg, dict(path=str(ck), sha256=d15.sha256(ck),
                          step=state["global_step"], config_sha256=d15.sha256(config_path),
                          clean_cm_full=state.get("metrics", {}).get("cm_full"),
                          clean_cm_noboundary=state.get("metrics", {}).get("cm_noboundary"))


def predict(model, net, op, ds, cfg):
    patch = int(cfg["patch"])
    stride = int(cfg["validation"]["stride"])
    batch = int(cfg["validation"]["inference_batch"])
    if model == "R01":
        return r01.infer_tile(net, op, patch, stride, batch)
    if model == "D15_DSM_ONLY":
        return r01.infer_tile(net, as_three_channels(ds), patch, stride, batch)
    secondary = second_stream(model, op, ds)
    return r02.infer_tile(net, op, secondary, patch, stride, batch)


def metrics(gt, pred):
    cm = np.zeros((6, 6), dtype=np.int64)
    r02.update_cm(cm, gt, pred)
    return cm


def safe_metrics(cm):
    result = r02.metrics_from_cm(cm)
    return {key: (None if isinstance(value, float) and not np.isfinite(value) else value)
            for key, value in result.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=("R01", "R05", "C-OO-QD", "D15_DSM_ONLY"), required=True)
    ap.add_argument("--seed", type=int, choices=(42, 17), required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("D15 expects exactly one visible GPU")
    protocol = r02.read_json(CONFIG)
    split = r02.read_json(ROOT / protocol["split_file"])
    ids = list(split["val2"])
    if len(ids) != 2 or set(ids) & set(split["historical_exposed_test6"]):
        raise RuntimeError("Val2/Test6 boundary failed")
    if args.smoke:
        ids = ids[:1]
    out = ROOT / "records/rebuild_v1_d15_capability_20260926" / (
        f"smoke_{args.model}_seed{args.seed}" if args.smoke else f"{args.model}_seed{args.seed}")
    if out.exists():
        raise FileExistsError(out)
    # Match the training-validation CUDA/cuDNN settings before building models.
    # r02.set_seed also enables deterministic algorithms and disables benchmark.
    r02.set_seed(args.seed)
    net, cfg, binding = load_model(args.model, args.seed)
    ref_net, ref_cfg, ref_binding = (net, cfg, binding) if args.model == "R01" else load_model("R01", args.seed)
    raw = {}
    for condition in protocol["rgb_conditions"]:
        tiles = {}
        pooled = {scope: np.zeros((6, 6), dtype=np.int64) for scope in ("full", "noboundary")}
        oracle_pooled = {scope: np.zeros((6, 6), dtype=np.int64) for scope in pooled}
        total_joint = {k: 0 for k in ("valid", "both_correct", "only_r01_correct", "only_candidate_correct", "both_wrong")}
        for tile in ids:
            item = r02.load_tile(Path(cfg["data_root"]), tile, need_nb=True)
            if args.smoke:
                item = {k: v[:512, :512] if getattr(v, "ndim", 0) >= 2 else v for k, v in item.items()}
            op, ds = condition_data(item["optical"], item["dsm"], condition)
            pred = predict(args.model, net, op, ds, cfg)
            ref = pred if args.model == "R01" else predict("R01", ref_net, op, ds, ref_cfg)
            tile_metrics = {}
            for scope, label in (("full", item["full_gt"]), ("noboundary", item["noboundary_gt"])):
                cm = metrics(label, pred)
                pooled[scope] += cm
                oracle = np.where(pred == label, pred, ref)
                oracle_cm = metrics(label, oracle)
                oracle_pooled[scope] += oracle_cm
                tile_metrics[scope] = dict(cm=cm.tolist(), metrics=safe_metrics(cm),
                                           oracle_cm=oracle_cm.tolist(), oracle_metrics=safe_metrics(oracle_cm))
            counts = joint(item["noboundary_gt"], ref, pred)
            for key in total_joint:
                total_joint[key] += counts[key]
            tiles[tile] = dict(metrics=tile_metrics, joint_noboundary=counts)
            print(f"D15 {args.model} seed{args.seed} {condition} {tile}", flush=True)
        raw[condition] = dict(tiles=tiles, joint_noboundary=total_joint,
                              pooled={scope: dict(cm=cm.tolist(), metrics=safe_metrics(cm),
                                                  oracle_cm=oracle_pooled[scope].tolist(),
                                                  oracle_metrics=safe_metrics(oracle_pooled[scope]))
                                      for scope, cm in pooled.items()})
        if condition == "clean" and not args.smoke and args.model in ("R01", "D15_DSM_ONLY"):
            diagnostic = dict(model=args.model, seed=args.seed, checkpoint=binding,
                              source_sha256=d15.sha256(Path(__file__)), scopes={})
            passed = True
            for scope, key in (("full", "clean_cm_full"), ("noboundary", "clean_cm_noboundary")):
                expected = binding[key]
                actual = pooled[scope]
                match = expected is not None and np.array_equal(actual, np.asarray(expected, dtype=np.int64))
                passed = passed and match
                diagnostic["scopes"][scope] = dict(
                    exact_match=match, expected_cm=expected, actual_cm=actual.tolist(),
                    difference_cm=None if expected is None else
                    (actual - np.asarray(expected, dtype=np.int64)).tolist())
            diagnostic["pass"] = passed
            diagnostic_path = ROOT / "records/rebuild_v1_d15_capability_20260926/diagnostics" / f"{args.model}_seed{args.seed}_clean.json"
            diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
            diagnostic_path.write_text(json.dumps(diagnostic, indent=2, allow_nan=False) + "\n")
            if not passed:
                raise RuntimeError(f"clean checkpoint metric reproduction failed; details: {diagnostic_path}")
            print("D15 CLEAN REPRODUCTION PASS", flush=True)
    result = dict(model=args.model, seed=args.seed, smoke=args.smoke, conditions=raw,
                  checkpoint=binding, r01_checkpoint=ref_binding,
                  config_sha256=d15.sha256(CONFIG), source_sha256=d15.sha256(Path(__file__)),
                  git_commit=r01.git_head(), val2_loaded=True, test6_loaded=False,
                  physical_gpu=os.environ["CUDA_VISIBLE_DEVICES"])
    out.mkdir(parents=True, exist_ok=False)
    (out / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("D15 EVAL COMPLETE", out, flush=True)


if __name__ == "__main__":
    main()
