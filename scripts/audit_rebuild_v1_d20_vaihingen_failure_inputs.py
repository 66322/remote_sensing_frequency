#!/usr/bin/env python3
"""CPU-only, read-only audit of all Vaihingen development tiles after the frozen gate failed."""

import hashlib
import json
from pathlib import Path
import time

import numpy as np
import tifffile

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rebuild_v1/d20_vaihingen_formal_seed42_20260928.json"
ARCHIVE = ROOT / "records/rebuild_v1_d20_vaihingen_seed42_compact_20260928"
RAW = ROOT / "records/rebuild_v1_d20_vaihingen_seed42_20260928"
OUT = ROOT / "records/rebuild_v1_d20_vaihingen_failure_inputs_20260928"
PALETTE = ((255, 255, 255), (0, 0, 255), (0, 255, 255),
           (0, 255, 0), (255, 255, 0), (255, 0, 0))
CLASS_NAMES = ("Impervious", "Building", "LowVegetation", "Tree", "Car", "Clutter")
GEO_TAGS = (33550, 33922, 34264, 34735, 34736, 34737)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def full_labels(rgb):
    if rgb.ndim != 3 or rgb.shape[2] < 3 or rgb.dtype != np.uint8:
        raise RuntimeError(f"unexpected label dimensions/dtype: {rgb.shape}, {rgb.dtype}")
    out = np.full(rgb.shape[:2], 255, dtype=np.uint8)
    for index, color in enumerate(PALETTE):
        out[np.all(rgb[..., :3] == color, axis=2)] = index
    if np.any(out == 255):
        raise RuntimeError(f"unrecognized full-label colors: {int(np.sum(out == 255))}")
    return out


def boundary(label):
    edge = np.zeros(label.shape, dtype=bool)
    dy = label[1:, :] != label[:-1, :]
    dx = label[:, 1:] != label[:, :-1]
    edge[1:, :] |= dy
    edge[:-1, :] |= dy
    edge[:, 1:] |= dx
    edge[:, :-1] |= dx
    return edge


def building_edge_enrichment(values, building):
    bx = building[:, 1:] != building[:, :-1]
    by = building[1:, :] != building[:-1, :]
    dx = np.abs(values[:, 1:] - values[:, :-1])
    dy = np.abs(values[1:, :] - values[:-1, :])
    count = int(bx.sum() + by.sum())
    if not count:
        return None
    at_boundary = float((dx[bx].sum(dtype=np.float64) + dy[by].sum(dtype=np.float64)) / count)
    global_mean = float((dx.sum(dtype=np.float64) + dy.sum(dtype=np.float64)) / (dx.size + dy.size))
    return dict(building_boundary_pixel_pairs=count, gradient_mean_at_building_boundary=at_boundary,
                gradient_mean_global=global_mean,
                boundary_enrichment_ratio=at_boundary / global_mean if global_mean > 0 else None)


def geotiff_tags(path):
    with tifffile.TiffFile(path) as tif:
        tags = tif.pages[0].tags
        return [key for key in GEO_TAGS if key in tags]


def tile_paths(data_root, tile, label_dir):
    name = f"top_mosaic_09cm_area{tile}.tif"
    return {"top": data_root / "top" / name,
            "dsm": data_root / "dsm" / f"dsm_09cm_matching_area{tile}.tif",
            "label": data_root / label_dir / name}


