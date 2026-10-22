"""T/V exploratory public-data runs with independent, sealed development groups."""
import gc
import hashlib
import json
import time
from pathlib import Path

import numpy as np

from phase3_combined_plan import jobs, read, digest, public_catalog_status
from phase3_stage_control import receipt, run as run_stage
from phase3_public_data import TileCache


def _dataset(stage):
    return "3DCD" if stage == "T" else "P3"


def _fold_rows(catalog, stage, fold):
    data = catalog["datasets"][_dataset(stage)]
    rows = data["development"]
    groups = sorted({str(r["group"]) for r in rows})
    if len(groups) != 3:
        raise RuntimeError("exactly three independent development groups required")
    held = groups[int(fold[1])]
    train = [r for r in rows if str(r["group"]) != held]
    evaluation = [r for r in rows if str(r["group"]) == held]
    if not train or not evaluation:
        raise RuntimeError("empty public-data fold")
    return train, evaluation, data["metadata"], held


def _shift(array, dy, dx):
    out = np.roll(array, (dy, dx), (0, 1))
    if dy > 0: out[:dy] = 0
    if dy < 0: out[dy:] = 0
    if dx > 0: out[:, :dx] = 0
    if dx < 0: out[:, dx:] = 0
    return out


def _match_height(a, b, valid, mode):
    from scipy.ndimage import gaussian_filter
    if mode == "plain" or mode == "nuisance_aug":
        return b, valid.astype(np.float32)
    stable = valid & (np.abs(b-a) < 20)
    offset = float(np.median((b-a)[stable])) if stable.sum() >= 100 else 0.0
    b = b - offset
    if mode == "robust_preprocess":
        return b, valid.astype(np.float32)
    ga = np.hypot(*np.gradient(gaussian_filter(a, 1)))
    gb = np.hypot(*np.gradient(gaussian_filter(b, 1)))
    choices = []
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            z = _shift(gb, dy, dx)
            v = valid & _shift(valid, dy, dx)
            score = float(np.mean(ga[v] * z[v])) if v.sum() >= 100 else -1e9
            choices.append((score, dy, dx))
    scores = np.array([x[0] for x in choices])
    if mode == "hard_correspondence":
        _, dy, dx = choices[int(scores.argmax())]
        return _shift(b, dy, dx), (valid & _shift(valid, dy, dx)).astype(np.float32)
    if mode == "soft_no_match":
        scores -= scores.max()
        weights = np.exp(np.clip(scores / .05, -30, 0))
        weights /= weights.sum()
        confidence = float(np.max(weights))
        # A low-confidence match leaves an explicit no-match signal.
        if confidence < .12:
            return b, np.zeros_like(a, np.float32)
        mixed = sum(float(weight) * _shift(b, dy, dx)
                    for weight, (_, dy, dx) in zip(weights, choices))
        return mixed, valid.astype(np.float32) * confidence
    raise ValueError(mode)


