import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import numpy as np
import torch

import train_rebuild_v1_r02_budget_pilot as r02
import train_rebuild_v1_r01_optical_only as r01

DEVICE = torch.device("cuda:0")


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def stats(values):
    a = np.asarray(values, dtype=np.float64)
    return {
        "median_ms": float(np.median(a)),
        "mean_ms": float(np.mean(a)),
        "min_ms": float(np.min(a)),
        "max_ms": float(np.max(a)),
        "std_ms": float(np.std(a)),
        "n": int(a.size),
    }


def time_cuda(fn, warmup=5, repeats=20):
    with torch.inference_mode():
        for _ in range(warmup):
            fn()
        torch.cuda.synchronize()
        vals = []
        for _ in range(repeats):
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            fn()
            torch.cuda.synchronize()
            vals.append((time.perf_counter() - t0) * 1000.0)
    return stats(vals)


def count_params(module):
    return int(sum(p.numel() for p in module.parameters()))


def load_r02(config_path, run_dir):
    cfg = r02.read_json(config_path)
    summary = r02.read_json(run_dir / "summary.json")
    if int(summary.get("global_step", -1)) != 16000:
        raise RuntimeError(f"R02 run incomplete: {summary}")
    state = torch.load(run_dir / "best_model.pth", map_location="cpu")
    net, _ = r02.build_model(cfg, Path(cfg["pretrain"]), resume_state=state)
    return cfg, state, net


