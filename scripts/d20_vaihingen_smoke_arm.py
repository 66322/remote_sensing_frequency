"""One-step matched Vaihingen development smoke with checkpoint reload."""

import argparse
import json
import os
from pathlib import Path
import time

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
os.environ.setdefault("XFORMERS_DISABLED", "1")
import numpy as np
from skimage import io
import torch

import d18_d19_night as d18
import d16_d17_portfolio as old
import train_rebuild_v1_r02_budget_pilot as r02

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rebuild_v1/d20_vaihingen_development_smoke_20260928.json"
OUT = ROOT / "records/rebuild_v1_d20_vaihingen_smoke_20260928"


def paths(data_root, tile_id, label_directory):
    name = f"top_mosaic_09cm_area{tile_id}.tif"
    return (data_root / "top" / name,
            data_root / "dsm" / f"dsm_09cm_matching_area{tile_id}.tif",
            data_root / label_directory / name)


def load_tile(data_root, tile_id, label_directory):
    opath, dpath, lpath = paths(data_root, tile_id, label_directory)
    for path in (opath, dpath, lpath):
        if not path.is_file():
            raise FileNotFoundError(path)
    optical = io.imread(str(opath))
    dsm = io.imread(str(dpath))
    label = io.imread(str(lpath))
    if optical.ndim != 3 or optical.shape[2] != 3 or optical.dtype != np.uint8:
        raise RuntimeError(f"Unexpected TOP bands/dtype: {opath} {optical.shape} {optical.dtype}")
    if dsm.ndim != 2 or optical.shape[:2] != dsm.shape or label.shape[:2] != dsm.shape:
        raise RuntimeError(f"Unaligned array shapes for tile {tile_id}")
    if not np.isfinite(dsm).all():
        raise RuntimeError(f"Nonfinite DSM pixels in tile {tile_id}")
    dmin, dmax = float(dsm.min()), float(dsm.max())
    if dmax <= dmin:
        raise RuntimeError(f"Constant DSM in tile {tile_id}")
    gt = r02.convert_full_gt(label)
    return (optical.astype(np.float32) / 255.0,
            ((dsm.astype(np.float32) - dmin) / (dmax - dmin)).astype(np.float32), gt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=("P0", "P1", "P2"), required=True)
    args = ap.parse_args()
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("exactly one visible GPU required")
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert cfg["steps"] == 1 and cfg["seed"] == 42 and cfg["test6_loaded"] is False
    assert cfg["optical_channels"] == ["near_infrared", "red", "green"]
    assert not set(cfg["train_ids"]) & set(cfg["development_ids"])
    assert not (set(cfg["train_ids"]) | set(cfg["development_ids"])) & set(cfg["historically_used_evaluation_ids_excluded"])
    assert cfg["smoke_train_id"] in cfg["train_ids"] and cfg["smoke_development_id"] in cfg["development_ids"]
    data_root = Path(cfg["data_root"]).resolve()
    data_root.relative_to(Path("/home/jovyan/zzx").resolve())
    input_files = (
        *paths(data_root, cfg["smoke_train_id"], cfg["training_label_directory"]),
        *paths(data_root, cfg["smoke_development_id"], cfg["development_label_directory"]),
    )
    input_hashes = {str(path): d18.sha(path) for path in input_files}
    signature = {
        "arm": args.arm, "seed": 42,
        "config_sha256": d18.sha(CONFIG),
        "source_sha256": d18.sha(Path(__file__)),
        "d18_binding": d18.binding(args.arm, True),
        "train_tile": cfg["smoke_train_id"],
        "development_tile": cfg["smoke_development_id"],
        "input_sha256": input_hashes,
        "optical_channels": cfg["optical_channels"],
        "test6_loaded": False,
    }
    output = OUT / args.arm
    run = ROOT / "runs/rebuild_v1" / f"D20_VAI_SMOKE_{args.arm}_seed42_20260928"
    summary = output / "summary.json"
    checkpoint = run / "checkpoint.pth"
    if summary.is_file():
        previous = json.loads(summary.read_text(encoding="utf-8"))
        if previous["signature"] != signature or previous["checkpoint_sha256"] != d18.sha(checkpoint):
            raise RuntimeError("existing smoke output has a different source/config binding")
        print("SMOKE REUSED", args.arm, flush=True)
        return
    output.mkdir(parents=True, exist_ok=True)
    run.mkdir(parents=True, exist_ok=True)
    r02.set_seed(42)
    started = time.time()
    train = load_tile(data_root, cfg["smoke_train_id"], cfg["training_label_directory"])
    cache = {str(cfg["smoke_train_id"]): train}
    sample_cfg = dict(patch=cfg["patch"], micro_batch=cfg["micro_batch"],
                      augmentation=dict(random_scale_min=1.0, random_scale_max=1.0,
                                        horizontal_flip_p=0.0, vertical_flip_p=0.0))
    op, ds, gt, _ = r02.sample_batch(cache, list(cache), sample_cfg)
    base = d18.read(d18.base_config())
    net = d18.build(args.arm, base, r02.DEVICE)
    optcfg = dict(base, optimizer=d18.read(d18.CONFIG)["pretrained_optimizer"],
                  schedule=d18.read(d18.CONFIG)["schedule"])
    optimizer = r02.build_optimizer(net, optcfg)
    optimizer.zero_grad(set_to_none=True)
    r02.set_lr(optimizer, optcfg, 1, 8000)
    aux = op.mean(1) if args.arm == "P1" else ds
    logits = net(op, aux)
    clean_loss = .5 * old.deterministic_ce(logits, gt)
    if not bool(torch.isfinite(clean_loss)):
        raise RuntimeError("nonfinite clean smoke loss")
    clean_loss.backward()
    del logits
    op_damaged, aux_damaged, _ = d18.training_transform(
        op, ds, args.arm, ["aux_down4"], 42000100)
    damaged_logits = net(op_damaged, aux_damaged)
    damaged_loss = .5 * old.deterministic_ce(damaged_logits, gt)
    if not bool(torch.isfinite(damaged_loss)):
        raise RuntimeError("nonfinite damaged smoke loss")
    damaged_loss.backward()
    loss_value = float(clean_loss.detach() + damaged_loss.detach())
    torch.nn.utils.clip_grad_norm_(net.parameters(), float("inf"), error_if_nonfinite=True)
    optimizer.step()
    net.eval()
    with torch.no_grad():
        probe = net(op, aux).argmax(1).cpu()
    state = {"model": net.state_dict(), "signature": signature, "global_step": 1}
    temporary = checkpoint.with_suffix(".tmp")
    torch.save(state, temporary)
    os.replace(temporary, checkpoint)
    del net, optimizer, state, clean_loss, damaged_loss, damaged_logits, op_damaged, aux_damaged
    torch.cuda.empty_cache()
    loaded = torch.load(checkpoint, map_location="cpu", weights_only=False)
    if loaded["signature"] != signature:
        raise RuntimeError("checkpoint signature changed")
    net = d18.build(args.arm, base, r02.DEVICE, loaded)
    net.eval()
    with torch.no_grad():
        reproduced = net(op, aux).argmax(1).cpu()
    if not torch.equal(probe, reproduced):
        raise RuntimeError("saved checkpoint did not reproduce the train-only prediction probe")
    del op, ds, gt, aux, probe, reproduced
    dev = load_tile(data_root, cfg["smoke_development_id"], cfg["development_label_directory"])
    patch = cfg["smoke_crop"]
    optical = np.ascontiguousarray(dev[0][:patch, :patch])
    height = np.ascontiguousarray(dev[1][:patch, :patch])
    labels = dev[2][:patch, :patch]
    aux = optical.mean(2).astype(np.float32) if args.arm == "P1" else height
    prediction = r02.infer_tile(net, optical, aux, patch, patch, 1)
    cm = np.zeros((6, 6), dtype=np.int64)
    r02.update_cm(cm, labels, prediction)
    result = {"arm": args.arm, "signature": signature,
              "checkpoint_path": str(checkpoint),
              "checkpoint_sha256": d18.sha(checkpoint), "loss": loss_value,
              "smoke_confusion_matrix": cm.tolist(), "smoke_metrics": r02.metrics_from_cm(cm),
              "elapsed_seconds": round(time.time() - started, 2),
              "scope": "one train step and 512px development crop; infrastructure check only"}
    summary.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("SMOKE COMPLETE", args.arm, result["smoke_metrics"]["valid_pixels"], flush=True)


if __name__ == "__main__":
    main()
