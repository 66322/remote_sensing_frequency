"""Two physical GPU workers; a failed job stops its stage without retry."""
import gc
import json
import multiprocessing as mp
import os
import queue
import time
import traceback
from pathlib import Path

from phase3_combined_plan import jobs, read


def receipt(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp." + str(os.getpid()))
    tmp.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def worker_environment(c, source, base, uuid):
    env = c.environment(source, uuid)
    base = Path(base)
    env.update(TMPDIR=str(base/"temporary"), TMP=str(base/"temporary"),
               TEMP=str(base/"temporary"), TORCH_HOME=str(base/"cache/torch"),
               XDG_CACHE_HOME=str(base/"cache"), CUDA_CACHE_PATH=str(base/"cache/cuda"),
               TRITON_CACHE_DIR=str(base/"cache/triton"),
               PYTORCH_KERNEL_CACHE_PATH=str(base/"cache/kernels"))
    return env


def _worker(stage, base, source, gpu, uuid, tasks, results):
    import sys
    local = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(local / "model"), str(Path(source) / "code"),
                    str(Path(source) / "code/scripts")]
    import phase3_m2_common as c
    os.environ.update(worker_environment(c, source, base, uuid))
    import torch
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    try:
        if torch.__version__ != "2.2.2+cu121" or not torch.cuda.is_available():
            raise RuntimeError("frozen Torch2.2.2+cu121 CUDA environment required")
        while True:
            job = tasks.get()
            if job is None:
                return
            try:
                if stage == "R":
                    from phase3_r_runtime import train_job
                else:
                    from phase3_public_runtime import train_job
                train_job(base, source, job, uuid)
                results.put((gpu, job["id"], None))
            except BaseException:
                results.put((gpu, job["id"], traceback.format_exc()))
                return
    finally:
        gc.collect()
        torch.cuda.empty_cache()


def run(stage, base, source, finalize, prepare=None):
    import fcntl
    import sys
    sys.path[:0] = [str(Path(source) / "code"), str(Path(source) / "code/scripts")]
    import phase3_m2_common as c
    base, source = Path(base).resolve(), Path(source).resolve()
    target = base / "publication" / stage / "summary.json"
    if target.exists():
        if read(target)["status"] == "COMPLETE_SERVER_CHECKED":
            return
        raise RuntimeError("existing stage publication requires manual inspection")
    with (base / (stage.lower() + "_stage.lock")).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        first = c.gpu_inventory()
        if not first["ready"]:
            raise RuntimeError("physical GPU0/1 occupied; stage has not started")
        if prepare:
            prepare()
        second = c.gpu_inventory()
        if not second["ready"] or any(second["selected"][g][1] != first["selected"][g][1]
                                           for g in (0, 1)):
            raise RuntimeError("GPU0/1 inventory changed before launch")
        ctx = mp.get_context("fork")
        tasks = {g: ctx.Queue() for g in (0, 1)}
        result = ctx.Queue()
        workers = {g: ctx.Process(target=_worker, args=(stage, str(base), str(source), g,
                                                        first["selected"][g][1], tasks[g], result))
                   for g in (0, 1)}
        for p in workers.values():
            p.start()
        pending = iter(jobs(stage))
        active = {}
        count = 0
        try:
            for gpu in (0, 1):
                task = next(pending, None)
                if task:
                    tasks[gpu].put(task)
                    active[gpu] = task["id"]
            while active:
                try:
                    gpu, job_id, error = result.get(timeout=10)
                except queue.Empty:
                    if any(p.exitcode is not None for p in workers.values()):
                        raise RuntimeError("worker exited without receipt")
                    continue
                if active[gpu] != job_id:
                    raise RuntimeError("out-of-order stage receipt")
                if error:
                    raise RuntimeError(job_id + " failed without retry:\n" + error)
                count += 1
                next_job = next(pending, None)
                if next_job:
                    tasks[gpu].put(next_job)
                    active[gpu] = next_job["id"]
                else:
                    del active[gpu]
                receipt(base / f"{stage.lower()}_status.json", {
                    "status": "RUNNING", "completed": count, "active": active,
                    "observed_at": c.now()})
            for gpu in workers:
                tasks[gpu].put(None)
            for p in workers.values():
                p.join()
            if any(p.exitcode != 0 for p in workers.values()):
                raise RuntimeError("stage worker process failed")
            finalize(base, source)
            receipt(base / f"{stage.lower()}_status.json", {
                "status": "COMPLETE_SERVER_CHECKED", "completed": count,
                "observed_at": c.now()})
        except BaseException as exc:
            receipt(base / f"{stage.lower()}_status.json", {
                "status": "FAILED_NO_RETRY", "completed": count, "error": str(exc),
                "observed_at": c.now()})
            for p in workers.values():
                if p.is_alive():
                    p.terminate()
                p.join()
            raise
