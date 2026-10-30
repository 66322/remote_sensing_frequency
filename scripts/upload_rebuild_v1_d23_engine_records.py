"""Publish only existing lightweight D23 admission evidence; no GPU/data access."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

BRANCH = "rebuild-v1-protocol-20260915"
REPO = "66322/remote_sensing_frequency"
FILES = ["cpu_checks.log", "gpu0/summary.json", "gpu0/preflight.json",
         "gpu0.log", "gpu1/summary.json", "gpu1/preflight.json", "gpu1.log"]

def digest(data):
    return hashlib.sha256(data).hexdigest()

def under(path, parent):
    path = path.resolve()
    path.relative_to(parent.resolve())
    return path

def git(cwd, *args, capture=False):
    # Authentication prompts remain in the terminal; never record them as evidence.
    return subprocess.run(["git", "-C", str(cwd), *args], check=True,
                          text=True, stdout=subprocess.PIPE if capture else None).stdout

def prepare(root, base, review):
    under(root, Path("/home/jovyan/zzx"))
    under(base, root / "records")
    under(review, base)
    if not re.fullmatch(r"research_d23_b_engine_admission_[A-Za-z0-9_]+", base.name):
        raise ValueError("unexpected admission directory")
    data = {}
    for name in FILES + [review.name]:
        path = under(base / name, base)
        if not path.is_file() or path.stat().st_size > 5 * 1024 * 1024:
            raise ValueError("missing or oversized light evidence: " + name)
        raw = path.read_bytes()
        raw.decode("utf-8")
        if name.endswith(".json"):
            json.loads(raw)
        data[name] = raw
    if sum(map(len, data.values())) > 20 * 1024 * 1024:
        raise ValueError("light evidence exceeds total budget")
    compact = json.loads(data[review.name])
    if Path(compact["server_directory"]).resolve() != base:
        raise ValueError("compact review belongs to another run")
    if digest(data["cpu_checks.log"]) != compact["cpu_checks"]["sha256"]:
        raise ValueError("CPU log changed after collection")
    if compact["cpu_checks"]["pass"] is not True:
        raise ValueError("CPU admission did not pass")
    for gpu, mode in ((0, "smoke"), (1, "profile")):
        key = str(gpu)
        row = compact["gpus"][key]
        summary = json.loads(data["gpu%d/summary.json" % gpu])
        pre = json.loads(data["gpu%d/preflight.json" % gpu])
        if digest(data["gpu%d/summary.json" % gpu]) != row["summary_sha256"]:
            raise ValueError("summary changed after collection")
        if digest(data["gpu%d/preflight.json" % gpu]) != row["preflight_sha256"]:
            raise ValueError("preflight changed after collection")
        if summary["signature"] != pre or row["signature"] != pre or pre["gpu"] != gpu:
            raise ValueError("device/source binding mismatch")
        if summary["status"] != "ENGINE_ADMISSION_COMPLETE" or summary["mode"] != mode:
            raise ValueError("incomplete engineering admission")
        if summary["formal_training_started"] is not False:
            raise ValueError("unexpected formal run")
    archive = dict(compact["archive"])
    archive_path = under(Path(archive["path"]), base)
    if not archive_path.is_file() or archive_path.stat().st_size != archive["bytes"]:
        raise ValueError("archive missing or size changed")
    h = hashlib.sha256()
    with archive_path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    if h.hexdigest() != archive["sha256"]:
        raise ValueError("archive hash changed")
    archive["uploaded"] = False
    return data, archive

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--directory", type=Path, required=True)
    ap.add_argument("--review", type=Path)
    args = ap.parse_args()
    root, base = args.root.resolve(), args.directory.resolve()
    reviews = sorted(base.glob("compact_review_*.json"))
    review = args.review.resolve() if args.review else (reviews[-1] if reviews else None)
    if review is None:
        raise ValueError("collect the existing records first")
    data, archive = prepare(root, base, review)
    origin = git(root, "remote", "get-url", "origin", capture=True).strip()
    if not re.search(r"github\.com[/:]66322/remote_sensing_frequency(?:\.git)?$", origin):
        raise ValueError("origin is not the authorized repository")
    git(root, "fetch", "origin", BRANCH)
    parent = git(root, "rev-parse", "FETCH_HEAD", capture=True).strip()
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%f") + "_" + str(os.getpid())
    worktree = under(base / ("github_upload_" + stamp), base)
    if worktree.exists():
        raise ValueError("upload snapshot already exists")
    git(root, "worktree", "add", "--detach", str(worktree), parent)
    relative = Path("records") / base.name / ("evidence_" + stamp)
    destination = worktree / relative
    destination.mkdir(parents=True, exist_ok=False)
    for name, raw in data.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as f:
            f.write(raw)
    manifest = {"kind": "EXISTING_LIGHT_EVIDENCE_UPLOAD",
                "created_at": datetime.now().astimezone().isoformat(),
                "server_directory": str(base), "upload_worktree": str(worktree),
                "branch": BRANCH, "base_commit": parent,
                "repository_directory": relative.as_posix(),
                "files": [{"path": name, "bytes": len(raw), "sha256": digest(raw)}
                          for name, raw in data.items()],
                "archive": archive, "new_training": False, "new_inference": False,
                "formal_runtime_admitted": False}
    with (destination / "upload_manifest.json").open("x", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    paths = [(relative / name).as_posix() for name in data] + [
        (relative / "upload_manifest.json").as_posix()]
    git(worktree, "add", "-f", "--", *paths)
    git(worktree, "-c", "user.name=66322",
        "-c", "user.email=57258129+66322@users.noreply.github.com",
        "commit", "-m", "records: upload existing D23 engine admission light evidence")
    commit = git(worktree, "rev-parse", "HEAD", capture=True).strip()
    # A concurrent update rejects the push; the recoverable commit stays in zzx.
    git(worktree, "push", "origin", "HEAD:refs/heads/" + BRANCH)
    print("D23_GITHUB_COMMIT=" + commit)
    print("D23_GITHUB_RECORDS=https://github.com/" + REPO + "/tree/" + commit + "/" + relative.as_posix())
    print("D23_UPLOAD_FILES=%d BYTES=%d" % (len(paths), sum(map(len, data.values()))))

if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print("UPLOAD_STOPPED: " + type(error).__name__ +
              "; existing evidence and any upload snapshot remain in the experiment directory.",
              file=sys.stderr)
        sys.exit(1)
