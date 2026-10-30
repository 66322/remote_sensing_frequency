"""Freeze input-space class prototypes from Potsdam Train16 labels only."""

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import numpy as np

import train_rebuild_v1_r02_budget_pilot as r02
from d9b_observable_features import RADII, sampled_observables

OUT = ROOT / "records/rebuild_v1_d9b_train16_prototypes_20260923"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(parts):
    stacked = [np.concatenate(group, axis=0).astype(np.float64) for group in parts]
    all_values = np.concatenate(stacked, axis=0)
    mean = all_values.mean(axis=0)
    std = np.maximum(all_values.std(axis=0), 1e-4)
    normalized = [(values - mean) / std for values in stacked]
    return {"global_mean": mean.tolist(), "global_std": std.tolist(),
            "class_mean": [values.mean(axis=0).tolist() for values in normalized],
            "class_std": [np.maximum(values.std(axis=0), 0.5).tolist() for values in normalized],
            "class_support": [len(values) for values in stacked]}


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    cfg_path = ROOT / "configs/rebuild_v1/r05_quality_plus_dropout_16k.json"
    cfg = r02.read_json(cfg_path)
    split_path = ROOT / cfg["split_file"]
    split = r02.read_json(split_path)
    ids = list(split["train16"])
    if len(ids) != 16 or set(ids) & (set(split["val2"]) | set(split["historical_exposed_test6"])):
        raise RuntimeError("Train16 split isolation failed")
    parts = {modality: [[] for _ in range(r02.N_CLASSES)] for modality in ("rgb", "dsm")}
    tile_support = {}
    for tile in ids:
        print("D9B PROTOTYPE TRAIN16", tile, flush=True)
        data = r02.load_tile(Path(cfg["data_root"]), tile, need_nb=False)
        gt = data["full_gt"]
        valid = np.flatnonzero((gt != r02.IGNORE_INDEX) & (gt < r02.N_CLASSES))
        rng = np.random.default_rng(20260923 + int(tile.replace("_", "")))
        chosen = rng.choice(valid, size=min(200000, valid.size), replace=False)
        yy, xx = np.unravel_index(chosen, gt.shape)
        labels = gt[yy, xx]
        counts = {}
        for cls in range(r02.N_CLASSES):
            members = np.flatnonzero(labels == cls)
            if members.size > 5000:
                members = rng.choice(members, size=5000, replace=False)
            counts[r02.CLASS_NAMES[cls]] = int(members.size)
            if not members.size:
                continue
            rgb_feat, dsm_feat, _ = sampled_observables(data["optical"], data["dsm"],
                                                        yy[members], xx[members])
            parts["rgb"][cls].append(rgb_feat)
            parts["dsm"][cls].append(dsm_feat)
        tile_support[tile] = counts
    if any(sum(len(x) for x in modality_class) == 0
           for modality in parts.values() for modality_class in modality):
        raise RuntimeError("missing class in Train16 prototype sample")
    stats = {modality: summarize(parts[modality]) for modality in parts}
    if any(n < 1000 for n in stats["rgb"]["class_support"]):
        raise RuntimeError("insufficient class support for prototype screen")
    payload = {"experiment_id": "D9B_TRAIN16_INPUT_PROTOTYPES",
               "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
               "source_split": "train16", "tile_ids": ids,
               "val2_loaded": False, "test6_loaded": False,
               "feature_definition": "RGB channels and RGB/DSM centered edge magnitudes at radii 2,8; per-tile normalized DSM",
               "radii": list(RADII), "sample_per_tile_max": 200000,
               "sample_per_class_per_tile_max": 5000,
               "class_names": r02.CLASS_NAMES, "tile_support": tile_support,
               "source_sha256": {str(cfg_path): sha(cfg_path), str(split_path): sha(split_path)},
               "prototype_type": "handcrafted multiscale class-conditional input prototype; not an SGMA deep-feature replication",
               **stats}
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / "prototypes.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("D9B PROTOTYPES COMPLETE", OUT, flush=True)


if __name__ == "__main__":
    main()
