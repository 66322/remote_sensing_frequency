import os
import sys
import csv
import json
import time
import copy
import random
import argparse
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
sys.path.insert(0, str(ROOT))

import numpy as np
import torch
import torch.nn.functional as F
from skimage import io

from model.vitcross_seg_modeling_freq_ablation import (
    VisionTransformerFreqAblation,
    CONFIGS,
)

N_CLASSES = 6
IGNORE_INDEX = 255
CLASS_NAMES = [
    "Impervious", "Building", "LowVegetation",
    "Tree", "Car", "Clutter",
]
PALETTE = {
    (255, 255, 255): 0,
    (0, 0, 255): 1,
    (0, 255, 255): 2,
    (0, 255, 0): 3,
    (255, 255, 0): 4,
    (255, 0, 0): 5,
}
BLACK = (0, 0, 0)
DEVICE = torch.device("cuda:0")


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_root_relative(value):
    p = Path(value)
    return p if p.is_absolute() else ROOT / p


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)


def convert_full_gt(rgb):
    out = np.full(rgb.shape[:2], IGNORE_INDEX, dtype=np.uint8)
    matched = np.zeros(rgb.shape[:2], dtype=bool)
    for color, idx in PALETTE.items():
        mask = np.all(rgb[..., :3] == np.asarray(color, dtype=rgb.dtype), axis=-1)
        out[mask] = idx
        matched |= mask
    if not matched.all():
        raise RuntimeError(f"FullGT unknown pixels: {int((~matched).sum())}")
    return out


def convert_noboundary_gt(rgb):
    out = np.full(rgb.shape[:2], IGNORE_INDEX, dtype=np.uint8)
    recognized = np.zeros(rgb.shape[:2], dtype=bool)
    for color, idx in PALETTE.items():
        mask = np.all(rgb[..., :3] == np.asarray(color, dtype=rgb.dtype), axis=-1)
        out[mask] = idx
        recognized |= mask
    black = np.all(rgb[..., :3] == np.asarray(BLACK, dtype=rgb.dtype), axis=-1)
    recognized |= black
    if not recognized.all():
        raise RuntimeError(f"NoBoundary unknown pixels: {int((~recognized).sum())}")
    return out


def dsm_name(tile_id):
    a, b = tile_id.split("_")
    return f"dsm_potsdam_{int(a):02d}_{int(b):02d}.tif"


def make_data_paths(data_root, tile_id):
    return {
        "rgb": data_root / "2_Ortho_RGB" / f"top_potsdam_{tile_id}_RGB.tif",
        "dsm": data_root / "1_DSM" / "1_DSM" / dsm_name(tile_id),
        "full": data_root / "5_Labels_for_participants" / f"top_potsdam_{tile_id}_label.tif",
        "nb": data_root / "5_Labels_for_participants_no_Boundary" / f"top_potsdam_{tile_id}_label_noBoundary.tif",
    }


def load_tile(data_root, tile_id, need_nb):
    paths = make_data_paths(data_root, tile_id)
    required = [paths["rgb"], paths["dsm"], paths["full"]]
    if need_nb:
        required.append(paths["nb"])
    for p in required:
        if not p.is_file():
            raise FileNotFoundError(p)

    optical = io.imread(str(paths["rgb"]))[..., :3].astype(np.float32) / 255.0
    dsm = io.imread(str(paths["dsm"])).astype(np.float32)
    dmin, dmax = float(dsm.min()), float(dsm.max())
    if dmax <= dmin:
        raise RuntimeError(f"DSM zero range: {tile_id}")
    dsm = ((dsm - dmin) / (dmax - dmin)).astype(np.float32)
    full = convert_full_gt(io.imread(str(paths["full"])))
    nb = convert_noboundary_gt(io.imread(str(paths["nb"]))) if need_nb else None

    shapes = [optical.shape[:2], dsm.shape, full.shape]
    if need_nb:
        shapes.append(nb.shape)
    if len(set(shapes)) != 1:
        raise RuntimeError(f"Shape mismatch {tile_id}: {shapes}")
    return {"optical": optical, "dsm": dsm, "full_gt": full, "noboundary_gt": nb}