def main():
    cfg = read(CONFIG)
    decision = read(ARCHIVE / "decision.json")
    manifest = read(ARCHIVE / "input_manifest.json")
    evaluation = {arm: read(ARCHIVE / f"{arm}_eval_summary.json") for arm in ("P0", "P2")}
    if decision["status"] != "COMPLETE" or decision["passed"] is not False:
        raise RuntimeError("this diagnostic applies only to the completed failed gate")
    if cfg["development_ids"] != decision["development_ids"] or manifest["development_ids"] != cfg["development_ids"]:
        raise RuntimeError("development split binding mismatch")
    data_root = Path(cfg["data_root"]).resolve()
    data_root.relative_to(Path("/home/jovyan/zzx").resolve())
    if any(evaluation[arm]["signature"]["training"]["input_manifest_sha256"] != sha(ARCHIVE / "input_manifest.json")
           for arm in evaluation):
        raise RuntimeError("evaluation/manifest binding mismatch")
    start = time.monotonic()
    rows = []
    for tile in cfg["development_ids"]:
        paths = tile_paths(data_root, tile, cfg["development_label_directory"])
        for name, path in paths.items():
            recorded = manifest["files"].get(str(path))
            if not path.is_file() or recorded is None or path.stat().st_size != recorded["size"] or sha(path) != recorded["sha256"]:
                raise RuntimeError(f"raw input differs from frozen manifest: tile {tile} {name}")
        top = tifffile.imread(paths["top"])
        dsm = tifffile.imread(paths["dsm"])
        gt = full_labels(tifffile.imread(paths["label"]))
        if top.ndim != 3 or top.shape[2] != 3 or top.dtype != np.uint8 or dsm.ndim != 2:
            raise RuntimeError(f"unexpected TOP/DSM format: tile {tile}")
        if not (top.shape[:2] == dsm.shape == gt.shape) or not np.isfinite(dsm).all():
            raise RuntimeError(f"shape/nonfinite failure: tile {tile}")
        predictions = {}
        for arm in ("P0", "P2"):
            path = RAW / arm / "clean" / f"tile_{tile}.npy"
            expected = evaluation[arm]["conditions"]["clean"]["tiles"][str(tile)]["prediction_sha256"]
            if not path.is_file() or sha(path) != expected:
                raise RuntimeError(f"clean prediction changed: {arm} tile {tile}")
            predictions[arm] = np.load(path, allow_pickle=False)
            if predictions[arm].shape != gt.shape or predictions[arm].dtype != np.uint8:
                raise RuntimeError(f"prediction shape/dtype mismatch: {arm} tile {tile}")
        correct0 = predictions["P0"] == gt
        correct2 = predictions["P2"] == gt
        rescue = correct2 & ~correct0
        harm = correct0 & ~correct2
        edge = boundary(gt)
        # Near-boundary is a fixed four-pixel Manhattan neighborhood.
        near = edge.copy()
        for _ in range(4):
            expanded = near.copy()
            expanded[1:, :] |= near[:-1, :]
            expanded[:-1, :] |= near[1:, :]
            expanded[:, 1:] |= near[:, :-1]
            expanded[:, :-1] |= near[:, 1:]
            near = expanded
        class_counts = np.bincount(gt.ravel(), minlength=6)
        class_paired = {}
        for index, name in enumerate(CLASS_NAMES):
            where = gt == index
            class_paired[name] = dict(support=int(class_counts[index]),
                                      p2_only_correct=int(np.count_nonzero(rescue & where)),
                                      p0_only_correct=int(np.count_nonzero(harm & where)))
        archived = decision["paired_by_tile"][str(tile)]["clean"]["P0"]
        if int(rescue.sum()) != archived["only_p2_correct"] or int(harm.sum()) != archived["only_control_correct"]:
            raise RuntimeError(f"clean paired counts differ from archived result: tile {tile}")
        if (sum(item["support"] for item in class_paired.values()) != gt.size or
                sum(item["p2_only_correct"] for item in class_paired.values()) != archived["only_p2_correct"] or
                sum(item["p0_only_correct"] for item in class_paired.values()) != archived["only_control_correct"]):
            raise RuntimeError(f"per-class partition differs from archived result: tile {tile}")
        paired_by_location = {
            "within_4px_of_label_boundary": dict(pixels=int(near.sum()),
                p2_only_correct=int(np.count_nonzero(rescue & near)),
                p0_only_correct=int(np.count_nonzero(harm & near))),
            "interior": dict(pixels=int((~near).sum()),
                p2_only_correct=int(np.count_nonzero(rescue & ~near)),
                p0_only_correct=int(np.count_nonzero(harm & ~near)))}
        if (sum(item["pixels"] for item in paired_by_location.values()) != gt.size or
                sum(item["p2_only_correct"] for item in paired_by_location.values()) != archived["only_p2_correct"] or
                sum(item["p0_only_correct"] for item in paired_by_location.values()) != archived["only_control_correct"]):
            raise RuntimeError(f"boundary partition differs from archived result: tile {tile}")
        dsm = dsm.astype(np.float32, copy=False)
        optical_mean = top.astype(np.float32).mean(axis=2) / 255.0
        row = dict(tile=tile, failed_gate=tile in (12, 14), pixels=int(gt.size),
            input_paths={name: str(path) for name, path in paths.items()},
            shape=list(gt.shape), geotiff_spatial_tag_ids={name: geotiff_tags(path) for name, path in paths.items()},
            optical_band_mean=[float(top[..., k].mean()) for k in range(3)],
            optical_zero_fraction=[float(np.mean(top[..., k] == 0)) for k in range(3)],
            optical_255_fraction=[float(np.mean(top[..., k] == 255)) for k in range(3)],
            dsm_min=float(dsm.min()), dsm_max=float(dsm.max()),
            dsm_p01=float(np.percentile(dsm, 1)), dsm_p50=float(np.percentile(dsm, 50)),
            dsm_p99=float(np.percentile(dsm, 99)),
            class_paired=class_paired,
            paired_by_location=paired_by_location,
            dsm_building_edge=building_edge_enrichment(dsm, gt == 1),
            optical_building_edge=building_edge_enrichment(optical_mean, gt == 1))
        rows.append(row)
        print(f"AUDIT tile={tile} failed_gate={row['failed_gate']} rescue={int(rescue.sum())} harm={int(harm.sum())}", flush=True)
    result = dict(status="COMPLETE", scope="exploratory_read_only_input_and_prediction_diagnostic",
                  frozen_gate_passed=False, frozen_gate_unchanged=True,
                  config_sha256=sha(CONFIG), decision_sha256=sha(ARCHIVE / "decision.json"),
                  manifest_sha256=sha(ARCHIVE / "input_manifest.json"),
                  source_sha256=sha(Path(__file__)), development_ids=cfg["development_ids"],
                  target_failure_ids=[12, 14], comparison_population="all_17_frozen_development_tiles",
                  gpu_used=False, model_training_started=False, test6_loaded=False,
                  geographic_alignment_status="cannot_be_proven_from_equal_shape_or_edge_enrichment_alone",
                  limitations="Edge enrichment is descriptive; it cannot establish registration accuracy or the cause of a negative model delta",
                  elapsed_seconds=round(time.monotonic() - start, 2), tiles=rows)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with (OUT / "tiles.tsv").open("w", encoding="utf-8", newline="") as f:
        f.write("tile\tfailed_gate\tpixels\tdsm_min\tdsm_max\tdsm_building_edge_ratio\toptical_building_edge_ratio\tnear_rescue\tnear_harm\tinterior_rescue\tinterior_harm\n")
        for row in rows:
            near = row["paired_by_location"]["within_4px_of_label_boundary"]
            interior = row["paired_by_location"]["interior"]
            def ratio(field):
                value = row[field]
                return "" if value is None or value["boundary_enrichment_ratio"] is None else str(value["boundary_enrichment_ratio"])
            f.write(f"{row['tile']}\t{row['failed_gate']}\t{row['pixels']}\t{row['dsm_min']}\t{row['dsm_max']}\t{ratio('dsm_building_edge')}\t{ratio('optical_building_edge')}\t{near['p2_only_correct']}\t{near['p0_only_correct']}\t{interior['p2_only_correct']}\t{interior['p0_only_correct']}\n")
    print("D20 VAIHINGEN FAILURE INPUT AUDIT COMPLETE", len(rows), flush=True)


if __name__ == "__main__":
    main()
