import csv
import json
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
DATA = ROOT / "records/rebuild_v1_d7_data_sampling_20260922"
OUT = ROOT / "records/rebuild_v1_d7_summary_20260922"


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def f(value):
    return float(value)


def lookup(rows, **want):
    matches = [r for r in rows if all(str(r[k]) == str(v) for k, v in want.items())]
    if len(matches) != 1:
        raise RuntimeError(f"expected one row for {want}, found {len(matches)}")
    return matches[0]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data_summary = json.loads((DATA / "summary.json").read_text(encoding="utf-8"))
    exposure = read_csv(DATA / "crop_exposure.csv")
    car = lookup(exposure, class_name="Car")
    evidence = {}
    detail_rows = []
    seed_flags = []
    for seed in (42, 17):
        base = ROOT / f"records/rebuild_v1_d7_semantic_errors_seed{seed}_20260922"
        summary = json.loads((base / "summary.json").read_text(encoding="utf-8"))
        if summary.get("historical_test6_loaded") is not False:
            raise RuntimeError(f"TEST6 safety failed for seed {seed}")
        classes = read_csv(base / "per_class_metrics.csv")
        regions = read_csv(base / "dataset_region_metrics.csv")
        objects = read_csv(base / "object_size_summary.csv")
        seed_data = {"class_condition_drops_pp": {}, "car_object_recall": {}}
        for condition in ("dsm_down8", "dsm_zero"):
            drops = {}
            for name in rclass_names(classes):
                clean = f(lookup(classes, model="R05", condition="clean", region="full", class_name=name)["IoU"])
                degraded = f(lookup(classes, model="R05", condition=condition, region="full", class_name=name)["IoU"])
                drops[name] = 100 * (clean - degraded)
                detail_rows.append({"seed": seed, "analysis": "class_iou_drop_pp", "condition": condition,
                                    "group": name, "value": drops[name]})
            seed_data["class_condition_drops_pp"][condition] = drops
        for model in ("R01", "R05"):
            small = lookup(objects, model=model, condition="clean", class_name="Car", size_bin="small")
            large = lookup(objects, model=model, condition="clean", class_name="Car", size_bin="large")
            gap = 100 * (f(large["recall_at_50pct"]) - f(small["recall_at_50pct"]))
            seed_data["car_object_recall"][model] = {
                "small": f(small["recall_at_50pct"]), "large": f(large["recall_at_50pct"]),
                "large_minus_small_pp": gap, "small_n": int(small["objects"]), "large_n": int(large["objects"]),
            }
            detail_rows.append({"seed": seed, "analysis": "car_large_minus_small_recall_pp",
                                "condition": "clean", "group": model, "value": gap})
        boundary_gaps = {}
        for model in ("R01", "R05"):
            boundary = f(lookup(regions, model=model, condition="clean", region="semantic_boundary_r3")["mIoU_fg5"])
            interior = f(lookup(regions, model=model, condition="clean", region="semantic_interior_r3")["mIoU_fg5"])
            boundary_gaps[model] = 100 * (interior - boundary)
        seed_data["semantic_interior_minus_boundary_r3_pp"] = boundary_gaps
        car_down8 = seed_data["class_condition_drops_pp"]["dsm_down8"]["Car"]
        mean_down8 = sum(seed_data["class_condition_drops_pp"]["dsm_down8"].values()) / 5
        seed_flags.append({
            "seed": seed,
            "car_small_object_gap_at_least_5pp": all(
                x["large_minus_small_pp"] >= 5 and x["small_n"] >= 20 and x["large_n"] >= 20
                for x in seed_data["car_object_recall"].values()
            ),
            "car_down8_drop_exceeds_fg_mean_by_1pp": car_down8 >= mean_down8 + 1,
            "semantic_boundary_gap_at_least_5pp": all(v >= 5 for v in boundary_gaps.values()),
        })
        evidence[str(seed)] = seed_data

    fg_ratio = f(data_summary["foreground_max_min_pixel_ratio"])
    car_absence = f(car["crop_absence_fraction"])
    decisions = {
        "pixel_imbalance_over_10x": fg_ratio >= 10,
        "car_absent_from_over_half_random_crops": car_absence >= 0.5,
        "replicated_car_small_object_gap": all(x["car_small_object_gap_at_least_5pp"] for x in seed_flags),
        "replicated_car_specific_down8_vulnerability": all(x["car_down8_drop_exceeds_fg_mean_by_1pp"] for x in seed_flags),
        "replicated_semantic_boundary_gap": all(x["semantic_boundary_gap_at_least_5pp"] for x in seed_flags),
    }
    recommendations = []
    if decisions["car_absent_from_over_half_random_crops"] and decisions["replicated_car_small_object_gap"]:
        recommendations.append("screen mixed class-aware crop on R01 before changing fusion")
    if decisions["pixel_imbalance_over_10x"]:
        recommendations.append("screen smoothed weighted CE against matched CE")
    if decisions["replicated_semantic_boundary_gap"]:
        recommendations.append("treat semantic boundary supervision as a separate controlled arm")
    if decisions["replicated_car_specific_down8_vulnerability"]:
        recommendations.append("test the long-tail x DSM-degradation interaction after the R01 screen")
    if not recommendations:
        recommendations.append("do not queue imbalance training; return to new-dataset reliability protocol")

    payload = {
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "experiment_id": "D7_DATA_SCALE_BOUNDARY_ERROR_AUDIT_SUMMARY",
        "status": "exploratory_development_evidence",
        "historical_test6_loaded": False,
        "data_evidence": {"foreground_max_min_pixel_ratio": fg_ratio,
                          "car_crop_absence_fraction": car_absence,
                          "crop_samples": data_summary["samples"]},
        "seed_evidence": evidence,
        "predeclared_screening_flags": seed_flags,
        "decisions": decisions,
        "recommended_next_controls": recommendations,
        "limitation": "Val2 has only two repeatedly inspected tiles; these flags select follow-up controls and are not final paper claims.",
    }
    (OUT / "decision_evidence.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with (OUT / "diagnostic_effects.csv").open("w", newline="", encoding="utf-8") as fobj:
        w = csv.DictWriter(fobj, fieldnames=list(detail_rows[0]), lineterminator="\n")
        w.writeheader(); w.writerows(detail_rows)
    print(json.dumps({"decisions": decisions, "recommended_next_controls": recommendations}, indent=2))


def rclass_names(rows):
    names = []
    for row in rows:
        name = row["class_name"]
        if int(row["class_index"]) < 5 and name not in names:
            names.append(name)
    return names


if __name__ == "__main__":
    main()
