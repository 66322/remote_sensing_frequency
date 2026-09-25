"""Offline D15 coverage and prespecified exploratory decision."""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
CONFIG = ROOT / "configs/rebuild_v1/d15_capability_20260926.json"
BASE = ROOT / "records/rebuild_v1_d15_capability_20260926"


def main():
    cfg = json.loads(CONFIG.read_text())
    data, missing = {}, []
    for seed in cfg["seeds"]:
        data[seed] = {}
        for model in cfg["models"]:
            p = BASE / f"{model}_seed{seed}/summary.json"
            if not p.is_file():
                missing.append(f"{model}_seed{seed}")
                continue
            d = json.loads(p.read_text())
            if d["seed"] != seed or d["model"] != model or d["smoke"] or d["test6_loaded"] is not False:
                raise RuntimeError(f"D15 summary invalid: {p}")
            if list(d["conditions"]) != cfg["rgb_conditions"]:
                raise RuntimeError(f"D15 condition coverage mismatch: {p}")
            data[seed][model] = d
    decision = dict(status="INCOMPLETE" if missing else "COMPLETE",
                    missing=missing, test6_loaded=False,
                    recorded_at=datetime.now().astimezone().isoformat(timespec="seconds"))
    if not missing:
        rows, seed_pass = [], {}
        primary = ("rgb_down2", "rgb_down4", "rgb_blur5", "rgb_local_down4_q1")
        for seed in cfg["seeds"]:
            deltas = []
            for condition in primary:
                scores = {model: 100 * data[seed][model]["conditions"][condition]["pooled"]
                          ["noboundary"]["metrics"]["mIoU_fg5"] for model in cfg["models"]}
                delta = scores["R05"] - max(scores["R01"], scores["C-OO-QD"])
                deltas.append(delta)
                rows.append(dict(seed=seed, condition=condition, scores_percent=scores,
                                 r05_minus_best_rgb_pp=delta))
            seed_pass[seed] = (sum(deltas) / len(deltas) >= 0.2 and sum(x > 0 for x in deltas) >= 3)
        decision.update(rows=rows, seed_pass=seed_pass,
                        rgb_degradation_gate_pass=all(seed_pass.values()),
                        gate_definition="Both seeds: R05 mean >= best(R01,C-OO-QD) +0.2 pp across four predeclared RGB degradations and positive on >=3/4; exploratory only")
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / "decision.json").write_text(json.dumps(decision, indent=2, allow_nan=False) + "\n")
    print(f"D15 {decision['status']} missing={missing}")
    if not missing:
        for row in decision["rows"]:
            print(f"seed{row['seed']} {row['condition']} delta={row['r05_minus_best_rgb_pp']:+.4f} pp")
        print("RGB_DEGRADATION_GATE", decision["rgb_degradation_gate_pass"])


if __name__ == "__main__":
    main()
