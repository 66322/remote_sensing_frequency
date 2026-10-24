"""CPU-only frozen Vaihingen seed42 development gate and paired-pixel audit."""

import json
from pathlib import Path

import numpy as np
from skimage import io

import d18_d19_night as d18
import train_rebuild_v1_r02_budget_pilot as r02

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rebuild_v1/d20_vaihingen_formal_seed42_20260928.json"
RECORD = ROOT / "records/rebuild_v1_d20_vaihingen_seed42_20260928"


def score(summary, cfg):
    conditions = {condition: 100 * summary["conditions"][condition]["pooled_metrics"]["mIoU_fg5"]
                  for condition in cfg["evaluation_conditions"]}
    families = {name: sum(conditions[c] for c in group) / len(group)
                for name, group in cfg["score_families"].items()}
    return dict(conditions=conditions, families=families,
                macro_pp=sum(families.values()) / len(families))


def load_prediction(arm, condition, tile, summary):
    path = RECORD / arm / condition / f"tile_{tile}.npy"
    row = summary["conditions"][condition]["tiles"][str(tile)]
    if d18.sha(path) != row["prediction_sha256"]:
        raise RuntimeError(f"prediction checksum changed: {arm} {condition} {tile}")
    return np.load(path, allow_pickle=False)


def main():
    cfg = d18.read(CONFIG)
    summaries = {arm: d18.read(RECORD / arm / "summary.json") for arm in cfg["arms"]}
    if any(summary["signature"]["training"]["config_sha256"] != d18.sha(CONFIG)
           for summary in summaries.values()):
        raise RuntimeError("evaluation config binding mismatch")
    if any(summary["development_ids"] != cfg["development_ids"] or
           set(summary["conditions"]) != set(cfg["evaluation_conditions"]) or
           summary["test6_loaded"] is not False or summary["independent_final_loaded"] is not False
           for summary in summaries.values()):
        raise RuntimeError("development evaluation incomplete or sealed data violated")
    summary_hashes = {arm: d18.sha(RECORD / arm / "summary.json") for arm in cfg["arms"]}
    signature = dict(config_sha256=d18.sha(CONFIG), source_sha256=d18.sha(Path(__file__)),
                     summary_sha256=summary_hashes)
    decision_path = RECORD / "decision.json"
    if decision_path.is_file():
        previous = d18.read(decision_path)
        if previous["signature"] != signature:
            raise RuntimeError("existing decision binding differs")
        print("DECISION REUSED", previous["status"], flush=True)
        return
    scores = {arm: score(summary, cfg) for arm, summary in summaries.items()}
    control = max(("P0", "P1"), key=lambda arm: scores[arm]["macro_pp"])
    candidate = scores["P2"]
    p0 = scores["P0"]
    gate = cfg["development_gate_pp"]
    family_delta = {name: candidate["families"][name] - p0["families"][name]
                    for name in cfg["score_families"]}
    tile_families = {}
    for tile in cfg["development_ids"]:
        deltas = {}
        for name, group in cfg["score_families"].items():
            values = []
            for condition in group:
                p2m = summaries["P2"]["conditions"][condition]["tiles"][str(tile)]["metrics"]["mIoU_fg5"]
                p0m = summaries["P0"]["conditions"][condition]["tiles"][str(tile)]["metrics"]["mIoU_fg5"]
                if p2m is None or p0m is None:
                    raise RuntimeError(f"missing foreground mIoU for tile {tile} {condition}")
                values.append(100 * (p2m - p0m))
            deltas[name] = sum(values) / len(values)
        tile_families[str(tile)] = deltas
    macro_gain = candidate["macro_pp"] - scores[control]["macro_pp"]
    checks = {
        "gain": macro_gain >= gate["macro_gain_over_stronger_control_min"],
        "clean": family_delta["clean"] >= -gate["clean_loss_vs_P0_max"],
        "families": min(family_delta.values()) >= -gate["family_loss_vs_P0_max"],
        "tile_clean": all(row["clean"] >= -gate["tile_clean_loss_vs_P0_max"]
                          for row in tile_families.values()),
        "tile_families": all(min(row.values()) >= -gate["tile_family_loss_vs_P0_max"]
                             for row in tile_families.values()),
    }
    paired = {}
    data_root = Path(cfg["data_root"]).resolve()
    data_root.relative_to(Path("/home/jovyan/zzx").resolve())
    for tile in cfg["development_ids"]:
        label_path = data_root / cfg["development_label_directory"] / f"top_mosaic_09cm_area{tile}.tif"
        label = r02.convert_full_gt(io.imread(str(label_path)))
        tile_rows = {}
        for condition in cfg["evaluation_conditions"]:
            predictions = {arm: load_prediction(arm, condition, tile, summaries[arm])
                           for arm in cfg["arms"]}
            if any(pred.shape != label.shape for pred in predictions.values()):
                raise RuntimeError(f"prediction shape mismatch: {condition} {tile}")
            row = {}
            for comparator in sorted({"P0", control}):
                a = predictions["P2"] == label
                b = predictions[comparator] == label
                row[comparator] = dict(valid=int(label.size), both_correct=int((a & b).sum()),
                    only_p2_correct=int((a & ~b).sum()), only_control_correct=int((~a & b).sum()),
                    both_wrong=int((~a & ~b).sum()))
                if sum(row[comparator][key] for key in
                       ("both_correct", "only_p2_correct", "only_control_correct", "both_wrong")) != label.size:
                    raise RuntimeError("paired count partition mismatch")
            tile_rows[condition] = row
        paired[str(tile)] = tile_rows
        print(f"PAIRED {tile}", flush=True)
    aggregate = {comparator: {} for comparator in sorted({"P0", control})}
    for comparator in aggregate:
        for condition in cfg["evaluation_conditions"]:
            aggregate[comparator][condition] = {
                key: sum(paired[str(tile)][condition][comparator][key] for tile in cfg["development_ids"])
                for key in ("valid", "both_correct", "only_p2_correct", "only_control_correct", "both_wrong")}
    result = dict(status="COMPLETE", signature=signature,
        evidence_level=cfg["evidence_level"], seed=42, scores=scores,
        control_for_macro=control, macro_gain_pp=macro_gain,
        family_delta_vs_P0_pp=family_delta, tile_family_delta_vs_P0_pp=tile_families,
        checks=checks, passed=all(checks.values()), paired_by_tile=paired, paired_pooled=aggregate,
        development_ids=cfg["development_ids"], test6_loaded=False,
        independent_final_loaded=False, seed17_auto_launched=False,
        interpretation="Development resource gate only; same mosaic, prior scene exposure, no independent final confirmation")
    d18.write(decision_path, result)
    print("D20 VAI DEVELOPMENT DECISION", result["passed"],
          f"macro_gain_pp={macro_gain:.4f}", checks, flush=True)


if __name__ == "__main__":
    main()
