"""Frozen D27 development gates, empirical harm rather than a safety theorem."""
import argparse,csv,math
from pathlib import Path
from d27_common import read,write,sha,now,validate_plan

def value(s,c,name='candidate'):
    return s['pooled'][c]['noboundary']['metrics'][name]['valid']['mIoU_fg5']*100
def scores(s,plan):
    row={f:sum(value(s,c) for c in cs)/len(cs) for f,cs in plan['evaluation']['families'].items()}
    row['S_available']=sum(row.values())/4
    return row
def worst(s,plan,reference='fixed_rgb'):
    return min((r['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']-r['scopes']['noboundary']['metrics'][reference]['valid']['mIoU_fg5'])*100 for c in plan['evaluation']['families']['QD'] for r in s['tiles'][c].values())
def harm_rate(s,conditions,region='both'):
    correct=harm=0
    for c in conditions:
        for row in s['tiles'][c].values():
            rep=row['scopes']['noboundary']['joint_reports'][region]
            for n in ('both_correct','only_rgb_correct'):
                correct+=rep[n]['valid'];harm+=rep[n]['fused_wrong']
    return dict(correct=correct,harm=harm,rate=harm/correct if correct else None)
def retention(s,conditions):
    n=k=0
    for c in conditions:
        for row in s['tiles'][c].values():
            rep=row['scopes']['noboundary']['joint_reports']['both']['only_dsm_correct']
            n+=rep['valid'];k+=rep['fused_correct']
    return k/n*100 if n else None
def reduced(a,b,factor=.8):
    # Zero baseline harm cannot provide evidence for a relative reduction claim.
    return a['rate'] is not None and b['rate'] is not None and b['rate']>0 and a['rate']<=factor*b['rate']+1e-12
def routing(s,conditions):
    rows=[r['route_diagnostics'] for c in conditions for r in s['tiles'][c].values()]
    n=sum(r['observed_cells'] for r in rows)
    weights=[sum(r['weight_sums'][k] for r in rows)/n if n else None for k in range(3)]
    entropy=sum(r['entropy_sum'] for r in rows)/n if n else None
    disagreement=sum(r['expert_disagreement_cells'] for r in rows)/n if n else None
    return dict(weights=weights,entropy=entropy,disagreement=disagreement)
