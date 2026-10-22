"""Immutable stage enumeration and read-only admission checks for the combined queue."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
STAGES = ("M2", "J", "R", "T", "V")
SEEDS = (42, 17)
FOLDS = ("F0", "F1", "F2")
J_ARMS = ("J1", "J2", "J3", "J4", "J5", "J6", "J7")
R_ARMS = ("concat_joint", "conditional_joint", "conditional_joint_aux")
T_ARMS = ("plain", "nuisance_aug", "robust_preprocess", "hard_correspondence", "soft_no_match")
V_ARMS = ("rgb_only", "ordinary_fusion", "rgb_relation", "rgb_geometry_relation", "shuffled_geometry")
FORBIDDEN = ("val2", "test6", "held4", "final")


def read(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def admissible_path(path: str, root: Path = Path("/home/jovyan/zzx")) -> Path:
    value = Path(path)
    if not value.is_absolute():
        raise ValueError("absolute source path required")
    if any(part.lower() in FORBIDDEN or part.lower() == "test" for part in value.parts):
        raise ValueError("held-out or forbidden data path")
    resolved = value.resolve()
    resolved.relative_to(root.resolve())
    if any(part.lower() in FORBIDDEN or part.lower() == "test" for part in resolved.parts):
        raise ValueError("held-out or forbidden resolved data path")
    if value.is_symlink() or any(parent.is_symlink() for parent in value.parents
                                 if parent != root and root in parent.parents):
        raise ValueError("symlinked input refused")
    return resolved


def jobs(stage: str):
    if stage not in ("J", "R", "T", "V"):
        raise ValueError(stage)
    arms = {"J": J_ARMS, "R": R_ARMS, "T": T_ARMS, "V": V_ARMS}[stage]
    return [
        {"id": f"{stage}_{fold}_s{seed}_{arm}", "stage": stage, "fold": fold,
         "seed": seed, "arm": arm}
        for fold in FOLDS for seed in SEEDS for arm in arms
    ]


def validate_plan(plan):
    def require(condition, message):
        if not condition:
            raise RuntimeError("combined plan contract: " + message)
    require(plan["schema_version"] == 1, "schema")
    require(plan["root"] == ROOT.as_posix(), "root")
    require(len(plan["m2_execution_commit"]) == 40, "M2 immutable commit")
    require(plan["physical_gpus"] == [0, 1], "GPU0/1 only")
    require(plan["seeds"] == list(SEEDS) and plan["folds"] == list(FOLDS), "fold/seed")
    require([(s["id"], s["jobs"], s["updates_per_job"]) for s in plan["stages"]] == [
        ("M2", 108, 32000), ("J", 42, 8000), ("R", 18, 32000),
        ("T", 30, 12000), ("V", 30, 12000)], "stage budgets")
    require(plan["no_automatic_retry"] and plan["no_automatic_seed_addition"], "retry/seed")
    require(not plan["release_test_enabled"] and not plan["new_data_test_split_enabled"], "test sealed")
    require(plan["no_automatic_B_or_C"], "M2 B/C sealed")
    require(sum(s["jobs"] for s in plan["stages"]) == 228, "job count")
    require(sum(s["jobs"] * s["updates_per_job"] for s in plan["stages"]) == 5088000,
            "update count")
    for stage in ("J", "R", "T", "V"):
        values = jobs(stage)
        require(len(values) == len({x["id"] for x in values}), "unique " + stage)
    return True


def public_catalog_status(catalog_path: Path | None, root: Path = Path("/home/jovyan/zzx")):
    """Read metadata only; never download or read sealed evaluation pixels."""
    if catalog_path is None or not catalog_path.exists():
        return {"ready": False, "reason": "catalog absent"}
    catalog_path = admissible_path(str(catalog_path), root)
    data = read(catalog_path)
    if data.get("schema_version") != 1:
        raise ValueError("catalog schema")
    result = {}
    for dataset in ("3DCD", "P3"):
        rows = data.get("datasets", {}).get(dataset, {}).get("development", [])
        groups = {str(row.get("group")) for row in rows}
        if not rows or len(groups) != 3 or "None" in groups:
            result[dataset] = {"ready": False, "reason": "three development groups required"}
            continue
        if dataset == "P3" and groups != {"CH", "NY", "NZ"}:
            result[dataset] = {"ready": False, "reason": "P3 development groups must be CH/NY/NZ"}
            continue
        if len({str(row.get("id")) for row in rows}) != len(rows) or any("id" not in row for row in rows):
            raise ValueError("missing/duplicate public-data id")
        metadata = data.get("datasets", {}).get(dataset, {}).get("metadata", {})
        required_metadata = ("dsm_units_to_meters", "change2d_positive_values",
                             "change2d_negative_values", "change3d_ignore_values",
                             "change3d_scale_m", "change3d_offset_m",
                             "pixel_grid_alignment_verified") if dataset == "3DCD" else ("allow_empty_tiles",)
        if any(field not in metadata for field in required_metadata):
            result[dataset] = {"ready": False, "reason": "explicit label/unit metadata required"}
            continue
        if dataset == "3DCD":
            if (not isinstance(metadata["pixel_grid_alignment_verified"], bool) or
                not metadata["pixel_grid_alignment_verified"] or
                any(not isinstance(metadata[key], (int, float)) for key in
                    ("dsm_units_to_meters", "change3d_scale_m", "change3d_offset_m")) or
                any(not isinstance(metadata[key], list) or
                    any(not isinstance(v, int) for v in metadata[key]) for key in
                    ("change2d_positive_values", "change2d_negative_values", "change3d_ignore_values")) or
                set(metadata["change2d_positive_values"]) & set(metadata["change2d_negative_values"])):
                result[dataset] = {"ready": False, "reason": "3DCD label coding/alignment not verified"}
                continue
        elif not isinstance(metadata["allow_empty_tiles"], bool):
            result[dataset] = {"ready": False, "reason": "P3 empty-tile contract must be bool"}
            continue
        fields = ("rgb_t1", "rgb_t2", "dsm_t1", "dsm_t2", "change2d", "change3d") if dataset == "3DCD" else ("rgb", "lidar", "instance")
        missing = []
        for row in rows:
            if row.get("split") != "development":
                raise ValueError("test/validation entry in development catalog")
            if dataset == "P3" and not isinstance(row.get("image_id"), int):
                missing.append(f"{row.get('id')}:image_id")
            for field in fields:
                if field not in row:
                    missing.append(f"{row.get('id')}:{field}")
                elif not admissible_path(row[field], root).is_file():
                    missing.append(f"{row.get('id')}:{field}")
        result[dataset] = {"ready": not missing, "samples": len(rows), "groups": sorted(groups),
                           "missing": missing[:10]}
    return result