def preload(data_root, train_ids, val_ids):
    print("=" * 100)
    print("PRELOAD REBUILD_V1 TRAIN16 + VAL2 (TEST6 IS NOT LOADED)")
    print("=" * 100)
    train_cache = {}
    val_cache = {}
    for tile_id in train_ids:
        d = load_tile(data_root, tile_id, need_nb=False)
        train_cache[tile_id] = (d["optical"], d["dsm"], d["full_gt"])
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

    ops, dss, gts, scales = [], [], [], []
    for _ in range(batch):
        tile_id = random.choice(train_ids)
        optical, dsm, gt = train_cache[tile_id]
        h, w = gt.shape
        scale = random.uniform(scale_min, scale_max)
        source = max(1, min(int(round(patch / scale)), h, w))
        y = random.randint(0, h - source)
        x = random.randint(0, w - source)
        op = optical[y:y+source, x:x+source, :]
        ds = dsm[y:y+source, x:x+source]
        label = gt[y:y+source, x:x+source]

        if random.random() < vp:
            op, ds, label = op[::-1, :, :], ds[::-1, :], label[::-1, :]
        if random.random() < hp:
            op, ds, label = op[:, ::-1, :], ds[:, ::-1], label[:, ::-1]

        op_t = torch.from_numpy(np.ascontiguousarray(op.transpose(2, 0, 1))).float().unsqueeze(0)
        ds_t = torch.from_numpy(np.ascontiguousarray(ds)).float().unsqueeze(0).unsqueeze(0)
        gt_t = torch.from_numpy(np.ascontiguousarray(label.astype(np.int64))).unsqueeze(0).unsqueeze(0).float()
        if source != patch:
            op_t = F.interpolate(op_t, size=(patch, patch), mode="bilinear", align_corners=False)
            ds_t = F.interpolate(ds_t, size=(patch, patch), mode="bilinear", align_corners=False)
            gt_t = F.interpolate(gt_t, size=(patch, patch), mode="nearest")
        ops.append(op_t.squeeze(0))
        dss.append(ds_t.squeeze(0).squeeze(0))
        gts.append(gt_t.squeeze(0).squeeze(0).long())
        scales.append(scale)

    return (
        torch.stack(ops).to(DEVICE, non_blocking=True),
        torch.stack(dss).to(DEVICE, non_blocking=True),
        torch.stack(gts).to(DEVICE, non_blocking=True),
        scales,
    )


def positions(length, patch, stride):
    out = list(range(0, length - patch + 1, stride))
    last = length - patch
    if out[-1] != last:
        out.append(last)
    return out


def infer_tile(net, optical, dsm, patch, stride, infer_batch):
    h, w = dsm.shape
    coords = [(y, x) for y in positions(h, patch, stride) for x in positions(w, patch, stride)]
    score = np.zeros((N_CLASSES, h, w), dtype=np.float32)
    with torch.inference_mode():
        for start in range(0, len(coords), infer_batch):
            batch_coords = coords[start:start+infer_batch]
            op = np.stack([
                optical[y:y+patch, x:x+patch, :].transpose(2, 0, 1)
                for y, x in batch_coords
            ])
            ds = np.stack([
                dsm[y:y+patch, x:x+patch]
                for y, x in batch_coords
            ])
            op_t = torch.from_numpy(np.ascontiguousarray(op)).to(DEVICE)
            ds_t = torch.from_numpy(np.ascontiguousarray(ds)).to(DEVICE)
            logits = net(op_t, ds_t).detach().cpu().numpy()
            for output, (y, x) in zip(logits, batch_coords):
                score[:, y:y+patch, x:x+patch] += output
    return np.argmax(score, axis=0).astype(np.uint8)


def update_cm(cm, gt, pred):
    valid = (gt != IGNORE_INDEX) & (gt < N_CLASSES)
    g = gt[valid].astype(np.int64)
    p = pred[valid].astype(np.int64)
    cm += np.bincount(N_CLASSES * g + p, minlength=N_CLASSES*N_CLASSES).reshape(N_CLASSES, N_CLASSES)


