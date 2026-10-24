"""Explicit repair of the diagnosed pre-training registration failure in existing runs.

Never edits a frozen source/binding, launches a new run, or retries a training job.
"""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
M2_COMMIT = "ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd"
COMBINED_COMMIT = "e65c6cb0830985461b3cd30e2f43158dd3d858cb"


def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()


def download(commit, name):
    url = "https://raw.githubusercontent.com/66322/remote_sensing_frequency/" + commit + "/" + name
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def validated_directory(value, prefix, records):
    if not value.is_absolute() or value.is_symlink():
        raise RuntimeError("absolute original run directory required")
    result = value.resolve()
    if result.parent != records or not result.name.startswith(prefix):
        raise RuntimeError("unexpected original run path")
    return result


def main():
    import fcntl
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--m2-directory", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="launch only after full admission and target checks")
    args = parser.parse_args()
    if not re.fullmatch("[a-f0-9]{40}", args.commit):
        raise RuntimeError("immutable full repair commit required")
    records = (ROOT/"records").resolve()
    combined = validated_directory(args.directory, "research_phase3_combined_", records)
    base = validated_directory(args.m2_directory, "research_phase3_m2_", records)
    if sorted(records.glob("research_phase3_m2_*")) != [base]:
        raise RuntimeError("M2 source is not unique; no implicit source selection")
    repairs = combined/"repairs"
    repairs.mkdir(exist_ok=True)
    with (repairs/"memfd_registration.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous = sorted(repairs.glob("memfd_*/launch.json"))
        if previous:
            for path in previous:
                print("EXISTING_REPAIR_NO_DUPLICATE", path, path.read_text(), flush=True)
            return
        repair = repairs/("memfd_" + args.commit)
        repair.mkdir(exist_ok=True)
        if (repair/"checks_failed.json").exists():
            raise RuntimeError("prior repair checks failed; preserve and inspect, no automatic retry")
        raw = download(args.commit, "configs/phase3_memfd_repair_manifest.json")
        manifest = json.loads(raw)
        if (manifest["schema_version"] != 1 or manifest["m2_execution_commit"] != M2_COMMIT
                or manifest["combined_execution_commit"] != COMBINED_COMMIT):
            raise RuntimeError("repair manifest contract differs")
        package = repair/"code"
        package.mkdir(exist_ok=True)
        for name, expected in manifest["files"].items():
            target = (package/name).resolve()
            target.relative_to(package.resolve())
            if target.exists():
                if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                    raise RuntimeError("existing repair source changed: " + name)
            else:
                data = download(args.commit, name)
                if hashlib.sha256(data).hexdigest() != expected:
                    raise RuntimeError("repair source download changed: " + name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        saved_manifest = repair/"execution_manifest.json"
        if saved_manifest.exists() and saved_manifest.read_bytes() != raw:
            raise RuntimeError("existing repair manifest differs")
        saved_manifest.write_bytes(raw)
        print("REPAIR_PACKAGE_VERIFIED", len(manifest["files"]), repair, flush=True)
        sys.path.insert(0, str(package/"scripts"))
        from phase3_memfd_repair_common import (read, write, sha, verify_sources,
            admit_registration_failure, validate_target_checks)
        # Locks prove no surviving controller owns either original run. Never kill by PID/name.
        for directory in (combined, base):
            with (directory/"controller.lock").open("a") as controller_lock:
                fcntl.flock(controller_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(controller_lock, fcntl.LOCK_UN)
        original_binding = verify_sources(base, combined)
        evidence = admit_registration_failure(base, combined)
        print("REGISTRATION_ONLY_ADMISSION_OK", "training_jobs=0", flush=True)
        for name, expected in manifest["required_m2_files"].items():
            if sha(base/"code"/name) != expected:
                raise RuntimeError("repair does not match frozen M2 file: " + name)
        import torch
        if torch.__version__ != "2.2.2+cu121" or not torch.cuda.is_available():
            raise RuntimeError("existing environment must remain Torch2.2.2+cu121 with CUDA")
        sys.path[:0] = [str(base/"code"), str(base/"code/scripts")]
        import phase3_m2_common as common
        inventory = common.gpu_inventory()
        if not inventory["ready"]:
            print("GPU0_OR_1_BUSY_NO_REPAIR_LAUNCHED", json.dumps(inventory), flush=True)
            return
        write(repair/"admission.json", {"observed_at": now(), "repair_commit": args.commit,
            "m2_directory": str(base), "combined_directory": str(combined),
            "original_binding": original_binding, "evidence": evidence,
            "gpu_inventory": inventory, "manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "frozen_sources_modified": False, "training_retry": False})
        entry = package/"scripts/phase3_memfd_entry.py"
        env = common.environment(base)
        env["M2_TARGET_RUNTIME"] = "1"
        checks = repair/"target_checks.log"
        passed = repair/"target_checks_passed.json"
        if passed.exists():
            receipt = read(passed)
            if (receipt["log_sha256"] != sha(checks) or receipt["original_binding"] != original_binding
                    or receipt["python"] != sys.version or receipt["executable"] != sys.executable):
                raise RuntimeError("prior successful repair check binding differs")
        else:
            print("CHECKING_ORIGINAL_M2_16", checks, flush=True)
            try:
                with checks.open("x", encoding="utf-8") as output:
                    result = subprocess.run([sys.executable, "-u", "-B", str(entry), "--mode", "checks",
                        "--directory", str(base)], cwd=base/"code", env=env,
                        stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, timeout=300)
            except BaseException as error:
                write(repair/"checks_failed.json", {"error": str(error), "log": str(checks),
                    "automatic_retry": False, "observed_at": now()})
                raise
            if result.returncode:
                write(repair/"checks_failed.json", {"returncode": result.returncode,
                    "log": str(checks), "automatic_retry": False, "observed_at": now()})
                raise RuntimeError("original M2 target checks failed; see " + str(checks))
            transcript = checks.read_text(encoding="utf-8")
            try:
                validate_target_checks(transcript)
            except RuntimeError:
                write(repair/"checks_failed.json", {"error": "full Linux memfd check was not proven",
                    "log": str(checks), "automatic_retry": False, "observed_at": now()})
                raise
            write(passed, {"passed": True, "original_binding": original_binding,
                "log_sha256": sha(checks), "observed_at": now(), "extra_training": False,
                "python": sys.version, "executable": sys.executable})
        print("ORIGINAL_M2_TARGET_CHECKS_PASSED", checks, flush=True)
        if not args.apply:
            print("CHECKS_ONLY_NO_CONTROLLER_LAUNCHED", flush=True)
            return
        # Recheck originals, no-job admission, source package and GPU occupancy just before launch.
        if verify_sources(base, combined) != original_binding:
            raise RuntimeError("original bindings changed during repair checks")
        admit_registration_failure(base, combined)
        for name, expected in manifest["files"].items():
            if sha(package/name) != expected:
                raise RuntimeError("repair code changed during checks")
        if not common.gpu_inventory()["ready"]:
            print("GPU_BECAME_BUSY_NO_REPAIR_LAUNCHED", flush=True)
            return
        # Durable launch intent is a duplicate guard even if this process dies after one Popen.
        launch = {"status": "LAUNCHING_ONCE", "repair_commit": args.commit,
            "m2_controller_pid": None, "combined_controller_pid": None,
            "training_retry": False, "automatic_retry": False, "observed_at": now()}
        write(repair/"launch.json", launch)
        runtime_receipt = {"repair_commit": args.commit, "original_execution_commit": M2_COMMIT,
            "original_binding": original_binding, "runtime_wrapper": str(entry),
            "repair_directory": str(repair), "repair_files": manifest["files"],
            "manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "only_change": "missing OS memfd API binding; no disk fallback",
            "frozen_sources_modified": False, "training_retry": False, "observed_at": now()}
        write(base/"runtime_repair.json", runtime_receipt)
        write(combined/"runtime_repair.json", runtime_receipt)
        env["PHASE3_RUNTIME_REPAIR_RECEIPT"] = str(base/"runtime_repair.json")
        write(base/"target_checks.json", {"passed": True, "log": str(checks),
            "log_sha256": sha(checks), "repair_commit": args.commit,
            "original_failed_log_preserved": True, "CUDA_checks": "first formal update; no extra training",
            "observed_at": now()})
        write(repair/"combined_status_before.json", read(combined/"queue_status.json"))
        # Write before Popen so an immediate child failure cannot be overwritten by this parent.
        write(base/"queue_status.json", {"status": "LAUNCHED_PREPARING",
            "launch_receipt": str(base/"launch.json"), "repair_commit": args.commit,
            "observed_at": now()})
        with (base/"nohup.log").open("x", encoding="utf-8") as output:
            process = subprocess.Popen([sys.executable, "-u", "-B", str(entry), "--mode", "m2",
                "--directory", str(base)], cwd=base/"code", env=env,
                stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        launch["m2_controller_pid"] = process.pid
        write(repair/"launch.json", launch)
        write(base/"launch.json", {"controller_pid": process.pid, "repair_commit": args.commit,
            "runtime_wrapper": str(entry), "observed_at": now()})
        with (repair/"combined_nohup.log").open("x", encoding="utf-8") as output:
            supervisor = subprocess.Popen([sys.executable, "-u", "-B", str(entry), "--mode", "combined",
                "--directory", str(combined)], cwd=combined/"code", env=env,
                stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        launch.update(status="CONTROLLERS_LAUNCHED", combined_controller_pid=supervisor.pid, observed_at=now())
        write(repair/"launch.json", launch)
        print("EXISTING_M2_MEMFD_REPAIR_LAUNCHED", base, "m2_pid", process.pid,
              "combined_pid", supervisor.pid, "repair", repair, flush=True)


if __name__ == "__main__":
    main()
