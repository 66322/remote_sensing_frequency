"""R: matched, public-initialized trainable representation comparison."""
import gc
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

from phase3_combined_plan import jobs, read, digest
from phase3_stage_control import receipt, run as run_stage


def _sources(m2):
    from phase3_j_runtime import _sources as verify
    return verify(m2)


def _models(m2, job):
    import torch
    from phase3_m2_runtime import make_model
    from phase3_r_joint import JointHead
    c = _sources(m2)
    base_job = dict(seed=job["seed"], fold=job["fold"], role="rgb_reference",
                    id="public_initialization_only")
    rgb = make_model(m2, dict(base_job, modality="rgb"), False)
    dsm = make_model(m2, dict(base_job, modality="dsm", role="dsm_student"), False)
    # The auxiliary pair shares head initialization; no arm-dependent stream.
    head_group = "conditional_joint" if job["arm"].startswith("conditional") else job["arm"]
    torch.manual_seed(c.key("R-head", job["fold"], job["seed"], head_group) % (2**63-1))
    head = JointHead(job["arm"]).cuda()
    return rgb, dsm, head


def _model_digest(modules):
    h = hashlib.sha256()
    for role, model in modules.items():
        for name, p in sorted(model.state_dict().items()):
            h.update((role + name).encode())
            h.update(p.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def train_job(base, m2, job, uuid):
    import torch
    from torch.nn import functional as F
    from phase3_m2_data import Crops
    from d24_data import PrefetchedBatches
    from phase3_r_joint import forward_joint
    from phase3_j_runtime import _evaluate

    c = _sources(m2)
    base, m2 = Path(base), Path(m2)
    folder = base / "jobs" / job["id"]
    folder.mkdir(parents=True, exist_ok=False)
    rgb, dsm, head = _models(m2, job)
    modules = {"rgb": rgb, "dsm": dsm, "head": head}
    initial = _model_digest(modules)
    fold_data = read(m2 / "folds.json")["folds"][job["fold"]]
    stream_job = dict(id=job["id"], arm="D0", modality="dsm", role="dsm_student",
                      fold=job["fold"], seed=job["seed"], train=fold_data["train"])
    stream = PrefetchedBatches(Crops(stream_job, read(m2 / "folds.json"), updates=32000),
                               16, min(8, c.resources()["crop_workers"]), 3, True)
    encoder = [p for model in (rgb,dsm) for name,p in model.named_parameters()
               if name.startswith("encoder.") and p.requires_grad]
    decoder = [p for model in (rgb,dsm) for name,p in model.named_parameters()
               if not name.startswith("encoder.") and p.requires_grad]
    decoder += [p for p in head.parameters() if p.requires_grad]
    params = encoder + decoder
    optimizer = torch.optim.AdamW([
        {"params":encoder,"base_lr":2e-5,"lr":2e-5},
        {"params":decoder,"base_lr":2e-4,"lr":2e-4}],weight_decay=.01)
    receipt(folder / "parameters.json", {
        "job": job, "combined_execution_commit": read(base/"registration.json")["execution_commit"],
        "m2_source": str(m2), "m2_binding": c.binding(m2),
        "initial_state_sha256": initial, "initialization": "public DINO only; no M2 fine-tune",
        "train_tiles": fold_data["train"], "heldout_tiles": fold_data["evaluation"],
        "auxiliary_DSM_CE": .5 if job["arm"] == "conditional_joint_aux" else 0,
        "primary_DSM_logit_coefficient": .1,
        "batch": 16, "microbatch": 4, "updates": 32000, "gpu_uuid": uuid,
        "trainable_parameters": sum(p.numel() for p in params),
    })
    start = time.monotonic()
    connected = set()
    with (folder / "trajectory.jsonl").open("x") as log, \
         (folder / "batch_hashes.jsonl").open("x") as hashes:
        for step, batch in enumerate(stream, 1):
            for m in modules.values():
                m.train()
            optimizer.zero_grad(set_to_none=True)
            factor = (.1 + .9 * step / 200 if step <= 200 else
                      (32000 - step) / (32000 - 200))
            for group in optimizer.param_groups:
                group["lr"] = group["base_lr"] * factor
            losses = []
            for start_at in range(0, 16, 4):
                x = batch["rgb"][start_at:start_at+4].cuda(non_blocking=True)
                z = batch["dsm"][start_at:start_at+4].cuda(non_blocking=True)
                y = batch["gt"][start_at:start_at+4].cuda(non_blocking=True)
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    low, dl = forward_joint(rgb, dsm, head, x, z)
                    label = F.interpolate(y[:, None].float(), low.shape[-2:], mode="nearest")[:, 0].long()
                    primary = F.cross_entropy(low.float(), label, ignore_index=255)
                    auxiliary = F.cross_entropy(dl.float(), label, ignore_index=255)
                    loss = primary + (.5 * auxiliary if job["arm"] == "conditional_joint_aux" else 0)
                if not bool(torch.isfinite(loss)):
                    raise RuntimeError("nonfinite R loss")
                (loss / 4).backward()
                losses.append(float(loss.detach()))
                del x, z, y, low, dl, label, primary, auxiliary, loss
            torch.nn.utils.clip_grad_norm_(params, 5, error_if_nonfinite=True)
            if step == 1:
                for role, model in modules.items():
                    if not any(p.grad is not None and bool(torch.isfinite(p.grad).all())
                               and bool((p.grad != 0).any()) for p in model.parameters()):
                        raise RuntimeError("R disconnected " + role)
                    connected.add(role)
            optimizer.step()
            hashes.write(json.dumps({"step": step, "sha256": hashlib.sha256(
                "|".join(batch["token"]).encode()).hexdigest()}) + "\n")
            if step == 1 or step % 20 == 0:
                row = {"step": step, "loss": float(np.mean(losses)),
                       "lr": [g["lr"] for g in optimizer.param_groups],
                       "elapsed_seconds": time.monotonic()-start}
                log.write(json.dumps(row) + "\n")
                log.flush(); hashes.flush()
                receipt(folder / "progress.json", row)
            if step in (8000, 16000, 24000):
                receipt(folder / f"age_{step}.json", {"step": step, "observed_at": c.now(),
                          "batch_stream_sha256": digest(folder / "batch_hashes.jsonl")})
    if connected != set(modules):
        raise RuntimeError("R gradient audit incomplete")
    endpoint = folder / "endpoint.pth"
    torch.save({"job": job, "step": 32000, "m2_binding": c.binding(m2),
                "models": {name: model.state_dict() for name, model in modules.items()}}, endpoint)
    receipt(folder / "training_complete.json", {
        "job": job, "updates": 32000, "initial_state_sha256": initial,
        "batch_stream_sha256": digest(folder / "batch_hashes.jsonl"),
        "endpoint_sha256": digest(endpoint), "gpu_uuid": uuid,
        "gradient_paths_checked": sorted(connected), "observed_at": c.now(),
    })
    for model in modules.values():
        model.eval()
    # The J evaluation routine reads frozen M2 outer-held4 only. At R evaluation
    # time the jointly trained modules are put in no-grad mode by its tile stitch.
    _evaluate(base, m2, job, c, head, {"rgb": rgb, "dsm": dsm})
    receipt(folder / "complete.json", {
        **read(folder / "training_complete.json"),
        "metrics_sha256": digest(folder / "metrics.json"),
        "automatic_retry": False, "m2_binding": c.binding(m2),
    })
    del optimizer, modules, rgb, dsm, head
    gc.collect(); torch.cuda.empty_cache()


def finalize(base, m2):
    from phase3_j_runtime import _metric
    base, m2 = Path(base), Path(m2)
    all_rows = []
    for job in jobs("R"):
        folder = base / "jobs" / job["id"]
        done = read(folder / "complete.json")
        if done["updates"] != 32000 or done["endpoint_sha256"] != digest(folder / "endpoint.pth"):
            raise RuntimeError("R endpoint mismatch " + job["id"])
        if done["metrics_sha256"] != digest(folder / "metrics.json"):
            raise RuntimeError("R metrics mismatch " + job["id"])
        all_rows.extend(read(folder / "metrics.json")["rows"])
    if len(all_rows) != 3*2*4*3*4:
        raise RuntimeError("R outer-held4 coverage mismatch")
    grouped = {}
    for row in all_rows:
        key = (row["arm"], row["fold"], row["seed"], row["condition"], row["region"])
        grouped.setdefault(key, np.zeros((6, 6), np.int64))
        grouped[key] += np.asarray(row["nb_cm"], np.int64)
    metrics = [dict(arm=k[0], fold=k[1], seed=k[2], condition=k[3], region=k[4],
                    miou_fg5_full=_metric(v), cm=v.tolist()) for k, v in sorted(grouped.items())]
    lookup={(m["arm"],m["fold"],m["seed"],m["condition"],m["region"]):m["miou_fg5_full"]
            for m in metrics}
    comparisons={}
    for left,right in (("conditional_joint","concat_joint"),
                       ("conditional_joint_aux","conditional_joint")):
        values=[]
        for fold in ("F0","F1","F2"):
            for seed in (42,17):
                a=lookup[(left,fold,seed,"rgb_down4","all")]
                b=lookup[(right,fold,seed,"rgb_down4","all")]
                values.append(None if a is None or b is None else a-b)
        comparisons[left+"_minus_"+right]={
            "six_paired_blocks_pp":values,
            "mean_pp":None if any(x is None for x in values) else float(np.mean(values)),
            "positive_blocks":sum(x is not None and x>0 for x in values)}
    out = base / "publication/R"
    out.mkdir(parents=True, exist_ok=True)
    receipt(out / "metrics.json", {"rows": metrics,"paired_comparisons":comparisons})
    receipt(out / "summary.json", {
        "status": "COMPLETE_SERVER_CHECKED", "jobs": 18, "updates": 576000,
        "per_tile_rows": len(all_rows), "m2_binding": _sources(m2).binding(m2),
        "interpretation": "development representation comparison; no automatic claim or test release",
    })


def run(base, m2):
    c = _sources(m2)
    from phase3_m2_data import prepare
    if not read(Path(base) / "publication/J/summary.json")["status"] == "COMPLETE_SERVER_CHECKED":
        raise RuntimeError("J integrity not complete")
    try:
        run_stage("R", base, m2, finalize, prepare=lambda: prepare(m2))
    finally:
        c.DATA.clear()
        gc.collect()
