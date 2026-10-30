"""D23-A CPU-only existing-prediction diagnostic. No torch, inference or training."""
import argparse
from datetime import datetime
import gc
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image

TILES = ("3_11", "5_10")
CONDITIONS = ("clean", "rgb_down4", "aux_noise_std010", "aux_zero", "aux_local_zero_q1")
AVAILABLE = CONDITIONS[:3]
CHECKPOINTS = {
    "R0": "29aa15f4cd149012996ddeadd7a5b40f593f99854318acd1d0d0acb286ed5975",
    "M0": "23b2939ea50867c96c0a17626fd4a85a27100ebd8296b2fc96440ed8bc3d34de",
}
COLORS = ((255,255,255), (0,0,255), (0,255,255), (0,255,0), (255,255,0), (255,0,0))
START = time.monotonic()
LIMIT_SECONDS = 1800
LIMIT_BYTES = 2 * 1024**3


def peak_rss():
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        class Info(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        info = Info()
        info.cb = ctypes.sizeof(info)
        kernel = ctypes.WinDLL("kernel32")
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        query = ctypes.WinDLL("psapi").GetProcessMemoryInfo
        query.argtypes = [wintypes.HANDLE, ctypes.POINTER(Info), wintypes.DWORD]
        query.restype = wintypes.BOOL
        if not query(kernel.GetCurrentProcess(), ctypes.byref(info), info.cb):
            raise OSError("cannot measure process memory")
        return int(info.PeakWorkingSetSize)
    import resource
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def guard():
    if time.monotonic() - START > LIMIT_SECONDS:
        raise RuntimeError("CPU time budget exceeded")
    if peak_rss() > LIMIT_BYTES:
        raise RuntimeError("peak RSS protection exceeded")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(4*1024*1024), b""):
            value.update(block)
            guard()
    return value.hexdigest()


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as target:
        json.dump(value, target, indent=2, allow_nan=False)
        target.write("\n")


def decode_label(path, scope):
    with Image.open(path) as im:
        if im.width * im.height > 40_000_000 or im.mode not in ("RGB", "RGBA", "P"):
            raise RuntimeError("unsupported label size/mode: " + str(path))
        rgb = np.asarray(im.convert("RGB"))
    guard()
    gt = np.full(rgb.shape[:2], 255, np.uint8)
    for idx, color in enumerate(COLORS):
        gt[np.all(rgb == color, axis=-1)] = idx
        guard()
    unknown = gt == 255
    if scope == "noboundary":
        unknown &= np.any(rgb != 0, axis=-1)
    if unknown.any():
        raise RuntimeError("unknown label colors: " + str(path))
    del rgb, unknown
    guard()
    return gt


