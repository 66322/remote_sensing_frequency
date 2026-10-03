"""Fixed development screens. Old D27/D28/D30 gates remain unchanged."""
import argparse,csv
from pathlib import Path
import numpy as np
from post_d30_common import read,write,sha,now,validate_plan,PHASES
from post_d30_evaluation import metric,decode_joint,joint_report

def value(s,c,name='candidate'):
    return 100*s['pooled'][c]['noboundary']['metrics'][name]['valid']['mIoU_fg5']
def mean(s,conditions,name='candidate'):return sum(value(s,c,name) for c in conditions)/len(conditions)
def score(s,plan):
    row={n:mean(s,cs) for n,cs in plan['evaluation']['families'].items()};row['S_available']=sum(row.values())/4
    return row
def difference(a,b,cs):return mean(a,cs)-mean(b,cs)
def worst(a,b,cs):
    return min(100*(ar['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']-b['tiles'][c][tile]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']) for c in cs for tile,ar in a['tiles'][c].items())
def retention(s,cs):
    joint=sum((decode_joint(row['scopes']['noboundary']['joint']['both']) for c in cs for row in s['tiles'][c].values()),np.zeros((6,)*4,np.int64))
    g,r,d,f=np.indices((6,)*4);rep=joint_report(joint);rates={}
    for name,p in (('rgb',r),('dsm',d)):
        denom=int(joint[p==g].sum());harm=int(joint[(p==g)&(f!=g)].sum())
        rates[name]=harm/denom if denom else None
    return dict(retentions={n:rep['only_'+n+'_correct']['retention'] for n in ('rgb','dsm')},harm=rates,joint_report=rep)
def safety(a,b,plan):
    cs=plan['evaluation']['primary'];ra,rb=retention(a,cs),retention(b,cs)
    keep={n:(ra['retentions'][n] is not None and rb['retentions'][n] is not None and 100*(ra['retentions'][n]-rb['retentions'][n])>=-.5-1e-9) for n in ('rgb','dsm')}
    harm={n:ra['harm'][n] is not None and rb['harm'][n] is not None and ra['harm'][n]<=rb['harm'][n]+1e-12 for n in ('rgb','dsm')}
    return dict(clean=difference(a,b,['clean'])>=-.1-1e-9,worst_tile=worst(a,b,cs)>=-.2-1e-9,**{'keep_'+n:v for n,v in keep.items()},**{'harm_'+n:v for n,v in harm.items()})
def passed(checks):return all(bool(x) for x in checks.values())

def screen(data,plan):
    out={};sel=data['selected'];fix=data['fixed8000'];primary=plan['evaluation']['primary'];geo=plan['design']['geometry_conditions']
    S=lambda s:score(s,plan)['S_available']
    if all(n in sel for n in PHASES['A']):
        a=sel['A2'];b=sel['A0'];checks=safety(a,b,plan)
        checks.update(vs_plain=S(a)-S(b)>=.2-1e-9,vs_all=S(a)-S(sel['A1'])>=.2-1e-9,vs_shuffled=S(a)-S(sel['A3'])>=.1-1e-9,fixed_same_sign=S(fix['A2'])>S(fix['A0']))
        out['A2']=dict(passed=passed(checks),checks=checks,delta_vs_plain_pp=S(a)-S(b),delta_vs_all_pp=S(a)-S(sel['A1']))
    if all(n in sel for n in ['A0']+PHASES['B']):
        a=sel['B3'];b=sel['B1'];checks=safety(a,sel['A0'],plan)
        # B retention comparison is augmentation-only B1 as specified in the accepted plan.
        retain_checks=safety(a,b,plan);checks['keep_rgb']=retain_checks['keep_rgb'];checks['keep_dsm']=retain_checks['keep_dsm']
        per_tile={tile:sum(100*(a['tiles'][c][tile]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']-b['tiles'][c][tile]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']) for c in geo)/len(geo) for tile in plan['data']['validation']}
        checks.update(vs_augmentation=difference(a,b,geo)>=.5-1e-9,vs_shuffle=difference(a,sel['B4'],geo)>=.2-1e-9,
                      each_tile_positive=all(v>0 for v in per_tile.values()),old_composite=S(a)-S(sel['A0'])>=-.1-1e-9,fixed_same_sign=difference(fix['B3'],fix['B1'],geo)>0)
        out['B3']=dict(passed=passed(checks),checks=checks,geometry_vs_augmentation_pp=difference(a,b,geo),geometry_vs_shuffle_pp=difference(a,sel['B4'],geo),per_tile_pp=per_tile)
    if all(n in sel for n in PHASES['C']):
        checks={};deltas={}
        for available in ('rgb','dsm'):
            cs=plan['design']['C_conditions'][available];a=sel['C2'];deltas[available]={n:difference(a,sel[n],cs) for n in ('C0','C1','C3')}
            checks.update({available+'_vs_'+n:v>=.3-1e-9 for n,v in deltas[available].items()})
            checks[available+'_anchor_floor']=mean(a,cs)-mean(a,cs,'fixed_'+available)>=-.1-1e-9
            checks[available+'_worst_tile']=worst(a,sel['C0'],cs)>=-.2-1e-9
            checks[available+'_fixed_same_sign']=difference(fix['C2'],fix['C0'],cs)>0
        out['C2']=dict(passed=passed(checks),checks=checks,deltas_pp=deltas)
    if all(n in sel for n in PHASES['F']):
        a=sel['F1'];b=sel['F0'];checks=safety(a,b,plan)
        checks.update(composite=S(a)-S(b)>=.2-1e-9,fixed_same_sign=S(fix['F1'])>S(fix['F0']))
        out['F1']=dict(passed=passed(checks),checks=checks,delta_pp=S(a)-S(b),band_ablation_deltas_pp={n:S(a)-S(sel[n]) for n in ('F2','F3')})
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();base=a.directory.resolve();base.relative_to(Path('/home/jovyan/zzx'))
    plan=read(base/'plan.json');validate_plan(plan);data={'selected':{},'fixed8000':{}};report={}
    for job in plan['jobs']:
        name=job['id'];folder=base/'jobs'/name
        if not (folder/'complete.json').exists():continue
        complete=read(folder/'complete.json')
        if complete['signature']['execution_commit']!=plan['execution_commit'] or complete['signature']['plan_sha256']!=sha(base/'plan.json') or complete['global_step']!=8000:raise RuntimeError('job completion binding differs '+name)
        if sha(folder/'selected.pth')!=complete['selected_checkpoint_sha256']:raise RuntimeError('selected checkpoint changed '+name)
        report[name]={}
        for age,tag in (('selected','evaluation'),('fixed8000','fixed8000')):
            path=folder/tag/'summary.json'
            if sha(path)!=complete[tag+'_summary_sha256']:raise RuntimeError('summary binding changed '+name)
            s=read(path);data[age][name]=s
            if s['binding']['training']!=complete['signature'] or s['test6_loaded']:raise RuntimeError('summary signature differs')
            report[name][age]=dict(scores_pp=score(s,plan),selected_step=complete['selected']['step'],retention=retention(s,plan['evaluation']['primary']),geometry_mean_pp=mean(s,plan['design']['geometry_conditions']),
                missing_mean_pp={n:mean(s,cs) for n,cs in plan['design']['C_conditions'].items()},
                clean_class_IoU=s['pooled']['clean']['full']['metrics']['candidate']['valid']['IoU'],
                label_boundary_IoU=s['pooled']['clean']['full']['metrics']['candidate']['label_boundary']['IoU'])
    result=dict(status='COMPLETE' if len(report)==22 else 'MAIN_COMPLETE' if len(report)>=18 else 'PARTIAL',observed_at=now(),jobs=report,screens=screen(data,plan),
                completed_jobs=len(report),conditional_F_policy='only frozen B3 passes',single_seed_development=True,test6_loaded=False,independent_final_loaded=False,new_contribution_established=False)
    write(base/'portfolio_screen.json',result)
    with (base/'results.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['job','age','C','QR','QD','QJ','S_available','geometry_mean_pp','remaining_rgb_pp','remaining_dsm_pp'])
        for j,ages in report.items():
            for age,row in ages.items():w.writerow([j,age]+[row['scores_pp'][n] for n in ('C','QR','QD','QJ','S_available')]+[row['geometry_mean_pp'],row['missing_mean_pp']['rgb'],row['missing_mean_pp']['dsm']])
    print('PORTFOLIO_SCREEN',len(report),'B3_pass=',result['screens'].get('B3',{}).get('passed',False),flush=True)
if __name__=='__main__':main()
