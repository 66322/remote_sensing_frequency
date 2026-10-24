import ast,hashlib,json,itertools,sys
from pathlib import Path
import numpy as np
B=Path(__file__).parent; D=B/'decoded'; H=lambda b:hashlib.sha256(b).hexdigest()
def need(x, msg):
    if not x:
        raise AssertionError(msg)

def close(a, b, msg):
    if isinstance(a, dict):
        need(set(a) == set(b), msg + ' keys')
        for k in a:
            close(a[k], b[k], msg + '/' + k)
    elif isinstance(a, list):
        need(len(a) == len(b), msg + ' length')
        for x, y in zip(a, b):
            close(x, y, msg)
    elif isinstance(a, (float, int)) and (not isinstance(a, bool)):
        need(b is not None and abs(a - b) < 1e-09, msg)
    else:
        need(a == b, msg)

class Audit:

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
man=json.loads((B/'received/upload_manifest.json').read_bytes())
class Current(Audit):
    def __init__(self):
        self.sources={r['path']:r for r in man['source_files']};self.man=man;self.raw={};self.names=[]
        self.count=dict(matrices=0,joints=0,embedded_case_bindings=0,prediction_bindings=0,read_payloads=0,transition_checks=0)
        self.artifacts={r['path']:r for r in self.read('server_artifact_index.json')['artifacts']}
    def read(self,n):
        raw=(D/n).read_bytes();self.raw[n]=H(raw);self.names.append(n);self.count['read_payloads']+=1
        return json.loads(raw)
a=Current()
m=type('Support',(),dict(digest=staticmethod(H)))()
def check(a, n):
    s = a.read(n)
    p = a.read('plan.json')
    assert not s['test6_loaded'] and (not s['independent_final_loaded'])
    out = {}
    for cond, rows in s['tiles'].items():
        assert set(rows) == set(p['data']['validation'])
        for t, row in rows.items():
            path = n.rsplit('/', 1)[0] + '/' + cond + '/' + t + '.json'
            if path in a.sources:
                raw = (json.dumps(row, indent=2, allow_nan=False) + '\n').encode()
                assert m.digest(raw) == a.sources[path]['original_sha256']
                a.count['embedded_case_bindings'] += 1
                if n.startswith(('jobs/P', 'jobs/T')) and 'binding' in s:
                    assert row['binding'] == s['binding']
                if n.startswith('jobs/'):
                    for name, sha in row['predictions'].items():
                        pp = a.man['server_directory'] + '/' + n.rsplit('/', 1)[0] + '/' + cond + '/' + name + '/' + t + '.npy'
                        assert a.artifacts[pp]['sha256'] == sha
                        a.count['prediction_bindings'] += 1
            for scope in ('full', 'noboundary'):
                z = row['scopes'][scope]
                for name, regs in z['metrics'].items():
                    for reg, v in regs.items():
                        a.metric(v)
                for reg, j in z['joint'].items():
                    a.joint(j, z['metrics'], reg)
        for scope in ('full', 'noboundary'):
            pool = s['pooled'][cond][scope]
            for name, regs in pool['metrics'].items():
                for reg, v in regs.items():
                    cm = a.metric(v)
                    assert (cm == sum((__import__('numpy').asarray(r['scopes'][scope]['metrics'][name][reg]['cm'], dtype='int64') for r in rows.values()))).all()
            for reg, j in pool['joint'].items():
                a.joint(j, pool['metrics'], reg)
        out[cond] = {'pooled': 100 * s['pooled'][cond]['noboundary']['metrics']['candidate']['valid']['mIoU_fg5'], 'tiles': {t: 100 * r['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5'] for t, r in rows.items()}}
    return out
