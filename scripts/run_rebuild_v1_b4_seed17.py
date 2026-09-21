"""Prespecified seed17 replication queue. Default is preflight only."""
import argparse
import csv
import json
import os
import signal
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from rebuild_v1_b2_common import ROOT, fingerprint, safe_output

ARMS = (
    ("C17", "configs/rebuild_v1/b4_c_seed17_4k.json",
     "scripts/train_rebuild_v1_b1_distillation.py", "B1_C_ce_control"),
    ("R05_KD17", "configs/rebuild_v1/b4_r05_teacher_seed17_4k.json",
     "scripts/train_rebuild_v1_b2_teacher_controls.py", "B2_R05_teacher"),
    ("KD17", "configs/rebuild_v1/b4_kd_seed17_4k.json",
     "scripts/train_rebuild_v1_b1_distillation.py", "B1_KD_safe_teacher"),
)

PROVENANCE_FILES = (
    "configs/rebuild_v1/b4_c_seed17_4k.json",
    "configs/rebuild_v1/b4_kd_seed17_4k.json",
    "configs/rebuild_v1/b4_r05_teacher_seed17_4k.json",
    "scripts/rebuild_v1_b2_common.py",
    "scripts/train_rebuild_v1_b1_distillation.py",
    "scripts/train_rebuild_v1_b2_teacher_controls.py",
    "scripts/eval_rebuild_v1_dual_robust_conditions.py",
    "scripts/eval_rebuild_v1_b3_paired_regions.py",
    "scripts/run_rebuild_v1_b4_seed17.py",
    "scripts/summarize_rebuild_v1_b4_seed17.py",
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def normalized(cfg):
    cfg = json.loads(json.dumps(cfg))
    for key in ("version", "purpose", "model_id"):
        cfg.pop(key, None)
    cfg["seed"] = "SEED"
    for key in ("student_init", "r01_teacher", "r05_teacher"):
        cfg[key] = key.upper()
    cfg["distillation"]["mode"] = "MODE"
    cfg["distillation"]["teacher_kl_weight"] = "KD_WEIGHT"
    return cfg


def validate_configs():
    expected = {
        "C17": ("B1-C", "ce_control", 0.0),
        "R05_KD17": ("B2-R05", "r05_teacher_kd", 0.5),
        "KD17": ("B1-KD", "safe_teacher_kd", 0.5),
    }
    configs = {}
    reference = read(ROOT / "configs/rebuild_v1/b1_kd_safe_teacher_4k.json")
    for label, rel, _, _ in ARMS:
        cfg = read(ROOT / rel)
        model_id, mode, weight = expected[label]
        if cfg["seed"] != 17 or cfg["model_id"] != model_id:
            raise RuntimeError("B4 identity/seed mismatch: " + label)
        if cfg["distillation"]["mode"] != mode or float(cfg["distillation"]["teacher_kl_weight"]) != weight:
            raise RuntimeError("B4 distillation mismatch: " + label)
        if float(cfg["distillation"]["missing_fallback_kl_weight"]) != 0.0:
            raise RuntimeError("B4 excludes extra fallback KL")
        if normalized(cfg) != normalized(reference):
            raise RuntimeError("B4 arm differs from matched seed42 protocol beyond controlled fields: " + label)
        for key, slug in (("student_init", "R05_dual_f0_quality_plus_dropout"),
                          ("r01_teacher", "R01_optical_only"),
                          ("r05_teacher", "R05_dual_f0_quality_plus_dropout")):
            expected_path = f"runs/rebuild_v1/{slug}_seed17_sched16000_stop16000/best_model.pth"
            if cfg[key] != expected_path:
                raise RuntimeError(f"B4 {label} {key} mismatch")
        configs[label] = cfg
    return configs


def validate_base_run(path):
    summary = read(path / "summary.json")
    metadata = read(path / "run_metadata.json")
    if summary.get("global_step") != 16000 or summary.get("test6_loaded") is not False:
        raise RuntimeError("Incomplete/unsafe seed17 base run: " + str(path))
    if int(metadata.get("config", {}).get("seed", -1)) != 17:
        raise RuntimeError("Base run metadata is not seed17: " + str(path))
    if not (path / "best_model.pth").is_file():
        raise RuntimeError("Missing seed17 base checkpoint: " + str(path))


def build_jobs(tag, root):
    jobs = []
    for label, cfg, trainer, slug in ARMS:
        smoke_run = ROOT / "runs/rebuild_v1" / f"{slug}_seed17_smoke20_{tag}"
        full_run = ROOT / "runs/rebuild_v1" / f"{slug}_seed17_sched4000_stop4000_{tag}"
        smoke = label + "_SMOKE"
        train = label + "_TRAIN"
        jobs.append({
            "name": smoke, "deps": [], "seconds": 1800,
            "command": [sys.executable, "-u", trainer, "--config", cfg,
                        "--run-tag", tag, "--smoke-steps", "20"],
            "outputs": [str(smoke_run)], "required": [str(smoke_run / "summary.json")],
            "kind": "train", "expected_step": 20,
        })
        jobs.append({
            "name": train, "deps": [smoke], "seconds": 14400,
            "command": [sys.executable, "-u", trainer, "--config", cfg, "--run-tag", tag],
            "outputs": [str(full_run)],
            "required": [str(full_run / "summary.json"), str(full_run / "best_model.pth")],
            "kind": "train", "expected_step": 4000,
        })
        robust_out = root / (label + "_ROBUST")
        robust = label + "_ROBUST"
        jobs.append({
            "name": robust, "deps": [train], "seconds": 3600,
            "command": [sys.executable, "-u", "scripts/eval_rebuild_v1_dual_robust_conditions.py",
                        "--variant", "R05", "--config", cfg, "--run-dir", str(full_run),
                        "--out", str(robust_out)],
            "outputs": [str(robust_out)], "required": [str(robust_out / "summary.json")],
            "kind": "robust", "expected_step": 4000,
        })
        paired_out = root / (label + "_PAIRED")
        paired = label + "_PAIRED"
        jobs.append({
            "name": paired, "deps": [train], "seconds": 3600,
            "command": [sys.executable, "-u", "scripts/eval_rebuild_v1_b3_paired_regions.py",
                        "--config", cfg, "--run-dir", str(full_run), "--out", str(paired_out),
                        "--label", label],
            "outputs": [str(paired_out)], "required": [str(paired_out / "summary.json")],
            "kind": "paired", "expected_step": 4000,
        })
    return jobs


def preflight(tag, root, jobs):
    if Path.cwd().resolve() != ROOT.resolve():
        raise RuntimeError("Run from the declared project root")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise RuntimeError("Export CUDA_VISIBLE_DEVICES=0 first")
    configs = validate_configs()
    for slug in ("R01_optical_only_seed17_sched16000_stop16000",
                 "R05_dual_f0_quality_plus_dropout_seed17_sched16000_stop16000"):
        validate_base_run(ROOT / "runs/rebuild_v1" / slug)
    for cfg in configs.values():
        if not Path(cfg["data_root"]).is_dir() or not Path(cfg["pretrain"]).is_file():
            raise RuntimeError("Missing data or pretrained asset")
    if shutil.disk_usage(ROOT).free < 20 * 1024**3:
        raise RuntimeError("Need at least 20 GiB free")
    safe_output(root)
    for job in jobs:
        for raw in job["outputs"]:
            safe_output(raw, "runs" if "/runs/" in raw else "records")
    gpu = subprocess.run(["nvidia-smi", "-i", "0", "--query-compute-apps=pid",
                          "--format=csv,noheader,nounits"], check=True,
                         capture_output=True, text=True)
    active = [x.strip() for x in gpu.stdout.splitlines() if x.strip().isdigit()]
    if active:
        raise RuntimeError("GPU0 has active compute PIDs: " + ", ".join(active))
    boundary = [sys.executable, "scripts/validate_execution_boundaries.py", "--torch-check",
                "--output", str(root)]
    for job in jobs:
        for output in job["outputs"]:
            boundary += ["--output", output]
    subprocess.run(boundary, check=True)
    subprocess.run([sys.executable, "-m", "unittest", "tests.test_rebuild_v1_b4_seed17", "-v"], check=True)
    return {"checked_at": now(), "tag": tag, "arms": list(configs),
            "primary": ["clean", "dsm_down8", "dsm_zero", "local damaged region"],
            "secondary": ["synthetic interface band", "per-class diagnostics"],
            "source_fingerprints": {rel: fingerprint(ROOT / rel) for rel in PROVENANCE_FILES},
            "jobs": jobs, "test6_loaded": False}


def terminate(proc):
    os.killpg(proc.pid, signal.SIGTERM)
    try:
        proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()


def execute(root, jobs, max_hours, report):
    import fcntl
    lock_path = ROOT / "records/rebuild_v1_b4_seed17_gpu0.lock"
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        root.mkdir(parents=True, exist_ok=False)
        (root / "preflight.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        deadline = time.monotonic() + max_hours * 3600
        states = {}

        def record(name, status, detail=""):
            states[name] = status
            print(now(), name, status, detail, flush=True)
            with (root / "status.tsv").open("a", newline="", encoding="utf-8") as f:
                csv.writer(f, delimiter="\t").writerow([now(), name, status, detail])

        record("QUEUE", "STARTED")
        try:
            for job in jobs:
                if any(states.get(dep) != "COMPLETE" for dep in job["deps"]):
                    record(job["name"], "SKIPPED", "dependency_not_complete")
                    continue
                if deadline <= time.monotonic():
                    record(job["name"], "SKIPPED", "deadline")
                    continue
                log_path = root / (job["name"] + ".log")
                with log_path.open("w", encoding="utf-8") as log:
                    boundary = [sys.executable, "scripts/validate_execution_boundaries.py",
                                "--torch-check", "--output", str(root)]
                    for output in job["outputs"]:
                        boundary += ["--output", output]
                    boundary_code = subprocess.run(
                        boundary, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT
                    ).returncode
                    if boundary_code:
                        record(job["name"], "BLOCKED", "execution_boundary_failed")
                        continue
                    record(job["name"], "STARTED")
                    proc = subprocess.Popen(job["command"], cwd=ROOT, stdout=log,
                                            stderr=subprocess.STDOUT, start_new_session=True)
                    try:
                        timeout = min(job["seconds"], max(1, deadline - time.monotonic()))
                        code = proc.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        terminate(proc)
                        code = 124
                    except BaseException:
                        if proc.poll() is None:
                            terminate(proc)
                        raise
                missing = [p for p in job["required"] if not Path(p).is_file()]
                valid = code == 0 and not missing
                if valid:
                    summary = read(job["required"][0])
                    if job["kind"] == "train":
                        valid = summary.get("global_step") == job["expected_step"] and summary.get("test6_loaded") is False
                    elif job["kind"] == "robust":
                        valid = summary.get("historical_test6_loaded") is False and int(summary.get("checkpoint_step", -1)) > 0
                    else:
                        valid = summary.get("status") == "COMPLETE" and summary.get("test6_loaded") is False
                record(job["name"], "COMPLETE" if valid else "FAILED",
                       "exit=" + str(code) + (" missing=" + ",".join(missing) if missing else ""))
        finally:
            result = subprocess.run([sys.executable, "scripts/summarize_rebuild_v1_b4_seed17.py",
                                     "--root", str(root)], cwd=ROOT)
            record("SUMMARIZE", "COMPLETE" if result.returncode == 0 else "FAILED",
                   "exit=" + str(result.returncode))
            failed = any(states.get(job["name"]) != "COMPLETE" for job in jobs) or result.returncode != 0
            record("QUEUE", "FINISHED_WITH_ISSUES" if failed else "COMPLETE")
            (root / "queue_summary.json").write_text(json.dumps(
                {"observed_at": now(), "statuses": states, "test6_loaded": False}, indent=2),
                encoding="utf-8")
        return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="b4seed17_20260921")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-hours", type=float, default=12)
    args = parser.parse_args()
    if not args.tag or not all(c.isalnum() or c in "_-" for c in args.tag):
        raise ValueError("Unsafe tag")
    if not 0 < args.max_hours <= 12:
        raise ValueError("max-hours must be in (0, 12]")
    root = ROOT / "records" / ("rebuild_v1_b4_" + args.tag)
    jobs = build_jobs(args.tag, root)
    report = preflight(args.tag, root, jobs)
    print("B4_PREFLIGHT_PASS", json.dumps(report, indent=2), flush=True)
    if not args.execute:
        print("NO JOBS STARTED. Re-run with --execute.")
        return 0
    return execute(root, jobs, args.max_hours, report)


if __name__ == "__main__":
    raise SystemExit(main())