def screen(s,plan):
    z={n:scores(v,plan) for n,v in s.items()};qd=plan['evaluation']['families']['QD'];ld=plan['evaluation']['local']['LD'];primary=plan['evaluation']['primary']
    diff=lambda a,b:z[a]['S_available']-z[b]['S_available']
    safety_harm={n:harm_rate(s[n],qd) for n in ('G0','G1')}
    safe=dict(worst_improvement_pp=worst(s['G1'],plan)-worst(s['G0'],plan),harm=safety_harm,
              composite_delta_pp=diff('G1','G0'),clean_vs_rgb_pp=value(s['G1'],'clean')-value(s['G1'],'clean','fixed_rgb'),worst_vs_rgb_pp=worst(s['G1'],plan))
    safe['passed']=safe['worst_improvement_pp']>=.2-1e-9 and reduced(safety_harm['G1'],safety_harm['G0']) and safe['composite_delta_pp']>=-.1-1e-9 and safe['clean_vs_rgb_pp']>=.5-1e-9 and safe['worst_vs_rgb_pp']>=-.2-1e-9
    route={family:routing(s['G1'],cs) for family,cs in plan['evaluation']['families'].items()}
    spread=max(abs(route[a]['weights'][k]-route[b]['weights'][k]) for a in route for b in route for k in range(3))
    specialize=max(r['disagreement'] for r in route.values())
    moe=dict(delta_pp=diff('G1','S1'),clean_delta_pp=z['G1']['C']-z['S1']['C'],routing_by_family=route,max_family_weight_difference=spread,max_expert_disagreement=specialize)
    moe['passed']=safe['passed'] and moe['delta_pp']>=.3-1e-9 and moe['clean_delta_pp']>=-.1-1e-9 and spread>=.02 and specialize>=.01
    keep={n:retention(s[n],primary) for n in ('G1','L1')}
    local=dict(delta_pp=diff('L1','G1'),vs_shuffled_pp=diff('L1','L1-sh'),boundary_harm={n:harm_rate(s[n],ld,'boundary16') for n in ('G1','L1')},retention=keep,worst_vs_rgb_pp=worst(s['L1'],plan))
    local['passed']=local['delta_pp']>=.2-1e-9 and local['vs_shuffled_pp']>=.2-1e-9 and reduced(local['boundary_harm']['L1'],local['boundary_harm']['G1']) and all(v is not None for v in keep.values()) and keep['L1']-keep['G1']>=-2-1e-9 and local['worst_vs_rgb_pp']>=-.2-1e-9
    class_deltas=[]
    for c in range(5):
        values=[(s['C1']['pooled'][condition]['noboundary']['metrics']['candidate']['valid']['IoU'][c]-s['L1']['pooled'][condition]['noboundary']['metrics']['candidate']['valid']['IoU'][c])*100 for condition in primary]
        class_deltas.append(sum(values)/len(values))
    classes=dict(delta_pp=diff('C1','L1'),vs_shuffled_pp=diff('C1','C1-sh'),per_class_mean_delta_pp=class_deltas,worst_vs_rgb_pp=worst(s['C1'],plan))
    classes['passed']=classes['delta_pp']>=.2-1e-9 and classes['vs_shuffled_pp']>=.2-1e-9 and sum(v>0 for v in class_deltas)>=3 and min(class_deltas)>=-.5-1e-9 and classes['worst_vs_rgb_pp']>=-.2-1e-9
    return dict(scores_pp=z,safety=safe,dynamic_routing=moe,local=local,classes=classes,
                CE_vs_safe={a+'1-'+a+'0':diff(a+'1',a+'0') for a in ('S','G','L','C')},
                new_contribution_established=False,statistical_significance_test=False,test6_loaded=False)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);args=ap.parse_args()
    base=args.directory.resolve();base.relative_to(Path('/home/jovyan/zzx').resolve());plan=read(base/'plan.json');jobs=validate_plan(plan)
    summaries={};records={};capacity={}
    for job in jobs:
        folder=base/'jobs'/job['id'];path=folder/'complete.json'
        if not path.exists():continue
        row=read(path)
        for name,key in (('evaluation','evaluation_summary_sha256'),('fixed8000','fixed8000_summary_sha256')):
            if sha(folder/name/'summary.json')!=row[key]:raise RuntimeError('evaluation changed')
        if sha(folder/'selected.pth')!=row['selected_checkpoint_sha256'] or row['global_step']!=8000 or row['test6_loaded']:raise RuntimeError('checkpoint/budget changed')
        if row['signature']['execution_commit']!=plan['execution_commit'] or row['signature']['plan_sha256']!=sha(base/'plan.json'):raise RuntimeError('binding changed')
        summaries[job['id']]=read(folder/'evaluation/summary.json');records[job['id']]=dict(selected=row['selected'],complete_sha256=sha(path));capacity[job['id']]=read(folder/'model_capacity.json')
    result=dict(status='COMPLETE' if len(summaries)==10 else 'INCOMPLETE_NO_SCIENTIFIC_GATE',completed_jobs=len(summaries),records=records,capacity=capacity,observed_at=now(),test6_loaded=False)
    if len(summaries)==10:
        if len({r['trainable_parameters'] for r in capacity.values()})!=1 or len({r['initial_fusion_state_sha256'] for r in capacity.values()})!=1:raise RuntimeError('capacity/common initialization differs')
        result['screen']=screen(summaries,plan)
    write(base/'screen_result.json',result)
    if summaries:
        rows=[dict(job=n,selected_step=records[n]['selected']['step'],**scores(s,plan)) for n,s in summaries.items()]
        with (base/'results.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        for row in rows:print('D27_RESULT',row,flush=True)
    print('D27_SCREEN',result['status'],len(summaries),'/10',flush=True)
    return 0 if len(summaries)==10 else 2
if __name__=='__main__':raise SystemExit(main())
