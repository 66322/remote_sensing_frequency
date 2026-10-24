"""Compact pooled pressure report; tile records retain the complete raw counts."""
import argparse,csv
from pathlib import Path
import numpy as np
from d27_common import read,write,sha,now
from d27_evaluation import metric,decode_joint,joint_report
from d28_pressure import pool_cm
from launch_rebuild_v1_d28 import MODELS

def aggregate(records):
    cm=pool_cm([r['metric']['cm'] for r in records]);joint=np.sum([decode_joint(r['joint']) for r in records],axis=0,dtype=np.int64)
    return dict(metric=metric(cm),joint_report=joint_report(joint))
def score(row):return row['metric']['mIoU_fg5']*100
def retention(row,name):return row['joint_report'][name]['retention']
def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args();base=a.directory.resolve();base.relative_to(Path('/home/jovyan/zzx'));plan=read(base/'plan.json');bindings=read(base/'checkpoint_binding.json')
    missing=[n for n in MODELS if not (base/'jobs'/n/'complete.json').exists()]
    if missing:write(base/'screen_result.json',dict(status='INCOMPLETE_NO_SCIENTIFIC_GATE',missing=missing,test6_loaded=False));return 2
    rows={};tile_metrics={};clean_checks={};records_index={};parent=Path(plan['predecessor_directory']);d26=Path(read(parent/'plan.json')['predecessor_directory'])
    for name in MODELS:
        rows[name]={};tile_metrics[name]={};records_index[name]={}
        for recipe in ('P1','P2'):
            for level in ('mild','strong'):
                cell=recipe+'_'+level;cases={}
                for pair in ('00','01','10','11'):
                    cases[pair]={}
                    for tile in ('3_11','5_10'):
                        path=base/'jobs'/name/'evaluation'/(cell+'_'+pair)/(tile+'.json');row=read(path)
                        if row['binding']['signature']['checkpoint']!=bindings['models'][name]:raise RuntimeError('result/checkpoint differs')
                        # Same stressed frozen anchors across all seven models, not clean anchors.
                        reference=read(base/'jobs/RGB_anchor/evaluation'/(cell+'_'+pair)/(tile+'.json'))
                        if any(row['predictions'][n]!=reference['predictions'][n] for n in ('rgb','dsm')):raise RuntimeError('frozen reference predictions differ')
                        cases[pair][tile]=row['scopes'];records_index[name][str(path.relative_to(base))]=sha(path)
                rows[name][cell]={};tile_metrics[name][cell]={}
                for regime,pairs in (('shared',['00','11']),('independent',['00','01','10','11'])):
                    rows[name][cell][regime]={scope:{region:aggregate([cases[pair][tile][scope][region] for pair in pairs for tile in ('3_11','5_10')]) for region in ('valid','untouched','only_rgb_damaged','only_dsm_damaged','both_damaged')} for scope in ('full','noboundary')}
                    tile_metrics[name][cell][regime]={tile:aggregate([cases[pair][tile]['noboundary']['valid'] for pair in pairs]) for tile in ('3_11','5_10')}
        if name in ('D26_B0','D27_S1','D27_G0','D27_G1','D27_L1'):
            folder=(d26 if name=='D26_B0' else parent)/'jobs'/name.split('_',1)[1]
            deltas=[]
            for tile in ('3_11','5_10'):
                original=read(folder/'evaluation/clean'/(tile+'.json'))['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']
                current=read(base/'jobs'/name/'evaluation/clean'/(tile+'.json'))['scopes']['noboundary']['valid']['metric']['mIoU_fg5']
                deltas.append((current-original)*100)
            clean_checks[name]=dict(delta_pp=deltas,passed=all(abs(d)<=1e-6 for d in deltas))
    means=lambda name,regime:sum(score(c[regime]['noboundary']['valid']) for c in rows[name].values())/4
    tilemean=lambda name,regime,tile:sum(score(c[regime][tile]) for c in tile_metrics[name].values())/4
    gaps=[score(c['independent']['noboundary']['valid'])-score(c['shared']['noboundary']['valid']) for c in rows['D26_B0'].values()]
    tilegaps={t:tilemean('D26_B0','independent',t)-tilemean('D26_B0','shared',t) for t in ('3_11','5_10')}
    phenomenon=dict(mean_gap_pp=sum(gaps)/4,cell_gaps_pp=gaps,tile_gaps_pp=tilegaps,passed=sum(gaps)/4>=.3 and sum(v>0 for v in gaps)>=3 and all(v>0 for v in tilegaps.values()))
    original=read(parent/'screen_result.json');gates=original.get('screen',{});comparisons={}
    for candidate,controls in (('D27_G1',['D27_G0','D27_S1']),('D27_L1',['D27_G1'])):
        for control in controls:
            shared=means(candidate,'shared')-means(control,'shared');ind=means(candidate,'independent')-means(control,'independent')
            tg={t:tilemean(candidate,'shared',t)-tilemean(control,'shared',t) for t in ('3_11','5_10')}
            retention_deltas={}
            for unique in ('only_rgb_correct','only_dsm_correct'):
                vals={}
                for model in (candidate,control):
                    reports=[c['shared']['noboundary']['valid']['joint_report'][unique] for c in rows[model].values()]
                    total=sum(r['valid'] for r in reports);correct=sum(r['fused_correct'] for r in reports);vals[model]=100*correct/total if total else None
                retention_deltas[unique]=None if None in vals.values() else vals[candidate]-vals[control]
            gate_name='safety' if control=='D27_G0' else 'dynamic_routing' if control=='D27_S1' else 'local'
            prior_pass=gates.get(gate_name,{}).get('passed',False)
            pressure_pass=shared>=.2 and ind>=-.1 and min(tg.values())>=-.2 and all(v is not None and v>=-.5 for v in retention_deltas.values())
            comparisons[candidate+'-'+control]=dict(shared_gain_pp=shared,independent_gain_pp=ind,gain_drop_pp=ind-shared,tile_shared_gains_pp=tg,unique_retention_deltas_pp=retention_deltas,original_D27_gate=gate_name,original_gate_passed=prior_pass,pressure_gate_passed=pressure_pass,eligible_for_further_design=pressure_pass and prior_pass)
    valid=all(r['passed'] for r in clean_checks.values())
    g1_b0_drop=(means('D27_G1','independent')-means('D26_B0','independent'))-(means('D27_G1','shared')-means('D26_B0','shared'))
    for c in comparisons.values():c['eligible_for_further_design'] &= valid and phenomenon['passed']
    result=dict(status='COMPLETE' if valid else 'BINDING_REPRODUCTION_FAILURE',scores_pp={n:{r:means(n,r) for r in ('shared','independent')} for n in MODELS},phenomenon=phenomenon,comparisons=comparisons,clean_checks=clean_checks,aggregate=rows,tile_metrics=tile_metrics,record_sha256=records_index,observed_at=now(),test6_loaded=False,new_training=False,D29_automatically_started=False,independent_replication_unit='two repeatedly exposed development tiles; support pairs are repeated evaluations, not independent samples')
    result['G1_B0_transfer_diagnostic']=dict(gain_drop_pp=g1_b0_drop,threshold_pp=.2,threshold_met=g1_b0_drop>=.2,causal_routing_attribution=False)
    write(base/'screen_result.json',result)
    with (base/'results.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['model','shared','independent']);writer.writeheader();writer.writerows(dict(model=n,**r) for n,r in result['scores_pp'].items())
    print('D28_SCREEN',result['status'],phenomenon,flush=True);return 0 if valid else 2
if __name__=='__main__':raise SystemExit(main())
