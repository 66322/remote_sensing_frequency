"""Offline integer/stream/endpoint checks, with explicit incomplete evidence."""
import argparse
from pathlib import Path
import numpy as np
from phase3_m1_common import *

def verify_results(base):
    base=Path(base); p=verify(base); old=Path(p['previous']); errors=[]; matrices=0; joints=0
    rows={}
    for f in sorted((base/'primary').glob('*.json')):
        z=read(f); rows[z['job']]=z
        if z.get('failed'): continue
        for t in VAL:
            for scope in ('full','noboundary'):
                a=np.asarray(z['tiles'][t][scope]); metric(a); matrices+=1
    for section in ('clean','results'):
        for f in sorted((base/section).rglob('*.json')):
            z=read(f)
            if 'counts' not in z: continue
            if z['binding']!=binding(base): raise RuntimeError('count binding differs '+str(f))
            for scope,rois in z['counts'].items():
                for roi,systems in rois.items():
                    ref=None
                    for name,stats in systems.items():
                        j=np.asarray(stats['joint']); a=np.asarray(stats['cm']); r=np.asarray(stats['rgb_cm'])
                        if j.shape!=(6,6,6) or not np.issubdtype(j.dtype,np.integer) or (j<0).any(): raise RuntimeError('invalid joint')
                        if not np.array_equal(j.sum(1),a) or not np.array_equal(j.sum(2),r): raise RuntimeError('joint marginal mismatch')
                        if stats['flow']!=flow(j): raise RuntimeError('rescue/harm differs')
                        if ref is not None and not np.array_equal(ref,r): raise RuntimeError('reference CM mismatch')
                        if z.get('availability')=='dsm_missing' and name!='dsm' and not np.array_equal(a,r): raise RuntimeError('fallback not exact')
                        ref=r; matrices+=2; joints+=1
    initial_checks=[]; stream_checks=[]
    for f in sorted((base/'jobs').glob('*/complete.json')):
        d=read(f); job=d['job']; folder=f.parent
        if not job_binding_ok(base,job,d) or sha(folder/'endpoint.pth')!=d['checkpoint_sha256']: raise RuntimeError('endpoint identity differs')
        if (folder/'failure.json').exists(): errors.append(job+': post-training task failed')
        stream=folder/'batch_hashes.jsonl'
        first=read(folder/'parameters.json')
        counterpart=old/'jobs/A_DSM/batch_hashes.jsonl' if first['seed']==42 else base/'jobs/M11_17/batch_hashes.jsonl'
        own=[json.loads(x) for x in stream.read_text().splitlines()]
        if len(own)!=16000 or [x['step'] for x in own]!=list(range(1,16001)): raise RuntimeError('stream step count differs')
        exact=counterpart.exists() and stream.read_bytes()==counterpart.read_bytes()
        # JSON separators need not match; compare the actual step and batch hash values.
        if counterpart.exists(): exact=own==[json.loads(x) for x in counterpart.read_text().splitlines()]
        stream_checks.append(dict(job=job,reference=str(counterpart),exact=exact))
        if not exact: errors.append(job+': paired batch stream differs or missing')
        if first['seed']==42:
            check=read(folder/'legacy_initial_check.json'); initial_checks.append(dict(job=job,**check))
    legacy=True
    if 'M00_42' in rows and not rows['M00_42'].get('failed'):
        for t in VAL:
            expected=read(old/'jobs/A_DSM/validation_16000'/(t+'.json'))['cm']
            if expected!=rows['M00_42']['tiles'][t]: legacy=False
    else: legacy=False
    reused_qualified=legacy and all(x['exact'] for x in initial_checks) and all(x['exact'] for x in stream_checks if x['job'].endswith('_42'))
    for job in [x['job'] for x in job_list()]:
        if job not in rows or rows[job].get('failed'): errors.append(job+': primary evidence incomplete')
    current_gate=gate(rows)
    if current_gate and current_gate['accepted']:
        for job in ('C21_42','C21_17'):
            if job not in rows or rows[job].get('failed'): errors.append(job+': required conditional counter incomplete')
    expected_models=[j for j,z in rows.items() if not z.get('failed')]
    for job in expected_models:
        for tile in VAL:
            for availability in ('both','rgb_missing','dsm_missing'):
                if not (base/'clean'/f'{job}_{tile}_{availability}.json').exists(): errors.append(f'{job}/{tile}: clean/fallback {availability} missing')
            count=len(list((base/'results'/job).glob(f'RGB_FAULT_{tile}_*.json')))
            if count!=160: errors.append(f'{job}/{tile}: RGB case count {count}/160')
            if not (base/'scale'/f'{job}_{tile}.json').exists(): errors.append(f'{job}/{tile}: scale diagnostic missing')
            for damage in ('down4','shift8'):
                if not list((base/'results'/job).glob(f'DSM_FAULT_{tile}_*_{damage}.json')): errors.append(f'{job}/{tile}: DSM {damage} missing')
    gatefile=base/'analysis/amplitude_gate.json'
    if gatefile.exists() and read(gatefile)!=dict(gate(rows),binding=binding(base)): raise RuntimeError('gate recomputation differs')
    result=dict(binding=binding(base),integer_matrices_verified=matrices,joint_tables_verified=joints,
        batch_streams=stream_checks,old_initial_checks=initial_checks,legacy_CM_exact=legacy,
        M00_42_causal_reuse_qualified=reused_qualified,all_required_evidence_complete=not errors,missing_or_failed=errors,
        primary_inference='R1/R2 eight endpoints remain valid if legacy anchor unqualified',observed_at=now())
    r=recovery(base)
    if r:
        for job,row in r['resumed'].items():
            f=base/'jobs'/job/'resume_loaded.json'
            if not f.exists(): errors.append(job+': resume restoration receipt absent'); continue
            loaded=read(f)
            if loaded['step']!=row['step'] or loaded['source_sha256']!=row['sha256'] or loaded['prefix_sha256']!=row['prefix_sha256']:
                raise RuntimeError('resume lineage differs')
        result.update(recovery_source=r['source_directory'],inherited_completed_jobs=sorted(r['completed']),
                      resumed_jobs={j:x['step'] for j,x in r['resumed'].items()},all_required_evidence_complete=not errors)
    write(base/'result_verification.json',result)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--directory',type=Path,required=True); print(json.dumps(verify_results(p.parse_args().directory),ensure_ascii=False))

