import argparse
import csv
import json
import math
import os
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import numpy as np
import torch
import torch.nn.functional as F

import train_rebuild_v1_r01_optical_only as r01
import train_rebuild_v1_r02_budget_pilot as r02

DEVICE = torch.device("cuda:0")
VALID_MODES = {
    "B1-C": "ce_control",
    "B1-KD": "safe_teacher_kd",
    "B1-SAFE": "safe_teacher_plus_fallback",
}


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def git_head():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return None


def load_checkpoint(path):
    path = r02.resolve_root_relative(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    state = torch.load(path, map_location="cpu")
    if "model" not in state:
        raise RuntimeError(f"checkpoint has no model state: {path}")
    return path, state


def validate_config(cfg):
    model_id = str(cfg.get("model_id", "")).upper()
    if model_id not in VALID_MODES:
        raise RuntimeError(f"unsupported B1 model_id: {model_id}")
    if cfg.get("model") != "dual_f0_quality_plus_modality_dropout":
        raise RuntimeError("B1 student must retain the R05 F0 architecture")
    mode = str(cfg["distillation"]["mode"])
    if mode != VALID_MODES[model_id]:
        raise RuntimeError(f"model_id/mode mismatch: {model_id}/{mode}")
    aug = cfg["augmentation"]
    total = sum(
        float(aug[key])
        for key in (
            "clean_p",
            "global_degraded_p",
            "global_missing_p",
            "local_missing_p",
            "local_degraded_p",
        )
    )
    if abs(total - 1.0) > 1e-9:
        raise RuntimeError(f"B1 treatment probabilities sum to {total}")
    if set(aug["degraded_types"]) != {"blur5", "down2", "down4", "down8"}:
        raise RuntimeError("B1 degraded_types mismatch")
    if not aug["local_area_fractions"]:
        raise RuntimeError("B1 local_area_fractions is empty")
    if model_id == "B1-C" and (
        float(cfg["distillation"]["teacher_kl_weight"]) != 0.0
        or float(cfg["distillation"]["missing_fallback_kl_weight"]) != 0.0
    ):
        raise RuntimeError("B1-C must be CE only")
    if model_id == "B1-KD" and float(
        cfg["distillation"]["missing_fallback_kl_weight"]
    ) != 0.0:
        raise RuntimeError("B1-KD must not use the extra fallback loss")


def blur5(x):
    return F.avg_pool2d(F.pad(x, (2, 2, 2, 2), mode="reflect"), 5, 1)


def down_restore(x, factor):
    h, w = x.shape[-2:]
    small = F.interpolate(
        x,
        size=(max(1, h // factor), max(1, w // factor)),
        mode="bilinear",
        align_corners=False,
        antialias=True,
    )
    return F.interpolate(small, size=(h, w), mode="bilinear", align_corners=False)


def degrade(x, kind):
    if x.ndim != 3:
        raise RuntimeError(f"DSM degradation expects BxHxW, got {tuple(x.shape)}")
    x4 = x.unsqueeze(1)
    if kind == "blur5":
        out = blur5(x4)
    elif kind.startswith("down"):
        out = down_restore(x4, int(kind.replace("down", "")))
    else:
        raise ValueError(kind)
    return out.squeeze(1)


def random_rectangle(height, width, area_fraction):
    aspect = math.exp(random.uniform(math.log(0.5), math.log(2.0)))
    rect_h = max(1, min(height, int(round(math.sqrt(area_fraction / aspect) * height))))
    rect_w = max(1, min(width, int(round(area_fraction * height * width / rect_h))))
    top = random.randint(0, height - rect_h)
    left = random.randint(0, width - rect_w)
    return top, left, rect_h, rect_w


def init_counts(cfg):
    keys = ["clean", "global_missing", "local_missing"]
    keys += [f"global_{kind}" for kind in cfg["augmentation"]["degraded_types"]]
    keys += [f"local_{kind}" for kind in cfg["augmentation"]["degraded_types"]]
    return {key: 0 for key in keys}


def apply_b1_treatments(dsm, cfg, counts):
    aug = cfg["augmentation"]
    treated = dsm.clone()
    missing = torch.zeros_like(dsm, dtype=torch.bool)
    labels = []
    p1 = float(aug["clean_p"])
    p2 = p1 + float(aug["global_degraded_p"])
    p3 = p2 + float(aug["global_missing_p"])
    p4 = p3 + float(aug["local_missing_p"])
    kinds = list(aug["degraded_types"])
    areas = [float(x) for x in aug["local_area_fractions"]]
    height, width = dsm.shape[-2:]

    for i in range(dsm.shape[0]):
        u = random.random()
        if u < p1:
            key = "clean"
        elif u < p2:
            kind = random.choice(kinds)
            treated[i : i + 1] = degrade(treated[i : i + 1], kind)
            key = f"global_{kind}"
        elif u < p3:
            treated[i].zero_()
            missing[i].fill_(True)
            key = "global_missing"
        else:
            top, left, rh, rw = random_rectangle(height, width, random.choice(areas))
            region = (slice(top, top + rh), slice(left, left + rw))
            if u < p4:
                treated[i][region] = 0.0
                missing[i][region] = True
                key = "local_missing"
            else:
                kind = random.choice(kinds)
                source = treated[i : i + 1, top : top + rh, left : left + rw]
                treated[i, top : top + rh, left : left + rw] = degrade(source, kind)[0]
                key = f"local_{kind}"
        counts[key] += 1
        labels.append(key)
    return treated, missing, labels


def kl_map(student_logits, teacher_prob_t, temperature):
    return (
        F.kl_div(
            F.log_softmax(student_logits / temperature, dim=1),
            teacher_prob_t,
            reduction="none",
        ).sum(dim=1)
        * temperature
        * temperature
    )


def teacher_targets(r01_teacher, r05_teacher, optical, dsm, missing, temperature):
    # no_grad keeps ordinary tensors that KL divergence can safely retain for
    # the student's backward pass; inference_mode tensors can be rejected when
    # an autograd operator needs to save its target.
    with torch.no_grad():
        logits1 = r01_teacher(optical)
        logits5 = r05_teacher(optical, dsm)
        prob1 = F.softmax(logits1, dim=1)
        prob5 = F.softmax(logits5, dim=1)
        choose5 = prob5.amax(dim=1) > prob1.amax(dim=1)
        choose5 &= ~missing
        prob1_t = F.softmax(logits1 / temperature, dim=1)
        prob5_t = F.softmax(logits5 / temperature, dim=1)
        safe_t = torch.where(choose5.unsqueeze(1), prob5_t, prob1_t)
    return safe_t, prob1_t, choose5


def save_state(path, net, optimizer, step, best, signature, counts):
    torch.save(
        {
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
        },
        path,
    )


def write_counts(path, counts):
    total = int(sum(counts.values()))
    payload = {
        "total_samples": total,
        "counts": counts,
        "fractions": {key: value / total if total else 0.0 for key, value in counts.items()},
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def append_csv(path, header, row):
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if new:
            writer.writerow(header)
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--smoke-steps", type=int, default=0)
    parser.add_argument("--smoke-eval", action="store_true")
    parser.add_argument("--run-tag", default="")
    args = parser.parse_args()

    cfg_path = r02.resolve_root_relative(args.config)
    cfg = r02.read_json(cfg_path)
    validate_config(cfg)
    model_id = str(cfg["model_id"]).upper()
    mode = str(cfg["distillation"]["mode"])
    seed = int(cfg["seed"])
    r02.set_seed(seed)

    split_path = r02.resolve_root_relative(cfg["split_file"])
    split = r02.read_json(split_path)
    train_ids, val_ids = list(split["train16"]), list(split["val2"])
    exposed = set(split["historical_exposed_test6"])
    if set(train_ids) & set(val_ids) or (set(train_ids) | set(val_ids)) & exposed:
        raise RuntimeError("Train16/Val2 split safety check failed")
    if len(train_ids) != 16 or len(val_ids) != 2:
        raise RuntimeError("expected Train16/Val2")

    total_steps = int(cfg["schedule"]["scheduler_total_steps"])
    stop_step = int(cfg["schedule"]["stop_at_step"])
    target_step = int(args.smoke_steps) if args.smoke_steps > 0 else stop_step
    if not (0 < target_step <= stop_step <= total_steps):
        raise RuntimeError("invalid B1 schedule")
    if int(cfg["effective_batch"]) != int(cfg["micro_batch"]) * int(cfg["accum_steps"]):
        raise RuntimeError("effective batch metadata mismatch")

    slug = {"B1-C": "B1_C_ce_control", "B1-KD": "B1_KD_safe_teacher", "B1-SAFE": "B1_SAFE_fallback"}[model_id]
    run_kind = f"smoke{target_step}" if args.smoke_steps else f"sched{total_steps}_stop{stop_step}"
    suffix = f"_{args.run_tag}" if args.run_tag else ""
    run_dir = ROOT / "runs/rebuild_v1" / f"{slug}_seed{seed}_{run_kind}{suffix}"
    if run_dir.exists() and not args.resume:
        raise FileExistsError(f"refusing to overwrite: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)

    signature = {
        "config_file": str(cfg_path),
        "split_file": str(split_path),
        "model_id": model_id,
        "mode": mode,
        "seed": seed,
        "train_ids": train_ids,
        "val_ids": val_ids,
        "scheduler_total_steps": total_steps,
        "stop_at_step": stop_step,
        "student_init": str(r02.resolve_root_relative(cfg["student_init"])),
        "test6_loaded": False,
    }

    train_cache, val_cache = r02.preload(Path(cfg["data_root"]), train_ids, val_ids)
    resume_path = run_dir / "last_train_state.pth"
    counts = init_counts(cfg)
    state = None
    if args.resume:
        if not resume_path.is_file():
            raise FileNotFoundError(resume_path)
        state = torch.load(resume_path, map_location="cpu")
        if state.get("signature") != signature:
            raise RuntimeError("resume signature mismatch")
        if set(state.get("augmentation_counts", {})) != set(counts):
            raise RuntimeError("resume augmentation counts mismatch")
        counts = {key: int(value) for key, value in state["augmentation_counts"].items()}

    if state is None:
        student_init_path, student_init_state = load_checkpoint(cfg["student_init"])
        student, _ = r02.build_model(cfg, Path(cfg["pretrain"]), resume_state=student_init_state)
    else:
        student_init_path = r02.resolve_root_relative(cfg["student_init"])
        student, _ = r02.build_model(cfg, Path(cfg["pretrain"]), resume_state=state)
    optimizer = r02.build_optimizer(student, cfg)
    global_step, best = 0, None
    if state is not None:
        optimizer.load_state_dict(state["optimizer"])
        global_step = int(state["global_step"])
        best = state.get("best")
        print(f"[RESUME] {model_id} global_step={global_step}")

    r01_teacher = r05_teacher = None
    r01_path = r05_path = None
    if mode != "ce_control":
        r01_path, r01_state = load_checkpoint(cfg["r01_teacher"])
        r05_path, r05_state = load_checkpoint(cfg["r05_teacher"])
        c1 = r02.read_json(ROOT / "configs/rebuild_v1/r01_optical_only_16k.json")
        c5 = r02.read_json(ROOT / "configs/rebuild_v1/r05_quality_plus_dropout_16k.json")
        r01_teacher, _, _ = r01.build_model(c1, Path(c1["pretrain"]), resume_state=r01_state)
        r05_teacher, _ = r02.build_model(c5, Path(c5["pretrain"]), resume_state=r05_state)
        for teacher in (r01_teacher, r05_teacher):
            teacher.eval()
            teacher.requires_grad_(False)

    # Model construction consumes Torch RNG. Reset only after every optional
    # teacher has been built so all three fresh runs see the same crops,
    # treatments and student stochastic state. A resumed run restores its exact
    # saved state at this same point.
    if state is None:
        r02.set_seed(seed)
    else:
        r02.restore_rng(state)

    started_at = now_iso()
    metadata = {
        "experiment_id": model_id,
        "started_at": started_at,
        "git_commit": git_head(),
        "config": cfg,
        "split": split,
        "signature": signature,
        "resume": bool(args.resume),
        "student_init_checkpoint": str(student_init_path),
        "r01_teacher_checkpoint": str(r01_path) if r01_path else None,
        "r05_teacher_checkpoint": str(r05_path) if r05_path else None,
    }
    (run_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )

    print("=" * 100)
    print(f"REBUILD_V1 {model_id}: {mode}")
    print("run:", run_dir)
    print("device: physical GPU 0 / logical cuda:0")
    print("actual target:", target_step)
    print("TEST6 loaded: False")
    print("=" * 100)

    train_csv = run_dir / "train_history.csv"
    val_csv = run_dir / "val_history.csv"
    counts_path = run_dir / "augmentation_counts.json"
    accum_steps = int(cfg["accum_steps"])
    eval_interval = int(cfg["validation"]["eval_interval_steps"])
    temperature = float(cfg["distillation"]["temperature"])
    kd_weight = float(cfg["distillation"]["teacher_kl_weight"])
    fallback_weight = float(cfg["distillation"]["missing_fallback_kl_weight"])
    loss_buffer = []
    torch.cuda.reset_peak_memory_stats()

    while global_step < target_step:
        next_step = global_step + 1
        started = time.time()
        lrs = r02.set_lr(optimizer, cfg, next_step, total_steps)
        optimizer.zero_grad(set_to_none=True)
        micro_total, micro_ce, micro_kd, micro_fb = [], [], [], []
        scales_all, routed_r05 = [], []
        for _ in range(accum_steps):
            optical, dsm, gt, scales = r02.sample_batch(train_cache, train_ids, cfg)
            dsm, missing, _ = apply_b1_treatments(dsm, cfg, counts)
            logits = student(optical, dsm)
            # Match the deterministic CE path used by the accepted R01-R05
            # trainers. CUDA nll_loss2d has no deterministic implementation in
            # the server's PyTorch build, while the flattened 2-D kernel does.
            flat_logits = logits.permute(0, 2, 3, 1).contiguous().view(
                -1, logits.shape[1]
            )
            flat_gt = gt.contiguous().view(-1)
            ce = F.cross_entropy(flat_logits, flat_gt)
            kd = logits.new_zeros(())
            fallback = logits.new_zeros(())
            if mode != "ce_control":
                safe_t, r01_t, choose5 = teacher_targets(
                    r01_teacher, r05_teacher, optical, dsm, missing, temperature
                )
                kd_pixels = kl_map(logits, safe_t, temperature)
                kd = kd_pixels.mean()
                if fallback_weight > 0.0 and bool(missing.any()):
                    fallback_pixels = kl_map(logits, r01_t, temperature)
                    fallback = fallback_pixels[missing].mean()
                routed_r05.append(float(choose5.float().mean()))
            loss = ce + kd_weight * kd + fallback_weight * fallback
            if not torch.isfinite(loss):
                raise RuntimeError(f"non-finite {model_id} loss before step {next_step}")
            (loss / accum_steps).backward()
            micro_total.append(float(loss.detach()))
            micro_ce.append(float(ce.detach()))
            micro_kd.append(float(kd.detach()))
            micro_fb.append(float(fallback.detach()))
            scales_all.extend(scales)
            del optical, dsm, gt, missing, logits, flat_logits, flat_gt, ce, kd, fallback, loss

        optimizer.step()
        global_step = next_step
        torch.cuda.synchronize()
        loss_value = float(np.mean(micro_total))
        loss_buffer.append(loss_value)
        seconds = time.time() - started
        row = [
            global_step,
            lrs["backbone"],
            lrs["decoder_head"],
            loss_value,
            float(np.mean(micro_ce)),
            float(np.mean(micro_kd)),
            float(np.mean(micro_fb)),
            float(np.mean(loss_buffer[-50:])),
            float(np.mean(scales_all)),
            float(np.mean(routed_r05)) if routed_r05 else 0.0,
            seconds,
        ]
        append_csv(
            train_csv,
            ["step", "lr_backbone", "lr_decoder_head", "loss", "ce", "teacher_kl", "fallback_kl", "mean50", "scale_mean", "teacher_r05_pixel_fraction", "sec_per_step"],
            row,
        )
        if global_step == 1 or global_step % 20 == 0:
            print(
                f"step {global_step:05d}/{target_step} loss={loss_value:.6f} "
                f"ce={np.mean(micro_ce):.6f} kd={np.mean(micro_kd):.6f} "
                f"fb={np.mean(micro_fb):.6f} GPU={torch.cuda.memory_allocated()/1024**3:.2f}G "
                f"{seconds:.2f}s",
                flush=True,
            )

        do_eval = (
            (not args.smoke_steps and (global_step % eval_interval == 0 or global_step == target_step))
            or (args.smoke_steps and args.smoke_eval and global_step == target_step)
        )
        if do_eval:
            result = r02.evaluate_val(student, val_cache, val_ids, cfg)
            full, nb = result["full"], result["noboundary"]
            print(
                f"VAL2 step={global_step} FULL={100*full['mIoU_fg5']:.4f} "
                f"NB={100*nb['mIoU_fg5']:.4f}",
                flush=True,
            )
            append_csv(
                val_csv,
                ["step", "full_OA", "full_mIoU_fg5", "nb_OA", "nb_mIoU_fg5", "eval_seconds"],
                [global_step, full["OA"], full["mIoU_fg5"], nb["OA"], nb["mIoU_fg5"], result["seconds"]],
            )
            score = float(nb["mIoU_fg5"])
            if best is None or score > float(best["value"]):
                best = {"metric": "val2_noboundary_mIoU_fg5", "value": score, "step": global_step}
                torch.save(
                    {
                        "model": student.state_dict(),
                        "global_step": global_step,
                        "best": best,
                        "metrics": result,
                        "signature": signature,
                        "augmentation_counts": dict(counts),
                    },
                    run_dir / "best_model.pth",
                )
                print(f"[BEST] {100*score:.4f}% @ {global_step}", flush=True)

        if global_step % 250 == 0 or global_step == target_step:
            save_state(resume_path, student, optimizer, global_step, best, signature, counts)
            write_counts(counts_path, counts)

    count_payload = write_counts(counts_path, counts)
    expected_samples = global_step * accum_steps * int(cfg["micro_batch"])
    if count_payload["total_samples"] != expected_samples:
        raise RuntimeError(
            f"augmentation count mismatch {count_payload['total_samples']} != {expected_samples}"
        )
    summary = {
        "experiment_id": model_id,
        "mode": mode,
        "started_at": started_at,
        "completed_at": now_iso(),
        "git_commit": git_head(),
        "global_step": global_step,
        "scheduler_total_steps": total_steps,
        "stop_at_step": stop_step,
        "best": best,
        "peak_allocated_gib": float(torch.cuda.max_memory_allocated() / 1024**3),
        "run_dir": str(run_dir),
        "test6_loaded": False,
        "augmentation": count_payload,
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print("COMPLETE", json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
