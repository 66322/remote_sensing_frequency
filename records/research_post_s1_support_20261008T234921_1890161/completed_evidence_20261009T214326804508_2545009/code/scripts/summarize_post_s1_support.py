"""Standalone raw-matrix audit and prospective P7/E/Q screens. No training."""
import argparse
from pathlib import Path
import numpy as np
from post_s1_support_common import *
from post_d30_evaluation import metric,decode_joint
def verify_summary(path):
    s=read(path)
    if s['test6_loaded'] or s['independent_final_loaded']:raise RuntimeError('forbidden split')
    for key,rows in s['tiles'].items():
        if set(rows)!={'3_11','5_10'}:raise RuntimeError('Val2 membership differs')
        sample=next(iter(rows.values()))
        for scope in ('full','noboundary'):
            for name,regions in sample['scopes'][scope]['metrics'].items():
                for region in regions:
                    cms=[]
                    for row in rows.values():
                        r=row['scopes'][scope]['metrics'][name][region];cm=np.asarray(r['cm'])
                        if cm.shape!=(6,6) or cm.dtype.kind not in 'iu' or (cm<0).any() or metric(cm)!=r:raise RuntimeError('raw metrics mismatch')
                        cms.append(cm.astype(np.int64))
                    if metric(sum(cms,np.zeros((6,6),np.int64)))!=s['pooled'][key][scope]['metrics'][name][region]:raise RuntimeError('pooled metrics mismatch')
            for region in sample['scopes'][scope]['joint']:
                arrays=[]
                for row in rows.values():
                    v=decode_joint(row['scopes'][scope]['joint'][region]);arrays.append(v)
                    for axes,name in [((1,2),'candidate'),((2,3),'fixed_rgb'),((1,3),'fixed_dsm')]:
                        if not np.array_equal(v.sum(axes),np.asarray(row['scopes'][scope]['metrics'][name][region]['cm'],np.int64)):raise RuntimeError('raw joint marginal mismatch')
                if not np.array_equal(sum(arrays,np.zeros((6,)*4,np.int64)),decode_joint(s['pooled'][key][scope]['joint'][region])):raise RuntimeError('raw joint pool mismatch')
    return s
def score(s,key,tile=None):
    row=s['tiles'][key][tile]['scopes']['noboundary'] if tile else s['pooled'][key]['noboundary']
    value=row['metrics']['candidate']['valid']['mIoU_fg5']
    if value is None:raise RuntimeError('undefined primary score')
    return 100*value
def compare(a,b,key,floor,both_positive=False):
    tiles={t:score(a,key,t)-score(b,key,t) for t in ('3_11','5_10')}
    delta=score(a,key)-score(b,key)
    return dict(pooled_gain_pp=delta,tile_gains_pp=tiles,threshold_pp=floor,
        passed=bool(delta>=floor-1e-9 and (not both_positive or all(v>0 for v in tiles.values()))))
