#!/usr/bin/env python3
"""A0 frozen DINOv2/v3 dense-feature probe. No implicit downloads or old M2 retraining."""
import argparse
import datetime as dt
import gc
import json
import os
import random
import re
import statistics
import subprocess
import sys
import time
import traceback
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
M2_NAME = "research_phase3_m2_revision_20261024T092814_2738345"
A0_NAME = "post_m2_a0_capability_20261029"
D3_SHA = "6876159a11b4df116f30f667f8c9888617df0751"
COLORS = ((255,255,255),(0,0,255),(0,255,255),(0,255,0),(255,255,0),(255,0,0))
EXPECTED = {"crop":512,"stride":256,"border":512,"batch":16,"updates":2000,"seed":42,"cal_pair":0}

def now():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def write_once(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")

def run_cmd(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()

def paths(args):
    root = Path(args.root).resolve()
    if root != ROOT:
        raise RuntimeError("This version binds to the established ROOT; revise the protocol before changing it.")
    m2 = root / "records" / M2_NAME
    out = root / "records" / A0_NAME
    for p in (m2, out):
        p.resolve().relative_to(root)
    return root,m2,out

def resource_snapshot():
    cores=len(os.sched_getaffinity(0)) if hasattr(os,"sched_getaffinity") else os.cpu_count() or 1
    cpu_max=Path("/sys/fs/cgroup/cpu.max")
    if cpu_max.is_file():
        quota,period=cpu_max.read_text().split()
        if quota!="max": cores=min(cores,max(1,int(quota)//int(period)))
    available=0
    meminfo=Path("/proc/meminfo")
    if meminfo.is_file():
        for line in meminfo.read_text().splitlines():
            if line.startswith("MemAvailable:"):
                available=int(line.split()[1])*1024
                break
    maxpath,currentpath=Path("/sys/fs/cgroup/memory.max"),Path("/sys/fs/cgroup/memory.current")
    if maxpath.is_file() and currentpath.is_file() and maxpath.read_text().strip()!="max":
        available=min(available,max(0,int(maxpath.read_text())-int(currentpath.read_text())))
    # Reserve two CPU cores per GPU process for decoding, CUDA submission and the OS.
    max_workers=min(8,max(0,cores//2-2))
    return dict(effective_cpu_cores=cores,cgroup_aware_memory_available_bytes=available,
                max_loader_workers_per_gpu=max_workers)

def code_commit():
    value=os.getenv("POST_M2_CODE_COMMIT","")
    if not re.fullmatch(r"[0-9a-f]{40}",value):
        raise RuntimeError("Set POST_M2_CODE_COMMIT to the exact published GitHub commit before smoke/profile/train/evaluate")
    return value

def contract(args, require_d3=False):
    root,m2,out = paths(args)
    plan = read(m2/"plan.json")
    folds = read(m2/"folds.json")
    pretrained = read(m2/"pretrained.json")
    if plan.get("updates") != 32000 or plan.get("batch") != 16:
        raise RuntimeError("M2 source binding differs; do not silently reuse another run")
    f0 = folds["folds"]["F0"]
    train8 = f0["train"]
    cal = f0["inner_pairs"][EXPECTED["cal_pair"]]
    train = [x for x in train8 if x not in cal]
    outer = f0["evaluation"]
    if len(train)!=6 or len(cal)!=2 or len(outer)!=4 or len(set(train+cal+outer))!=12:
        raise RuntimeError("F0 train/cal/outer coverage invalid")
    root_config = read(root/"configs/rebuild_v1/r05_quality_plus_dropout_16k.json")
    data = Path(root_config["data_root"]).resolve()
    data.relative_to(Path("/home/jovyan/zzx"))
    d2_repo = Path(pretrained["repository"]).resolve()
    d2_weight = Path(pretrained["path"]).resolve()
    if not (d2_repo/"hubconf.py").is_file() or not d2_weight.is_file():
        raise RuntimeError("DINOv2 public repo/weight absent; old M2 endpoints are not used")
    d3_repo = os.getenv("POST_M2_DINO3_REPO")
    d3_weight = os.getenv("POST_M2_DINO3_WEIGHTS")
    d3 = None
    if d3_repo and d3_weight:
        repo,weight = Path(d3_repo).resolve(),Path(d3_weight).resolve()
        if not (repo/"hubconf.py").is_file() or not weight.is_file():
            raise RuntimeError("DINOv3 repo/weight missing; first accept official model terms and prepare the checkpoint")
        actual_sha = run_cmd(["git","-C",str(repo),"rev-parse","HEAD"])
        if actual_sha != D3_SHA:
            raise RuntimeError("DINOv3 source commit differs from frozen reference")
        d3 = {"repo":str(repo),"weight":str(weight),"repo_commit":actual_sha,"weight_bytes":weight.stat().st_size}
    elif require_d3:
        raise RuntimeError("DINOv3 source/weight not configured; set POST_M2_DINO3_REPO and POST_M2_DINO3_WEIGHTS")
    return dict(root=root,m2=m2,out=out,data=data,d2={"repo":str(d2_repo),"weight":str(d2_weight),"source_binding":pretrained},
                d3=d3,folds={"train":train,"calibration":cal,"outer":outer},fold_method=folds.get("method"))

def tile_paths(data,tile):
    if not tile.replace("_","").isdigit():
        raise RuntimeError("non-whitelisted tile")
    a,b = map(int,tile.split("_"))
    return (data/"2_Ortho_RGB"/("top_potsdam_"+tile+"_RGB.tif"),
            data/"5_Labels_for_participants"/("top_potsdam_"+tile+"_label.tif"),
            data/"5_Labels_for_participants_no_Boundary"/("top_potsdam_"+tile+"_label_noBoundary.tif"))

def inventory(args):
    c = contract(args)
    missing=[]
    sizes={}
    for tile in sum(c["folds"].values(),[]):
        rgb,full,nb=tile_paths(c["data"],tile)
        for p in (rgb,full,nb):
            if not p.is_file(): missing.append(str(p))
            else: sizes[str(p)]=p.stat().st_size
    try:
        gpu=run_cmd(["nvidia-smi","--query-gpu=index,name,memory.total,memory.free,uuid","--format=csv,noheader,nounits"])
        apps=run_cmd(["nvidia-smi","--query-compute-apps=pid,gpu_uuid,used_memory","--format=csv,noheader,nounits"])
    except (OSError,subprocess.CalledProcessError) as e:
        gpu,apps="",repr(e)
    print(json.dumps(dict(status="BLOCKED_INPUT" if missing else "DATA_PRESENT",
        observed_at=now(),python=sys.version,resources=resource_snapshot(),
        folds=c["folds"],fold_method=c["fold_method"],
        missing=missing,dino2_weight_bytes=Path(c["d2"]["weight"]).stat().st_size,
        dino3=c["d3"],data_bytes=sum(sizes.values()),gpu_inventory=gpu,compute_apps=apps,
        external_model_terms="DINOv3 weights require the user's official license acceptance",
        server_not_started_by_inventory=True),ensure_ascii=False,indent=2))
    if missing: raise RuntimeError("F0 inputs missing")

def ensure_gpu(kind):
    import torch
    if sys.version_info < (3,11): raise RuntimeError("Upgrade the active remote_sensing environment in place to Python >=3.11")
    ver=tuple(int(x) for x in torch.__version__.split("+")[0].split(".")[:3])
    if ver < (2,7,1): raise RuntimeError("Upgrade the active remote_sensing environment in place to Torch >=2.7.1")
    if not torch.cuda.is_available(): raise RuntimeError("CUDA unavailable")
    if torch.cuda.device_count()!=1: raise RuntimeError("Set CUDA_VISIBLE_DEVICES to exactly one physical GPU, 0 or 1")
    device_name=torch.cuda.get_device_name(0)
    if "H100" not in device_name: raise RuntimeError("Expected user-authorized H100 physical GPU")
    free_bytes,total_bytes=torch.cuda.mem_get_info(0)
    if free_bytes < 20*1024**3:
        raise RuntimeError("Less than 20 GiB GPU memory free; do not contend with other jobs")
    return torch,device_name

def smoke(args):
    c=contract(args,require_d3=args.kind=="dino3")
    commit=code_commit()
    torch,device_name=ensure_gpu(args.kind)
    encoder,patch=load_encoder(c,args.kind)
    with torch.inference_mode():
        feat=extract(encoder,torch.zeros((1,3,512,512),device="cuda"),patch)
    if feat.shape[0]!=1 or feat.shape[1]!=384 or not bool(torch.isfinite(feat).all()):
        raise RuntimeError("Frozen encoder smoke test failed")
    result=dict(status="SMOKE_PASSED",kind=args.kind,observed_at=now(),code_commit=commit,
                gpu=device_name,python=sys.version,torch=torch.__version__,
                feature_shape=list(feat.shape),patch=patch,resources=resource_snapshot())
    write_once(c["out"]/("smoke_"+args.kind+".json"),result)
    print(json.dumps(result,ensure_ascii=False,indent=2))

def load_encoder(c,kind):
    import torch
    if kind=="dino2":
        source=c["d2"]
        model=torch.hub.load(source["repo"],"dinov2_vits14",source="local",pretrained=False)
        state=torch.load(source["weight"],map_location="cpu",weights_only=False)
        model.load_state_dict(state,strict=True)
        patch=14
    else:
        if c["d3"] is None: raise RuntimeError("DINOv3 not prepared")
        source=c["d3"]
        model=torch.hub.load(source["repo"],"dinov3_vits16",source="local",weights=source["weight"])
        patch=16
    return model.eval().requires_grad_(False).cuda(),patch

def arrays(c,tiles,need_labels=True):
    import numpy as np
    from PIL import Image
    data={}
    for tile in tiles:
        rgbp,_,nbp=tile_paths(c["data"],tile)
        with Image.open(rgbp) as im: rgb=np.asarray(im.convert("RGB")).copy()
        item={"rgb":rgb}
        if need_labels:
            with Image.open(nbp) as im: src=np.asarray(im.convert("RGB"))
            out=np.full(src.shape[:2],255,np.uint8)
            known=np.all(src==0,axis=-1)
            for k,color in enumerate(COLORS):
                mask=np.all(src==color,axis=-1)
                out[mask]=k; known|=mask
            if not known.all(): raise RuntimeError("unknown label pixels: "+str(nbp))
            if out.shape!=rgb.shape[:2]: raise RuntimeError("unaligned label: "+str(nbp))
            item["nb"]=out
        data[tile]=item
    return data

def crop_key(index,seed=42):
    import hashlib
    raw=("A0|F0|"+str(seed)+"|"+str(index)).encode()
    return int.from_bytes(hashlib.blake2b(raw,digest_size=8).digest(),"big")

class Crops:
    def __init__(self,data,tiles,length):
        self.data,self.tiles,self.length=data,tuple(tiles),length
    def __len__(self): return self.length
    def __getitem__(self,index):
        import numpy as np
        import torch
        rng=random.Random(crop_key(index))
        tile=rng.choice(self.tiles)
        item=self.data[tile]
        h,w=item["rgb"].shape[:2]
        # Both training and calibration use a 512-pixel exclusion strip at every tile edge.
        y=rng.randrange(512,h-1023)
        x=rng.randrange(512,w-1023)
        rgb=item["rgb"][y:y+512,x:x+512]
        gt=item["nb"][y:y+512,x:x+512]
        if rng.randrange(2): rgb=np.flip(rgb,axis=0);gt=np.flip(gt,axis=0)
        if rng.randrange(2): rgb=np.flip(rgb,axis=1);gt=np.flip(gt,axis=1)
        return torch.from_numpy(np.ascontiguousarray(rgb.transpose(2,0,1))),torch.from_numpy(np.ascontiguousarray(gt))

def loader(data,tiles,workers,length):
    import torch
    kwargs=dict(dataset=Crops(data,tiles,length),batch_size=16,shuffle=False,
                num_workers=workers,pin_memory=True,drop_last=True)
    if workers: kwargs.update(persistent_workers=True,prefetch_factor=2)
    return torch.utils.data.DataLoader(**kwargs)

def extract(encoder,images,patch):
    import torch
    from torch.nn import functional as F
    h,w=images.shape[-2:]
    pad=(0,(-w)%patch,0,(-h)%patch)
    mean=images.new_tensor((.485,.456,.406))[None,:,None,None]
    std=images.new_tensor((.229,.224,.225))[None,:,None,None]
    normalized=F.pad((images-mean)/std,pad,mode="replicate")
    with torch.inference_mode(),torch.autocast("cuda",dtype=torch.bfloat16):
        features=encoder.forward_features(normalized)["x_norm_patchtokens"]
    gh,gw=normalized.shape[-2]//patch,normalized.shape[-1]//patch
    if features.shape[1]!=gh*gw: raise RuntimeError("DINO patch grid changed")
    return features.transpose(1,2).reshape(images.shape[0],features.shape[-1],gh,gw).float()

def one_update(encoder,patch,head,optimizer,batch,micro):
    import torch
    from torch.nn import functional as F
    rgb,gt=batch
    valid_pixels=int((gt[:,::4,::4]!=255).sum().item())
    if valid_pixels==0: raise RuntimeError("all training target pixels ignored")
    optimizer.zero_grad(set_to_none=True)
    losses=[]
    for start in range(0,16,micro):
        x=rgb[start:start+micro].to("cuda",non_blocking=True).float().div_(255)
        y=gt[start:start+micro].to("cuda",non_blocking=True).long()
        feat=extract(encoder,x,patch)
        low=head(feat)
        z=F.interpolate(low,size=(128,128),mode="bilinear",align_corners=False)
        target=F.interpolate(y[:,None].float(),size=(128,128),mode="nearest")[:,0].long()
        loss=F.cross_entropy(z,target,ignore_index=255,reduction="sum")/valid_pixels
        loss.backward()
        losses.append(loss.detach())
    optimizer.step()
    return torch.stack(losses).sum()

def coords(h,w):
    if h<512 or w<512:raise RuntimeError("tile too small")
    axis=lambda n:sorted(set(list(range(0,n-511,256))+[n-512]))
    return [(y,x) for y in axis(h) for x in axis(w)]

def predict_tile(encoder,patch,head,rgb,batch_size,limit=None):
    import numpy as np
    import torch
    from torch.nn import functional as F
    h,w=rgb.shape[:2]
    positions=coords(h,w)
    if limit is not None: positions=positions[:limit]
    score=torch.zeros((6,h,w),device="cuda",dtype=torch.float32)
    coverage=torch.zeros((h,w),device="cuda",dtype=torch.int32)
    head.eval()
    started=time.perf_counter()
    cpu_stack_seconds=0.0
    phases={"h2d":[],"encoder":[],"head_resize":[],"stitch":[]}
    with torch.inference_mode():
        for first in range(0,len(positions),batch_size):
            use=positions[first:first+batch_size]
            t=time.perf_counter()
            packed=torch.from_numpy(np.stack([rgb[y:y+512,x:x+512].transpose(2,0,1) for y,x in use])).pin_memory()
            cpu_stack_seconds+=time.perf_counter()-t
            marks=[torch.cuda.Event(enable_timing=True) for _ in range(5)]
            marks[0].record()
            x=packed.to("cuda",non_blocking=True).float().div_(255)
            marks[1].record()
            feat=extract(encoder,x,patch)
            marks[2].record()
            low=head(feat)
            z=F.interpolate(low.float(),size=(512,512),mode="bilinear",align_corners=False)
            marks[3].record()
            for j,(y,x) in enumerate(use):
                score[:,y:y+512,x:x+512].add_(z[j])
                coverage[y:y+512,x:x+512].add_(1)
            marks[4].record()
            for name,a,b in zip(phases,marks[:-1],marks[1:]):
                phases[name].append((a,b))
    torch.cuda.synchronize()
    forward_wall_seconds=time.perf_counter()-started
    if limit is None:
        area=coverage[512:h-512,512:w-512]
        if bool((area==0).any()):raise RuntimeError("central evaluation region uncovered")
    pred=score.argmax(0).to(torch.uint8).cpu().numpy() if limit is None else None
    torch.cuda.synchronize()
    seconds=time.perf_counter()-started
    timings={"cpu_stack_seconds":cpu_stack_seconds,
             "forward_wall_seconds":forward_wall_seconds,
             "finalize_wall_seconds":seconds-forward_wall_seconds,
             "total_wall_seconds":seconds}
    timings.update({name:sum(a.elapsed_time(b) for a,b in pairs)/1000 for name,pairs in phases.items()})
    del score,coverage
    return pred,seconds,len(positions),timings

def cm_tile(pred,gt,border=512):
    import numpy as np
    h,w=gt.shape
    a=gt[border:h-border,border:w-border]
    b=pred[border:h-border,border:w-border]
    valid=a<6
    return np.bincount((a[valid].astype(np.int64)*6+b[valid]),minlength=36).reshape(6,6)

def metrics(cm):
    import numpy as np
    cm=np.asarray(cm,dtype=np.int64)
    tp=np.diag(cm)
    union=cm.sum(0)+cm.sum(1)-tp
    iou=np.divide(tp,union,out=np.zeros(6,dtype=float),where=union>0)
    return dict(cm=cm.tolist(),iou=iou.tolist(),nb_fg5_miou=float(iou[:5].mean()*100),
                support=cm.sum(1).tolist(),valid_pixels=int(cm.sum()))

def run_profile(args):
    import numpy as np
    c=contract(args,require_d3=args.kind=="dino3")
    commit=code_commit()
    if read(c["out"]/("smoke_"+args.kind+".json"))["status"]!="SMOKE_PASSED":
        raise RuntimeError("model smoke not passed")
    torch,device_name=ensure_gpu(args.kind)
    resources=resource_snapshot()
    if resources["cgroup_aware_memory_available_bytes"] < 6*1024**3:
        raise RuntimeError("Less than 6 GiB CPU memory headroom for dual-GPU profile")
    profile_started=time.perf_counter()
    data=arrays(c,c["folds"]["train"],True)
    data_load_seconds=time.perf_counter()-profile_started
    model_started=time.perf_counter()
    encoder,patch=load_encoder(c,args.kind)
    model_load_seconds=time.perf_counter()-model_started
    with torch.inference_mode():
        test=torch.zeros((1,3,512,512),device="cuda")
        channels=extract(encoder,test,patch).shape[1]
    if channels!=384:raise RuntimeError("A0 probe assumes both ViT-S teachers have 384-channel patch features")
    torch.manual_seed(42)
    head=torch.nn.Conv2d(channels,6,1).cuda()
    selected=[]
    # Actual data and model: loader, teacher forward, head/backward/optimizer.
    candidates=[(0,16)]
    for workers in (4,8):
        if workers<=resources["max_loader_workers_per_gpu"]: candidates.append((workers,16))
    if resources["max_loader_workers_per_gpu"]>=4: candidates.extend(((4,8),(4,4)))
    for workers,micro in candidates:
        stream=iter(loader(data,c["folds"]["train"],workers,16*42))
        optimizer=torch.optim.AdamW(head.parameters(),lr=1e-4)
        waits=[];compute=[]
        torch.cuda.synchronize()
        for step in range(32):
            t=time.perf_counter();batch=next(stream);w=time.perf_counter()-t
            t=time.perf_counter();one_update(encoder,patch,head,optimizer,batch,micro)
            torch.cuda.synchronize();elapsed=time.perf_counter()-t
            if step>=8:waits.append(w);compute.append(elapsed)
        selected.append(dict(workers=workers,micro=micro,median_data_wait_seconds=float(statistics.median(waits)),
             median_compute_seconds=float(statistics.median(compute)),
             median_total_seconds=float(statistics.median(waits)+statistics.median(compute)),
             peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved()))
        del stream,optimizer
        gc.collect()
    # One complete training tile measures the true full-image stitch and metric path.
    first_tile=c["folds"]["train"][0]
    tile=data[first_tile]
    eval_rows=[]
    for bs in (8,16,32):
        _,seconds,n,timings=predict_tile(encoder,patch,head,tile["rgb"],bs,limit=64)
        eval_rows.append(dict(batch=bs,sample_windows=64,sample_seconds=seconds,
                              sample_windows_per_second=64/seconds,phase_seconds=timings,
                              peak_allocated_bytes=torch.cuda.max_memory_allocated()))
    best_eval=min(eval_rows,key=lambda x:x["sample_seconds"])["batch"]
    _,full_seconds,nfull,full_timings=predict_tile(encoder,patch,head,tile["rgb"],best_eval)
    best_train=min(selected,key=lambda x:x["median_total_seconds"])
    out=dict(status="PROFILE_COMPLETED_NO_SCIENTIFIC_RESULT",kind=args.kind,observed_at=now(),code_commit=commit,
         python=sys.version,torch=torch.__version__,gpu=device_name,seed=42,crop=512,effective_batch=16,
         candidates=selected,selected_train={"workers":best_train["workers"],"micro":best_train["micro"]},
         eval_candidates=eval_rows,selected_eval_batch=best_eval,
         full_tile={"tile":first_tile,"windows":nfull,"seconds":full_seconds,"windows_per_second":nfull/full_seconds,
                    "phase_seconds":full_timings},
         disposable_profile_optimizer_updates=32*len(candidates),resources=resources,
         data_load_seconds=data_load_seconds,model_load_seconds=model_load_seconds,
         total_profile_wall_seconds=time.perf_counter()-profile_started,
         peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),
         cpu_resident_input_bytes=sum(v.nbytes for row in data.values() for v in row.values()),
         note="Profiling synchronizes each timed step; formal run samples aggregate wall time without per-step synchronization. Both model paths must be measured separately.")
    write_once(c["out"]/("profile_"+args.kind+".json"),out)
    print(json.dumps(out,ensure_ascii=False,indent=2))

def run_train(args):
    c=contract(args,require_d3=args.kind=="dino3")
    commit=code_commit()
    torch,device_name=ensure_gpu(args.kind)
    profile=read(c["out"]/("profile_"+args.kind+".json"))
    if profile["status"]!="PROFILE_COMPLETED_NO_SCIENTIFIC_RESULT":raise RuntimeError("target profile missing")
    if profile["code_commit"]!=commit:raise RuntimeError("profile made from another code commit")
    selected=profile["selected_train"]
    if selected["micro"] not in (4,8,16) or selected["workers"] not in (0,4,8):
        raise RuntimeError("invalid profiled batch/worker choice")
    folder=c["out"]/args.kind
    folder.mkdir(parents=True,exist_ok=True)
    receipt=folder/"train_complete.json"
    if receipt.exists():raise RuntimeError("already trained; do not repeat")
    write_once(folder/"train_started.json",dict(observed_at=now(),kind=args.kind,seed=42,
           train_tiles=c["folds"]["train"],calibration_tiles=c["folds"]["calibration"],
           outer_tiles=c["folds"]["outer"],selected=selected,source=c["d2"] if args.kind=="dino2" else c["d3"],
           profile=profile["observed_at"],code_commit=commit,gpu=device_name,
           environment={"python":sys.version,"torch":torch.__version__}))
    try:
        torch.manual_seed(42);torch.cuda.manual_seed_all(42)
        wall_started=time.perf_counter()
        data=arrays(c,c["folds"]["train"],True)
        data_load_seconds=time.perf_counter()-wall_started
        model_started=time.perf_counter()
        encoder,patch=load_encoder(c,args.kind)
        model_load_seconds=time.perf_counter()-model_started
        with torch.inference_mode(): channels=extract(encoder,torch.zeros((1,3,512,512),device="cuda"),patch).shape[1]
        if channels!=384:raise RuntimeError("unexpected teacher feature channels")
        torch.manual_seed(42)
        head=torch.nn.Conv2d(384,6,1).cuda()
        opt=torch.optim.AdamW(head.parameters(),lr=1e-4,weight_decay=0.01)
        stream=iter(loader(data,c["folds"]["train"],selected["workers"],16*2000))
        trajectory=[]
        start=time.perf_counter();interval=time.perf_counter()
        for step in range(1,2001):
            batch=next(stream)
            loss=one_update(encoder,patch,head,opt,batch,selected["micro"])
            if step==1 or step%100==0:
                torch.cuda.synchronize()
                row=dict(step=step,loss=float(loss),elapsed_seconds=time.perf_counter()-start,
                    interval_seconds=time.perf_counter()-interval,
                    gpu_allocated_bytes=torch.cuda.memory_allocated(),gpu_reserved_bytes=torch.cuda.memory_reserved())
                interval=time.perf_counter()
                trajectory.append(row)
                (folder/"progress.json").write_text(json.dumps(row,allow_nan=False)+"\n",encoding="utf-8")
                print("A0_TRAIN",args.kind,json.dumps(row),flush=True)
                if step==500 and row["elapsed_seconds"] > 2.5*step*min(
                    x["median_total_seconds"] for x in profile["candidates"] if
                    x["workers"]==selected["workers"] and x["micro"]==selected["micro"]):
                    raise RuntimeError("formal training >2.5x profiled step budget at update 500; inspect shared-resource contention")
        endpoint=folder/"head_2000.pth"
        torch.save(dict(kind=args.kind,step=2000,seed=42,head=head.state_dict(),
                        train_tiles=c["folds"]["train"],profile=profile["observed_at"]),endpoint)
        write_once(folder/"trajectory.json",trajectory)
        write_once(receipt,dict(status="TRAINED_HEAD_ONLY",kind=args.kind,optimizer_updates=2000,
                   endpoint_bytes=endpoint.stat().st_size,elapsed_seconds=time.perf_counter()-start,
                   total_wall_seconds=time.perf_counter()-wall_started,
                   data_load_seconds=data_load_seconds,model_load_seconds=model_load_seconds,
                   observed_at=now(),code_commit=commit,gpu=device_name,peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                   peak_reserved_bytes=torch.cuda.max_memory_reserved()))
    except Exception:
        (folder/"failure.txt").write_text(traceback.format_exc(),encoding="utf-8")
        raise

def run_evaluate(args):
    import numpy as np
    c=contract(args,require_d3=args.kind=="dino3")
    commit=code_commit()
    torch,device_name=ensure_gpu(args.kind)
    folder=c["out"]/args.kind
    done=read(folder/"train_complete.json")
    if done.get("status")!="TRAINED_HEAD_ONLY":raise RuntimeError("training not complete")
    if done.get("code_commit")!=commit:raise RuntimeError("trained head from another code commit")
    if args.split=="outer":
        screen=read(c["out"]/"calibration_screen.json")
        if screen["status"]!="READY_FOR_OUTER_DEVELOPMENT_EVALUATION":
            raise RuntimeError("calibration screen did not pass")
    profile=read(c["out"]/("profile_"+args.kind+".json"))
    tiles=c["folds"][args.split]
    result_path=folder/(args.split+"_result.json")
    if result_path.exists():raise RuntimeError("evaluation already complete; do not repeat")
    write_once(folder/(args.split+"_started.json"),dict(observed_at=now(),tiles=tiles))
    try:
        wall_started=time.perf_counter()
        encoder,patch=load_encoder(c,args.kind)
        model_load_seconds=time.perf_counter()-wall_started
        head=torch.nn.Conv2d(384,6,1).cuda()
        ckpt=torch.load(folder/"head_2000.pth",map_location="cpu",weights_only=False)
        if ckpt["kind"]!=args.kind or ckpt["step"]!=2000:raise RuntimeError("head endpoint identity mismatch")
        head.load_state_dict(ckpt["head"],strict=True)
        data_started=time.perf_counter()
        data=arrays(c,tiles,True)
        data_load_seconds=time.perf_counter()-data_started
        rows=[];pooled=np.zeros((6,6),np.int64)
        for tile in tiles:
            tile_started=time.perf_counter()
            pred,seconds,nwindows,timings=predict_tile(encoder,patch,head,data[tile]["rgb"],profile["selected_eval_batch"])
            metric_started=time.perf_counter()
            cm=cm_tile(pred,data[tile]["nb"])
            pooled+=cm
            rows.append(dict(tile=tile,seconds=seconds,windows=nwindows,phase_seconds=timings,
                             metric_seconds=time.perf_counter()-metric_started,
                             tile_total_seconds=time.perf_counter()-tile_started,**metrics(cm)))
            print("A0_EVAL",args.kind,args.split,tile,rows[-1]["nb_fg5_miou"],flush=True)
            baseline=profile["full_tile"]
            if nwindows==baseline["windows"] and seconds>2.5*baseline["seconds"]:
                raise RuntimeError("full-tile evaluation >2.5x profiled time; inspect data/CPU/GPU contention")
            del pred
        result=dict(status="EVALUATION_COMPLETE",kind=args.kind,split=args.split,tiles=rows,
            pooled=metrics(pooled),observed_at=now(),code_commit=commit,gpu=device_name,
            model_load_seconds=model_load_seconds,data_load_seconds=data_load_seconds,
            total_wall_seconds=time.perf_counter()-wall_started,
            peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),
            evidence_scope="F0 development. Neither inner calibration nor F0 outer is independent final test.")
        write_once(result_path,result)
        print(json.dumps(dict(kind=args.kind,split=args.split,pooled=result["pooled"],tile_speeds=[(x["tile"],x["seconds"],x["windows"]) for x in rows]),ensure_ascii=False))
    except Exception:
        (folder/(args.split+"_failure.txt")).write_text(traceback.format_exc(),encoding="utf-8")
        raise

def screen(args):
    c=contract(args)
    a=read(c["out"]/"dino2"/"calibration_result.json")
    b=read(c["out"]/"dino3"/"calibration_result.json")
    if a["tiles"][0]["tile"]!=b["tiles"][0]["tile"] or [r["tile"] for r in a["tiles"]] != [r["tile"] for r in b["tiles"]]:
        raise RuntimeError("calibration tiles unpaired")
    gains=[y["nb_fg5_miou"]-x["nb_fg5_miou"] for x,y in zip(a["tiles"],b["tiles"])]
    overall=b["pooled"]["nb_fg5_miou"]-a["pooled"]["nb_fg5_miou"]
    trajectories=[read(c["out"]/kind/"trajectory.json") for kind in ("dino2","dino3")]
    learned=all(len(t)>=10 and
                statistics.median(x["loss"] for x in t[:5])>
                statistics.median(x["loss"] for x in t[-5:]) for t in trajectories)
    eligible=learned and all(x["pooled"]["nb_fg5_miou"]>=50 for x in (a,b))
    positive=eligible and overall>=0.3 and min(gains)>=-0.2
    result=dict(status=("READY_FOR_OUTER_DEVELOPMENT_EVALUATION" if positive else
                        "INVALID_PROBE" if not eligible else "NO_INCREMENT_STOP_A_ROUTE"),
        observed_at=now(),dino3_minus_dino2_pooled_pp=overall,
        tile_differences_pp=gains,training_trajectory_decreased=learned,
        both_probes_competent=eligible,criteria={"delta_pp":0.3,"tile_floor_pp":-0.2,
        "inner_miou_floor_percent":50,"relative_train_loss_decrease_required":True},
        interpretation="A0 selected-frozen-feature probe only; no general claim that one teacher has or lacks world knowledge.")
    write_once(c["out"]/"calibration_screen.json",result)
    print(json.dumps(result,ensure_ascii=False,indent=2))

def status(args):
    c=contract(args)
    out={}
    for kind in ("dino2","dino3"):
        folder=c["out"]/kind
        out[kind]={n:(folder/n).exists() for n in ("train_started.json","train_complete.json","calibration_result.json",
                    "outer_result.json","failure.txt","calibration_failure.txt","outer_failure.txt")}
        profile=c["out"]/("profile_"+kind+".json")
        out[kind]["profile"]=profile.exists()
    out["calibration_screen"]=(c["out"]/"calibration_screen.json").exists()
    print(json.dumps(out,indent=2))

def run_pair(args):
    # Parent does not import torch or initialize CUDA. Fail one child, stop the other.
    c=contract(args,require_d3=True)
    commit=code_commit()
    resources=resource_snapshot()
    phase=args.phase
    if phase=="evaluate" and not args.split:raise RuntimeError("pair evaluate requires --split")
    if phase!="evaluate" and args.split:raise RuntimeError("--split only belongs to evaluation")
    if phase=="evaluate" and args.split=="outer":
        if read(c["out"]/"calibration_screen.json")["status"]!="READY_FOR_OUTER_DEVELOPMENT_EVALUATION":
            raise RuntimeError("calibration gate did not pass")
    if phase=="profile":
        required=[c["out"]/("smoke_"+k+".json") for k in ("dino2","dino3")]
    elif phase=="train":
        required=[c["out"]/("profile_"+k+".json") for k in ("dino2","dino3")]
    elif phase=="evaluate":
        required=[c["out"]/k/"train_complete.json" for k in ("dino2","dino3")]
    else: required=[]
    for path in required:
        if not path.is_file():raise RuntimeError("prerequisite missing: "+str(path))
    key=phase+(("_"+args.split) if args.split else "")
    suffix=("{}/"+args.split+"_result.json") if phase=="evaluate" else {
        "smoke":"smoke_{}.json","profile":"profile_{}.json",
        "train":"{}/train_complete.json"}[phase]
    outputs=[c["out"]/suffix.format(k) for k in ("dino2","dino3")]
    if any(path.exists() for path in outputs):
        raise RuntimeError("phase already partly or fully complete; inspect status before rerun")
    gpu=run_cmd(["nvidia-smi","--query-gpu=index,name,memory.free,uuid","--format=csv,noheader,nounits"])
    gpu_rows={}
    for row in gpu.splitlines():
        fields=[x.strip() for x in row.split(",")]
        gpu_rows[int(fields[0])]=fields
    if not all(i in gpu_rows and "H100" in gpu_rows[i][1] and int(gpu_rows[i][2])>=40000 for i in (0,1)):
        raise RuntimeError("physical GPU0/1 must each be an H100 with >=40 GiB free")
    apps=run_cmd(["nvidia-smi","--query-compute-apps=gpu_uuid,pid,used_memory","--format=csv,noheader,nounits"])
    if any(gpu_rows[i][3] in apps for i in (0,1)):
        raise RuntimeError("GPU0 or GPU1 already has an active compute app")
    parallel=(resources["effective_cpu_cores"]>=12 and
              resources["cgroup_aware_memory_available_bytes"]>=12*1024**3)
    base_env=os.environ.copy()
    base_env.update(OMP_NUM_THREADS="1",MKL_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",
                    NUMEXPR_NUM_THREADS="1",PYTHONDONTWRITEBYTECODE="1")
    commands=[]
    for gpu_id,kind in ((0,"dino2"),(1,"dino3")):
        cmd=[sys.executable,str(Path(__file__).resolve()),phase,"--kind",kind]
        if phase=="evaluate":cmd.extend(["--split",args.split])
        commands.append((gpu_id,kind,cmd))
    if not parallel:
        print("A0_PAIR_SEQUENTIAL_LOW_SHARED_RESOURCES",json.dumps(resources),flush=True)
    launched=[]
    try:
        for gpu_id,kind,cmd in commands:
            env=base_env.copy();env["CUDA_VISIBLE_DEVICES"]=str(gpu_id)
            logpath=c["out"]/("pair_"+key+"_"+kind+".log")
            logpath.parent.mkdir(parents=True,exist_ok=True)
            logfile=logpath.open("x",encoding="utf-8")
            process=subprocess.Popen(cmd,env=env,stdout=logfile,stderr=subprocess.STDOUT)
            launched.append((kind,process,logfile,logpath))
            print("A0_PAIR_LAUNCHED",phase,kind,"gpu",gpu_id,"pid",process.pid,"log",logpath,flush=True)
            if not parallel:
                rc=process.wait();logfile.close()
                if rc:raise RuntimeError(kind+" "+key+" failed; see "+str(logpath))
        if parallel:
            remaining={kind for kind,_,_,_ in launched}
            while remaining:
                for kind,process,logfile,logpath in launched:
                    if kind not in remaining:continue
                    rc=process.poll()
                    if rc is None:continue
                    remaining.remove(kind);logfile.close()
                    print("A0_PAIR_EXIT",kind,rc,flush=True)
                    if rc:raise RuntimeError(kind+" "+key+" failed; see "+str(logpath))
                if remaining:time.sleep(2)
    except BaseException:
        for _,process,logfile,_ in launched:
            if process.poll() is None:process.terminate()
        for _,process,logfile,_ in launched:
            try:process.wait(timeout=30)
            except subprocess.TimeoutExpired:process.kill();process.wait()
            if not logfile.closed:logfile.close()
        raise
    receipt=dict(status="PAIR_PHASE_COMPLETE",phase=phase,split=args.split,observed_at=now(),
                 code_commit=commit,parallel=parallel,resources=resources,
                 outputs=[str(path) for path in outputs])
    write_once(c["out"]/("pair_"+key+"_complete.json"),receipt)
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("inventory","smoke","profile","train","evaluate","screen","status","pair"))
    p.add_argument("--root",default=str(ROOT))
    p.add_argument("--kind",choices=("dino2","dino3"))
    p.add_argument("--split",choices=("calibration","outer"))
    p.add_argument("--phase",choices=("smoke","profile","train","evaluate"))
    a=p.parse_args()
    if a.command in ("smoke","profile","train","evaluate") and not a.kind:p.error("--kind required")
    if a.command=="evaluate" and not a.split:p.error("--split required")
    if a.command=="pair" and not a.phase:p.error("--phase required")
    if a.command=="inventory":inventory(a)
    elif a.command=="smoke":smoke(a)
    elif a.command=="profile":run_profile(a)
    elif a.command=="train":run_train(a)
    elif a.command=="evaluate":run_evaluate(a)
    elif a.command=="screen":screen(a)
    elif a.command=="pair":run_pair(a)
    else:status(a)

if __name__=="__main__":main()