def _features(stage, arm, item, training=False, seed=0):
    if stage == "T":
        a = item["dsm1"].copy()
        b = item["dsm2"].copy()
        valid = item["measurement_valid"]
        if arm == "nuisance_aug" and training:
            rng = np.random.default_rng(seed)
            dy,dx = int(rng.integers(-2, 3)), int(rng.integers(-2, 3))
            b = _shift(b, dy, dx)
            valid = valid & _shift(valid, dy, dx)
            b += rng.uniform(-3, 3)
        matched, confidence = _match_height(a, b, valid, arm)
        channels = np.concatenate((item["rgb1"], item["rgb2"],
                                   (a / 100)[..., None], (matched / 100)[..., None],
                                   confidence[..., None],
                                   np.clip((matched-a)/30, -3, 3)[..., None]), -1)
        return channels.astype(np.float32)
    height = item["height"].copy()
    available = item["height_valid"].astype(np.float32)
    if arm in ("rgb_only", "rgb_relation"):
        height[:] = 0
        available[:] = 0
    elif arm == "shuffled_geometry":
        height = np.roll(height, (height.shape[0]//2, height.shape[1]//2), (0, 1))
        available = np.roll(available, (available.shape[0]//2, available.shape[1]//2), (0, 1))
    return np.concatenate((item["rgb"], np.clip(height/30, -5, 5)[..., None],
                           available[..., None]), -1).astype(np.float32)


def _relation_target(instance):
    result = np.zeros((4,) + instance.shape, np.float32)
    for channel, (dy, dx) in enumerate(((0,1),(1,0),(0,-1),(-1,0))):
        moved = _shift(instance, -dy, -dx)
        result[channel] = ((instance > 0) & (instance == moved)).astype(np.float32)
    return result


def _crop(item, stage, arm, row_seed, index):
    rng = np.random.default_rng(row_seed)
    h, w = (item["changed"] if stage == "T" else item["instance"]).shape
    if min(h, w) < 128:
        raise ValueError("public-data sample smaller than 128 pixels")
    y = int(rng.integers(0, h-127)); x = int(rng.integers(0, w-127))
    sub = {k: (v[y:y+128, x:x+128] if isinstance(v, np.ndarray) else v)
           for k, v in item.items()}
    features = _features(stage, arm, sub, training=True, seed=row_seed)
    if stage == "T":
        target = np.stack((sub["changed"], sub["delta"], sub["valid"].astype(np.float32)))
    else:
        instance = sub["instance"]
        target = np.concatenate(((instance > 0)[None].astype(np.float32),
                                 _relation_target(instance)), 0)
    return features.transpose(2,0,1).copy(), target.copy(), (sub["id"], y, x)


def _loss(stage, arm, logits, target):
    import torch
    from torch.nn import functional as F
    if stage == "T":
        valid = target[:, 2] > .5
        change = F.binary_cross_entropy_with_logits(logits[:, 0], target[:, 0], reduction="none")
        segmentation = (change*valid).sum() / valid.sum().clamp(min=1)
        height_mask = valid & (target[:, 0] > .5)
        height = F.smooth_l1_loss(logits[:, 1], target[:, 1], reduction="none")
        return segmentation + .1*(height*height_mask).sum()/height_mask.sum().clamp(min=1)
    building = F.binary_cross_entropy_with_logits(logits[:, 0], target[:, 0])
    if arm in ("rgb_relation", "rgb_geometry_relation", "shuffled_geometry"):
        relations = F.binary_cross_entropy_with_logits(logits[:, 1:5], target[:, 1:5])
        return building + .25*relations
    return building


def _cm(gt, pred, valid):
    index = gt[valid].astype(np.int64)*2 + pred[valid].astype(np.int64)
    return np.bincount(index, minlength=4).reshape(2,2).astype(np.int64).tolist()


def _instances_from_edges(mask, relation=None):
    from scipy.ndimage import label
    if relation is None:
        return label(mask)[0].astype(np.int32)
    h,w = mask.shape
    parent = np.arange(h*w, dtype=np.int32)
    def root(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for y in range(h):
        for x in range(w):
            if not mask[y,x]: continue
            a = y*w+x
            if x+1<w and mask[y,x+1] and relation[0,y,x]>.5 and relation[2,y,x+1]>.5:
                parent[root(a)] = root(a+1)
            if y+1<h and mask[y+1,x] and relation[1,y,x]>.5 and relation[3,y+1,x]>.5:
                parent[root(a)] = root(a+w)
    flat = np.zeros(h*w, np.int32)
    for a in np.flatnonzero(mask.ravel()): flat[a] = root(int(a))+1
    _, inverse = np.unique(flat, return_inverse=True)
    return inverse.reshape(h,w).astype(np.int32)


def _objects(gt, pred):
    from scipy.optimize import linear_sum_assignment
    g = np.unique(gt[gt>0]); p = np.unique(pred[pred>0])
    if not len(g) or not len(p):
        return dict(tp=0, fp=int(len(p)), fn=int(len(g)), merges=0, splits=0)
    gi = {int(v):i for i,v in enumerate(g)}; pi = {int(v):i for i,v in enumerate(p)}
    overlap = np.zeros((len(g),len(p)),np.int64)
    both = (gt>0)&(pred>0)
    for a,b in zip(gt[both],pred[both]): overlap[gi[int(a)],pi[int(b)]]+=1
    area_g = np.array([(gt==v).sum() for v in g]); area_p = np.array([(pred==v).sum() for v in p])
    iou = overlap / np.maximum(1,area_g[:,None]+area_p[None,:]-overlap)
    rr,cc = linear_sum_assignment(-iou)
    tp = int((iou[rr,cc]>=.5).sum())
    substantive = overlap >= np.maximum(10, .1*area_g[:,None])
    return dict(tp=tp,fp=int(len(p)-tp),fn=int(len(g)-tp),
                merges=int((substantive.sum(0)>1).sum()),
                splits=int((substantive.sum(1)>1).sum()))


def _boundary_counts(gt, pred):
    from scipy.ndimage import binary_erosion, distance_transform_edt
    g = gt ^ binary_erosion(gt)
    p = pred ^ binary_erosion(pred)
    g_match = distance_transform_edt(~p) <= 2 if p.any() else np.zeros_like(g)
    p_match = distance_transform_edt(~g) <= 2 if g.any() else np.zeros_like(p)
    return dict(gt_boundary=int(g.sum()), pred_boundary=int(p.sum()),
                recalled=int((g & g_match).sum()), precise=int((p & p_match).sum()))


def train_job(base, m2, job, uuid):
    import torch
    from phase3_public_models import SmallUNet
    from phase3_m2_common import key, now
    stage = job["stage"]
    base = Path(base)
    folder = base / "jobs" / job["id"]
    folder.mkdir(parents=True, exist_ok=False)
    catalog = read(base / "catalog.json")
    train, evaluation, metadata, held = _fold_rows(catalog, stage, job["fold"])
    cache = TileCache(_dataset(stage), metadata)
    torch.manual_seed(key("public", stage, job["fold"], job["seed"])%(2**63-1))
    model = SmallUNet(10 if stage == "T" else 5, 2 if stage == "T" else 5).cuda()
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=.01)
    initial = hashlib.sha256(b"".join(p.detach().cpu().numpy().tobytes()
                                       for p in model.state_dict().values())).hexdigest()
    receipt(folder / "parameters.json", {
        "job":job, "combined_execution_commit":read(base/"registration.json")["execution_commit"],
        "dataset":_dataset(stage),"catalog_sha256":digest(base/"catalog.json"),
        "development_train_ids":[r["id"] for r in train],
        "development_held_group":held,"evaluation_ids":[r["id"] for r in evaluation],
        "initial_state_sha256":initial,"updates":12000,"batch":8,"crop":128,
        "GPU_UUID":uuid,"scope":"exploratory public data; no public test split",
    })
    start=time.monotonic()
    with (folder/"trajectory.jsonl").open("x") as log, \
         (folder/"batch_hashes.jsonl").open("x") as hashes:
        for step in range(1,12001):
            samples=[]; labels=[]; tokens=[]
            for index in range(8):
                seed=key(stage,job["fold"],job["seed"],step,index)
                row=train[seed%len(train)]
                item=cache.get(row)
                x,y,token=_crop(item,stage,job["arm"],seed,index)
                samples.append(x);labels.append(y);tokens.append(str(token))
            x=torch.from_numpy(np.stack(samples)).cuda()
            y=torch.from_numpy(np.stack(labels)).cuda()
            model.train();opt.zero_grad(set_to_none=True)
            lr=3e-4*(.1+.9*step/100 if step<=100 else (12000-step)/11900)
            for group in opt.param_groups:group["lr"]=lr
            with torch.autocast("cuda",dtype=torch.bfloat16):
                logits=model(x)
                loss=_loss(stage,job["arm"],logits.float(),y)
            if not bool(torch.isfinite(loss)):raise RuntimeError("nonfinite public-data loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(),5,error_if_nonfinite=True)
            opt.step()
            hashes.write(json.dumps({"step":step,"sha256":hashlib.sha256(
                "|".join(tokens).encode()).hexdigest()})+"\n")
            if step==1 or step%20==0:
                record=dict(step=step,loss=float(loss.detach()),elapsed_seconds=time.monotonic()-start)
                log.write(json.dumps(record)+"\n");log.flush();hashes.flush()
                receipt(folder/"progress.json",record)
            if step in (3000,6000,9000):
                receipt(folder/f"age_{step}.json",{"step":step,"observed_at":now()})
    endpoint=folder/"endpoint.pth"
    if digest(base/"catalog.json")!=read(folder/"parameters.json")["catalog_sha256"]:
        raise RuntimeError("public catalog changed during training")
    torch.save({"job":job,"step":12000,"model":model.state_dict(),
                "catalog_sha256":digest(base/"catalog.json")},endpoint)
    model.eval()
    rows=[]
    with torch.no_grad():
        for row in evaluation:
            item=cache.get(row)
            features=_features(stage,job["arm"],item)
            x=torch.from_numpy(features.transpose(2,0,1)[None].copy()).cuda()
            output=model(x).float()[0].cpu().numpy()
            pred=output[0]>0
            if stage=="T":
                valid=item["valid"]
                changed=item["changed"]>.5
                height_mask=valid&changed
                rows.append(dict(id=row["id"],group=held,cm=_cm(changed,pred,valid),
                                 changed_height_abs_error_sum=float(np.abs(output[1]-item["delta"])[height_mask].sum()),
                                 changed_height_count=int(height_mask.sum())))
            else:
                truth=item["instance"]>0
                relation=None if job["arm"] in ("rgb_only","ordinary_fusion") else 1/(1+np.exp(-output[1:5]))
                instances=_instances_from_edges(pred,relation)
                rows.append(dict(id=row["id"],group=held,cm=_cm(truth,pred,np.ones_like(truth,bool)),
                                 object_counts=_objects(item["instance"],instances),
                                 boundary_counts=_boundary_counts(truth,pred)))
            del x,output
    receipt(folder/"metrics.json",{"rows":rows,"held_group":held,
            "evaluation":"full development held-group; public test sealed"})
    if digest(base/"catalog.json")!=read(folder/"parameters.json")["catalog_sha256"]:
        raise RuntimeError("public catalog changed during evaluation")
    receipt(folder/"complete.json",{
        "job":job,"updates":12000,"initial_state_sha256":initial,
        "catalog_sha256":digest(base/"catalog.json"),
        "batch_stream_sha256":digest(folder/"batch_hashes.jsonl"),
        "endpoint_sha256":digest(endpoint),"metrics_sha256":digest(folder/"metrics.json"),
        "gpu_uuid":uuid,"automatic_retry":False,"observed_at":now(),
    })
    cache.clear();del model,opt;gc.collect();torch.cuda.empty_cache()


def finalize(base, m2, stage):
    base=Path(base)
    rows=[]
    scores=[]
    for job in jobs(stage):
        folder=base/"jobs"/job["id"]
        done=read(folder/"complete.json")
        if done["updates"]!=12000 or digest(folder/"endpoint.pth")!=done["endpoint_sha256"]:
            raise RuntimeError("public-data endpoint mismatch: "+job["id"])
        if digest(folder/"metrics.json")!=done["metrics_sha256"]:
            raise RuntimeError("public-data metrics mismatch: "+job["id"])
        evidence=read(folder/"metrics.json")
        rows.append({"job":job,"metrics":evidence})
        cm=sum((np.asarray(tile["cm"],np.int64) for tile in evidence["rows"]),
               np.zeros((2,2),np.int64))
        union=int(cm[1,1]+cm[1,0]+cm[0,1])
        score=dict(job=job["id"],arm=job["arm"],fold=job["fold"],seed=job["seed"],
                   held_group=evidence["held_group"],cm=cm.tolist(),
                   foreground_iou=None if union==0 else float(cm[1,1]/union))
        if stage=="T":
            error=sum(tile["changed_height_abs_error_sum"] for tile in evidence["rows"])
            count=sum(tile["changed_height_count"] for tile in evidence["rows"])
            score.update(changed_height_mae_m=None if count==0 else error/count,
                         changed_height_count=count)
        else:
            objects={name:sum(tile["object_counts"][name] for tile in evidence["rows"])
                     for name in ("tp","fp","fn","merges","splits")}
            boundaries={name:sum(tile["boundary_counts"][name] for tile in evidence["rows"])
                        for name in ("gt_boundary","pred_boundary","recalled","precise")}
            denom=2*objects["tp"]+objects["fp"]+objects["fn"]
            precision=None if boundaries["pred_boundary"]==0 else boundaries["precise"]/boundaries["pred_boundary"]
            recall=None if boundaries["gt_boundary"]==0 else boundaries["recalled"]/boundaries["gt_boundary"]
            boundary_f1=None if precision is None or recall is None or precision+recall==0 else 2*precision*recall/(precision+recall)
            score.update(object_counts=objects,boundary_counts=boundaries,
                         object_f1=None if denom==0 else 2*objects["tp"]/denom,
                         boundary_f1_2px=boundary_f1)
        scores.append(score)
    metric="foreground_iou" if stage=="T" else "object_f1"
    arm_pairs=(("soft_no_match","robust_preprocess"),("hard_correspondence","robust_preprocess")) if stage=="T" else (
        ("rgb_geometry_relation","rgb_relation"),("rgb_geometry_relation","ordinary_fusion"),
        ("rgb_geometry_relation","shuffled_geometry"))
    lookup={(r["arm"],r["fold"],r["seed"]):r[metric] for r in scores}
    comparisons={}
    for left,right in arm_pairs:
        values=[]
        for fold in ("F0","F1","F2"):
            for seed in (42,17):
                a,b=lookup[(left,fold,seed)],lookup[(right,fold,seed)]
                values.append(None if a is None or b is None else a-b)
        comparisons[left+"_minus_"+right]={"metric":metric,
            "six_paired_blocks":values,
            "mean":None if any(x is None for x in values) else float(np.mean(values)),
            "positive_blocks":sum(x is not None and x>0 for x in values)}
    output=base/"publication"/stage
    output.mkdir(parents=True,exist_ok=True)
    receipt(output/"metrics.json",{"jobs":rows,"pooled_development_scores":scores,
                                   "paired_comparisons":comparisons})
    receipt(output/"summary.json",{
        "status":"COMPLETE_SERVER_CHECKED","jobs":30,"updates":360000,
        "catalog_sha256":digest(base/"catalog.json"),
        "scope":"independent exploratory public-data evidence; no public test",
        "claim_gate":"manual methods/baseline review required before paper claim",
    })


def run(stage, base, m2):
    if stage not in ("T","V"):raise ValueError(stage)
    status=public_catalog_status(Path(base)/"catalog.json")
    if not status[_dataset(stage)]["ready"]:
        raise RuntimeError("public-data catalog not ready: "+repr(status[_dataset(stage)]))
    run_stage(stage,base,m2,lambda b,s:finalize(b,s,stage))
