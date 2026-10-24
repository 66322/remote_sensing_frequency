"""Validate D7 completion and create a compact, commit-ready evidence directory."""
import csv, hashlib, json, shutil
from pathlib import Path
ROOT=Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
QUEUE=ROOT/"records/rebuild_v1_d7_queue_20260922"; OUT=ROOT/"records/rebuild_v1_d7_compact_20260922"
SOURCES=[
 ROOT/"records/rebuild_v1_d7_data_sampling_20260922/summary.json",
 ROOT/"records/rebuild_v1_d7_data_sampling_20260922/class_statistics.csv",
 ROOT/"records/rebuild_v1_d7_data_sampling_20260922/crop_exposure.csv",
 ROOT/"records/rebuild_v1_d7_data_sampling_20260922/component_area_quantiles.csv",
 ROOT/"records/rebuild_v1_d7_summary_20260922/decision_evidence.json",
 ROOT/"records/rebuild_v1_d7_summary_20260922/diagnostic_effects.csv",
]
for seed in (42,17):
 base=ROOT/f"records/rebuild_v1_d7_semantic_errors_seed{seed}_20260922"
 SOURCES += [base/"summary.json",base/"dataset_region_metrics.csv",base/"per_class_metrics.csv",base/"per_tile_class_metrics.csv",base/"object_size_summary.csv"]
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def main():
 lines=list(csv.reader(QUEUE.joinpath("status.tsv").open(encoding="utf-8"),delimiter="\t"))
 if any(len(x)>2 and x[2]=="FAILED" for x in lines) or not any(len(x)>2 and x[1]=="QUEUE" and x[2]=="FINISHED" and "failures=0" in x[3] for x in lines): raise RuntimeError("D7 queue incomplete")
 for p in SOURCES:
  if not p.is_file():raise FileNotFoundError(p)
  if p.suffix==".json" and json.loads(p.read_text()).get("historical_test6_loaded",json.loads(p.read_text()).get("test6_loaded",False)) is not False:raise RuntimeError(f"TEST6 safety failed: {p}")
 if OUT.exists():raise FileExistsError(OUT)
 OUT.mkdir(); manifest=[]
 for p in SOURCES:
  name=f"{p.parent.name}__{p.name}"; q=OUT/name; shutil.copy2(p,q); manifest.append({"source":str(p),"file":name,"bytes":p.stat().st_size,"sha256":sha(p)})
 (OUT/"source_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
 (OUT/"SHA256SUMS").write_text("\n".join(f"{sha(p)}  {p.name}" for p in sorted(OUT.iterdir()) if p.is_file())+"\n")
 print("D7_ARCHIVE_COMPLETE",OUT)
if __name__=="__main__":main()
