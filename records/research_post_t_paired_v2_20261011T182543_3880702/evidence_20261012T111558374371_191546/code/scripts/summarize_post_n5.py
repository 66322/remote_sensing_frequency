"""Recompute N5 fixed-candidate gates from pooled integer matrices."""
import argparse
from pathlib import Path
import numpy as np
from post_n5_common import *
from post_d30_evaluation import metric,decode_joint
from summarize_post_ab_n1 import audit_summary,cell
from summarize_post_d30 import difference,worst,score,retention
def content_cell(base,j,plan):
    folder=base/'jobs'/j;c=read(folder/'complete.json');out={}
    for tag in ('content_evaluation','content_fixed8000'):
        path=folder/tag/'summary.json'
        if sha(path)!=c[tag+'_summary_sha256']:raise RuntimeError('content completion SHA differs')
        s=read(path)
        if s['binding']['training']!=c['signature'] or set(s['tiles'])!={d+'_'+r for d in ('rgb','dsm') for r in ('U','H','L','T')}:raise RuntimeError('content coverage/binding differs')
        audit_summary(s,plan)
        for condition,rows in s['tiles'].items():
            for row in rows.values():
                for scope in ('full','noboundary'):
                    for region,jr in row['scopes'][scope]['joint'].items():
                        a=decode_joint(jr);cm=row['scopes'][scope]['metrics']['candidate'][region]['cm']
                        if (a<0).any():raise RuntimeError('negative joint count')
                        if not np.array_equal(a.sum((1,2)),cm):raise RuntimeError('joint candidate marginal differs')
                        if not np.array_equal(a.sum((2,3)),row['scopes'][scope]['metrics']['fixed_rgb'][region]['cm']) or not np.array_equal(a.sum((1,3)),row['scopes'][scope]['metrics']['fixed_dsm'][region]['cm']):raise RuntimeError('joint anchors differ')
            for scope in ('full','noboundary'):
                for r,jr in s['pooled'][condition][scope]['joint'].items():
                    total=sum((decode_joint(x['scopes'][scope]['joint'][r]) for x in rows.values()),np.zeros((6,)*4,np.int64))
                    if not np.array_equal(total,decode_joint(jr)):raise RuntimeError('joint pooling differs')
        out[tag]=s
    return out
def tile_difference(a,b,conditions,tile):
    return 100*sum(a['tiles'][c][tile]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']-b['tiles'][c][tile]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5'] for c in conditions)/len(conditions)
def screen(data,content,plan):
    c,b,o='N5-3','N5-1','N5-0';a=content[c]['content_evaluation'];control=content[b]['content_evaluation'];cs=['rgb_T','dsm_T']
    checks={};deltas={}
    deltas['T_mean_vs_random']=difference(a,control,cs);checks['T_mean_gain']=deltas['T_mean_vs_random']>=.5-1e-9
    deltas['T_tile_mean']={t:tile_difference(a,control,cs,t) for t in plan['data']['validation']};checks['T_both_tiles_positive']=all(x>0 for x in deltas['T_tile_mean'].values())
    deltas['fixed_T_mean_vs_random']=difference(content[c]['content_fixed8000'],content[b]['content_fixed8000'],cs);checks['fixed_T_positive']=deltas['fixed_T_mean_vs_random']>0
    for condition in ('clean','dsm_missing','rgb_missing'):
        value=difference(data[c]['evaluation'],data[o]['evaluation'],[condition]);deltas[condition+'_vs_original']=value;checks[condition+'_floor']=value>=-.1-1e-9
    value=difference(data[c]['evaluation'],data[b]['evaluation'],plan['N5_old_random_conditions']);deltas['old_random_vs_random']=value;checks['old_random_floor']=value>=-.1-1e-9
    value=worst(data[c]['evaluation'],data[b]['evaluation'],plan['evaluation']['primary']);deltas['worst_primary_vs_random']=value;checks['worst_primary_floor']=value>=-.2-1e-9
    directions={d:dict(pooled_gain_pp=difference(a,control,[d+'_T']),tile_gains_pp={t:tile_difference(a,control,[d+'_T'],t) for t in plan['data']['validation']}) for d in ('rgb','dsm')}
    # Both-direction role requires gains in each direction/tile, not only their average.
    bilateral=all(r['pooled_gain_pp']>0 and all(x>0 for x in r['tile_gains_pp'].values()) for r in directions.values())
    return dict(primary_candidate=c,passed=all(checks.values()),bilateral_candidate=all(checks.values()) and bilateral,checks=checks,deltas_pp=deltas,directions=directions,
        ordinary_scores={j:score(data[j]['evaluation'],plan) for j in IDS},harm_and_retention={j:retention(data[j]['evaluation'],plan['evaluation']['primary']) for j in IDS},
        old_random_conditions=plan['N5_old_random_conditions'],new_contribution_established=False,automatic_training=False,test6_loaded=False,observed_at=now())
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();base=a.directory;plan=read(base/'plan.json');validate(plan)
    data={j:cell(base,j,plan) for j in IDS};content={j:content_cell(base,j,plan) for j in IDS}
    result=screen(data,content,plan);write(base/'n5_screen.json',result)
    print('N5_SCREEN',result['passed'],result['deltas_pp'],flush=True)
if __name__=='__main__':main()
