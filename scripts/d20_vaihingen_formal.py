"""Matched Vaihingen seed42 development training and full-tile evaluation."""

import argparse
import json
import os
from pathlib import Path
import random
import time

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
os.environ.setdefault("XFORMERS_DISABLED", "1")
import numpy as np
import torch

import d18_d19_night as d18
import d16_d17_portfolio as old
import train_rebuild_v1_r02_budget_pilot as r02
from train_rebuild_v1_d16_d17 import sample, save
from d20_vaihingen_smoke_arm import load_tile

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rebuild_v1/d20_vaihingen_formal_seed42_20260928.json"
RECORD = ROOT / "records/rebuild_v1_d20_vaihingen_seed42_20260928"


def setup(arm):
    cfg = d18.read(CONFIG)
    if cfg["arms"] != ["P0", "P1", "P2"] or arm not in cfg["arms"]:
        raise RuntimeError("arm mismatch")
    if cfg["seeds"] != [42] or cfg["train_steps"] != 8000:
        raise RuntimeError("seed/budget mismatch")
    if cfg["micro_batch"] * cfg["accum_steps"] != 16:
        raise RuntimeError("effective batch mismatch")
    if cfg["test6_loaded"] is not False or cfg["independent_final_loaded"] is not False:
        raise RuntimeError("sealed data policy mismatch")
    if set(cfg["train_ids"]) & (set(cfg["development_ids"]) | set(cfg["excluded_historical_eval_ids"])):
        raise RuntimeError("split overlap")
    if set(cfg["development_ids"]) & set(cfg["excluded_historical_eval_ids"]):
        raise RuntimeError("development/history overlap")
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("exactly one visible CUDA GPU required")
    manifest = RECORD / "input_manifest.json"
    if not manifest.is_file():
        raise RuntimeError("input manifest missing; run queue preflight")
    signature = dict(
        arm=arm, seed=42, config_sha256=d18.sha(CONFIG),
        source_sha256=d18.sha(Path(__file__)),
        loader_sha256=d18.sha(ROOT / "scripts/d20_vaihingen_smoke_arm.py"),
        input_manifest_sha256=d18.sha(manifest),
        d18_binding=d18.binding(arm, False),
        train_ids=cfg["train_ids"], development_ids=cfg["development_ids"],
        test6_loaded=False, independent_final_loaded=False)
    return cfg, signature


def run_dir(arm):
    return ROOT / "runs/rebuild_v1" / f"D20_VAI_{arm}_seed42_8000_20260928"


def safe_metrics(cm):
    return {key: None if isinstance(value, float) and not np.isfinite(value) else value
            for key, value in r02.metrics_from_cm(cm).items()}


