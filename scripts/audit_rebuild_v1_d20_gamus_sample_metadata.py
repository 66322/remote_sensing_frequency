#!/usr/bin/env python3
"""Inspect the nine already downloaded GAMUS samples for provenance metadata."""

import hashlib
import json
from pathlib import Path
import re

import h5py


PROJECT = Path(__file__).resolve().parents[1]
SOURCE_AUDIT = PROJECT / "records/rebuild_v1_d20_gamus_source_acceptance_compact_20260928/audit.json"
DATA_ROOT = Path("/home/jovyan/zzx/datasets/rebuild_v1_d20_gamus").resolve()
OUTPUT = PROJECT / "records/rebuild_v1_d20_gamus_sample_metadata_20260928/audit.json"
GEO_KEY = re.compile(r"crs|epsg|geo|spatial|coordinate|projection|transform|affine|origin|bounds|extent|source|license", re.I)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def scalar(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")[:256]
    if isinstance(value, (str, int, float, bool)):
        return value if not isinstance(value, str) else value[:256]
    if hasattr(value, "shape") and value.shape == ():
        return scalar(value.item())
    if hasattr(value, "size") and value.size <= 16:
        return [scalar(item) for item in value.flat]
    return {"type": type(value).__name__, "shape": list(getattr(value, "shape", ())), "value_omitted": True}


def attributes(group):
    return {str(key): scalar(group.attrs[key]) for key in sorted(group.attrs)}


def main():
    source = json.loads(SOURCE_AUDIT.read_text(encoding="utf-8"))
    assert source["status"] == "SAMPLE_CONTENT_PASS_SOURCE_ACCEPTANCE_PENDING"
    result = {
        "status": "SAMPLE_METADATA_INSPECTED_SOURCE_ACCEPTANCE_PENDING",
        "source_audit": str(SOURCE_AUDIT.relative_to(PROJECT)).replace("\\", "/"),
        "dataset_revision": source["revision"],
        "scope": "nine_existing_HDF5_samples_only_no_download_no_training",
        "files": [],
    }
    for sample in source["samples"]:
        for modality in ("images", "heights", "classes"):
            expected = sample["triplet"][modality]
            path = (DATA_ROOT / expected["relative_path"]).resolve()
            path.relative_to(DATA_ROOT)
            if not path.is_file() or path.stat().st_size != expected["bytes"]:
                raise RuntimeError(f"missing or size-changed sample: {path}")
            if digest(path) != expected["sha256"]:
                raise RuntimeError(f"SHA-256 changed since Stage A: {path}")
            with h5py.File(path, "r") as handle:
                if "image" not in handle or not isinstance(handle["image"], h5py.Dataset):
                    raise RuntimeError(f"missing image dataset: {path}")
                dataset = handle["image"]
                root_attrs = attributes(handle)
                image_attrs = attributes(dataset)
                result["files"].append({
                    "city": sample["city"],
                    "modality": modality,
                    "relative_path": expected["relative_path"],
                    "sha256": expected["sha256"],
                    "root_keys": sorted(handle.keys()),
                    "root_attributes": root_attrs,
                    "image_shape": list(dataset.shape),
                    "image_dtype": str(dataset.dtype),
                    "image_attributes": image_attrs,
                    "possible_geo_or_source_attribute_keys": sorted(
                        key for key in set(root_attrs) | set(image_attrs) if GEO_KEY.search(key)
                    ),
                })
    assert len(result["files"]) == 9
    result["files_with_possible_geo_or_source_attributes"] = sum(
        bool(item["possible_geo_or_source_attribute_keys"]) for item in result["files"]
    )
    result["interpretation_limit"] = (
        "Attribute-key inspection cannot prove geographic alignment or identify original rights; "
        "absence of a key in these nine samples does not establish absence in all files."
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".json.partial")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    temporary.rename(OUTPUT)
    print("status:", result["status"])
    print("files:", len(result["files"]))
    print("files_with_possible_geo_or_source_attributes:", result["files_with_possible_geo_or_source_attributes"])
    print("output:", OUTPUT)


if __name__ == "__main__":
    main()
