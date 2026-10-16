"""Prespecified diagnostic contrasts, never selects a new training candidate."""
import argparse,itertools
from pathlib import Path
import numpy as np
from post_t_mechanism_common import *
def score(row):
    cm=np.asarray(row['cm'])
    if cm.shape!=(6,6) or cm.dtype.kind not in 'iu' or (cm<0).any():raise ValueError('invalid raw counts')
    cm=cm.astype(np.int64);tp=np.diag(cm);den=cm.sum(0)+cm.sum(1)-tp
    used=den[:5]>0;value=100*float(np.mean(tp[:5][used]/den[:5][used]))
    if abs(value-100*row['mIoU_fg5'])>1e-8:raise ValueError('metric/count mismatch')
    return value
def scores(s):
    if s['test6_loaded'] or s['independent_final_loaded']:raise ValueError('source scope')
    out={}
    for key,rows in s['tiles'].items():
        if set(rows)!=set(['3_11','5_10']):raise ValueError('tile split')
        def metric(row):return row['metrics']['candidate']['valid']
        pcs=metric(s['pooled'][key]['noboundary'])
        parts={t:metric(r['scopes']['noboundary']) for t,r in rows.items()}
        if not np.array_equal(sum(np.asarray(v['cm'],dtype=np.int64) for v in parts.values()),np.asarray(pcs['cm'],dtype=np.int64)):raise ValueError('pooled counts')
        out[key]=dict(pooled=score(pcs),tiles={t:score(v) for t,v in parts.items()})
    return out
def compare(a,b):
    return {k:dict(pooled_gain_pp=a[k]['pooled']-b[k]['pooled'],tile_gains_pp={t:a[k]['tiles'][t]-b[k]['tiles'][t] for t in ('3_11','5_10')}) for k in a if k in b}
def signal(row,threshold=.3):
    return row['pooled_gain_pp']>=threshold and all(v>0 for v in row['tile_gains_pp'].values())
def summarize(base):
    p=validate(read(base/'plan.json'));verify_snapshot(base)
    all_scores={};bindings={}
    for j in ORDER:
        accept_worker(base,j,p);f=base/'jobs'/j/'summary.json';all_scores[j]=scores(read(f));bindings[j]=dict(path=str(f),sha256=sha(f))
    pred=Path(p['predecessor_directory']);parent=p['parent_transfer_plan'];curves={};exposure={}
    for j in previous.ORDER:
        c=previous.accept_worker(pred,j,parent);exposure[j]={k:c['treatment_counts'].get(k) for k in ('branch_nonzero_updates','branch_exposed_updates')}
        paths={step:pred/'jobs'/j/folder/'summary.json' for step,folder in ((0,'initial_evaluation'),(8000,'support_evaluation'))}
        for step,path in paths.items():
            artifact=path.relative_to(pred/'jobs'/j).as_posix()
            if sha(path)!=c['artifacts'][artifact]:raise RuntimeError('trajectory reference changed')
        z=scores(read(paths[0]));last=scores(read(paths[8000]));mid=all_scores['L_'+j]
        curves[j]=dict(step0=z,step4000=mid,step8000=last,delta_0_4000=compare(mid,z),delta_4000_8000=compare(last,mid))
    pairs={}
    module_cards=[j for j in p['jobs'] if j['kind']=='module']
    for factor in ('rgb','dsm','head','context'):
        pairs[factor]={}
        for a in module_cards:
            low=False if factor=='context' else 0;high=True if factor=='context' else 3
            if a[factor]!=low:continue
            b=next(b for b in module_cards if b[factor]==high and all(b[k]==a[k] for k in ('rgb','dsm','head','context') if k!=factor))
            pairs[factor][b['id']+'-'+a['id']]=compare(all_scores[b['id']],all_scores[a['id']])
    contrasts={b+'-'+a:compare(all_scores[b],all_scores[a]) for a,b in [('M000_context','M003_context'),('M000_context','M300_context'),('M000_context','M030_context'),('M003_context','M333_context'),('M333_masked','M333_context')]}
    budget=all(signal(curves[j]['delta_4000_8000']['rgb_U']) for j in ('T1','T7'))
    for j in ('T1','T7'):
        curves[j]['late_rgb_U_signal']=signal(curves[j]['delta_4000_8000']['rgb_U'])
    endpoint=read(base/'jobs/M333_context/endpoint_checks.json')
    if len(endpoint)!=16 or not all(x['exact'] for x in endpoint):raise RuntimeError('R0 endpoint proof missing')
    recommendations=dict(matched_budget_study_supported=budget,
      budget_interpretation='late gain is a planning signal, not proof that longer training succeeds; absent signal is not proof of optimal convergence',
      representation_followup_signal=signal(contrasts['M333_context-M003_context']['rgb_U']),
      representation_interpretation='package compatibility contrast only; negative swaps do not prove information absent',
      next_training_launched=False,automatic_retry=False)
    result=dict(observed_at=now(),plan_sha256=sha(base/'plan.json'),code_manifest_sha256=sha(base/'code_manifest.json'),optimizer_updates=0,
       scores=all_scores,module_factor_pairs=pairs,fixed_contrasts=contrasts,learning_curves=curves,branch_exposure=exposure,
       endpoint_checks=endpoint,recommendations=recommendations,source_summaries=bindings,
       scope='Potsdam Val2 seed42 repeated development; known masks; no Test6/held4/final',
       predecessor_T7_gate=read(pred/'transfer_screen.json')['T7_passed'])
    write(base/'mechanism_screen.json',result)
    print('MECHANISM_SCREEN',recommendations,flush=True)
    return result
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();summarize(a.directory)
if __name__=='__main__':main()
