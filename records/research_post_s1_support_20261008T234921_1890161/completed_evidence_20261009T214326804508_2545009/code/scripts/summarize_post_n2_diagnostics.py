"""Integer pooled summaries and problem triggers; never starts training."""
import argparse
from pathlib import Path
import numpy as np
from post_n2_diag_common import *
from post_n2_masks import e1_gate

def metric(cm):
    cm=np.asarray(cm,np.int64);tp=np.diag(cm);union=cm.sum(0)+cm.sum(1)-tp;iou=np.divide(tp,union,out=np.full(6,np.nan),where=union>0)
    return float(np.nanmean(iou[:5])) if np.isfinite(iou[:5]).any() else None

def checked_matrix(row):
    cm=np.asarray(row['cm'])
    if cm.shape!=(6,6) or cm.dtype.kind not in 'iu' or (cm<0).any():raise RuntimeError('invalid integer matrix')
    cm=cm.astype(np.int64);tp=np.diag(cm);support=cm.sum(1);fp=cm.sum(0)-tp;fn=support-tp
    for key,expected in (('support',support.tolist()),('TP',tp.tolist()),('FP',fp.tolist()),('FN',fn.tolist()),('valid',int(cm.sum()))):
        if row[key]!=expected:raise RuntimeError('matrix-derived count differs '+key)
    expected=metric(cm);reported=row['mIoU_fg5']
    if (expected is None)!=(reported is None) or expected is not None and abs(expected-reported)>1e-10:raise RuntimeError('matrix-derived fg5 differs')
    return cm

def checked_joint(row):
    if row['shape']!=[6]*4 or row['dtype']!='int64' or row['format']!='sparse_flat_index_count':raise RuntimeError('joint encoding changed')
    flat=np.zeros(6**4,np.int64);seen=set()
    for index,count in row['nonzero']:
        if type(index)!=int or type(count)!=int or not 0<=index<6**4 or count<=0 or index in seen:raise RuntimeError('invalid sparse joint')
        flat[index]=count;seen.add(index)
    return flat.reshape((6,)*4)

def validate_scopes(row):
    for scope in ('full','noboundary'):
        value=row['scopes'][scope];matrices={n:{r:checked_matrix(x) for r,x in regions.items()} for n,regions in value['metrics'].items()}
        for region,encoded in value['joint'].items():
            a=checked_joint(encoded)
            for name,axes in (('candidate',(1,2)),('rgb',(2,3)),('dsm',(1,3))):
                if not np.array_equal(a.sum(axes),matrices[name][region]):raise RuntimeError('joint marginal differs')
        if not np.array_equal(matrices['candidate']['all'],matrices['candidate']['mask_location']+matrices['candidate']['other_locations']):raise RuntimeError('location partition differs')

def load_job(base,job):
    folder=base/'jobs'/job['id'];complete=read(folder/'complete.json');summary=read(folder/'summary.json')
    if complete['optimizer_updates']!=0 or complete['summary_sha256']!=sha(folder/'summary.json') or complete['signature']!=summary['binding'] or summary['binding']['plan_sha256']!=sha(base/'plan.json') or summary['binding']['job']!=job:raise RuntimeError('diagnostic completion differs')
    result={}
    for condition,tiles in summary['records'].items():
        result[condition]={}
        if set(tiles)!=set(('3_11','5_10')):raise RuntimeError('diagnostic tiles changed')
        for tile,binding in tiles.items():
            path=within(binding['path'],folder)
            if sha(path)!=binding['sha256']:raise RuntimeError('diagnostic record changed')
            row=read(path)
            if row['test6_loaded'] or row['independent_final_loaded'] or row['binding']['training']!=summary['binding']:raise RuntimeError('record scope changed')
            if row['binding']['tile']!=tile:raise RuntimeError('tile binding changed')
            validate_scopes(row);cm=checked_matrix(row['scopes']['noboundary']['metrics']['candidate']['all'])
            result[condition][tile]=cm.astype(np.int64)
    expected={d+'_'+r for d in ('rgb','dsm') for r in (('U','H','L') if job['stage']=='E1' else ('known_missing','false_negative','false_positive'))}
    if set(result)!=expected:raise RuntimeError('condition list changed')
    for r in summary['clean'].values():
        for scope in ('full','noboundary'):checked_matrix(r['metrics'][scope])
    return summary,result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();base=a.directory.resolve();base.relative_to(Path('/home/jovyan/zzx'))
    plan=validate(read(base/'plan.json'));rows={};pooled={};raw={};E2={};clean_scores={}
    for job in plan['jobs']:
        summary,result=load_job(base,job);name=job['model']
        if job['stage']=='E1':
            clean_scores[name]=dict(tile_fraction={t:metric(r['metrics']['noboundary']['cm']) for t,r in summary['clean'].items()},pooled_fraction=metric(sum((np.asarray(r['metrics']['noboundary']['cm'],np.int64) for r in summary['clean'].values()),np.zeros((6,6),np.int64))))
            rows[name]={k:{t:metric(cm) for t,cm in tiles.items()} for k,tiles in result.items()}
            pooled[name]={k:metric(sum(tiles.values(),np.zeros((6,6),np.int64))) for k,tiles in result.items()}
            raw[name]={k:sum(tiles.values(),np.zeros((6,6),np.int64)).tolist() for k,tiles in result.items()}
        else:
            E2[name]={}
            for direction in ('rgb','dsm'):
                known=result[direction+'_known_missing'];miss=result[direction+'_false_negative'];fp=result[direction+'_false_positive']
                delta=100*(metric(sum(known.values(),np.zeros((6,6),np.int64)))-metric(sum(miss.values(),np.zeros((6,6),np.int64))))
                td={t:100*(metric(known[t])-metric(miss[t])) for t in known}
                clean={t:summary['clean'][t]['metrics']['noboundary']['cm'] for t in known}
                E2[name][direction]=dict(missed_flag_cost_pp=delta,tile_costs_pp=td,problem_signal=delta>=.5-1e-9 and all(x>0 for x in td.values()),false_positive_vs_clean_pp=100*(metric(sum((np.asarray(v,np.int64) for v in clean.values()),np.zeros((6,6),np.int64)))-metric(sum(fp.values(),np.zeros((6,6),np.int64)))),raw_matrices={k:{t:cm.tolist() for t,cm in result[direction+'_'+k].items()} for k in ('known_missing','false_negative','false_positive')})
    gate=e1_gate(rows,pooled,.5)
    e0=read(base/'e0_screen.json')
    for records in e0['records'].values():
        for binding in records.values():
            if sha(within(binding['path'],base))!=binding['sha256']:raise RuntimeError('E0 record SHA differs')
    report=dict(E0=e0['gate'],E1=gate,E1_tile_metrics_fraction=rows,E1_pooled_metrics_fraction=pooled,E1_clean_references=clean_scores,E1_pooled_matrices=raw,E2=E2,
        N4='NO_IDENTIFIABLE_CONDITION_EXPOSURE_EVIDENCE_FROM_EXISTING_COUNTS',next_action='review problem triggers; implement one matched training family only when justified',
        optimizer_updates=0,automatic_training=False,T_evaluated=False,test6_loaded=False,independent_final_loaded=False,observed_at=now())
    write(base/'diagnostic_screen.json',report);print('POST_N2_DIAGNOSTICS_SCREEN',gate['N5_problem_trigger'],report['E0']['N3_problem_trigger'],flush=True)
if __name__=='__main__':main()
