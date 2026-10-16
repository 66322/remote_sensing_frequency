"""Apply the frozen D12 screen without changing models or Val2 thresholds."""
import csv
import json
from pathlib import Path

from summarize_rebuild_v1_d11_probe import family_average
from d12_night_probe import ROOT, CFG, BASE, D11


def rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def condition_values(items, method):
    return {r["condition"]: float(r["sampled_mIoU_fg5"])
            for r in items if r["method"] == method and r["tile"] == "ALL" and r["group"] == "all"}


def main():
    cfg = json.loads(CFG.read_text())
    expected = cfg["core_models"] + cfg["mechanism_models"]
    loaded = {}
    missing = []
    for seed in cfg["seeds"]:
        for model in expected:
            folder = BASE / "models" / f"seed{seed}_{model}"
            if not (folder / "summary.json").is_file():
                missing.append(f"seed{seed}_{model}")
                continue
            meta = json.loads((folder / "summary.json").read_text())
            data = rows(folder / "routing.csv")
            if meta["seed"] != seed or meta["model"] != model or meta["test6_loaded"]:
                raise RuntimeError("D12 result mismatch")
            values = condition_values(data, "probe")
            if set(values) != set(cfg["evaluation_conditions"]):
                raise RuntimeError("D12 incomplete conditions")
            loaded[seed, model] = (meta, data, values)
    output = []
    for (seed, model), (meta, data, values) in loaded.items():
        scalar = {}
        for name in ("confidence", "entropy"):
            scalar[name] = condition_values(rows(D11 / "models" / f"seed{seed}_{name}" / "routing.csv"), "probe")
        baseline = {condition: max(scalar["confidence"][condition], scalar["entropy"][condition])
                    for condition in cfg["evaluation_conditions"]}
        rgb = condition_values(data, "RGB")
        worst = max(float(r["harm"]) for r in data
                    if r["method"] == "probe" and r["tile"] != "ALL" and r["group"] == "all")
        improvement = 100 * family_average({c: values[c] - baseline[c] for c in values})
        passed = (model in cfg["core_models"] and improvement >= cfg["minimum_family_gain_pp"]
                  and values["clean"] >= rgb["clean"] and worst <= cfg["harm_budget"])
        output.append(dict(seed=seed, model=model, threshold=meta["threshold"],
                           parameters=meta["parameter_count"], clean_sampled_mIoU_percent=100*values["clean"],
                           clean_minus_RGB_pp=100*(values["clean"]-rgb["clean"]),
                           family_delta_vs_calibrated_scalar_pp=improvement,
                           worst_tile_condition_H_percent=100*worst, screen=passed))
    result = BASE / "screen_summary.csv"
    with result.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output[0]) if output else
                                ["seed", "model", "screen"], lineterminator="\n")
        writer.writeheader(); writer.writerows(output)
    candidates = [name for name in cfg["full_resolution_priority"]
                  if all(any(row["seed"] == seed and row["model"] == name and row["screen"]
                             for row in output) for seed in cfg["seeds"])][:cfg["max_full_resolution_candidates"]]
    decision = dict(completed=len(loaded), expected=len(expected)*len(cfg["seeds"]), missing=missing,
                    full_resolution_candidates=candidates, test6_loaded=False,
                    residual_gate_authorized=False, independent_confirmation=False,
                    note="Predetermined practical screen; no Val2 threshold or model tuning")
    (BASE / "decision.json").write_text(json.dumps(decision, indent=2) + "\n")
    print("D12 completed", len(loaded), "/", decision["expected"], "missing", missing)
    for row in output:
        print(row)
    print("FULL_RESOLUTION_CANDIDATES", candidates)
    raise SystemExit(1 if missing else 0)


if __name__ == "__main__":
    main()
