"""Offline audit of archived D20 Vaihingen counts and frozen development gate."""

import hashlib
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "records/rebuild_v1_d20_vaihingen_seed42_compact_20260928"
CONFIG = ROOT / "configs/rebuild_v1/d20_vaihingen_formal_seed42_20260928.json"
OUTPUT = BASE / "offline_audit.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    # Git's committed bytes preserve the server hashes across Windows CRLF checkout.
    relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    committed = subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=ROOT)
    return hashlib.sha256(committed).hexdigest()


def close(actual, expected, label):
    if not math.isclose(actual, expected, rel_tol=0, abs_tol=1e-10):
        raise RuntimeError(f"{label}: {actual} != {expected}")


def miou_fg5(cm):
    if len(cm) != 6 or any(len(row) != 6 for row in cm):
        raise RuntimeError("CM must be 6x6")
    if any(type(value) is not int or value < 0 for row in cm for value in row):
        raise RuntimeError("CM must contain nonnegative integers")
    values = []
    for cls in range(5):
        intersection = cm[cls][cls]
        union = sum(cm[cls]) + sum(row[cls] for row in cm) - intersection
        if union:
            values.append(intersection / union)
    if not values:
        raise RuntimeError("no foreground class in CM")
    return sum(values) / len(values)


def score(summary, config):
    families = {}
    for name, conditions in config["score_families"].items():
        families[name] = sum(100 * miou_fg5(summary["conditions"][condition]["pooled_cm"])
                             for condition in conditions) / len(conditions)
    return families, sum(families.values()) / len(families)


