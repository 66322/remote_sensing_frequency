"""Print a small read-only D9A score and stratum comparison for review."""

import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
BASE = ROOT / "records/rebuild_v1_d9a_summary_20260923"


def rows(name):
    with (BASE / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def compare(pairs):
    valid = [(a, b, n) for a, b, n in pairs if a is not None and b is not None]
    if not valid:
        return "none"
    auroc = [a[0] - b[0] for a, b, _ in valid]
    auprc = [a[1] - b[1] for a, b, _ in valid]
    return (f"n={len(valid)}; AUROC wins={sum(x > 0 for x in auroc)}, "
            f"mean Δ={sum(auroc)/len(auroc):+.4f}; "
            f"AUPRC wins={sum(x > 0 for x in auprc)}, "
            f"mean Δ={sum(auprc)/len(auprc):+.4f}; "
            f"min support={min(n for _, _, n in valid)}")


def value(row, stem):
    x, y = row[stem + "_benefit_auroc"], row[stem + "_benefit_auprc"]
    return None if not x or not y else (float(x), float(y))


def main():
    summary = rows("summary_table.csv")
    strata = rows("strata_table.csv")
    confidence = "confidence_margin"
    print("D9A direct scores vs confidence, 16 seed-condition rows")
    for candidate in ("entropy_margin", "class_agreement_margin", "confidence_times_js"):
        pairs = [(value(r, candidate), value(r, confidence), int(r["ranked_non_neutral"]))
                 for r in summary]
        print(candidate, compare(pairs))

    grouped = defaultdict(dict)
    for row in strata:
        grouped[(row["seed"], row["condition"], row["group"])][row["score"]] = row
    print("D9A confidence×JS vs confidence within strata")
    for group in ("class:Building", "class:Car", "class_size:Car:small", "region:damaged"):
        pairs = []
        for (seed, condition, found_group), scores in grouped.items():
            if found_group != group or set(scores) != {confidence, "confidence_times_js"}:
                continue
            a, b = scores["confidence_times_js"], scores[confidence]
            va = (float(a["benefit_auroc"]), float(a["benefit_auprc"])) if a["benefit_auroc"] and a["benefit_auprc"] else None
            vb = (float(b["benefit_auroc"]), float(b["benefit_auprc"])) if b["benefit_auroc"] and b["benefit_auprc"] else None
            pairs.append((va, vb, int(b["count"])))
        print(group, compare(pairs))
    print("Local damaged-region details (confidence and confidence×JS)")
    for (seed, condition, group), scores in sorted(grouped.items()):
        if group != "region:damaged":
            continue
        a, b = scores.get("confidence_times_js"), scores.get(confidence)
        if not a or not b:
            continue
        print(seed, condition, "n=" + b["count"],
              "conf=" + b["benefit_auroc"] + "/" + b["benefit_auprc"],
              "confJS=" + a["benefit_auroc"] + "/" + a["benefit_auprc"])


if __name__ == "__main__":
    main()
