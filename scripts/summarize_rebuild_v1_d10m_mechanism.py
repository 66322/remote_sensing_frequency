"""Summarize D10M once, retaining missing jobs rather than silently dropping them."""
import csv
import json
from pathlib import Path
from d10m_mechanism import CONDITIONS

BASE = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d10m_mechanism_20260923")


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    missing, rows, contrasts = [], [], []
    for seed in (42, 17):
        for condition in CONDITIONS:
            folder = BASE / f"seed{seed}_{condition}"
            if not (folder / "summary.json").exists():
                missing.append(folder.name)
                continue
            meta = json.loads((folder / "summary.json").read_text())
            if meta["seed"] != seed or meta["condition"] != condition or meta["smoke"] or meta["test6_loaded"]:
                raise RuntimeError(f"Invalid completed run: {folder}")
            spectra = read_csv(folder / "spectra.csv")
            for row in read_csv(folder / "metrics.csv"):
                if row["tile"] == "ALL" and row["region"] == "interior":
                    row["max_amplitude_relative_l2"] = max(float(s["amplitude_relative_l2"]) for s in spectra)
                    rows.append(row)
            curves = read_csv(folder / "harm_rescue.csv")
            for tile in meta["val_ids"]:
                subset = {r["score"]: r for r in curves if r["tile"] == tile and r["group"] == "interior" and float(r["harm_budget"]) == .005}
                baseline = max(float(subset[s]["rescue"]) for s in ("confidence_margin", "entropy_margin"))
                contrasts.append(dict(seed=seed, condition=condition, tile=tile,
                                      baseline_rescue=baseline,
                                      structure_r8_rescue=float(subset["structure_r8"]["rescue"]),
                                      delta_rescue=float(subset["structure_r8"]["rescue"])-baseline))
    if not rows:
        raise RuntimeError("No completed D10M runs; inspect queue log")
    for name, content in (("mechanism_summary", rows), ("structure_rescue_contrast", contrasts)):
        with (BASE / f"{name}.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(content[0]), lineterminator="\n")
            writer.writeheader(); writer.writerows(content)
    (BASE / "completion.json").write_text(json.dumps(dict(expected=20, completed=20-len(missing), missing=missing), indent=2)+"\n")
    print("D10M interior NoBoundary; mIoU and R-H in percentage points; FFT error dimensionless")
    print("seed condition FFT_error R01 R05 dual_minus_clean safe_conf safe_entropy dual_H dual_R")
    for seed in (42, 17):
        clean = next((float(r["mIoU_fg5"]) for r in rows if int(r["seed"]) == seed and r["condition"] == "clean" and r["method"] == "R05"), None)
        for condition in CONDITIONS:
            part = {r["method"]: r for r in rows if int(r["seed"]) == seed and r["condition"] == condition}
            if not part:
                continue
            dual = part["R05"]
            scores = [100*float(part[m]["mIoU_fg5"]) for m in ("R01", "R05", "safe_confidence", "safe_entropy")]
            delta = f"{scores[1]-100*clean:+.4f}" if clean is not None else "NA"
            print(seed, condition, f'{float(dual["max_amplitude_relative_l2"]):.2e}',
                  f"{scores[0]:.4f} {scores[1]:.4f}", delta, f"{scores[2]:.4f} {scores[3]:.4f}",
                  f'{100*float(dual["harm"]):.4f} {100*float(dual["rescue"]):.4f}')
    print("Matched harm <=0.5%: structure_r8 minus stronger confidence/entropy rescue (pp); post-hoc only")
    for r in contrasts:
        print(r["seed"], r["condition"], r["tile"], f'{100*r["delta_rescue"]:+.4f}')
    print("COMPLETE", 20-len(missing), "/ 20; missing:", missing)
    raise SystemExit(1 if missing else 0)


if __name__ == "__main__":
    main()
