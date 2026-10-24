import os
import sys
import gc
import json
import hashlib
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

CONFIG = ROOT / "configs" / "rebuild_v1" / "r02_budget_pilot_12k.json"
OUT = ROOT / "records" / "rebuild_v1_resume_exactness_20260915"
TMP = OUT / "resume_state_tmp.pth"
TOTAL_AUDIT_STEPS = 40
SPLIT_STEP = 20


def preload_train_only(cfg, train_ids):
    cache = {}
    data_root = Path(cfg["data_root"])
    print("PRELOAD TRAIN16 ONLY FOR RESUME AUDIT")
    for tile_id in train_ids:
        d = r02.load_tile(data_root, tile_id, need_nb=False)
        cache[tile_id] = (d["optical"], d["dsm"], d["full_gt"])
        print(" train", tile_id, d["full_gt"].shape)
    return cache


def train_range(net, optimizer, cache, train_ids, cfg, start_step, end_step, scheduler_total_steps):
    losses = []
    accum_steps = int(cfg["accum_steps"])
    net.train()
    for next_step in range(start_step, end_step + 1):
        r02.set_lr(optimizer, cfg, next_step, scheduler_total_steps)
        optimizer.zero_grad(set_to_none=True)
        micro_losses = []
        for _ in range(accum_steps):
            optical, dsm, gt, _ = r02.sample_batch(cache, train_ids, cfg)
            logits = net(optical, dsm)
            flat_logits = logits.permute(0, 2, 3, 1).contiguous().view(-1, logits.shape[1])
            flat_gt = gt.contiguous().view(-1)
            loss = F.cross_entropy(flat_logits, flat_gt)
            if not torch.isfinite(loss):
                raise RuntimeError(f"non-finite loss at step {next_step}")
            (loss / accum_steps).backward()
            micro_losses.append(float(loss.detach()))
            del optical, dsm, gt, logits, loss
        optimizer.step()
        torch.cuda.synchronize()
        value = float(np.mean(micro_losses))
        losses.append(value)
        if next_step == start_step or next_step == end_step or next_step % 10 == 0:
            print(f" step {next_step:03d} loss={value:.10f}")
    return losses


def hash_value(h, value):
    if torch.is_tensor(value):
        t = value.detach().cpu().contiguous()
        h.update(b"tensor")
        h.update(str(tuple(t.shape)).encode())
        h.update(str(t.dtype).encode())
        h.update(t.numpy().tobytes())
    elif isinstance(value, dict):
        h.update(b"dict")
        for k in sorted(value.keys(), key=lambda x: str(x)):
            h.update(str(k).encode())
            hash_value(h, value[k])
    elif isinstance(value, (list, tuple)):
        h.update(type(value).__name__.encode())
        for x in value:
            hash_value(h, x)
    elif isinstance(value, np.ndarray):
        h.update(b"ndarray")
        h.update(str(value.shape).encode())
        h.update(str(value.dtype).encode())
        h.update(value.tobytes())
    else:
        h.update(repr(value).encode())


def digest(value):
    h = hashlib.sha256()
    hash_value(h, value)
    return h.hexdigest()


def release(net, optimizer):
    del net
    del optimizer
    gc.collect()
    torch.cuda.empty_cache()


