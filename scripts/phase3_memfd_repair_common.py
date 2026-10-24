"""Read-only admission and binding checks for a registration-only memfd repair."""
import hashlib
import json
import os
from pathlib import Path
import re

M2_COMMIT = "ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd"
COMBINED_COMMIT = "e65c6cb0830985461b3cd30e2f43158dd3d858cb"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp." + str(os.getpid()))
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def bindings(base):
    return {name: sha(base/name) for name in ("plan.json", "code_manifest.json", "folds.json")}


def validate_target_checks(transcript):
    if ("Ran 16 tests" not in transcript or "skipped" in transcript.lower()
            or not re.search(r"test_linux_process_memfd[^\n]*\.\.\. ok", transcript)):
        raise RuntimeError("all original 16 checks including Linux FD transport must pass")
    return True


def verify_sources(base, combined):
    binding = bindings(base)
    if read(base/"registration.json")["binding"] != binding:
        raise RuntimeError("original M2 registration binding changed")
    plan = read(base/"plan.json")
    if (plan["execution_commit"] != M2_COMMIT or plan["core_jobs"] != 108
            or plan["updates"] != 32000 or plan["batch"] != 16 or plan["auto_retry"]
            or plan["physical_gpus"] != [0, 1]):
        raise RuntimeError("original M2 execution contract differs")
    for name, expected in read(base/"code_manifest.json")["files"].items():
        target = (base/"code"/name).resolve()
        target.relative_to((base/"code").resolve())
        if sha(target) != expected:
            raise RuntimeError("original M2 source changed: " + name)
    registration = read(combined/"registration.json")
    if (registration["execution_commit"] != COMBINED_COMMIT
            or read(combined/"plan.json")["m2_execution_commit"] != M2_COMMIT):
        raise RuntimeError("combined execution source differs")
    manifest = combined/"code/configs/phase3_combined_execution_manifest.json"
    if sha(manifest) != registration["manifest_sha256"]:
        raise RuntimeError("combined manifest changed")
    if read(manifest)["files"] != registration["package_files"]:
        raise RuntimeError("combined manifest payload differs")
    for name, expected in registration["package_files"].items():
        target = (combined/"code"/name).resolve()
        target.relative_to((combined/"code").resolve())
        if sha(target) != expected:
            raise RuntimeError("combined source changed: " + name)
    return binding


def admit_registration_failure(base, combined):
    """Refuse training resumes, partial launches, foreign failures and missing evidence."""
    if (base/"launch.json").exists() or any((base/"jobs").iterdir()):
        raise RuntimeError("M2 has launch or job evidence; no training retry permitted")
    for name in ("queue_status.json", "controller_failure.json", "target_checks.json",
                 "input_index.json", "nohup.log", "runtime_repair.json"):
        if (base/name).exists():
            raise RuntimeError("M2 progressed beyond this registration-only repair: " + name)
    failure = read(base/"registration_failure.json")
    if failure["automatic_retry"] or "test_phase3_m2.py" not in failure["error"]:
        raise RuntimeError("unexpected M2 registration failure")
    log = (base/"target_checks.log").read_text(encoding="utf-8")
    if not all(text in log for text in ("ERROR: test_linux_process_memfd",
            "Linux anonymous memfd required; no disk-array fallback", "FAILED (errors=1)")):
        raise RuntimeError("not the diagnosed single memfd admission failure")
    status = read(combined/"queue_status.json")
    if (status["status"] != "STOPPED_NO_AUTOMATIC_RETRY"
            or status["error"] != "M2 bootstrap failed; see m2_bootstrap.log"):
        raise RuntimeError("unexpected combined stop; no automatic restart")
    if any((combined/"jobs").iterdir()) or (combined/"m2_source.json").exists():
        raise RuntimeError("combined progressed beyond M2 registration")
    return {"m2_failure": failure, "combined_status": status,
            "failed_checks_sha256": sha(base/"target_checks.log"), "training_jobs": 0}
