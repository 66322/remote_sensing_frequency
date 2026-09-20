"""GPU0 serial queue; default is preflight ONLY. --execute explicitly starts jobs."""
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

from rebuild_v1_b2_common import ROOT, fingerprint, safe_output, validate_matched_config

OLD = [
    ("C", "b1_c_ce_control_4k.json", "B1_C_ce_control_seed42_sched4000_stop4000"),
    ("KD", "b1_kd_safe_teacher_4k.json", "B1_KD_safe_teacher_seed42_sched4000_stop4000"),
    ("SAFE", "b1_safe_fallback_4k.json", "B1_SAFE_fallback_seed42_sched4000_stop4000"),
]
NEW = [("R05_KD", "b2_r05_teacher_4k.json", "B2_R05_teacher"),
       ("AVG_KD", "b2_safe_average_teacher_4k.json", "B2_AVG_safe_teacher")]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def verify_sources():
    import hashlib
    m = read(ROOT / "configs/rebuild_v1/b2_night_manifest.json")
    for group in ("base_sources", "payload_sources"):
        for rel, expected in m[group].items():
            actual = hashlib.sha256((ROOT / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            if actual != expected:
                raise RuntimeError("Source mismatch, review before running: " + rel)
    return m


def validate_run(path, expected=4000):
    summary = read(path / "summary.json")
    if summary.get("global_step") != expected or summary.get("test6_loaded") is not False:
        raise RuntimeError("Incomplete/unsafe run: " + str(path))
    if not (path / "best_model.pth").is_file() or not summary.get("best"):
        raise RuntimeError("Missing selected checkpoint: " + str(path))
    return summary


def commands(tag, out):
    jobs = []
    def region(label, cfg, run, smoke=False, deps=()):
        name = label + ("_REGION_SMOKE" if smoke else "_REGIONS")
        dest = out / name
        command = [sys.executable, "-u", "scripts/eval_rebuild_v1_b2_regions.py",
                   "--config", "configs/rebuild_v1/" + cfg, "--run-dir", str(run),
                   "--out", str(dest), "--label", label]
        if smoke:
            command.append("--smoke")
        jobs.append(dict(name=name, command=command, outputs=[str(dest)], deps=list(deps),
                         seconds=1800 if smoke else 7200,
                         required=[str(dest / "summary.json")]))
        return name

    smoke = region(*OLD[0][:2], ROOT / "runs/rebuild_v1" / OLD[0][2], smoke=True)
    for label, cfg, slug in OLD:
        region(label, cfg, ROOT / "runs/rebuild_v1" / slug, deps=[smoke])
    for label, cfg, slug in NEW:
        previous = None
        for is_smoke in (True, False):
            name = label + ("_TRAIN_SMOKE" if is_smoke else "_TRAIN")
            kind = "smoke20" if is_smoke else "sched4000_stop4000"
            run = ROOT / "runs/rebuild_v1" / (slug + "_seed42_" + kind + "_" + tag)
            command = [sys.executable, "-u", "scripts/train_rebuild_v1_b2_teacher_controls.py",
                       "--config", "configs/rebuild_v1/" + cfg, "--run-tag", tag]
            if is_smoke:
                command += ["--smoke-steps", "20"]
            jobs.append(dict(name=name, command=command, outputs=[str(run)],
                             deps=[] if is_smoke else [previous],
                             seconds=1800 if is_smoke else 18000,
                             required=[str(run / "summary.json"), str(run / "last_train_state.pth")]
                             + ([] if is_smoke else [str(run / "best_model.pth")])))
            previous = name
        region(label, cfg, run, deps=[previous, smoke])
    return jobs


def preflight(tag, out, jobs):
    if Path.cwd().resolve() != ROOT.resolve():
        raise RuntimeError("Run from the declared server project root")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise RuntimeError("Export CUDA_VISIBLE_DEVICES=0 first")
    manifest = verify_sources()
    if shutil.disk_usage(ROOT).free < 20 * 1024**3:
        raise RuntimeError("Need at least 20 GiB free for new checkpoints and diagnostics")
    ref = read(ROOT / "configs/rebuild_v1/b1_kd_safe_teacher_4k.json")
    split = read(ROOT / ref["split_file"])
    if len(split["train16"]) != 16 or len(set(split["train16"])) != 16 or len(split["val2"]) != 2 or len(set(split["val2"])) != 2:
        raise RuntimeError("Expected unique Train16/Val2")
    if set(split["train16"]) & set(split["val2"]) or (set(split["train16"]) | set(split["val2"])) & set(split["historical_exposed_test6"]):
        raise RuntimeError("Split overlap")
    for _, cfg, _ in NEW:
        validate_matched_config(read(ROOT / "configs/rebuild_v1" / cfg), ref)
    input_paths = set()
    for _, cfg_name, slug in OLD:
        cfg = read(ROOT / "configs/rebuild_v1" / cfg_name)
        run = ROOT / "runs/rebuild_v1" / slug
        validate_run(run)
        metadata = read(run / "run_metadata.json")
        if metadata["config"] != cfg:
            raise RuntimeError("Old run/config mismatch: " + slug)
        input_paths.add(run / "best_model.pth")
    for key in ("student_init", "r01_teacher", "r05_teacher"):
        path = ROOT / ref[key]
        validate_run(path.parent, 16000)
        input_paths.add(path)
    if not Path(ref["data_root"]).is_dir() or not Path(ref["pretrain"]).is_file():
        raise RuntimeError("Data/pretrained asset missing")
    for job in jobs:
        for raw in job["outputs"]:
            category = "runs" if "/runs/" in raw else "records"
            safe_output(raw, category)
    safe_output(out)
    # Prevent accidentally sharing GPU0 with an independently launched job.
    gpu = subprocess.run(["nvidia-smi", "-i", "0", "--query-compute-apps=pid",
                          "--format=csv,noheader,nounits"], check=True, capture_output=True, text=True)
    active = [line.strip() for line in gpu.stdout.splitlines() if line.strip().isdigit()]
    if active:
        raise RuntimeError("GPU0 has active compute PIDs: " + ", ".join(active))
    boundary = [sys.executable, "scripts/validate_execution_boundaries.py", "--torch-check", "--output", str(out)]
    for job in jobs:
        for path in job["outputs"]:
            boundary += ["--output", path]
    subprocess.run(boundary, check=True)
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_rebuild_v1_b2_night.py", "-v"], check=True)
    return dict(checked_at=now(), tag=tag, base_commit=manifest["base_commit"],
                input_fingerprints=[fingerprint(p) for p in sorted(input_paths)],
                jobs=jobs, test6_loaded=False)


def terminate(proc):
    # Called only on explicitly documented deadline or user interruption.
    os.killpg(proc.pid, signal.SIGTERM)
    try:
        proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()


def execute(out, jobs, hours, report):
    import fcntl
    lock_path = ROOT / "records/rebuild_v1_b2_gpu0.lock"
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        out.mkdir(parents=True, exist_ok=False)
        (out / "preflight.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        deadline = time.monotonic() + hours * 3600
        states = {}
        def record(name, status, detail=""):
            states[name] = status
            print(now(), name, status, detail, flush=True)
            with (out / "status.tsv").open("a", encoding="utf-8", newline="") as f:
                csv.writer(f, delimiter="\t").writerow([now(), name, status, detail])
        record("QUEUE", "STARTED")
        try:
            for job in jobs:
                name = job["name"]
                if any(states.get(dep) != "COMPLETE" for dep in job["deps"]):
                    record(name, "SKIPPED", "dependency_not_complete")
                    continue
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    record(name, "SKIPPED", "night_deadline")
                    continue
                # Recheck boundaries immediately before EACH child job.
                boundary = [sys.executable, "scripts/validate_execution_boundaries.py",
                            "--torch-check", "--output", str(out)]
                for path in job["outputs"]:
                    boundary += ["--output", path]
                with (out / (name + ".log")).open("w", encoding="utf-8") as log:
                    rc = subprocess.run(boundary, stdout=log, stderr=subprocess.STDOUT).returncode
                    if rc:
                        record(name, "BLOCKED", "execution_boundary_failed")
                        continue
                    record(name, "STARTED")
                    proc = subprocess.Popen(job["command"], cwd=ROOT, stdout=log,
                                            stderr=subprocess.STDOUT, start_new_session=True)
                    try:
                        rc = proc.wait(timeout=min(job["seconds"], max(1, deadline-time.monotonic())))
                    except subprocess.TimeoutExpired:
                        record(name, "TIMEOUT_TERMINATING", "TERM then KILL after 60s")
                        terminate(proc)
                        rc = 124
                    except BaseException:
                        if proc.poll() is None:
                            terminate(proc)
                        raise
                missing = [p for p in job["required"] if not Path(p).is_file()]
                if rc == 0 and not missing:
                    # Completion flags, not mere existence.
                    s = read(job["required"][0])
                    if "_REGION" in name:
                        valid = s.get("status") == "COMPLETE" and s.get("test6_loaded") is False
                    else:
                        valid = s.get("global_step") == (20 if name.endswith("_SMOKE") else 4000) and s.get("test6_loaded") is False
                    if not valid:
                        rc = 91
                record(name, "COMPLETE" if rc == 0 and not missing else "FAILED",
                       "exit=" + str(rc) + (" missing=" + ",".join(missing) if missing else ""))
        except KeyboardInterrupt:
            record("QUEUE", "INTERRUPTED", "No retry")
            raise
        finally:
            summary_result = subprocess.run([sys.executable, "scripts/summarize_rebuild_v1_b2_night.py", "--queue", str(out)], check=False)
            record("SUMMARIZE", "COMPLETE" if summary_result.returncode == 0 else "FAILED", str(summary_result.returncode))
            failed = any(states.get(j["name"]) != "COMPLETE" for j in jobs) or summary_result.returncode != 0
            if states.get("QUEUE") != "INTERRUPTED":
                record("QUEUE", "FINISHED_WITH_ISSUES" if failed else "COMPLETE")
            (out / "queue_summary.json").write_text(json.dumps(dict(
                observed_at=now(), statuses=states, test6_loaded=False), indent=2), encoding="utf-8")
            archive_results(out, jobs)
        return 1 if failed else 0


def archive_results(out, jobs):
    import zipfile
    paths = set()
    for parent in [out] + [Path(p) for j in jobs for p in j["outputs"] if "/runs/" in p]:
        if parent.is_dir():
            for p in parent.rglob("*"):
                if p.is_file() and p.suffix in (".csv", ".json", ".npy", ".log", ".tsv", ".md"):
                    paths.add(p)
    # Preserve code/config provenance without datasets, weights, or credentials.
    manifest = read(ROOT / "configs/rebuild_v1/b2_night_manifest.json")
    for rel in list(manifest["payload_sources"]) + ["configs/rebuild_v1/b2_night_manifest.json"]:
        paths.add(ROOT / rel)
    with zipfile.ZipFile(out / "morning_results.zip", "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(paths):
            z.write(p, p.relative_to(ROOT).as_posix())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="night20260920_v1")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--max-hours", type=float, default=12)
    args = ap.parse_args()
    if not args.tag or not all(c.isalnum() or c in "_-" for c in args.tag):
        raise ValueError("Unsafe tag")
    if not 0 < args.max_hours <= 12:
        raise ValueError("Hard night budget must be in (0, 12] hours")
    out = ROOT / "records" / ("rebuild_v1_b2_" + args.tag)
    jobs = commands(args.tag, out)
    report = preflight(args.tag, out, jobs)
    print("PREFLIGHT_PASS", json.dumps(report, indent=2), flush=True)
    if not args.execute:
        print("NO JOBS STARTED. Re-run with --execute to launch.")
        return 0
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    return execute(out, jobs, args.max_hours, report)


if __name__ == "__main__":
    raise SystemExit(main())
