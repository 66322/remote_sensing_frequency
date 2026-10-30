#!/usr/bin/env python3
"""Extract PP4k/PH4k per-class GSD curves from the saved E51-B summary.

No model inference is performed. This script only reads the existing JSON and
writes compact CSV summaries that make the same-step class behavior explicit.

The historical summary contains a stale human-readable PP10k label, but its
result keys/checkpoint fields for this directory are PP4k/PH4k. This script
validates those checkpoint steps before producing output.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "records" / "e51b_gsd_same_step_pp4k_ph4k_20260914"
SRC_JSON = SRC_DIR / "summary.json"
OUT_DIR = ROOT / "records" / "e51b_same_step_per_class_summary_20260915"

CLASS_NAMES = [
    "Impervious",
    "Building",
    "LowVegetation",
    "Tree",
    "Car",
    "Clutter",
]

SPLITS = ["full", "noboundary"]


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"No rows for {path}")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if not SRC_JSON.is_file():
        raise FileNotFoundError(SRC_JSON)

    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    results = data["results"]
    target_gsds = [float(x) for x in data["target_gsds_m"]]

    per_class_rows: list[dict] = []
    overall_rows: list[dict] = []

    for gsd_m in target_gsds:
        pp_key = f"PP4k_{gsd_m:.2f}"
        ph_key = f"PH4k_{gsd_m:.2f}"

        if pp_key not in results or ph_key not in results:
            raise KeyError(
                f"Missing same-step result at {gsd_m:.2f} m: "
                f"need {pp_key} and {ph_key}"
            )

        pp = results[pp_key]
        ph = results[ph_key]

        pp_step = int(pp["checkpoint_step"])
        ph_step = int(ph["checkpoint_step"])
        if pp_step != 4000 or ph_step != 4000:
            raise RuntimeError(
                f"Not a PP4k/PH4k pair at {gsd_m:.2f} m: "
                f"PP={pp_step}, PH={ph_step}"
            )

        for split in SPLITS:
            pp_split = pp[split]
            ph_split = ph[split]

            overall_rows.append(
                {
                    "target_gsd_cm": gsd_m * 100.0,
                    "split": split,
                    "pp_checkpoint_step": pp_step,
                    "ph_checkpoint_step": ph_step,
                    "PP4k_OA": pp_split["OA"],
                    "PH4k_OA": ph_split["OA"],
                    "PH_minus_PP_OA_pp": 100.0
                    * (float(ph_split["OA"]) - float(pp_split["OA"])),
                    "PP4k_mF1_fg5": pp_split["mF1_fg5"],
                    "PH4k_mF1_fg5": ph_split["mF1_fg5"],
                    "PH_minus_PP_mF1_fg5_pp": 100.0
                    * (
                        float(ph_split["mF1_fg5"])
                        - float(pp_split["mF1_fg5"])
                    ),
                    "PP4k_mIoU_fg5": pp_split["mIoU_fg5"],
                    "PH4k_mIoU_fg5": ph_split["mIoU_fg5"],
                    "PH_minus_PP_mIoU_fg5_pp": 100.0
                    * (
                        float(ph_split["mIoU_fg5"])
                        - float(pp_split["mIoU_fg5"])
                    ),
                }
            )

            pp_iou = list(pp_split["per_class_iou"])
            ph_iou = list(ph_split["per_class_iou"])
            if len(pp_iou) != len(CLASS_NAMES) or len(ph_iou) != len(CLASS_NAMES):
                raise RuntimeError(
                    f"Unexpected class count at {gsd_m:.2f} m / {split}"
                )

            for class_index, class_name in enumerate(CLASS_NAMES):
                p = float(pp_iou[class_index])
                h = float(ph_iou[class_index])
                per_class_rows.append(
                    {
                        "target_gsd_cm": gsd_m * 100.0,
                        "split": split,
                        "class_index": class_index,
                        "class_name": class_name,
                        "PP4k_IoU": p,
                        "PH4k_IoU": h,
                        "PH_minus_PP_IoU_pp": 100.0 * (h - p),
                    }
                )

    write_csv(OUT_DIR / "overall_curves.csv", overall_rows)
    write_csv(OUT_DIR / "per_class_iou_curves.csv", per_class_rows)

    metadata = {
        "source": str(SRC_JSON.relative_to(ROOT)),
        "interpretation": "strict same-step PP4k vs PH4k",
        "note": (
            "Historical summary.json contains a stale PP10k comparison_note; "
            "checkpoint_step and result keys are validated as PP4k/PH4k here."
        ),
        "target_gsds_m": target_gsds,
        "splits": SPLITS,
        "classes": CLASS_NAMES,
    }
    (OUT_DIR / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"[PASS] source: {SRC_JSON}")
    print(f"[PASS] overall: {OUT_DIR / 'overall_curves.csv'}")
    print(f"[PASS] per-class: {OUT_DIR / 'per_class_iou_curves.csv'}")
    print(f"[PASS] metadata: {OUT_DIR / 'metadata.json'}")


if __name__ == "__main__":
    main()