def screens(p,ordinary,U,E,D1,base_ordinary,base_U,route_U):
    g=p['design']['gates'];fixed=U['P7']
    rgb=dict(base=compare(fixed,base_U,'rgb_U',g['rgb_base_pp'],True),
        **{j:compare(fixed,U[j],'rgb_U',g['mechanism_pp'],True) for j in ('P6','P8','P9')},
        R0=compare(fixed,route_U,'rgb_U',g['route_floor_pp']))
    protect={k:compare(ordinary['P7'],base_ordinary,k,g['clean_missing_floor_pp']) for k in ('clean','rgb_missing','dsm_missing')}
    worst_rows=[dict(condition=k,tile=t,gain_pp=score(ordinary['P7'],k,t)-score(base_ordinary,k,t)) for k in p['evaluation']['primary'] for t in p['data']['validation']]
    worst=min(worst_rows,key=lambda x:x['gain_pp'])
    dsm=compare(fixed,base_U,'dsm_U',g['dsm_U_floor_pp'])
    passed=all(x['passed'] for x in rgb.values()) and all(x['passed'] for x in protect.values()) and worst['gain_pp']>=g['worst_tile_floor_pp']-1e-9 and dsm['passed']
    stress={k:compare(E['P7'],E['S1-0'],k,g['clean_missing_floor_pp']) for k in E_KEYS}
    stress_worst=min((dict(condition=k,tile=t,gain_pp=score(E['P7'],k,t)-score(E['S1-0'],k,t)) for k in E_KEYS for t in p['data']['validation']),key=lambda x:x['gain_pp'])
    shape={k:compare(E['P7'],E['S1-0'],k,g['E_shape_gain_pp'],True) for k in E_KEYS if k.endswith('__clean')}
    epass=all(x['passed'] for x in stress.values()) and all(x['passed'] for x in shape.values()) and stress_worst['gain_pp']>=g['worst_tile_floor_pp']-1e-9
    signal=compare(D1['S1-0/A1B0C0'],D1['S1-0/A1B1C1'],'dsm_U',g['D1_DSM_signal_pp'],True)
    per_arm={}
    for j in ['P'+str(i) for i in range(10)]:
        per_arm[j]=dict(rgb_U=score(U[j],'rgb_U'),dsm_U=score(U[j],'dsm_U'),
            S_available=sum(score(ordinary[j],k) for k in p['evaluation']['primary'])/len(p['evaluation']['primary']),
            primary_candidate=j=='P7')
    factors={}
    for name,pairs in {'freeze_vs_shared':[('P4','P0'),('P5','P1'),('P6','P2'),('P7','P3')],
        'context_vs_mask':[('P1','P0'),('P3','P2'),('P5','P4'),('P7','P6')],
        'local_vs_global':[('P2','P0'),('P3','P1'),('P6','P4'),('P7','P5')]}.items():
        factors[name]={a+'-'+b:{key:compare(U[a],U[b],key,0.) for key in ('rgb_U','dsm_U')} for a,b in pairs}
    return dict(P7_passed=bool(passed),P7=dict(rgb=rgb,protection=protect,worst_primary_tile=worst,dsm_U=dsm),
        E_passed=bool(epass),E=dict(protection=stress,worst_tile=stress_worst,new_shape_gain=shape,
            P7_vs_R0={k:compare(E['P7'],E['R0'],k,g['route_floor_pp']) for k in E_KEYS}),
        D1_DSM_signal=signal,Q_status='ELIGIBLE_AWAITING_FROZEN_PROTOCOL' if passed and epass and signal['passed'] else 'SKIPPED_GATE',
        Q_auto_training=False,per_arm=per_arm,paired_factor_effects=factors,bilateral_candidate=False,
        contribution_status='numerical development gates only; cost and independent generalization assessed separately',
        scope='Val2 seed42 development evidence; no independent generalization')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();base=a.directory.resolve()
    p=validate(read(base/'plan.json'));root=Path(p['source_directory']).parent.parent;verify_snapshot(base)
    ordinary={};U={};E={};D1={}
    for task in ['D1']+ORDER+['E']:accept_worker(base,task,p)
    for j in ORDER:
        ordinary[j]=verify_summary(base/'jobs'/j/'evaluation/summary.json')
        U[j]=verify_summary(base/'jobs'/j/'support_evaluation/summary.json')
    d=read(base/'jobs/D1/summary.json')
    for name,row in d['records'].items():
        path=within(row['path'],base)
        if sha(path)!=row['sha256']:raise RuntimeError('D1 index differs')
        D1[name]=verify_summary(path)
    e=read(base/'jobs/E/summary.json')
    for name,row in e['records'].items():
        path=within(row['path'],base)
        if sha(path)!=row['sha256']:raise RuntimeError('E index differs')
        E[name]=verify_summary(path)
    source_binding(root,'S1-0',checkpoint=False)
    ref=root/'records'/SOURCE_NAME/'jobs/S1-0'
    s=screens(p,ordinary,U,E,D1,verify_summary(ref/'evaluation/summary.json'),verify_summary(ref/'support_evaluation/summary.json'),
        verify_summary(base/'R0_U/summary.json'))
    # Cost comparison is a required boundary, not inferred from accuracy.
    s['cost_evidence']={j:dict(capacity=read(base/'jobs'/j/'model_capacity.json'),
        last_progress=read(base/'jobs'/j/'progress.json')) for j in ORDER}
    s['E_inference_cost']={j:{k:{t:E[j]['tiles'][k][t].get('cost') for t in p['data']['validation']} for k in E_KEYS} for j in ['S1-0','S1-3']+ORDER}
    s['R0_E_serial_inference_seconds']={k:{t:sum(E[j]['tiles'][k][t].get('cost',{}).get('candidate_native_tile_inference_seconds',0.) for j in ('S1-0','S1-3')) for t in p['data']['validation']} for k in E_KEYS}
    s['cost_assessment']='R0 requires two full model forwards plus cheap splice; candidate-only native tile times and trainable parameters reported; matching accuracy alone is engineering evidence'
    s.update(plan_sha256=sha(base/'plan.json'),mask_manifest_sha256=sha(base/'mask_manifest.json'),observed_at=now(),
        fixed8000=True,new_optimizer_updates=80000,Test6_read=False,automatic_followup=False)
    write(base/'support_screen.json',s)
    print('SUPPORT_SCREEN',s['P7_passed'],s['E_passed'],s['Q_status'],flush=True)
if __name__=='__main__':main()
