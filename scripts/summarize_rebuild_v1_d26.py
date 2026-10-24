"""Predeclared development gates. Never turns a technical failure into a result."""
import argparse,csv
from pathlib import Path
from d26_common import read,write,sha,now,validate_plan

def value(summary,condition,name='candidate',region='valid'):
    return summary['pooled'][condition]['noboundary']['metrics'][name][region]['mIoU_fg5']*100

def scores(summary,plan):
    result={family:sum(value(summary,c) for c in cs)/len(cs) for family,cs in plan['evaluation']['families'].items()}
    result['S_available']=sum(result.values())/4
    for family,cs in plan['evaluation']['local'].items():result[family]=sum(value(summary,c) for c in cs)/len(cs)
    return result

def pair_gate(candidate,control,plan):
    a,b=scores(candidate,plan),scores(control,plan)
    tile_differences=[(candidate['tiles'][c][t]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']-control['tiles'][c][t]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5'])*100 for c in plan['evaluation']['primary'] for t in plan['data']['validation']]
    deltas={k:a[k]-b[k] for k in ('S_available','C','QR','QD','QJ')}
    passed=deltas['S_available']>=.2-1e-9 and deltas['C']>=-.1-1e-9 and all(deltas[k]>=-.2-1e-9 for k in ('QR','QD','QJ')) and min(tile_differences)>=-.5-1e-9
    return dict(passed=passed,deltas_pp=deltas,worst_tile_condition_delta_pp=min(tile_differences))

def protections(candidate,b0,plan):
    missing={c:value(candidate,c)-value(candidate,c,'fixed_dsm' if c=='rgb_missing' else 'fixed_rgb') for c in plan['evaluation']['missing']}
    local={family:sum(value(candidate,c)-value(b0,c) for c in cs)/len(cs) for family,cs in plan['evaluation']['local'].items()}
    worst=min((candidate['tiles'][c][t]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']-b0['tiles'][c][t]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5'])*100 for cs in plan['evaluation']['local'].values() for c in cs for t in plan['data']['validation'])
    identity=all(all(row['fallback_logits_equal_own'].values()) for rows in candidate['tiles'].values() for row in rows.values())
    return dict(passed=all(v>=-.1-1e-9 for v in missing.values()) and all(v>=-.2-1e-9 for v in local.values()) and worst>=-.5-1e-9 and identity,missing_vs_fixed_expert_pp=missing,local_vs_B0_pp=local,worst_local_tile_delta_pp=worst,logit_identity_own=identity)

def retention(summary,plan):
    totals={n:[0,0] for n in ('only_rgb_correct','only_dsm_correct')}
    for c in plan['evaluation']['primary']:
        for n in totals:
            row=summary['pooled'][c]['noboundary']['joint_reports']['both'][n]
            totals[n][0]+=row['valid'];totals[n][1]+=row['fused_correct']
    # Descriptive aggregate across repeated stress conditions, no independent N claim.
    return {n:v[1]/v[0]*100 if v[0] else None for n,v in totals.items()}

