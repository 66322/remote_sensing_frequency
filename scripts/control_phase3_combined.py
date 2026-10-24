"""Single-owner M2→J→R→T→V supervisor. No job retry or test release."""
import argparse
import fcntl
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from phase3_combined_plan import read, digest, public_catalog_status, validate_plan
from phase3_stage_control import receipt

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")


def now():
    from datetime import datetime, timezone, timedelta
    return datetime.now(timezone(timedelta(hours=8))).isoformat()


def _verify_package(queue):
    registration=read(queue/"registration.json")
    manifest_path=queue/"code/configs/phase3_combined_execution_manifest.json"
    if digest(manifest_path)!=registration["manifest_sha256"]:
        raise RuntimeError("combined execution manifest changed")
    files=registration["package_files"]
    if read(manifest_path)["files"]!=files:
        raise RuntimeError("combined execution manifest payload differs from registration")
    for name,expected in files.items():
        path=(queue/"code"/name).resolve()
        path.relative_to((queue/"code").resolve())
        if digest(path)!=expected:
            raise RuntimeError("combined execution source changed: "+name)


def _m2_directory(records):
    values = sorted(records.glob("research_phase3_m2_*"))
    if len(values) > 1:
        raise RuntimeError("multiple M2 runs; manual source selection required")
    return values[0] if values else None


def _m2_core(base):
    source = base / "publication"
    summary = source / "summary.json"
    gates = source / "gates.json"
    if not summary.exists() or not gates.exists():
        return False
    if read(summary)["status"] != "COMPLETE_SERVER_CHECKED":
        raise RuntimeError("M2 did not finish as server-checked")
    if not read(gates)["status"]["G0"]:
        raise RuntimeError("M2 input integrity G0 failed; later stages blocked")
    return True


def _source_ready(directory):
    status = directory / "queue_status.json"
    if status.exists() and read(status)["status"] in (
        "FAILED_NO_RETRY", "GPU_BUSY_NOT_STARTED", "GPU_BECAME_BUSY_NOT_TRAINED"):
        raise RuntimeError("M2 requires manual review: " + status.read_text(encoding="utf-8"))
    return _m2_core(directory)


def run(queue):
    queue = Path(queue).resolve()
    plan = read(queue / "plan.json")
    validate_plan(plan)
    records = ROOT / "records"
    package = queue / "code"
    catalog_source = Path(read(queue / "registration.json")["catalog_source"])
    with (queue / "controller.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        source = None
        try:
            _verify_package(queue)
            while source is None:
                source = _m2_directory(records)
                if source is None:
                    _verify_package(queue)
                    receipt(queue / "queue_status.json", {"status":"WAIT_M2_REGISTRATION",
                            "observed_at":now()})
                    completed = subprocess.run([sys.executable, "-B",
                        str(package / "scripts/bootstrap_phase3_m2.py"),
                        "--root", str(ROOT), "--commit", plan["m2_execution_commit"]],
                        cwd=package, capture_output=True, text=True, timeout=600)
                    (queue / "m2_bootstrap.log").write_text(
                        completed.stdout + completed.stderr, encoding="utf-8")
                    if completed.returncode:
                        raise RuntimeError("M2 bootstrap failed; see m2_bootstrap.log")
                    source = _m2_directory(records)
                    if source is None:
                        time.sleep(300)
            receipt(queue / "m2_source.json", {"directory":str(source),
                    "binding_commit":plan["m2_execution_commit"],"observed_at":now()})
            if read(source/"plan.json")["execution_commit"]!=plan["m2_execution_commit"]:
                raise RuntimeError("existing M2 source commit differs from frozen queue plan")
            while not _source_ready(source):
                receipt(queue / "queue_status.json", {"status":"WAIT_M2",
                        "source":str(source),"last_source_status":
                        read(source/"queue_status.json") if (source/"queue_status.json").exists() else None,
                        "observed_at":now()})
                time.sleep(300)
            sys.path[:0] = [str(source/"code"),str(source/"code/scripts")]
            from phase3_j_runtime import run as run_j
            from phase3_r_runtime import run as run_r
            from phase3_public_runtime import run as run_public
            for stage, invoke in (("J",lambda:run_j(queue,source)),
                                  ("R",lambda:run_r(queue,source))):
                _verify_package(queue)
                receipt(queue/"queue_status.json",{"status":"RUNNING_"+stage,
                        "observed_at":now()})
                invoke()
                _verify_package(queue)
            if (queue/"catalog.json").exists():
                status=public_catalog_status(queue/"catalog.json")
                if not all(status[x]["ready"] for x in ("3DCD","P3")):
                    raise RuntimeError("frozen queue catalog incomplete")
            else:
                while True:
                    status=public_catalog_status(catalog_source)
                    if all(status[x]["ready"] for x in ("3DCD","P3")):
                        before=digest(catalog_source)
                        shutil.copyfile(catalog_source,queue/"catalog.json")
                        if before!=digest(catalog_source) or before!=digest(queue/"catalog.json"):
                            raise RuntimeError("catalog changed during freeze; no public-data training")
                        break
                    receipt(queue/"queue_status.json",{"status":"WAIT_PUBLIC_DATA",
                            "catalog_source":str(catalog_source),"readiness":status,
                            "observed_at":now()})
                    time.sleep(600)
            for stage in ("T","V"):
                _verify_package(queue)
                receipt(queue/"queue_status.json",{"status":"RUNNING_"+stage,
                        "observed_at":now()})
                run_public(stage,queue,source)
                _verify_package(queue)
            receipt(queue/"queue_status.json",{"status":"COMPLETE_SERVER_CHECKED",
                    "completed_stages":["M2","J","R","T","V"],"observed_at":now()})
        except BaseException as exc:
            receipt(queue/"queue_status.json",{"status":"STOPPED_NO_AUTOMATIC_RETRY",
                    "error":str(exc),"observed_at":now()})
            raise


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--directory",type=Path,required=True)
    args=parser.parse_args()
    run(args.directory)
