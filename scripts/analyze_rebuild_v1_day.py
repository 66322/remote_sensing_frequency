"""Read-only paired development analysis from completed portfolio summaries."""
import csv
import math
import shutil
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import day_portfolio_common as p
import numpy as np


def score(summary,condition='clean'):
    scope=summary['primary_scope']
    return 100*summary['conditions'][condition]['pooled'][scope]['metrics']['mIoU_fg5']


def family_scores(summary,tile=None):
    scope=summary['primary_scope']
    groups={'clean':['clean'],
        'optical_quality':['rgb_down2','rgb_down4','rgb_blur5','rgb_local_down4_q1'],
        'auxiliary_quality':['aux_down4','aux_noise_std010']}
    def value(condition):
        entry=summary['conditions'][condition]
        row=entry['pooled'][scope] if tile is None else entry['tiles'][str(tile)]['scopes'][scope]
        return 100*row['metrics']['mIoU_fg5']
    result={name:sum(value(c) for c in members)/len(members) for name,members in groups.items()}
    result['macro']=sum(result.values())/len(result)
    return result


def audit(summary):
    for condition,entry in summary['conditions'].items():
        for scope,pooled in entry['pooled'].items():
            matrices=[row['scopes'][scope] for row in entry['tiles'].values()]
            combined=sum((np.asarray(row['cm'],dtype=np.int64) for row in matrices),
                np.zeros((6,6),dtype=np.int64))
            if not np.array_equal(combined,np.asarray(pooled['cm'],dtype=np.int64)):
                raise RuntimeError('pooled count mismatch: '+condition)
            for row in matrices+[pooled]:
                cm=np.asarray(row['cm'],dtype=np.int64)
                if cm.shape!=(6,6) or (cm<0).any() or int(cm.sum())!=row['metrics']['valid_pixels']:
                    raise RuntimeError('invalid integer confusion matrix')
                if cm.sum(1).tolist()!=row['metrics']['class_true_count']:
                    raise RuntimeError('class count mismatch')
                tp=np.diag(cm).astype(np.float64)
                union=cm.sum(0)+cm.sum(1)-tp
                iou=np.divide(tp,union,out=np.full(6,np.nan),where=union>0)
                value=float(np.nanmean(iou[:5]))
                if not math.isclose(value,row['metrics']['mIoU_fg5'],rel_tol=0,abs_tol=1e-12):
                    raise RuntimeError('metric recomputation mismatch')


