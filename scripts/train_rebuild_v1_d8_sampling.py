import argparse, csv, json, os, random, subprocess, sys, time
from collections import Counter
from datetime import datetime
from pathlib import Path
os.environ["CUDA_VISIBLE_DEVICES"]="0"; os.environ["CUBLAS_WORKSPACE_CONFIG"]=":4096:8"
ROOT=Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"); sys.path[:0]=[str(ROOT/"scripts"),str(ROOT)]
import numpy as np, torch
import torch.nn.functional as F
from scipy import ndimage
import train_rebuild_v1_r01_optical_only as r01
import train_rebuild_v1_r02_budget_pilot as r02

def now(): return datetime.now().astimezone().isoformat(timespec="seconds")
def head():
 try: return subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
 except Exception: return None
def append(path,header,row):
 new=not path.exists()
 with path.open("a",newline="",encoding="utf-8") as f:
  w=csv.writer(f); w.writerow(header) if new else None; w.writerow(row)
def component_centers(gt, threshold=None):
 labels,n=ndimage.label(gt==4,structure=np.ones((3,3),np.uint8)); areas=np.bincount(labels.ravel())[1:]
 centers=[]
 for i,box in enumerate(ndimage.find_objects(labels),1):
  if box is None or (threshold is not None and areas[i-1]>threshold): continue
  cy=(box[0].start+box[0].stop-1)//2; cx=(box[1].start+box[1].stop-1)//2
  centers.append((cy,cx,int(areas[i-1])))
 return centers