def metrics_from_cm(cm):
    x = cm.astype(np.float64)
    tp = np.diag(x)
    row, col = x.sum(1), x.sum(0)
    fp, fn = col - tp, row - tp
    union = tp + fp + fn
    f1_denom = 2*tp + fp + fn
    iou = np.divide(tp, union, out=np.full_like(tp, np.nan), where=union > 0)
    f1 = np.divide(2*tp, f1_denom, out=np.full_like(tp, np.nan), where=f1_denom > 0)
    total = x.sum()
    return {
        "OA": float(tp.sum()/total) if total > 0 else float("nan"),
        "mF1_fg5": float(np.nanmean(f1[:5])),
        "mIoU_fg5": float(np.nanmean(iou[:5])),
        "mF1_all6": float(np.nanmean(f1)),
        "mIoU_all6": float(np.nanmean(iou)),
        "per_class_iou": [None if not np.isfinite(v) else float(v) for v in iou],
        "valid_pixels": int(total),
    }


def evaluate_val(net, val_cache, val_ids, cfg):
    patch = int(cfg["patch"])
    vcfg = cfg["validation"]
    stride = int(vcfg["stride"])
    infer_batch = int(vcfg["inference_batch"])
    cm_full = np.zeros((N_CLASSES, N_CLASSES), dtype=np.int64)
    cm_nb = np.zeros((N_CLASSES, N_CLASSES), dtype=np.int64)
    t0 = time.time()
    net.eval()
    for tile_id in val_ids:
        d = val_cache[tile_id]
        print(f"  VAL {tile_id}", flush=True)
        pred = infer_tile(net, d["optical"], d["dsm"], patch, stride, infer_batch)
        update_cm(cm_full, d["full_gt"], pred)
        update_cm(cm_nb, d["noboundary_gt"], pred)
    out = {
        "full": metrics_from_cm(cm_full),
        "noboundary": metrics_from_cm(cm_nb),
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
    net = VisionTransformerFreqAblation(
        config,
        img_size=patch,
        num_classes=N_CLASSES,
        freq_variant="F0",
    ).to(DEVICE)
    if resume_state is None:
        net.load_from(weights=np.load(str(pretrain)))
        print("[PASS] pretrained weights loaded")
    else:
        net.load_state_dict(resume_state["model"], strict=True)
        print("[PASS] model state restored")

    forbidden = [n for n, _ in net.named_modules() if "freq_fusion" in n.lower() or "dysampler" in n.lower()]
    if forbidden:
        raise RuntimeError(f"R02 F0 must contain no frequency modules: {forbidden[:5]}")
    return net, config


def build_optimizer(net, cfg):
    ocfg = cfg["optimizer"]
    base_lr = float(ocfg["backbone_lr"])
    mult = float(ocfg["decoder_head_lr_mult"])
    backbone, head = [], []
    for name, p in net.named_parameters():
        if not p.requires_grad:
            continue
        if name.startswith("decoder.") or name.startswith("segmentation_head."):
            head.append(p)
        else:
            backbone.append(p)
    assigned = sum(p.numel() for p in backbone) + sum(p.numel() for p in head)
    trainable = sum(p.numel() for p in net.parameters() if p.requires_grad)
    if assigned != trainable:
        raise RuntimeError(f"optimizer grouping mismatch {assigned} != {trainable}")
    opt = torch.optim.AdamW(
        [
            {"params": backbone, "lr": base_lr, "lr_mult": 1.0, "group_name": "backbone"},
            {"params": head, "lr": base_lr*mult, "lr_mult": mult, "group_name": "decoder_head"},
        ],
        betas=tuple(float(x) for x in ocfg["betas"]),
        weight_decay=float(ocfg["weight_decay"]),
    )
    return opt


def lr_factor(step, cfg, scheduler_total_steps):
    scfg = cfg["schedule"]
    warmup = int(scfg["warmup_steps"])
    warmup_ratio = float(scfg["warmup_ratio"])
    power = float(scfg["poly_power"])
    if warmup >= scheduler_total_steps:
        raise ValueError("warmup_steps must be < scheduler_total_steps")
    if step <= warmup:
        alpha = step / warmup if warmup > 0 else 1.0
        return warmup_ratio + alpha*(1.0-warmup_ratio)
    progress = (step - warmup) / (scheduler_total_steps - warmup)
    progress = min(max(progress, 0.0), 1.0)
    return (1.0-progress)**power


def set_lr(optimizer, cfg, step, scheduler_total_steps):
    base_lr = float(cfg["optimizer"]["backbone_lr"])
    factor = lr_factor(step, cfg, scheduler_total_steps)
    out = {}
    for group in optimizer.param_groups:
        group["lr"] = base_lr * float(group["lr_mult"]) * factor
        out[group["group_name"]] = group["lr"]
    return out


def save_state(path, net, optimizer, step, best, signature):
    torch.save({
        "model": net.state_dict(),
        "optimizer": optimizer.state_dict(),
        "global_step": int(step),
        "best": best,
        "signature": signature,
        "python_rng": random.getstate(),
        "numpy_rng": np.random.get_state(),
        "torch_rng": torch.get_rng_state(),
        "cuda_rng": torch.cuda.get_rng_state_all(),
    }, path)


def restore_rng(state):
    random.setstate(state["python_rng"])
    np.random.set_state(state["numpy_rng"])
    torch.set_rng_state(state["torch_rng"])
    torch.cuda.set_rng_state_all(state["cuda_rng"])


def append_csv(path, header, row):
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerow(row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rebuild_v1/r02_budget_pilot_12k.json")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--scheduler-total-steps", type=int, default=None)
    parser.add_argument("--stop-at-step", type=int, default=None)
    parser.add_argument("--smoke-steps", type=int, default=0)
    parser.add_argument("--smoke-eval", action="store_true")
    parser.add_argument("--run-tag", default="")
    args = parser.parse_args()

    cfg_path = resolve_root_relative(args.config)
    cfg = read_json(cfg_path)
    if cfg["model_id"] != "R02" or cfg["model"] != "dual_f0_clean":
        raise RuntimeError("This trainer is intentionally restricted to the R02 clean F0 pilot")

    split_path = resolve_root_relative(cfg["split_file"])
    split = read_json(split_path)
    train_ids = list(split["train16"])
    val_ids = list(split["val2"])
    exposed_test6 = set(split["historical_exposed_test6"])
    if set(train_ids) & set(val_ids):
        raise RuntimeError("train/val overlap")
    if (set(train_ids) | set(val_ids)) & exposed_test6:
        raise RuntimeError("REBUILD_V1 train/val must not contain historical TEST6")
    if len(train_ids) != 16 or len(val_ids) != 2:
        raise RuntimeError("expected train16/val2")

    default_sched = int(cfg["schedule"]["scheduler_total_steps"])
    default_stop = int(cfg["schedule"]["stop_at_step"])
    scheduler_total_steps = args.scheduler_total_steps or default_sched
    stop_at_step = args.stop_at_step or default_stop
    if scheduler_total_steps <= 0 or stop_at_step <= 0 or stop_at_step > scheduler_total_steps:
        raise ValueError("require 0 < stop_at_step <= scheduler_total_steps")
    if args.smoke_steps < 0:
        raise ValueError("smoke steps must be >=0")
    target_step = args.smoke_steps if args.smoke_steps > 0 else stop_at_step

    seed = int(cfg["seed"])
    set_seed(seed)
    data_root = Path(cfg["data_root"])
    pretrain = Path(cfg["pretrain"])
    if not pretrain.is_file():
        raise FileNotFoundError(pretrain)

    run_kind = f"smoke{args.smoke_steps}" if args.smoke_steps > 0 else f"sched{scheduler_total_steps}_stop{stop_at_step}"
    suffix = f"_{args.run_tag}" if args.run_tag else ""
    run_dir = ROOT / "runs" / "rebuild_v1" / f"R02_dual_f0_seed{seed}_{run_kind}{suffix}"
    if run_dir.exists() and not args.resume:
        raise FileExistsError(f"refusing to overwrite: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)

    signature = {
        "config_file": str(cfg_path),
        "split_file": str(split_path),
        "seed": seed,
        "train_ids": train_ids,
        "val_ids": val_ids,
        "scheduler_total_steps": scheduler_total_steps,
        "stop_at_step": stop_at_step,
        "model": "R02_dual_F0",
        "test6_loaded": False,
    }
    with open(run_dir / "run_metadata.json", "w", encoding="utf-8") as f:
        json.dump({"config": cfg, "split": split, "signature": signature}, f, indent=2, ensure_ascii=False)

    train_cache, val_cache = preload(data_root, train_ids, val_ids)
    resume_path = run_dir / "last_train_state.pth"
    state = None
    if args.resume:
        if not resume_path.is_file():
            raise FileNotFoundError(resume_path)
        state = torch.load(resume_path, map_location="cpu")
        if state.get("signature") != signature:
            raise RuntimeError("resume signature mismatch; refusing to mix schedules/splits")

    net, model_cfg = build_model(cfg, pretrain, resume_state=state)
    optimizer = build_optimizer(net, cfg)
    global_step = 0
    best = None
    if state is not None:
        optimizer.load_state_dict(state["optimizer"])
        global_step = int(state["global_step"])
        best = state.get("best")
        restore_rng(state)
        print(f"[RESUME] global_step={global_step}")

    train_csv = run_dir / "train_history.csv"
    val_csv = run_dir / "val_history.csv"
    eval_interval = int(cfg["validation"]["eval_interval_steps"])
    accum_steps = int(cfg["accum_steps"])
    if int(cfg["effective_batch"]) != int(cfg["micro_batch"]) * accum_steps:
        raise RuntimeError("effective batch metadata mismatch")

    print("=" * 100)
    print("REBUILD_V1 R02 COMPLETE-SCHEDULE BUDGET PILOT")
    print("run:", run_dir)
    print("train16:", train_ids)
    print("val2:", val_ids)
    print("TEST6 loaded: False")
    print("scheduler_total_steps:", scheduler_total_steps)
    print("stop_at_step:", stop_at_step)
    print("actual target:", target_step)
    print("warmup_steps:", cfg["schedule"]["warmup_steps"])
    print("patch/effective batch:", cfg["patch"], cfg["effective_batch"])
    print("val stride:", cfg["validation"]["stride"])
    print("=" * 100)

    loss_buffer = []
    torch.cuda.reset_peak_memory_stats()
    while global_step < target_step:
        next_step = global_step + 1
        t0 = time.time()
        lrs = set_lr(optimizer, cfg, next_step, scheduler_total_steps)
        optimizer.zero_grad(set_to_none=True)
        micro_losses = []
        all_scales = []

        for _ in range(accum_steps):
            optical, dsm, gt, scales = sample_batch(train_cache, train_ids, cfg)
            logits = net(optical, dsm)
            flat_logits = logits.permute(0, 2, 3, 1).contiguous().view(-1, logits.shape[1])
            flat_gt = gt.contiguous().view(-1)
            loss = F.cross_entropy(flat_logits, flat_gt)
            if not torch.isfinite(loss):
                raise RuntimeError(f"non-finite loss before step {next_step}")
            (loss / accum_steps).backward()
            micro_losses.append(float(loss.detach()))
            all_scales.extend(scales)
            del optical, dsm, gt, logits, loss

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
            args.smoke_steps == 0 and (global_step % eval_interval == 0 or global_step == target_step)
        ) or (
            args.smoke_steps > 0 and args.smoke_eval and global_step == target_step
        )

        if do_eval:
            print(f"\n--- VAL2 @ step {global_step} ---")
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
                }, run_dir / "best_model.pth")
                print(f"[BEST] {100*score:.4f}% @ {global_step}")

        # Overwrite one resumable state periodically and at the requested stop.
        if global_step % 250 == 0 or global_step == target_step:
            save_state(resume_path, net, optimizer, global_step, best, signature)

    summary = {
        "global_step": global_step,
        "scheduler_total_steps": scheduler_total_steps,
        "stop_at_step": stop_at_step,
        "best": best,
        "peak_allocated_gib": float(torch.cuda.max_memory_allocated()/1024**3),
        "run_dir": str(run_dir),
        "test6_loaded": False,
    }
    with open(run_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print("=" * 100)
    print("COMPLETE", json.dumps(summary, ensure_ascii=False))
    print("=" * 100)


if __name__ == "__main__":
    main()
