import os, sys, csv, json, argparse, time
from datetime import datetime
from pathlib import Path
os.environ["CUDA_VISIBLE_DEVICES"]="0"; os.environ["CUBLAS_WORKSPACE_CONFIG"]=":4096:8"
ROOT=Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"); sys.path[:0]=[str(ROOT/"scripts"),str(ROOT)]
import numpy as np, torch
from scipy.ndimage import uniform_filter
import train_rebuild_v1_r01_optical_only as r01
import train_rebuild_v1_r02_budget_pilot as r02
from eval_rebuild_v1_d4_expert_complementarity import validate_run, oracle_prediction
from eval_rebuild_v1_d5_confidence_routing import infer_scores, softmax_np
from eval_rebuild_v1_dual_robust_conditions import down_restore

METHODS=("R01_optical","R05_dual","max_confidence","safe_explicit","safe_inferred_zero","pixel_oracle")
def masks(shape):
 h,w=shape; out={}
 for ratio in (.1,.25,.5):
  side=ratio**.5; hh,ww=int(h*side),int(w*side); y,x=(h-hh)//2,(w-ww)//2
  m=np.zeros(shape,bool); m[y:y+hh,x:x+ww]=1; out[f"rect_{int(100*ratio)}pct"]=m
 m=np.zeros(shape,bool); m[:,3*w//8:5*w//8]=1; out["vertical_stripe_25pct"]=m
 m=np.zeros(shape,bool); m[3*h//8:5*h//8,:]=1; out["horizontal_stripe_25pct"]=m
 m=np.zeros(shape,bool)
 for ya,xa in ((1,1),(1,5),(5,1),(5,5)): m[ya*h//8:(ya+1)*h//8,xa*w//8:(xa+1)*w//8]=1
 out["four_blocks_625pct"]=m; return out
def conditions(shape):
 ms=masks(shape); out=[]
 for n,m in ms.items(): out.append((f"missing_{n}","missing",m,None))
 base=ms["rect_25pct"]
 for kind in ("blur5","down2","down4","down8"): out.append((f"local_{kind}_rect25","degraded",base,kind))
 return out
def write(path,rows):
 with open(path,"w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n"); w.writeheader(); w.writerows(rows)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--seed",type=int,choices=[17,42],required=True); ap.add_argument("--smoke",action="store_true"); a=ap.parse_args()
 d1=ROOT/f"runs/rebuild_v1/R01_optical_only_seed{a.seed}_sched16000_stop16000"; d5=ROOT/f"runs/rebuild_v1/R05_dual_f0_quality_plus_dropout_seed{a.seed}_sched16000_stop16000"
 _,c1=validate_run(d1); _,c5=validate_run(d5); cfg1=r02.read_json(ROOT/"configs/rebuild_v1/r01_optical_only_16k.json"); cfg5=r02.read_json(ROOT/"configs/rebuild_v1/r05_quality_plus_dropout_16k.json")
 split=r02.read_json(ROOT/cfg5["split_file"]); ids=list(split["val2"][:1] if a.smoke else split["val2"]); assert not(set(ids)&set(split["historical_exposed_test6"]))
 s1=torch.load(c1,map_location="cpu"); s5=torch.load(c5,map_location="cpu"); n1,_,_=r01.build_model(cfg1,Path(cfg1["pretrain"]),resume_state=s1); n5,_=r02.build_model(cfg5,Path(cfg5["pretrain"]),resume_state=s5); n1.eval(); n5.eval()
 patch=int(cfg5["patch"]); stride=int(cfg5["validation"]["stride"]); batch=int(cfg5["validation"]["inference_batch"]); cms={}; timings=[]
 for tile in ids:
  d=r02.load_tile(Path(cfg5["data_root"]),tile,True); specs=conditions(d["dsm"].shape); specs=specs[:2] if a.smoke else specs
  t=time.time(); p1=softmax_np(infer_scores(n1,d["optical"],d["dsm"],patch,stride,batch,True)); timings.append({"seed":a.seed,"tile":tile,"expert":"R01","condition":"optical_once","seconds":time.time()-t})
  pred1=p1.argmax(0).astype(np.uint8)
  for name,family,mask,kind in specs:
   treated=d["dsm"].copy()
   if family=="missing": treated[mask]=0
   else:
    degraded=uniform_filter(d["dsm"],size=5,mode="reflect").astype(np.float32) if kind=="blur5" else down_restore(d["dsm"],int(kind[4:]))
    treated[mask]=degraded[mask]
   t=time.time(); p5=softmax_np(infer_scores(n5,d["optical"],treated,patch,stride,batch,False)); timings.append({"seed":a.seed,"tile":tile,"expert":"R05","condition":name,"seconds":time.time()-t})
   pred5=p5.argmax(0).astype(np.uint8); choose=p5.max(0)>p1.max(0); inferred=treated==0
   for sp,gt in (("full",d["full_gt"]),("noboundary",d["noboundary_gt"])):
    preds={"R01_optical":pred1,"R05_dual":pred5,"max_confidence":np.where(choose,pred5,pred1),"safe_explicit":np.where(choose&~(mask if family=="missing" else False),pred5,pred1),"safe_inferred_zero":np.where(choose&~inferred,pred5,pred1),"pixel_oracle":oracle_prediction(gt,pred1,pred5)}
    for method,pred in preds.items():
     key=(name,family,method,sp); cms.setdefault(key,np.zeros((r02.N_CLASSES,r02.N_CLASSES),np.int64)); r02.update_cm(cms[key],gt,pred)
 rows=[]
 for (name,family,method,sp),cm in cms.items():
  mt=r02.metrics_from_cm(cm); rows.append({"condition":name,"family":family,"method":method,"split":sp,"mIoU_fg5":mt["mIoU_fg5"],"OA":mt["OA"]})
 suffix="_smoke" if a.smoke else ""; out=ROOT/f"records/rebuild_v1_d6_mask_generalization_seed{a.seed}_20260920{suffix}"; out.mkdir(parents=True,exist_ok=True); write(out/"method_metrics.csv",rows); write(out/"timings.csv",timings)
 (out/"summary.json").write_text(json.dumps({"recorded_at":datetime.now().astimezone().isoformat(timespec="seconds"),"seed":a.seed,"smoke":a.smoke,"historical_test6_loaded":False,"methods":METHODS},indent=2)+"\n",encoding="utf-8"); print("D6 COMPLETE",out)
if __name__=="__main__": main()
