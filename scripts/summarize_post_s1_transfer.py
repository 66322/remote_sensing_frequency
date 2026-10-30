"""Raw integer audit, fixed T7 acceptance and descriptive factorial effects."""
import argparse
from pathlib import Path
from post_s1_transfer_common import *
from summarize_post_s1_support import verify_summary,score,compare

def screens(p,ordinary,U,E,initial,refs):
    g=p['design']['gates'];fixed=U['T7']
    contrasts={j:compare(fixed,U[j],'rgb_U',g['matched_pp'],True) for j in ('T1','T6','T9')}
    contrasts['base']=compare(fixed,refs['base_U'],'rgb_U',g['base_pp'],True)
    contrasts['R0']=compare(fixed,refs['R0_U'],'rgb_U',g['route_floor_pp'])
    protect={k:compare(ordinary['T7'],refs['base_ordinary'],k,g['protect_floor_pp']) for k in ('clean','rgb_missing','dsm_missing')}
    worst=min((dict(condition=k,tile=t,gain_pp=score(ordinary['T7'],k,t)-score(refs['base_ordinary'],k,t)) for k in p['evaluation']['primary'] for t in p['data']['validation']),key=lambda r:r['gain_pp'])
    dsm=compare(fixed,refs['base_U'],'dsm_U',g['protect_floor_pp'])
    shape={k:compare(E['T7'],refs['E_S1-0'],k,g['shape_pp'],True) for k in E_KEYS if k.endswith('__clean')}
    stress={k:compare(E['T7'],refs['E_S1-0'],k,g['protect_floor_pp']) for k in E_KEYS}
    route_stress={k:compare(E['T7'],refs['E_R0'],k,g['route_floor_pp']) for k in E_KEYS}
    stress_worst=min((dict(condition=k,tile=t,gain_pp=score(E['T7'],k,t)-score(refs['E_S1-0'],k,t)) for k in E_KEYS for t in p['data']['validation']),key=lambda r:r['gain_pp'])
    numerical=all(v['passed'] for v in contrasts.values()) and all(v['passed'] for v in protect.values()) and dsm['passed'] and worst['gain_pp']>=g['worst_tile_floor_pp']
    epass=all(v['passed'] for group in (shape,stress,route_stress) for v in group.values()) and stress_worst['gain_pp']>=g['worst_tile_floor_pp']
    pairs={f'T{2*i+1}-T{2*i}':compare(U[f'T{2*i+1}'],U[f'T{2*i}'],'rgb_U',0.) for i in range(5)}
    return dict(T7_passed=bool(numerical and epass),U_passed=bool(numerical),E_passed=bool(epass),
        T7=dict(contrasts=contrasts,protection=protect,worst_primary_tile=worst,dsm_U=dsm),
        E=dict(shape=shape,protection=stress,route=route_stress,worst_tile=stress_worst),
        per_arm={j:dict(donor=job_card(j)['donor'],context=job_card(j)['support_preserved'],
            initial_rgb_U=score(initial[j],'rgb_U'),rgb_U=score(U[j],'rgb_U'),dsm_U=score(U[j],'dsm_U'),
            new_training_gain_pp=score(U[j],'rgb_U')-score(initial[j],'rgb_U'),
            S_available=sum(score(ordinary[j],k) for k in p['evaluation']['primary'])/len(p['evaluation']['primary'])) for j in ORDER},
        paired_context_effects=pairs,
        initialization_effects={f'T{i}-T{8+i%2}':compare(U[f'T{i}'],U[f'T{8+i%2}'],'rgb_U',0.) for i in range(8)},
        donor_context_interactions={f'S1-{i}_vs_S1-0':pairs[f'T{2*i+1}-T{2*i}']['pooled_gain_pp']-pairs['T1-T0']['pooled_gain_pp'] for i in (1,2,3)},
        old_P7=compare(fixed,refs['P7_U'],'rgb_U',0.),
        scope='Potsdam Val2 seed42 development; no independent confirmation; repeated E stress',
        contribution_status='private frozen decoder transfer is an adaptation control, not a novelty claim',
        automatic_followup=False,new_optimizer_updates=80000,test6_loaded=False,independent_final_loaded=False)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();base=a.directory.resolve()
    p=validate(read(base/'plan.json'));verify_snapshot(base)
    for j in ORDER:accept_worker(base,j,p)
    sets={tag:{j:verify_summary(base/'jobs'/j/tag/'summary.json') for j in ORDER} for tag in ('evaluation','support_evaluation','stress_evaluation','initial_evaluation')}
    idx=read(base/'reference_index.json');prep=read(base/'preparation_complete.json')
    if sha(base/'reference_index.json')!=prep['reference_index_sha256']:raise RuntimeError('reference index changed')
    refs={}
    for name,row in idx.items():
        path=within(row['path'],base)
        if sha(path)!=row['sha256']:raise RuntimeError('reference summary changed')
        refs[name]=verify_summary(path)
    r=screens(p,sets['evaluation'],sets['support_evaluation'],sets['stress_evaluation'],sets['initial_evaluation'],refs)
    r['capacity']={j:read(base/'jobs'/j/'model_capacity.json') for j in ORDER}
    r['candidate_inference_seconds']={j:{k:{t:sets['stress_evaluation'][j]['tiles'][k][t]['cost']['candidate_native_tile_inference_seconds'] for t in p['data']['validation']} for k in E_KEYS} for j in ORDER}
    r['historical_R0_serial_seconds']={k:{t:sum(refs['E_'+n]['tiles'][k][t]['cost']['candidate_native_tile_inference_seconds'] for n in ('S1-0','S1-3')) for t in p['data']['validation']} for k in E_KEYS}
    r['cost_boundary']='same server historical E serial timing; not simultaneous benchmark or guaranteed speedup; no second expert pass in candidate'
    r.update(plan_sha256=sha(base/'plan.json'),observed_at=now())
    write(base/'transfer_screen.json',r);print('TRANSFER_SCREEN',r['T7_passed'],flush=True)
if __name__=='__main__':main()
