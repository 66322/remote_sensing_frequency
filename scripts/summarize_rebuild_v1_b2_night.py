"""Collect completed evaluation outputs only; no selection or success gate by score."""
import argparse
import csv
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path

from rebuild_v1_b2_common import ROOT


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    if rows:
        with Path(path).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", type=Path, required=True)
    args = ap.parse_args()
    out = args.queue.resolve()
    out.relative_to((ROOT / "records").resolve())
    all_rows, family_rows, inputs = [], [], []
    for d in sorted(out.glob("*_REGIONS")):
        if not (d / "summary.json").is_file():
            continue
        s = json.loads((d / "summary.json").read_text(encoding="utf-8"))
        if s.get("status") != "COMPLETE" or s.get("smoke") is not False:
            continue
        rows = [r for r in read_csv(d / "region_metrics.csv") if r["tile"] == "ALL"]
        for r in rows:
            r["checkpoint_step"] = s["checkpoint_step"]
            r["checkpoint_sha256"] = s["checkpoint"]["sha256"]
        all_rows.extend(rows)
        groups = defaultdict(list)
        for r in rows:
            if r["mIoU_fg5"] and math.isfinite(float(r["mIoU_fg5"])):
                groups[(r["model"], r["family"], r["split"], r["region"])].append(float(r["mIoU_fg5"]))
        for key, values in groups.items():
            family_rows.append(dict(zip(("model", "family", "split", "region"), key),
                                    condition_count=len(values), mean_mIoU_fg5=sum(values)/len(values),
                                    worst_mIoU_fg5=min(values)))
        inputs.append(str(d))
    write_csv(out / "morning_all_regions.csv", all_rows)
    write_csv(out / "morning_family_summary.csv", family_rows)
    index = {(r["model"], r["condition"], r["split"], r["region"]): r for r in all_rows}
    deltas = []
    for a, b in (("KD", "C"), ("SAFE", "KD"), ("R05_KD", "C"),
                 ("AVG_KD", "C"), ("AVG_KD", "KD"), ("R05_KD", "KD")):
        for key, row in index.items():
            if key[0] != a:
                continue
            other = index.get((b, *key[1:]))
            if not other or not row["mIoU_fg5"] or not other["mIoU_fg5"]:
                continue
            deltas.append(dict(candidate=a, reference=b, condition=key[1], split=key[2],
                               region=key[3], delta_mIoU_fg5_pp=100*(float(row["mIoU_fg5"])-float(other["mIoU_fg5"]))))
    write_csv(out / "morning_deltas.csv", deltas)
    checks = []
    for label, old_dir in (
        ("C", "rebuild_v1_b1_c_robust_eval_20260920"),
        ("KD", "rebuild_v1_b1_kd_robust_eval_20260920"),
        ("SAFE", "rebuild_v1_b1_safe_robust_eval_20260920")):
        old_csv = ROOT / "records" / old_dir / "dataset_metrics.csv"
        if not old_csv.is_file():
            checks.append(dict(model=label, status="NOT_CHECKED", detail="original CSV unavailable"))
            continue
        for old in read_csv(old_csv):
            key = (label, old["condition"], old["split"], "whole")
            new = index.get(key)
            if new:
                diff = float(new["mIoU_fg5"]) - float(old["mIoU_fg5"])
                checks.append(dict(model=label, status="PASS" if abs(diff) < 1e-7 else "REVIEW",
                                   detail=f"{key}: delta={diff}"))
    write_csv(out / "reproduction_checks.csv", checks)
    notes = [
        "# Morning handoff",
        "",
        "Material Passport: prepared/collected computational artifacts; Val2 development evidence only.",
        "No test6 access. No automatic best-method selection. Missing/failed arms are not zero scores.",
        "Family means give equal weight to conditions, not pixels. Report the families separately.",
        "Regional IoU uses pooled tile confusion matrices. Absent-class IoU is NA (existing fg5 convention).",
        "Boundary is the synthetic fault interface, not a semantic class boundary; it overlaps other regions.",
        "Confidence diagnostics must be read jointly with coverage; fixed thresholds are not matched coverage.",
        "See status.tsv for all failures and skips, reproduction_checks.csv for baseline consistency.",
        "Completed evaluation directories: " + ", ".join(inputs),
    ]
    (out / "MORNING_README.md").write_text("\n".join(notes)+"\n", encoding="utf-8")
    print("MORNING_REPORT", out, "completed_evaluations=", len(inputs))


if __name__ == "__main__":
    main()

