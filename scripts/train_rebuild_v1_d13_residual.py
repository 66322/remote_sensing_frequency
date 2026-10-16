"""Train one D13 frozen-R01 residual arm. Formal runs never read Val2."""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

import argparse
import hashlib
import json
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]
import numpy as np
import torch
import torch.nn.functional as F

import train_rebuild_v1_r01_optical_only as r01
import train_rebuild_v1_r02_budget_pilot as r02
from eval_rebuild_v1_d4_expert_complementarity import validate_run
from d13_residual import ARMS, ResidualHead, features_for_arm, apply_residual, risk_loss

CONFIG = ROOT / "configs/rebuild_v1/d13_residual_overnight_20260924.json"
RUN_LABEL = "20260924"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def treatment(auxiliary, probabilities):
    """Apply the same sampled second-stream treatment to every matched arm."""
    import train_rebuild_v1_b1_distillation as b1
    x = auxiliary.clone()
    available = torch.ones_like(x, dtype=torch.bool)
    labels = []
    keys = list(probabilities)
    edges = np.cumsum([float(probabilities[k]) for k in keys])
    if abs(float(edges[-1]) - 1.0) > 1e-9:
        raise RuntimeError("D13 treatment probabilities must sum to one")
    for i in range(x.shape[0]):
        u = random.random()
        key = keys[int(np.searchsorted(edges, u, side="right"))]
        view = x[i:i+1]
        h, w = x.shape[-2:]
        if key == "clean":
            pass
        elif key == "dsm_blur5":
            x[i:i+1] = b1.degrade(view, "blur5")
        elif key == "dsm_down8":
            x[i:i+1] = b1.degrade(view, "down8")
        elif key == "dsm_noise_std010":
            x[i:i+1] = (view + torch.randn_like(view) * 0.10).clamp(0, 1)
        elif key == "roll16":
            x[i:i+1] = torch.roll(view, 16, dims=-1)
        elif key == "dsm_zero":
            x[i].zero_()
            available[i].zero_()
        elif key == "dsm_local_zero_q1":
            top = random.randint(0, h - h//2)
            left = random.randint(0, w - w//2)
            x[i, top:top+h//2, left:left+w//2] = 0
            available[i, top:top+h//2, left:left+w//2] = False
        elif key == "dsm_local_down8_q1":
            top = random.randint(0, h - h//2)
            left = random.randint(0, w - w//2)
            degraded = b1.degrade(x[i:i+1], "down8")[0]
            x[i, top:top+h//2, left:left+w//2] = degraded[top:top+h//2, left:left+w//2]
        else:
            raise ValueError(key)
        labels.append(key)
    return x, available, labels


def load_anchor(seed, cfg):
    anchor_config = r02.read_json(ROOT / cfg["r01_config"])
    run = ROOT / f"runs/rebuild_v1/R01_optical_only_seed{seed}_sched16000_stop16000"
    _, checkpoint_path = validate_run(run)
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    if int(checkpoint.get("global_step", -1)) < 1:
        raise RuntimeError("R01 checkpoint has no recorded global step")
    net, _, _ = r01.build_model(anchor_config, Path(anchor_config["pretrain"]),
                                 resume_state=checkpoint)
    net.eval()
    net.requires_grad_(False)
    return net, checkpoint_path, anchor_config


def run_dir(arm, seed, smoke_steps=0):
    kind = f"smoke{smoke_steps}" if smoke_steps else "sched4000_stop4000"
    return ROOT / "runs/rebuild_v1" / f"D13_{arm}_seed{seed}_{kind}_{RUN_LABEL}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--seed", type=int, choices=(42, 17), required=True)
    parser.add_argument("--smoke-steps", type=int, default=0)
    args = parser.parse_args()
    cfg = r02.read_json(CONFIG)
    tcfg = cfg["training"]
    split = r02.read_json(ROOT / cfg["split_file"])
    ids = list(split["train16"])
    if len(ids) != 16 or set(ids) & (set(split["val2"]) | set(split["historical_exposed_test6"])):
        raise RuntimeError("D13 split safety check failed")
    if args.seed not in cfg["seeds"] or args.arm not in cfg["stage1_arms"] + cfg["stage2_arms"]:
        raise RuntimeError("arm/seed absent from frozen config")
    if int(tcfg["micro_batch"]) * int(tcfg["accum_steps"]) != int(tcfg["effective_batch"]):
        raise RuntimeError("effective batch mismatch")
    steps = int(args.smoke_steps or tcfg["steps"])
    if not (0 < steps <= int(tcfg["steps"])):
        raise RuntimeError("invalid target steps")
    out = run_dir(args.arm, args.seed, args.smoke_steps)
    out.resolve().relative_to(Path("/home/jovyan/zzx").resolve())
    if out.exists():
        raise FileExistsError(f"refusing to overwrite {out}")
    out.mkdir(parents=True, exist_ok=False)

    anchor, anchor_path, anchor_config = load_anchor(args.seed, cfg)
    # Avoid loading Val2 for training, even for smoke runs.
    train_cache, _ = r02.preload(Path(anchor_config["data_root"]), ids, [])
    r02.set_seed(args.seed)
    head = ResidualHead().to(r02.DEVICE)
    init_digest = hashlib.sha256()
    for tensor in head.state_dict().values():
        init_digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    initial_head_sha256 = init_digest.hexdigest()
    optimizer = torch.optim.AdamW(head.parameters(), lr=float(tcfg["learning_rate"]),
                                  weight_decay=float(tcfg["weight_decay"]))
    # Reset after both model constructions so paired arms see identical crops,
    # corruption choices, and random noise for a given seed.
    r02.set_seed(args.seed)
    sampler_cfg = {"patch": tcfg["patch"], "micro_batch": tcfg["micro_batch"],
                   "augmentation": {k: tcfg[k] for k in ("random_scale_min", "random_scale_max",
                              "horizontal_flip_p", "vertical_flip_p")}}
    counts = {name: 0 for name in tcfg["condition_probabilities"]}
    decoder = []
    handle = anchor.decoder.register_forward_hook(lambda _m, _i, x: decoder.append(x))
    started = time.time()
    use_risk = args.arm in ("rgb_risk", "dsm_risk") or args.arm in cfg["stage2_arms"]
    metadata = dict(experiment=cfg["experiment"], arm=args.arm, seed=args.seed,
                    smoke_steps=args.smoke_steps, git_commit=subprocess.check_output(
                        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                    config_sha256=sha256(CONFIG), anchor_checkpoint=str(anchor_path),
                    anchor_sha256=sha256(anchor_path), train_tiles=ids,
                    initial_head_sha256=initial_head_sha256,
                    source_sha256={name: sha256(ROOT / name) for name in (
                        "scripts/d13_residual.py", "scripts/train_rebuild_v1_d13_residual.py",
                        "scripts/train_rebuild_v1_r01_optical_only.py",
                        "scripts/train_rebuild_v1_r02_budget_pilot.py",
                        "model/rebuild_v1_optical_only.py")},
                    val2_loaded=False, test6_loaded=False,
                    started_at=datetime.now().astimezone().isoformat(timespec="seconds"))
    (out / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    losses = []
    try:
        for step in range(1, steps + 1):
            optimizer.zero_grad(set_to_none=True)
            lr = float(tcfg["learning_rate"]) * (1 - (step - 1) / int(tcfg["steps"]))
            for group in optimizer.param_groups:
                group["lr"] = lr
            micro = []
            for _ in range(int(tcfg["accum_steps"])):
                optical, dsm, gt, _ = r02.sample_batch(train_cache, ids, sampler_cfg)
                auxiliary = optical.mean(dim=1) if args.arm.startswith("rgb_") else dsm
                auxiliary, available, kinds = treatment(auxiliary, tcfg["condition_probabilities"])
                for kind in kinds:
                    counts[kind] += 1
                decoder.clear()
                with torch.no_grad():
                    logits0 = anchor(optical)
                if len(decoder) != 1:
                    raise RuntimeError("R01 decoder hook returned unexpected count")
                sem = decoder.pop().detach()
                inputs = features_for_arm(args.arm, logits0.detach(), optical,
                                          auxiliary[:, None], sem)
                logits = apply_residual(logits0, head(inputs), available)
                loss, ce, risk = risk_loss(logits, logits0, gt, available, use_risk,
                                           float(tcfg["risk_lambda"]))
                if not bool(torch.isfinite(loss)):
                    raise RuntimeError(f"nonfinite D13 loss {args.arm}/{args.seed}/{step}")
                (loss / int(tcfg["accum_steps"])).backward()
                micro.append((float(loss.detach()), float(ce), float(risk)))
                del optical, dsm, gt, auxiliary, available, logits0, sem, inputs, logits, loss
            optimizer.step()
            losses.append(np.mean(micro, axis=0).tolist())
            if step == 1 or step % 100 == 0 or step == steps:
                print(f"D13 {args.arm} seed{args.seed} {step}/{steps} loss={losses[-1][0]:.5f} "
                      f"ce={losses[-1][1]:.5f} risk={losses[-1][2]:.5f} "
                      f"elapsed={time.time()-started:.1f}s "
                      f"GPU={torch.cuda.memory_allocated()/1024**3:.2f}GiB", flush=True)
    finally:
        handle.remove()
    torch.save({"model": head.state_dict(), "global_step": steps,
                "arm": args.arm, "seed": args.seed, "metadata": metadata},
               out / "final_model.pth")
    summary = dict(**metadata, completed_at=datetime.now().astimezone().isoformat(timespec="seconds"),
                   global_step=steps, final_loss=losses[-1], treatment_counts=counts,
                   seconds=time.time()-started, output=str(out),
                   peak_allocated_gib=torch.cuda.max_memory_allocated()/1024**3)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("D13 TRAIN COMPLETE", json.dumps({"arm": args.arm, "seed": args.seed,
                                             "steps": steps, "seconds": summary["seconds"]}), flush=True)


if __name__ == "__main__":
    main()
