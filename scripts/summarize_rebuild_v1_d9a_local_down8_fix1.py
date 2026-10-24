"""Verify the D9A local-down8 routing correction without replacing originals."""

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
QUEUE = ROOT / "records/rebuild_v1_d9a_local_down8_fix1_queue_20260923"
OUT = ROOT / "records/rebuild_v1_d9a_local_down8_fix1_summary_20260923"


def rows(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def one(items, **criteria):
    found = [r for r in items if all(r[k] == str(v) for k, v in criteria.items())]
    if len(found) != 1:
        raise RuntimeError(f"expected one {criteria}: {len(found)}")
    return found[0]


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    status = QUEUE / "status.tsv"
    events = list(csv.reader(status.open(encoding="utf-8"), delimiter="\t"))
    if not events or events[-1][1:4] != ["QUEUE", "FINISHED", "failures=0"]:
        raise RuntimeError("correction queue incomplete")
    for seed in (42, 17):
        name = f"D9A_FIX1_{seed}_local_down8"
        stages = [r for r in events if len(r) > 2 and r[1] == name]
        if [r[2] for r in stages] != ["START", "COMPLETE"] or stages[-1][3] != "0":
            raise RuntimeError(f"incomplete correction stage: {name}")
    queue_log = QUEUE / "queue.log"
    if queue_log.read_text(encoding="utf-8", errors="replace").count("GPU_OK") != 2:
        raise RuntimeError("GPU0 preflight count mismatch")
    if OUT.exists():
        raise FileExistsError(OUT)

    results = {}
    sources = [status, queue_log]
    for seed in (42, 17):
        old = ROOT / f"records/rebuild_v1_d9a_seed{seed}_dsm_local_down8_q1_20260923"
        new = ROOT / f"records/rebuild_v1_d9a_seed{seed}_dsm_local_down8_q1_20260923_fix1"
        sources += [QUEUE / f"D9A_FIX1_{seed}_local_down8.log"]
        old_summary = json.loads((old / "summary.json").read_text(encoding="utf-8"))
        new_summary = json.loads((new / "summary.json").read_text(encoding="utf-8"))
        if (new_summary.get("run_tag") != "fix1"
                or new_summary.get("hard_missing_fallback_applied") is not False
                or new_summary.get("test6_loaded") is not False
                or new_summary.get("val_ids") != ["3_11", "5_10"]
                or old_summary.get("test6_loaded") is not False):
            raise RuntimeError(f"correction provenance failed: seed {seed}")
        for filename in ("summary.json", "method_metrics.csv", "ranking_metrics.csv", "selected_harm.csv"):
            sources += [old / filename, new / filename]
        old_rank = one(rows(old / "ranking_metrics.csv"), tile="ALL", group="all",
                       score="confidence_margin", neutral_ce="0.01")
        new_rank = one(rows(new / "ranking_metrics.csv"), tile="ALL", group="all",
                       score="confidence_margin", neutral_ce="0.01")
        if old_rank["count"] != new_rank["count"] or any(
            abs(float(old_rank[key]) - float(new_rank[key])) > 1e-4
            for key in ("benefit_auroc", "benefit_auprc")
        ):
            raise RuntimeError(f"benefit ranking unexpectedly changed: seed {seed}")
        ranking_exactly_identical = ((old / "ranking_metrics.csv").read_bytes()
                                     == (new / "ranking_metrics.csv").read_bytes())
        old_methods, new_methods = rows(old / "method_metrics.csv"), rows(new / "method_metrics.csv")
        for split in ("full", "noboundary"):
            for method in ("R01", "R05", "correctness_oracle"):
                before = one(old_methods, tile="ALL", split=split, method=method)
                after = one(new_methods, tile="ALL", split=split, method=method)
                if abs(float(before["mIoU_fg5"]) - float(after["mIoU_fg5"])) > 1e-9:
                    raise RuntimeError(f"frozen expert/oracle changed: {seed} {split} {method}")
        before = one(old_methods, tile="ALL", split="noboundary", method="D5_safe_confidence")
        after = one(new_methods, tile="ALL", split="noboundary", method="D5_safe_confidence")
        rgb = one(new_methods, tile="ALL", split="noboundary", method="R01")
        dual = one(new_methods, tile="ALL", split="noboundary", method="R05")
        old_harm = one(rows(old / "selected_harm.csv"), tile="ALL", method="D5_safe_confidence")
        new_harm = one(rows(new / "selected_harm.csv"), tile="ALL", method="D5_safe_confidence")
        results[str(seed)] = {
            "old_d5_nb_miou_percent_invalid": 100 * float(before["mIoU_fg5"]),
            "corrected_d5_nb_miou_percent": 100 * float(after["mIoU_fg5"]),
            "change_pp": 100 * (float(after["mIoU_fg5"]) - float(before["mIoU_fg5"])),
            "corrected_d5_minus_rgb_pp": 100 * (float(after["mIoU_fg5"]) - float(rgb["mIoU_fg5"])),
            "corrected_d5_minus_dual_pp": 100 * (float(after["mIoU_fg5"]) - float(dual["mIoU_fg5"])),
            "old_selected_dual": int(old_harm["selected_dual"]),
            "corrected_selected_dual": int(new_harm["selected_dual"]),
            "old_selected_harm_rate_invalid": float(old_harm["selected_harm_rate"]),
            "corrected_selected_harm_rate": float(new_harm["selected_harm_rate"]),
            "ranking_aggregate_unchanged_within_1e-4": True,
            "ranking_csv_byte_identical": ranking_exactly_identical,
        }

    OUT.mkdir(parents=True, exist_ok=False)
    manifest = [{"source": str(p), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in sources]
    (OUT / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    payload = {"experiment_id": "D9A_LOCAL_DOWN8_ROUTING_FIX1",
               "reason": "Original D9A forced RGB in a degraded-but-available DSM quadrant.",
               "affected_outputs": ["D5_safe_confidence method_metrics", "D5_safe_confidence selected_harm"],
               "unaffected_outputs": ["R01/R05/oracle metrics", "all CE-benefit ranking metrics"],
               "test6_loaded": False, "results": results}
    (OUT / "decision_evidence.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
