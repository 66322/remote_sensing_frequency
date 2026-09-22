import csv,json
from pathlib import Path
ROOT=Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
MODES={"C":"random_ce","A":"any_car","S":"small_car"}
def rows(p):
 with p.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def one(xs,**q):
 z=[x for x in xs if all(x[k]==str(v) for k,v in q.items())]
 if len(z)!=1:raise RuntimeError((q,len(z)))
 return z[0]
def main():
 data={}
 for arm,mode in MODES.items():
  d=ROOT/f"records/rebuild_v1_d8_{mode}_eval_20260922"; s=json.loads((d/"summary.json").read_text()); pc=rows(d/"per_class_metrics.csv"); ob=rows(d/"object_size_metrics.csv")
  car=one(pc,tile="ALL",class_name="Car"); small=[x for x in ob if x["class_name"]=="Car" and x["size_bin"]=="small"]
  n=sum(int(x["objects"]) for x in small); mc=sum(float(x["mean_correct_fraction"])*int(x["objects"]) for x in small)/n; rr=sum(float(x["recall_at_50pct"])*int(x["objects"]) for x in small)/n
  data[arm]={"full_mIoU_fg5":s["full_mIoU_fg5"],"nb_mIoU_fg5":s["nb_mIoU_fg5"],"car_iou":float(car["IoU"]),"car_precision":float(car["precision"]),"small_car_mean_correct":mc,"small_car_recall50":rr,"per_tile_small_mean_correct":{x["tile"]:float(x["mean_correct_fraction"]) for x in small}}
 c=data["C"]; gates={}
 for arm in ("A","S"):
  x=data[arm]; delta={k:100*(x[k]-c[k]) for k in ("nb_mIoU_fg5","car_iou","car_precision","small_car_mean_correct","small_car_recall50")}; same=all(x["per_tile_small_mean_correct"][t]>c["per_tile_small_mean_correct"][t] for t in c["per_tile_small_mean_correct"]); gates[arm]={"delta_pp":delta,"per_tile_same_positive_direction":same,"pass":delta["small_car_recall50"]>=3 and delta["small_car_mean_correct"]>=2 and delta["car_iou"]>=.5 and delta["car_precision"]>=-1 and delta["nb_mIoU_fg5"]>=-.3 and same}
 out=ROOT/"records/rebuild_v1_d8_summary_20260922";out.mkdir(parents=True,exist_ok=True);(out/"decision_evidence.json").write_text(json.dumps({"experiment_id":"D8_SMALL_CAR_SAMPLING_SCREEN","fixed_step":4000,"test6_loaded":False,"metrics":data,"gates":gates,"proceed_seed17":[a for a,g in gates.items() if g["pass"]]},indent=2)+"\n");print(json.dumps(gates,indent=2))
if __name__=="__main__":main()