def main():
    path=p.OUT/'scope.json'
    if not path.is_file():
        raise RuntimeError('scope not frozen')
    selected=set(p.read(path)['selected_job_ids'])
    jobs=[j for j in p.jobs() if j['job_id'] in selected]
    summaries={}
    rows=[]
    for job in jobs:
        summary_path=p.eval_dir(job)/'summary.json'
        if not summary_path.is_file():
            continue
        entry=p.read(summary_path)
        if entry['job']!=job or entry['test6_loaded'] is not False:
            raise RuntimeError('invalid evaluation binding '+job['job_id'])
        train=p.read(p.run_dir(job)/'summary.json')
        if train['global_step']!=job['steps'] or train['signature']!=entry['signature']['training']:
            raise RuntimeError('training/evaluation signature mismatch')
        if train['checkpoint_sha256']!=entry['signature']['checkpoint_sha256']:
            raise RuntimeError('checkpoint binding mismatch')
        audit(entry)
        summaries[job['job_id']]=entry
        p.COMPACT.mkdir(parents=True,exist_ok=True)
        shutil.copy2(summary_path,p.COMPACT/(job['job_id']+'_evaluation.json'))
        p.write(p.COMPACT/(job['job_id']+'_training.json'),train)
        for condition,data in entry['conditions'].items():
            metrics=data['pooled'][entry['primary_scope']]['metrics']
            rows.append(dict(job_id=job['job_id'],direction=job['direction'],
                dataset=job['dataset'],arm=job['arm'],scale=job['scale'],condition=condition,
                primary_scope=entry['primary_scope'],mIoU_fg5=metrics['mIoU_fg5'],
                mIoU_all6=metrics['mIoU_all6'],valid_pixels=metrics['valid_pixels'],
                checkpoint_sha256=entry['signature']['checkpoint_sha256']))
    p.COMPACT.mkdir(parents=True,exist_ok=True)
    with (p.COMPACT/'metrics.csv').open('w',newline='',encoding='utf-8') as dest:
        writer=csv.DictWriter(dest,fieldnames=list(rows[0]) if rows else ['job_id'])
        writer.writeheader()
        writer.writerows(rows)
    comparisons=[]
    b_decisions={}
    c_decisions={}
    index={(j['direction'],j['dataset'],j['arm'],j['scale']):j['job_id'] for j in jobs}
    def get(direction,dataset,arm,scale):
        job_id=index.get((direction,dataset,arm,scale))
        return summaries.get(job_id)
    for dataset in ('potsdam','vaihingen'):
        for modality in ('R0','M1','M0'):
            frozen,last4=get('A',dataset,modality+'_frozen',0),get('A',dataset,modality+'_last4',0)
            if frozen and last4:
                comparisons.append(dict(dataset=dataset,comparison='A_last4_minus_frozen_'+modality,
                                        delta_pp=score(last4)-score(frozen)))
        candidate=get('B',dataset,'low_high_dsm',0)
        controls=[get('B',dataset,a,0) for a in ('gray','raw_dsm','low_rolled_high_dsm')]
        if candidate and all(controls):
            candidate_family=family_scores(candidate)
            reference=p.read(p.d21.eval_dir(dict(dataset=dataset,arm='R0',seed=42))/'summary.json')
            all_controls=dict(zip(('gray','raw_dsm','low_rolled_high_dsm'),controls))
            all_controls['D21_R0_anchor']=reference
            control_family={name:family_scores(entry) for name,entry in all_controls.items()}
            strongest=max(control_family[name]['macro'] for name in ('gray','raw_dsm','low_rolled_high_dsm'))
            failures=[]
            if candidate_family['macro']-strongest<p.config()['b_candidate_gain_min_pp']:
                failures.append('macro gain below +0.2 pp over strongest B control')
            for name,baseline in all_controls.items():
                ref=control_family[name]
                for family in ('clean','optical_quality','auxiliary_quality'):
                    limit=p.config()['b_clean_loss_max_pp'] if family=='clean' else p.config()['b_family_loss_max_pp']
                    if candidate_family[family]-ref[family]<-limit:
                        failures.append(f'pooled {family} below {name} protection')
                for tile in p.datasets()[dataset]['dev']:
                    cand_tile=family_scores(candidate,tile)
                    ref_tile=family_scores(baseline,tile)
                    for family in ('clean','optical_quality','auxiliary_quality'):
                        limit=p.config()['b_tile_clean_loss_max_pp'] if family=='clean' else p.config()['b_tile_family_loss_max_pp']
                        if cand_tile[family]-ref_tile[family]<-limit:
                            failures.append(f'tile {tile} {family} below {name} protection')
            b_decisions[dataset]=dict(candidate_scores=candidate_family,
                strongest_control_macro=strongest,failures=failures,
                development_gate_passed=not failures,
                synthetic_aux_zero_prediction_equality='checked per tile during evaluation',
                actual_missing_dsm_detection_claim=False)
            for arm,control in zip(('gray','raw_dsm','low_rolled_high_dsm'),controls):
                delta=candidate_family['macro']-family_scores(control)['macro']
                comparisons.append(dict(dataset=dataset,comparison='B3_minus_'+arm,
                    delta_pp=delta,passes_prefrozen_0p2pp=delta>=p.config()['b_candidate_gain_min_pp']))
        for scale in (2,4):
            cells={a:get('C',dataset,a,scale) for a in ('bicubic_ce','learned_ce','learned_pixel_ce','learned_pixel_high_ce')}
            if all(cells.values()):
                for numerator,denominator in (('learned_ce','bicubic_ce'),
                    ('learned_pixel_ce','learned_ce'),('learned_pixel_high_ce','learned_ce'),
                    ('learned_pixel_high_ce','learned_pixel_ce')):
                    comparisons.append(dict(dataset=dataset,scale=scale,
                        comparison='C_'+numerator+'_minus_'+denominator,
                        delta_pp=score(cells[numerator])-score(cells[denominator])))
                candidate=cells['learned_pixel_high_ce']
                strongest=max(score(cells[a]) for a in ('learned_ce','learned_pixel_ce'))
                failures=[]
                if score(candidate)-strongest<p.config()['c_candidate_gain_min_pp']:
                    failures.append('C3 clean LR-task gain below +0.2 pp over stronger C1/C2')
                for name in ('learned_ce','learned_pixel_ce'):
                    control=cells[name]
                    for tile in p.datasets()[dataset]['dev']:
                        scope=candidate['primary_scope']
                        cand_tile=100*candidate['conditions']['clean']['tiles'][str(tile)]['scopes'][scope]['metrics']['mIoU_fg5']
                        ctrl_tile=100*control['conditions']['clean']['tiles'][str(tile)]['scopes'][scope]['metrics']['mIoU_fg5']
                        if cand_tile-ctrl_tile<-p.config()['c_tile_loss_max_pp']:
                            failures.append(f'tile {tile} below {name} protection')
                c_decisions[f'{dataset}_scale{scale}']=dict(candidate_clean_pp=score(candidate),
                    strongest_C1_C2_clean_pp=strongest,failures=failures,
                    development_gate_passed=not failures)
        c1,c3=get('C',dataset,'learned_ce',4),get('C',dataset,'learned_pixel_high_ce',4)
        d1,d3,gray=(get('D',dataset,a,4) for a in ('learned_ce_dsm',
            'learned_pixel_high_ce_dsm','learned_pixel_high_ce_gray'))
        if all((c1,c3,d1,d3,gray)):
            comparisons.append(dict(dataset=dataset,comparison='D_recovery_x_DSM_interaction',
                delta_pp=(score(d3)-score(d1))-(score(c3)-score(c1))))
            comparisons.append(dict(dataset=dataset,comparison='D_DSM_minus_gray_capacity',
                delta_pp=score(d3)-score(gray)))
    p.write(p.COMPACT/'analysis.json',dict(completed=len(summaries),selected=len(selected),
        comparisons=comparisons,b_decisions=b_decisions,c_decisions=c_decisions,
        rows=len(rows),integer_count_audit='PASS',test6_loaded=False,
        interpretation='single-seed paired development evidence; no independent final claim'))
    for name in ('plan.json','preflight.json','scope.json','scope.sha256',
                 'microbatch_profile.json','input_manifest.json'):
        source=p.OUT/name
        if source.is_file():
            shutil.copy2(source,p.COMPACT/name)
    print('ANALYZED',len(summaries),'/',len(selected),flush=True)


if __name__=='__main__':
    main()