def screen(summaries,plan):
    scored={n:scores(s,plan) for n,s in summaries.items()};out={}
    for candidate in ('XSF','XS','XF'):
        pairs={control:pair_gate(summaries[candidate],summaries[control],plan) for control in ('B0','CAP','X')}
        protect=protections(summaries[candidate],summaries['B0'],plan)
        joint_delta=scored[candidate]['S_available']-scored['J0']['S_available']
        out[candidate]=dict(comparisons=pairs,protections=protect,vs_J0_pp=joint_delta,main_gate=all(v['passed'] for v in pairs.values()) and protect['passed'] and joint_delta>=-.1-1e-9,overall_leading_gate=joint_delta>=.2-1e-9)
    v=lambda n:scored[n]['S_available']
    frequency=[v('XSF')-v('XS'),v('XF')-v('X'),v('XSF')-v('XSF-shF')]
    semantic=[v('XSF')-v('XF'),v('XS')-v('X'),v('XSF')-v('XSF-shS')]
    baseline=retention(summaries['X'],plan);primary=retention(summaries['XSF'],plan)
    retention_delta={n:primary[n]-baseline[n] if primary[n] is not None and baseline[n] is not None else None for n in primary}
    keep=all(v is not None and v>=-.5-1e-9 for v in retention_delta.values()) and any(v is not None and v>=1-1e-9 for v in retention_delta.values())
    return dict(scores_pp=scored,candidates=out,frequency=dict(deltas_pp=frequency,passed=min(frequency)>=.1-1e-9),semantic=dict(deltas_pp=semantic,passed=min(semantic)>=.1-1e-9),factor_interaction_pp=(v('XSF')-v('XS'))-(v('XF')-v('X')),unique_information_retention=dict(delta_vs_X_pp=retention_delta,claim_gate=keep,aggregation='sum counts over10 primary stress conditions, descriptive repeated pixels'),primary_XSF_eligible=out['XSF']['main_gate'],primary_full_mechanism_eligible=out['XSF']['main_gate'] and min(frequency)>=.1-1e-9 and min(semantic)>=.1-1e-9,new_contribution_established=False,statistical_significance_test=False,test6_loaded=False,automatic_followup=False)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);args=ap.parse_args()
    base=args.directory.resolve();base.relative_to(Path('/home/jovyan/zzx').resolve());plan=read(base/'plan.json');jobs=validate_plan(plan)
    summaries={};fixed={};records={};capacity={}
    for job in jobs:
        folder=base/'jobs'/job['id'];path=folder/'complete.json'
        if not path.exists():continue
        complete=read(path)
        for name,key in (('evaluation','evaluation_summary_sha256'),('fixed8000','fixed8000_summary_sha256')):
            summary=folder/name/'summary.json'
            if sha(summary)!=complete[key]:raise RuntimeError('summary checksum changed')
        if sha(folder/'selected.pth')!=complete['selected_checkpoint_sha256'] or complete['global_step']!=8000 or complete['test6_loaded']:raise RuntimeError('completed binding changed')
        summaries[job['id']]=read(folder/'evaluation/summary.json');fixed[job['id']]=read(folder/'fixed8000/summary.json');records[job['id']]=dict(selected=complete['selected'],path=str(path),sha256=sha(path));capacity[job['id']]=read(folder/'model_capacity.json')
        if complete['signature']['execution_commit']!=plan['execution_commit'] or complete['signature']['plan_sha256']!=sha(base/'plan.json'):raise RuntimeError('scientific binding changed')
    result=dict(status='COMPLETE' if len(summaries)==9 else 'INCOMPLETE_NO_SCIENTIFIC_GATE',completed_jobs=len(summaries),records=records,capacity=capacity,observed_at=now(),test6_loaded=False)
    if len(summaries)==9:
        matched=['CAP','X','XS','XF','XSF','XSF-shS','XSF-shF']
        if len({capacity[n]['trainable_parameters'] for n in matched})!=1 or len({capacity[n]['initial_fusion_state_sha256'] for n in capacity})!=1:raise RuntimeError('capacity/common initialization control failed')
        result['screen']=screen(summaries,plan)
        result['fixed_reference_scores_pp']={}
        for name in ('fixed_rgb','fixed_dsm','fixed_probability_average','fixed_availability_switch'):
            ref={f:sum(value(summaries['B0'],c,name) for c in cs)/len(cs) for f,cs in plan['evaluation']['families'].items()}
            ref['S_available']=sum(ref.values())/4
            ref['missing']={c:value(summaries['B0'],c,name) for c in plan['evaluation']['missing']}
            result['fixed_reference_scores_pp'][name]=ref
        result['fixed8000_scores_pp']={n:{f:sum(value(s,c) for c in cs)/len(cs) for f,cs in plan['evaluation']['families'].items()} for n,s in fixed.items()}
        for row in result['fixed8000_scores_pp'].values():row['S_available']=sum(row.values())/4
        result['fixed8000_factor_deltas_pp']={name:result['fixed8000_scores_pp'][a]['S_available']-result['fixed8000_scores_pp'][b]['S_available'] for name,a,b in [('XSF-XS','XSF','XS'),('XF-X','XF','X'),('XSF-XF','XSF','XF'),('XS-X','XS','X'),('XSF-shS','XSF','XSF-shS'),('XSF-shF','XSF','XSF-shF')]}
        print('D26_SCREEN_COMPLETE 9/9',result['screen']['primary_full_mechanism_eligible'],flush=True)
    write(base/'screen_result.json',result)
    if summaries:
        rows=[dict(job=n,selected_step=records[n]['selected']['step'],**scores(s,plan)) for n,s in summaries.items()]
        with (base/'results.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        for row in rows:print('D26_RESULT',row,flush=True)
    return 0 if len(summaries)==9 else 2
if __name__=='__main__':raise SystemExit(main())
