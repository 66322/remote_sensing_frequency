#!/usr/bin/env python3
"""Read-only Vaihingen development-source audit. No model or Potsdam access."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np
import tifffile

from inspect_rebuild_v1_vaihingen_d10_metadata import header
from inventory_rebuild_v1_vaihingen_unused_metadata import ROOTS, USED_EVAL, USED_TRAIN

PROJECT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
DEFAULT_OUTPUT = PROJECT / "records/rebuild_v1_d20_vaihingen_content_20260928"
EXPECTED_IDS = (2, 4, 6, 8, 10, 12, 14, 16, 20, 22, 24, 27, 29, 31, 33, 35, 38)
PALETTE = {
    (255, 255, 255): "Impervious",
    (0, 0, 255): "Building",
    (0, 255, 255): "LowVegetation",
    (0, 255, 0): "Tree",
    (255, 255, 0): "Car",
    (255, 0, 0): "Clutter",
}


def tile_paths(root: Path, tile_id: int) -> dict[str, Path]:
    base = f"top_mosaic_09cm_area{tile_id}.tif"
    return {
        "optical": root / "top" / base,
        "dsm": root / "dsm" / f"dsm_09cm_matching_area{tile_id}.tif",
        "full_gt": root / "gts_complete" / base,
    }


def choose_paths(tile_id: int) -> tuple[dict[str, Path] | None, list[dict]]:
    choices = []
    for root in ROOTS:
        paths = tile_paths(root, tile_id)
        choices.append({"root": str(root), "present": {k: p.is_file() for k, p in paths.items()}})
        if all(p.is_file() for p in paths.values()):
            return paths, choices
    return None, choices


def sample_grid(array: np.ndarray, limit: int = 100_000) -> np.ndarray:
    pixels = array.shape[0] * array.shape[1]
    stride = max(1, math.ceil(math.sqrt(pixels / limit)))
    return array[::stride, ::stride]


def inspect_tile(tile_id: int) -> dict:
    paths, choices = choose_paths(tile_id)
    row = {"id": tile_id, "historical_status": "unused_id_same_mosaic_development_only",
           "path_choices": choices, "paths": None, "checks": {}, "errors": []}
    if paths is None:
        row["errors"].append("No single allowed root contains the exact TOP/DSM/gts_complete trio")
        return row
    row["paths"] = {k: str(v) for k, v in paths.items()}
    row["headers"] = {k: header(str(v)) for k, v in paths.items()}
    try:
        optical = tifffile.imread(paths["optical"])
        optical_shape = optical.shape
        row["optical"] = {"shape": list(optical_shape), "dtype": str(optical.dtype),
                          "sample_minmax_per_band": []}
        if optical.ndim == 3 and optical.shape[2] >= 3:
            small = sample_grid(optical[..., :3])
            row["optical"]["sample_minmax_per_band"] = [
                [float(small[..., c].min()), float(small[..., c].max())] for c in range(3)
            ]
        del optical

        dsm = tifffile.imread(paths["dsm"])
        dsm_shape = dsm.shape
        dsm_sample = sample_grid(dsm)
        finite = np.isfinite(dsm_sample)
        row["dsm"] = {"shape": list(dsm_shape), "dtype": str(dsm.dtype),
                      "sample_count": int(dsm_sample.size),
                      "sample_nonfinite": int((~finite).sum()),
                      "sample_minmax": [float(dsm_sample[finite].min()),
                                        float(dsm_sample[finite].max())] if finite.any() else None}
        del dsm, dsm_sample

        labels = tifffile.imread(paths["full_gt"])
        gt_shape = labels.shape
        row["full_gt"] = {"shape": list(gt_shape), "dtype": str(labels.dtype),
                          "sample_colors": {}, "sample_unknown_count": None}
        if labels.ndim == 3 and labels.shape[2] >= 3:
            small = sample_grid(labels[..., :3]).reshape(-1, 3)
            colors, counts = np.unique(small, axis=0, return_counts=True)
            found = {tuple(map(int, color)): int(count)
                     for color, count in zip(colors, counts)}
            row["full_gt"]["sample_colors"] = {
                ",".join(map(str, color)): {"class": PALETTE.get(color), "count": count}
                for color, count in found.items()
            }
            row["full_gt"]["sample_unknown_count"] = sum(
                count for color, count in found.items() if color not in PALETTE
            )
        del labels

        same_grid = optical_shape[:2] == dsm_shape[:2] == gt_shape[:2]
        header_values = list(row["headers"].values())
        georef_known = all(h.get("georeferenced") for h in header_values)
        if georef_known:
            first = header_values[0]
            georef_match = all(h.get("crs") == first.get("crs") and
                               h.get("bounds") == first.get("bounds") for h in header_values[1:])
        else:
            georef_match = None
        row["checks"] = {
            "same_pixel_shape": same_grid,
            "top_has_at_least_three_bands": len(optical_shape) == 3 and optical_shape[2] >= 3,
            "dsm_one_band": len(dsm_shape) == 2,
            "full_gt_rgb_palette_sample_recognized": (
                len(gt_shape) == 3 and gt_shape[2] >= 3 and
                row["full_gt"]["sample_unknown_count"] == 0
            ),
            "dsm_sample_finite": row["dsm"]["sample_nonfinite"] == 0,
            "geographic_header_alignment": georef_match,
        }
    except Exception as exc:
        row["errors"].append(f"{type(exc).__name__}: {exc}")
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    allowed = Path("/home/jovyan/zzx").resolve()
    if output != allowed and allowed not in output.parents:
        raise SystemExit(f"Output must remain under {allowed}: {output}")
    output.mkdir(parents=True, exist_ok=True)
    rows = [inspect_tile(tile_id) for tile_id in EXPECTED_IDS]
    ready = [r for r in rows if not r["errors"] and
             all(value is True for key, value in r["checks"].items()
                 if key != "geographic_header_alignment") and
             r["checks"].get("geographic_header_alignment") is not False]
    status = "CONTENT_SAMPLE_CHECKS_PASS_DEVELOPMENT_ONLY" if len(ready) == len(rows) else "REVIEW_REQUIRED"
    result = {
        "schema_version": "1.0", "created_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": status, "scope": "Vaihingen same-mosaic development source",
        "roots": [str(r) for r in ROOTS], "expected_ids": list(EXPECTED_IDS),
        "previously_used_train_ids": sorted(USED_TRAIN), "previously_used_eval_ids": sorted(USED_EVAL),
        "label_choice": "Exact gts_complete/top_mosaic_09cm_area<ID>.tif; noBoundary excluded",
        "optical_band_meaning": ["near infrared", "red", "green"],
        "sample_limit_per_tile": 100_000,
        "ready_development_ids": [r["id"] for r in ready], "tiles": rows,
        "limits": ["Pixel sample does not prove every label pixel belongs to the palette",
                   "Matching dimensions without georeferencing do not prove geographic alignment",
                   "Same-mosaic scenes and past use preclude independent final confirmation",
                   "No fit/dev/final split or D20 GPU training is authorized by this audit"],
        "gpu_used": False, "potsdam_test6_loaded": False,
    }
    (output / "audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (output / "tiles.tsv").open("w", encoding="utf-8") as stream:
        stream.write("id\tready_development\tfull_gt_path\tsame_pixel_shape\tgeographic_header_alignment\tunknown_colors_sample\terrors\n")
        for r in rows:
            stream.write("\t".join([str(r["id"]), str(r["id"] in result["ready_development_ids"]),
                (r["paths"] or {}).get("full_gt", ""), str(r["checks"].get("same_pixel_shape")),
                str(r["checks"].get("geographic_header_alignment")),
                str(r.get("full_gt", {}).get("sample_unknown_count")), " | ".join(r["errors"])]) + "\n")
    print(json.dumps({"status": status, "ready_development_ids": result["ready_development_ids"],
                      "review_ids": [r["id"] for r in rows if r["id"] not in result["ready_development_ids"]],
                      "record": str(output / "audit.json")}, ensure_ascii=False))
    return 0 if status.startswith("CONTENT_SAMPLE_CHECKS_PASS") else 2


if __name__ == "__main__":
    sys.exit(main())
