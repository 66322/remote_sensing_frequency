"""Validate raw-count summaries and apply preregistered N1 development screen."""
import argparse
from pathlib import Path
import numpy as np
from post_ab_queue_common import read,write,sha,now,N1,validate_plan
from summarize_post_d30 import score,difference,worst,retention
from post_d30_evaluation import metric

def audit_summary(s,plan):
    if s['test6_loaded'] or s['independent_final_loaded']:raise RuntimeError('final source opened')
    for condition,rows in s['tiles'].items():
        if set(rows)!=set(plan['data']['validation']):raise RuntimeError('tile set differs')
        for scope in ('full','noboundary'):
            sample=next(iter(rows.values()))['scopes'][scope]['metrics']
            for name,regions in sample.items():
                for region in regions:
                    cs=[]
                    for row in rows.values():
                        cm=np.asarray(row['scopes'][scope]['metrics'][name][region]['cm'])
                        if cm.shape!=(6,6) or cm.dtype.kind not in 'iu' or (cm<0).any():raise RuntimeError('invalid integer matrix')
                        cs.append(cm.astype(np.int64))
                    pooled=s['pooled'][condition][scope]['metrics'][name][region]
                    total=sum(cs,np.zeros((6,6),np.int64))
                    if not np.array_equal(total,np.asarray(pooled['cm'],np.int64)):raise RuntimeError('pooled counts differ')
                    actual=metric(total)['mIoU_fg5'];reported=pooled['mIoU_fg5']
                    if actual is None:
                        if reported is not None:raise RuntimeError('undefined metric differs')
                    elif reported is None or abs(actual-reported)>1e-12:raise RuntimeError('offline IoU differs')

def cell(base,job,plan):
    folder=base/'jobs'/job;complete=read(folder/'complete.json')
    if complete['global_step']!=8000 or complete['signature']['execution_commit']!=plan['execution_commit'] or complete['signature']['plan_sha256']!=sha(base/'plan.json'):
        raise RuntimeError('completion binding differs '+job)
    if sha(folder/'selected.pth')!=complete['selected_checkpoint_sha256']:raise RuntimeError('checkpoint binding differs')
    out={}
    for tag in ('evaluation','fixed8000'):
        path=folder/tag/'summary.json'
        if sha(path)!=complete[tag+'_summary_sha256']:raise RuntimeError('summary SHA differs')
        s=read(path)
        if s['binding']['training']!=complete['signature']:raise RuntimeError('summary provenance differs')
        audit_summary(s,plan);out[tag]=s
    return out

def screen(data,plan):
    sel={j:data[j]['evaluation'] for j in N1};fix={j:data[j]['fixed8000'] for j in N1}
    S=lambda s:score(s,plan)['S_available']
    candidate=sel['N1-3'];checks={};deltas={}
    for b in ('N1-1','N1-2'):
        deltas[b]=S(candidate)-S(sel[b]);checks['S_vs_'+b]=deltas[b]>=.3-1e-9
        checks['fixed_sign_vs_'+b]=S(fix['N1-3'])>S(fix[b])
        for c in ('clean','dsm_missing','rgb_missing'):
            checks[c+'_floor_vs_'+b]=difference(candidate,sel[b],[c])>=-.1-1e-9
        checks['worst_vs_'+b]=worst(candidate,sel[b],plan['evaluation']['primary'])>=-.2-1e-9
        # Equal family and condition weights at tile level, matching S_available.
        tile_deltas={}
        for tile in plan['data']['validation']:
            def tile_score(s):
                vals=[]
                for cs in plan['evaluation']['families'].values():
                    vals.append(sum(100*s['tiles'][c][tile]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5'] for c in cs)/len(cs))
                return sum(vals)/len(vals)
            tile_deltas[tile]=tile_score(candidate)-tile_score(sel[b])
        checks['both_tiles_positive_vs_'+b]=all(x>0 for x in tile_deltas.values())
    scores={j:S(sel[j]) for j in N1}
    return dict(primary_candidate='N1-3',passed=all(checks.values()),checks=checks,deltas_pp=deltas,scores_pp=scores,
                frozen_multiscale_pp=scores['N1-1']-scores['N1-0'],adaptation_late_pp=scores['N1-2']-scores['N1-0'],
                interaction_pp=(scores['N1-3']-scores['N1-2'])-(scores['N1-1']-scores['N1-0']),
                baseline_for_reserved_N2='N1-3' if all(checks.values()) else 'N1-2',
                baseline_rule='fixed primary if all gates pass, otherwise predefined ordinary adapted late-feature baseline; never post-hoc maximum',
                harm_and_retention={j:retention(sel[j],plan['evaluation']['primary']) for j in N1},
                observed_at=now(),single_seed_development=True,new_contribution_established=False,test6_loaded=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args();base=a.directory.resolve()
    base.relative_to(Path('/home/jovyan/zzx'));plan=read(base/'plan.json');validate_plan(plan)
    data={j:cell(base,j,plan) for j in N1};result=screen(data,plan);write(base/'n1_screen.json',result)
    print('POST_AB_N1_SCREEN',result['passed'],result['deltas_pp'],flush=True)
if __name__=='__main__':main()
