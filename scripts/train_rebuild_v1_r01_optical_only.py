import os
import sys
import csv
import json
import time
import copy
import random
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import numpy as np
import torch
import torch.nn.functional as F
from skimage import io

import train_rebuild_v1_r02_budget_pilot as r02
from model.rebuild_v1_optical_only import (
    VisionTransformerOpticalOnly,
    CONFIGS,
    structural_audit,
)

DEVICE = torch.device("cuda:0")
IGNORE_INDEX = 255
N_CLASSES = 6
CLASS_NAMES = r02.CLASS_NAMES
PALETTE = r02.PALETTE
BLACK = r02.BLACK


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def git_head():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return None


def make_data_paths(data_root, tile_id):
    return {
        "rgb": data_root / "2_Ortho_RGB" / f"top_potsdam_{tile_id}_RGB.tif",
        "full": data_root / "5_Labels_for_participants" / f"top_potsdam_{tile_id}_label.tif",
        "nb": data_root / "5_Labels_for_participants_no_Boundary" / f"top_potsdam_{tile_id}_label_noBoundary.tif",
    }


def load_tile(data_root, tile_id, need_nb):
    paths = make_data_paths(data_root, tile_id)
    required = [paths["rgb"], paths["full"]]
    if need_nb:
        required.append(paths["nb"])
    for p in required:
        if not p.is_file():
            raise FileNotFoundError(p)

    optical = io.imread(str(paths["rgb"]))[..., :3].astype(np.float32) / 255.0
    full = r02.convert_full_gt(io.imread(str(paths["full"])))
    nb = r02.convert_noboundary_gt(io.imread(str(paths["nb"]))) if need_nb else None
    shapes = [optical.shape[:2], full.shape]
    if need_nb:
        shapes.append(nb.shape)
    if len(set(shapes)) != 1:
        raise RuntimeError(f"R01 shape mismatch {tile_id}: {shapes}")
    return {"optical": optical, "full_gt": full, "noboundary_gt": nb}


def preload(data_root, train_ids, val_ids):
    print("=" * 100)
    print("PRELOAD REBUILD_V1 R01 OPTICAL TRAIN16 + VAL2 (DSM AND TEST6 ARE NOT LOADED)")
    print("=" * 100)
    train_cache, val_cache = {}, {}
    for tile_id in train_ids:
        d = load_tile(data_root, tile_id, need_nb=False)
        train_cache[tile_id] = (d["optical"], d["full_gt"])
        print(f"train {tile_id}: {d['full_gt'].shape}")
    for tile_id in val_ids:
        d = load_tile(data_root, tile_id, need_nb=True)
        val_cache[tile_id] = d
        ignored = int((d["noboundary_gt"] == IGNORE_INDEX).sum())
        print(f"val   {tile_id}: {d['full_gt'].shape}, nb_ignored={ignored}")
    return train_cache, val_cache


def sample_batch(train_cache, train_ids, cfg):
    patch = int(cfg["patch"])
    batch = int(cfg["micro_batch"])
    aug = cfg["augmentation"]
    scale_min = float(aug["random_scale_min"])
    scale_max = float(aug["random_scale_max"])
    hp = float(aug["horizontal_flip_p"])
    vp = float(aug["vertical_flip_p"])

    ops, gts, scales = [], [], []
    for _ in range(batch):
        tile_id = random.choice(train_ids)
        optical, gt = train_cache[tile_id]
        h, w = gt.shape
        scale = random.uniform(scale_min, scale_max)
        source = max(1, min(int(round(patch / scale)), h, w))
        y = random.randint(0, h - source)
        x = random.randint(0, w - source)
        op = optical[y:y+source, x:x+source, :]
        label = gt[y:y+source, x:x+source]

        if random.random() < vp:
            op, label = op[::-1, :, :], label[::-1, :]
        if random.random() < hp:
            op, label = op[:, ::-1, :], label[:, ::-1]

        op_t = torch.from_numpy(np.ascontiguousarray(op.transpose(2, 0, 1))).float().unsqueeze(0)
        gt_t = torch.from_numpy(np.ascontiguousarray(label.astype(np.int64))).unsqueeze(0).unsqueeze(0).float()
        if source != patch:
            op_t = F.interpolate(op_t, size=(patch, patch), mode="bilinear", align_corners=False)
            gt_t = F.interpolate(gt_t, size=(patch, patch), mode="nearest")
        ops.append(op_t.squeeze(0))
        gts.append(gt_t.squeeze(0).squeeze(0).long())
        scales.append(scale)

    return (
        torch.stack(ops).to(DEVICE, non_blocking=True),
        torch.stack(gts).to(DEVICE, non_blocking=True),
        scales,
    )