def train(arm):
    cfg, signature = setup(arm)
    run = run_dir(arm)
    run.mkdir(parents=True, exist_ok=True)
    ck = run / "last_train_state.pth"
    summary_path = run / "summary.json"
    if summary_path.is_file():
        result = d18.read(summary_path)
        if result["signature"] != signature or result["global_step"] != cfg["train_steps"] or d18.sha(ck) != result["checkpoint_sha256"]:
            raise RuntimeError("completed training binding/checkpoint changed")
        print("TRAIN REUSED", arm, flush=True)
        return
    r02.set_seed(42)
    state = torch.load(ck, map_location="cpu", weights_only=False) if ck.is_file() else None
    if state is not None and state["signature"] != signature:
        raise RuntimeError("checkpoint resume binding mismatch")
    base = d18.read(d18.base_config())
    parent = d18.read(d18.CONFIG)
    model = d18.build(arm, base, r02.DEVICE, state)
    optcfg = dict(base, optimizer=parent["pretrained_optimizer"], schedule=parent["schedule"])
    optimizer = r02.build_optimizer(model, optcfg)
    if state is not None:
        optimizer.load_state_dict(state["optimizer"])
        old.restore_rng(state)
    else:
        r02.set_seed(42)
    start = int(state["global_step"]) if state else 0
    if start >= cfg["train_steps"]:
        print("TRAIN CHECKPOINT COMPLETE; FINALIZING", arm, flush=True)
    counts = state["treatment_counts"] if state else {key: 0 for key in parent["treatment_probabilities"]}
    data_root = Path(cfg["data_root"]).resolve()
    data_root.relative_to(Path("/home/jovyan/zzx").resolve())
    loading_started = time.monotonic()
    cache = {str(tile): load_tile(data_root, tile, cfg["training_label_directory"])
             for tile in cfg["train_ids"]}
    loading_seconds = time.monotonic() - loading_started
    sampler = dict(base, patch=cfg["patch"], micro_batch=cfg["micro_batch"])
    names = list(parent["treatment_probabilities"])
    weights = list(parent["treatment_probabilities"].values())
    model.train()
    started = time.monotonic()
    for step in range(start + 1, cfg["train_steps"] + 1):
        optimizer.zero_grad(set_to_none=True)
        r02.set_lr(optimizer, optcfg, step, cfg["train_steps"])
        total = 0.0
        for micro in range(cfg["accum_steps"]):
            key = 42000000 + step * 100 + micro
            op, ds, gt, _ = sample(cache, list(cache), sampler, key)
            kinds = random.Random(key + 1).choices(names, weights=weights, k=len(op))
            for kind in kinds:
                counts[kind] += 1
            op2, aux2, available = d18.training_transform(
                op, ds, arm, kinds, key, parent["structured_mask"])
            aux = op.mean(1) if arm == "P1" else ds
            clean = model(op, aux)
            loss = .5 * old.deterministic_ce(clean, gt)
            if not bool(torch.isfinite(loss)):
                raise RuntimeError(f"nonfinite clean loss at {step}")
            total += float(loss.detach()) / cfg["accum_steps"]
            (loss / cfg["accum_steps"]).backward()
            del loss, clean
            damaged = model(op2, aux2)
            loss = .5 * old.deterministic_ce(damaged, gt)
            if not bool(torch.isfinite(loss)):
                raise RuntimeError(f"nonfinite damaged loss at {step}")
            total += float(loss.detach()) / cfg["accum_steps"]
            (loss / cfg["accum_steps"]).backward()
            del loss, damaged, op, ds, gt, op2, aux2, aux, available
        torch.nn.utils.clip_grad_norm_(model.parameters(), float("inf"), error_if_nonfinite=True)
        optimizer.step()
        if step == 1 or step % 100 == 0 or step == cfg["train_steps"]:
            torch.cuda.synchronize()
            elapsed = time.monotonic() - started
            sec_per_step = elapsed / (step - start)
            remaining = (cfg["train_steps"] - step) * sec_per_step
            print(f"TRAIN {arm} step={step}/{cfg['train_steps']} loss={total:.5f} elapsed={elapsed:.1f}s approx_remaining={remaining/60:.1f}min", flush=True)
            d18.write(run / "progress.json", dict(arm=arm, step=step, total_steps=cfg["train_steps"],
                seconds_this_session=round(elapsed, 2), approx_remaining_minutes=round(remaining/60, 1)))
        if step % cfg["checkpoint_every"] == 0 or step == cfg["train_steps"]:
            save(ck, model, None, optimizer, step, signature, counts)
    probe_op, probe_ds, _, _ = sample(cache, list(cache), dict(sampler, micro_batch=1), 42999999)
    probe_aux = probe_op.mean(1) if arm == "P1" else probe_ds
    model.eval()
    with torch.no_grad():
        prediction = model(probe_op, probe_aux).argmax(1).cpu()
    probe = run / "clean_probe.pth"
    temporary = probe.with_name(probe.name + ".tmp")
    torch.save(dict(rgb=probe_op.cpu(), aux=probe_aux.cpu(), pred=prediction), temporary)
    os.replace(temporary, probe)
    d18.write(summary_path, dict(arm=arm, seed=42, signature=signature, global_step=cfg["train_steps"],
        checkpoint_sha256=d18.sha(ck), clean_probe_sha256=d18.sha(probe),
        treatment_counts=counts, train_tiles=cfg["train_ids"],
        seconds_this_session=round(time.monotonic() - started, 2),
        data_load_seconds=round(loading_seconds, 2),
        trainable_parameters=sum(p.numel() for p in model.parameters() if p.requires_grad),
        total_parameters=sum(p.numel() for p in model.parameters()),
        checkpoint_selection="fixed_final_step", development_labels_loaded=False,
        test6_loaded=False, independent_final_loaded=False))
    print("TRAIN COMPLETE", arm, flush=True)


