"""Offline audit of the eight GitHub-archived D15 summaries; no dataset access."""
import hashlib
import json
import subprocess
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "records/rebuild_v1_d15_compact_20260926"
MODELS = ("R01", "R05", "C-OO-QD", "D15_DSM_ONLY")
PRIMARY = ("rgb_down2", "rgb_down4", "rgb_blur5", "rgb_local_down4_q1")


def digest_blob(commit, path):
    return hashlib.sha256(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)).hexdigest()


def miou(cm):
    cm = np.asarray(cm, dtype=np.int64)
    assert cm.shape == (6, 6) and (cm >= 0).all()
    tp = np.diag(cm).astype(float)
    union = cm.sum(0) + cm.sum(1) - tp
    iou = np.divide(tp, union, out=np.full(6, np.nan), where=union > 0)
    return float(np.nanmean(iou[:5]))


def main():
    data = {}
    for seed in (42, 17):
        for model in MODELS:
            path = BASE / f"server_{model}_seed{seed}_summary.json"
            d = json.loads(path.read_text())
            assert d["seed"] == seed and d["model"] == model
            assert d["test6_loaded"] is False and d["smoke"] is False
            assert d["config_sha256"] == digest_blob(d["git_commit"], "configs/rebuild_v1/d15_capability_20260926.json")
            assert d["source_sha256"] == digest_blob(d["git_commit"], "scripts/eval_rebuild_v1_d15_capability.py")
            for condition, entry in d["conditions"].items():
                assert set(entry["tiles"]) == {"3_11", "5_10"}
                counts = entry["joint_noboundary"]
                assert counts["valid"] == sum(v for k, v in counts.items() if k != "valid")
                for scope in ("full", "noboundary"):
                    pooled = entry["pooled"][scope]
                    for field, metric in (("cm", "metrics"), ("oracle_cm", "oracle_metrics")):
                        cm = np.asarray(pooled[field], dtype=np.int64)
                        tile_sum = sum(np.asarray(t["metrics"][scope][field], dtype=np.int64)
                                       for t in entry["tiles"].values())
                        assert np.array_equal(cm, tile_sum)
                        assert abs(miou(cm) - pooled[metric]["mIoU_fg5"]) < 1e-12
                        assert int(cm.sum()) == pooled[metric]["valid_pixels"]
                    assert counts["valid"] == entry["pooled"]["noboundary"]["metrics"]["valid_pixels"]
            if model in ("R01", "D15_DSM_ONLY"):
                for scope in ("full", "noboundary"):
                    assert d["conditions"]["clean"]["pooled"][scope]["cm"] == d["checkpoint"]["clean_cm_" + scope]
            data[seed, model] = d
        for model in MODELS:
            assert data[seed, model]["r01_checkpoint"]["sha256"] == data[seed, "R01"]["checkpoint"]["sha256"]
        for model in ("R01", "C-OO-QD"):
            for scope in ("full", "noboundary"):
                assert data[seed, model]["conditions"]["rgb_down4"]["pooled"][scope]["cm"] == data[seed, model]["conditions"]["rgb_down4_dsm_zero"]["pooled"][scope]["cm"]
        for condition in PRIMARY:
            for scope in ("full", "noboundary"):
                assert data[seed, "D15_DSM_ONLY"]["conditions"]["clean"]["pooled"][scope]["cm"] == data[seed, "D15_DSM_ONLY"]["conditions"][condition]["pooled"][scope]["cm"]
    decision = json.loads((BASE / "decision.json").read_text())
    assert decision["status"] == "COMPLETE" and decision["missing"] == []
    rows = []
    for row in decision["rows"]:
        seed, condition = row["seed"], row["condition"]
        scores = {m: 100 * miou(data[seed, m]["conditions"][condition]["pooled"]["noboundary"]["cm"]) for m in MODELS}
        delta = scores["R05"] - max(scores["R01"], scores["C-OO-QD"])
        assert abs(delta - row["r05_minus_best_rgb_pp"]) < 1e-10
        rows.append(dict(seed=seed, condition=condition, delta_pp=delta))
    means = {seed: float(np.mean([r["delta_pp"] for r in rows if r["seed"] == seed])) for seed in (42, 17)}
    gate = all(means[s] >= .2 and sum(r["delta_pp"] > 0 for r in rows if r["seed"] == s) >= 3 for s in (42, 17))
    assert gate == decision["rgb_degradation_gate_pass"]
    result = dict(status="PASS", summaries=8, means_pp=means, gate=gate,
                  checks="Git-blob config/evaluator hashes, per-tile CM sums, offline mIoU, checkpoint clean CMs, paired pixel counts, reference hashes, input invariance, decision recomputation",
                  limitation="Server checkpoint bytes and raw data were not available for independent rehash/reinference; Val2 is exploratory.")
    (BASE / "offline_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
