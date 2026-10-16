"""Validate D9A entropy-routing queue and compare both unfitted safe routes."""

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
QUEUE = ROOT / "records/rebuild_v1_d9a_entropy_route_queue_20260923"
OUT = ROOT / "records/rebuild_v1_d9a_entropy_route_summary_20260923"
CONDITIONS = ("clean", "dsm_zero", "dsm_down8", "dsm_blur5",
              "dsm_noise_std010", "dsm_shift_right_4px",
              "dsm_local_zero_q1", "dsm_local_down8_q1")


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def one(rows, **keys):
    found = [r for r in rows if all(r[k] == str(v) for k, v in keys.items())]
    if len(found) != 1:
        raise RuntimeError(f"expected one row {keys}, got {len(found)}")
    return found[0]


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    status = QUEUE / "status.tsv"
    events = list(csv.reader(status.open(encoding="utf-8"), delimiter="\t"))
    if not events or events[-1][1:4] != ["QUEUE", "FINISHED", "failures=0"]:
        raise RuntimeError("D9A entropy-route queue did not finish with zero failures")
    expected = ["D9A_ENT_SMOKE"] + [f"D9A_ENT_{seed}_{condition}"
                                   for seed in (42, 17) for condition in CONDITIONS]
    for name in expected:
        stages = [r for r in events if len(r) >= 4 and r[1] == name]
        if [r[2] for r in stages] != ["START", "COMPLETE"] or stages[-1][3] != "0":
            raise RuntimeError(f"stage incomplete: {name}")
    queue_log = QUEUE / "queue.log"
    if queue_log.read_text(encoding="utf-8", errors="replace").count("GPU_OK") != len(expected):
        raise RuntimeError("GPU0 preflight count mismatch")
    smoke_summary_path = ROOT / "records/rebuild_v1_d9a_entropy_route_seed42_clean_20260923_smoke/summary.json"
    smoke_summary = json.loads(smoke_summary_path.read_text(encoding="utf-8"))
    if (smoke_summary.get("smoke") is not True or smoke_summary.get("test6_loaded") is not False
            or smoke_summary.get("val_ids") != ["3_11"]):
        raise RuntimeError("smoke provenance failed")
    sources = [status, queue_log, QUEUE / "D9A_ENT_SMOKE.log", smoke_summary_path]
    rows = []
    for seed in (42, 17):
        for condition in CONDITIONS:
            name = f"D9A_ENT_{seed}_{condition}"
            route_dir = ROOT / f"records/rebuild_v1_d9a_entropy_route_seed{seed}_{condition}_20260923"
            d9a_suffix = "_fix1" if condition == "dsm_local_down8_q1" else ""
            ref_dir = ROOT / f"records/rebuild_v1_d9a_seed{seed}_{condition}_20260923{d9a_suffix}"
            route_summary_path = route_dir / "summary.json"
            route_summary = json.loads(route_summary_path.read_text(encoding="utf-8"))
            if (route_summary.get("seed") != seed or route_summary.get("condition") != condition
                    or route_summary.get("smoke") is not False
                    or route_summary.get("val_ids") != ["3_11", "5_10"]
                    or route_summary.get("test6_loaded") is not False):
                raise RuntimeError(f"provenance failed: {seed} {condition}")
            method_path = route_dir / "method_metrics.csv"
            harm_path = route_dir / "selected_harm.csv"
            class_path = route_dir / "class_iou.csv"
            region_path = route_dir / "region_metrics.csv"
            ref_path = ref_dir / "method_metrics.csv"
            sources.extend([QUEUE / f"{name}.log", route_summary_path,
                            method_path, harm_path, class_path, region_path, ref_path])
            methods, harms, ref = read_csv(method_path), read_csv(harm_path), read_csv(ref_path)
            for split in ("full", "noboundary"):
                for current, old in (("R01", "R01"), ("R05", "R05"),
                                     ("safe_confidence", "D5_safe_confidence")):
                    a = one(methods, tile="ALL", split=split, method=current)
                    b = one(ref, tile="ALL", split=split, method=old)
                    if abs(float(a["mIoU_fg5"]) - float(b["mIoU_fg5"])) > 1e-4:
                        raise RuntimeError(f"frozen control mismatch: {seed} {condition} {split} {current}")
            nb = {method: one(methods, tile="ALL", split="noboundary", method=method)
                  for method in ("R01", "R05", "safe_confidence", "min_entropy", "safe_entropy")}
            h = {method: one(harms, tile="ALL", group="all", method=method)
                 for method in ("safe_confidence", "min_entropy", "safe_entropy")}
            if condition == "dsm_zero":
                for method in ("safe_confidence", "safe_entropy"):
                    if int(h[method]["selected_dual"]) != 0 or nb[method]["mIoU_fg5"] != nb["R01"]["mIoU_fg5"]:
                        raise RuntimeError(f"deterministic DSM-zero fallback failed: {seed} {method}")
            row = {"seed": seed, "condition": condition}
            for method, metric in nb.items():
                row[f"{method}_nb_miou_percent"] = 100 * float(metric["mIoU_fg5"])
            for method, harm in h.items():
                row[f"{method}_selected_dual"] = int(harm["selected_dual"])
                row[f"{method}_selected_harm_rate"] = (None if harm["selected_harm_rate"] in ("", "None")
                                                       else float(harm["selected_harm_rate"]))
                row[f"{method}_harm_per_valid"] = float(harm["harm_per_valid"])
            row["safe_entropy_minus_safe_confidence_miou_pp"] = (
                row["safe_entropy_nb_miou_percent"] - row["safe_confidence_nb_miou_percent"])
            rows.append(row)

    OUT.mkdir(parents=True, exist_ok=False)
    with (OUT / "route_comparison.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    manifest = [{"source": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
                for path in sources]
    (OUT / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    deltas = [r["safe_entropy_minus_safe_confidence_miou_pp"] for r in rows]
    payload = {"experiment_id": "D9A_ENTROPY_ROUTING_AUDIT",
               "completed_stages": len(expected), "queue_failures": 0,
               "test6_loaded": False, "frozen_controls_match_D9A_within_1e-4": True,
               "safe_entropy_miou_wins": sum(x > 0 for x in deltas),
               "safe_entropy_miou_ties": sum(x == 0 for x in deltas),
               "mean_safe_entropy_minus_confidence_miou_pp": sum(deltas) / len(deltas),
               "rows": rows,
               "interpretation": "Exploratory Val2 decision audit; ranking gain alone cannot establish safe routing."}
    (OUT / "decision_evidence.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("D9A ENTROPY ROUTE SUMMARY COMPLETE", OUT)
    print("seed condition R01 R05 safe_confidence safe_entropy entropy_minus_conf_pp confidence_harm entropy_harm")
    for r in rows:
        print(r["seed"], r["condition"],
              *(f"{r[f'{m}_nb_miou_percent']:.4f}" for m in ("R01", "R05", "safe_confidence", "safe_entropy")),
              f"{r['safe_entropy_minus_safe_confidence_miou_pp']:+.4f}",
              r["safe_confidence_selected_harm_rate"], r["safe_entropy_selected_harm_rate"])
    print("wins", payload["safe_entropy_miou_wins"], "mean_delta_pp",
          f"{payload['mean_safe_entropy_minus_confidence_miou_pp']:+.4f}")


if __name__ == "__main__":
    main()
