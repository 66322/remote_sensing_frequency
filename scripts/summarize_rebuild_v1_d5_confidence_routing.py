import csv, json
from datetime import datetime
from pathlib import Path

ROOT=Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
OUT=ROOT/"records/rebuild_v1_d5_confidence_routing_summary_20260920"
DEPLOY=("prob_avg","prob_alpha25","prob_alpha75","max_confidence","min_entropy","safe_max_confidence")

def load(seed):
    p=ROOT/f"records/rebuild_v1_d5_confidence_routing_seed{seed}_20260920/method_metrics.csv"
    with open(p,newline="",encoding="utf-8") as f: return list(csv.DictReader(f))

def score(rows,c,m):
    r=next(x for x in rows if x["condition"]==c and x["method"]==m and x["split"]=="noboundary")
    return 100*float(r["mIoU_fg5"])

def main():
    OUT.mkdir(parents=True,exist_ok=True); evidence={}; table=[]
    for seed in (42,17):
        rows=load(seed); conditions=sorted({x["condition"] for x in rows})
        r01=score(rows,"clean","R01_optical")
        candidates={}
        for method in DEPLOY:
            clean=score(rows,"clean",method); zero=score(rows,"dsm_zero",method); down8=score(rows,"dsm_down8",method)
            best_clean=max(score(rows,"clean","R01_optical"),score(rows,"clean","R05_dual"))
            best_down8=max(score(rows,"dsm_down8","R01_optical"),score(rows,"dsm_down8","R05_dual"))
            passed=(clean>=best_clean-0.2 and zero>=r01-0.2 and down8>=best_down8-0.2)
            candidates[method]={"clean":clean,"dsm_zero":zero,"dsm_down8":down8,"pass":passed}
            table.append({"seed":seed,"method":method,**candidates[method]})
        evidence[str(seed)]={"candidates":candidates,"passing_methods":[m for m,v in candidates.items() if v["pass"]]}
    shared=sorted(set(evidence["42"]["passing_methods"]) & set(evidence["17"]["passing_methods"]))
    payload={"recorded_at":datetime.now().astimezone().isoformat(timespec="seconds"),
             "experiment_id":"D5_CONFIDENCE_ROUTING_SUMMARY","historical_test6_loaded":False,
             "seed_evidence":evidence,"shared_passing_methods":shared,
             "proceed_with_nonlearned_router":bool(shared),
             "next_if_none":"Train a benefit-aware router using expert correctness/disagreement labels and a hard Optical fallback mask."}
    with open(OUT/"method_summary.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]),lineterminator="\n"); w.writeheader(); w.writerows(table)
    (OUT/"decision_evidence.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2,ensure_ascii=False))

if __name__=="__main__": main()
