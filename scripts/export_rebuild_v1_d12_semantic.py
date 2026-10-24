"""Export matched frozen decoder features for D11 development and D10M Val2 samples."""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import torch
import eval_rebuild_v1_d9a_benefit as d9a
import train_rebuild_v1_r01_optical_only as r01
import train_rebuild_v1_r02_budget_pilot as r02
from d10m_mechanism import translate
from d11_benefit_probe import checkpoint_identity, validate_roles
from d12_semantic import infer_at_pixels
from eval_rebuild_v1_d4_expert_complementarity import validate_run
from eval_rebuild_v1_d5_confidence_routing import softmax_np

ROOT = d9a.ROOT
CFG = ROOT / "configs/rebuild_v1/d12_night_20260923.json"
D11 = ROOT / "records/rebuild_v1_d11_benefit_probe_20260923"
D10 = ROOT / "records/rebuild_v1_d10m_mechanism_20260923"
BASE = ROOT / "records/rebuild_v1_d12_night_20260923"


def treated_dsm(dsm, condition, tile):
    if condition.startswith("roll"):
        return translate(dsm, int(condition[4:]), True)
    return d9a.condition_dsm(dsm, condition, tile)[0]


def source(cfg, seed, tile, condition, role):
    if role == "evaluation":
        folder = D10 / f"seed{seed}_{condition}"
        meta = json.loads((folder / "summary.json").read_text())
        if meta["seed"] != seed or meta["condition"] != condition or meta["test6_loaded"] or meta["smoke"]:
            raise RuntimeError("D10M source manifest mismatch")
        path = folder / f"samples_{tile}.npz"
    else:
        folder = D11 / "development" / f"seed{seed}_{tile}"
        meta = json.loads((folder / "summary.json").read_text())
        if meta["seed"] != seed or meta["tile"] != tile or meta["role"] != role or meta["smoke"] or meta["test6_loaded"] or meta["val2_loaded"]:
            raise RuntimeError("D11 development manifest mismatch")
        path = folder / f"{condition}.npz"
        if hashlib.sha256(path.read_bytes()).hexdigest() != meta["files_sha256"][path.name]:
            raise RuntimeError("D11 source hash mismatch")
    with np.load(path, allow_pickle=False) as data:
        yy, xx = data["yy"].copy(), data["xx"].copy()
        expected_rgb = data["rgb_prob"].copy()
        expected_dual = data["dual_prob"].copy()
    return path, meta, yy, xx, expected_rgb, expected_dual


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, choices=(17, 42), required=True)
    parser.add_argument("--tile", required=True)
    parser.add_argument("--condition", required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    cfg = json.loads(CFG.read_text())
    split = json.loads((ROOT / "configs/rebuild_v1/potsdam_split_seed20260915.json").read_text())
    validate_roles(cfg, split)
    role = next((key for key in ("fit", "probability_calibration", "threshold_calibration", "evaluation")
                 if args.tile in cfg[key]), None)
    if role is None or args.condition not in cfg["development_conditions" if role != "evaluation" else "evaluation_conditions"]:
        raise ValueError("unplanned tile or condition")
    out = BASE / "semantic" / f"seed{args.seed}_{args.tile}_{args.condition}{'_smoke' if args.smoke else ''}"
    out.resolve().relative_to(Path("/home/jovyan/zzx").resolve())
    if out.exists():
        raise FileExistsError(out)
    path, meta, yy, xx, expected_rgb, expected_dual = source(cfg, args.seed, args.tile, args.condition, role)
    if args.smoke:
        yy, xx = yy[:256], xx[:256]
        expected_rgb, expected_dual = expected_rgb[:, :256], expected_dual[:, :256]
    c1 = r02.read_json(ROOT / "configs/rebuild_v1/r01_optical_only_16k.json")
    c5 = r02.read_json(ROOT / "configs/rebuild_v1/r05_quality_plus_dropout_16k.json")
    _, ck1 = validate_run(ROOT / f"runs/rebuild_v1/R01_optical_only_seed{args.seed}_sched16000_stop16000")
    _, ck5 = validate_run(ROOT / f"runs/rebuild_v1/R05_dual_f0_quality_plus_dropout_seed{args.seed}_sched16000_stop16000")
    s1, s5 = torch.load(ck1, map_location="cpu"), torch.load(ck5, map_location="cpu")
    identity = dict(checkpoint_rgb=str(ck1), checkpoint_dual=str(ck5),
                    checkpoint_steps=[int(s1["global_step"]), int(s5["global_step"])])
    checkpoint_identity(meta, identity)
    net1, _, _ = r01.build_model(c1, Path(c1["pretrain"]), resume_state=s1)
    net5, _ = r02.build_model(c5, Path(c5["pretrain"]), resume_state=s5)
    net1.eval(); net5.eval()
    d = r02.load_tile(Path(c5["data_root"]), args.tile, need_nb=True)
    with np.load(path, allow_pickle=False) as source_data:
        source_labels = source_data["labels"][:len(yy)]
    if not np.array_equal(d["noboundary_gt"][yy, xx], source_labels):
        raise RuntimeError("semantic and probability sample coordinates differ")
    treated = treated_dsm(d["dsm"], args.condition, args.tile)
    patch = int(c5["patch"])
    stride = int(c5["validation"]["stride"])
    batch = int(c5["validation"]["inference_batch"])
    if args.condition == "clean":
        sem1, score1 = infer_at_pixels(net1, d["optical"], d["dsm"], yy, xx, patch, stride, batch, True, True)
        err1 = float(np.max(np.abs(softmax_np(score1) - expected_rgb)))
    else:
        clean_folder = BASE / "semantic" / f"seed{args.seed}_{args.tile}_clean{'_smoke' if args.smoke else ''}"
        clean_meta = json.loads((clean_folder / "summary.json").read_text())
        with np.load(clean_folder / "semantic.npz", allow_pickle=False) as cached:
            if (clean_meta["checkpoint_identity"] != identity or
                    not np.array_equal(cached["yy"], yy) or not np.array_equal(cached["xx"], xx)):
                raise RuntimeError("clean RGB semantic cache mismatch")
            sem1 = cached["sem_rgb"].copy()
        err1 = clean_meta["max_probability_error"][0]
    sem5, score5 = infer_at_pixels(net5, d["optical"], treated, yy, xx, patch, stride, batch, False, True)
    # D11/D10M cache probabilities must match the same selected checkpoints.
    # Small floating point differences are expected from accumulation order.
    err5 = float(np.max(np.abs(softmax_np(score5) - expected_dual)))
    if err1 > 2e-4 or err5 > 2e-4:
        raise RuntimeError(f"frozen probability mismatch: RGB={err1}, dual={err5}")
    out.mkdir(parents=True, exist_ok=False)
    artifact = out / "semantic.npz"
    np.savez_compressed(artifact, yy=yy, xx=xx, sem_rgb=sem1, sem_dual=sem5)
    summary = dict(seed=args.seed, tile=args.tile, condition=args.condition, role=role, smoke=args.smoke,
                   sample_n=len(yy), source=str(path), source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   semantic_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
                   config_sha256=hashlib.sha256(CFG.read_bytes()).hexdigest(),
                   checkpoint_identity=identity, max_probability_error=[err1, err5],
                   test6_loaded=False, git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip())
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("D12 SEMANTIC COMPLETE", out, flush=True)


if __name__ == "__main__":
    main()
