"""D13 predeclared continuation gate and compact unattended summaries."""
import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
sys.path.insert(0, str(ROOT / "scripts"))
import train_rebuild_v1_r02_budget_pilot as r02
from train_rebuild_v1_d13_residual import CONFIG, RUN_LABEL, sha256

BASE = ROOT / f"records/rebuild_v1_d13_residual_{RUN_LABEL}"


def condition_value(result, condition, name):
    return float(result["data"][condition]["noboundary"][name])


def family_mean(result, field):
    cfg = r02.read_json(CONFIG)
    families = cfg["evaluation"]["families"]
    values = []
    for conditions in families.values():
        if field == "mIoU":
            values.append(sum(result["data"][c]["noboundary"]["metrics"]["mIoU_fg5"]
                              for c in conditions) / len(conditions))
        else:
            values.append(sum(condition_value(result, c, field) for c in conditions)/len(conditions))
    return float(sum(values)/len(values))


def gate_for_seed(results, seed):
    cfg = r02.read_json(CONFIG)["evaluation"]
    current = results[("dsm_risk", seed)]
    other = {arm: results[(arm, seed)] for arm in ("rgb_ce", "dsm_ce", "rgb_risk")}
    score = family_mean(current, "mIoU")
    best_control = max((family_mean(r, "mIoU"), arm) for arm, r in other.items())
    ce = other["dsm_ce"]
    harm, ce_harm = family_mean(current, "H"), family_mean(ce, "H")
    rescue, ce_rescue = family_mean(current, "R"), family_mean(ce, "R")
    available = [c for family in cfg["families"].values() for c in family]
    worst = max(float(v["noboundary"]["H"])
                for c in available for v in current["data"][c]["tiles"].values())
    clean = current["data"]["clean"]["noboundary"]["metrics"]["mIoU_fg5"]
    noise = current["data"]["dsm_noise_std010"]["noboundary"]["metrics"]["mIoU_fg5"]
    baseline = current["baseline"]["noboundary"]["metrics"]["mIoU_fg5"]
    checks = {
        "family_gain": 100*(score-best_control[0]) >= float(cfg["minimum_mean_gain_pp"])-1e-10,
        "harm_reduction": harm <= ce_harm*(1-float(cfg["minimum_harm_reduction_fraction"]))+1e-12,
        "rescue_retention": rescue >= ce_rescue*float(cfg["minimum_rescue_retention_fraction"])-1e-12,
        "worst_harm": worst <= float(cfg["max_worst_tile_condition_harm_fraction"])+1e-12,
        "clean_vs_R01": clean >= baseline-1e-12,
        "noise_vs_R01": 100*(noise-baseline) >= -float(cfg["max_noise_below_r01_pp"])-1e-10,
        "missing_fallback": all(current["data"][c]["noboundary"]["harm_count"] == 0
                                for c in ("dsm_zero",)),
    }
    return dict(seed=seed, passed=all(checks.values()), checks=checks,
                family_mIoU_percent=100*score, best_control=best_control[1],
                family_gain_pp=100*(score-best_control[0]),
                family_H_percent=100*harm, dsm_ce_H_percent=100*ce_harm,
                family_R_percent=100*rescue, dsm_ce_R_percent=100*ce_rescue,
                worst_tile_condition_H_percent=100*worst,
                clean_minus_R01_pp=100*(clean-baseline),
                noise_minus_R01_pp=100*(noise-baseline))


