"""Summarize paired D14 intervention sensitivity without a selection gate."""
import json
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
BASE = ROOT / "records/rebuild_v1_d14_dsm_intervention_20260926"
CONFIG = ROOT / "configs/rebuild_v1/d14_dsm_intervention_20260926.json"


def main():
    cfg = json.loads(CONFIG.read_text())
    rows, missing = [], []
    for arm in cfg["arms"]:
        for seed in cfg["seeds"]:
            path = BASE / f"{arm}_seed{seed}" / "summary.json"
            if not path.is_file():
                missing.append(f"{arm}_seed{seed}")
                continue
            d = json.loads(path.read_text())
            if (d["arm"] != arm or d["seed"] != seed or d["smoke"] or
                    d["test6_loaded"] is not False or
                    d["availability_forced_present"] is not True or
                    tuple(d["data"]) != tuple(cfg["interventions"])):
                raise RuntimeError(f"invalid D14 summary {path}")
            clean = d["data"]["clean"]["noboundary"]
            for condition in cfg["interventions"][1:]:
                altered = d["data"][condition]["noboundary"]
                flips = altered["comparison_to_clean"]
                if arm.startswith("rgb_") and flips["flip_count"] != 0:
                    raise RuntimeError(f"RGB control unexpectedly changed: {arm}/{seed}")
                rows.append(dict(arm=arm, seed=seed, condition=condition,
                                 clean_mIoU_percent=100*clean["metrics"]["mIoU_fg5"],
                                 delta_mIoU_pp=100*(altered["metrics"]["mIoU_fg5"]-
                                                    clean["metrics"]["mIoU_fg5"]),
                                 flip_percent=100*flips["flip_fraction"],
                                 flip_count=flips["flip_count"], valid=flips["valid"],
                                 H_percent=100*altered["H"],
                                 R_percent=100*altered["R"]))
    decision = dict(status="COMPLETE" if not missing else "INCOMPLETE",
                    missing=missing, rows=rows, diagnostic_only=True,
                    model_selection=False, test6_loaded=False)
    (BASE / "decision.json").write_text(json.dumps(decision, indent=2, allow_nan=False)+"\n")
    print("D14", decision["status"], "missing", missing, flush=True)
    for row in rows:
        print(row, flush=True)


if __name__ == "__main__":
    main()
