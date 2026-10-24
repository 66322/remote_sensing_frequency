import base64,gzip,hashlib,json,math
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent
M=json.loads((ROOT/'upload_manifest.json').read_bytes())
source={r['path']:r for r in M['source_files']}
rows={};issues=[];stats={'payloads':0,'decoded_JSON':0,'matrices':0,'transition_cells':0,'bootstrap_summaries':0}
def digest(b):return hashlib.sha256(b).hexdigest()
def fail(s):issues.append(s)
for r in M['files']:
    p=ROOT/('summary.encoded.json' if r['path']=='summary.json' else 'encoded/'+r['path'])
    b=p.read_bytes();stats['payloads']+=1
    if len(b)!=r['bytes'] or digest(b)!=r['sha256']:fail('payload '+r['path'])
    raw=b
    if p.suffix in ('.json','.jsonl'):
        try:obj=json.loads(b)
        except json.JSONDecodeError:obj=None
        if isinstance(obj,dict) and obj.get('record_encoding')=='gzip-base64-exact-v1':
            raw=gzip.decompress(base64.b64decode(obj['payload_base64']))
            if len(raw)!=obj['original_bytes'] or digest(raw)!=obj['original_sha256']:fail('wrapper '+r['path'])
        if p.suffix=='.json':rows[r['path']]=json.loads(raw);stats['decoded_JSON']+=1
    if r['path'] in source:
        s=source[r['path']]
        if len(raw)!=s['original_bytes'] or digest(raw)!=s['original_sha256']:fail('original '+r['path'])
    target=ROOT/'decoded'/r['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
S=rows['summary.json'];B=S['binding']
for n,h in B.items():
    if digest((ROOT/'decoded'/n).read_bytes())!=h:fail('binding '+n)
plan=rows['plan.json'];cases={}
for job in plan['jobs']:
    complete=rows['jobs/'+job['id']+'/complete.json']
    if complete['binding']!=B or complete['optimizer_updates']!=0:fail('job binding '+job['id'])
    for c in job['cases']:
        name='{model}_{tile}_{dsm}_{realization:02d}_{family}_{ratio}'.format(**c)
        p='cases/'+name+'.json';row=rows[p];cases[name]=row
        if row['case']!=c or row['binding']!=B or row['optimizer_updates']!=0:fail('case '+name)
        if digest((ROOT/'decoded'/p).read_bytes())!=complete['records'][name]:fail('job record '+name)
for phase,count in [('D',160),('E',120)]:
    c=rows['analysis/'+phase+'/complete.json']
    if c['binding']!=B or len(c['records'])!=count:fail('analysis completion '+phase)
    for name,h in c['records'].items():
        p='analysis/'+phase+'/'+name+'.json'
        if digest((ROOT/'decoded'/p).read_bytes())!=h or rows[p]['binding']!=B:fail('CPU record '+name)
for prefix in ('','cpu_acceleration_20261013T110244_1189050/'):
    c=rows[prefix+'code_manifest.json']
    for name,h in c['files'].items():
        if digest((ROOT/'decoded'/prefix/'code'/name).read_bytes())!=h:fail('code '+prefix+name)
for gpu in (0,1):
    c=rows[f'smoke/gpu{gpu}/complete.json']
    if not c['all_passed'] or c['binding']!=B or c['optimizer_updates']!=0:fail('smoke '+str(gpu))

def matrix(v):
    a=np.asarray(v)
    if a.shape!=(6,6) or a.dtype.kind not in 'iu' or (a<0).any():raise ValueError('invalid int matrix')
    stats['matrices']+=1;return a.astype(np.int64)
def walk(v,where):
    if isinstance(v,dict):
        if 'clean_cm' in v and 'missing_cm' in v:
            a,b=matrix(v['clean_cm']),matrix(v['missing_cm'])
            if not np.array_equal(a.sum(1),b.sum(1)):fail('class support '+where)
            t=v.get('transitions')
            if t:
                stats['transition_cells']+=1
                if (int(a.sum())!=t['valid'] or int(np.trace(a))!=t['reference_correct'] or
                    int(a.sum()-np.trace(a))!=t['reference_wrong'] or
                    int(np.trace(a)-np.trace(b))!=t['harmed']-t['rescued'] or
                    not 0<=t['harmed']+t['rescued']<=t['flips']<=t['valid']):fail('transition '+where)
                for g in range(6):
                    z=t['by_class'][str(g)]
                    if int(a[g].sum())!=z['valid'] or int(a[g,g])!=z['reference_correct'] or int(a[g,g]-b[g,g])!=z['harmed']-z['rescued']:fail('class transition '+where)
        for k,x in v.items():walk(x,where+'/'+k)
    elif isinstance(v,list):
        for i,x in enumerate(v):
            if isinstance(x,(dict,list)):walk(x,where+'/'+str(i))
for n,row in cases.items():walk(row,n)
for p,row in rows.items():
    if p.startswith('analysis/D/') and p.endswith('.json') and 'result' in row:walk(row['result'],p)

def score(cm,classes=range(5)):
    a=np.asarray(cm,np.int64);u=a.sum(0)+a.sum(1)-a.diagonal()
    idx=list(classes)
    return 100*float((a.diagonal()[idx]/u[idx]).mean()) if all(u[idx]>0) else None
def cid(m,t,ds='intact',i=0,f='clean',r=25):return f'{m}_{t}_{ds}_{i:02d}_{f}_{r}'
def damage(m,ds,i,f,r=25,region='missing',tiles=('3_11','5_10'),classes=range(5),clean_field='clean_cm'):
    cells=[cases[cid(m,t,ds,i,f,r)]['scopes']['noboundary'][region] for t in tiles]
    a=sum((np.asarray(x[clean_field],np.int64) for x in cells));b=sum((np.asarray(x['missing_cm'],np.int64) for x in cells))
    x,y=score(a,classes),score(b,classes)
    return None if x is None or y is None else x-y
def close(a,b,where):
    if a is None or b is None:
        if a!=b:fail('null '+where)
    elif not math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-9):fail('numeric '+where)
