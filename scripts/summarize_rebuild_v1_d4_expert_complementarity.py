import csv
import json
from datetime import datetime
from pathlib import Path


ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
OUT = ROOT / "records/rebuild_v1_d4_expert_complementarity_summary_20260920"
SEEDS = (42, 17)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def mean(values):
    return sum(values) / len(values) if values else None


def get_metric(rows, condition, method):
    row = next(
        r for r in rows
        if r["condition"] == condition
        and r["method"] == method
        and r["split"] == "noboundary"
    )
    return 100.0 * float(row["mIoU_fg5"])


def region_mean(rows, family, method, region="damaged"):
    values = [
        100.0 * float(r["mIoU_fg5"])
        for r in rows
        if r["family"] == family
        and r["method"] == method
        and r["split"] == "noboundary"
        and r["region"] == region
    ]
    return mean(values)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    seed_evidence = {}
    table = []
    for seed in SEEDS:
        source = ROOT / f"records/rebuild_v1_d4_expert_complementarity_seed{seed}_20260920"
        metrics = read_csv(source / "method_metrics.csv")
        regions = read_csv(source / "region_metrics.csv")
        agreement = read_csv(source / "prediction_agreement.csv")

        conditions = sorted({r["condition"] for r in metrics if r["split"] == "noboundary"})
        oracle_headrooms = []
        for condition in conditions:
            r01 = get_metric(metrics, condition, "R01_optical")
            r05 = get_metric(metrics, condition, "R05_dual")
            rule = get_metric(metrics, condition, "condition_rule")
            oracle = get_metric(metrics, condition, "pixel_oracle")
            headroom = oracle - max(r01, r05)
            oracle_headrooms.append(headroom)
            table.append({
                "seed": seed,
                "condition": condition,
                "R01_optical_mIoU_fg5_pp": r01,
                "R05_dual_mIoU_fg5_pp": r05,
                "condition_rule_mIoU_fg5_pp": rule,
                "pixel_oracle_mIoU_fg5_pp": oracle,
                "oracle_headroom_over_best_expert_pp": headroom,
            })

        local_zero_r01 = region_mean(regions, "D1_local_missing", "R01_optical")
        local_zero_r05 = region_mean(regions, "D1_local_missing", "R05_dual")
        local_down8_r01 = region_mean(regions, "D3_local_down8", "R01_optical")
        local_down8_r05 = region_mean(regions, "D3_local_down8", "R05_dual")
        agreement_by_condition = {r["condition"]: r for r in agreement}
        seed_evidence[str(seed)] = {
            "clean": {
                method: get_metric(metrics, "clean", method)
                for method in ("R01_optical", "R05_dual", "condition_rule", "pixel_oracle")
            },
            "global_dsm_zero": {
                method: get_metric(metrics, "dsm_zero", method)
                for method in ("R01_optical", "R05_dual", "condition_rule", "pixel_oracle")
            },
            "global_dsm_down8": {
                method: get_metric(metrics, "dsm_down8", method)
                for method in ("R01_optical", "R05_dual", "condition_rule", "pixel_oracle")
            },
            "local_missing_damaged_mean": {
                "R01_optical": local_zero_r01,
                "R05_dual": local_zero_r05,
                "R01_minus_R05_pp": local_zero_r01 - local_zero_r05,
            },
            "local_down8_damaged_mean": {
                "R01_optical": local_down8_r01,
                "R05_dual": local_down8_r05,
                "R05_minus_R01_pp": local_down8_r05 - local_down8_r01,
            },
            "mean_oracle_headroom_over_best_expert_pp": mean(oracle_headrooms),
            "local_zero_only_r01_correct_fraction_mean": mean([
                float(r["only_r01_correct_fraction"])
                for name, r in agreement_by_condition.items()
                if name.startswith("dsm_local_zero_")
            ]),
        }

    with open(OUT / "condition_comparison.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(table[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(table)

    per_seed_gate = {}
    for seed, ev in seed_evidence.items():
        per_seed_gate[seed] = {
            "R01_better_in_local_missing": ev["local_missing_damaged_mean"]["R01_minus_R05_pp"] > 0,
            "R05_better_in_local_down8": ev["local_down8_damaged_mean"]["R05_minus_R01_pp"] > 0,
            "oracle_headroom_at_least_0_5pp": ev["mean_oracle_headroom_over_best_expert_pp"] >= 0.5,
        }
        per_seed_gate[seed]["pass"] = all(per_seed_gate[seed].values())

    payload = {
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "experiment_id": "D4_EXPERT_COMPLEMENTARITY_SUMMARY",
        "historical_test6_loaded": False,
        "seed_evidence": seed_evidence,
        "gate_criteria": per_seed_gate,
        "proceed_to_B1_frozen_expert_gate": all(x["pass"] for x in per_seed_gate.values()),
        "next_if_pass": "Train a local reliability map for Zsafe = Zopt + g * (Zdual - Zopt) with both experts frozen.",
        "next_if_fail": "Use deterministic Optical fallback for missing DSM and retain R05 only for available DSM; do not train a learned gate.",
    }
    with open(OUT / "decision_evidence.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
