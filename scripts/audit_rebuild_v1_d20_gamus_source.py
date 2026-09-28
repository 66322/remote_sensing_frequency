#!/usr/bin/env python3
"""CPU-only Stage-A audit of author-linked revised GAMUS metadata and nine sample files."""

import collections
import hashlib
import json
import os
from pathlib import Path
import re
import time
import urllib.request

import h5py
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ZZX = Path("/home/jovyan/zzx")
DATA = ZZX / "datasets/rebuild_v1_d20_gamus"
RECORD = ROOT / "records/rebuild_v1_d20_gamus_source_acceptance_20260928"
REPO = "earthflow/GAMUS"
REVISION = "a3c0e2511f06d909612406f436cf8abb4da805f5"
API = f"https://huggingface.co/api/datasets/{REPO}"
SPLITS = ("train", "val", "test")
MODALITIES = ("images", "heights", "classes")
SAMPLES = {
    "DC": ("train", "DC_01_25"),
    "PHL": ("train", "PHL_6148"),
    "NYC": ("test", "NYC_17683"),
}
SUFFIX = {"images": {"DC": "RGB", "PHL": "RGB", "NYC": "IMG"},
          "heights": {"DC": "AGL", "PHL": "AGL", "NYC": "AGL"},
          "classes": {"DC": "CLS", "PHL": "CLS", "NYC": "CLS"}}
HEADERS = {"User-Agent": "Codex-D20-GAMUS-source-acceptance"}


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=40) as response:
        return json.load(response), response.headers.get("Link", "")


def tree(modality, split):
    # The Hub tree API returns LFS metadata by default. expand=true rejects
    # page sizes above 100 with HTTP 400, so use the default 1000-item pages.
    url = f"{API}/tree/{REVISION}/{modality}/{split}?limit=1000"
    items = []
    while url:
        page, link = get_json(url)
        items.extend(x for x in page if x.get("type") == "file")
        match = re.search(r'<([^>]+)>; rel="next"', link)
        url = match.group(1) if match else None
    return items


def base(filename):
    suffix = filename.rsplit("_", 1)[-1]
    if suffix not in ("RGB.h5", "IMG.h5", "AGL.h5", "CLS.h5"):
        raise RuntimeError(f"unexpected GAMUS filename suffix: {filename}")
    return filename.rsplit("_", 1)[0]


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(relative, expected_size, expected_sha):
    target = DATA / relative
    target.resolve().relative_to(DATA.resolve())
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file():
        if target.stat().st_size != expected_size or sha(target) != expected_sha:
            raise RuntimeError(f"existing sample differs from pinned Hub metadata: {target}")
        return target
    url = f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/{relative}"
    temporary = target.with_name(target.name + ".partial")
    if temporary.exists():
        raise RuntimeError(f"partial sample exists; inspect before retry: {temporary}")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=90) as src, temporary.open("xb") as dst:
            while True:
                block = src.read(1024 * 1024)
                if not block:
                    break
                dst.write(block)
                if dst.tell() > 16 * 1024 * 1024:
                    raise RuntimeError(f"sample exceeded 16 MiB transfer cap: {relative}")
        if temporary.stat().st_size != expected_size or sha(temporary) != expected_sha:
            raise RuntimeError(f"sample size/SHA differs from pinned Hub metadata: {relative}")
        os.replace(temporary, target)
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise
    return target


def h5_info(path):
    with h5py.File(path, "r") as f:
        if "image" not in f or not isinstance(f["image"], h5py.Dataset):
            raise RuntimeError(f"expected HDF5 image dataset absent: {path}")
        values = f["image"][()]
    if not np.issubdtype(values.dtype, np.number):
        raise RuntimeError(f"non-numeric HDF5 image dataset: {path}")
    info = {"shape": list(values.shape), "dtype": str(values.dtype),
            "finite": bool(np.isfinite(values).all()),
            "min": float(np.min(values)), "max": float(np.max(values))}
    if path.parent.parent.name == "classes":
        unique, counts = np.unique(values, return_counts=True)
        info["class_counts"] = {str(int(key)): int(value) for key, value in zip(unique, counts)}
    return info


