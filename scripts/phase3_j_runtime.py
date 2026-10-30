"""J frozen-expert diagnostics; runs after the original M2 checks, on GPU 0/1."""
from __future__ import annotations

import csv
import gc
import hashlib
import json
import multiprocessing as mp
import os
import queue
import sys
import time
import traceback
from pathlib import Path

import numpy as np

from phase3_combined_plan import FOLDS, J_ARMS, SEEDS, digest, jobs, read


def _atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp." + str(os.getpid()))
    tmp.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _sources(m2):
    code = Path(m2) / "code"
    for entry in (str(code), str(code / "scripts")):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    head_module = str(Path(__file__).resolve().parents[1] / "model")
    if head_module not in sys.path:
        sys.path.insert(0, head_module)
    import phase3_m2_common as original
    original.verify(m2)
    summary = read(Path(m2) / "publication/summary.json")
    gates = read(Path(m2) / "publication/gates.json")
    if summary["status"] != "COMPLETE_SERVER_CHECKED" or not gates["status"]["G0"]:
        raise RuntimeError("M2 core scientific input integrity has not passed")
    return original


def _job_sources(m2, job, c):
    manifest = {j["id"]: j for j in c.jobs(read(Path(m2) / "folds.json"))}
    stem = f"{job['fold']}_s{job['seed']}_"
    result = {"rgb": manifest[stem + "R"], "dsm": manifest[stem + "D0"]}
    if job["arm"] == "J4":
        other = SEEDS[(SEEDS.index(job["seed"]) + 1) % len(SEEDS)]
        result["second_rgb"] = manifest[f"{job['fold']}_s{other}_R"]
    return result


def _model_initial_digest(model):
    h = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        h.update(name.encode())
        h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def _head_seed(c, job):
    group = "J56" if job["arm"] in ("J5", "J6") else job["arm"]
    return c.key("phase3-J", job["fold"], job["seed"], group) % (2**63 - 1)


def _initialize_experts(m2, job, c):
    from phase3_m2_runtime import make_model
    source = _job_sources(m2, job, c)
    result = {}
    for role, spec in source.items():
        result[role] = make_model(m2, spec, True).eval().requires_grad_(False)
    return source, result


def _head(job, c):
    import torch
    from phase3_j_heads import FrozenExpertHead
    torch.manual_seed(_head_seed(c, job))
    return FrozenExpertHead(job["arm"]).cuda()


def _low(head, experts, rgb, dsm):
    from phase3_j_heads import expert_grids
    grids = expert_grids(experts["rgb"], experts["dsm"], rgb, dsm,
                         experts.get("second_rgb"))
    return head(*grids[:4], second_rgb=grids[4]), grids[2], grids[3]


