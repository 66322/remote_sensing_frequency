"""Acquire and inventory the authors' DFC19 archive; never open raster pixels.

The SynRS3D authors link DFC19.zip at the Google Drive ID below. Download and
all resulting records stay under /home/jovyan/zzx. This is source feasibility,
not an accepted D10 split or permission to train on historical Test6.
"""

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath

DATA_ROOT = Path("/home/jovyan/zzx/datasets/rebuild_v1_d10_dfc19")
ARCHIVE = DATA_ROOT / "DFC19.zip"
REPORT = DATA_ROOT / "archive_inventory.json"
SOURCE_URL = "https://drive.google.com/file/d/1eoF16sxIHOQ5928SrboMqbi686sfKFLF/view?usp=sharing"
SOURCE_PAGE = "https://github.com/JTRNEO/SynRS3D#real-world-elevation-datasets"
ROLES = {"opt", "gt_nDSM", "gt_ss_mask"}


def safe_member(name):
    posix = PurePosixPath(name.replace("\\", "/"))
    return bool(posix.parts) and not posix.is_absolute() and ".." not in posix.parts and ":" not in posix.parts[0]


def classify(name):
    parts = PurePosixPath(name.replace("\\", "/")).parts
    if Path(parts[-1]).suffix.lower() not in (".tif", ".tiff"):
        return None
    for index, part in enumerate(parts[:-1]):
        if part in ROLES:
            return part, Path(parts[-1]).stem
    return None


def inspect_archive():
    if not ARCHIVE.is_file():
        raise FileNotFoundError(ARCHIVE)
    digest = hashlib.sha256()
    with ARCHIVE.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    by_role = defaultdict(set)
    examples = defaultdict(list)
    unsafe = []
    names = []
    with zipfile.ZipFile(ARCHIVE) as archive:
        members = archive.infolist()
        for member in members:
            if not safe_member(member.filename):
                unsafe.append(member.filename)
                continue
            if member.is_dir():
                continue
            names.append(member.filename)
            matched = classify(member.filename)
            if matched:
                role, stem = matched
                by_role[role].add(stem)
                if len(examples[role]) < 3:
                    examples[role].append(member.filename)
    common = set.intersection(*(by_role[role] for role in ROLES)) if all(by_role[role] for role in ROLES) else set()
    report = {
        "source_page": SOURCE_PAGE,
        "source_archive_url": SOURCE_URL,
        "archive": str(ARCHIVE),
        "archive_size_bytes": ARCHIVE.stat().st_size,
        "archive_sha256": digest.hexdigest(),
        "member_count": len(members),
        "unsafe_member_count": len(unsafe),
        "unsafe_member_examples": unsafe[:5],
        "role_file_counts": {role: len(by_role[role]) for role in sorted(ROLES)},
        "role_examples": dict(examples),
        "matching_triplet_stem_count": len(common),
        "matching_triplet_stem_examples": sorted(common)[:20],
        "other_member_examples": [n for n in names if classify(n) is None][:20],
        "raster_pixels_read": False,
        "test6_loaded": False,
        "source_accepted_for_d10": False,
        "next_gate": "Check geographic IDs, masks/class codes, alignment, access terms and scene-disjoint partitions before extracting or training."
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if unsafe:
        raise RuntimeError("archive contains unsafe member paths; no extraction performed")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="Download official-author-linked DFC19.zip if absent")
    args = parser.parse_args()
    if not str(DATA_ROOT.resolve()).startswith("/home/jovyan/zzx/"):
        raise RuntimeError("runtime data path must stay under /home/jovyan/zzx")
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    if args.download:
        try:
            import gdown
        except ImportError as exc:
            raise RuntimeError("gdown is required for --download; install it under /home/jovyan/zzx, then retry") from exc
        free_gib = shutil.disk_usage(DATA_ROOT).free / (1024 ** 3)
        print(f"available_disk_GiB={free_gib:.1f} source={SOURCE_URL}", flush=True)
        result = gdown.download(SOURCE_URL, str(ARCHIVE), quiet=False,
                                resume=True, use_cookies=False)
        if result != str(ARCHIVE) or not ARCHIVE.is_file():
            raise RuntimeError("download did not produce the expected archive")
    report = inspect_archive()
    if not all(report["role_file_counts"].values()):
        print("WARNING: expected opt/gt_nDSM/gt_ss_mask folders were not all identified; inspect archive layout before extraction", file=sys.stderr)


if __name__ == "__main__":
    main()
