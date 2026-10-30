"""Fit-only P2 timing probe; no development labels or persistent model weights."""

import json
import os
from pathlib import Path
import random
import resource
import statistics
import time

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
os.environ.setdefault("XFORMERS_DISABLED", "1")
import torch

import d18_d19_night as d18
import d16_d17_portfolio as old
import train_rebuild_v1_r02_budget_pilot as r02
from train_rebuild_v1_d16_d17 import sample
from d20_vaihingen_smoke_arm import load_tile

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rebuild_v1/d20_vaihingen_fit_budget_probe_20260928.json"
OUT = ROOT / "records/rebuild_v1_d20_vaihingen_fit_budget_probe_20260928/summary.json"


def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert cfg["arm"] == "P2" and cfg["seed"] == 42
    assert cfg["probe_steps"] == 20 and cfg["micro_batch"] * cfg["accum_steps"] == 16
    assert cfg["test6_loaded"] is False and cfg["development_labels_loaded"] is False
    assert cfg["formal_training_authorized_by_this_config"] is False
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("exactly one visible CUDA GPU required")
    data_root = Path(cfg["data_root"]).resolve()
    data_root.relative_to(Path("/home/jovyan/zzx").resolve())
    signature = {
        "config_sha256": d18.sha(CONFIG),
        "source_sha256": d18.sha(Path(__file__)),
        "loader_sha256": d18.sha(ROOT / "scripts/d20_vaihingen_smoke_arm.py"),
        "d18_binding": d18.binding("P2", True),
        "train_ids": cfg["train_ids"],
        "development_labels_loaded": False,
        "test6_loaded": False,
    }
    if OUT.is_file():
        previous = json.loads(OUT.read_text(encoding="utf-8"))
        if previous["signature"] != signature:
            raise RuntimeError("existing timing record has a different source/config binding")
        print("FIT BUDGET PROBE REUSED", flush=True)
        return
    r02.set_seed(cfg["seed"])
    loading_started = time.monotonic()
    cache = {str(tile): load_tile(data_root, tile, cfg["training_label_directory"])
             for tile in cfg["train_ids"]}
    loading_seconds = time.monotonic() - loading_started
    base = d18.read(d18.base_config())
    parent = d18.read(d18.CONFIG)
    train_cfg = dict(base, patch=cfg["patch"], micro_batch=cfg["micro_batch"])
    optcfg = dict(base, optimizer=parent["pretrained_optimizer"], schedule=parent["schedule"])
    net = d18.build("P2", base, r02.DEVICE)
    optimizer = r02.build_optimizer(net, optcfg)
    r02.set_seed(cfg["seed"])
    net.train()
    torch.cuda.reset_peak_memory_stats()
    step_seconds, losses = [], []
    names = list(parent["treatment_probabilities"])
    weights = list(parent["treatment_probabilities"].values())
    for step in range(1, cfg["probe_steps"] + 1):
        torch.cuda.synchronize()
        started = time.monotonic()
        optimizer.zero_grad(set_to_none=True)
        r02.set_lr(optimizer, optcfg, step, cfg["candidate_formal_steps_for_projection_only"])
        total_loss = 0.0
        for micro in range(cfg["accum_steps"]):
            key = 42000000 + step * 100 + micro
            op, ds, gt, _ = sample(cache, list(cache), train_cfg, key)
            kinds = random.Random(key + 1).choices(names, weights=weights, k=len(op))
            op2, aux2, _ = d18.training_transform(
                op, ds, "P2", kinds, key, parent["structured_mask"])
            clean = net(op, ds)
            loss = .5 * old.deterministic_ce(clean, gt)
            if not bool(torch.isfinite(loss)):
                raise RuntimeError(f"nonfinite clean loss at step {step}")
            total_loss += float(loss.detach()) / cfg["accum_steps"]
            (loss / cfg["accum_steps"]).backward()
            del loss, clean
            damaged = net(op2, aux2)
            loss = .5 * old.deterministic_ce(damaged, gt)
            if not bool(torch.isfinite(loss)):
                raise RuntimeError(f"nonfinite damaged loss at step {step}")
            total_loss += float(loss.detach()) / cfg["accum_steps"]
            (loss / cfg["accum_steps"]).backward()
            del loss, damaged, op, ds, gt, op2, aux2
        torch.nn.utils.clip_grad_norm_(net.parameters(), float("inf"), error_if_nonfinite=True)
        optimizer.step()
        torch.cuda.synchronize()
        elapsed = time.monotonic() - started
        step_seconds.append(elapsed)
        losses.append(total_loss)
        print(f"FIT PROBE P2 step={step}/{cfg['probe_steps']} seconds={elapsed:.2f} loss={total_loss:.5f}", flush=True)
    warmup = cfg["warmup_steps_excluded_from_timing"]
    steady = step_seconds[warmup:]
    median = statistics.median(steady)
    result = {
        "status": "COMPLETE", "signature": signature,
        "train_tiles_loaded": len(cache), "fit_only": True,
        "optical_channels": cfg["optical_channels"],
        "data_load_seconds": round(loading_seconds, 2),
        "step_seconds": [round(x, 3) for x in step_seconds],
        "losses_diagnostic_only": [round(x, 5) for x in losses],
        "steady_step_median_seconds": round(median, 3),
        "steady_step_max_seconds": round(max(steady), 3),
        "projected_8000_step_train_hours_P2_only": round(median * 8000 / 3600, 2),
        "cuda_peak_allocated_gib": round(torch.cuda.max_memory_allocated() / 2**30, 3),
        "host_peak_rss_gib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20, 3),
        "candidate_budget_not_frozen": True,
        "development_labels_loaded": False, "test6_loaded": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("FIT BUDGET PROBE COMPLETE", result["steady_step_median_seconds"], flush=True)


if __name__ == "__main__":
    main()