def load_results(arms, seeds):
    results, missing = {}, []
    expected_sha = sha256(CONFIG)
    for arm in arms:
        for seed in seeds:
            path = BASE / f"{arm}_seed{seed}" / "summary.json"
            if not path.is_file():
                missing.append(f"{arm}_seed{seed}")
                continue
            value = json.loads(path.read_text())
            if (value["arm"] != arm or value["seed"] != seed or value["test6_loaded"] is not False
                    or value["config_sha256"] != expected_sha
                    or value["train_steps"] != int(r02.read_json(CONFIG)["training"]["steps"])):
                raise RuntimeError(f"invalid D13 evidence {path}")
            results[(arm, seed)] = value
    return results, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("stage1", "final"), required=True)
    args = ap.parse_args()
    cfg = r02.read_json(CONFIG)
    seeds = cfg["seeds"]
    results, missing = load_results(cfg["stage1_arms"], seeds)
    if missing:
        gate = dict(status="INCOMPLETE", stage1_pass=False, missing=missing,
                    reason="not all paired full-image Stage 1 evaluations completed")
    else:
        for seed in seeds:
            pair = [results[(arm, seed)] for arm in cfg["stage1_arms"]]
            for key in ("anchor_sha256", "initial_head_sha256", "treatment_counts"):
                if any(p[key] != pair[0][key] for p in pair[1:]):
                    raise RuntimeError(f"D13 matched Stage 1 {key} diverged for seed {seed}")
        decisions = [gate_for_seed(results, seed) for seed in seeds]
        gate = dict(status="COMPLETE", stage1_pass=all(x["passed"] for x in decisions),
                    seed_decisions=decisions, missing=[],
                    reason="both seeds passed" if all(x["passed"] for x in decisions)
                    else "one or both seeds failed the prespecified Stage 1 gate")
    gate.update(recorded_at=datetime.now().astimezone().isoformat(timespec="seconds"),
                config_sha256=sha256(CONFIG), val2_exploratory=True, test6_loaded=False)
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / "stage1_decision.json").write_text(json.dumps(gate, indent=2, allow_nan=False)+"\n")
    print("D13 STAGE1", gate["status"], gate["reason"], flush=True)
    for row in gate.get("seed_decisions", []):
        print("seed", row["seed"], "pass", row["passed"], "gain_pp", round(row["family_gain_pp"], 4),
              "H_percent", round(row["family_H_percent"], 4), "R_percent", round(row["family_R_percent"], 4),
              "checks", row["checks"], flush=True)
    if args.stage == "final":
        extended = dict(gate=gate, stage2_status="SKIPPED", stage2_rows=[])
        if gate["stage1_pass"]:
            extra, absent = load_results(cfg["stage2_arms"], seeds)
            if absent:
                extended["stage2_status"] = "INCOMPLETE"
                extended["stage2_missing"] = absent
            else:
                extended["stage2_status"] = "COMPLETE"
                for seed in seeds:
                    reference = results[("dsm_risk", seed)]
                    for arm in cfg["stage2_arms"]:
                        for key in ("anchor_sha256", "initial_head_sha256", "treatment_counts"):
                            if extra[(arm, seed)][key] != reference[key]:
                                raise RuntimeError(f"D13 Stage 2 matched {key} diverged: {arm}/{seed}")
                for arm in cfg["stage2_arms"]:
                    for seed in seeds:
                        value = extra[(arm, seed)]
                        base = results[("dsm_risk", seed)]
                        capacity = extra[("dsm_capacity", seed)]
                        row = dict(arm=arm, seed=seed,
                                   family_mIoU_percent=100*family_mean(value, "mIoU"),
                                   minus_DSM_risk_pp=100*(family_mean(value, "mIoU")-family_mean(base, "mIoU")),
                                   minus_capacity_pp=100*(family_mean(value, "mIoU")-family_mean(capacity, "mIoU")),
                                   family_H_percent=100*family_mean(value, "H"),
                                   family_R_percent=100*family_mean(value, "R"))
                        extended["stage2_rows"].append(row)
                        print("STAGE2", row, flush=True)
                extended["stable_feature_increment"] = {
                    arm: all(row["minus_DSM_risk_pp"] > 0 and row["minus_capacity_pp"] > 0
                             for row in extended["stage2_rows"] if row["arm"] == arm)
                    for arm in ("dsm_semantic", "dsm_frequency", "dsm_semantic_frequency")
                }
        (BASE / "final_decision.json").write_text(json.dumps(extended, indent=2, allow_nan=False)+"\n")
        print("D13 FINAL stage2", extended["stage2_status"], flush=True)


if __name__ == "__main__":
    main()
