"""Read-only review of existing D9A entropy-route class, size and region rows."""

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
SUMMARY = ROOT / "records/rebuild_v1_d9a_entropy_route_summary_20260923"
CONDITIONS = ("clean", "dsm_zero", "dsm_down8", "dsm_blur5",
              "dsm_noise_std010", "dsm_shift_right_4px",
              "dsm_local_zero_q1", "dsm_local_down8_q1")


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def one(rows, **keys):
    found = [r for r in rows if all(r[k] == str(v) for k, v in keys.items())]
    if len(found) != 1:
        raise RuntimeError(f"expected one row {keys}: {len(found)}")
    return found[0]


def number(value):
    return None if value in ("", "None", None) else float(value)


def checked(path, manifest):
    entry = manifest.get(str(path))
    if entry is None:
        raise RuntimeError(f"source missing from manifest: {path}")
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    if h != entry["sha256"]:
        raise RuntimeError(f"source changed after summary: {path}")
    return read_csv(path)


def main():
    decision = json.loads((SUMMARY / "decision_evidence.json").read_text(encoding="utf-8"))
    if (decision.get("queue_failures") != 0 or decision.get("completed_stages") != 17
            or decision.get("test6_loaded") is not False):
        raise RuntimeError("D9A entropy-route summary validation failed")
    entries = json.loads((SUMMARY / "source_manifest.json").read_text(encoding="utf-8"))
    manifest = {item["source"]: item for item in entries}
    class_wins = {"Car": 0, "Building": 0}
    class_valid = {"Car": 0, "Building": 0}
    print("D9A ENTROPY ROUTE STRATA REVIEW — source hashes verified")
    print("seed condition Car_IoU_delta_pp Building_IoU_delta_pp smallCar_support smallCar_conf_selected/harm smallCar_entropy_selected/harm")
    for seed in (42, 17):
        for condition in CONDITIONS:
            base = ROOT / f"records/rebuild_v1_d9a_entropy_route_seed{seed}_{condition}_20260923"
            classes = checked(base / "class_iou.csv", manifest)
            harms = checked(base / "selected_harm.csv", manifest)
            deltas = {}
            for cls in ("Car", "Building"):
                conf = one(classes, tile="ALL", split="noboundary", method="safe_confidence", **{"class": cls})
                ent = one(classes, tile="ALL", split="noboundary", method="safe_entropy", **{"class": cls})
                a, b = number(conf["IoU"]), number(ent["IoU"])
                deltas[cls] = None if a is None or b is None else 100 * (b - a)
                if deltas[cls] is not None:
                    class_valid[cls] += 1
                    class_wins[cls] += deltas[cls] > 0
            small_conf = one(harms, tile="ALL", group="class_size:Car:small", method="safe_confidence")
            small_ent = one(harms, tile="ALL", group="class_size:Car:small", method="safe_entropy")
            if small_conf["valid_sampled"] != small_ent["valid_sampled"]:
                raise RuntimeError(f"small Car support mismatch: {seed} {condition}")
            fmt = lambda x: "NA" if x is None else f"{x:+.4f}"
            rate = lambda x: "NA" if number(x) is None else f"{number(x):.4f}"
            print(seed, condition, fmt(deltas["Car"]), fmt(deltas["Building"]),
                  small_conf["valid_sampled"],
                  f"{small_conf['selected_dual']}/{rate(small_conf['selected_harm_rate'])}",
                  f"{small_ent['selected_dual']}/{rate(small_ent['selected_harm_rate'])}")
    print("per-class IoU wins", class_wins, "valid", class_valid)
    print("Local damaged-region NoBoundary mIoU and selected harm")
    print("seed condition conf_mIoU entropy_mIoU delta_pp conf_selected/harm entropy_selected/harm support")
    for seed in (42, 17):
        for condition in ("dsm_local_zero_q1", "dsm_local_down8_q1"):
            base = ROOT / f"records/rebuild_v1_d9a_entropy_route_seed{seed}_{condition}_20260923"
            regions = checked(base / "region_metrics.csv", manifest)
            harms = checked(base / "selected_harm.csv", manifest)
            conf = one(regions, tile="ALL", region="damaged", method="safe_confidence")
            ent = one(regions, tile="ALL", region="damaged", method="safe_entropy")
            hc = one(harms, tile="ALL", group="region:damaged", method="safe_confidence")
            he = one(harms, tile="ALL", group="region:damaged", method="safe_entropy")
            c, e = 100 * float(conf["mIoU_fg5"]), 100 * float(ent["mIoU_fg5"])
            rate = lambda x: "NA" if number(x) is None else f"{number(x):.4f}"
            print(seed, condition, f"{c:.4f}", f"{e:.4f}", f"{e-c:+.4f}",
                  f"{hc['selected_dual']}/{rate(hc['selected_harm_rate'])}",
                  f"{he['selected_dual']}/{rate(he['selected_harm_rate'])}",
                  hc["valid_sampled"])


if __name__ == "__main__":
    main()
