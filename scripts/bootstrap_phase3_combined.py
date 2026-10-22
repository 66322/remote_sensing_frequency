"""Register one combined queue from an immutable GitHub commit; never start a duplicate."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
REPO="https://raw.githubusercontent.com/66322/remote_sensing_frequency/"


def sha(value): return hashlib.sha256(value).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def download(commit,path):
    with urllib.request.urlopen(REPO+commit+"/"+path,timeout=120) as response:
        return response.read()


def main():
    import fcntl
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--commit",required=True)
    p.add_argument("--catalog",type=Path,default=ROOT/"records/phase3_combined_public_catalog.json")
    p.add_argument("--inspect",action="store_true")
    args=p.parse_args()
    root=args.root.resolve()
    if root!=ROOT or not re.fullmatch(r"[a-f0-9]{40}",args.commit):
        raise RuntimeError("exact project root and full immutable commit required")
    records=root/"records"
    catalog=args.catalog.resolve()
    catalog.relative_to(Path("/home/jovyan/zzx"))
    if args.inspect:
        print("COMBINED_INSPECT_ONLY",json.dumps({
            "m2_runs":[str(v) for v in sorted(records.glob("research_phase3_m2_*"))],
            "combined_runs":[str(v) for v in sorted(records.glob("research_phase3_combined_*"))],
            "catalog_path":str(catalog),"catalog_present":catalog.is_file()},ensure_ascii=False))
        return
    manifest=json.loads(download(args.commit,"configs/phase3_combined_execution_manifest.json"))
    if manifest["schema_version"]!=1:
        raise RuntimeError("combined manifest schema mismatch")
    package=records/("phase3_combined_package_"+args.commit)
    package.mkdir(exist_ok=True)
    with (records/"phase3_combined_registration.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for name,expected in manifest["files"].items():
            target=(package/name).resolve();target.relative_to(package.resolve())
            if target.exists():
                if sha(target.read_bytes())!=expected:
                    raise RuntimeError("existing package source changed: "+name)
                continue
            data=download(args.commit,name)
            if sha(data)!=expected:raise RuntimeError("downloaded source mismatch: "+name)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(data)
        sys.path[:0]=[str(package),str(package/"scripts")]
        from phase3_combined_plan import validate_plan, admissible_path, public_catalog_status
        plan=read(package/"configs/phase3_combined_plan.json")
        validate_plan(plan)
        admissible_path(str(catalog))
        for suite in ("test_phase3_combined_plan.py", "test_phase3_j_heads.py",
                      "test_phase3_public_queue.py"):
            check=subprocess.run([sys.executable,"-B","-m","unittest","discover",
                "-s",str(package/"tests"),"-p",suite,"-v"],cwd=package,
                capture_output=True,text=True,timeout=300)
            if check.returncode:
                raise RuntimeError("combined target check failed ("+suite+"): "+check.stderr[-3000:])
        print("COMBINED_TARGET_CHECKS_PASSED",3)
        # A catalog may be prepared later, but any present one must obey the sealed-source rule.
        print("PUBLIC_CATALOG_STATUS",json.dumps(public_catalog_status(catalog),ensure_ascii=False))
        existing=sorted(records.glob("research_phase3_combined_*"))
        if existing:
            for directory in existing:
                print("EXISTING_COMBINED_NO_DUPLICATE",directory)
                if (directory/"queue_status.json").exists():
                    print((directory/"queue_status.json").read_text(encoding="utf-8"))
            return
        stamp=datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%dT%H%M%S")
        queue=records/f"research_phase3_combined_{stamp}_{os.getpid()}"
        queue.mkdir()
        for name in ("jobs","publication","temporary","cache/torch","cache/cuda",
                     "cache/triton","cache/kernels"):
            (queue/name).mkdir(parents=True)
        # Sources are frozen under this exact run, not fetched at training time.
        import shutil
        shutil.copytree(package,queue/"code")
        (queue/"plan.json").write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (queue/"registration.json").write_text(json.dumps({
            "execution_commit":args.commit,"catalog_source":str(catalog),
            "manifest_sha256":sha(download(args.commit,"configs/phase3_combined_execution_manifest.json")),
            "package_files":manifest["files"],"registered_at":stamp,
            "auto_retry":False,"test_release":False},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        with (queue/"nohup.log").open("x",encoding="utf-8") as output:
            process=subprocess.Popen([sys.executable,"-u","-B",
                str(queue/"code/scripts/control_phase3_combined.py"),"--directory",str(queue)],
                cwd=queue/"code",stdin=subprocess.DEVNULL,stdout=output,
                stderr=subprocess.STDOUT,start_new_session=True)
        print("COMBINED_REGISTERED",queue,"controller_pid",process.pid)


if __name__=="__main__":main()