def infer_tile(net, optical, patch, stride, infer_batch):
    h, w = optical.shape[:2]
    coords = [
        (y, x)
        for y in r02.positions(h, patch, stride)
        for x in r02.positions(w, patch, stride)
    ]
    score = np.zeros((N_CLASSES, h, w), dtype=np.float32)
    with torch.inference_mode():
        for start in range(0, len(coords), infer_batch):
            batch_coords = coords[start:start + infer_batch]
            op = np.stack([
                optical[y:y+patch, x:x+patch, :].transpose(2, 0, 1)
                for y, x in batch_coords
            ])
            op_t = torch.from_numpy(np.ascontiguousarray(op)).to(DEVICE)
            logits = net(op_t).detach().cpu().numpy()
            for output, (y, x) in zip(logits, batch_coords):
                score[:, y:y+patch, x:x+patch] += output
    return np.argmax(score, axis=0).astype(np.uint8)


def evaluate_val(net, val_cache, val_ids, cfg):
    patch = int(cfg["patch"])
    stride = int(cfg["validation"]["stride"])
    infer_batch = int(cfg["validation"]["inference_batch"])
    cm_full = np.zeros((N_CLASSES, N_CLASSES), dtype=np.int64)
    cm_nb = np.zeros((N_CLASSES, N_CLASSES), dtype=np.int64)
    t0 = time.time()
    net.eval()
    for tile_id in val_ids:
        d = val_cache[tile_id]
        print(f"  VAL {tile_id}", flush=True)
        pred = infer_tile(net, d["optical"], patch, stride, infer_batch)
        r02.update_cm(cm_full, d["full_gt"], pred)
        r02.update_cm(cm_nb, d["noboundary_gt"], pred)
    out = {
        "full": r02.metrics_from_cm(cm_full),
        "noboundary": r02.metrics_from_cm(cm_nb),
        "cm_full": cm_full.tolist(),
        "cm_noboundary": cm_nb.tolist(),
        "seconds": float(time.time() - t0),
    }
    net.train()
    return out


