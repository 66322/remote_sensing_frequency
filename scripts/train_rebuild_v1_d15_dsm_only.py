"""Matched R01 architecture/schedule using R02-normalized DSM as three channels."""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import numpy as np
import torch
import torch.nn.functional as F
import train_rebuild_v1_r01_optical_only as r01
import train_rebuild_v1_r02_budget_pilot as r02
from d15_capability import as_three_channels

CONFIG = ROOT / "configs/rebuild_v1/d15_capability_20260926.json"


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def preload(data_root, train_ids, val_ids):
    train, val = {}, {}
    for tile in train_ids:
        d = r02.load_tile(data_root, tile, need_nb=False)
        train[tile] = (as_three_channels(d["dsm"]), d["full_gt"])
    for tile in val_ids:
        d = r02.load_tile(data_root, tile, need_nb=True)
        val[tile] = {"optical": as_three_channels(d["dsm"]),
                     "full_gt": d["full_gt"], "noboundary_gt": d["noboundary_gt"]}
    return train, val


def run_dir(seed, smoke=False):
    suffix = "_smoke" if smoke else ""
    return ROOT / f"runs/rebuild_v1/D15_dsm_only_seed{seed}_sched16000_stop16000{suffix}"


def save_atomic(path, net, optimizer, step, best, signature):
    temporary = path.with_suffix(".tmp")
    r02.save_state(temporary, net, optimizer, step, best, signature)
    temporary.replace(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, choices=(42, 17), required=True)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--smoke-steps", type=int, default=0)
    args = ap.parse_args()
    protocol = r02.read_json(CONFIG)
    cfg = r02.read_json(ROOT / protocol["base_config"])
    cfg["seed"] = args.seed
    split = r02.read_json(ROOT / protocol["split_file"])
    train_ids, val_ids = list(split["train16"]), list(split["val2"])
    if (len(train_ids), len(val_ids)) != (16, 2) or set(train_ids) & set(val_ids):
        raise RuntimeError("expected disjoint Train16/Val2")
    if (set(train_ids) | set(val_ids)) & set(split["historical_exposed_test6"]):
        raise RuntimeError("Test6 boundary violation")
    if cfg["schedule"]["stop_at_step"] != protocol["training_steps"]:
        raise RuntimeError("D15 schedule mismatch")
    if args.smoke_steps < 0 or args.smoke_steps > 10:
        raise RuntimeError("smoke steps must be 0..10")
    if int(cfg["micro_batch"]) * int(cfg["accum_steps"]) != int(cfg["effective_batch"]):
        raise RuntimeError("batch mismatch")
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("D15 expects exactly one visible GPU per worker")
    data_root = Path(cfg["data_root"])
    pretrain = Path(cfg["pretrain"])
    if not pretrain.is_file():
        raise FileNotFoundError(pretrain)
    out = run_dir(args.seed, args.smoke_steps > 0)
    if out.exists() and not args.resume:
        raise FileExistsError(out)
    out.mkdir(parents=True, exist_ok=True)
    if args.resume and (out / "summary.json").is_file():
        raise RuntimeError("completed run cannot be resumed")
    signature = dict(experiment="D15_DSM_ONLY", seed=args.seed,
                     config_sha256=sha256(CONFIG), base_config_sha256=sha256(ROOT / protocol["base_config"]),
                     source_sha256=sha256(Path(__file__)),
                     r01_source_sha256=sha256(ROOT / "scripts/train_rebuild_v1_r01_optical_only.py"),
                     r02_source_sha256=sha256(ROOT / "scripts/train_rebuild_v1_r02_budget_pilot.py"),
                     helper_sha256=sha256(ROOT / "scripts/d15_capability.py"),
                     representation=protocol["dsm_representation"],
                     train_ids=train_ids, val_ids=val_ids, target_step=protocol["training_steps"])
    state_path = out / "last_train_state.pth"
    state = torch.load(state_path, map_location="cpu") if args.resume else None
    if state is not None and state.get("signature") != signature:
        raise RuntimeError("resume signature mismatch")
    r02.set_seed(args.seed)
    train_cache, val_cache = preload(data_root, train_ids, val_ids)
    net, _, audit = r01.build_model(cfg, pretrain, resume_state=state)
    optimizer = r02.build_optimizer(net, cfg)
    step = 0
    best = None
    if state is not None:
        optimizer.load_state_dict(state["optimizer"])
        step, best = int(state["global_step"]), state.get("best")
        r02.restore_rng(state)
    target = args.smoke_steps or protocol["training_steps"]
    if step >= target:
        raise RuntimeError("resume state already reached target")
    metadata = dict(experiment="D15_DSM_ONLY", started_at=r01.now_iso(),
                    git_commit=r01.git_head(), signature=signature, config=cfg,
                    structural_audit=audit, physical_gpu=os.environ["CUDA_VISIBLE_DEVICES"],
                    test6_loaded=False)
    (out / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    torch.cuda.reset_peak_memory_stats()
    losses = []
    while step < target:
        t0 = time.time()
        next_step = step + 1
        lrs = r02.set_lr(optimizer, cfg, next_step, protocol["training_steps"])
        optimizer.zero_grad(set_to_none=True)
        micro = []
        for _ in range(int(cfg["accum_steps"])):
            x, gt, _ = r01.sample_batch(train_cache, train_ids, cfg)
            logits = net(x)
            loss = F.cross_entropy(logits.permute(0, 2, 3, 1).reshape(-1, 6), gt.reshape(-1))
            if not torch.isfinite(loss):
                raise RuntimeError(f"nonfinite loss at {next_step}")
            (loss / int(cfg["accum_steps"])).backward()
            micro.append(float(loss.detach()))
            del x, gt, logits, loss
        optimizer.step()
        step = next_step
        value = float(np.mean(micro))
        losses.append(value)
        r01.append_csv(out / "train_history.csv", ["step", "loss", "mean50", "lr_backbone", "seconds"],
                       [step, value, float(np.mean(losses[-50:])), lrs["backbone"], time.time() - t0])
        if step == 1 or step % 20 == 0:
            print(f"D15 DSM seed{args.seed} step={step}/{target} loss={value:.6f}", flush=True)
        if not args.smoke_steps and (step % int(cfg["validation"]["eval_interval_steps"]) == 0 or step == target):
            result = r01.evaluate_val(net, val_cache, val_ids, cfg)
            score = float(result["noboundary"]["mIoU_fg5"])
            r01.append_csv(out / "val_history.csv", ["step", "full_mIoU_fg5", "nb_mIoU_fg5"],
                           [step, result["full"]["mIoU_fg5"], score])
            if best is None or score > best["value"]:
                best = dict(metric="val2_noboundary_mIoU_fg5", value=score, step=step)
                torch.save(dict(model=net.state_dict(), global_step=step, best=best,
                                metrics=result, signature=signature), out / "best_model.pth")
        if step % 250 == 0 or step == target:
            save_atomic(state_path, net, optimizer, step, best, signature)
    summary = dict(experiment="D15_DSM_ONLY", seed=args.seed, global_step=step,
                   best=best, completed_at=r01.now_iso(), git_commit=r01.git_head(),
                   config_sha256=signature["config_sha256"], source_sha256=signature["source_sha256"],
                   physical_gpu=os.environ["CUDA_VISIBLE_DEVICES"],
                   peak_allocated_gib=torch.cuda.max_memory_allocated() / 1024**3,
                   test6_loaded=False, smoke=bool(args.smoke_steps))
    (out / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print("D15 DSM TRAIN COMPLETE", out, flush=True)


if __name__ == "__main__":
    main()