def main():
    cfg = r02.read_json(CONFIG)
    split = r02.read_json(r02.resolve_root_relative(cfg["split_file"]))
    train_ids = list(split["train16"])
    scheduler_total_steps = int(cfg["schedule"]["scheduler_total_steps"])
    if scheduler_total_steps != 12000:
        raise RuntimeError("audit expects the frozen 12k scheduler")
    if TOTAL_AUDIT_STEPS >= int(cfg["schedule"]["warmup_steps"]):
        raise RuntimeError("audit step count unexpectedly reaches warmup boundary")

    OUT.mkdir(parents=True, exist_ok=True)
    if TMP.exists():
        TMP.unlink()

    cache = preload_train_only(cfg, train_ids)
    pretrain = Path(cfg["pretrain"])
    signature = {
        "audit": "REBUILD_V1 resume exactness",
        "scheduler_total_steps": scheduler_total_steps,
        "split_step": SPLIT_STEP,
        "seed": int(cfg["seed"]),
    }

    print("\n" + "=" * 100)
    print("REFERENCE: uninterrupted 40-step trajectory")
    print("=" * 100)
    r02.set_seed(int(cfg["seed"]))
    ref_net, _ = r02.build_model(cfg, pretrain, resume_state=None)
    ref_opt = r02.build_optimizer(ref_net, cfg)
    ref_losses = train_range(
        ref_net, ref_opt, cache, train_ids, cfg,
        1, TOTAL_AUDIT_STEPS, scheduler_total_steps,
    )
    ref_model_digest = digest(ref_net.state_dict())
    ref_optimizer_digest = digest(ref_opt.state_dict())
    release(ref_net, ref_opt)

    print("\n" + "=" * 100)
    print("SPLIT: 20 steps -> torch.save/load -> restore RNG -> 20 steps")
    print("=" * 100)
    r02.set_seed(int(cfg["seed"]))
    split_net, _ = r02.build_model(cfg, pretrain, resume_state=None)
    split_opt = r02.build_optimizer(split_net, cfg)
    split_losses_a = train_range(
        split_net, split_opt, cache, train_ids, cfg,
        1, SPLIT_STEP, scheduler_total_steps,
    )

    r02.save_state(
        TMP, split_net, split_opt, SPLIT_STEP,
        best=None, signature=signature,
    )
    release(split_net, split_opt)

    state = torch.load(TMP, map_location="cpu")
    if state.get("signature") != signature:
        raise RuntimeError("saved audit signature mismatch")

    split_net, _ = r02.build_model(cfg, pretrain, resume_state=state)
    split_opt = r02.build_optimizer(split_net, cfg)
    split_opt.load_state_dict(state["optimizer"])
    r02.restore_rng(state)

    split_losses_b = train_range(
        split_net, split_opt, cache, train_ids, cfg,
        SPLIT_STEP + 1, TOTAL_AUDIT_STEPS, scheduler_total_steps,
    )
    split_losses = split_losses_a + split_losses_b
    split_model_digest = digest(split_net.state_dict())
    split_optimizer_digest = digest(split_opt.state_dict())

    loss_exact = ref_losses == split_losses
    model_exact = ref_model_digest == split_model_digest
    optimizer_exact = ref_optimizer_digest == split_optimizer_digest
    max_loss_diff = max(abs(a - b) for a, b in zip(ref_losses, split_losses))

    result = {
        "protocol": "uninterrupted 40 steps vs 20 + save/load/RNG restore + 20",
        "scheduler_total_steps": scheduler_total_steps,
        "split_step": SPLIT_STEP,
        "total_audit_steps": TOTAL_AUDIT_STEPS,
        "loss_exact": loss_exact,
        "max_abs_loss_diff": max_loss_diff,
        "model_state_sha256_reference": ref_model_digest,
        "model_state_sha256_resumed": split_model_digest,
        "model_state_exact": model_exact,
        "optimizer_state_sha256_reference": ref_optimizer_digest,
        "optimizer_state_sha256_resumed": split_optimizer_digest,
        "optimizer_state_exact": optimizer_exact,
        "pass": bool(loss_exact and model_exact and optimizer_exact),
        "temporary_state_removed": True,
        "reference_losses": ref_losses,
        "resumed_losses": split_losses,
    }

    with open(OUT / "result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    if TMP.exists():
        TMP.unlink()

    print("\n" + "=" * 100)
    print("RESUME EXACTNESS RESULT")
    print("loss exact      :", loss_exact)
    print("max loss diff   :", max_loss_diff)
    print("model exact     :", model_exact)
    print("optimizer exact :", optimizer_exact)
    print("PASS            :", result["pass"])
    print("output          :", OUT / "result.json")
    print("temporary 2.3G-ish resume state removed:", not TMP.exists())
    print("=" * 100)

    release(split_net, split_opt)
    if not result["pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
