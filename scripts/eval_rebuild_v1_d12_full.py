"""Full-image confirmation for at most two frozen D12 candidates per seed/condition."""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
import eval_rebuild_v1_d9a_benefit as d9a
import train_rebuild_v1_r01_optical_only as r01
import train_rebuild_v1_r02_budget_pilot as r02
from d10m_mechanism import sampled_structure
from d11_benefit_probe import features as d11_features, probabilities as d11_probabilities
from d12_night_probe import ROOT, CFG, BASE, D11, features, predict
from d12_semantic import infer_at_pixels
from eval_rebuild_v1_d4_expert_complementarity import validate_run
from eval_rebuild_v1_d5_confidence_routing import softmax_np
from export_rebuild_v1_d12_semantic import treated_dsm


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, choices=(17, 42), required=True)
    parser.add_argument("--condition", required=True)
    args = parser.parse_args()
    cfg = json.loads(CFG.read_text())
    decision = json.loads((BASE / "decision.json").read_text())
    candidates = decision["full_resolution_candidates"]
    if not candidates or args.condition not in cfg["evaluation_conditions"]:
        raise ValueError("no frozen candidate or invalid condition")
    out = BASE / "full_resolution" / f"seed{args.seed}_{args.condition}"
    out.resolve().relative_to(Path("/home/jovyan/zzx").resolve())
    if out.exists():
        raise FileExistsError(out)
    models = {}
    identity = None
    for name in candidates:
        path = BASE / "models" / f"seed{args.seed}_{name}" / "model.json"
        model = json.loads(path.read_text())
        if model["seed"] != args.seed or model["model"] != name:
            raise RuntimeError("candidate model mismatch")
        if identity is None:
            identity = model["checkpoint_identity"]
        elif identity != model["checkpoint_identity"]:
            raise RuntimeError("candidate experts differ")
        models[name] = model
    scalar = {name: json.loads((D11 / "models" / f"seed{args.seed}_{name}" / "model.json").read_text())
              for name in ("confidence", "entropy")}
    c1 = r02.read_json(ROOT / "configs/rebuild_v1/r01_optical_only_16k.json")
    c5 = r02.read_json(ROOT / "configs/rebuild_v1/r05_quality_plus_dropout_16k.json")
    _, ck1 = validate_run(ROOT / f"runs/rebuild_v1/R01_optical_only_seed{args.seed}_sched16000_stop16000")
    _, ck5 = validate_run(ROOT / f"runs/rebuild_v1/R05_dual_f0_quality_plus_dropout_seed{args.seed}_sched16000_stop16000")
    s1, s5 = torch.load(ck1, map_location="cpu"), torch.load(ck5, map_location="cpu")
    actual = dict(checkpoint_rgb=str(ck1), checkpoint_dual=str(ck5),
                  checkpoint_steps=[int(s1["global_step"]), int(s5["global_step"])])
    if identity != actual:
        raise RuntimeError("full-resolution expert checkpoint mismatch")
    net1, _, _ = r01.build_model(c1, Path(c1["pretrain"]), resume_state=s1)
    net5, _ = r02.build_model(c5, Path(c5["pretrain"]), resume_state=s5)
    net1.eval(); net5.eval()
    patch, stride, batch = int(c5["patch"]), int(c5["validation"]["stride"]), int(c5["validation"]["inference_batch"])
    rows = []
    cms = {}
    counts = {}
    for tile in cfg["evaluation"]:
        d = r02.load_tile(Path(c5["data_root"]), tile, need_nb=True)
        treated = treated_dsm(d["dsm"], args.condition, tile)
        h, w = d["full_gt"].shape
        yy, xx = np.indices((h, w), dtype=np.int32).reshape(2, -1)
        sem1, score1 = infer_at_pixels(net1, d["optical"], d["dsm"], yy, xx,
                                      patch, stride, batch, True, True)
        sem5, score5 = infer_at_pixels(net5, d["optical"], treated, yy, xx,
                                      patch, stride, batch, False, True)
        rgb_prob, dual_prob = softmax_np(score1), softmax_np(score5)
        del score1, score5
        labels = d["full_gt"].reshape(-1)
        nb_labels = d["noboundary_gt"].reshape(-1)
        rgb_pred, dual_pred = rgb_prob.argmax(0), dual_prob.argmax(0)
        methods = ["RGB", "dual", "confidence", "entropy", *candidates]
        tile_cm = {(split, name): np.zeros((6, 6), np.int64)
                   for split in ("full", "noboundary") for name in methods}
        tile_h = {name: 0 for name in methods}
        tile_r = {name: 0 for name in methods}
        tile_n = 0
        # Work in row strips so feature normalization and the head never see labels.
        for row0 in range(0, h, 256):
            row1 = min(h, row0 + 256)
            lo, hi = row0*w, row1*w
            sy, sx = yy[lo:hi], xx[lo:hi]
            margin0, margin1 = max(0, row0-64), min(h, row1+64)
            freq = sampled_structure(d["optical"][margin0:margin1],
                                     treated[margin0:margin1], sy-margin0, sx)
            sample = dict(rgb_prob=rgb_prob[:, lo:hi], dual_prob=dual_prob[:, lo:hi], **freq)
            semantic = dict(sem_rgb=sem1[:, lo:hi], sem_dual=sem5[:, lo:hi])
            decisions = {"RGB": np.zeros(hi-lo, bool), "dual": np.ones(hi-lo, bool)}
            for name, model in scalar.items():
                x, _ = d11_features(sample, name)
                p = d11_probabilities(model, x)
                decisions[name] = ((p[:, 0] - p[:, 1]) > model["threshold"])
            for name, model in models.items():
                x = features(sample, semantic, name, args.seed, tile, args.condition)
                p = predict(model, x)
                decisions[name] = ((p[:, 0] - p[:, 1]) > model["threshold"])
            eligible = rgb_pred[lo:hi] != dual_pred[lo:hi]
            for name in ("confidence", "entropy", *candidates):
                decisions[name] &= eligible & (args.condition != "dsm_zero")
            for name, chosen in decisions.items():
                prediction = np.where(chosen, dual_pred[lo:hi], rgb_pred[lo:hi])
                for split, gt in (("full", labels[lo:hi]), ("noboundary", nb_labels[lo:hi])):
                    valid = gt != r02.IGNORE_INDEX
                    np.add.at(tile_cm[split, name], (gt[valid], prediction[valid]), 1)
                valid_nb = nb_labels[lo:hi] != r02.IGNORE_INDEX
                tile_h[name] += int(np.sum(valid_nb & (rgb_pred[lo:hi] == nb_labels[lo:hi]) &
                                          (prediction != nb_labels[lo:hi])))
                tile_r[name] += int(np.sum(valid_nb & (rgb_pred[lo:hi] != nb_labels[lo:hi]) &
                                          (prediction == nb_labels[lo:hi])))
            tile_n += int(np.sum(nb_labels[lo:hi] != r02.IGNORE_INDEX))
        for (split, name), cm in tile_cm.items():
            key = (split, name)
            cms[key] = cms.get(key, np.zeros((6, 6), np.int64)) + cm
            m = r02.metrics_from_cm(cm)
            rows.append(dict(seed=args.seed, condition=args.condition, tile=tile, split=split,
                             method=name, valid_pixels=int(cm.sum()), mIoU_fg5=m["mIoU_fg5"],
                             Car_IoU=m["per_class_iou"][4], Building_IoU=m["per_class_iou"][1],
                             harm=None if split == "full" else tile_h[name]/tile_n,
                             rescue=None if split == "full" else tile_r[name]/tile_n,
                             cm_json=json.dumps(cm.tolist(), separators=(",", ":"))))
            if split == "noboundary":
                old = counts.get(name, (0, 0, 0))
                counts[name] = (old[0]+tile_h[name], old[1]+tile_r[name], old[2]+tile_n)
        del d, treated, sem1, sem5, rgb_prob, dual_prob
    for (split, name), cm in cms.items():
        m = r02.metrics_from_cm(cm)
        harm, rescue, n = counts[name]
        rows.append(dict(seed=args.seed, condition=args.condition, tile="ALL", split=split,
                         method=name, valid_pixels=int(cm.sum()), mIoU_fg5=m["mIoU_fg5"],
                         Car_IoU=m["per_class_iou"][4], Building_IoU=m["per_class_iou"][1],
                         harm=None if split == "full" else harm/n,
                         rescue=None if split == "full" else rescue/n,
                         cm_json=json.dumps(cm.tolist(), separators=(",", ":"))))
    out.mkdir(parents=True, exist_ok=False)
    with (out / "metrics.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    summary = dict(seed=args.seed, condition=args.condition, candidates=candidates,
                   checkpoint_identity=identity, model_sha256={name: hashlib.sha256(
                       (BASE / "models" / f"seed{args.seed}_{name}" / "model.json").read_bytes()).hexdigest()
                       for name in candidates}, test6_loaded=False,
                   scope="complete Val2 images; exploratory, not independent confirmation")
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("D12 FULL COMPLETE", out, flush=True)


if __name__ == "__main__":
    main()