def evaluate(arm):
    cfg, signature = setup(arm)
    run = run_dir(arm)
    train_result = d18.read(run / "summary.json")
    if train_result["signature"] != signature or train_result["global_step"] != cfg["train_steps"]:
        raise RuntimeError("training summary binding/budget mismatch")
    ck = run / "last_train_state.pth"
    if d18.sha(ck) != train_result["checkpoint_sha256"]:
        raise RuntimeError("checkpoint hash mismatch")
    output = RECORD / arm
    output.mkdir(parents=True, exist_ok=True)
    eval_signature = dict(training=signature, checkpoint_sha256=train_result["checkpoint_sha256"],
                          evaluation_source_sha256=d18.sha(Path(__file__)))
    summary_path = output / "summary.json"
    if summary_path.is_file():
        previous = d18.read(summary_path)
        if previous["signature"] != eval_signature:
            raise RuntimeError("existing evaluation binding mismatch")
        missing = [(condition, tile) for condition in cfg["evaluation_conditions"]
                   for tile in cfg["development_ids"]
                   if not (output / condition / f"tile_{tile}.json").is_file() or
                   not (output / condition / f"tile_{tile}.npy").is_file()]
        if not missing:
            print("EVAL REUSED", arm, flush=True)
            return
        print("EVAL REPAIR MISSING OUTPUTS", arm, len(missing), flush=True)
    r02.set_seed(42)
    base = d18.read(d18.base_config())
    state = torch.load(ck, map_location="cpu", weights_only=False)
    if state["signature"] != signature:
        raise RuntimeError("saved state binding mismatch")
    model = d18.build(arm, base, r02.DEVICE, state)
    model.eval()
    probe = torch.load(run / "clean_probe.pth", map_location="cpu", weights_only=False)
    if d18.sha(run / "clean_probe.pth") != train_result["clean_probe_sha256"]:
        raise RuntimeError("clean probe hash mismatch")
    with torch.no_grad():
        reproduction = model(probe["rgb"].to(r02.DEVICE), probe["aux"].to(r02.DEVICE)).argmax(1).cpu()
    if not torch.equal(reproduction, probe["pred"]):
        raise RuntimeError("checkpoint reload failed to reproduce clean probe")
    del probe, reproduction
    data_root = Path(cfg["data_root"]).resolve()
    conditions = cfg["evaluation_conditions"]
    began = time.monotonic()
    done = 0
    for tile in cfg["development_ids"]:
        existing = []
        for condition in conditions:
            detail = output / condition / f"tile_{tile}.json"
            prediction = output / condition / f"tile_{tile}.npy"
            existing.append(detail.is_file() and prediction.is_file())
        if all(existing):
            for condition in conditions:
                row = d18.read(output / condition / f"tile_{tile}.json")
                if row["signature"] != eval_signature or row["prediction_sha256"] != d18.sha(output / condition / f"tile_{tile}.npy"):
                    raise RuntimeError(f"partial evaluation binding changed: {condition} {tile}")
            done += len(conditions)
            continue
        optical, dsm, label = load_tile(data_root, tile, cfg["development_label_directory"])
        op = torch.from_numpy(np.ascontiguousarray(optical.transpose(2, 0, 1)))[None]
        ds = torch.from_numpy(np.ascontiguousarray(dsm))[None]
        for condition in conditions:
            detail_dir = output / condition
            detail_dir.mkdir(parents=True, exist_ok=True)
            detail = detail_dir / f"tile_{tile}.json"
            prediction_path = detail_dir / f"tile_{tile}.npy"
            if detail.is_file() and prediction_path.is_file():
                row = d18.read(detail)
                if row["signature"] != eval_signature or row["prediction_sha256"] != d18.sha(prediction_path):
                    raise RuntimeError(f"partial evaluation binding changed: {condition} {tile}")
                done += 1
                continue
            treated, aux, _ = d18.transform(op, ds, arm, [condition],
                torch.Generator().manual_seed(42000000 + tile * 100 + conditions.index(condition)))
            top = np.ascontiguousarray(treated[0].permute(1, 2, 0).numpy())
            secondary = np.ascontiguousarray(aux[0].numpy())
            predicted = r02.infer_tile(model, top, secondary, cfg["patch"],
                                       cfg["evaluation_stride"], cfg["evaluation_batch"])
            cm = np.zeros((6, 6), dtype=np.int64)
            r02.update_cm(cm, label, predicted)
            if int(cm.sum()) != int(label.size):
                raise RuntimeError(f"invalid full-label pixels in development tile {tile}")
            temporary = prediction_path.with_suffix(".tmp.npy")
            np.save(temporary, predicted)
            os.replace(temporary, prediction_path)
            d18.write(detail, dict(signature=eval_signature, arm=arm, condition=condition,
                tile=tile, cm=cm.tolist(), metrics=safe_metrics(cm),
                prediction_sha256=d18.sha(prediction_path), valid_pixels=int(cm.sum())))
            done += 1
            print(f"EVAL {arm} {done}/{len(cfg['development_ids'])*len(conditions)} {condition} tile={tile}", flush=True)
            d18.write(output / "progress.json", dict(arm=arm, completed=done,
                total=len(cfg["development_ids"])*len(conditions), seconds=round(time.monotonic()-began, 2)))
    results = {}
    for condition in conditions:
        pooled = np.zeros((6, 6), dtype=np.int64)
        tiles = {}
        for tile in cfg["development_ids"]:
            row = d18.read(output / condition / f"tile_{tile}.json")
            if row["signature"] != eval_signature:
                raise RuntimeError("tile summary binding changed")
            pooled += np.asarray(row["cm"], dtype=np.int64)
            tiles[str(tile)] = dict(cm=row["cm"], metrics=row["metrics"],
                                    valid_pixels=row["valid_pixels"], prediction_sha256=row["prediction_sha256"])
        results[condition] = dict(pooled_cm=pooled.tolist(), pooled_metrics=safe_metrics(pooled), tiles=tiles)
    if arm == "P0":
        for condition in conditions:
            if condition.startswith("aux_") and results[condition]["pooled_cm"] != results["clean"]["pooled_cm"]:
                raise RuntimeError("P0 auxiliary invariance failed")
    d18.write(summary_path, dict(arm=arm, seed=42, signature=eval_signature,
        conditions=results, development_ids=cfg["development_ids"],
        development_labels_loaded=True, test6_loaded=False, independent_final_loaded=False,
        checkpoint_selection="fixed_final_step", trainable_parameters=train_result["trainable_parameters"],
        evaluation_seconds=round(time.monotonic()-began, 2)))
    print("EVAL COMPLETE", arm, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("train", "eval"))
    ap.add_argument("--arm", choices=("P0", "P1", "P2"), required=True)
    args = ap.parse_args()
    if args.action == "train":
        train(args.arm)
    else:
        evaluate(args.arm)


if __name__ == "__main__":
    main()