p=a.read('plan.json');q=a.read('queue_status.json');screen=a.read('mechanism_screen.json');code=a.read('code_manifest.json')
assert q['status']=='MECHANISM_COMPLETE_AWAITING_REVIEW' and q['CPU']=='COMPLETE' and len(q['jobs'])==26 and all(x['status']=='COMPLETE' for x in q['jobs'].values())
assert p['total_optimizer_steps']==screen['optimizer_updates']==0 and p['physical_gpus']==[0] and not p['test_release']
assert p['execution_commit']==code['commit']=='cd958925cb5d4292dd15802830e97493c9c67033'
assert p['data']['validation']==['3_11','5_10'] and p['training']['seed']==42
assert screen['plan_sha256']==a.raw['plan.json'] and screen['code_manifest_sha256']==a.raw['code_manifest.json']
verified_code=[];unreceived_manifest_entries=[]
for n,h in code['files'].items():
    f=D/'code'/n
    if f.is_file():assert H(f.read_bytes())==h,n;verified_code.append(n)
    else:unreceived_manifest_entries.append(n)
prep=a.read('preparation_complete.json');masks=a.read('mask_manifest.json');ix=a.read('reference_index.json')
assert prep['plan_sha256']==masks['plan_sha256']==a.raw['plan.json']
assert prep['mask_manifest_sha256']==a.raw['mask_manifest.json'] and prep['reference_index_sha256']==a.raw['reference_index.json']
refs={}
for name,row in ix.items():
    refs[name]=check(a,'references/'+name+'.json');assert a.raw['references/'+name+'.json']==row['sha256']

prior=json.loads((B/'prior_full_t_audit.json').read_text(encoding='utf-8'))
scores={};bindings={};transitions={}
for card in p['jobs']:
    j=card['id'];pre='jobs/'+j+'/'
    c=a.read(pre+'complete.json');bind=a.read(pre+'checkpoint_binding.json')
    assert c['job']==card and c['execution_commit']==p['execution_commit'] and c['optimizer_updates']==0 and not c['test6_loaded'] and not c['independent_final_loaded']
    assert c['plan_sha256']==bind['plan_sha256']==a.raw['plan.json'] and c['code_manifest_sha256']==bind['code_manifest_sha256']==a.raw['code_manifest.json']
    assert bind['job']==card and bind['optimizer_updates']==0
    for n,h in c['artifacts'].items():assert H((D/pre/n).read_bytes())==h,(j,n)
    if card['kind']=='module':assert bind['checkpoint']['sources']=={k:p['donors'][k] for k in ('S1-0','S1-3')}
    else:
        v=prior['midpoint_bindings'][card['source_job']];b=bind['checkpoint']
        assert b['training']==v['training'] and b['step']==v['step']==4000 and b['checkpoint_sha256']==v['checkpoint_sha256']
    s=a.read(pre+'summary.json');assert s['binding']==bind
    assert set(s['tiles'])==set(card['keys'])
    scores[j]=check(a,pre+'summary.json');close(scores[j],screen['scores'][j],'screen scores '+j)
    assert screen['source_summaries'][j]['sha256']==a.raw[pre+'summary.json']
    transitions[j]={}
    for key,rows in s['tiles'].items():
        transitions[j][key]={}
        for tile,row in rows.items():
            assert row['binding']==bind and row['confusion_matrix_dtype']=='int64'
            for ref,tag in [('fixed_reference','base_U' if key in ('rgb_U','dsm_U') else 'E_S1-0'),('R0_reference','R0_U' if key in ('rgb_U','dsm_U') else 'E_R0')]:
                rr=row[ref];source=a.read('references/'+tag+'.json')['tiles'][key][tile]
                assert rr['summary_sha256']==ix[tag]['sha256'] and rr['prediction_sha256']==source['predictions']
            for ref in ('transition_vs_base','transition_vs_R0'):
                for scope,z in row[ref].items():
                    cc=a.metric(z['control']);ca=a.metric(z['candidate'])
                    assert z['valid']==int(cc.sum())==int(ca.sum())
                    assert sum(z[k] for k in ('rescued','harmed','both_correct','both_wrong'))==z['valid']
                    assert int(np.trace(ca)-np.trace(cc))==z['rescued']-z['harmed']
                    assert sum(v['valid'] for v in z['by_class'].values())==z['valid']
                    for k in ('rescued','harmed'):assert sum(v[k] for v in z['by_class'].values())==z[k]
                    a.count['transition_checks']+=1
            transitions[j][key][tile]={ref:{k:z[k] for k in ('valid','rescued','harmed')} for ref,z in [(ref,row[ref]['noboundary']) for ref in ('transition_vs_base','transition_vs_R0')]}
    bindings[j]=bind
    print('AUDITED',j,flush=True)

