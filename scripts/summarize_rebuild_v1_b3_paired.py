"""Summarize B3 paired diagnostics without treating pixels/quadrants as replicates."""
import argparse
import csv
import json
from pathlib import Path

from rebuild_v1_b2_common import ROOT


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    if rows:
        with Path(path).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    root = (ROOT / args.root).resolve()
    root.relative_to((ROOT / "records").resolve())
    rows = []
    for summary in sorted(root.glob("*/summary.json")):
        meta = json.loads(summary.read_text(encoding="utf-8"))
        if meta.get("status") != "COMPLETE" or meta.get("test6_loaded") is not False:
            raise RuntimeError("Incomplete/unsafe evaluation: " + str(summary.parent))
        rows.extend(read_csv(summary.parent / "paired_metrics.csv"))
    if not rows:
        raise RuntimeError("No completed paired evaluations found")
    write_csv(root / "all_paired_metrics.csv", rows)

    selected = [r for r in rows if r["tile"] == "ALL" and r["split"] == "noboundary"]
    family_rows = []
    for model in sorted({r["model"] for r in selected}):
        for family in ("D1_local_missing", "D3_local_down8"):
            for region in ("whole", "damaged", "intact", "boundary"):
                group = [r for r in selected if r["model"] == model and r["family"] == family and r["region"] == region]
                if len(group) != 4:
                    raise RuntimeError(f"Expected four quadrant conditions: {model} {family} {region}")
                deltas = [100 * float(r["delta_mIoU_fg5"]) for r in group]
                family_rows.append({
                    "model": model, "family": family, "split": "noboundary", "region": region,
                    "conditions": len(group), "mean_delta_mIoU_fg5_pp": sum(deltas) / len(deltas),
                    "worst_delta_mIoU_fg5_pp": min(deltas), "best_delta_mIoU_fg5_pp": max(deltas),
                    "interpretation": "descriptive repeated-condition summary; not four independent replicates",
                })
    write_csv(root / "paired_family_summary.csv", family_rows)
    print("B3_PAIRED_SUMMARY_COMPLETE", root)
    for row in family_rows:
        if row["region"] in ("damaged", "boundary"):
            print(row["model"], row["family"], row["region"],
                  f"mean_delta={row['mean_delta_mIoU_fg5_pp']:+.4f} pp",
                  f"worst={row['worst_delta_mIoU_fg5_pp']:+.4f} pp")


if __name__ == "__main__":
    main()