def local_availability(shape, condition, start, end):
    h, w = shape
    a = np.ones((end-start, w), bool)
    if condition == "aux_zero":
        a[:] = False
    elif condition == "aux_local_zero_q1":
        y0, y1 = max(start, h//4), min(end, h//4+h//2)
        if y1 > y0:
            a[y0-start:y1-start, w//4:w//4+w//2] = False
    return a


def joint_counts(gt, p0, p1, condition, chunk_rows=128):
    if gt.shape != p0.shape or gt.shape != p1.shape or gt.ndim != 2:
        raise RuntimeError("prediction/GT shape mismatch")
    counts = {region: np.zeros((6,6,6), np.int64) for region in ("available", "missing")}
    for start in range(0, gt.shape[0], chunk_rows):
        end = min(start+chunk_rows, gt.shape[0])
        y = gt[start:end]
        x0, x1 = p0[start:end], p1[start:end]
        for x in (x0, x1):
            if x.dtype.kind not in "iu" or (x < 0).any() or (x > 5).any():
                raise RuntimeError("prediction must contain integer class IDs 0..5")
        a = local_availability(gt.shape, condition, start, end)
        valid = y < 6
        for region, region_mask in (("available", a), ("missing", ~a)):
            mask = valid & region_mask
            key = y[mask].astype(np.int64)*36 + x0[mask].astype(np.int64)*6 + x1[mask].astype(np.int64)
            counts[region] += np.bincount(key, minlength=216).reshape(6,6,6)
        guard()
    return counts


def metrics(cm):
    cm = np.asarray(cm, dtype=np.int64)
    tp, support, predicted = np.diag(cm), cm.sum(1), cm.sum(0)
    union = support+predicted-tp
    if int(cm.sum()) == 0:
        return {"valid": 0, "fg5": None, "OA": None, "cm": cm.tolist()}
    iou = np.divide(tp, union, out=np.full(6, np.nan), where=union>0)
    return {"valid": int(cm.sum()), "fg5": float(np.nanmean(iou[:5])), "OA": float(tp.sum()/cm.sum()),
            "per_class_iou": [None if not np.isfinite(x) else float(x) for x in iou], "cm": cm.tolist(),
            "support": support.tolist(), "TP": tp.tolist(), "FP": (predicted-tp).tolist(),
            "FN": (support-tp).tolist()}


def summarize(counts):
    available, missing = counts["available"], counts["missing"]
    total = available+missing
    cms = {name: np.zeros((6,6), np.int64) for name in ("R0", "M0", "M0_safe", "oracle_safe")}
    categories = np.zeros((6,4), np.int64)
    available_categories = np.zeros((6,4), np.int64)
    for y in range(6):
        for x0 in range(6):
            for x1 in range(6):
                category = 0 if x0==y and x1==y else 1 if x0==y else 2 if x1==y else 3
                n, a, m = int(total[y,x0,x1]), int(available[y,x0,x1]), int(missing[y,x0,x1])
                categories[y,category] += n
                available_categories[y,category] += a
                cms["R0"][y,x0] += n
                cms["M0"][y,x1] += n
                cms["M0_safe"][y,x1] += a
                cms["M0_safe"][y,x0] += m
                oracle = x1 if x1==y and x0!=y else x0
                cms["oracle_safe"][y,oracle] += a
                cms["oracle_safe"][y,x0] += m
    valid = int(total.sum())
    return {"metrics": {k: metrics(v) for k,v in cms.items()},
            "category_order": ["both_correct","only_R0_correct_harm","only_M0_correct_rescue","both_wrong"],
            "raw_categories_by_truth": categories.tolist(),
            "available_categories_by_truth": available_categories.tolist(),
            "safe_harm": int(available_categories[:,1].sum()),
            "safe_rescue": int(available_categories[:,2].sum()),
            "safe_harm_fraction_valid": None if valid==0 else float(available_categories[:,1].sum()/valid),
            "safe_rescue_fraction_valid": None if valid==0 else float(available_categories[:,2].sum()/valid),
            "regions": {k: {"joint_int64": v.tolist(), "valid": int(v.sum())} for k,v in counts.items()}}


def binding(root):
    base_path = root/"configs/rebuild_v1/r05_quality_plus_dropout_16k.json"
    base = read(base_path)
    split = read(root/base["split_file"])
    if split["val2"] != list(TILES) or set(TILES) & set(split["historical_exposed_test6"]):
        raise RuntimeError("locked development split mismatch")
    queue = root/"records/rebuild_v1_d21_queue_20260928"
    manifest_path = queue/"input_manifest.json"
    manifest_sha = sha(manifest_path)
    manifest = read(manifest_path)
    summaries, provenance = {}, {"inputs": [], "checkpoints": [], "manifest_sha256": manifest_sha}
    for arm, expected in CHECKPOINTS.items():
        run = root/"runs/rebuild_v1"/("D21_potsdam_"+arm+"_seed42_16000_20260928")
        ev = root/"records/rebuild_v1_d21_20260928"/("potsdam_"+arm+"_seed42")
        train, summary = read(run/"summary.json"), read(ev/"summary.json")
        job = {"dataset": "potsdam", "arm": arm, "seed": 42}
        if train["job"] != job or summary["job"] != job or train["global_step"] != 16000:
            raise RuntimeError("wrong expert/seed/budget")
        if summary["smoke"] or summary["evaluation_ids"] != list(TILES) or summary["primary_scope"]!="noboundary":
            raise RuntimeError("wrong evaluation scope")
        if summary["signature"]["training"] != train["signature"]:
            raise RuntimeError("training/evaluation signature mismatch")
        if train["signature"]["input_manifest_sha256"] != manifest_sha:
            raise RuntimeError("input manifest binding mismatch")
        for row in (train, summary, train["signature"]):
            if row.get("test6_loaded") is not False:
                raise RuntimeError("Test6 policy mismatch")
        if any(row.get("independent_final_loaded") is not False for row in (summary, train["signature"])):
            raise RuntimeError("independent final policy mismatch")
        if train["checkpoint_sha256"] != expected or summary["signature"]["checkpoint_sha256"] != expected:
            raise RuntimeError("checkpoint record mismatch")
        ck = run/"last_train_state.pth"
        if sha(ck) != expected:
            raise RuntimeError("checkpoint bytes mismatch")
        provenance["checkpoints"].append({"arm":arm, "path":str(ck), "sha256":expected})
        summaries[arm] = summary
    for name, path in (("configs/rebuild_v1/r05_quality_plus_dropout_16k.json", base_path), (base["split_file"], root/base["split_file"])):
        actual = sha(path)
        if any(s["signature"]["training"]["source_sha256"].get(name) != actual for s in summaries.values()):
            raise RuntimeError("base configuration/split differs from training source")
    data_root = Path(base["data_root"])
    if not data_root.is_absolute():
        raise RuntimeError("expected an absolute D21 data root")
    labels = {}
    manifest_rows = {row["path"]:row for row in manifest["files"]}
    for tile in TILES:
        for scope, folder, suffix in (("full","5_Labels_for_participants","label"),
                                     ("noboundary","5_Labels_for_participants_no_Boundary","label_noBoundary")):
            path = data_root/folder/("top_potsdam_"+tile+"_"+suffix+".tif")
            row = manifest_rows.get(str(path))
            if row is None or path.stat().st_size != row["size"] or sha(path) != row["sha256"]:
                raise RuntimeError("GT manifest mismatch: "+str(path))
            labels[(tile,scope)] = path
            provenance["inputs"].append({"path":str(path),"sha256":row["sha256"]})
    provenance["base_config_sha256"] = sha(base_path)
    return summaries, labels, provenance


def process_pair(root, tile, condition, summaries, labels):
    arrays, before, pred_evidence = {}, {}, []
    for arm in CHECKPOINTS:
        folder = root/"records/rebuild_v1_d21_20260928"/("potsdam_"+arm+"_seed42")/condition
        path = folder/(tile+".npy")
        detail = read(folder/(tile+".json"))
        stored = summaries[arm]["conditions"][condition]["tiles"][tile]
        if detail["signature"] != summaries[arm]["signature"] or {k:v for k,v in detail.items() if k!="signature"} != stored:
            raise RuntimeError("per-tile summary/detail binding mismatch")
        if detail["tile"]!=tile or detail["condition"]!=condition or sha(path)!=detail["prediction_sha256"]:
            raise RuntimeError("prediction hash/identity mismatch")
        before[arm] = (path.stat().st_size, path.stat().st_mtime_ns)
        arrays[arm] = np.load(path, mmap_mode="r", allow_pickle=False)
        if arrays[arm].ndim!=2:
            raise RuntimeError("prediction must be 2D")
        pred_evidence.append({"arm":arm,"path":str(path),"sha256":detail["prediction_sha256"],
                              "dtype":str(arrays[arm].dtype),"shape":list(arrays[arm].shape),"bytes":path.stat().st_size})
    result = {}
    for scope in ("full", "noboundary"):
        label_path = labels[(tile,scope)]
        label_before = (label_path.stat().st_size, label_path.stat().st_mtime_ns)
        gt = decode_label(label_path,scope)
        counts = joint_counts(gt, arrays["R0"], arrays["M0"], condition)
        row = summarize(counts)
        for arm in CHECKPOINTS:
            expected = summaries[arm]["conditions"][condition]["tiles"][tile]["scopes"][scope]["cm"]
            if row["metrics"][arm]["cm"] != expected:
                raise RuntimeError("raw confusion matrix differs from D21: "+arm+"/"+tile+"/"+scope)
        if label_before != (label_path.stat().st_size,label_path.stat().st_mtime_ns):
            raise RuntimeError("label changed during diagnostic")
        result[scope] = row
        del gt
        gc.collect()
        guard()
    for arm in CHECKPOINTS:
        path = Path(next(x["path"] for x in pred_evidence if x["arm"]==arm))
        if before[arm] != (path.stat().st_size,path.stat().st_mtime_ns):
            raise RuntimeError("prediction changed during diagnostic")
    del arrays
    gc.collect()
    return {"tile":tile,"condition":condition,"predictions":pred_evidence,"scopes":result}


def allocation_decision(rows):
    gains, pooled = {}, {}
    for condition in CONDITIONS:
        selected = [r for r in rows if r["condition"]==condition]
        if {r["tile"] for r in selected}!=set(TILES):
            raise RuntimeError("missing development tile")
        scopes = {}
        for scope in ("full","noboundary"):
            counts = {region:sum((np.asarray(r["scopes"][scope]["regions"][region]["joint_int64"],np.int64)
                                 for r in selected),np.zeros((6,6,6),np.int64))
                      for region in ("available","missing")}
            scopes[scope] = summarize(counts)
        pooled[condition] = scopes
        ms = scopes["noboundary"]["metrics"]
        if condition in AVAILABLE:
            gains[condition] = 100*(ms["oracle_safe"]["fg5"]-max(ms["R0"]["fg5"],ms["M0_safe"]["fg5"]))
    mean = sum(gains.values())/3
    return {"mean_available_gain_pp":mean, "gains_pp":gains,
            "threshold_mean_pp":0.5, "rgb_down4_must_be_positive":True,
            "eligible_to_prepare_B":bool(mean>=0.5 and gains["rgb_down4"]>0),
            "meaning":"engineering allocation heuristic; label-informed diagnostic, not deployable or theoretical mIoU upper bound",
            "pooled":pooled}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--mode",choices=("profile","full"),required=True)
    ap.add_argument("--profile",type=Path)
    args = ap.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    out.relative_to(root/"records")
    if out.exists():
        raise RuntimeError("refuse to overwrite any output directory")
    out.mkdir(parents=True)
    try:
        source_sha = sha(Path(__file__))
        old = read(args.profile) if args.mode=="full" and args.profile else None
        if args.mode=="full":
            if old is None or old.get("status")!="PROFILE_PASS" or old["script_sha256"]!=source_sha or old["root"]!=str(root):
                raise RuntimeError("full mode requires matching successful profile.json")
            if old["estimated_full_seconds"]>1800 or old["peak_rss_bytes"]>LIMIT_BYTES or not old["eligible_resource_budget"]:
                raise RuntimeError("profile exceeds proposed resource budget")
        began = time.monotonic()
        summaries, labels, provenance = binding(root)
        bind_seconds = time.monotonic()-began
        if old is not None and old["provenance"]!=provenance:
            raise RuntimeError("profile/full input bindings changed")
        pairs = [(TILES[0],"clean")] if args.mode=="profile" else [(t,c) for t in TILES for c in CONDITIONS]
        rows = []
        began = time.monotonic()
        for tile, condition in pairs:
            row = process_pair(root,tile,condition,summaries,labels)
            rows.append(row)
            write_new(out/(tile+"_"+condition+".json"),row)
            print("PAIR_COMPLETE",tile,condition,"rss_MiB",round(peak_rss()/1024**2,1),flush=True)
        pairs_seconds = time.monotonic()-began
        payload = {"status":"PROFILE_PASS" if args.mode=="profile" else "COMPLETE",
                   "observed_at":datetime.now().astimezone().isoformat(),"root":str(root),
                   "script_sha256":source_sha,"provenance":provenance,"mode":args.mode,
                   "binding_seconds":bind_seconds,"pairs_seconds":pairs_seconds,
                   "elapsed_seconds":time.monotonic()-START,"peak_rss_bytes":peak_rss(),
                   "test6_loaded":False,"independent_final_loaded":False,
                   "new_inference":False,"new_training":False}
        if args.mode=="profile":
            payload["estimated_full_seconds"] = bind_seconds+10*pairs_seconds
            payload["eligible_resource_budget"] = payload["estimated_full_seconds"]<=1800 and peak_rss()<=LIMIT_BYTES
            payload["decision"] = None
        else:
            payload["decision"] = allocation_decision(rows)
        guard()
        write_new(out/("profile.json" if args.mode=="profile" else "decision.json"),payload)
        print(json.dumps({k:v for k,v in payload.items() if k not in ("provenance","decision")}),flush=True)
        if args.mode=="full":
            print("D23_A_DECISION",json.dumps({k:v for k,v in payload["decision"].items() if k!="pooled"}),flush=True)
        return 0
    except Exception as exc:
        write_new(out/"failure.json",{"status":"TECHNICAL_FAILURE","error":str(exc),
                  "observed_at":datetime.now().astimezone().isoformat(),
                  "test6_loaded":False,"new_training":False,"new_inference":False})
        print("D23_A_TECHNICAL_FAILURE",str(exc),file=sys.stderr,flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