def sequence(expected,actual,where):
    if len(expected)!=len(actual):fail('length '+where);return
    for a,b in zip(expected,actual):close(a,b,where)
for m in ('S1','R16'):
    for ds in ('intact','crop_shuffle','tile_shuffle','zero'):
        for name,tiles in [('pooled',('3_11','5_10')),('3_11',('3_11',)),('5_10',('5_10',))]:
            d={f:[damage(m,ds,i,f,tiles=tiles) for i in range(1,21)] for f in ('pixel','random','gradient','matched')}
            for f,v in d.items():sequence(v,S['A'][m][ds][name]['damage'][f]['per_realization'],'A/'+m+'/'+ds+'/'+f)
            for key,other in [('PE','matched'),('PE_total','random')]:
                sequence([a-b for a,b in zip(d['gradient'],d[other])],S['A'][m][ds][name][key]['per_realization'],'A/'+key)
        for f in ('pixel','random','gradient','matched'):
            row=S['C'][m][ds][f]
            for k in range(5):sequence([damage(m,ds,i,f,classes=(k,)) for i in range(1,21)],row['damage_by_class'][str(k)]['per_realization'],'C')
for ratio in (5,10,25):
    for region in ('all','missing','core5'):
        sequence([damage('S1','intact',i,'pixel',r=ratio,region=region) for i in range(1,21)],S['B'][str(ratio)][region]['damage']['per_realization'],'B')
for f in ('pixel','random','gradient','matched'):
    for support,tiles in [('pooled',('3_11','5_10')),('3_11',('3_11',)),('5_10',('5_10',))]:
        for region in ('valid','mask','healthy'):
            dest=S['D'][f][support][region]
            for system,reported in dest['scores'].items():
                values=[]
                for i in range(1,21):
                    cells=[rows[f'analysis/D/{t}_{i:02d}_{f}.json']['result']['systems'][system][region] for t in tiles]
                    values.append(score(sum((np.asarray(x['missing_cm'],np.int64) for x in cells))))
                sequence(values,reported['per_realization'],'D score '+system)

def bootstrap_walk(v):
    if isinstance(v,dict):
        if 'per_realization' in v and 'CI95' in v and 'mean' in v:
            vals=v['per_realization']
            if len(vals)==20 and all(x is not None and np.isfinite(x) for x in vals):
                a=np.array(vals,float);rng=np.random.Generator(np.random.PCG64(61011));means=a[rng.integers(0,20,size=(5000,20))].mean(1)
                close(float(a.mean()),v['mean'],'bootstrap mean');sequence(np.quantile(means,[.025,.975]).tolist(),v['CI95'],'bootstrap CI');stats['bootstrap_summaries']+=1
        for x in v.values():bootstrap_walk(x)
    elif isinstance(v,list):
        for x in v:
            if isinstance(x,(list,dict)):bootstrap_walk(x)
bootstrap_walk(S)
out=dict(status='PASS' if not issues else 'FAIL',issues=issues,statistics=stats,cases=len(cases),GPU_jobs=len(plan['jobs']),
    sources_uploaded=len(M['files']),scientific_support='Potsdam fit12/Val2 3_11,5_10 native512/stride256 NB fg5; frozen seed42;20mask IDs',
    limitations=['server array/weight bodies not downloaded or independently rehashed','no GPU rerun','two repeatedly used Val2 tiles are not independent test/generalization','secondary signflip not independently recomputed'])
(ROOT/'audit_result.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
