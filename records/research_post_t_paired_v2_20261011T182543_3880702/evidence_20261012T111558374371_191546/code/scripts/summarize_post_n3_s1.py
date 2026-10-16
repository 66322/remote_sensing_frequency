"""Frozen nine-cell gates with complete binding and integer pooling checks."""
import argparse
from pathlib import Path
from post_n3_s1_common import *
from summarize_post_ab_n1 import cell,audit_summary
from summarize_post_d30 import score,difference,worst,retention
def tile_score(s,p,tile):
    families=p['evaluation']['families']
    return sum(sum(100*s['tiles'][c][tile]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5'] for c in cs)/len(cs) for cs in families.values())/len(families)
def U(s,tile=None,direction=None):
    keys=[direction+'_U'] if direction else ['rgb_U','dsm_U']
    return sum(100*(s['tiles'][c][tile]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5'] if tile else s['pooled'][c]['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']) for c in keys)/len(keys)
def gates(data,p):
    sel={j:data[j]['evaluation'] for j in IDS};fix={j:data[j]['fixed8000'] for j in IDS}
    us={j:data[j]['support_evaluation'] for j in IDS};uf={j:data[j]['support_fixed8000'] for j in IDS}
    S=lambda x:score(x,p)['S_available']
    checks={};deltas={}
    for b in ('N3-0','N3-1'):
        delta=S(sel['N3-4'])-S(sel[b]);deltas['S_vs_'+b]=delta;checks['S_vs_'+b]=delta>=.3-1e-9
        checks['fixed_S_vs_'+b]=S(fix['N3-4'])>S(fix[b])
        checks['tiles_S_vs_'+b]=all(tile_score(sel['N3-4'],p,t)>tile_score(sel[b],p,t) for t in p['data']['validation'])
    for family,b in [('QR','N3-2'),('QD','N3-3')]:
        cs=p['evaluation']['families'][family];delta=difference(sel['N3-4'],sel[b],cs);deltas[family+'_vs_'+b]=delta
        checks[family+'_vs_'+b]=delta>=.2-1e-9;checks['fixed_'+family+'_vs_'+b]=difference(fix['N3-4'],fix[b],cs)>0
        checks['tiles_'+family+'_vs_'+b]=all(sum(100*(sel['N3-4']['tiles'][c][t]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']-sel[b]['tiles'][c][t]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']) for c in cs)/len(cs)>0 for t in p['data']['validation'])
    for b in ('N3-0','N3-1'):
        for condition in ('clean','dsm_missing','rgb_missing'):checks[condition+'_floor_vs_'+b]=difference(sel['N3-4'],sel[b],[condition])>=-.1-1e-9
        checks['worst_vs_'+b]=worst(sel['N3-4'],sel[b],p['evaluation']['primary'])>=-.2-1e-9
    n3=dict(candidate='N3-4',passed=all(checks.values()),checks=checks,deltas_pp=deltas)
    checks={};deltas={}
    for b,threshold in [('S1-0',.5),('S1-1',.2),('S1-2',.2)]:
        delta=U(us['S1-3'])-U(us[b]);deltas['U_mean_vs_'+b]=delta;checks['U_mean_vs_'+b]=delta>=threshold-1e-9
        checks['fixed_U_vs_'+b]=U(uf['S1-3'])>U(uf[b])
        checks['tile_U_vs_'+b]=all(U(us['S1-3'],t)>U(us[b],t) for t in p['data']['validation'])
    for c in ('clean','dsm_missing','rgb_missing'):checks[c+'_floor']=difference(sel['S1-3'],sel['S1-0'],[c])>=-.1-1e-9
    checks['worst_primary_floor']=worst(sel['S1-3'],sel['S1-0'],p['evaluation']['primary'])>=-.2-1e-9
    directions={d:{b:dict(pooled_gain_pp=U(us['S1-3'],direction=d)-U(us[b],direction=d),
        tile_gains_pp={t:U(us['S1-3'],t,d)-U(us[b],t,d) for t in p['data']['validation']}) for b in ('S1-0','S1-1','S1-2')} for d in ('rgb','dsm')}
    bilateral=all(r['pooled_gain_pp']>0 and all(v>0 for v in r['tile_gains_pp'].values()) for ds in directions.values() for r in ds.values())
    s1=dict(candidate='S1-3',passed=all(checks.values()),bilateral_candidate=all(checks.values()) and bilateral,checks=checks,deltas_pp=deltas,directions=directions,
        interaction_U_pp=U(us['S1-3'])-U(us['S1-2'])-U(us['S1-1'])+U(us['S1-0']),
        simple_policy_rule='if a single-factor control matches the joint, close combination contribution; no budget/seed rescue')
    return dict(N3=n3,S1=s1,scores_pp={j:S(sel[j]) for j in IDS},U_pp={j:U(us[j]) for j in IDS},
        primary_retention={j:retention(sel[j],p['evaluation']['primary']) for j in IDS},observed_at=now(),automatic_followup=False,new_contribution_established=False)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();base=a.directory.resolve();p=read(base/'plan.json');validate_plan(p)
    data={j:cell(base,j,p) for j in IDS}
    for j in IDS:
        folder=base/'jobs'/j;c=read(folder/'complete.json')
        if c['signature']['initial_checkpoint_sha256']!=BASE_SHA or c['signature']['mask_manifest_sha256']!=sha(base/'mask_manifest.json'):raise RuntimeError('base/mask binding changed')
        for tag in ('support_evaluation','support_fixed8000'):
            path=folder/tag/'summary.json'
            if sha(path)!=c[tag+'_summary_sha256']:raise RuntimeError('support summary binding differs')
            row=read(path)
            if row['binding']['training']!=c['signature'] or set(row['tiles'])!={'rgb_U','dsm_U'}:raise RuntimeError('support provenance differs')
            audit_summary(row,p);data[j][tag]=row
    result=gates(data,p);write(base/'n3_s1_screen.json',result)
    print('N3_S1_SCREEN',result['N3']['passed'],result['S1']['passed'],result['S1']['bilateral_candidate'],flush=True)
if __name__=='__main__':main()
