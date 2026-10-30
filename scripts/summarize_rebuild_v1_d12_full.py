"""Read-only aggregation of completed frozen full-image D12 comparisons."""
import csv
import json
from summarize_rebuild_v1_d11_probe import family_average
from d12_night_probe import BASE, CFG


def main():
    cfg = json.loads(CFG.read_text())
    decision = json.loads((BASE / "decision.json").read_text())
    candidates = decision["full_resolution_candidates"]
    if not candidates:
        print("D12 full resolution: no screened candidate")
        return
    rows, missing = [], []
    for seed in cfg["seeds"]:
        for condition in cfg["evaluation_conditions"]:
            folder = BASE / "full_resolution" / f"seed{seed}_{condition}"
            if not (folder / "summary.json").is_file():
                missing.append(f"seed{seed}_{condition}")
                continue
            meta = json.loads((folder / "summary.json").read_text())
            if meta["seed"] != seed or meta["condition"] != condition or meta["candidates"] != candidates or meta["test6_loaded"]:
                raise RuntimeError("D12 full manifest mismatch")
            with (folder / "metrics.csv").open(newline="") as stream:
                rows += [r for r in csv.DictReader(stream) if r["tile"] == "ALL" and r["split"] == "noboundary"]
    print("D12 full-image jobs", 14-len(missing), "/14; missing", missing)
    for seed in cfg["seeds"]:
        for name in candidates:
            block = [r for r in rows if int(r["seed"]) == seed]
            own = {r["condition"]: float(r["mIoU_fg5"]) for r in block if r["method"] == name}
            if set(own) != set(cfg["evaluation_conditions"]):
                continue
            controls = {c: max(float(r["mIoU_fg5"]) for r in block
                               if r["condition"] == c and r["method"] in ("confidence", "entropy"))
                        for c in own}
            gain = 100*family_average({c: own[c]-controls[c] for c in own})
            print(f"seed={seed} model={name} full_NoBoundary_family_delta_vs_scalar_pp={gain:+.4f}")
    (BASE / "full_summary.json").write_text(json.dumps(
        dict(candidates=candidates, completed_jobs=14-len(missing), missing=missing,
             scope="exploratory complete Val2, not independent test or guaranteed risk"), indent=2) + "\n")
    raise SystemExit(1 if missing else 0)


if __name__ == "__main__":
    main()
