import json,gzip,base64,hashlib
from pathlib import Path
import argparse
ap=argparse.ArgumentParser()
ap.add_argument('--directory',type=Path,required=True)
P=ap.parse_args().directory
M=json.loads((P/'decoded/upload_manifest.json').read_bytes())
files={r['path']:r for r in M['files']}
sources={r['path']:r for r in M['source_files']}
def sha(b):return hashlib.sha256(b).hexdigest()
def read(name):
    raw=(P/'encoded'/name).read_bytes()
    assert sha(raw)==files[name]['sha256'],('upload sha',name)
    v=json.loads(raw)
    if 'payload_base64' in v:
        raw=gzip.decompress(base64.b64decode(v['payload_base64'],validate=True))
        assert len(raw)==v['original_bytes'] and sha(raw)==v['original_sha256']
    assert sha(raw)==sources[name]['original_sha256'],('source sha',name)
    return json.loads(raw),sha(raw)
plan,psha=read('plan.json')
screen,_=read('portfolio_screen.json')
queue,_=read('queue_status.json')
repair,_=read('evaluation_repair_20261004T085441046626_2720259/repair_manifest.json')
def cmmetric(cm):
    assert len(cm)==6 and all(len(r)==6 for r in cm)
    assert all(type(v)==int and v>=0 for r in cm for v in r)
    iou=[]
    for c in range(6):
        den=sum(cm[c])+sum(r[c] for r in cm)-cm[c][c]
        iou.append(cm[c][c]/den if den else None)
    vals=[x for x in iou[:5] if x is not None]
    return sum(vals)/len(vals) if vals else None
def sumcm(cms):return [[sum(m[y][x] for m in cms) for x in range(6)] for y in range(6)]
def joint(row):
    assert row['shape']==[6,6,6,6] and row['dtype']=='int64'
    out={}
    for i,n in row['nonzero']:
        assert type(i)==type(n)==int and 0<=i<1296 and n>0 and i not in out
        out[i]=n
    return out
def jointcm(d):
    out=[[0]*6 for _ in range(6)]
    for i,n in d.items():out[i//216][i%6]+=n
    return out
def rates(s,cs):
    total={}
    for c in cs:
        for tile,row in s['tiles'][c].items():
            for i,n in joint(row['scopes']['noboundary']['joint']['both']).items():total[i]=total.get(i,0)+n
    rden=dden=rharm=dharm=ronly=donly=rkeep=dkeep=0
    for i,n in total.items():
        g=i//216;r=i//36%6;d=i//6%6;f=i%6
        if r==g:rden+=n;rharm+=n*(f!=g)
        if d==g:dden+=n;dharm+=n*(f!=g)
        if r==g and d!=g:ronly+=n;rkeep+=n*(f==g)
        if d==g and r!=g:donly+=n;dkeep+=n*(f==g)
    return dict(keep_rgb=rkeep/ronly,keep_dsm=dkeep/donly,harm_rgb=rharm/rden,harm_dsm=dharm/dden)
audit={'jobs':{},'manifest_files':len(M['files'])+1,'source_bytes':M['source_total_bytes'],'upload_bytes':M['upload_total_bytes'],'repair':repair,'queue_observed_at':queue['observed_at'],'queue':queue['status'],'screen_observed_at':screen['observed_at'],'screens':screen['screens'],'verified_cm_pairs':0,'verified_joint_pairs':0}
for j in ['A0','A1','A2','A3','B1','B3','B4']:
    comp,_=read('jobs/'+j+'/complete.json')
    assert comp['global_step']==8000 and comp['signature']['execution_commit']==plan['execution_commit'] and comp['signature']['plan_sha256']==psha
    audit['jobs'][j]={}
    for age,folder in [('selected','evaluation'),('fixed8000','fixed8000')]:
        s,digest=read('jobs/'+j+'/'+folder+'/summary.json')
        assert digest==comp[folder+'_summary_sha256']
        assert s['binding']['training']==comp['signature'] and not s['test6_loaded'] and not s['independent_final_loaded']
        for c,pooled in s['pooled'].items():
            for scope,pool in pooled.items():
                rows=[r['scopes'][scope] for r in s['tiles'][c].values()]
                for model,regions in pool['metrics'].items():
                    for reg,m in regions.items():
                        assert sumcm([r['metrics'][model][reg]['cm'] for r in rows])==m['cm']
                        got=cmmetric(m['cm']);expected=m['mIoU_fg5']
                        assert got==expected or (got is not None and expected is not None and abs(got-expected)<1e-12)
                        audit['verified_cm_pairs']+=1
                for reg,q in pool['joint'].items():
                    counts={}
                    for r in rows:
                        for i,n in joint(r['joint'][reg]).items():counts[i]=counts.get(i,0)+n
                    assert counts==joint(q)
                    assert jointcm(counts)==pool['metrics']['candidate'][reg]['cm']
                    audit['verified_joint_pairs']+=1
        val=lambda c:100*cmmetric(s['pooled'][c]['noboundary']['metrics']['candidate']['valid']['cm'])
        scores={k:sum(val(c) for c in cs)/len(cs) for k,cs in plan['evaluation']['families'].items()}
        scores['S_available']=sum(scores.values())/4
        geo=sum(val(c) for c in plan['design']['geometry_conditions'])/len(plan['design']['geometry_conditions'])
        for k,v in scores.items():assert abs(v-screen['jobs'][j][age]['scores_pp'][k])<1e-10
        assert abs(geo-screen['jobs'][j][age]['geometry_mean_pp'])<1e-10
        audit['jobs'][j][age]=dict(scores=scores,geometry=geo,rates=rates(s,plan['evaluation']['primary']),selected_step=comp['selected']['step'])
        del s
(P/'audit_result.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps({k:v for k,v in audit.items() if k not in ('repair','jobs')},ensure_ascii=False))
print('RATES',json.dumps({j:v['selected']['rates'] for j,v in audit['jobs'].items()}))


