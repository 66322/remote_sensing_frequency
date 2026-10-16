"""Eight-arm development screen, with available and missing ability reported separately."""
import argparse
import csv
from pathlib import Path
import numpy as np
from d25_common import read,write,sha,now,within,validate_plan
from summarize_rebuild_v1_d24 import metric,scores,risk,audit_counts,matched

MISSING=('aux_zero','aux_local_zero_q1','aux_local_zero_stripe_eighth')

def abilities(s,tile=None):
    return dict(**scores(s,tile=tile),aux_zero=metric(s,'aux_zero',tile=tile),
                missing_macro=float(np.mean([metric(s,c,tile=tile) for c in MISSING])))

def compare(a,b):
    x,y=abilities(a),abilities(b)
    delta={k:x[k]-y[k] for k in x}
    return dict(delta_pp=delta,practical_gain=((delta['composite']>=.2 and delta['missing_macro']>=-.1)
                     or (delta['missing_macro']>=.5 and delta['composite']>=-.1)),
                negative_transfer=matched(a,b))

def floor(a,p0,plan):
    delta=compare(a,p0)['delta_pp']
    minimum=min(metric(a,c,tile=t)-metric(p0,c,tile=t)
                for c in plan['evaluation']['old_development_conditions'] for t in plan['data']['validation'])
    threshold=plan['screen']
    return dict(pass_floor=(abilities(a)['clean']>=threshold['clean_floor_pp']
                 and delta['composite']>=-.1 and delta['aux_zero']>=-.1
                 and delta['missing_macro']>=-.1 and minimum>=-.3),
                min_old_condition_tile_delta_pp=minimum,delta_vs_P0_pp=delta,
                clean_floor_pp=threshold['clean_floor_pp'])

def build_screen(plan,state,summaries,completes):
    rows=[]
    comparisons={}
    floors={}
    for j,s in summaries.items():
        rows.append(dict(id=j,**abilities(s),selected_step=completes[j]['selected']['step'],
                         pair_enabled_steps=completes[j]['treatment_counts'].get('Pair:enabled_steps',0)))
    for a,b in (('P1','P0'),('P2','P0'),('P2','P5'),('P3','P2'),('P3','P7'),
                ('P3','P0'),('P4','P0'),('P5','P0'),('P0','P6'),('P2','P6')):
        comparisons[a+'-'+b]=compare(summaries[a],summaries[b]) if a in summaries and b in summaries else None
    if 'P0' in summaries:
        for j in ('P2','P3','P4','P5','P7'):
            if j in summaries:floors[j]=floor(summaries[j],summaries['P0'],plan)
    def supported(j,controls):
        if j not in floors or any(comparisons.get(j+'-'+c) is None for c in controls):return None
        return floors[j]['pass_floor'] and all(comparisons[j+'-'+c]['practical_gain'] for c in controls)
    decisions={'H1_separate_decoders':supported('P2',('P0','P5')),
               'H2_projection_separate':supported('P3',('P2','P7')),
               'projection_shared':supported('P4',('P0',)),
               'Pair_corrected':None}
    if comparisons.get('P1-P0') is not None:
        if completes['P1']['treatment_counts'].get('Pair:enabled_steps')!=4000:
            raise RuntimeError('Pair did not actually run every update')
        decisions['Pair_corrected']=comparisons['P1-P0']['negative_transfer']['fusion_screen_pass']
    interaction=None
    if all(j in summaries for j in ('P0','P2','P3','P4')):
        interaction={k:abilities(summaries['P3'])[k]-abilities(summaries['P2'])[k]
                       -abilities(summaries['P4'])[k]+abilities(summaries['P0'])[k]
                     for k in ('clean','composite','missing_macro')}
    pressure={j:{c:metric(s,c) for c in plan['evaluation']['pressure_diagnostics']} for j,s in summaries.items()}
    return dict(observed_at=now(),complete_jobs=len(rows),rows=rows,matched_comparisons=comparisons,
                ability_floors=floors,mechanism_screen=decisions,
                factorial_interaction_pp=interaction,pressure_diagnostic_only=pressure,
                original_plan=plan['id'],test6_loaded=False,independent_final_loaded=False,
                evidence_level='single_seed_reused_Val2_development_only',
                interpretation='Screen support is not independent confirmation or gradient-causality proof; inspect gradient logs and raw tile counts. No automatic follow-up training.')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True)
    args=ap.parse_args();base=within(args.directory,'/home/jovyan/zzx')
    plan=read(base/'plan.json');validate_plan(plan);state=read(base/'queue_status.json')
    summaries,completes,audits,gradient_rows={},{},{},{}
    for job in plan['jobs']:
        j=job['id'];out=base/'jobs'/j
        if state['jobs'][j]['status']!='COMPLETE':continue
        complete=read(out/'complete.json')
        if sha(out/'evaluation/summary.json')!=complete['evaluation_summary_sha256']:
            raise RuntimeError('evaluation checksum changed')
        s=read(out/'evaluation/summary.json')
        if s['signature']['training']!=complete['signature'] or complete['signature']['plan_sha256']!=sha(base/'plan.json'):
            raise RuntimeError('scientific binding changed')
        if set(s['pooled'])!=set(plan['evaluation']['conditions']):
            raise RuntimeError('condition missing')
        summaries[j]=s;completes[j]=complete;audits[j]=audit_counts(s)
        diagnostics=[read(p) for p in sorted((out/'gradient_diagnostics').glob('step_*.json'))]
        if any(d['signature']!=complete['signature'] for d in diagnostics):
            raise RuntimeError('gradient diagnostic binding changed')
        gradient_rows[j]=dict(sampled_steps=len(diagnostics),
            sampled_conflict_fraction=float(np.mean([d['conflict'] for d in diagnostics])) if diagnostics else None,
            mean_cosine=float(np.mean([d['cosine'] for d in diagnostics])) if diagnostics else None,
            mean_present_norm=float(np.mean([d['present_norm'] for d in diagnostics])) if diagnostics else None,
            mean_missing_norm=float(np.mean([d['missing_norm'] for d in diagnostics])) if diagnostics else None,
            scope='first update and every100 updates; sampled diagnostics, not all4000 steps')
    result=build_screen(plan,state,summaries,completes)
    result['raw_tile_matrices_checked']=audits
    result['gradient_diagnostics_summary']=gradient_rows
    result['mechanism_attribution_requires_gradient_review']=True
    write(base/'screen_result.json',result)
    with (base/'results.csv').open('w',newline='') as f:
        fields=['id','clean','rgb_family','aux_family','composite','aux_zero','missing_macro','selected_step','pair_enabled_steps']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(result['rows'])
    for row in result['rows']:
        print('D25_RESULT',row['id'],'clean=%.4f composite=%.4f missing=%.4f'%(row['clean'],row['composite'],row['missing_macro']))
    print('D25_SCREEN_COMPLETE',len(result['rows']),'/8','test6_loaded=False',flush=True)

if __name__=='__main__':main()
