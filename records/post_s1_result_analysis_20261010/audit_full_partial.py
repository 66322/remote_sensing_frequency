import json,hashlib,shutil,sys,importlib.util
from pathlib import Path
B=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("prev",B/"audit_base.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
old=m.Audit(B/"old");new=m.Audit(B/"new")
prev=B.parent/"post-s1-partial-analysis-20261009/received"
for a in [old,new]:
    a.artifacts={x['path']:x for x in a.read('server_artifact_index.json')['artifacts']}
for n,e in old.files.items():
    src=prev/n
    if src.is_file() and m.digest(src.read_bytes())==e["sha256"]:
        dst=B/"old"/n
        if not dst.exists(): dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
def check(a,n):
    s=a.read(n);p=a.read("plan.json")
    assert not s["test6_loaded"] and not s["independent_final_loaded"]
    out={}
    for cond,rows in s["tiles"].items():
        assert set(rows)==set(p["data"]["validation"])
        for t,row in rows.items():
            path=n.rsplit("/",1)[0]+"/"+cond+"/"+t+".json"
            if path in a.sources:
                raw=(json.dumps(row,indent=2,allow_nan=False)+"\n").encode()
                assert m.digest(raw)==a.sources[path]["original_sha256"]
                a.count["embedded_case_bindings"]+=1
                if n.startswith(('jobs/P','jobs/T')) and 'binding' in s:assert row['binding']==s['binding']
                if n.startswith('jobs/'):
                    for name,sha in row['predictions'].items():
                        pp=a.man['server_directory']+'/'+n.rsplit('/',1)[0]+'/'+cond+'/'+name+'/'+t+'.npy'
                        assert a.artifacts[pp]['sha256']==sha
                        a.count['prediction_bindings']+=1
            for scope in ("full","noboundary"):
                z=row["scopes"][scope]
                for name,regs in z["metrics"].items():
                    for reg,v in regs.items():a.metric(v)
                for reg,j in z["joint"].items():a.joint(j,z["metrics"],reg)
        for scope in ("full","noboundary"):
            pool=s["pooled"][cond][scope]
            for name,regs in pool["metrics"].items():
                for reg,v in regs.items():
                    cm=a.metric(v)
                    assert (cm==sum(__import__("numpy").asarray(r["scopes"][scope]["metrics"][name][reg]["cm"],dtype="int64") for r in rows.values())).all()
            for reg,j in pool["joint"].items():a.joint(j,pool["metrics"],reg)
        out[cond]={"pooled":100*s["pooled"][cond]["noboundary"]["metrics"]["candidate"]["valid"]["mIoU_fg5"],"tiles":{t:100*r["scopes"]["noboundary"]["metrics"]["candidate"]["valid"]["mIoU_fg5"] for t,r in rows.items()}}
    return out
result={"old":{},"new":{},"limits":["No remote server access; no GPU rerun.","Raw payload audit covers fetched summaries only; large ordinary summaries except T0 reuse or server-screen only.","Prediction/checkpoint files remain on server; SHA indices do not independently rehash server files."]}
screen=old.read("support_screen.json")
result["old"]["screen"]=screen
result["old"]["U"]={j:check(old,f"jobs/{j}/support_evaluation/summary.json") for j in ["P"+str(i) for i in range(10)]}
result["old"]["E"]={j:check(old,f"jobs/E/{j}/evaluation/summary.json") for j in ["P7","R0","S1-0"]}
result["new"]["base_U"]=check(new,"references/base_U.json")
result["new"]["R0_U"]=check(new,"references/R0_U.json")
result["new"]["U"]={};result["new"]["initial"]={};result["new"]["E"]={}
for j in ["T"+str(i) for i in range(5)]:
    c=new.read(f"jobs/{j}/complete.json");pr=new.read(f"jobs/{j}/protection.json")
    assert c["global_step"]==c["optimizer_updates"]==c["selected"]["step"]==8000
    assert c["signature"]["physical_gpu"]==0 and c["signature"]["job"]["seed"]==42
    assert pr["base_parameter_digest_equal"] and pr["native_prediction_outside_support_equal"]
    for key,folder in [("U","support_evaluation"),("initial","initial_evaluation"),("E","stress_evaluation")]:
        n=f"jobs/{j}/{folder}/summary.json"
        result["new"][key][j]=check(new,n)
        assert new.raw[n]==c["artifacts"][folder+"/summary.json"]
result["new"]["ordinary"]={j:check(new,f"jobs/{j}/evaluation/summary.json") for j in ["T"+str(i) for i in range(5)]}
result["new"]["capacity"]={j:new.read(f"jobs/{j}/model_capacity.json") for j in ["T"+str(i) for i in range(5)]}
assert all(x["trainable_parameters"]==622150 for x in result["new"]["capacity"].values())
result["old"]["ordinary"]={j:check(old,f"jobs/{j}/evaluation/summary.json") for j in ["P"+str(i) for i in range(10)]}
result['base_ordinary']=check(new,'references/base_ordinary.json')
result['R0_ordinary']=check(old,'R0_ordinary/summary.json')
def available(x,p):return sum(x[k]['pooled'] for k in p['evaluation']['primary'])/len(p['evaluation']['primary'])
result['S_available']={kind:{j:available(x,a.read('plan.json')) for j,x in result[kind]['ordinary'].items()} for kind,a in [('old',old),('new',new)]}
for j,v in result['S_available']['old'].items():assert abs(v-screen['per_arm'][j]['S_available'])<1e-9
result['base_S_available']=available(result['base_ordinary'],old.read('plan.json'))
result['new_protection_comparisons']={j:{k:x[k]['pooled']-result['base_ordinary'][k]['pooled'] for k in ['clean','rgb_missing','dsm_missing']} for j,x in result['new']['ordinary'].items()}
result['new_worst_primary_tile']={j:min(x[k]['tiles'][t]-result['base_ordinary'][k]['tiles'][t] for k in new.read('plan.json')['evaluation']['primary'] for t in ['3_11','5_10']) for j,x in result['new']['ordinary'].items()}
result['limits']=['No remote server access or GPU rerun.','All ten P and five completed T ordinary/U summaries checked; E raw scope covers old P7/R0/S1-0 and all five T; other E arms use server screen.','Prediction/checkpoint files remain on server; SHA indices do not independently rehash server files.','D0/D1 retain prior partial audit; not rerun in this receipt.']
result["audit"]={"old":old.count,"new":new.count,"original_sha256":{"old":old.raw,"new":new.raw}}
(B/"audit.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print("COUNTS",result["audit"]["old"],result["audit"]["new"])
for j in result["new"]["U"]:
    u=result["new"]["U"][j]["rgb_U"];ini=result["new"]["initial"][j]["rgb_U"]
    print(j,"initial",ini,"final",u,"train_gain",u["pooled"]-ini["pooled"],"R0",u["pooled"]-result["new"]["R0_U"]["rgb_U"]["pooled"])
for l,r in [("T1","T0"),("T3","T2")]:
    print("PAIR",l,r,result["new"]["U"][l]["rgb_U"]["pooled"]-result["new"]["U"][r]["rgb_U"]["pooled"])
for j,e in result["new"]["E"].items():print("STRESS",j,{k:round(v["pooled"],4) for k,v in e.items()})
