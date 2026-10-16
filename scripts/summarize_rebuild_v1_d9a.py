"""Validate D9A completion and make a compact, source-hashed comparison."""

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
QUEUE = ROOT / "records/rebuild_v1_d9a_queue_20260923"
OUT = ROOT / "records/rebuild_v1_d9a_summary_20260923"
CONDITIONS = (
    "clean", "dsm_zero", "dsm_down8", "dsm_blur5", "dsm_noise_std010",
    "dsm_shift_right_4px", "dsm_local_zero_q1", "dsm_local_down8_q1",
)
SCORES = ("confidence_margin", "entropy_margin", "confidence_times_js",
          "class_agreement_margin")


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def one(rows, **criteria):
    selected = [row for row in rows if all(row[k] == str(v) for k, v in criteria.items())]
    if len(selected) != 1:
        raise RuntimeError(f"expected one {criteria}, found {len(selected)}")
    return selected[0]


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path, rows):
    if not rows:
        raise RuntimeError(f"no rows: {path}")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def validate_queue():
    status = QUEUE / "status.tsv"
    rows = list(csv.reader(status.open(encoding="utf-8"), delimiter="\t"))
    if not rows or rows[0][1:3] != ["QUEUE", "START"]:
        raise RuntimeError("missing D9A queue start")
    if rows[0][3] != "ed92ae4f605c87d5c8ebd5c6c932c548d77b28c0":
        raise RuntimeError(f"unexpected D9A launch commit: {rows[0][3]}")
    if not any(r[1:3] == ["QUEUE", "FINISHED"] and r[3] == "failures=0" for r in rows):
        raise RuntimeError("D9A queue not successfully finished")
    expected = ["D9A_SMOKE"] + [f"D9A_{seed}_{condition}"
                                  for seed in (42, 17) for condition in CONDITIONS]
    for name in expected:
        events = [r for r in rows if len(r) > 2 and r[1] == name]
        if [r[2] for r in events] != ["START", "COMPLETE"] or events[-1][3] != "0":
            raise RuntimeError(f"incomplete stage {name}: {events}")
    queue_log = QUEUE / "queue.log"
    preflight = queue_log.read_text(encoding="utf-8", errors="replace")
    if preflight.count("GPU_OK") != len(expected):
        raise RuntimeError("GPU0 preflight count does not match completed stages")
    stage_logs = [QUEUE / f"{name}.log" for name in expected]
    for path in stage_logs:
        if not path.is_file():
            raise FileNotFoundError(path)
    smoke_text = stage_logs[0].read_text(encoding="utf-8", errors="replace")
    if "R01 TRUE OPTICAL-ONLY structural audit" not in smoke_text or "D9A COMPLETE" not in smoke_text:
        raise RuntimeError("smoke structural audit/completion missing")
    return [status, queue_log, *stage_logs], len(expected)


