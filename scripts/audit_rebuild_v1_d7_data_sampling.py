import argparse
import csv
import json
import random
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import numpy as np
from scipy import ndimage
from skimage import io

import train_rebuild_v1_r02_budget_pilot as r02


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def label_path(data_root, tile):
    return data_root / "5_Labels_for_participants" / f"top_potsdam_{tile}_label.tif"


def load_gt(data_root, tile):
    path = label_path(data_root, tile)
    if not path.is_file():
        raise FileNotFoundError(path)
    return r02.convert_full_gt(io.imread(str(path))).astype(np.uint8, copy=False)


def component_areas(mask):
    labels, count = ndimage.label(mask, structure=np.ones((3, 3), dtype=np.uint8))
    if count == 0:
        return np.empty(0, dtype=np.int64)
    return np.bincount(labels.ravel())[1:].astype(np.int64, copy=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=20260922)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    cfg = r02.read_json(ROOT / "configs/rebuild_v1/r01_optical_only_16k.json")
    split = r02.read_json(ROOT / cfg["split_file"])
    train_ids = list(split["train16"])
    exposed = set(split["historical_exposed_test6"])
    if len(train_ids) != 16 or set(train_ids) & exposed:
        raise RuntimeError("Train16/Test6 split safety check failed")
    data_root = Path(cfg["data_root"])
    samples = 32 if args.smoke else args.samples
    ids = train_ids[:1] if args.smoke else train_ids
    out = args.out or ROOT / (
        "records/rebuild_v1_d7_data_sampling_smoke_20260922"
        if args.smoke else "records/rebuild_v1_d7_data_sampling_20260922"
    )
    out.mkdir(parents=True, exist_ok=True)

    cache = {}
    tile_rows, class_rows, component_rows = [], [], []
    total_counts = np.zeros(r02.N_CLASSES, dtype=np.int64)
    all_areas = {i: [] for i in range(r02.N_CLASSES)}
    for tile in ids:
        gt = load_gt(data_root, tile)
        cache[tile] = gt
        counts = np.bincount(gt.ravel(), minlength=r02.N_CLASSES)[: r02.N_CLASSES]
        total_counts += counts
        valid = int(counts.sum())
        for cls, name in enumerate(r02.CLASS_NAMES):
            areas = component_areas(gt == cls)
            all_areas[cls].append(areas)
            tile_rows.append({
                "tile": tile,
                "class_index": cls,
                "class_name": name,
                "pixels": int(counts[cls]),
                "pixel_fraction": float(counts[cls] / max(valid, 1)),
                "component_count": int(len(areas)),
                "component_area_median": float(np.median(areas)) if len(areas) else "",
            })

    valid_total = int(total_counts.sum())
    for cls, name in enumerate(r02.CLASS_NAMES):
        areas = np.concatenate(all_areas[cls]) if all_areas[cls] else np.empty(0)
        class_rows.append({
            "class_index": cls,
            "class_name": name,
            "pixels": int(total_counts[cls]),
            "pixel_fraction": float(total_counts[cls] / max(valid_total, 1)),
            "tiles_present": int(sum(r["pixels"] > 0 for r in tile_rows if r["class_index"] == cls)),
            "component_count": int(len(areas)),
        })
        if len(areas):
            component_rows.append({
                "class_index": cls,
                "class_name": name,
                "component_count": int(len(areas)),
                "area_q10": float(np.quantile(areas, 0.10)),
                "area_q25": float(np.quantile(areas, 0.25)),
                "area_median": float(np.quantile(areas, 0.50)),
                "area_q75": float(np.quantile(areas, 0.75)),
                "area_q90": float(np.quantile(areas, 0.90)),
                "area_max": int(areas.max()),
            })

    rng = random.Random(args.seed)
    patch = int(cfg["patch"])
    aug = cfg["augmentation"]
    crop_rows = []
    present = np.zeros(r02.N_CLASSES, dtype=np.int64)
    sampled_pixels = np.zeros(r02.N_CLASSES, dtype=np.int64)
    positive_pixels = {i: [] for i in range(r02.N_CLASSES)}
    scale_bins = Counter()
    for sample_id in range(samples):
        tile = rng.choice(ids)
        gt = cache[tile]
        scale = rng.uniform(float(aug["random_scale_min"]), float(aug["random_scale_max"]))
        source = max(1, min(int(round(patch / scale)), *gt.shape))
        y = rng.randint(0, gt.shape[0] - source)
        x = rng.randint(0, gt.shape[1] - source)
        crop = gt[y : y + source, x : x + source]
        counts = np.bincount(crop.ravel(), minlength=r02.N_CLASSES)[: r02.N_CLASSES]
        # Nearest-neighbour resizing preserves fractions closely; use expected output pixels.
        expected = np.rint(counts * (patch * patch / float(source * source))).astype(np.int64)
        sampled_pixels += expected
        present += counts > 0
        for cls in range(r02.N_CLASSES):
            if counts[cls] > 0:
                positive_pixels[cls].append(int(expected[cls]))
        scale_bins["0.5_1.0" if scale < 1 else "1.0_1.5" if scale < 1.5 else "1.5_2.0"] += 1
        if args.smoke or sample_id < 200:
            crop_rows.append({
                "sample_id": sample_id,
                "tile": tile,
                "scale": scale,
                "source_size": source,
                **{f"{r02.CLASS_NAMES[i]}_pixels": int(expected[i]) for i in range(r02.N_CLASSES)},
            })

    exposure_rows = []
    sampled_total = int(sampled_pixels.sum())
    for cls, name in enumerate(r02.CLASS_NAMES):
        positives = positive_pixels[cls]
        exposure_rows.append({
            "class_index": cls,
            "class_name": name,
            "crop_presence_fraction": float(present[cls] / samples),
            "crop_absence_fraction": float(1 - present[cls] / samples),
            "sampled_pixel_fraction": float(sampled_pixels[cls] / max(sampled_total, 1)),
            "positive_crop_pixels_median": float(np.median(positives)) if positives else 0.0,
            "positive_crop_pixels_q10": float(np.quantile(positives, 0.10)) if positives else 0.0,
        })

    fg = total_counts[:5]
    nonzero = fg[fg > 0]
    summary = {
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "experiment_id": "D7_DATA_SAMPLING_AUDIT",
        "smoke": args.smoke,
        "seed": args.seed,
        "samples": samples,
        "train_ids": ids,
        "historical_test6_loaded": False,
        "patch": patch,
        "scale_range": [aug["random_scale_min"], aug["random_scale_max"]],
        "foreground_max_min_pixel_ratio": float(nonzero.max() / nonzero.min()),
        "scale_bin_counts": dict(scale_bins),
        "component_size_bins_source": "Train16 FullGT connected components, 8-connectivity",
    }
    write_csv(out / "tile_class_statistics.csv", tile_rows)
    write_csv(out / "class_statistics.csv", class_rows)
    write_csv(out / "component_area_quantiles.csv", component_rows)
    write_csv(out / "crop_exposure.csv", exposure_rows)
    write_csv(out / "crop_sample_preview.csv", crop_rows)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("D7 DATA/SAMPLING AUDIT COMPLETE", out)


if __name__ == "__main__":
    main()
