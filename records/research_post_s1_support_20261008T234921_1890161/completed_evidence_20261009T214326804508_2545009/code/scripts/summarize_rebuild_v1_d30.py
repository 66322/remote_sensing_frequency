"""D30 continuous paired effects and predeclared development allocation screen."""
import argparse,csv
from pathlib import Path
import numpy as np
from d30_common import read,write,sha,now,validate_plan,TRAIN_IDS
from d27_evaluation import metric,decode_joint,joint_report
from summarize_rebuild_v1_d27 import scores,harm_rate

def summary(folder,tag,plan,expected_signature=None):
    tiles={};pooled={}
    for condition in plan['evaluation']['primary']:
        tiles[condition]={}
        for tile in plan['data']['validation']:
            row=read(folder/tag/condition/(tile+'.json'))
            if expected_signature is not None and row['binding']['training']!=expected_signature:raise RuntimeError('tile training binding differs')
            if row['confusion_matrix_dtype']!='int64':raise RuntimeError('raw counts must be int64')
            tiles[condition][tile]=row
        pooled[condition]={}
        for scope in ('full','noboundary'):
            cm=sum(np.asarray(r['scopes'][scope]['metrics']['candidate']['valid']['cm'],np.int64) for r in tiles[condition].values())
            if cm.shape!=(6,6) or (cm<0).any():raise RuntimeError('invalid confusion matrix')
            pooled[condition][scope]=dict(metrics={'candidate':{'valid':metric(cm)}})
    return dict(tiles=tiles,pooled=pooled)

def describe(s,plan):
    parts=scores(s,plan);conditions=plan['evaluation']['primary']
    joint=sum((decode_joint(r['scopes']['noboundary']['joint']['both']) for c in conditions for r in s['tiles'][c].values()),np.zeros((6,)*4,np.int64))
    rep=joint_report(joint)
    return dict(scores_pp=parts,only_rgb_correct=rep['only_rgb_correct'],only_dsm_correct=rep['only_dsm_correct'],
                QD_harm=harm_rate(s,plan['evaluation']['families']['QD']),
                clean_class_IoU=metric(sum(np.asarray(r['scopes']['noboundary']['metrics']['candidate']['valid']['cm'],np.int64) for r in s['tiles']['clean'].values()))['IoU'])

def paired(a,b,plan):
    values={}
    for condition in plan['evaluation']['primary']:
        values[condition]={}
        for tile in plan['data']['validation']:
            ar=a['tiles'][condition][tile];br=b['tiles'][condition][tile]
            for name in ('fixed_rgb','fixed_dsm','fixed_probability_average','fixed_availability_switch'):
                if ar['predictions'][name]!=br['predictions'][name]:raise RuntimeError('comparison frozen references differ')
            values[condition][tile]=100*(ar['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']-br['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5'])
    return dict(tile_condition_deltas_pp=values,worst_delta_pp=min(v for row in values.values() for v in row.values()))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();base=a.directory.resolve();base.relative_to(Path('/home/jovyan/zzx'))
    plan=read(base/'plan.json');validate_plan(plan);reuse=read(base/'reuse_binding.json')
    for path,row in reuse['files'].items():
        if sha(base/path)!=row['sha256']:raise RuntimeError('reused raw record changed')
    all_ids=('S0','S1')+TRAIN_IDS;data={};report={}
    for age,tag in (('selected','evaluation'),('fixed8000','fixed8000')):
        data[age]={};report[age]={}
        for arm in all_ids:
            folder=base/'reused'/arm if arm in ('S0','S1') else base/'jobs'/arm
            signature=read(folder/'complete.json')['signature'] if arm not in ('S0','S1') else None
            s=summary(folder,tag,plan,signature);data[age][arm]=s;report[age][arm]=describe(s,plan)
        for arm in all_ids[1:]:paired(data[age][arm],data[age]['S0'],plan)
    comparisons={}
    for arm in TRAIN_IDS:
        control='S0' if arm in ('P','R') else 'S1'
        comparison={}
        for age in data:
            ar=report[age][arm];br=report[age][control]
            comparison[age]=dict(control=control,score_deltas_pp={k:ar['scores_pp'][k]-br['scores_pp'][k] for k in ar['scores_pp']},
                                 **paired(data[age][arm],data[age][control],plan))
        comparisons[arm]=comparison
    interaction={age:{k:report[age]['S1']['scores_pp'][k]-report[age]['P']['scores_pp'][k]-report[age]['R']['scores_pp'][k]+report[age]['S0']['scores_pp'][k] for k in report[age]['S0']['scores_pp']} for age in report}
    screen={}
    for arm in TRAIN_IDS:
        ar=report['selected'][arm];br=report['selected']['S0'];pairs=paired(data['selected'][arm],data['selected']['S0'],plan)
        delta=ar['scores_pp']['S_available']-br['scores_pp']['S_available']
        clean=ar['scores_pp']['C']-br['scores_pp']['C']
        final=report['fixed8000'][arm]['scores_pp']['S_available']-report['fixed8000']['S0']['scores_pp']['S_available']
        ha,hb=ar['QD_harm']['rate'],br['QD_harm']['rate']
        checks=dict(composite=delta>=.2-1e-9,clean=clean>=-.1-1e-9,worst=pairs['worst_delta_pp']>=-.2-1e-9,harm=ha is not None and hb is not None and ha<=hb+1e-12,fixed_same_sign=final>0)
        screen[arm]=dict(passed=all(checks.values()),checks=checks,selected_delta_pp=delta,clean_delta_pp=clean,fixed8000_delta_pp=final,**pairs)
    replay={}
    for arm in ('G0','G1'):
        folder=base/'jobs'/('replay_'+arm);rows={}
        for mode in ('original_reused','uniform','expert0','expert1','expert2'):
            for c in ('clean','rgb_down4','aux_noise_std010'):
                path=lambda tile:folder/'original_reused'/c/(tile+'.json') if mode=='original_reused' else folder/'modes'/mode/'evaluation'/c/(tile+'.json')
                tile_rows=[read(path(t)) for t in plan['data']['validation']]
                cm=sum(np.asarray(r['scopes']['noboundary']['metrics']['candidate']['valid']['cm'],np.int64) for r in tile_rows)
                joint=sum((decode_joint(r['scopes']['noboundary']['joint']['both']) for r in tile_rows),np.zeros((6,)*4,np.int64))
                rows.setdefault(mode,{})[c]=dict(mIoU_fg5_pp=100*metric(cm)['mIoU_fg5'],joint_report=joint_report(joint))
        replay[arm]=rows
    result=dict(status='COMPLETE',training=report,comparisons=comparisons,factorial_interaction_pp=interaction,
                continuation_screen=screen,checkpoint_interventions=replay,observed_at=now(),test6_loaded=False,independent_final_loaded=False,
                interpretation='single seed development diagnosis, no significance/novelty claim; original D27 gates remain failed',D29_started=False)
    write(base/'screen_result.json',result)
    with (base/'results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['age','job','C','QR','QD','QJ','S_available']);w.writeheader()
        for age,arms in report.items():
            for arm,row in arms.items():w.writerow(dict(age=age,job=arm,**row['scores_pp']))
    for arm in TRAIN_IDS:print('D30_RESULT',arm,report['selected'][arm]['scores_pp'],'continue='+str(screen[arm]['passed']),flush=True)
    print('D30_SCREEN_COMPLETE original_D27_gates_unchanged',flush=True);return 0
if __name__=='__main__':raise SystemExit(main())