def build_model(cfg, pretrain, resume_state=None):
    patch = int(cfg["patch"])
    config = copy.deepcopy(CONFIGS["R50-ViT-B_16"])
    config.n_classes = N_CLASSES
    config.n_skip = 3
    config.patches.grid = (patch // 16, patch // 16)
    net = VisionTransformerOpticalOnly(
        config,
        img_size=patch,
        num_classes=N_CLASSES,
    ).to(DEVICE)
    if resume_state is None:
        net.load_from(np.load(str(pretrain)))
        print("[PASS] R01 pretrained weights loaded")
    else:
        net.load_state_dict(resume_state["model"], strict=True)
        print("[PASS] R01 model state restored")

    audit = structural_audit(net)
    if not audit["pass"]:
        raise RuntimeError(f"R01 structural audit failed: {audit}")
    print("[PASS] R01 TRUE OPTICAL-ONLY structural audit", json.dumps(audit))
    return net, config, audit


def append_csv(path, header, row):
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerow(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/rebuild_v1/r01_optical_only_16k.json")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--smoke-steps", type=int, default=0)
    ap.add_argument("--smoke-eval", action="store_true")
    ap.add_argument("--run-tag", default="")
    ap.add_argument("--seed-override", type=int, default=None)
    args = ap.parse_args()

    cfg_path = r02.resolve_root_relative(args.config)
    cfg = r02.read_json(cfg_path)
    if args.seed_override is not None:
        cfg["seed"] = int(args.seed_override)
    if cfg.get("model_id") != "R01" or cfg.get("model") != "optical_only_f0":
        raise RuntimeError("R01 trainer requires model_id=R01 and model=optical_only_f0")

    split_path = r02.resolve_root_relative(cfg["split_file"])
    split = r02.read_json(split_path)
    train_ids = list(split["train16"])
    val_ids = list(split["val2"])
    exposed = set(split["historical_exposed_test6"])
    if set(train_ids) & set(val_ids):
        raise RuntimeError("train/val overlap")
    if (set(train_ids) | set(val_ids)) & exposed:
        raise RuntimeError("R01 train/val overlaps historical TEST6")
    if len(train_ids) != 16 or len(val_ids) != 2:
        raise RuntimeError("expected Train16 / Val2")

    scheduler_total_steps = int(cfg["schedule"]["scheduler_total_steps"])
    stop_at_step = int(cfg["schedule"]["stop_at_step"])
    if not (0 < stop_at_step <= scheduler_total_steps):
        raise RuntimeError("invalid complete schedule")
    if args.smoke_steps < 0:
        raise RuntimeError("smoke steps must be >=0")
    target_step = args.smoke_steps if args.smoke_steps > 0 else stop_at_step

    seed = int(cfg["seed"])
    r02.set_seed(seed)
    data_root = Path(cfg["data_root"])
    pretrain = Path(cfg["pretrain"])
    if not pretrain.is_file():
        raise FileNotFoundError(pretrain)

    run_kind = f"smoke{args.smoke_steps}" if args.smoke_steps else f"sched{scheduler_total_steps}_stop{stop_at_step}"
    suffix = f"_{args.run_tag}" if args.run_tag else ""
    run_dir = ROOT / "runs" / "rebuild_v1" / f"R01_optical_only_seed{seed}_{run_kind}{suffix}"
    if run_dir.exists() and not args.resume:
        raise FileExistsError(f"refusing to overwrite: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)

    started_at = now_iso()
    existing_meta = None
    meta_path = run_dir / "run_metadata.json"
    if args.resume and meta_path.is_file():
        existing_meta = r02.read_json(meta_path)
        started_at = existing_meta.get("started_at", started_at)

    signature = {
        "config_file": str(cfg_path),
        "split_file": str(split_path),
        "seed": seed,
        "train_ids": train_ids,
        "val_ids": val_ids,
        "scheduler_total_steps": scheduler_total_steps,
        "stop_at_step": stop_at_step,
        "model": "R01_true_optical_only_F0",
        "dsm_loaded": False,
        "test6_loaded": False,
    }

    train_cache, val_cache = preload(data_root, train_ids, val_ids)
    resume_path = run_dir / "last_train_state.pth"
    state = None
    if args.resume:
        if not resume_path.is_file():
            raise FileNotFoundError(resume_path)
        state = torch.load(resume_path, map_location="cpu")
        if state.get("signature") != signature:
            raise RuntimeError("resume signature mismatch")

    net, _, audit = build_model(cfg, pretrain, resume_state=state)
    optimizer = r02.build_optimizer(net, cfg)
    global_step = 0
    best = None
    if state is not None:
        optimizer.load_state_dict(state["optimizer"])
        global_step = int(state["global_step"])
        best = state.get("best")
        r02.restore_rng(state)
        print(f"[RESUME] global_step={global_step}")

    metadata = {
        "experiment_id": "R01",
        "started_at": started_at,
        "last_launch_at": now_iso(),
        "git_commit": git_head(),
        "config": cfg,
        "split": split,
        "signature": signature,
        "structural_audit": audit,
        "resume": bool(args.resume),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    train_csv = run_dir / "train_history.csv"
    val_csv = run_dir / "val_history.csv"
    eval_interval = int(cfg["validation"]["eval_interval_steps"])
    accum_steps = int(cfg["accum_steps"])
    if int(cfg["effective_batch"]) != int(cfg["micro_batch"]) * accum_steps:
        raise RuntimeError("effective batch metadata mismatch")

    print("=" * 100)
    print("REBUILD_V1 R01 TRUE OPTICAL-ONLY")
    print("run:", run_dir)
    print("train16:", train_ids)
    print("val2:", val_ids)
    print("DSM loaded: False")
    print("TEST6 loaded: False")
    print("scheduler_total_steps:", scheduler_total_steps)
    print("stop_at_step:", stop_at_step)
    print("actual target:", target_step)
    print("warmup_steps:", cfg["schedule"]["warmup_steps"])
    print("patch/effective batch:", cfg["patch"], cfg["effective_batch"])
    print("val stride:", cfg["validation"]["stride"])
    print("started_at:", started_at)
    print("git_commit:", metadata["git_commit"])
    print("=" * 100)

    loss_buffer = []
    torch.cuda.reset_peak_memory_stats()
    while global_step < target_step:
        next_step = global_step + 1
        t0 = time.time()
        lrs = r02.set_lr(optimizer, cfg, next_step, scheduler_total_steps)
        optimizer.zero_grad(set_to_none=True)
        micro_losses, all_scales = [], []

        for _ in range(accum_steps):
            optical, gt, scales = sample_batch(train_cache, train_ids, cfg)
            logits = net(optical)
            flat_logits = logits.permute(0, 2, 3, 1).contiguous().view(-1, logits.shape[1])
            flat_gt = gt.contiguous().view(-1)
            loss = F.cross_entropy(flat_logits, flat_gt)
            if not torch.isfinite(loss):
                raise RuntimeError(f"non-finite R01 loss before step {next_step}")
            (loss / accum_steps).backward()
            micro_losses.append(float(loss.detach()))
            all_scales.extend(scales)
            del optical, gt, logits, loss

        optimizer.step()
        global_step = next_step
        torch.cuda.synchronize()
        loss_value = float(np.mean(micro_losses))
        loss_buffer.append(loss_value)
        mean50 = float(np.mean(loss_buffer[-50:]))
        sec = time.time() - t0
        append_csv(
            train_csv,
            ["step", "lr_backbone", "lr_decoder_head", "loss", "mean50", "scale_mean", "sec_per_step"],
            [global_step, lrs["backbone"], lrs["decoder_head"], loss_value, mean50, float(np.mean(all_scales)), sec],
        )

        if global_step == 1 or global_step % 20 == 0:
            print(
                f"step {global_step:06d}/{target_step} | loss={loss_value:.6f} | mean50={mean50:.6f} | "
                f"lr={lrs['backbone']:.3e} | GPU={torch.cuda.memory_allocated()/1024**3:.2f}G | {sec:.3f}s"
            )

        do_eval = (
            (args.smoke_steps == 0 and (global_step % eval_interval == 0 or global_step == target_step))
            or (args.smoke_steps > 0 and args.smoke_eval and global_step == target_step)
        )
        if do_eval:
            print(f"\n--- R01 VAL2 @ step {global_step} ---")
            result = evaluate_val(net, val_cache, val_ids, cfg)
            full, nb = result["full"], result["noboundary"]
            print(f"FULL OA={100*full['OA']:.4f} mIoU_fg5={100*full['mIoU_fg5']:.4f}")
            print(f"NB   OA={100*nb['OA']:.4f} mIoU_fg5={100*nb['mIoU_fg5']:.4f} ({result['seconds']:.1f}s)")
            append_csv(
                val_csv,
                ["step", "full_OA", "full_mIoU_fg5", "nb_OA", "nb_mIoU_fg5", "eval_seconds"],
                [global_step, full["OA"], full["mIoU_fg5"], nb["OA"], nb["mIoU_fg5"], result["seconds"]],
            )
            score = float(nb["mIoU_fg5"])
            if best is None or score > float(best["value"]):
                best = {"metric": "val2_noboundary_mIoU_fg5", "value": score, "step": global_step}
                torch.save({
                    "model": net.state_dict(),
                    "global_step": global_step,
                    "best": best,
                    "metrics": result,
                    "signature": signature,
                    "structural_audit": audit,
                }, run_dir / "best_model.pth")
                print(f"[BEST] {100*score:.4f}% @ {global_step}")

        if global_step % 250 == 0 or global_step == target_step:
            r02.save_state(resume_path, net, optimizer, global_step, best, signature)

    completed_at = now_iso()
    summary = {
        "experiment_id": "R01",
        "started_at": started_at,
        "completed_at": completed_at,
        "git_commit": git_head(),
        "global_step": global_step,
        "scheduler_total_steps": scheduler_total_steps,
        "stop_at_step": stop_at_step,
        "best": best,
        "peak_allocated_gib": float(torch.cuda.max_memory_allocated()/1024**3),
        "run_dir": str(run_dir),
        "dsm_loaded": False,
        "test6_loaded": False,
        "structural_audit": audit,
    }
    with open(run_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print("=" * 100)
    print("COMPLETE", json.dumps(summary, ensure_ascii=False))
    print("=" * 100)


if __name__ == "__main__":
    main()
