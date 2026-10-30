"""Development-only matched comparisons; missing/failed controls stay undecidable."""
import argparse
import csv
from pathlib import Path
import numpy as np
from d24_common import read,write,now,within

RGB=('rgb_down2','rgb_down4','rgb_blur5','rgb_local_down4_q1')
AUX=('aux_down4','aux_noise_std010')
AVAILABLE=('clean',)+RGB+AUX+('rgb_contrast060','aux_shift8')

def metric(summary,condition,name='candidate',tile=None):
    row=summary['pooled'][condition][name]['noboundary'] if tile is None else summary['tiles'][condition][tile]['results'][name]['noboundary']
    return row['mIoU_fg5']*100

def scores(summary,name='candidate',tile=None):
    clean=metric(summary,'clean',name,tile)
    rgb=float(np.mean([metric(summary,c,name,tile) for c in RGB]))
    aux=float(np.mean([metric(summary,c,name,tile) for c in AUX]))
    return dict(clean=clean,rgb_family=rgb,aux_family=aux,composite=(clean+rgb+aux)/3)

def risk(summary):
    harm,rescue=[],[]
    for c in AVAILABLE:
        row=summary['pooled'][c]['candidate']['noboundary']['available']
        harm.append(row['harm']/max(1,row['valid']))
        rescue.append(row['rescue']/max(1,row['valid']))
    return dict(harm_macro=float(np.mean(harm)),rescue_macro=float(np.mean(rescue)))

def matched(candidate,control):
    a,b=scores(candidate),scores(control)
    delta={k:a[k]-b[k] for k in a}
    tile_delta={tile:{k:scores(candidate,tile=tile)[k]-scores(control,tile=tile)[k]
                      for k in ('clean','rgb_family','aux_family')}
                for tile in ('3_11','5_10')}
    guard=(delta['clean']>=-.1 and delta['rgb_family']>=-.3 and delta['aux_family']>=-.3
           and all(v>=-.3 for rows in tile_delta.values() for v in rows.values()))
    ra,rb=risk(candidate),risk(control)
    harm_reduction=1-ra['harm_macro']/rb['harm_macro'] if rb['harm_macro']>0 else None
    rescue_retention=ra['rescue_macro']/rb['rescue_macro'] if rb['rescue_macro']>0 else None
    return dict(delta_pp=delta,tile_delta_pp=tile_delta,precision_protection_pass=guard,
                fusion_screen_pass=delta['composite']>=.2 and guard,
                harm_reduction=harm_reduction,rescue_retention=rescue_retention,
                negative_transfer_screen_pass=(harm_reduction is not None and harm_reduction>=.1
                    and rescue_retention is not None and rescue_retention>=.9),
                harm_reference='fixed R0; own optical modality effects separately retained in raw summary')

