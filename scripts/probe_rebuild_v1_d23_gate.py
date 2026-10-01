"""D23-B bounded crop-only GPU resource probe; no formal training or dev evaluation."""
import argparse
from datetime import datetime
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

EXPECTED={"R0":"29aa15f4cd149012996ddeadd7a5b40f593f99854318acd1d0d0acb286ed5975",
          "M0":"23b2939ea50867c96c0a17626fd4a85a27100ebd8296b2fc96440ed8bc3d34de"}
START=time.monotonic()


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(4*1024*1024),b""): h.update(b)
    return h.hexdigest()


def write(p,x):
    with Path(p).open("x",encoding="utf-8") as f:
        json.dump(x,f,indent=2,allow_nan=False);f.write("\n")


def gpu_inventory():
    text=subprocess.check_output(["nvidia-smi","--query-gpu=index,uuid,memory.used,utilization.gpu",
                                  "--format=csv,noheader,nounits"],text=True)
    result={}
    for line in text.splitlines():
        index,uuid,memory,util=(v.strip() for v in line.split(","))
        result[int(index)]={"uuid":uuid,"used_mib":int(memory),"util_percent":int(util)}
    return result


def require_idle(info):
    if info["used_mib"]>1024 or info["util_percent"]>5:
        raise RuntimeError("requested physical GPU is busy; no job is interrupted")


def reject_existing_compute(uuid):
    lines=subprocess.check_output(["nvidia-smi","--query-compute-apps=gpu_uuid,pid","--format=csv,noheader"],text=True)
    if any(line.split(",",1)[0].strip()==uuid for line in lines.splitlines()):
        raise RuntimeError("requested GPU already has a compute process")


def guard(torch):
    import resource
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    if time.monotonic()-START>1800: raise RuntimeError("30-minute probe cap reached")
    if rss>8*1024**3: raise RuntimeError("8-GiB host RSS cap reached")
    if torch.cuda.max_memory_allocated()>32*1024**3 or torch.cuda.max_memory_reserved()>40*1024**3:
        raise RuntimeError("GPU allocated/reserved protection reached")
    return int(rss)


def compare_logits(reference, candidate):
    """Pixelwise diagnostics; aggregate utility counts cannot establish equality."""
    import torch
    if reference.shape != candidate.shape or not torch.isfinite(candidate).all():
        raise RuntimeError("invalid diagnostic logits")
    changed=reference.argmax(1)!=candidate.argmax(1)
    margin=reference.topk(2,dim=1).values
    margin=margin[:,0]-margin[:,1]
    return {"pixels":changed.numel(),"changed_pixels":int(changed.sum()),
            "max_abs_logit_delta":float((reference-candidate).abs().max()),
            "changed_reference_margin_max":float(margin[changed].max()) if changed.any() else None}


