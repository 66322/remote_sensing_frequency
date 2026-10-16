import csv
import json
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
OUT = ROOT / "records/rebuild_v1_b1_pilot_summary_20260920"
METHODS = {
    "B1-C": ROOT / "records/rebuild_v1_b1_c_robust_eval_20260920/dataset_metrics.csv",
    "B1-KD": ROOT / "records/rebuild_v1_b1_kd_robust_eval_20260920/dataset_metrics.csv",
    "B1-SAFE": ROOT / "records/rebuild_v1_b1_safe_robust_eval_20260920/dataset_metrics.csv",
}
REFERENCES = {
    "R05_clean": 87.04855733950684,
    "R01_dsm_zero": 85.37125509929237,
    "SafeMaxConfidence_dsm_down8": 86.37707502639303,
}


def read_metrics(path):
    if not path.is_file():
        return None
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["split"] == "noboundary"]
    return {row["condition"]: 100.0 * float(row["mIoU_fg5"]) for row in rows}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    metrics = {name: read_metrics(path) for name, path in METHODS.items()}
    complete = all(value is not None for value in metrics.values())
    evidence = {}
    for name, values in metrics.items():
        if values is None:
            evidence[name] = {"status": "missing"}
            continue
        key = {
            "clean": values["clean"],
            "dsm_zero": values["dsm_zero"],
            "dsm_down8": values["dsm_down8"],
        }
        key["three_condition_mean"] = sum(key.values()) / 3.0
        evidence[name] = key

    criteria = None
    proceed = False
    if complete:
        safe = evidence["B1-SAFE"]
        control = evidence["B1-C"]
        criteria = {
            "safe_mean_exceeds_ce_control": safe["three_condition_mean"] > control["three_condition_mean"],
            "clean_within_0_5pp_of_R05": safe["clean"] >= REFERENCES["R05_clean"] - 0.5,
            "zero_within_0_3pp_of_R01": safe["dsm_zero"] >= REFERENCES["R01_dsm_zero"] - 0.3,
            "down8_within_0_3pp_of_safe_teacher": safe["dsm_down8"] >= REFERENCES["SafeMaxConfidence_dsm_down8"] - 0.3,
        }
        proceed = all(criteria.values())

    payload = {
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "experiment_id": "B1_SINGLE_STUDENT_DISTILLATION_PILOT",
        "historical_test6_loaded": False,
        "reference_metrics_nb_mIoU_fg5_percent": REFERENCES,
        "method_evidence": evidence,
        "complete": complete,
        "gate_criteria": criteria,
        "proceed_to_full16k_seed42_then_seed17": proceed,
        "next_if_pass": "Evaluate B1-SAFE on D6 masks and latency, then run the frozen full schedule and seed17 replication.",
        "next_if_fail": "Keep SafeMaxConfidence as the inference baseline and inspect which B1 loss term or condition failed before changing the model.",
    }
    (OUT / "decision_evidence.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
