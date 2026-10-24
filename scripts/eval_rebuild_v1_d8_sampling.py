import argparse,csv,json,os,sys
from datetime import datetime
from pathlib import Path
os.environ["CUDA_VISIBLE_DEVICES"]="0"; os.environ["CUBLAS_WORKSPACE_CONFIG"]=":4096:8"
ROOT=Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"); sys.path[:0]=[str(ROOT/"scripts"),str(ROOT)]
import numpy as np,torch
import train_rebuild_v1_r01_optical_only as r01
import train_rebuild_v1_r02_budget_pilot as r02
from eval_rebuild_v1_d7_semantic_errors import object_rows,rows_from_cm,write_csv
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--config",required=True); ap.add_argument("--run-dir",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
 cfg=r02.read_json(ROOT/a.config); run=ROOT/a.run_dir; summary=r02.read_json(run/"summary.json")
 if summary.get("global_step")!=4000 or summary.get("fixed_decision_step")!=4000 or summary.get("test6_loaded") is not False: raise RuntimeError("unsafe/incomplete D8 run")
 state=torch.load(run/"final_model.pth",map_location="cpu"); net,_,_=r01.build_model(cfg,Path(cfg["pretrain"]),resume_state=state); net.eval()
 split=r02.read_json(ROOT/cfg["split_file"]); ids=list(split["val2"]); assert not(set(ids)&set(split["historical_exposed_test6"]))
 with (ROOT/"records/rebuild_v1_d7_data_sampling_20260922/component_area_quantiles.csv").open(newline="",encoding="utf-8") as f: thresholds={x["class_name"]:(float(x["area_q25"]),float(x["area_q75"])) for x in csv.DictReader(f)}
 cm=np.zeros((r02.N_CLASSES,r02.N_CLASSES),np.int64); nbcm=np.zeros_like(cm); tile_rows=[]; class_rows=[]; objects=[]
 for tile in ids:
  d=r01.load_tile(Path(cfg["data_root"]),tile,True); pred=r01.infer_tile(net,d["optical"],int(cfg["patch"]),int(cfg["validation"]["stride"]),int(cfg["validation"]["inference_batch"])); tcm=np.zeros_like(cm); tnb=np.zeros_like(cm); r02.update_cm(tcm,d["full_gt"],pred); r02.update_cm(tnb,d["noboundary_gt"],pred); cm+=tcm; nbcm+=tnb
  m=r02.metrics_from_cm(tcm); mn=r02.metrics_from_cm(tnb); tile_rows.append({"model":cfg["model_id"],"tile":tile,"full_mIoU_fg5":m["mIoU_fg5"],"nb_mIoU_fg5":mn["mIoU_fg5"]}); class_rows+=rows_from_cm({"model":cfg["model_id"],"tile":tile},tcm); objects+=object_rows(42,cfg["model_id"],"clean",tile,d["full_gt"],pred,thresholds)
 m=r02.metrics_from_cm(cm); mn=r02.metrics_from_cm(nbcm); class_rows+=rows_from_cm({"model":cfg["model_id"],"tile":"ALL"},cm)
 grouped={}
 for x in objects:
  k=(x["tile"],x["class_name"],x["size_bin"]); grouped.setdefault(k,[]).append(x)
 obj=[]
 for (tile,cls,size),xs in grouped.items(): obj.append({"model":cfg["model_id"],"tile":tile,"class_name":cls,"size_bin":size,"objects":len(xs),"mean_correct_fraction":float(np.mean([x["correct_fraction"] for x in xs])),"recall_at_50pct":float(np.mean([x["recalled_at_50pct"] for x in xs]))})
 out=ROOT/a.out; out.mkdir(parents=True,exist_ok=False); write_csv(out/"per_tile_metrics.csv",tile_rows); write_csv(out/"per_class_metrics.csv",class_rows); write_csv(out/"object_size_metrics.csv",obj)
 (out/"summary.json").write_text(json.dumps({"recorded_at":datetime.now().astimezone().isoformat(timespec="seconds"),"model":cfg["model_id"],"fixed_step":4000,"full_mIoU_fg5":m["mIoU_fg5"],"nb_mIoU_fg5":mn["mIoU_fg5"],"test6_loaded":False},indent=2)+"\n")
 print("D8 EVAL COMPLETE",out)
if __name__=="__main__": main()
