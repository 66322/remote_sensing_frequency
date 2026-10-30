"""Fixed N2 screen with independent raw-count and checkpoint/summary binding checks."""
import argparse
from pathlib import Path
from post_ab_n2_common import read,write,now,validate_plan,N2
from summarize_post_ab_n1 import cell
from summarize_post_d30 import score,difference,worst,retention

def screen(data,plan):
    sel={j:data[j]['evaluation'] for j in N2};fix={j:data[j]['fixed8000'] for j in N2}
    a=sel['N2-3'];b=sel['N2-0'];S=lambda s:score(s,plan)['S_available']
    comparisons={'spatial':('N2-0',plan['evaluation']['primary'],.3),
        'dsm_degraded_vs_height_only':('N2-1',plan['evaluation']['families']['QD'],.2),
        'rgb_degraded_vs_semantic_only':('N2-2',plan['evaluation']['families']['QR'],.2),
        'height_correspondence':('N2-4',plan['evaluation']['families']['QR'],.2),
        'semantic_correspondence':('N2-5',plan['evaluation']['families']['QD'],.2)}
    checks={};deltas={};tile_deltas={}
    for name,(ref,cs,floor) in comparisons.items():
        d=S(a)-S(sel[ref]) if name=='spatial' else difference(a,sel[ref],cs)
        deltas[name]=d;checks[name]=d>=floor-1e-9
        fixed_delta=S(fix['N2-3'])-S(fix[ref]) if name=='spatial' else difference(fix['N2-3'],fix[ref],cs)
        checks['fixed_sign_'+name]=fixed_delta>0
        td={}
        for tile in plan['data']['validation']:
            if name=='spatial':
                families=plan['evaluation']['families'].values()
                td[tile]=sum(sum(100*(a['tiles'][c][tile]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']-sel[ref]['tiles'][c][tile]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']) for c in cc)/len(cc) for cc in families)/4
            else:
                td[tile]=sum(100*(a['tiles'][c][tile]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']-sel[ref]['tiles'][c][tile]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']) for c in cs)/len(cs)
        tile_deltas[name]=td;checks['both_tiles_positive_'+name]=all(d>0 for d in td.values())
    for c in ('clean','dsm_missing','rgb_missing'):checks[c+'_floor']=difference(a,b,[c])>=-.1-1e-9
    checks['worst_floor']=worst(a,b,plan['evaluation']['primary'])>=-.2-1e-9
    return dict(primary_candidate='N2-3',passed=all(checks.values()),checks=checks,deltas_pp=deltas,
        tile_deltas_pp=tile_deltas,scores_pp={j:score(sel[j],plan) for j in N2},
        fixed8000_scores_pp={j:score(fix[j],plan) for j in N2},
        harm_and_retention={j:retention(sel[j],plan['evaluation']['primary']) for j in N2},
        base='N1-2',observed_at=now(),single_seed_development=True,new_contribution_established=False,
        test6_loaded=False,independent_final_loaded=False)
def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args()
    base=a.directory.resolve();base.relative_to(Path('/home/jovyan/zzx'))
    plan=read(base/'plan.json');validate_plan(plan)
    result=screen({j:cell(base,j,plan) for j in N2},plan)
    write(base/'n2_screen.json',result)
    print('POST_AB_N2_SCREEN',result['passed'],result['deltas_pp'],flush=True)
if __name__=='__main__':main()