def main():
    queue_sources, completed_stages = validate_queue()
    if OUT.exists():
        raise FileExistsError(OUT)
    source_paths = list(queue_sources)
    table, strata = [], []
    seed_condition = {}
    for seed in (42, 17):
        for condition in CONDITIONS:
            base = ROOT / f"records/rebuild_v1_d9a_seed{seed}_{condition}_20260923"
            files = {name: base / name for name in
                     ("summary.json", "method_metrics.csv", "ranking_metrics.csv", "selected_harm.csv")}
            for path in files.values():
                if not path.is_file():
                    raise FileNotFoundError(path)
                source_paths.append(path)
            summary = json.loads(files["summary.json"].read_text(encoding="utf-8"))
            if (summary.get("seed") != seed or summary.get("condition") != condition
                    or summary.get("test6_loaded") is not False
                    or summary.get("val_ids") != ["3_11", "5_10"]
                    or summary.get("smoke") is not False):
                raise RuntimeError(f"invalid run summary: {files['summary.json']}")
            method = read_csv(files["method_metrics.csv"])
            ranking = read_csv(files["ranking_metrics.csv"])
            harm = read_csv(files["selected_harm.csv"])
            rank = {name: one(ranking, tile="ALL", group="all", score=name,
                              neutral_ce="0.01") for name in SCORES}
            counts = {(r["count"], r["benefit_count"], r["harm_count"])
                      for r in rank.values()}
            if len(counts) != 1:
                raise RuntimeError(f"score support mismatch: {seed} {condition}")
            base_row = {"seed": seed, "condition": condition,
                        "sample_valid": sum(int(x["sample_pixels"]) for x in summary["tile_summaries"]),
                        "ranked_non_neutral": int(rank["confidence_margin"]["count"]),
                        "benefit_count": int(rank["confidence_margin"]["benefit_count"]),
                        "harm_count": int(rank["confidence_margin"]["harm_count"])}
            for name in SCORES:
                for metric in ("benefit_auroc", "benefit_auprc", "harm_auroc", "harm_auprc"):
                    value = rank[name][metric]
                    base_row[f"{name}_{metric}"] = float(value) if value else None
            for model in ("R01", "R05", "D5_safe_confidence", "correctness_oracle"):
                for split in ("full", "noboundary"):
                    r = one(method, tile="ALL", method=model, split=split)
                    base_row[f"{model}_{split}_miou_percent"] = 100 * float(r["mIoU_fg5"])
            for model in ("R05", "D5_safe_confidence"):
                r = one(harm, tile="ALL", method=model)
                base_row[f"{model}_selected_dual"] = int(r["selected_dual"])
                base_row[f"{model}_selected_harm"] = int(r["selected_harm"])
                base_row[f"{model}_selected_harm_rate"] = (
                    float(r["selected_harm_rate"]) if r["selected_harm_rate"] else None)
            if condition == "dsm_zero":
                if base_row["D5_safe_confidence_selected_dual"] != 0:
                    raise RuntimeError(f"DSM-zero fallback selected dual: seed {seed}")
                for split in ("full", "noboundary"):
                    if abs(base_row[f"D5_safe_confidence_{split}_miou_percent"]
                           - base_row[f"R01_{split}_miou_percent"]) > 1e-9:
                        raise RuntimeError(f"DSM-zero fallback metric mismatch: seed {seed}")
            table.append(base_row)
            seed_condition[f"{seed}/{condition}"] = {
                "confidence_auroc": base_row["confidence_margin_benefit_auroc"],
                "entropy_auroc": base_row["entropy_margin_benefit_auroc"],
                "disagreement_auroc": base_row["confidence_times_js_benefit_auroc"],
                "confidence_auprc": base_row["confidence_margin_benefit_auprc"],
                "disagreement_auprc": base_row["confidence_times_js_benefit_auprc"],
                "r01_nb_miou_percent": base_row["R01_noboundary_miou_percent"],
                "r05_nb_miou_percent": base_row["R05_noboundary_miou_percent"],
                "d5_nb_miou_percent": base_row["D5_safe_confidence_noboundary_miou_percent"],
                "d5_selected_harm_rate": base_row["D5_safe_confidence_selected_harm_rate"],
            }
            for group in ("class:Car", "class:Building", "class_size:Car:small",
                          "region:damaged"):
                for name in ("confidence_margin", "confidence_times_js"):
                    found = [r for r in ranking if r["tile"] == "ALL" and r["group"] == group
                             and r["score"] == name and r["neutral_ce"] == "0.01"]
                    if len(found) > 1:
                        raise RuntimeError(f"duplicate stratum: {seed} {condition} {group} {name}")
                    if found:
                        strata.append({"seed": seed, "condition": condition,
                                       "group": group, "score": name, **{
                                           k: found[0][k] for k in ("count", "benefit_count",
                                                                   "harm_count", "benefit_auroc",
                                                                   "benefit_auprc")}})

    OUT.mkdir(parents=True, exist_ok=False)
    write_csv(OUT / "summary_table.csv", table)
    write_csv(OUT / "strata_table.csv", strata)
    manifest = [{"source": str(p), "bytes": p.stat().st_size, "sha256": sha256(p)}
                for p in source_paths]
    (OUT / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    decision = {"experiment_id": "D9A_FROZEN_EXPERT_BENEFIT_AUDIT",
                "launch_commit": "ed92ae4f605c87d5c8ebd5c6c932c548d77b28c0",
                "completed_stages": completed_stages, "failed_stages": 0,
                "seeds": [42, 17], "conditions": list(CONDITIONS),
                "test6_loaded": False, "source_files_hashed": len(manifest),
                "summary": seed_condition,
                "gate_status": "not_evaluated",
                "reason": "D9A compares only unfitted direct scores on repeatedly inspected Val2; semantic/frequency fitted combinations, ECE and an independent evaluation source are absent."}
    (OUT / "decision_evidence.json").write_text(json.dumps(decision, indent=2) + "\n")
    print("D9A SUMMARY COMPLETE", OUT)
    print("seed condition conf_AUROC conf_AUPRC disagree_AUROC disagree_AUPRC R01_NB R05_NB D5_NB D5_harm_rate")
    for row in table:
        def fmt(key):
            value = row[key]
            return "NA" if value is None else f"{value:.4f}"
        print(row["seed"], row["condition"],
              *(fmt(key) for key in ("confidence_margin_benefit_auroc",
                                     "confidence_margin_benefit_auprc",
                                     "confidence_times_js_benefit_auroc",
                                     "confidence_times_js_benefit_auprc",
                                     "R01_noboundary_miou_percent",
                                     "R05_noboundary_miou_percent",
                                     "D5_safe_confidence_noboundary_miou_percent",
                                     "D5_safe_confidence_selected_harm_rate")))


if __name__ == "__main__":
    main()