def load_r01(config_path, run_dir):
    cfg = r02.read_json(config_path)
    summary = r02.read_json(run_dir / "summary.json")
    if int(summary.get("global_step", -1)) != 16000 or summary.get("dsm_loaded") is not False:
        raise RuntimeError(f"R01 run incomplete/invalid: {summary}")
    state = torch.load(run_dir / "best_model.pth", map_location="cpu")
    net, _, audit = r01.build_model(cfg, Path(cfg["pretrain"]), resume_state=state)
    if not audit["pass"]:
        raise RuntimeError(audit)
    return cfg, state, net


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=["R02", "R01"], required=True)
    ap.add_argument("--repeats", type=int, default=20)
    ap.add_argument("--warmup", type=int, default=5)
    ap.add_argument("--tile", default="3_11")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    if args.model == "R02":
        config_path = ROOT / "configs/rebuild_v1/r02_budget_pilot_16k.json"
        run_dir = ROOT / "runs/rebuild_v1/R02_dual_f0_seed42_sched16000_stop16000"
        cfg, state, net = load_r02(config_path, run_dir)
        split = r02.read_json(r02.resolve_root_relative(cfg["split_file"]))
        if args.tile not in split["val2"]:
            raise RuntimeError("profile tile must be in Val2")
        d = r02.load_tile(Path(cfg["data_root"]), args.tile, need_nb=True)
        patch = int(cfg["patch"])
        op_np = d["optical"][:patch, :patch].transpose(2, 0, 1)[None]
        ds_np = d["dsm"][:patch, :patch][None]
        op = torch.from_numpy(np.ascontiguousarray(op_np)).to(DEVICE)
        ds = torch.from_numpy(np.ascontiguousarray(ds_np)).to(DEVICE)
        net.eval()

        def transformer_call():
            return net.transformer(op, ds)

        with torch.inference_mode():
            tx, ty, _, features = transformer_call()
            fused = tx + ty

        transform_t = time_cuda(transformer_call, args.warmup, args.repeats)
        decoder_t = time_cuda(lambda: net.decoder(fused, features), args.warmup, args.repeats)
        with torch.inference_mode():
            dec = net.decoder(fused, features)
        head_t = time_cuda(lambda: net.segmentation_head(dec), args.warmup, args.repeats)
        full_t = time_cuda(lambda: net(op, ds), args.warmup, args.repeats)

        torch.cuda.reset_peak_memory_stats()
        with torch.inference_mode():
            _ = net(op, ds)
        torch.cuda.synchronize()
        peak_crop = float(torch.cuda.max_memory_allocated() / 1024**3)

        t0 = time.perf_counter()
        _ = r02.infer_tile(
            net,
            d["optical"],
            d["dsm"],
            patch,
            int(cfg["validation"]["stride"]),
            int(cfg["validation"]["inference_batch"]),
        )
        torch.cuda.synchronize()
        tile_seconds = float(time.perf_counter() - t0)

    else:
        config_path = ROOT / "configs/rebuild_v1/r01_optical_only_16k.json"
        run_dir = ROOT / "runs/rebuild_v1/R01_optical_only_seed42_sched16000_stop16000"
        cfg, state, net = load_r01(config_path, run_dir)
        split = r02.read_json(r02.resolve_root_relative(cfg["split_file"]))
        if args.tile not in split["val2"]:
            raise RuntimeError("profile tile must be in Val2")
        d = r01.load_tile(Path(cfg["data_root"]), args.tile, need_nb=True)
        patch = int(cfg["patch"])
        op_np = d["optical"][:patch, :patch].transpose(2, 0, 1)[None]
        op = torch.from_numpy(np.ascontiguousarray(op_np)).to(DEVICE)
        net.eval()

        def transformer_call():
            return net.transformer(op)

        with torch.inference_mode():
            tx, _, features = transformer_call()

        transform_t = time_cuda(transformer_call, args.warmup, args.repeats)
        decoder_t = time_cuda(lambda: net.decoder(tx, features), args.warmup, args.repeats)
        with torch.inference_mode():
            dec = net.decoder(tx, features)
        head_t = time_cuda(lambda: net.segmentation_head(dec), args.warmup, args.repeats)
        full_t = time_cuda(lambda: net(op), args.warmup, args.repeats)

        torch.cuda.reset_peak_memory_stats()
        with torch.inference_mode():
            _ = net(op)
        torch.cuda.synchronize()
        peak_crop = float(torch.cuda.max_memory_allocated() / 1024**3)

        t0 = time.perf_counter()
        _ = r01.infer_tile(
            net,
            d["optical"],
            patch,
            int(cfg["validation"]["stride"]),
            int(cfg["validation"]["inference_batch"]),
        )
        torch.cuda.synchronize()
        tile_seconds = float(time.perf_counter() - t0)

    result = {
        "experiment": f"REBUILD_V1_{args.model}_COMPUTE_PROFILE",
        "recorded_at": now_iso(),
        "model": args.model,
        "checkpoint_step": int(state.get("global_step", -1)),
        "config": str(config_path),
        "run_dir": str(run_dir),
        "device": torch.cuda.get_device_name(0),
        "precision": "FP32",
        "patch": int(cfg["patch"]),
        "stride": int(cfg["validation"]["stride"]),
        "inference_batch": int(cfg["validation"]["inference_batch"]),
        "profile_tile": args.tile,
        "params": {
            "total": count_params(net),
            "transformer": count_params(net.transformer),
            "decoder": count_params(net.decoder),
            "segmentation_head": count_params(net.segmentation_head),
        },
        "crop_batch1_latency": {
            "transformer": transform_t,
            "decoder": decoder_t,
            "head": head_t,
            "full_forward": full_t,
        },
        "crop_batch1_peak_allocated_gib": peak_crop,
        "end_to_end_tile_seconds": tile_seconds,
        "notes": [
            "CUDA synchronization used around timed sections.",
            "Tile timing includes sliding-window extraction, host/device movement, score accumulation, and model inference.",
            "Compare R01 and R02 only when patch/stride/inference_batch/precision/profile tile match exactly.",
        ],
    }

    out = args.out
    if out is None:
        out = ROOT / "records/rebuild_v1_compute_profile_20260916" / f"{args.model.lower()}_profile.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("PROFILE COMPLETE:", out)


if __name__ == "__main__":
    main()