def main():
    started = time.monotonic()
    DATA.resolve().relative_to(ZZX.resolve())
    RECORD.resolve().relative_to(ZZX.resolve())
    repository, _ = get_json(f"{API}/revision/{REVISION}")
    if repository["sha"] != REVISION or repository["private"] or repository["gated"]:
        raise RuntimeError("author-linked public GAMUS revision unavailable")
    license_tag = repository.get("cardData", {}).get("license")
    inventories = {}
    entry_by_path = {}
    for modality in MODALITIES:
        inventories[modality] = {}
        for split in SPLITS:
            entries = tree(modality, split)
            identifiers = [base(Path(row["path"]).name) for row in entries]
            if len(identifiers) != len(set(identifiers)):
                raise RuntimeError(f"duplicate GAMUS identifiers: {modality}/{split}")
            cities = collections.Counter(value.split("_", 1)[0] for value in identifiers)
            inventories[modality][split] = {"files": len(entries), "cities": dict(sorted(cities.items()))}
            entry_by_path.update({row["path"]: row for row in entries})
            inventories[modality][split]["identifiers"] = identifiers
            print("METADATA", modality, split, len(entries), dict(cities), flush=True)
    for split in SPLITS:
        if any(set(inventories["images"][split]["identifiers"]) !=
               set(inventories[modality][split]["identifiers"]) for modality in MODALITIES[1:]):
            raise RuntimeError(f"RGB/height/class metadata pairs differ: {split}")
    samples = []
    for city, (split, stem) in SAMPLES.items():
        triplet = {}
        for modality in MODALITIES:
            relative = f"{modality}/{split}/{stem}_{SUFFIX[modality][city]}.h5"
            entry = entry_by_path.get(relative)
            if entry is None or "lfs" not in entry:
                raise RuntimeError(f"pinned GAMUS sample metadata missing: {relative}")
            expected_size = int(entry["lfs"]["size"])
            expected_sha = entry["lfs"]["oid"]
            path = download(relative, expected_size, expected_sha)
            triplet[modality] = {"path": str(path), "relative_path": relative,
                                 "bytes": expected_size, "sha256": expected_sha,
                                 "content": h5_info(path)}
        spatial = triplet["images"]["content"]["shape"][:2]
        good = (len(triplet["images"]["content"]["shape"]) == 3 and
                triplet["images"]["content"]["shape"][2] == 3 and
                triplet["heights"]["content"]["shape"] == spatial and
                triplet["classes"]["content"]["shape"] == spatial and
                all(item["content"]["finite"] for item in triplet.values()) and
                set(map(int, triplet["classes"]["content"]["class_counts"])) <= set(range(7)))
        samples.append({"city": city, "split": split, "stem": stem, "content_pass": bool(good),
                        "triplet": triplet})
        print("SAMPLE", city, "content_pass", good, flush=True)
    counts = {modality: {split: {key: value for key, value in inventories[modality][split].items()
                                      if key != "identifiers"} for split in SPLITS}
              for modality in MODALITIES}
    result = {
        "status": "SAMPLE_CONTENT_PASS_SOURCE_ACCEPTANCE_PENDING" if all(x["content_pass"] for x in samples)
                  else "SAMPLE_CONTENT_REVIEW_REQUIRED",
        "scope": "author_linked_revised_GAMUS_stage_a_three_city_metadata_and_one_triplet_per_city",
        "repository": REPO, "revision": REVISION, "hub_license_tag": license_tag,
        "license_conclusion": "metadata_tag_only_underlying_source_rights_and_provenance_require_review",
        "official_author_repo": "https://github.com/EarthNets/RSI-MMSegmentation",
        "removed_DFC2019_JAX_OMA_per_author_repo": True,
        "inventory": counts, "metadata_pairing_all_splits": True,
        "provided_splits_mix_cities": True,
        "split_conclusion": "new_geographically_separated_fit_dev_final_split_required_before_training",
        "samples": samples, "sample_count": len(samples),
        "gpu_used": False, "training_started": False, "potsdam_test6_loaded": False,
        "elapsed_seconds": round(time.monotonic() - started, 2),
    }
    RECORD.mkdir(parents=True, exist_ok=True)
    (RECORD / "audit.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("COMPACT DECISION", result["status"], "samples", len(samples), flush=True)


if __name__ == "__main__":
    main()