def diff(x,y):return {k:dict(pooled_gain_pp=x[k]['pooled']-y[k]['pooled'],tile_gains_pp={t:x[k]['tiles'][t]-y[k]['tiles'][t] for t in p['data']['validation']}) for k in x if k in y}
fixed={name:diff(scores[name.split('-')[0]],scores[name.split('-')[1]]) for name in screen['fixed_contrasts']}
close(fixed,screen['fixed_contrasts'],'fixed contrasts')
pairs={}
for factor in ('rgb','dsm','head','context'):
    pairs[factor]={}
    for lo in p['jobs']:
        if lo['kind']!='module' or lo[factor]!=(False if factor=='context' else 0):continue
        hi=next(x for x in p['jobs'] if x['kind']=='module' and x[factor]==(True if factor=='context' else 3) and all(x[k]==lo[k] for k in ('rgb','dsm','head','context') if k!=factor))
        pairs[factor][hi['id']+'-'+lo['id']]=diff(scores[hi['id']],scores[lo['id']])
close(pairs,screen['module_factor_pairs'],'all factor pairs')
curves={}
for j in prior['U']:
    z=prior['initial'][j];mid=scores['L_'+j];last=prior['U'][j]
    for step,val in [(0,z),(4000,mid),(8000,last)]:close(val,screen['learning_curves'][j]['step'+str(step)],'curve '+j)
    curve=dict(step0=z,step4000=mid,step8000=last,delta_0_4000=diff(mid,z),delta_4000_8000=diff(last,mid))
    for k in ('delta_0_4000','delta_4000_8000'):close(curve[k],screen['learning_curves'][j][k],'curve delta '+j)
    curves[j]=curve
sig=lambda r:r['pooled_gain_pp']>=.3 and all(x>0 for x in r['tile_gains_pp'].values())
assert screen['recommendations']['matched_budget_study_supported']==all(sig(curves[j]['delta_4000_8000']['rgb_U']) for j in ('T1','T7'))
assert screen['recommendations']['representation_followup_signal']==sig(fixed['M333_context-M003_context']['rgb_U'])
assert not screen['recommendations']['next_training_launched'] and not screen['predecessor_T7_gate']
ep=a.read('jobs/M333_context/endpoint_checks.json');assert len(ep)==16 and all(x['exact'] for x in ep);close(ep,screen['endpoint_checks'],'endpoint screen')
s=a.read('jobs/M333_context/summary.json')
for key,rows in s['tiles'].items():
    tag='R0_U' if key in ('rgb_U','dsm_U') else 'E_R0';ref=a.read('references/'+tag+'.json')
    for tile,row in rows.items():
        assert row['predictions']['candidate']==ref['tiles'][key][tile]['predictions']['candidate']
        for scope in ('full','noboundary'):assert row['transition_vs_R0'][scope]['rescued']==row['transition_vs_R0'][scope]['harmed']==0
    close(scores['M333_context'][key],refs[tag][key],'R0 exact metrics')
assert all(scores[j]['dsm_U']==refs['base_U']['dsm_U'] for j in scores)
r=dict(source_commit='57ef5ad9e5238f69f94c5d8ede00023a20499144',verification='ANALYZED',receipt=json.loads((B/'receipt_audit.json').read_text()),counts=a.count,code_files_verified=len(verified_code),unreceived_code_manifest_entries=unreceived_manifest_entries,scores=scores,fixed_contrasts=fixed,module_factor_pairs=pairs,learning_curves=curves,endpoint_cases_verified=16,transitions=transitions,bindings=bindings,recommendations=screen['recommendations'],prior_T_original_count_audit_reused=True,limitations=['No GPU rerun or independent server array/checkpoint body rehash.','0/8000 counts and 4000 validation bindings reused from prior verified full-T audit; new 4000/U counts independently recalculated.','Known masks, Val2 seed42 repeatedly used development; no bilateral or independent generalization claim.'])
(B/'audit.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'counts':a.count,'fixed_rgb':{k:v['rgb_U'] for k,v in fixed.items()},'recommendations':r['recommendations']},ensure_ascii=False),flush=True)
