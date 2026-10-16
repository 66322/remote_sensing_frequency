import csv
import json
from datetime import datetime
from pathlib import Path


ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
R05 = ROOT / "records/rebuild_v1_r05_local_failure_diagnostics_20260918"
CONTROL = ROOT / "records/rebuild_v1_c_oo_qd_local_failure_diagnostics_20260918"
OUT = ROOT / "records/rebuild_v1_local_failure_comparison_20260918"


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_rows(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def mean(values):
    return sum(values) / len(values) if values else None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    r05 = {
        (r["condition"], r["split"]): r
        for r in read_rows(R05 / "dataset_metrics.csv")
    }
    control = {
        (r["condition"], r["split"]): r
        for r in read_rows(CONTROL / "dataset_metrics.csv")
    }
    if set(r05) != set(control):
        raise RuntimeError("R05 and C-OO-QD diagnostic condition sets differ")

    comparison = []
    for key in sorted(r05):
        a, b = r05[key], control[key]
        comparison.append({
            "condition": a["condition"],
            "family": a["family"],
            "split": a["split"],
            "r05_mIoU_fg5": float(a["mIoU_fg5"]),
            "control_mIoU_fg5": float(b["mIoU_fg5"]),
            "r05_minus_control_pp": 100.0 * (float(a["mIoU_fg5"]) - float(b["mIoU_fg5"])),
            "r05_drop_from_clean_pp": float(a["drop_from_clean_mIoU_fg5_pp"]),
            "control_drop_from_clean_pp": float(b["drop_from_clean_mIoU_fg5_pp"]),
        })
    write_rows(OUT / "paired_condition_comparison.csv", comparison)

    nb = [r for r in comparison if r["split"] == "noboundary"]
    families = sorted({r["family"] for r in nb})
    family_rows = []
    for family in families:
        rows = [r for r in nb if r["family"] == family]
        family_rows.append({
            "family": family,
            "condition_count": len(rows),
            "mean_r05_minus_control_pp": mean([r["r05_minus_control_pp"] for r in rows]),
            "mean_r05_drop_from_clean_pp": mean([r["r05_drop_from_clean_pp"] for r in rows]),
            "mean_control_drop_from_clean_pp": mean([r["control_drop_from_clean_pp"] for r in rows]),
        })
    write_rows(OUT / "family_summary.csv", family_rows)

    shift_rows = [r for r in nb if r["family"] == "D2_misalignment"]
    monotonic = {}
    for direction in ("up", "down", "left", "right"):
        ordered = []
        for pixels in (2, 4, 8):
            name = f"dsm_shift_{direction}_{pixels}px"
            ordered.append(next(r["r05_drop_from_clean_pp"] for r in shift_rows if r["condition"] == name))
        monotonic[direction] = {
            "drops_pp_at_2_4_8": ordered,
            "nondecreasing": ordered[0] <= ordered[1] <= ordered[2],
        }

    down8 = [r for r in nb if r["family"] == "D3_local_down8"]
    local_zero = [r for r in nb if r["family"] == "D1_local_missing"]
    decision = {
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "historical_test6_loaded": False,
        "r05_local_down8_advantage_mean_pp": mean([r["r05_minus_control_pp"] for r in down8]),
        "r05_local_missing_drop_mean_pp": mean([r["r05_drop_from_clean_pp"] for r in local_zero]),
        "r05_local_down8_drop_mean_pp": mean([r["r05_drop_from_clean_pp"] for r in down8]),
        "r05_shift_drop_mean_pp": mean([r["r05_drop_from_clean_pp"] for r in shift_rows]),
        "shift_monotonic_by_direction": monotonic,
        "all_shift_directions_monotonic": all(v["nondecreasing"] for v in monotonic.values()),
        "interpretation_rule": {
            "local_reliability": "supported when local failures cause material loss and R05 retains a positive local-down8 advantage over C-OO-QD",
            "alignment_module": "supported when shift loss is material and nondecreasing in most or all directions",
            "fallback_only": "preferred when spatial patterns are weak or inconsistent",
        },
    }
    with open(OUT / "decision_evidence.json", "w", encoding="utf-8") as f:
        json.dump(decision, f, indent=2, ensure_ascii=False)
    print(json.dumps(decision, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
