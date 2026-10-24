"""Summarize D9B primary flip-benefit results only after source completion."""

import csv
import json
from pathlib import Path

from eval_rebuild_v1_d9b_decision_benefit import ROOT, SCORES, PROTOTYPE
from eval_rebuild_v1_d9a_benefit import CONDITIONS

QUEUE = ROOT / "records/rebuild_v1_d9b_decision_screen_queue_20260923/status.tsv"
OUT = ROOT / "records/rebuild_v1_d9b_decision_screen_summary_20260923"


def main():
    lines = [x.split("\t") for x in QUEUE.read_text(encoding="utf-8").splitlines()]
    if not lines or lines[-1][1:3] != ["QUEUE", "FINISHED"]:
        raise RuntimeError("D9B queue not finished")
    failed = [x for x in lines if x[2] == "FAILED"]
    if failed:
        raise RuntimeError(f"D9B queue failed: {[x[1] for x in failed]}")
    completed = {x[1] for x in lines if x[2] == "COMPLETE"}
    expected = {"D9B_TRAIN16_PROTOTYPES", "D9B_SMOKE"}
    expected |= {f"D9B_{seed}_{condition}" for seed in (42, 17) for condition in CONDITIONS}
    if completed != expected:
        raise RuntimeError(f"stage mismatch missing={expected-completed} extra={completed-expected}")
    import hashlib
    digest = hashlib.sha256(PROTOTYPE.read_bytes()).hexdigest()
    rows = []
    for seed in (42, 17):
        for condition in CONDITIONS:
            folder = ROOT / f"records/rebuild_v1_d9b_seed{seed}_{condition}_20260923"
            meta = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
            if meta["smoke"] or meta["test6_loaded"] or meta["prototype_sha256"] != digest:
                raise RuntimeError(f"invalid source provenance: {folder}")
            with (folder / "decision_metrics.csv").open(newline="", encoding="utf-8") as f:
                data = list(csv.DictReader(f))
            actual = [r for r in data if r["tile"] == "ALL" and r["group"] == "all"]
            if {r["score"] for r in actual} != set(SCORES):
                raise RuntimeError(f"score mismatch: {folder}")
            rows.extend(actual)
    by_key = {(int(r["seed"]), r["condition"], r["score"]): r for r in rows}
    lines_out = ["seed condition score flip_AUROC flip_AUPRC dual_only rgb_only both_wrong agreement ΔAUROC_vs_best_direct ΔAUPRC_vs_best_direct"]
    wins = {name: {"auroc": 0, "auprc": 0} for name in SCORES[2:]}
    for seed in (42, 17):
        for condition in CONDITIONS:
            direct = [by_key[(seed, condition, name)] for name in SCORES[:2]]
            for name in SCORES:
                r = by_key[(seed, condition, name)]
                auc = float(r["flip_auroc"])
                ap = float(r["flip_auprc"])
                delta_auc = auc - max(float(c["flip_auroc"]) for c in direct)
                delta_ap = ap - max(float(c["flip_auprc"]) for c in direct)
                if name in wins:
                    wins[name]["auroc"] += delta_auc > 0
                    wins[name]["auprc"] += delta_ap > 0
                lines_out.append(f'{seed} {condition} {name} {auc:.4f} {ap:.4f} {r["dual_only_correct"]} {r["rgb_only_correct"]} {r["both_wrong"]} {r["agreement"]} {delta_auc:+.4f} {delta_ap:+.4f}')
    if OUT.exists():
        raise FileExistsError(OUT)
    OUT.mkdir(parents=True)
    (OUT / "primary_results.txt").write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    (OUT / "decision.json").write_text(json.dumps({
        "experiment_id": "D9B_UNFITTED_DECISION_SCREEN", "rows": 16,
        "source": "exploratory Val2", "test6_loaded": False,
        "prototype_sha256": digest, "queue_failures": 0,
        "wins_vs_best_direct_out_of_16": wins,
        "fitted_or_calibrated": False,
        "next_gate": "independent labelled scenes required before model fitting or safety gate",
    }, indent=2) + "\n", encoding="utf-8")
    print("D9B SUMMARY COMPLETE", OUT)
    print("\n".join(lines_out))
    print("wins", wins)


if __name__ == "__main__":
    main()
