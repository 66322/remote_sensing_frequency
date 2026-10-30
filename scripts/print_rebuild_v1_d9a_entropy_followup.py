"""Read existing D9A/D5 outputs to separate ranking from routed mIoU."""

import csv
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
SUMMARY = ROOT / "records/rebuild_v1_d9a_summary_20260923"
GROUPS = ("class:Building", "class:Car", "class_size:Car:small", "region:damaged")
CONDITIONS = ("clean", "dsm_zero", "dsm_down8", "dsm_local_zero_q1",
              "dsm_local_down8_q1")


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def by_key(rows, keys):
    out = {}
    for row in rows:
        key = tuple(row[k] for k in keys)
        if key in out:
            raise RuntimeError(f"duplicate row {key}")
        out[key] = row
    return out


def mean(xs):
    return sum(xs) / len(xs) if xs else None


def main():
    summary = read_rows(SUMMARY / "summary_table.csv")
    print("D9A entropy-margin vs confidence-margin by seed and condition")
    print("seed condition ΔAUROC ΔAUPRC non-neutral-support")
    for row in summary:
        da = float(row["entropy_margin_benefit_auroc"]) - float(row["confidence_margin_benefit_auroc"])
        dp = float(row["entropy_margin_benefit_auprc"]) - float(row["confidence_margin_benefit_auprc"])
        print(row["seed"], row["condition"], f"{da:+.4f}", f"{dp:+.4f}",
              row["ranked_non_neutral"])

    print("D9A entropy-margin vs confidence-margin within strata")
    print("group comparisons AUROC-wins mean-ΔAUROC AUPRC-wins mean-ΔAUPRC min-support")
    for group in GROUPS:
        da, dp, support = [], [], []
        for seed in (42, 17):
            for condition in (r["condition"] for r in summary if r["seed"] == str(seed)):
                path = ROOT / f"records/rebuild_v1_d9a_seed{seed}_{condition}_20260923/ranking_metrics.csv"
                rows = by_key(read_rows(path), ("tile", "group", "score", "neutral_ce"))
                key = ("ALL", group, "entropy_margin", "0.01")
                control = ("ALL", group, "confidence_margin", "0.01")
                if key not in rows or control not in rows:
                    continue
                a, b = rows[key], rows[control]
                if not a["benefit_auroc"] or not b["benefit_auroc"]:
                    continue
                da.append(float(a["benefit_auroc"]) - float(b["benefit_auroc"]))
                dp.append(float(a["benefit_auprc"]) - float(b["benefit_auprc"]))
                support.append(int(a["count"]))
        if da:
            print(group, len(da), sum(v > 0 for v in da), f"{mean(da):+.4f}",
                  sum(v > 0 for v in dp), f"{mean(dp):+.4f}", min(support))
        else:
            print(group, "none")

    print("Existing D5 NoBoundary mIoU (%) — routing outcome, not benefit ranking")
    print("seed condition R01 R05 min_entropy safe_max_confidence")
    for seed in (42, 17):
        path = ROOT / f"records/rebuild_v1_d5_confidence_routing_seed{seed}_20260920/method_metrics.csv"
        if not path.is_file():
            print(seed, "D5 original metrics missing:", path)
            continue
        rows = by_key(read_rows(path), ("condition", "method", "split"))
        for condition in CONDITIONS:
            values = []
            for method in ("R01_optical", "R05_dual", "min_entropy", "safe_max_confidence"):
                row = rows.get((condition, method, "noboundary"))
                values.append(f"{100*float(row['mIoU_fg5']):.4f}" if row else "NA")
            print(seed, condition, *values)


if __name__ == "__main__":
    main()