def _train(base, m2, job, c, uuid):
    import torch
    from torch.nn import functional as F
    from d24_data import PrefetchedBatches
    from phase3_m2_data import Crops

    base = Path(base)
    folder = base / "jobs" / job["id"]
    folder.mkdir(parents=True, exist_ok=False)
    source, experts = _initialize_experts(m2, job, c)
    head = _head(job, c)
    initial = _model_initial_digest(head)
    train_tiles = read(Path(m2) / "folds.json")["folds"][job["fold"]]["train"]
    stream_job = dict(role="dsm_student", arm="D0", fold=job["fold"], seed=job["seed"],
                      train=train_tiles, id=job["id"])
    batches = PrefetchedBatches(Crops(stream_job, read(Path(m2) / "folds.json"), updates=8000),
                                16, min(8, c.resources()["crop_workers"]), 3, True)
    optimizer = torch.optim.AdamW(head.parameters(), lr=2e-4, weight_decay=.01)
    _atomic(folder / "parameters.json", {
        "job": job, "combined_execution_commit": read(base/"registration.json")["execution_commit"],
        "m2_source": str(m2), "m2_binding": c.binding(m2),
        "source_jobs": {k: v["id"] for k, v in source.items()},
        "source_endpoints": {k: read(Path(m2) / "jobs" / v["id"] / "complete.json")["checkpoint_sha256"]
                             for k, v in source.items()},
        "heldout_tiles": read(Path(m2) / "folds.json")["folds"][job["fold"]]["evaluation"],
        "train_tiles": train_tiles, "initial_state_sha256": initial,
        "trainable_parameters": sum(p.numel() for p in head.parameters()),
        "physical_gpu_uuid": uuid, "budget": 8000, "batch": 16,
        "training_expert_predictions": "in-sample on train8; evaluation exclusively outer-held4",
    })
    started = time.monotonic()
    with (folder / "trajectory.jsonl").open("x", encoding="utf-8") as log, \
         (folder / "batch_hashes.jsonl").open("x", encoding="utf-8") as hashes:
        for step, batch in enumerate(batches, 1):
            head.train()
            for group in optimizer.param_groups:
                group["lr"] = 2e-4 * (.1 + .9 * step / 100 if step <= 100 else
                                      (8000 - step) / (8000 - 100))
            rgb = batch["rgb"].cuda(non_blocking=True)
            dsm = batch["dsm"].cuda(non_blocking=True)
            target = batch["gt"].cuda(non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                low, _, _ = _low(head, experts, rgb, dsm)
                score = F.interpolate(low.float(), target.shape[-2:], mode="nearest")
                loss = F.cross_entropy(score, target, ignore_index=255)
            if not bool(torch.isfinite(loss)):
                raise RuntimeError("nonfinite J loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(head.parameters(), 5.0, error_if_nonfinite=True)
            optimizer.step()
            token = hashlib.sha256("|".join(batch["token"]).encode()).hexdigest()
            hashes.write(json.dumps({"step": step, "sample_stream_sha256": token}) + "\n")
            if step == 1 or step % 20 == 0:
                value = {"step": step, "loss": float(loss.detach()),
                         "elapsed_seconds": time.monotonic() - started}
                log.write(json.dumps(value) + "\n")
                log.flush()
                hashes.flush()
                _atomic(folder / "progress.json", value)
            if step in (2000, 4000, 6000):
                _atomic(folder / f"age_{step}.json", {"step": step, "observed_at": c.now(),
                                                      "batch_stream_sha256": digest(folder / "batch_hashes.jsonl")})
    torch.save({"job": job, "step": 8000, "state": head.state_dict(),
                "m2_binding": c.binding(m2)}, folder / "endpoint.pth")
    _atomic(folder / "training_complete.json", {
        "job": job, "updates": 8000, "initial_state_sha256": initial,
        "batch_stream_sha256": digest(folder / "batch_hashes.jsonl"),
        "endpoint_sha256": digest(folder / "endpoint.pth"),
        "observed_at": c.now(), "gpu_uuid": uuid,
    })
    _evaluate(base, m2, job, c, head.eval(), experts)
    _atomic(folder / "complete.json", {
        **read(folder / "training_complete.json"),
        "metrics_sha256": digest(folder / "metrics.json"),
        "m2_binding": c.binding(m2), "automatic_retry": False,
    })
    del optimizer, head, experts
    gc.collect()
    torch.cuda.empty_cache()


def _predict_tile(head, experts, item, rgb, dsm, baseline=False):
    import torch
    from torch.nn import functional as F
    h, w = rgb.shape[:2]
    if h % 4 or w % 4 or min(h, w) < 1024:
        raise RuntimeError("J outer tile geometry differs from M2 protocol")
    positions = lambda n: sorted(set(list(range(0, n - 511, 256)) + [n - 512]))
    coords = [(y, x) for y in positions(h) for x in positions(w)]
    score = torch.zeros((6, h, w), device="cuda", dtype=torch.float32)
    rscore = torch.zeros_like(score) if baseline else None
    dscore = torch.zeros_like(score) if baseline else None
    coverage = torch.zeros((h, w), device="cuda", dtype=torch.uint8)
    with torch.no_grad():
        for start in range(0, len(coords), 8):
            use = coords[start:start + 8]
            r = torch.from_numpy(np.stack([rgb[y:y+512, x:x+512].transpose(2, 0, 1)
                                            for y, x in use])).cuda()
            d = torch.from_numpy(np.stack([dsm[y:y+512, x:x+512]
                                            for y, x in use])).cuda()
            low, rl, dl = _low(head, experts, r, d)
            for i, (y, x) in enumerate(use):
                score[:, y:y+512, x:x+512] += F.interpolate(
                    low[i:i+1].float(), size=(512, 512), mode="nearest")[0]
                if baseline:
                    rscore[:, y:y+512, x:x+512] += F.interpolate(
                        rl[i:i+1].float(), size=(512, 512), mode="nearest")[0]
                    dscore[:, y:y+512, x:x+512] += F.interpolate(
                        dl[i:i+1].float(), size=(512, 512), mode="nearest")[0]
                coverage[y:y+512, x:x+512] += 1
    if not bool(coverage.all()) or not bool(torch.isfinite(score).all()):
        raise RuntimeError("J invalid inference coverage")
    prediction = score.argmax(0).cpu().numpy().astype(np.uint8)
    reference = None
    if baseline:
        blend = .9 * torch.softmax(rscore, 0) + .1 * torch.softmax(dscore, 0)
        reference = blend.argmax(0).cpu().numpy().astype(np.uint8)
    del score, rscore, dscore, coverage
    torch.cuda.empty_cache()
    return prediction, reference


def _matrix(gt, prediction, keep):
    mask = keep & (gt < 6)
    values = gt[mask].astype(np.int64) * 6 + prediction[mask].astype(np.int64)
    return np.bincount(values, minlength=36).reshape(6, 6).astype(np.int64)


def _evaluate(base, m2, job, c, head, experts):
    from phase3_m2_counts import reconstruct_masks
    from phase3_m2_runtime import damaged_rgb
    from scipy.ndimage import maximum_filter
    rows = []
    heldout = read(Path(m2) / "folds.json")["folds"][job["fold"]]["evaluation"]
    for tile in heldout:
        item = c.DATA[tile]
        h, w = item["nb"].shape
        central = np.zeros((h, w), bool)
        central[512:h-512, 512:w-512] = True
        frozen = read(Path(m2) / "mask_design" / f"{tile}_1.json")["metadata"]
        mask = reconstruct_masks(tile, 1, item, frozen)["random"]
        healthy = ~maximum_filter(mask, size=17, mode="constant", cval=0).astype(bool)
        for condition in ("clean", "rgb_down4"):
            rgb = item["rgb"] if condition == "clean" else damaged_rgb(
                item, "down4", mask, c.key(tile, "random", 1, "noise"))
            pred, reference = _predict_tile(head, experts, item, rgb, item["dsm"],
                                            baseline=job["arm"] == "J1")
            for region, keep in (("all", central),
                                 ("damaged", central & mask),
                                 ("healthy", central & healthy)):
                if condition == "clean" and region != "all":
                    continue
                row = {"tile": tile, "fold": job["fold"], "seed": job["seed"],
                       "arm": job["arm"], "condition": condition, "region": region,
                       "nb_cm": _matrix(item["nb"], pred, keep).tolist(),
                       "full_cm": _matrix(item["full"], pred, keep).tolist()}
                rows.append(row)
                if reference is not None:
                    rows.append({**row, "arm": "J0_probability_0p9_0p1",
                                 "nb_cm": _matrix(item["nb"], reference, keep).tolist(),
                                 "full_cm": _matrix(item["full"], reference, keep).tolist()})
            del pred, reference
    _atomic(Path(base) / "jobs" / job["id"] / "metrics.json", {
        "protocol": "M2 outer-held4, central512, noBoundary foreground5 main",
        "rgb_fault": "M2 structured_v0 random family realization1, 25 percent area",
        "rows": rows,
    })


def _worker(base, m2, gpu, uuid, tasks, results):
    c = _sources(m2)
    from phase3_stage_control import worker_environment
    os.environ.update(worker_environment(c, m2, base, uuid))
    import torch
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    try:
        if torch.__version__ != "2.2.2+cu121" or not torch.cuda.is_available():
            raise RuntimeError("M2 target Torch2.2.2+cu121/CUDA required")
        while True:
            job = tasks.get()
            if job is None:
                return
            try:
                _train(base, m2, job, c, uuid)
                results.put({"kind": "complete", "job": job["id"], "gpu": gpu})
            except BaseException:
                results.put({"kind": "failed", "job": job["id"], "gpu": gpu,
                             "traceback": traceback.format_exc()})
                return
    finally:
        c.DATA.clear()
        gc.collect()
        torch.cuda.empty_cache()


def _metric(cm):
    a = np.asarray(cm, dtype=np.int64)
    union = a.sum(0) + a.sum(1) - a.diagonal()
    return None if a.shape != (6, 6) or (union[:5] == 0).any() else float(
        100 * np.mean(a.diagonal()[:5] / union[:5]))


def _finalize(base, m2):
    base = Path(base)
    all_rows = []
    for job in jobs("J"):
        folder = base / "jobs" / job["id"]
        receipt = read(folder / "complete.json")
        if receipt["updates"] != 8000 or digest(folder / "endpoint.pth") != receipt["endpoint_sha256"]:
            raise RuntimeError("J endpoint receipt mismatch: " + job["id"])
        if digest(folder / "metrics.json") != receipt["metrics_sha256"]:
            raise RuntimeError("J metrics receipt mismatch: " + job["id"])
        all_rows.extend(read(folder / "metrics.json")["rows"])
    expected = 3 * 2 * 4 * (7 * 4 + 4)
    if len(all_rows) != expected:
        raise RuntimeError(f"J count coverage {len(all_rows)}/{expected}")
    # Four tile confusion matrices are pooled before mIoU. Neither pixels nor
    # mask placements are treated as independent repeats.
    grouped = {}
    for row in all_rows:
        key = (row["fold"], row["seed"], row["arm"], row["condition"], row["region"])
        grouped.setdefault(key, np.zeros((6, 6), np.int64))
        grouped[key] += np.asarray(row["nb_cm"], np.int64)
    summary = []
    for key, cm in sorted(grouped.items()):
        summary.append(dict(zip(("fold", "seed", "arm", "condition", "region"), key),
                            miou_fg5_full=_metric(cm), cm=cm.tolist()))
    lookup = {(r["fold"], r["seed"], r["arm"], r["condition"], r["region"]):
              r["miou_fg5_full"] for r in summary}
    checks = {}
    for control in ("J0_probability_0p9_0p1", "J1", "J2", "J3", "J4", "J5", "J7"):
        values = [lookup[(fold, seed, "J6", "rgb_down4", "all")] -
                  lookup[(fold, seed, control, "rgb_down4", "all")]
                  for fold in FOLDS for seed in SEEDS]
        checks["J6_minus_" + control] = dict(
            differences_pp=values, mean_pp=float(np.mean(values)),
            positive_blocks=sum(x > 0 for x in values))
    clean = {str(seed): float(np.mean([
        lookup[(fold, seed, "J6", "clean", "all")] -
        lookup[(fold, seed, "J3", "clean", "all")] for fold in FOLDS]))
        for seed in SEEDS}
    support = all(z["mean_pp"] >= .2 and z["positive_blocks"] >= 4
                  for z in checks.values()) and all(v >= -.2 for v in clean.values())
    publication = base / "publication/J"
    publication.mkdir(parents=True, exist_ok=True)
    _atomic(publication / "gates.json", {
        "integrity": True, "J6_conditional_support": support,
        "comparison": checks, "clean_minus_RGB_only_pp": clean,
        "interpretation": "preregistered development criterion, not significance or a reason to retry",
        "R_next": "R executes after J integrity regardless of J6 outcome",
    })
    _atomic(publication / "summary.json", {
        "status": "COMPLETE_SERVER_CHECKED", "jobs": 42, "updates": 336000,
        "rows": len(all_rows), "source_m2": str(m2),
        "source_m2_binding": _sources(m2).binding(m2),
        "scope": "Fit12 outer-held4 only; no legacy Val2/Test6/held4/final",
    })
    with (publication / "metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["fold", "seed", "arm", "condition",
                                                    "region", "miou_fg5_full", "cm"])
        writer.writeheader()
        writer.writerows(summary)
    _atomic(publication / "evidence_index.json", {
        "jobs": [{"id": j["id"],
                  "endpoint_sha256": read(base / "jobs" / j["id"] / "complete.json")["endpoint_sha256"],
                  "metrics_sha256": read(base / "jobs" / j["id"] / "complete.json")["metrics_sha256"]}
                 for j in jobs("J")],
        "retained": "all per-tile int64 matrices, sample stream hashes, trajectories and endpoints",
    })
    (publication / "REPORT.md").write_text(
        "# J 条件几何表征诊断\n\n"
        f"完成42/42，336000次头部更新。J6相对各强对照满足预登记开发判据：{support}。\n\n"
        "本阶段只冻结M2专家并训练头部；不能推断独立DSM分类损失对表示的因果影响。"
        "完整逐fold×seed结果见metrics.csv，负结果与端点保留服务器。\n",
        encoding="utf-8")


def run(base, m2):
    """Single-owner two-card stage. Failure preserves originals and never retries."""
    import fcntl
    base, m2 = Path(base).resolve(), Path(m2).resolve()
    if (base / "publication/J/summary.json").exists():
        if read(base / "publication/J/summary.json")["status"] == "COMPLETE_SERVER_CHECKED":
            return
        raise RuntimeError("J existing publication requires manual inspection")
    with (base / "j_stage.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        c = _sources(m2)
        from phase3_m2_data import prepare
        inventory = c.gpu_inventory()
        if not inventory["ready"]:
            raise RuntimeError("GPU0/1 occupied before J, no new job started")
        prepare(m2)
        second = c.gpu_inventory()
        if not second["ready"] or any(
            second["selected"][g][1] != inventory["selected"][g][1] for g in (0, 1)
        ):
            raise RuntimeError("GPU0/1 changed during J preparation")
        context = mp.get_context("fork")
        tasks = {g: context.Queue() for g in (0, 1)}
        results = context.Queue()
        workers = {g: context.Process(
            target=_worker, args=(str(base), str(m2), g,
                                  inventory["selected"][g][1], tasks[g], results))
            for g in (0, 1)}
        for worker in workers.values():
            worker.start()
        pending = iter(jobs("J"))
        active = {}
        completed = set()
        try:
            for gpu in (0, 1):
                task = next(pending, None)
                if task:
                    tasks[gpu].put(task)
                    active[gpu] = task["id"]
            while active:
                try:
                    result = results.get(timeout=10)
                except queue.Empty:
                    if any(worker.exitcode is not None for worker in workers.values()):
                        raise RuntimeError("J worker exited without receipt")
                    continue
                gpu, job = result["gpu"], result["job"]
                if active[gpu] != job:
                    raise RuntimeError("J out-of-order receipt")
                if result["kind"] != "complete":
                    raise RuntimeError("J job failed without retry: " + job + "\n" +
                                       result["traceback"])
                completed.add(job)
                task = next(pending, None)
                if task is None:
                    del active[gpu]
                else:
                    tasks[gpu].put(task)
                    active[gpu] = task["id"]
                _atomic(base / "j_status.json", {"status": "RUNNING", "completed": len(completed),
                                                 "active": active, "observed_at": c.now()})
            for gpu in workers:
                tasks[gpu].put(None)
            for worker in workers.values():
                worker.join()
            if any(worker.exitcode != 0 for worker in workers.values()):
                raise RuntimeError("J worker process failed")
            _finalize(base, m2)
            _atomic(base / "j_status.json", {"status": "COMPLETE_SERVER_CHECKED",
                                             "completed": 42, "observed_at": c.now()})
        except BaseException as exc:
            _atomic(base / "j_status.json", {"status": "FAILED_NO_RETRY",
                                             "error": str(exc), "observed_at": c.now()})
            for worker in workers.values():
                if worker.is_alive():
                    worker.terminate()
                worker.join()
            raise
        finally:
            c.DATA.clear()
            gc.collect()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--m2-directory", type=Path, required=True)
    args = parser.parse_args()
    run(args.directory, args.m2_directory)