def sample_batch(cache,ids,cfg,mode,indices,counts):
 patch=int(cfg["patch"]); aug=cfg["augmentation"]; ops=[]; gts=[]; scales=[]
 for _ in range(int(cfg["micro_batch"])):
  tile=random.choice(ids); op,gt=cache[tile]; h,w=gt.shape
  scale=random.uniform(float(aug["random_scale_min"]),float(aug["random_scale_max"])); source=max(1,min(int(round(patch/scale)),h,w))
  aware=mode!="random_ce" and random.random()<float(aug["aware_crop_p"])
  pool=indices[tile]["small" if mode=="small_car" else "all"] if aware else []
  if pool:
   cy,cx,_=random.choice(pool); jy=random.randint(-source//4,source//4); jx=random.randint(-source//4,source//4)
   y=max(0,min(h-source,cy-source//2+jy)); x=max(0,min(w-source,cx-source//2+jx)); treatment=mode
  else:
   y=random.randint(0,h-source); x=random.randint(0,w-source); treatment="random"
  a=op[y:y+source,x:x+source]; b=gt[y:y+source,x:x+source]
  if random.random()<float(aug["vertical_flip_p"]): a,b=a[::-1],b[::-1]
  if random.random()<float(aug["horizontal_flip_p"]): a,b=a[:,::-1],b[:,::-1]
  at=torch.from_numpy(np.ascontiguousarray(a.transpose(2,0,1))).float()[None]; bt=torch.from_numpy(np.ascontiguousarray(b)).float()[None,None]
  if source!=patch: at=F.interpolate(at,size=(patch,patch),mode="bilinear",align_corners=False); bt=F.interpolate(bt,size=(patch,patch),mode="nearest")
  ops.append(at[0]); gts.append(bt[0,0].long()); scales.append(scale); counts[treatment]+=1
 return torch.stack(ops).cuda(),torch.stack(gts).cuda(),scales
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--config",required=True); ap.add_argument("--smoke-steps",type=int,default=0); ap.add_argument("--smoke-eval",action="store_true"); ap.add_argument("--run-tag",default=""); a=ap.parse_args()
 cfg=r02.read_json(ROOT/a.config); mode=cfg["sampling"]["mode"]
 if mode not in {"random_ce","any_car","small_car"}: raise RuntimeError(mode)
 split=r02.read_json(ROOT/cfg["split_file"]); ids=list(split["train16"]); vals=list(split["val2"])
 if (set(ids)|set(vals))&set(split["historical_exposed_test6"]): raise RuntimeError("TEST6 overlap")
 seed=int(cfg["seed"]); r02.set_seed(seed); cache,valcache=r01.preload(Path(cfg["data_root"]),ids,vals)
 threshold=int(cfg["sampling"]["small_car_max_area"]); indices={}
 for tile in ids:
  gt=cache[tile][1]; indices[tile]={"all":component_centers(gt),"small":component_centers(gt,threshold)}
  if not indices[tile]["small"]: raise RuntimeError(f"no small Car in {tile}")
 init=ROOT/cfg["student_init"]; state=torch.load(init,map_location="cpu"); net,_,audit=r01.build_model(cfg,Path(cfg["pretrain"]),resume_state=state)
 opt=r02.build_optimizer(net,cfg); total=int(cfg["schedule"]["scheduler_total_steps"]); target=a.smoke_steps or int(cfg["schedule"]["stop_at_step"])
 kind=f"smoke{a.smoke_steps}" if a.smoke_steps else f"sched{total}_stop{target}"; suffix=f"_{a.run_tag}" if a.run_tag else ""
 run=ROOT/"runs/rebuild_v1"/f"D8_{mode}_seed{seed}_{kind}{suffix}"; run.mkdir(parents=True,exist_ok=False)
 signature={"experiment_id":cfg["model_id"],"mode":mode,"seed":seed,"student_init":str(init),"small_car_max_area":threshold,"test6_loaded":False}
 (run/"run_metadata.json").write_text(json.dumps({"started_at":now(),"git_commit":head(),"config":cfg,"signature":signature,"structural_audit":audit},indent=2)+"\n")
 counts=Counter(); losses=[]; start=now(); torch.cuda.reset_peak_memory_stats()
 for step in range(1,target+1):
  t=time.time(); lrs=r02.set_lr(opt,cfg,step,total); opt.zero_grad(set_to_none=True); micro=[]; scales=[]
  for _ in range(int(cfg["accum_steps"])):
   x,y,s=sample_batch(cache,ids,cfg,mode,indices,counts); z=net(x)
   # The server CUDA build has no deterministic NCHW nll_loss2d kernel.
   # The flattened 2-D CE path is the already validated B1/B2 solution.
   flat_z=z.permute(0,2,3,1).contiguous().view(-1,z.shape[1]); flat_y=y.contiguous().view(-1)
   loss=F.cross_entropy(flat_z,flat_y)
   if not torch.isfinite(loss): raise RuntimeError("non-finite loss")
   (loss/int(cfg["accum_steps"])).backward(); micro.append(float(loss.detach())); scales+=s
  opt.step(); torch.cuda.synchronize(); lv=float(np.mean(micro)); losses.append(lv)
  append(run/"train_history.csv",["step","lr_backbone","lr_decoder_head","loss","mean50","scale_mean","sec"],[step,lrs["backbone"],lrs["decoder_head"],lv,float(np.mean(losses[-50:])),float(np.mean(scales)),time.time()-t])
  if step==1 or step%20==0: print(f"step {step:05d}/{target} loss={lv:.6f} counts={dict(counts)}",flush=True)
  if (a.smoke_steps and a.smoke_eval and step==target) or (not a.smoke_steps and (step%1000==0 or step==target)):
   m=r01.evaluate_val(net,valcache,vals,cfg); append(run/"val_history.csv",["step","full_mIoU_fg5","nb_mIoU_fg5"],[step,m["full"]["mIoU_fg5"],m["noboundary"]["mIoU_fg5"]]); print("VAL",step,m["full"]["mIoU_fg5"],m["noboundary"]["mIoU_fg5"],flush=True)
  if step%250==0 or step==target: torch.save({"model":net.state_dict(),"global_step":step,"signature":signature},run/"last_train_state.pth")
 final=run/"final_model.pth"; torch.save({"model":net.state_dict(),"global_step":target,"signature":signature},final)
 summary={"experiment_id":cfg["model_id"],"mode":mode,"started_at":start,"completed_at":now(),"git_commit":head(),"global_step":target,"fixed_decision_step":4000,"checkpoint":str(final),"sampling_counts":dict(counts),"test6_loaded":False,"peak_allocated_gib":torch.cuda.max_memory_allocated()/1024**3}
 (run/"summary.json").write_text(json.dumps(summary,indent=2)+"\n"); print("COMPLETE",json.dumps(summary),flush=True)
if __name__=="__main__": main()
