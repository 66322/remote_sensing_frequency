import os
import sys
import csv
import json
import time
import random
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import numpy as np
import torch
import torch.nn.functional as F

import train_rebuild_v1_r02_budget_pilot as r02

DEVICE = torch.device("cuda:0")


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return None


def mean_blur5(t):
    # t: 1xCxHxW, corruption after crop/resize.
    z = F.pad(t, (2, 2, 2, 2), mode="reflect")
    return F.avg_pool2d(z, kernel_size=5, stride=1)


def down2_restore(t):
    h, w = t.shape[-2:]
    small = F.interpolate(
        t,
        size=(max(1, h // 2), max(1, w // 2)),
        mode="bilinear",
        align_corners=False,
        antialias=True,
    )
    return F.interpolate(
        small,
        size=(h, w),
        mode="bilinear",
        align_corners=False,
    )


def init_counts(variant):
    if variant == "R03":
        keys = [
            "clean",
            "optical_blur5",
            "optical_down2",
            "second_stream_blur5",
            "second_stream_down2",
        ]
    elif variant == "R04":
        keys = ["clean", "optical_zero", "second_stream_zero"]
    elif variant == "R05":
        keys = [
            "clean",
            "optical_blur5",
            "optical_down2",
            "second_stream_blur5",
            "second_stream_down2",
            "optical_zero",
            "second_stream_zero",
        ]
    else:
        raise ValueError(variant)
    return {k: 0 for k in keys}


def validate_policy(cfg, variant):
    aug = cfg["augmentation"]

    if variant == "R03":
        if not aug.get("quality_corruption") or aug.get("modality_dropout"):
            raise RuntimeError("R03 config must enable only quality_corruption")

        total = (
            float(aug["clean_p"])
            + float(aug["optical_degraded_p"])
            + float(aug["dsm_degraded_p"])
        )
        within = (
            float(aug["blur5_within_degraded_p"])
            + float(aug["down2_within_degraded_p"])
        )
        if abs(total - 1.0) > 1e-9 or abs(within - 1.0) > 1e-9:
            raise RuntimeError("R03 probabilities must sum to one")

    elif variant == "R04":
        if aug.get("quality_corruption") or not aug.get("modality_dropout"):
            raise RuntimeError("R04 config must enable only modality_dropout")

        total = (
            float(aug["clean_p"])
            + float(aug["optical_dropout_p"])
            + float(aug["dsm_dropout_p"])
        )
        if abs(total - 1.0) > 1e-9 or not aug.get("never_drop_both", False):
            raise RuntimeError("R04 policy mismatch")

    elif variant == "R05":
        if not aug.get("quality_corruption") or not aug.get("modality_dropout"):
            raise RuntimeError(
                "R05 must enable both quality_corruption and modality_dropout"
            )

        dropout_total = (
            float(aug["optical_dropout_p"])
            + float(aug["dsm_dropout_p"])
            + float(aug["no_dropout_p"])
        )

        conditional_total = (
            float(aug["clean_within_no_dropout_p"])
            + float(aug["optical_degraded_within_no_dropout_p"])
            + float(aug["dsm_degraded_within_no_dropout_p"])
        )

        degraded_total = (
            float(aug["blur5_within_degraded_p"])
            + float(aug["down2_within_degraded_p"])
        )

        if abs(dropout_total - 1.0) > 1e-9:
            raise RuntimeError("R05 dropout probabilities must sum to one")
        if abs(conditional_total - 1.0) > 1e-9:
            raise RuntimeError("R05 conditional quality probabilities must sum to one")
        if abs(degraded_total - 1.0) > 1e-9:
            raise RuntimeError("R05 degraded subtype probabilities must sum to one")
        if not aug.get("never_drop_both", False):
            raise RuntimeError("R05 must never drop both modalities")

    else:
        raise ValueError(variant)


def apply_training_treatment(op_t, ds_t, cfg, variant, counts):
    aug = cfg["augmentation"]

    if variant == "R03":
        u = random.random()
        p_clean = float(aug["clean_p"])
        p_opt = float(aug["optical_degraded_p"])

        if u < p_clean:
            key = "clean"
        elif u < p_clean + p_opt:
            if random.random() < float(aug["blur5_within_degraded_p"]):
                op_t = mean_blur5(op_t)
                key = "optical_blur5"
            else:
                op_t = down2_restore(op_t)
                key = "optical_down2"
        else:
            if random.random() < float(aug["blur5_within_degraded_p"]):
                ds_t = mean_blur5(ds_t)
                key = "second_stream_blur5"
            else:
                ds_t = down2_restore(ds_t)
                key = "second_stream_down2"

    elif variant == "R04":
        u = random.random()
        p_clean = float(aug["clean_p"])
        p_opt = float(aug["optical_dropout_p"])

        if u < p_clean:
            key = "clean"
        elif u < p_clean + p_opt:
            op_t = torch.zeros_like(op_t)
            key = "optical_zero"
        else:
            ds_t = torch.zeros_like(ds_t)
            key = "second_stream_zero"

    elif variant == "R05":
        # ----------------------------------------------------
        # Stage 1: modality dropout.
        # If dropout occurs, do NOT apply quality corruption.
        # ----------------------------------------------------
        u = random.random()
        p_opt_drop = float(aug["optical_dropout_p"])
        p_dsm_drop = float(aug["dsm_dropout_p"])

        if u < p_opt_drop:
            op_t = torch.zeros_like(op_t)
            key = "optical_zero"

        elif u < p_opt_drop + p_dsm_drop:
            ds_t = torch.zeros_like(ds_t)
            key = "second_stream_zero"

        else:
            # ------------------------------------------------
            # Stage 2: R03 quality policy conditional on
            # no modality dropout.
            # ------------------------------------------------
            v = random.random()
            p_clean = float(aug["clean_within_no_dropout_p"])
            p_opt_deg = float(aug["optical_degraded_within_no_dropout_p"])

            if v < p_clean:
                key = "clean"

            elif v < p_clean + p_opt_deg:
                if random.random() < float(aug["blur5_within_degraded_p"]):
                    op_t = mean_blur5(op_t)
                    key = "optical_blur5"
                else:
                    op_t = down2_restore(op_t)
                    key = "optical_down2"

            else:
                if random.random() < float(aug["blur5_within_degraded_p"]):
                    ds_t = mean_blur5(ds_t)
                    key = "second_stream_blur5"
                else:
                    ds_t = down2_restore(ds_t)
                    key = "second_stream_down2"

    else:
        raise ValueError(variant)

    counts[key] += 1
    return op_t, ds_t, key



def sample_batch(train_cache, train_ids, cfg, variant, counts):
    patch = int(cfg["patch"])
    batch = int(cfg["micro_batch"])
    aug = cfg["augmentation"]
    scale_min = float(aug["random_scale_min"])
    scale_max = float(aug["random_scale_max"])
    hp = float(aug["horizontal_flip_p"])
    vp = float(aug["vertical_flip_p"])

    ops, dss, gts, scales, treatments = [], [], [], [], []
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

        # C-OO-QD: replace DSM with a fixed Optical grayscale stream
        # AFTER matched crop/resize/flip and BEFORE the R05 treatment.
        # No DSM value reaches the network.
        ds_t = op_t.mean(dim=1, keepdim=True)

        # Frozen order:
        # normalized Optical -> crop/resize -> gray second stream
        # -> matched R05 treatment -> network.
        op_t, ds_t, treatment = apply_training_treatment(
            op_t, ds_t, cfg, variant, counts
        )
        ops.append(op_t.squeeze(0))
        dss.append(ds_t.squeeze(0).squeeze(0))
        gts.append(gt_t.squeeze(0).squeeze(0).long())
        scales.append(scale)
        treatments.append(treatment)

    return (
        torch.stack(ops).to(DEVICE, non_blocking=True),
        torch.stack(dss).to(DEVICE, non_blocking=True),
        torch.stack(gts).to(DEVICE, non_blocking=True),
        scales,
        treatments,
    )


def save_state(path, net, optimizer, step, best, signature, counts):
    torch.save({
        "model": net.state_dict(),
        "optimizer": optimizer.state_dict(),
        "global_step": int(step),
        "best": best,
        "signature": signature,
        "augmentation_counts": dict(counts),
        "python_rng": random.getstate(),
        "numpy_rng": np.random.get_state(),
        "torch_rng": torch.get_rng_state(),
        "cuda_rng": torch.cuda.get_rng_state_all(),
    }, path)


def write_counts(path, counts):
    total = int(sum(counts.values()))
    payload = {
        "total_samples": total,
        "counts": counts,
        "fractions": {k: (v / total if total else 0.0) for k, v in counts.items()},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return payload


def append_csv(path, header, row):
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerow(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--smoke-steps", type=int, default=0)
    ap.add_argument("--smoke-eval", action="store_true")
    ap.add_argument("--run-tag", default="")
    args = ap.parse_args()

    cfg_path = r02.resolve_root_relative(args.config)
    cfg = r02.read_json(cfg_path)
    variant = str(cfg.get("model_id", "")).upper()
    if variant != "C-OO-QD":
        raise RuntimeError(
            "This trainer is intentionally restricted to C-OO-QD"
        )

    expected_model = "dual_f0_optical_gray_quality_plus_dropout"
    if cfg.get("model") != expected_model:
        raise RuntimeError("C-OO-QD model metadata mismatch")

    # C-OO-QD uses the exact R05 probability policy.
    policy_variant = "R05"
    validate_policy(cfg, policy_variant)

    split_path = r02.resolve_root_relative(cfg["split_file"])
    split = r02.read_json(split_path)
    train_ids = list(split["train16"])
    val_ids = list(split["val2"])
    exposed = set(split["historical_exposed_test6"])
    if set(train_ids) & set(val_ids):
        raise RuntimeError("train/val overlap")
    if (set(train_ids) | set(val_ids)) & exposed:
        raise RuntimeError("train/val overlaps historical TEST6")
    if len(train_ids) != 16 or len(val_ids) != 2:
        raise RuntimeError("expected Train16 / Val2")

    scheduler_total_steps = int(cfg["schedule"]["scheduler_total_steps"])
    stop_at_step = int(cfg["schedule"]["stop_at_step"])
    if not (0 < stop_at_step <= scheduler_total_steps):
        raise RuntimeError("invalid schedule")
    target_step = args.smoke_steps if args.smoke_steps > 0 else stop_at_step

    seed = int(cfg["seed"])
    r02.set_seed(seed)
    data_root = Path(cfg["data_root"])
    pretrain = Path(cfg["pretrain"])
    if not pretrain.is_file():
        raise FileNotFoundError(pretrain)

    slug = "C_OO_QD_dual_optical_gray_quality_plus_dropout"
    run_kind = f"smoke{args.smoke_steps}" if args.smoke_steps else f"sched{scheduler_total_steps}_stop{stop_at_step}"
    suffix = f"_{args.run_tag}" if args.run_tag else ""
    run_dir = ROOT / "runs/rebuild_v1" / f"{slug}_seed{seed}_{run_kind}{suffix}"
    if run_dir.exists() and not args.resume:
        raise FileExistsError(f"refusing to overwrite: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)

    started_at = now_iso()
    meta_path = run_dir / "run_metadata.json"
    if args.resume and meta_path.is_file():
        started_at = r02.read_json(meta_path).get("started_at", started_at)

    signature = {
        "config_file": str(cfg_path),
        "split_file": str(split_path),
        "seed": seed,
        "train_ids": train_ids,
        "val_ids": val_ids,
        "scheduler_total_steps": scheduler_total_steps,
        "stop_at_step": stop_at_step,
        "model": expected_model,
        "variant": variant,
        "policy_variant": policy_variant,
        "second_stream": "fixed_optical_channel_mean",
        "dsm_loaded_for_dataset_compatibility": True,
        "dsm_used_by_network": False,
        "test6_loaded": False,
    }

    train_cache, val_cache = r02.preload(data_root, train_ids, val_ids)

    # Validation must also use Optical grayscale as the second stream.
    # The original DSM arrays are replaced before any validation inference.
    for tile_id, item in val_cache.items():
        item["dsm"] = item["optical"].mean(axis=2).astype(
            np.float32, copy=False
        )
    resume_path = run_dir / "last_train_state.pth"
    state = None
    counts = init_counts(policy_variant)
    if args.resume:
        if not resume_path.is_file():
            raise FileNotFoundError(resume_path)
        state = torch.load(resume_path, map_location="cpu")
        if state.get("signature") != signature:
            raise RuntimeError("resume signature mismatch")
        old_counts = state.get("augmentation_counts")
        if old_counts is None or set(old_counts) != set(counts):
            raise RuntimeError("resume augmentation counts missing/mismatch")
        counts = {k: int(v) for k, v in old_counts.items()}

    net, _ = r02.build_model(cfg, pretrain, resume_state=state)
    optimizer = r02.build_optimizer(net, cfg)
    global_step, best = 0, None
    if state is not None:
        optimizer.load_state_dict(state["optimizer"])
        global_step = int(state["global_step"])
        best = state.get("best")
        r02.restore_rng(state)
        print(f"[RESUME] {variant} global_step={global_step}")

    metadata = {
        "experiment_id": variant,
        "started_at": started_at,
        "last_launch_at": now_iso(),
        "git_commit": git_head(),
        "config": cfg,
        "split": split,
        "signature": signature,
        "resume": bool(args.resume),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    train_csv = run_dir / "train_history.csv"
    val_csv = run_dir / "val_history.csv"
    counts_path = run_dir / "augmentation_counts.json"
    eval_interval = int(cfg["validation"]["eval_interval_steps"])
    accum_steps = int(cfg["accum_steps"])
    if int(cfg["effective_batch"]) != int(cfg["micro_batch"]) * accum_steps:
        raise RuntimeError("effective batch metadata mismatch")

    print("=" * 100)
    print(f"REBUILD_V1 {variant} ROBUST DUAL F0")
    print("run:", run_dir)
    print("train16:", train_ids)
    print("val2:", val_ids)
    print("TEST6 loaded: False")
    print("scheduler_total_steps:", scheduler_total_steps)
    print("actual target:", target_step)
    print("policy:", json.dumps(cfg["augmentation"], ensure_ascii=False))
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
            optical, dsm, gt, scales, _ = sample_batch(
                train_cache,
                train_ids,
                cfg,
                policy_variant,
                counts,
            )
            logits = net(optical, dsm)
            flat_logits = logits.permute(0, 2, 3, 1).contiguous().view(-1, logits.shape[1])
            flat_gt = gt.contiguous().view(-1)
            loss = F.cross_entropy(flat_logits, flat_gt)
            if not torch.isfinite(loss):
                raise RuntimeError(f"non-finite {variant} loss before step {next_step}")
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
            (args.smoke_steps == 0 and (global_step % eval_interval == 0 or global_step == target_step))
            or (args.smoke_steps > 0 and args.smoke_eval and global_step == target_step)
        )
        if do_eval:
            print(f"\n--- {variant} CLEAN VAL2 @ step {global_step} ---")
            result = r02.evaluate_val(net, val_cache, val_ids, cfg)
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
                    "augmentation_counts": dict(counts),
                }, run_dir / "best_model.pth")
                print(f"[BEST] {100*score:.4f}% @ {global_step}")

        if global_step % 250 == 0 or global_step == target_step:
            save_state(resume_path, net, optimizer, global_step, best, signature, counts)
            write_counts(counts_path, counts)

    counts_payload = write_counts(counts_path, counts)
    expected_samples = int(global_step * accum_steps * int(cfg["micro_batch"]))
    if counts_payload["total_samples"] != expected_samples:
        raise RuntimeError(
            f"augmentation count mismatch {counts_payload['total_samples']} != {expected_samples}"
        )

    summary = {
        "experiment_id": variant,
        "started_at": started_at,
        "completed_at": now_iso(),
        "git_commit": git_head(),
        "global_step": global_step,
        "scheduler_total_steps": scheduler_total_steps,
        "stop_at_step": stop_at_step,
        "best": best,
        "peak_allocated_gib": float(torch.cuda.max_memory_allocated()/1024**3),
        "run_dir": str(run_dir),
        "test6_loaded": False,
        "augmentation": counts_payload,
    }
    with open(run_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print("=" * 100)
    print("COMPLETE", json.dumps(summary, ensure_ascii=False))
    print("=" * 100)


if __name__ == "__main__":
    main()
