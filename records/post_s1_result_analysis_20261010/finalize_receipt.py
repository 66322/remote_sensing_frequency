import json,importlib.util
from pathlib import Path
B=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location("base",B/"audit_base.py");m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
a=m.Audit(B/"new");x=json.loads((B/"audit.json").read_text(encoding="utf-8"))
p=a.read("plan.json");q=a.read("queue_status.json");snap=a.read("completed_snapshot.json")
assert p["primary_candidate"]=="T7" and p["physical_gpus"]==[0] and p["max_gpu_workers"]==1
assert snap["queue_last_observed"]==q["observed_at"] and snap["included_jobs"]==["T0","T1","T2","T3","T4"]
assert snap["excluded_jobs"]=={"T5":"RUNNING","T6":"PENDING","T7":"PENDING","T8":"PENDING","T9":"PENDING"}
arts={r["path"]:r for r in a.read("server_artifact_index.json")["artifacts"]}
exposure={}
for j in snap["included_jobs"]:
    n=f"jobs/{j}/complete.json";c=a.read(n)
    assert a.raw[n]==snap["completed_bindings"][j]["complete_sha256"]
    assert c["signature"]["plan_sha256"]==a.raw["plan.json"]
    assert c["signature"]["job"]==next(v for v in p["jobs"] if v["id"]==j)
    assert c["signature"]["donor_checkpoint_sha256"]==p["donors"][c["signature"]["job"]["donor"]]["sha256"]
    for name,sha in c["artifacts"].items():
        if name.endswith(".pth"):assert arts[a.man["server_directory"]+"/jobs/"+j+"/"+name]["sha256"]==sha
        nn="jobs/"+j+"/"+name
        if nn in x["audit"]["original_sha256"]["new"]:assert x["audit"]["original_sha256"]["new"][nn]==sha
    exposure[j]=c["treatment_counts"]["branch_nonzero_updates"]
assert len(set(exposure.values()))==1
for j,u in x["old"]["U"].items():
    for cond in ["rgb_U","dsm_U"]:assert abs(u[cond]["pooled"]-x["old"]["screen"]["per_arm"][j][cond])<1e-9
for k,v in x["old"]["screen"]["E"]["P7_vs_R0"].items():
    assert abs(x["old"]["E"]["P7"][k]["pooled"]-x["old"]["E"]["R0"][k]["pooled"]-v["pooled_gain_pp"])<1e-9
x["status"]="PASS_SCOPED_OFFLINE_AUDIT";x["evidence_commit"]="f4815a7aa417b1b8344d33603b5e181e1c1ab078";x["new_membership"]=snap;x["new_effective_branch_updates"]=exposure
(B/"audit.json").write_text(json.dumps(x,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print("BINDINGS_PASS",exposure)