def audit_counts(summary):
    matrices=0
    for rows in summary['tiles'].values():
        for row in rows.values():
            for name,scopes in row['results'].items():
                for scope,value in scopes.items():
                    raw=np.asarray(value['cm'])
                    cm=raw.astype(np.int64)
                    if raw.dtype.kind not in 'iu' or cm.shape!=(6,6) or (cm<0).any() or int(cm.sum())!=value['all']['valid']:
                        raise RuntimeError('raw count matrix invalid')
                    tp=np.diag(cm);support=cm.sum(1);fp=cm.sum(0)-tp;fn=support-tp
                    if not all(np.array_equal(v,value[k]) for k,v in [('TP',tp),('support',support),('FP',fp),('FN',fn)]):
                        raise RuntimeError('per-class counters mismatch')
                    union=tp+fp+fn
                    iou=np.divide(tp,union,out=np.full(6,np.nan),where=union>0)
                    if abs(float(np.nanmean(iou[:5]))-value['mIoU_fg5'])>1e-12:
                        raise RuntimeError('fg5 does not match original matrix')
                    if abs(float(np.nanmean(iou))-value['mIoU_6'])>1e-12:
                        raise RuntimeError('six-class metric does not match original matrix')
                    for key in ('valid','harm','rescue'):
                        if value['all'][key]!=value['available'][key]+value['missing'][key]:
                            raise RuntimeError('availability pooling mismatch')
                        if value['all'][key]!=sum(v[key] for v in value['by_class'].values()):
                            raise RuntimeError('class risk pooling mismatch')
                    reference=row['results']['R0'][scope]
                    net=int(tp.sum())-sum(reference['TP'])
                    if net!=value['all']['rescue']-value['all']['harm']:
                        raise RuntimeError('net correct differs from rescue minus harm')
                    matrices+=1
            for scope,value in row['own_optical_reference'].items():
                candidate=row['results']['candidate'][scope]
                optical=row['results']['own_optical'][scope]
                if value['cm']!=candidate['cm'] or value['missing']['harm'] or value['missing']['rescue']:
                    raise RuntimeError('own optical reference/fallback mismatch')
                if sum(candidate['TP'])-sum(optical['TP'])!=value['all']['rescue']-value['all']['harm']:
                    raise RuntimeError('own optical net-correct identity failed')
    for condition,models in summary['pooled'].items():
        for name,scopes in models.items():
            for scope,value in scopes.items():
                pooled=sum((np.asarray(row['results'][name][scope]['cm'],np.int64)
                            for row in summary['tiles'][condition].values()),np.zeros((6,6),np.int64))
                if not np.array_equal(pooled,value['cm']):raise RuntimeError('tile pooling mismatch')
    return matrices

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);args=ap.parse_args()
    base=within(args.directory,'/home/jovyan/zzx')
    plan=read(base/'plan.json');state=read(base/'queue_status.json')
    summaries,rows,audits={},[],{}
    for job in sorted(plan['jobs'],key=lambda j:j['priority']):
        j=job['id'];record=base/'jobs'/j/'evaluation/summary.json'
        if state['jobs'][j]['status']!='COMPLETE' or not record.exists():continue
        s=read(record);summaries[j]=s;audits[j]=audit_counts(s)
        value=scores(s)
        row=dict(id=j,route=job['route'],**value,aux_zero=metric(s,'aux_zero'),
                 selected_step=read(base/'jobs'/j/'complete.json')['selected']['step'],
                 delta_vs_fixed_M0_pp=value['composite']-scores(s,'M0_safe')['composite'])
        rows.append(row)
    comparisons={}
    for j,control in [('A1','A0'),('A2','A0'),('A3','A2'),('B1','B0'),('B2','B0'),('B3','B2'),
                      ('B3','B1'),('D1','D0'),('D2','D0'),('A2','D1'),('A2','D2')]:
        key=j+'-'+control
        comparisons[key]=matched(summaries[j],summaries[control]) if j in summaries and control in summaries else dict(status='UNAVAILABLE',reason='matched run incomplete')
    c={}
    if all(j in summaries for j in ('C0','C1','C2','C3')):
        a=scores(summaries['C2'])
        gain={j:a['clean']-scores(summaries[j])['clean'] for j in ('C0','C1','C3')}
        tile_min=min(scores(summaries['C2'],tile=t)[family]-scores(summaries['C0'],tile=t)[family]
                     for t in ('3_11','5_10') for family in ('clean','rgb_family'))
        rgb=a['rgb_family']-scores(summaries['C0'])['rgb_family']
        c=dict(clean_gain_pp=gain,rgb_family_delta_vs_C0_pp=rgb,min_tile_clean_or_RGB_delta_vs_C0_pp=tile_min,
               regional_KD_screen_pass=gain['C0']>=.2 and gain['C1']>=.1 and gain['C3']>=.1 and rgb>=-.1 and tile_min>=-.3,
               primary='optical-only clean fg5; no full-fusion contribution claim')
    else:c=dict(status='UNAVAILABLE',reason='C0/C1/C2/C3 not all complete')
    decisions={}
    for name,comparison in [('Pair_frozen','A1-A0'),('Pair_last4','A3-A2'),
                            ('class_prototype_pixel_CE','B1-B0'),('class_prototype_balanced_CE','B3-B2')]:
        value=comparisons[comparison]
        decisions[name]=value.get('fusion_screen_pass') if 'delta_pp' in value else None
    balance=comparisons['B3-B1'];semantic=comparisons['B3-B2']
    decisions['prototype_plus_balance_extra_effect']=(balance['delta_pp']['composite']>=.1 and
                 balance['precision_protection_pass'] and semantic['fusion_screen_pass']) if 'delta_pp' in balance and 'delta_pp' in semantic else None
    interaction={}
    for name,ids in [('Pair_x_last4',('A3','A2','A1','A0')),('Q_x_D',('A2','D1','D2','D0'))]:
        if all(j in summaries for j in ids):
            values=[scores(summaries[j])['composite'] for j in ids]
            interaction[name]=values[0]-values[1]-values[2]+values[3]
    result=dict(observed_at=now(),evidence_level='single_seed_reused_Val2_development_only',
                complete_jobs=len(rows),rows=rows,matched_comparisons=comparisons,C_region_screen=c,
                factorial_interaction_composite_pp=interaction,mechanism_screen=decisions,raw_tile_matrices_checked=audits,
                original_plan=plan['id'],test6_loaded=False,independent_final_loaded=False,
                multiple_comparison_warning='screening signals only; no independent replication or p values')
    write(base/'screen_result.json',result)
    with (base/'results.csv').open('w',newline='') as f:
        fields=['id','route','clean','rgb_family','aux_family','composite','aux_zero','selected_step','delta_vs_fixed_M0_pp']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    for row in rows:print('D24_RESULT',row['id'],'clean=%.4f composite=%.4f'%(row['clean'],row['composite']))
    print('D24_SCREEN_COMPLETE',len(rows),'/15','test6_loaded=False',flush=True)
if __name__=='__main__':main()
