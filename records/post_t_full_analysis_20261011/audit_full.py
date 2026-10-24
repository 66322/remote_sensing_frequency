import argparse,base64,gzip,hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
B=Path(__file__).parent


def need(x,msg):
    if not x:raise AssertionError(msg)

def digest(b):return hashlib.sha256(b).hexdigest()

def close(a,b,msg):
    if isinstance(a,dict):
        need(set(a)==set(b),msg+' keys')
        for k in a:close(a[k],b[k],msg+'/'+k)
    elif isinstance(a,list):
        need(len(a)==len(b),msg+' length')
        for x,y in zip(a,b):close(x,y,msg)
    elif isinstance(a,(float,int)) and not isinstance(a,bool):need(b is not None and abs(a-b)<1e-9,msg)
    else:need(a==b,msg)

class Audit:

    def __init__(self, b):
        self.b = b
        self.count = dict(read_payloads=0, matrices=0, joints=0, embedded_case_bindings=0, prediction_bindings=0)
        self.man = json.loads((b / 'upload_manifest.json').read_text())
        self.files = {x['path']: x for x in self.man['files']}
        self.sources = {x['path']: x for x in self.man['source_files']}
        self.raw = {}
        self.names = []
        tree = json.loads((b / 'git_tree.json').read_text())
        blobs = {x['path']: x for x in tree['tree'] if x['type'] == 'blob'}
        need(not tree['truncated'] and set(blobs) == set(self.files) | {'upload_manifest.json'}, 'manifest tree coverage')
        for n, row in self.files.items():
            need(row['bytes'] == blobs[n]['size'], 'manifest tree size ' + n)
        self.blobs = blobs

    def read(self, n):
        raw = (self.b / n).read_bytes()
        expected = self.files[n]
        if digest(raw) != expected['sha256'] and raw.endswith(b'\n'):
            raw = raw[:-1]
        need(len(raw) == expected['bytes'] and digest(raw) == expected['sha256'], 'upload bytes ' + n)
        need(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\x00' + raw).hexdigest() == self.blobs[n]['sha'], 'Git blob ' + n)
        x = json.loads(raw)
        if isinstance(x, dict) and 'payload_base64' in x and (x.get('record_encoding') == 'gzip-base64-exact-v1'):
            raw = gzip.decompress(base64.b64decode(x['payload_base64'], validate=True))
            need(len(raw) == x['original_bytes'] and digest(raw) == x['original_sha256'], 'envelope ' + n)
            x = json.loads(raw)
        if n in self.sources:
            s = self.sources[n]
            need(len(raw) == s['original_bytes'] and digest(raw) == s['original_sha256'], 'original ' + n)
        self.raw[n] = digest(raw)
        self.names.append(n)
        self.count['read_payloads'] += 1
        return x

    def metric(self, row):
        cm = np.asarray(row['cm'])
        need(cm.shape == (6, 6) and cm.dtype.kind in 'iu' and (cm >= 0).all(), 'CM int64')
        cm = cm.astype(np.int64)
        tp = np.diag(cm)
        su = cm.sum(1)
        fp = cm.sum(0) - tp
        fn = su - tp
        den = tp + fp + fn
        io = [float(tp[i] / den[i]) if den[i] else None for i in range(6)]
        m = lambda ids: float(np.mean([io[i] for i in ids if io[i] is not None])) if any((io[i] is not None for i in ids)) else None
        for k, v in dict(support=su.tolist(), TP=tp.tolist(), FP=fp.tolist(), FN=fn.tolist(), IoU=io, mIoU_fg5=m(range(5)), mIoU_6=m(range(6)), valid=int(cm.sum())).items():
            close(v, row[k], 'metric ' + k)
        self.count['matrices'] += 1
        return cm

    def joint(self, j, metrics, region):
        need(j['shape'] == [6] * 4 and j['dtype'] == 'int64', 'joint schema')
        flat = np.zeros(6 ** 4, np.int64)
        seen = set()
        for i, n in j['nonzero']:
            need(isinstance(i, int) and isinstance(n, int) and (0 <= i < 6 ** 4) and (n > 0) and (i not in seen), 'joint sparse')
            seen.add(i)
            flat[i] = n
        v = flat.reshape((6,) * 4)
        for name, axis in [('fixed_rgb', 1), ('fixed_dsm', 2), ('candidate', 3)]:
            axes = tuple((a for a in range(4) if a not in (0, axis)))
            need(np.array_equal(v.sum(axes), np.asarray(metrics[name][region]['cm'], np.int64)), 'joint marginal ' + name)
        self.count['joints'] += 1
        return v

m=SimpleNamespace(Audit=Audit,digest=digest,close=close)

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

a=m.Audit(B/'received');p=a.read('plan.json');q=a.read('queue_status.json');snap=a.read('completed_snapshot.json');screen=a.read('transfer_screen.json');code=a.read('code_manifest.json');masks=a.read('mask_manifest.json');prep=a.read('preparation_complete.json');refs_ix=a.read('reference_index.json')
a.artifacts={x['path']:x for x in a.read('server_artifact_index.json')['artifacts']}
assert q['status']=='TRANSFER_COMPLETE_AWAITING_REVIEW' and q['CPU']=='COMPLETE' and all(v['status']=='COMPLETE' for v in q['jobs'].values())
assert snap['included_jobs']==['T'+str(i) for i in range(10)] and not snap['excluded_jobs'] and snap['scientific_final_gate_available']
assert q['screen_sha256']==a.raw['transfer_screen.json'] and p['execution_commit']==code['commit']=='4bf69489f789e998b7bf3181d3b3057c6ff7c04e'
assert p['physical_gpus']==[0] and p['data']['validation']==['3_11','5_10'] and p['training']['seed']==42 and not p['test_release']
assert prep['plan_sha256']==masks['plan_sha256']==a.raw['plan.json'] and prep['reference_index_sha256']==a.raw['reference_index.json'] and prep['mask_manifest_sha256']==a.raw['mask_manifest.json']
r={'source_commit':'379f301f255b9d2348cf11cad79e1374fedd1e7b','last_observed':q['observed_at'],'captured_at':snap['captured_at'],'status':q['status'],'U':{},'initial':{},'E':{},'ordinary':{},'capacity':{},'exposure':{},'midpoint_bindings':{}}
for tag in ['base_U','R0_U','base_ordinary','E_R0','E_S1-0','P7_U']:
    n='references/'+tag+'.json';r[tag]=check(a,n);assert a.raw[n]==refs_ix[tag]['sha256']
for i in range(10):
    j='T'+str(i);c=a.read(f'jobs/{j}/complete.json');pr=a.read(f'jobs/{j}/protection.json');cap=a.read(f'jobs/{j}/model_capacity.json');sig=c['signature'];card=p['jobs'][i]
    assert sig['job']==card and sig['plan_sha256']==a.raw['plan.json'] and sig['code_manifest_sha256']==a.raw['code_manifest.json'] and sig['mask_manifest_sha256']==a.raw['mask_manifest.json'] and sig['initial_checkpoint_sha256']==p['initial_checkpoint']['sha256']
    assert c['global_step']==c['optimizer_updates']==c['selected']['step']==8000 and sig['physical_gpu']==0 and card['seed']==42
    assert c['selected']['selection']=='prospectively fixed8000' and not c['test6_loaded'] and not c['independent_final_loaded']
    assert a.raw[f'jobs/{j}/complete.json']==snap['completed_bindings'][j]['complete_sha256']
    assert pr['base_parameter_digest_equal'] and pr['native_prediction_outside_support_equal'] and pr['initial_base_sha256']==pr['final_base_sha256']
    assert cap['trainable_parameters']==622150
    for name in ['model_capacity.json','protection.json']:assert a.raw[f'jobs/{j}/'+name]==c['artifacts'][name]
    for key,tag in [('U','support_evaluation'),('initial','initial_evaluation'),('E','stress_evaluation'),('ordinary','evaluation')]:
        n=f'jobs/{j}/{tag}/summary.json';r[key][j]=check(a,n);assert a.raw[n]==c['artifacts'][tag+'/summary.json']
    for name,h in c['artifacts'].items():
        if name.endswith('.pth'):assert a.artifacts[a.man['server_directory']+'/jobs/'+j+'/'+name]['sha256']==h
    v=a.read(f'jobs/{j}/validation/step_4000.json');assert v['binding']['training']==sig and v['binding']['step']==4000
    r['midpoint_bindings'][j]=v['binding'];r['capacity'][j]=cap['trainable_parameters'];r['exposure'][j]=c['treatment_counts']
    print('AUDITED',j,flush=True)
def diff(x,y,k='rgb_U',th=.0,positive=False):
    z={'pooled_gain_pp':x[k]['pooled']-y[k]['pooled'],'tile_gains_pp':{t:x[k]['tiles'][t]-y[k]['tiles'][t] for t in ('3_11','5_10')},'threshold_pp':th}
    z['passed']=z['pooled_gain_pp']>=th and (not positive or all(v>0 for v in z['tile_gains_pp'].values()));return z
g=p['design']['gates'];fixed=r['U']['T7']
con={j:diff(fixed,r['U'][j],th=g['matched_pp'],positive=True) for j in ('T1','T6','T9')};con['base']=diff(fixed,r['base_U'],th=g['base_pp'],positive=True);con['R0']=diff(fixed,r['R0_U'],th=g['route_floor_pp'])
prot={k:diff(r['ordinary']['T7'],r['base_ordinary'],k,g['protect_floor_pp']) for k in ('clean','rgb_missing','dsm_missing')};dsm=diff(fixed,r['base_U'],'dsm_U',g['protect_floor_pp'])
worst=min(({'condition':k,'tile':t,'gain_pp':r['ordinary']['T7'][k]['tiles'][t]-r['base_ordinary'][k]['tiles'][t]} for k in p['evaluation']['primary'] for t in p['data']['validation']),key=lambda x:x['gain_pp'])
shape={k:diff(r['E']['T7'],r['E_S1-0'],k,g['shape_pp'],True) for k in r['E']['T7'] if k.endswith('__clean')}
stress={k:diff(r['E']['T7'],r['E_S1-0'],k,g['protect_floor_pp']) for k in r['E']['T7']};route={k:diff(r['E']['T7'],r['E_R0'],k,g['route_floor_pp']) for k in r['E']['T7']}
sw=min(({'condition':k,'tile':t,'gain_pp':r['E']['T7'][k]['tiles'][t]-r['E_S1-0'][k]['tiles'][t]} for k in r['E']['T7'] for t in p['data']['validation']),key=lambda x:x['gain_pp'])
gate={'T7':dict(contrasts=con,protection=prot,worst_primary_tile=worst,dsm_U=dsm),'E':dict(shape=shape,protection=stress,route=route,worst_tile=sw)}
gate['U_passed']=all(x['passed'] for x in [*con.values(),*prot.values(),dsm]) and worst['gain_pp']>=g['worst_tile_floor_pp'];gate['E_passed']=all(x['passed'] for z in (shape,stress,route) for x in z.values()) and sw['gain_pp']>=g['worst_tile_floor_pp'];gate['T7_passed']=gate['U_passed'] and gate['E_passed']
for k,v in gate.items():m.close(v,screen[k],'screen '+k)
r['gate']=gate;r['paired_context_effects']={f'T{2*i+1}-T{2*i}':diff(r['U'][f'T{2*i+1}'],r['U'][f'T{2*i}']) for i in range(5)}
m.close(r['paired_context_effects'],screen['paired_context_effects'],'pairs')
r['per_arm']={}
for j in r['U']:
    row=dict(donor=p['jobs'][int(j[1:])]['donor'],context=bool(int(j[1:])%2),initial_rgb_U=r['initial'][j]['rgb_U']['pooled'],rgb_U=r['U'][j]['rgb_U']['pooled'],dsm_U=r['U'][j]['dsm_U']['pooled'],new_training_gain_pp=r['U'][j]['rgb_U']['pooled']-r['initial'][j]['rgb_U']['pooled'],S_available=sum(r['ordinary'][j][k]['pooled'] for k in p['evaluation']['primary'])/len(p['evaluation']['primary']))
    m.close(row,screen['per_arm'][j],'per arm '+j);r['per_arm'][j]=row
    assert all(abs(r['ordinary'][j][k]['pooled']-r['base_ordinary'][k]['pooled'])<1e-9 for k in [*p['evaluation']['primary'],'rgb_missing','dsm_missing'])
    row['ordinary_deltas_pp']={k:r['ordinary'][j][k]['pooled']-r['base_ordinary'][k]['pooled'] for k in r['ordinary'][j]}
r['audit']={'counts':a.count,'manifest_payloads':len(a.files),'read_names':sorted(set(a.names)),'original_sha256':a.raw,'tree_sha':'6eaf2b957caa5014fb6553743b5cb72ee626ae2b'}
r['limitations']=['Offline count/binding audit only; no GPU rerun or server array/checkpoint-body rehash.','Receipt inventory checked but not every payload independently downloaded; reused payloads verified against new receipt SHA.','Val2 seed42 repeated development only; no independent final generalization or bilateral evidence.']
(B/'audit.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'last_observed':r['last_observed'],'counts':a.count,'per_arm':r['per_arm'],'gate':gate,'pairs':r['paired_context_effects']},ensure_ascii=False))

