"""Compact morning summary for the prespecified B4 seed17 replication."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

from rebuild_v1_b2_common import ROOT

LABELS = ("C17", "R05_KD17", "KD17")


def rows(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write(path, data):
    if data:
        with Path(path).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    root.relative_to((ROOT / "records").resolve())
    robust_rows, pair_rows = [], []
    missing = []
    for label in LABELS:
        robust = root / (label + "_ROBUST") / "dataset_metrics.csv"
        paired = root / (label + "_PAIRED") / "paired_metrics.csv"
        if not robust.is_file() or not paired.is_file():
            missing.append(label)
            continue
        selected = {r["condition"]: 100 * float(r["mIoU_fg5"])
                    for r in rows(robust) if r["split"] == "noboundary"
                    and r["condition"] in ("clean", "dsm_down8", "dsm_zero")}
        robust_rows.append({"model": label, **selected})
        groups = defaultdict(list)
        for r in rows(paired):
            if r["tile"] == "ALL" and r["split"] == "noboundary" and r["region"] in ("damaged", "boundary"):
                groups[(r["family"], r["region"])].append(100 * float(r["delta_mIoU_fg5"]))
        for (family, region), values in sorted(groups.items()):
            pair_rows.append({"model": label, "family": family, "region": region,
                              "condition_count": len(values),
                              "mean_delta_mIoU_fg5_pp": sum(values) / len(values),
                              "worst_delta_mIoU_fg5_pp": min(values)})
    if missing:
        print("B4_SUMMARY_INCOMPLETE missing=" + ",".join(missing))
        return 2
    write(root / "b4_global_summary.csv", robust_rows)
    write(root / "b4_paired_summary.csv", pair_rows)
    print("B4_SEED17_SUMMARY_COMPLETE", root)
    print("GLOBAL NB mIoU_fg5 (%)")
    for r in robust_rows:
        print(r["model"], *(f"{k}={r[k]:.4f}" for k in ("clean", "dsm_down8", "dsm_zero")))
    print("LOCAL corrupt-clean NB mIoU_fg5 (pp; descriptive quadrant mean)")
    for r in pair_rows:
        print(r["model"], r["family"], r["region"],
              f"mean={r['mean_delta_mIoU_fg5_pp']:+.4f}",
              f"worst={r['worst_delta_mIoU_fg5_pp']:+.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
