"""Export head-development observations from Train16; never load Val2/Test6."""
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
from d10m_mechanism import sampled_structure
from d11_benefit_probe import validate_roles
from eval_rebuild_v1_d4_expert_complementarity import validate_run
from eval_rebuild_v1_d5_confidence_routing import infer_scores, softmax_np

ROOT = d9a.ROOT
CONFIG = ROOT / "configs/rebuild_v1/d11_supervised_benefit_probe.json"
BASE = ROOT / "records/rebuild_v1_d11_benefit_probe_20260923"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, choices=(17,42), required=True)
    ap.add_argument("--tile", required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    cfg = json.loads(CONFIG.read_text())
    c1 = r02.read_json(ROOT / "configs/rebuild_v1/r01_optical_only_16k.json")
    c5 = r02.read_json(ROOT / "configs/rebuild_v1/r05_quality_plus_dropout_16k.json")
    split = r02.read_json(ROOT / c5["split_file"])
    validate_roles(cfg, split)
    role = next((r for r in ("fit", "probability_calibration", "threshold_calibration") if args.tile in cfg[r]), None)
    if role is None:
        raise ValueError("Only predefined Train16 development tiles can be exported")
    out = BASE / "development" / (f"seed{args.seed}_{args.tile}" + ("_smoke" if args.smoke else ""))
    out.resolve().relative_to(Path("/home/jovyan/zzx").resolve())
    if out.exists():
        raise FileExistsError(out)
    completed1, ck1 = validate_run(ROOT / f"runs/rebuild_v1/R01_optical_only_seed{args.seed}_sched16000_stop16000")
    completed5, ck5 = validate_run(ROOT / f"runs/rebuild_v1/R05_dual_f0_quality_plus_dropout_seed{args.seed}_sched16000_stop16000")
    s1, s5 = torch.load(ck1, map_location="cpu"), torch.load(ck5, map_location="cpu")
    net1, _, _ = r01.build_model(c1, Path(c1["pretrain"]), resume_state=s1)
    net5, _ = r02.build_model(c5, Path(c5["pretrain"]), resume_state=s5)
    net1.eval(); net5.eval()
    d = r02.load_tile(Path(c5["data_root"]), args.tile, need_nb=True)
    gt = d["noboundary_gt"]
    valid = np.flatnonzero((gt != r02.IGNORE_INDEX) & (gt < r02.N_CLASSES))
    n = min(len(valid), 1000 if args.smoke else cfg["samples_per_development_tile"])
    if not n:
        raise ValueError("no valid NoBoundary pixels")
    rng = np.random.default_rng(20260923 + int(args.tile.replace("_", "")))
    sample = rng.choice(valid, n, replace=False)
    yy, xx = np.unravel_index(sample, gt.shape)
    patch, stride, batch = int(c5["patch"]), int(c5["validation"]["stride"]), int(c5["validation"]["inference_batch"])
    full_rgb = softmax_np(infer_scores(net1, d["optical"], d["dsm"], patch, stride, batch, True))
    rgb = full_rgb[:, yy, xx].copy()
    del full_rgb
    out.mkdir(parents=True, exist_ok=False)
    conditions = cfg["development_conditions"][:1] if args.smoke else cfg["development_conditions"]
    hashes = {}
    for condition in conditions:
        print(f"D11 EXPORT seed={args.seed} role={role} tile={args.tile} condition={condition}", flush=True)
        treated, _ = d9a.condition_dsm(d["dsm"], condition, args.tile)
        full_dual = softmax_np(infer_scores(net5, d["optical"], treated, patch, stride, batch, False))
        dual = full_dual[:, yy, xx].copy()
        del full_dual
        observable = sampled_structure(d["optical"], treated, yy, xx)
        path = out / f"{condition}.npz"
        np.savez_compressed(path, yy=yy, xx=xx, labels=gt[yy,xx], rgb_prob=rgb, dual_prob=dual, **observable)
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    meta = dict(seed=args.seed, tile=args.tile, role=role, smoke=args.smoke, conditions=conditions,
                test6_loaded=False, val2_loaded=False, expert_training_exposed=True,
                checkpoint_rgb=str(ck1), checkpoint_dual=str(ck5),
                checkpoint_steps=[int(s.get("global_step",-1)) for s in (s1,s5)],
                training_completed_steps=[int(s["global_step"]) for s in (completed1,completed5)],
                config_sha256=hashlib.sha256(CONFIG.read_bytes()).hexdigest(), sample_n=n,
                files_sha256=hashes, commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip())
    (out/"summary.json").write_text(json.dumps(meta,indent=2)+"\n")
    print("D11 EXPORT COMPLETE",out,flush=True)


if __name__ == "__main__":
    main()