def main():
    cfg = read(CONFIG)
    decision = read(BASE / "decision.json")
    manifest = read(BASE / "input_manifest.json")
    context = (BASE / "run_context.txt").read_text(encoding="utf-8")
    status = (BASE / "status.tsv").read_text(encoding="utf-8")
    if "\tQUEUE\tCOMPLETE\t0" not in status or "\tANALYSIS\tCOMPLETE\t" not in status:
        raise RuntimeError("queue or analysis did not complete")
    if "HEAD=86d7195aa0ce9b797b92677c2ea6153b14018710" not in context:
        raise RuntimeError("execution commit differs from user-reported formal run")
    if manifest["train_ids"] != cfg["train_ids"] or manifest["development_ids"] != cfg["development_ids"]:
        raise RuntimeError("input manifest split mismatch")
    if manifest["data_root"] != cfg["data_root"] or len(manifest["files"]) != 87:
        raise RuntimeError("input manifest root/count mismatch")
    if any(not path.startswith("/home/jovyan/zzx/") or item["size"] <= 0 or
           len(item["sha256"]) != 64 for path, item in manifest["files"].items()):
        raise RuntimeError("input manifest path/size/checksum malformed")
    if decision["status"] != "COMPLETE" or decision["signature"]["config_sha256"] != sha(CONFIG):
        raise RuntimeError("decision config/status mismatch")
    if decision["signature"]["source_sha256"] != sha(ROOT / "scripts/d20_vaihingen_decide.py"):
        raise RuntimeError("decision implementation changed")
    if decision["development_ids"] != cfg["development_ids"] or decision["seed"] != 42:
        raise RuntimeError("decision split/seed mismatch")
    if decision["test6_loaded"] is not False or decision["independent_final_loaded"] is not False:
        raise RuntimeError("sealed evaluation data policy mismatch")
    summaries = {}
    for arm in cfg["arms"]:
        train = read(BASE / f"{arm}_train_summary.json")
        evaluation_path = BASE / f"{arm}_eval_summary.json"
        summary = read(evaluation_path)
        summaries[arm] = summary
        if f"\tTRAIN_{arm}\tCOMPLETE\t" not in status or f"\tEVAL_{arm}\tCOMPLETE\t" not in status:
            raise RuntimeError(f"incomplete archived train/eval status: {arm}")
        signature = train["signature"]
        if signature["config_sha256"] != sha(CONFIG) or signature["input_manifest_sha256"] != sha(BASE / "input_manifest.json"):
            raise RuntimeError(f"training source/data binding mismatch: {arm}")
        if signature["arm"] != arm or signature["train_ids"] != cfg["train_ids"] or signature["development_ids"] != cfg["development_ids"]:
            raise RuntimeError(f"training arm/split mismatch: {arm}")
        if train["global_step"] != cfg["train_steps"] or train["checkpoint_selection"] != "fixed_final_step":
            raise RuntimeError(f"training budget/selection mismatch: {arm}")
        if train["development_labels_loaded"] is not False or train["test6_loaded"] is not False:
            raise RuntimeError(f"training data leakage flag: {arm}")
        if summary["signature"]["training"] != signature or summary["signature"]["checkpoint_sha256"] != train["checkpoint_sha256"]:
            raise RuntimeError(f"evaluation/checkpoint binding mismatch: {arm}")
        if summary["development_ids"] != cfg["development_ids"] or set(summary["conditions"]) != set(cfg["evaluation_conditions"]):
            raise RuntimeError(f"evaluation scope mismatch: {arm}")
        if summary["test6_loaded"] is not False or summary["independent_final_loaded"] is not False:
            raise RuntimeError(f"evaluation data leakage flag: {arm}")
        if decision["signature"]["summary_sha256"][arm] != sha(evaluation_path):
            raise RuntimeError(f"decision input hash mismatch: {arm}")
        for condition in cfg["evaluation_conditions"]:
            item = summary["conditions"][condition]
            if set(item["tiles"]) != {str(tile) for tile in cfg["development_ids"]}:
                raise RuntimeError(f"missing tile: {arm} {condition}")
            pooled = [[0] * 6 for _ in range(6)]
            for tile, row in item["tiles"].items():
                cm = row["cm"]
                close(miou_fg5(cm), row["metrics"]["mIoU_fg5"], f"tile mIoU {arm}/{condition}/{tile}")
                if sum(map(sum, cm)) != row["valid_pixels"]:
                    raise RuntimeError(f"tile valid-pixel count mismatch: {arm}/{condition}/{tile}")
                for i in range(6):
                    for j in range(6):
                        pooled[i][j] += cm[i][j]
            if pooled != item["pooled_cm"]:
                raise RuntimeError(f"pooled CM mismatch: {arm}/{condition}")
            close(miou_fg5(pooled), item["pooled_metrics"]["mIoU_fg5"], f"pooled mIoU {arm}/{condition}")
    scored = {arm: score(summary, cfg) for arm, summary in summaries.items()}
    control = max(("P0", "P1"), key=lambda arm: scored[arm][1])
    gain = scored["P2"][1] - scored[control][1]
    if decision["control_for_macro"] != control:
        raise RuntimeError("stronger-control selection mismatch")
    close(gain, decision["macro_gain_pp"], "macro gain")
    for arm in cfg["arms"]:
        close(scored[arm][1], decision["scores"][arm]["macro_pp"], f"macro {arm}")
        for name, value in scored[arm][0].items():
            close(value, decision["scores"][arm]["families"][name], f"family {arm}/{name}")
    delta = {name: scored["P2"][0][name] - scored["P0"][0][name] for name in cfg["score_families"]}
    for name, value in delta.items():
        close(value, decision["family_delta_vs_P0_pp"][name], f"family delta {name}")
    tile_delta = {}
    for tile in cfg["development_ids"]:
        row = {}
        for name, conditions in cfg["score_families"].items():
            row[name] = sum(100 * (miou_fg5(summaries["P2"]["conditions"][condition]["tiles"][str(tile)]["cm"]) -
                                   miou_fg5(summaries["P0"]["conditions"][condition]["tiles"][str(tile)]["cm"]))
                            for condition in conditions) / len(conditions)
            close(row[name], decision["tile_family_delta_vs_P0_pp"][str(tile)][name], f"tile family {tile}/{name}")
        tile_delta[str(tile)] = row
    guard = cfg["development_gate_pp"]
    checks = dict(gain=gain >= guard["macro_gain_over_stronger_control_min"],
                  clean=delta["clean"] >= -guard["clean_loss_vs_P0_max"],
                  families=min(delta.values()) >= -guard["family_loss_vs_P0_max"],
                  tile_clean=all(row["clean"] >= -guard["tile_clean_loss_vs_P0_max"] for row in tile_delta.values()),
                  tile_families=all(min(row.values()) >= -guard["tile_family_loss_vs_P0_max"] for row in tile_delta.values()))
    if checks != decision["checks"] or all(checks.values()) != decision["passed"]:
        raise RuntimeError("frozen development gate recomputation mismatch")
    paired = decision["paired_by_tile"]
    for tile in cfg["development_ids"]:
        for condition in cfg["evaluation_conditions"]:
            for comparator, counts in paired[str(tile)][condition].items():
                if counts["valid"] != sum(counts[key] for key in
                   ("both_correct", "only_p2_correct", "only_control_correct", "both_wrong")):
                    raise RuntimeError(f"paired pixel partition mismatch: {tile}/{condition}/{comparator}")
                if counts["valid"] != summaries["P2"]["conditions"][condition]["tiles"][str(tile)]["valid_pixels"]:
                    raise RuntimeError(f"paired valid-pixel mismatch: {tile}/{condition}/{comparator}")
    for comparator, conditions in decision["paired_pooled"].items():
        for condition, counts in conditions.items():
            for key, value in counts.items():
                if value != sum(paired[str(tile)][condition][comparator][key] for tile in cfg["development_ids"]):
                    raise RuntimeError(f"paired pooled mismatch: {comparator}/{condition}/{key}")
    failed_tiles = {tile: row for tile, row in tile_delta.items()
                    if row["clean"] < -guard["tile_clean_loss_vs_P0_max"] or
                    min(row.values()) < -guard["tile_family_loss_vs_P0_max"]}
    report = dict(status="PASS", archive_commit="5538bf3", run_commit="86d7195",
                  arms=cfg["arms"], conditions=len(cfg["evaluation_conditions"]),
                  development_tiles=len(cfg["development_ids"]),
                  cm_rows_checked=len(cfg["arms"]) * len(cfg["evaluation_conditions"]) * len(cfg["development_ids"]),
                  stronger_control=control, macro_gain_pp=gain,
                  checks=checks, passed=all(checks.values()), failed_tiles=failed_tiles,
                  scope_limit="Archived counts and hashes only; raw rasters, checkpoints and predictions remain on server and were not independently reopened")
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
