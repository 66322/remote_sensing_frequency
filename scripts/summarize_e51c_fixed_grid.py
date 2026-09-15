import csv
import json
import argparse
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
DEFAULT_IN = (
    ROOT
    / "records"
    / "e51c_fixed_grid_information_degradation_20260915"
    / "progress.json"
)

CLASS_NAMES = [
    "Impervious",
    "Building",
    "LowVegetation",
    "Tree",
    "Car",
    "Clutter",
]


def write_csv(path, rows):
    if not rows:
        print(f"[WARN] no rows for {path.name}")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"[PASS] {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_IN)
    args = parser.parse_args()

    if not args.input.is_file():
        raise FileNotFoundError(args.input)

    with open(args.input, "r", encoding="utf-8") as f:
        progress = json.load(f)

    out = args.input.parent

    # Index complete PP/PH pairs.
    groups = sorted(
        {
            (r["modality"], float(r["information_loss_factor"]))
            for r in progress.values()
        }
    )

    # Native-grid clean reference (factor 1.0) for corruption-drop calculations.
    clean = {}
    for modality, factor in groups:
        if abs(factor - 1.0) > 1e-12:
            continue
        for model in ("PP4k", "PH4k"):
            key = f"{model}__{modality}__x{factor:.4f}"
            if key in progress:
                clean[(modality, model)] = progress[key]

    paired_dataset = []
    paired_per_class = []
    paired_per_tile = []

    for modality, factor in groups:
        pp_key = f"PP4k__{modality}__x{factor:.4f}"
        ph_key = f"PH4k__{modality}__x{factor:.4f}"
        if pp_key not in progress or ph_key not in progress:
            continue

        pp = progress[pp_key]
        ph = progress[ph_key]

        pp_tiles = {x["tile_id"]: x for x in pp["per_tile"]}
        ph_tiles = {x["tile_id"]: x for x in ph["per_tile"]}

        for split in ("full", "noboundary"):
            ppm = pp[split]
            phm = ph[split]

            pp_clean = clean.get((modality, "PP4k"))
            ph_clean = clean.get((modality, "PH4k"))

            if pp_clean is not None:
                pp_drop = 100.0 * (
                    pp_clean[split]["mIoU_fg5"] - ppm["mIoU_fg5"]
                )
            else:
                pp_drop = None

            if ph_clean is not None:
                ph_drop = 100.0 * (
                    ph_clean[split]["mIoU_fg5"] - phm["mIoU_fg5"]
                )
            else:
                ph_drop = None

            robustness_advantage = (
                None
                if pp_drop is None or ph_drop is None
                else pp_drop - ph_drop
            )

            paired_dataset.append(
                {
                    "modality": modality,
                    "information_loss_factor": factor,
                    "split": split,
                    "PP4k_mIoU_fg5": ppm["mIoU_fg5"],
                    "PH4k_mIoU_fg5": phm["mIoU_fg5"],
                    "PH_minus_PP_mIoU_fg5_pp": 100.0
                    * (phm["mIoU_fg5"] - ppm["mIoU_fg5"]),
                    "PP4k_drop_from_clean_pp": pp_drop,
                    "PH4k_drop_from_clean_pp": ph_drop,
                    "PH_robustness_advantage_pp": robustness_advantage,
                    "PP4k_OA": ppm["OA"],
                    "PH4k_OA": phm["OA"],
                    "PH_minus_PP_OA_pp": 100.0 * (phm["OA"] - ppm["OA"]),
                    "PP_valid_pixels": ppm["valid_pixels"],
                    "PH_valid_pixels": phm["valid_pixels"],
                }
            )

            for class_idx, class_name in enumerate(CLASS_NAMES):
                pp_iou = ppm["per_class_iou"][class_idx]
                ph_iou = phm["per_class_iou"][class_idx]
                delta = (
                    None
                    if pp_iou is None or ph_iou is None
                    else 100.0 * (ph_iou - pp_iou)
                )
                paired_per_class.append(
                    {
                        "modality": modality,
                        "information_loss_factor": factor,
                        "split": split,
                        "class_index": class_idx,
                        "class_name": class_name,
                        "PP4k_IoU": pp_iou,
                        "PH4k_IoU": ph_iou,
                        "PH_minus_PP_IoU_pp": delta,
                        "PP_union_pixels": ppm["per_class_union"][class_idx],
                        "PH_union_pixels": phm["per_class_union"][class_idx],
                    }
                )

            for tile_id in sorted(set(pp_tiles) & set(ph_tiles)):
                ppt = pp_tiles[tile_id][split]
                pht = ph_tiles[tile_id][split]
                paired_per_tile.append(
                    {
                        "modality": modality,
                        "information_loss_factor": factor,
                        "split": split,
                        "tile_id": tile_id,
                        "PP4k_mIoU_fg5": ppt["mIoU_fg5"],
                        "PH4k_mIoU_fg5": pht["mIoU_fg5"],
                        "PH_minus_PP_mIoU_fg5_pp": 100.0
                        * (pht["mIoU_fg5"] - ppt["mIoU_fg5"]),
                        "PP_n_available_fg5": ppt["n_available_fg5"],
                        "PH_n_available_fg5": pht["n_available_fg5"],
                        "PP_valid_pixels": ppt["valid_pixels"],
                        "PH_valid_pixels": pht["valid_pixels"],
                    }
                )

    write_csv(out / "paired_dataset_extended.csv", paired_dataset)
    write_csv(out / "paired_per_class.csv", paired_per_class)
    write_csv(out / "paired_per_tile.csv", paired_per_tile)

    print()
    print(f"[PASS] complete pairs summarized: {len(paired_dataset)} dataset split rows")
    if not clean:
        print("[WARN] no factor=1.0 pair found; drop-from-clean columns remain empty")


if __name__ == "__main__":
    main()