def decision_audit(torch, pair, views, truth, out):
    """No gate optimization. Compare microbatch partitions and repeat each partition."""
    references=[]
    for optical,secondary,mask in views:
        chunks={key:[] for key in ("z0","z1")}
        for start in range(0,16,2):
            inp=pair(optical[start:start+2],secondary[start:start+2])
            for key in chunks: chunks[key].append(inp[key].cpu())
            del inp
        references.append({key:torch.cat(value) for key,value in chunks.items()})
    rows=[]
    for micro in (2,4,8,16):
        repeats=[]
        for repeat in range(2):
            counts={"valid":0,"positive":0,"negative":0}; comparisons=[]; hashes=[]
            for vi,(optical,secondary,mask) in enumerate(views):
                digests={key:hashlib.sha256() for key in ("z0","z1")}
                totals={key:{"pixels":0,"changed_pixels":0,"max_abs_logit_delta":0.,
                             "changed_reference_margin_max":None} for key in digests}
                for start in range(0,16,micro):
                    stop=start+micro;inp=pair(optical[start:stop],secondary[start:stop])
                    p0,p1=inp["z0"].argmax(1),inp["z1"].argmax(1)
                    y=truth[start:stop];m=mask[start:stop]
                    counts["valid"]+=y.numel()
                    counts["positive"]+=int((m&(p1==y)&(p0!=y)).sum())
                    counts["negative"]+=int((m&(p0==y)&(p1!=y)).sum())
                    for key in digests:
                        candidate=inp[key].cpu()
                        digests[key].update(candidate.argmax(1).numpy().tobytes())
                        comparison=compare_logits(references[vi][key][start:stop],candidate)
                        for name in ("pixels","changed_pixels"):totals[key][name]+=comparison[name]
                        totals[key]["max_abs_logit_delta"]=max(totals[key]["max_abs_logit_delta"],comparison["max_abs_logit_delta"])
                        value=comparison["changed_reference_margin_max"]
                        if value is not None:
                            totals[key]["changed_reference_margin_max"]=max(totals[key]["changed_reference_margin_max"] or 0.,value)
                        del candidate
                    del inp,p0,p1
                    guard(torch)
                hashes.append({key:value.hexdigest() for key,value in digests.items()})
                comparisons.append({"view":"clean" if vi==0 else "aux_local_zero", "experts":totals})
            repeats.append({"utility_counts":counts,"prediction_sha256":hashes,"comparisons":comparisons})
        stable=(repeats[0]["prediction_sha256"]==repeats[1]["prediction_sha256"] and
                repeats[0]["utility_counts"]==repeats[1]["utility_counts"])
        row={"micro_batch":micro,"reference_micro_batch":2,"repeat_prediction_stable":stable,"repeats":repeats}
        write(out/("decision_micro%d.json"%micro),row);rows.append(row)
        print("D23_B_DECISION_AUDIT",json.dumps(row),flush=True)
        if not stable:raise RuntimeError("fixed-microbatch expert prediction not repeatable")
    return rows


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--gate-module",type=Path,required=True)
    ap.add_argument("--gpu",type=int,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--decision-audit-only",action="store_true")
    args=ap.parse_args()
    root,out=args.root.resolve(),args.output.resolve()
    scope_root=Path("/home/jovyan/zzx").resolve()
    root.relative_to(scope_root)
    args.gate_module.resolve().relative_to(scope_root)
    out.relative_to(root/"records")
    if out.exists(): raise RuntimeError("refuse to overwrite output")
    out.mkdir(parents=True)
    try:
        inventory=gpu_inventory()
        if args.gpu not in inventory: raise RuntimeError("physical GPU not present")
        require_idle(inventory[args.gpu])
        uuid=inventory[args.gpu]["uuid"]
        reject_existing_compute(uuid)
        os.environ["CUDA_VISIBLE_DEVICES"]=uuid
        os.environ["CUBLAS_WORKSPACE_CONFIG"]=":4096:8"
        os.environ["XFORMERS_DISABLED"]="1"
        import numpy as np
        from PIL import Image
        import torch
        from torch.nn import functional as F
        if torch.cuda.device_count()!=1: raise RuntimeError("one visible GPU required")
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark=False
        torch.backends.cudnn.deterministic=True
        # Preserve fresh-process D21 backend defaults; saved-probe reproduction checks compatibility.
        torch.set_num_threads(1)
        np.random.seed(42);torch.manual_seed(42);torch.cuda.manual_seed_all(42)
        spec=importlib.util.spec_from_file_location("d23_gate",args.gate_module)
        g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
        sys.path.insert(0,str(root))
        from model.rebuild_v1_night_screen import load_dino
        from model.rebuild_v1_d21_detail import DetailDinoSegmenter

        dcfg=read(root/"configs/rebuild_v1/d18_d19_night_20260927.json")["dino"]
        repository=(root/dcfg["repository_dir"]).resolve()
        weights=(root/dcfg["weights_path"]).resolve()
        repository.relative_to(scope_root);weights.relative_to(scope_root)
        repo_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=repository,text=True).strip()
        subprocess.run(["git","diff","--exit-code","HEAD","--","dinov2","hubconf.py"],cwd=repository,check=True)
        base=read(root/"configs/rebuild_v1/r05_quality_plus_dropout_16k.json")
        split=read(root/base["split_file"])
        tile="2_12"
        if tile not in split["train16"] or tile in split["val2"] or tile in split["historical_exposed_test6"]:
            raise RuntimeError("probe tile must be gate-fit training tile")
        experts={};bindings=[]
        for arm,expected in EXPECTED.items():
            run=root/"runs/rebuild_v1"/("D21_potsdam_"+arm+"_seed42_16000_20260928")
            row=read(run/"summary.json")
            if row["job"]!={"dataset":"potsdam","arm":arm,"seed":42} or row["global_step"]!=16000 or row["test6_loaded"] is not False:
                raise RuntimeError("expert identity mismatch")
            ck=run/"last_train_state.pth"
            if row["checkpoint_sha256"]!=expected or sha(ck)!=expected: raise RuntimeError("expert weight SHA mismatch")
            signature=row["signature"]
            for name in ("model/rebuild_v1_d21_detail.py","model/rebuild_v1_night_screen.py",
                         "configs/rebuild_v1/r05_quality_plus_dropout_16k.json",base["split_file"]):
                if sha(root/name)!=signature["source_sha256"].get(name): raise RuntimeError("D21 executed source changed: "+name)
            if repo_commit!=signature["dino_commit"] or sha(weights)!=signature["dino_sha256"]:
                raise RuntimeError("DINO binding mismatch")
            if torch.__version__!=signature["torch_version"]: raise RuntimeError("use exact D21 torch environment")
            state=torch.load(ck,map_location="cpu",weights_only=False)
            if state["signature"]!=signature: raise RuntimeError("loaded checkpoint signature mismatch")
            model=DetailDinoSegmenter(load_dino(repository,weights),arm)
            model.load_state_dict(state["model"],strict=True);del state
            experts[arm]=model.to("cuda").eval()
            probe=run/"clean_probe.pth"
            if sha(probe)!=row["clean_probe_sha256"]: raise RuntimeError("saved training probe SHA mismatch")
            saved=torch.load(probe,map_location="cpu",weights_only=False)
            with torch.no_grad(): pred=model(saved["rgb"].cuda(),saved["aux"].cuda()).argmax(1).cpu()
            if not torch.equal(pred,saved["pred"]): raise RuntimeError("D21 saved training prediction not reproduced")
            bindings.append({"arm":arm,"checkpoint_sha256":expected,"saved_training_probe_reproduced":True})
            del saved,pred
            guard(torch)
        pair=g.FrozenExpertPair(experts["R0"],experts["M0"])
        before={arm:sha(root/"runs/rebuild_v1"/("D21_potsdam_"+arm+"_seed42_16000_20260928")/"last_train_state.pth") for arm in EXPECTED}
        # Load one training tile only; no Val2 labels/images and no all-tile feature cache.
        data=Path(base["data_root"])
        data.resolve().relative_to(scope_root)
        label_path=data/"5_Labels_for_participants"/("top_potsdam_"+tile+"_label.tif")
        rgb_path=data/"2_Ortho_RGB"/("top_potsdam_"+tile+"_RGB.tif")
        a,b=(int(x) for x in tile.split("_"))
        ds_path=data/"1_DSM/1_DSM"/("dsm_potsdam_%02d_%02d.tif"%(a,b))
        manifest=read(root/"records/rebuild_v1_d21_queue_20260928/input_manifest.json")
        manifest_rows={x["path"]:x for x in manifest["files"]}
        for path in (rgb_path,ds_path,label_path):
            row=manifest_rows.get(str(path))
            if row is None or sha(path)!=row["sha256"]: raise RuntimeError("training input SHA mismatch")
        with Image.open(rgb_path) as im: rgb=np.array(im.convert("RGB"))
        with Image.open(ds_path) as im: ds=np.array(im,dtype=np.float32)
        with Image.open(label_path) as im: label_rgb=np.array(im.convert("RGB"))
        if not (rgb.shape[:2]==ds.shape==label_rgb.shape[:2]) or not np.isfinite(ds).all():
            raise RuntimeError("training image shape/value mismatch")
        dmin,dmax=float(ds.min()),float(ds.max())
        if dmax<=dmin: raise RuntimeError("constant DSM")
        colors=((255,255,255),(0,0,255),(0,255,255),(0,255,0),(255,255,0),(255,0,0))
        rng=np.random.default_rng(42);ops=[];auxs=[];ys=[]
        for i in range(16):
            y=int(rng.integers(0,ds.shape[0]-512+1));x=int(rng.integers(0,ds.shape[1]-512+1))
            rr=label_rgb[y:y+512,x:x+512]
            yy=np.full((512,512),255,np.int64)
            for k,c in enumerate(colors): yy[np.all(rr==c,axis=-1)]=k
            if (yy==255).any(): raise RuntimeError("unknown training label color")
            ops.append(torch.from_numpy(rgb[y:y+512,x:x+512].copy()).permute(2,0,1).float()/255)
            auxs.append(torch.from_numpy(((ds[y:y+512,x:x+512]-dmin)/(dmax-dmin)).copy()))
            ys.append(torch.from_numpy(yy))
        del rgb,ds,label_rgb;gc.collect()
        op,aux,y=torch.stack(ops).cuda(),torch.stack(auxs).cuda(),torch.stack(ys).cuda()
        del ops,auxs,ys
        available=torch.ones_like(aux,dtype=torch.bool);available[:,128:384,128:384]=False
        treated=torch.where(available,aux,torch.zeros_like(aux))
        views=((op,aux,torch.ones_like(available)),(op,treated,available))
        if args.decision_audit_only:
            write(out/"preflight.json",{"observed_at":datetime.now().astimezone().isoformat(),
                  "gpu":args.gpu,"uuid":uuid,"torch_version":torch.__version__,"bindings":bindings,
                  "matmul_allow_tf32":torch.backends.cuda.matmul.allow_tf32,
                  "cudnn_allow_tf32":torch.backends.cudnn.allow_tf32,
                  "script_sha256":sha(Path(__file__)),"gate_sha256":sha(args.gate_module)})
            rows=decision_audit(torch,pair,views,y,out)
            for arm in EXPECTED:
                if sha(root/"runs/rebuild_v1"/("D21_potsdam_"+arm+"_seed42_16000_20260928")/"last_train_state.pth")!=before[arm]:
                    raise RuntimeError("expert checkpoint file changed")
            write(out/"summary.json",{"status":"DECISION_AUDIT_COMPLETE","observed_at":datetime.now().astimezone().isoformat(),
                  "gpu":args.gpu,"uuid":uuid,"rows":rows,"test6_loaded":False,
                  "development_labels_loaded":False,"formal_training_started":False,
                  "checkpoint_saved":False,"cross_microbatch_differences_are_diagnostic_only":True})
            return 0
        rows=[];baseline_counts=None
        for micro in (2,4,8,16):
            torch.manual_seed(42);gate=g.DenseBenefitGate("TSF").cuda()
            optimizer=torch.optim.AdamW(gate.parameters(),lr=3e-4,weight_decay=.01)
            torch.cuda.empty_cache();torch.cuda.reset_peak_memory_stats()
            times=[];counts_last=None;loss_last=None
            for step in range(12):
                torch.cuda.synchronize();began=time.monotonic()
                # Two passes avoid caching all full-batch dense features; this timing includes both.
                counts={"valid":0,"positive":0,"negative":0}
                for optical,secondary,mask in views:
                    for start in range(0,16,micro):
                        stop=start+micro
                        inp=pair(optical[start:stop],secondary[start:stop])
                        p0,p1=inp["z0"].argmax(1),inp["z1"].argmax(1)
                        truth=y[start:stop];m=mask[start:stop]
                        counts["valid"]+=truth.numel()
                        counts["positive"]+=int((m&(p1==truth)&(p0!=truth)).sum())
                        counts["negative"]+=int((m&(p0==truth)&(p1!=truth)).sum())
                        del inp,p0,p1
                if baseline_counts is None: baseline_counts=counts.copy()
                if counts!=baseline_counts: raise RuntimeError("expert decisions changed across steps/microbatches")
                optimizer.zero_grad(set_to_none=True);value=0.
                for optical,secondary,mask in views:
                    for start in range(0,16,micro):
                        stop=start+micro
                        inp=pair(optical[start:stop],secondary[start:stop])
                        result=gate(inp["E"],inp["S"],inp["F"],inp["z0"],inp["z1"],mask[start:stop])
                        parts=g.loss_sums(result["logits"],result["gate_logits"],inp["z0"],inp["z1"],y[start:stop],mask[start:stop])
                        loss=parts["ce_sum"]/counts["valid"]+.5*(
                            parts["positive_sum"]/max(1,counts["positive"])+parts["negative_sum"]/max(1,counts["negative"]))
                        loss.backward();value+=float(loss.detach())
                        if not torch.equal(result["logits"].permute(0,2,3,1)[~mask[start:stop]],
                                           inp["z0"].permute(0,2,3,1)[~mask[start:stop]]):
                            raise RuntimeError("missing-region fallback mismatch")
                        del inp,result,parts,loss
                torch.nn.utils.clip_grad_norm_(gate.parameters(),float("inf"),error_if_nonfinite=True)
                if any(p.grad is not None for p in pair.parameters()): raise RuntimeError("expert received a gradient")
                optimizer.step();torch.cuda.synchronize()
                times.append(time.monotonic()-began)
                counts_last,loss_last=counts,value
                guard(torch)
            row={"micro_batch":micro,"accum_steps":16//micro,"effective_batch":16,
                 "warmup_steps":2,"measured_steps":10,"step_median_seconds":statistics.median(times[2:]),
                 "step_times_seconds":times[2:],"gpu_peak_allocated_bytes":torch.cuda.max_memory_allocated(),
                 "gpu_peak_reserved_bytes":torch.cuda.max_memory_reserved(),"host_peak_rss_bytes":guard(torch),
                 "loss_final":loss_last,"utility_counts":counts_last,
                 "scope":"two_pass_frozen_experts_two_views_TSF_training_crop_only"}
            rows.append(row);write(out/("micro%d.json"%micro),row)
            print("D23_B_CROP_PROFILE",json.dumps(row),flush=True)
            del gate,optimizer;gc.collect();torch.cuda.empty_cache()
        for arm in EXPECTED:
            if sha(root/"runs/rebuild_v1"/("D21_potsdam_"+arm+"_seed42_16000_20260928")/"last_train_state.pth")!=before[arm]:
                raise RuntimeError("expert checkpoint file changed")
        final_inventory=gpu_inventory()
        if final_inventory[args.gpu]["uuid"]!=uuid: raise RuntimeError("physical GPU UUID changed")
        payload={"status":"CROP_PROFILE_COMPLETE","observed_at":datetime.now().astimezone().isoformat(),
                 "gpu":args.gpu,"uuid":uuid,"gpu_before":inventory[args.gpu],"gpu_at_completion":final_inventory[args.gpu],
                 "torch_version":torch.__version__,"tile":tile,"bindings":bindings,"profiles":rows,
                 "matmul_allow_tf32":torch.backends.cuda.matmul.allow_tf32,
                 "cudnn_allow_tf32":torch.backends.cudnn.allow_tf32,
                 "script_sha256":sha(Path(__file__)),"gate_sha256":sha(args.gate_module),
                 "test6_loaded":False,"development_labels_loaded":False,"independent_final_loaded":False,
                 "formal_training_started":False,"checkpoint_saved":False,
                 "remaining_before_formal":["single training/evaluation engine","14-condition full-image evaluation and post-stitch fallback",
                                           "TCAP fit statistics","full-image resource benchmark","frozen wall/job and disk caps"],
                 "elapsed_seconds":time.monotonic()-START}
        write(out/"summary.json",payload)
        print("D23_B_CROP_PROFILE_COMPLETE",str(out),flush=True)
        return 0
    except Exception as exc:
        write(out/"failure.json",{"status":"TECHNICAL_FAILURE","observed_at":datetime.now().astimezone().isoformat(),
                                 "error":str(exc),"formal_training_started":False})
        print("D23_B_PROBE_FAILURE",str(exc),file=sys.stderr,flush=True)
        return 2


if __name__=="__main__": sys.exit(main())
