import os, sys, csv, json, argparse
from datetime import datetime
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import numpy as np
import torch
import torch.nn.functional as F
import train_rebuild_v1_r01_optical_only as r01
import train_rebuild_v1_r02_budget_pilot as r02
from eval_rebuild_v1_d4_expert_complementarity import (
    apply_condition, oracle_prediction, validate_run,
)
from eval_rebuild_v1_local_failure_diagnostics import condition_specs as local_specs


METHODS = (
    "R01_optical", "R05_dual", "prob_avg", "prob_alpha25",
    "prob_alpha75", "max_confidence", "min_entropy",
    "safe_max_confidence", "pixel_oracle",
)


def specs():
    local = local_specs()
    wanted = {"clean"} | {f"dsm_local_zero_q{i}" for i in range(1, 5)} | {
        f"dsm_local_down8_q{i}" for i in range(1, 5)
    }
    out = [x for x in local if x["name"] in wanted]
    return [out[0], {"name": "dsm_zero", "family": "D4_global_missing"},
            {"name": "dsm_down8", "family": "D4_global_down8"}, *out[1:]]


def softmax_np(logits):
    x = torch.from_numpy(logits)
    return F.softmax(x, dim=0).numpy()


def infer_scores(net, optical, dsm, patch, stride, batch, optical_only):
    h, w = optical.shape[:2]
    coords = [(y, x) for y in r02.positions(h, patch, stride)
              for x in r02.positions(w, patch, stride)]
    scores = np.zeros((r02.N_CLASSES, h, w), np.float32)
    counts = np.zeros((h, w), np.float32)
    with torch.inference_mode():
        for start in range(0, len(coords), batch):
            bc = coords[start:start + batch]
            op = np.stack([optical[y:y+patch, x:x+patch].transpose(2, 0, 1) for y, x in bc])
            op_t = torch.from_numpy(np.ascontiguousarray(op)).to(r02.DEVICE)
            if optical_only:
                logits = net(op_t)
            else:
                ds = np.stack([dsm[y:y+patch, x:x+patch] for y, x in bc])
                ds_t = torch.from_numpy(np.ascontiguousarray(ds)).to(r02.DEVICE)
                logits = net(op_t, ds_t)
            for value, (y, x) in zip(logits.detach().cpu().numpy(), bc):
                scores[:, y:y+patch, x:x+patch] += value
                counts[y:y+patch, x:x+patch] += 1
    return scores / counts[None]


def route_predictions(p1, p5, gt, missing_mask):
    pred1, pred5 = p1.argmax(0).astype(np.uint8), p5.argmax(0).astype(np.uint8)
    avg = (p1 + p5) / 2
    conf_choose5 = p5.max(0) > p1.max(0)
    eps = 1e-8
    ent1 = -(p1 * np.log(p1 + eps)).sum(0)
    ent5 = -(p5 * np.log(p5 + eps)).sum(0)
    ent_choose5 = ent5 < ent1
    safe_choose5 = conf_choose5 if missing_mask is None else (conf_choose5 & ~missing_mask)
    return {
        "R01_optical": pred1,
        "R05_dual": pred5,
        "prob_avg": avg.argmax(0).astype(np.uint8),
        "prob_alpha25": (0.75*p1 + 0.25*p5).argmax(0).astype(np.uint8),
        "prob_alpha75": (0.25*p1 + 0.75*p5).argmax(0).astype(np.uint8),
        "max_confidence": np.where(conf_choose5, pred5, pred1).astype(np.uint8),
        "min_entropy": np.where(ent_choose5, pred5, pred1).astype(np.uint8),
        "safe_max_confidence": np.where(safe_choose5, pred5, pred1).astype(np.uint8),
        "pixel_oracle": oracle_prediction(gt, pred1, pred5),
    }


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader(); w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, choices=[17, 42], required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    run1 = ROOT / f"runs/rebuild_v1/R01_optical_only_seed{args.seed}_sched16000_stop16000"
    run5 = ROOT / f"runs/rebuild_v1/R05_dual_f0_quality_plus_dropout_seed{args.seed}_sched16000_stop16000"
    _, ck1 = validate_run(run1); _, ck5 = validate_run(run5)
    c1 = r02.read_json(ROOT / "configs/rebuild_v1/r01_optical_only_16k.json")
    c5 = r02.read_json(ROOT / "configs/rebuild_v1/r05_quality_plus_dropout_16k.json")
    split = r02.read_json(ROOT / c5["split_file"])
    ids = list(split["val2"][:1] if args.smoke else split["val2"])
    if set(ids) & set(split["historical_exposed_test6"]): raise RuntimeError("TEST6 overlap")
    s1, s5 = torch.load(ck1, map_location="cpu"), torch.load(ck5, map_location="cpu")
    n1, _, _ = r01.build_model(c1, Path(c1["pretrain"]), resume_state=s1)
    n5, _ = r02.build_model(c5, Path(c5["pretrain"]), resume_state=s5)
    n1.eval(); n5.eval()
    conds = specs()
    if args.smoke: conds = [x for x in conds if x["name"] in {"clean", "dsm_zero", "dsm_local_zero_q1"}]
    cms = {(x["name"], m, sp): np.zeros((r02.N_CLASSES, r02.N_CLASSES), np.int64)
           for x in conds for m in METHODS for sp in ("full", "noboundary")}
    patch, stride, batch = int(c5["patch"]), int(c5["validation"]["stride"]), int(c5["validation"]["inference_batch"])
    for tile in ids:
        d = r02.load_tile(Path(c5["data_root"]), tile, need_nb=True)
        print("R01", tile, flush=True)
        p1 = softmax_np(infer_scores(n1, d["optical"], d["dsm"], patch, stride, batch, True))
        for spec in conds:
            treated, mask = apply_condition(d["dsm"], spec)
            print("D5", args.seed, tile, spec["name"], flush=True)
            p5 = softmax_np(infer_scores(n5, d["optical"], treated, patch, stride, batch, False))
            missing = mask if spec["family"] in ("D1_local_missing", "D4_global_missing") else None
            for sp, gt in (("full", d["full_gt"]), ("noboundary", d["noboundary_gt"])):
                for method, pred in route_predictions(p1, p5, gt, missing).items():
                    r02.update_cm(cms[(spec["name"], method, sp)], gt, pred)
    rows = []
    for spec in conds:
        for method in METHODS:
            for sp in ("full", "noboundary"):
                mt = r02.metrics_from_cm(cms[(spec["name"], method, sp)])
                rows.append({"condition": spec["name"], "family": spec["family"], "method": method,
                             "split": sp, "OA": mt["OA"], "mIoU_fg5": mt["mIoU_fg5"], "mIoU_all6": mt["mIoU_all6"]})
    suffix = "_smoke" if args.smoke else ""
    out = ROOT / f"records/rebuild_v1_d5_confidence_routing_seed{args.seed}_20260920{suffix}"
    out.mkdir(parents=True, exist_ok=True); write_csv(out / "method_metrics.csv", rows)
    payload = {"recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
               "experiment_id": "D5_CONFIDENCE_ROUTING", "seed": args.seed, "smoke": args.smoke,
               "historical_test6_loaded": False, "conditions": conds, "methods": METHODS,
               "r01_checkpoint": str(ck1), "r05_checkpoint": str(ck5)}
    (out / "summary.json").write_text(json.dumps(payload, indent=2)+"\n", encoding="utf-8")
    print("D5 COMPLETE", out)


if __name__ == "__main__": main()
