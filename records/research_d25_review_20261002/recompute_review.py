"""D25 offline review of pinned GitHub light originals; no server, training or inference."""
import hashlib,json,math,sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent
PINNED_EVIDENCE='records/research_d25_missingness_20261002T130253_1358078/evidence_20261002T171201888612_1513281'
REPO_ROOT=ROOT.parent.parent
SRC=(REPO_ROOT/PINNED_EVIDENCE) if (REPO_ROOT/PINNED_EVIDENCE).is_dir() else ROOT/'source'
from datetime import datetime
now=lambda:datetime.now().astimezone().isoformat()
RGB=('rgb_down2','rgb_down4','rgb_blur5','rgb_local_down4_q1')
AUX=('aux_down4','aux_noise_std010')
AVAILABLE=('clean',)+RGB+AUX+('rgb_contrast060','aux_shift8')
MISSING=('aux_zero','aux_local_zero_q1','aux_local_zero_stripe_eighth')

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

def abilities(s,tile=None):
    return dict(**scores(s,tile=tile),aux_zero=metric(s,'aux_zero',tile=tile),
                missing_macro=float(np.mean([metric(s,c,tile=tile) for c in MISSING])))

def compare(a,b):
    x,y=abilities(a),abilities(b)
    delta={k:x[k]-y[k] for k in x}
    return dict(delta_pp=delta,practical_gain=((delta['composite']>=.2 and delta['missing_macro']>=-.1)
                     or (delta['missing_macro']>=.5 and delta['composite']>=-.1)),
                negative_transfer=matched(a,b))

def floor(a,p0,plan):
    delta=compare(a,p0)['delta_pp']
    minimum=min(metric(a,c,tile=t)-metric(p0,c,tile=t)
                for c in plan['evaluation']['old_development_conditions'] for t in plan['data']['validation'])
    threshold=plan['screen']
    return dict(pass_floor=(abilities(a)['clean']>=threshold['clean_floor_pp']
                 and delta['composite']>=-.1 and delta['aux_zero']>=-.1
                 and delta['missing_macro']>=-.1 and minimum>=-.3),
                min_old_condition_tile_delta_pp=minimum,delta_vs_P0_pp=delta,
                clean_floor_pp=threshold['clean_floor_pp'])

def build_screen(plan,state,summaries,completes):
    rows=[]
    comparisons={}
    floors={}
    for j,s in summaries.items():
        rows.append(dict(id=j,**abilities(s),selected_step=completes[j]['selected']['step'],
                         pair_enabled_steps=completes[j]['treatment_counts'].get('Pair:enabled_steps',0)))
    for a,b in (('P1','P0'),('P2','P0'),('P2','P5'),('P3','P2'),('P3','P7'),
                ('P3','P0'),('P4','P0'),('P5','P0'),('P0','P6'),('P2','P6')):
        comparisons[a+'-'+b]=compare(summaries[a],summaries[b]) if a in summaries and b in summaries else None
    if 'P0' in summaries:
        for j in ('P2','P3','P4','P5','P7'):
            if j in summaries:floors[j]=floor(summaries[j],summaries['P0'],plan)
    def supported(j,controls):
        if j not in floors or any(comparisons.get(j+'-'+c) is None for c in controls):return None
        return floors[j]['pass_floor'] and all(comparisons[j+'-'+c]['practical_gain'] for c in controls)
    decisions={'H1_separate_decoders':supported('P2',('P0','P5')),
               'H2_projection_separate':supported('P3',('P2','P7')),
               'projection_shared':supported('P4',('P0',)),
               'Pair_corrected':None}
    if comparisons.get('P1-P0') is not None:
        if completes['P1']['treatment_counts'].get('Pair:enabled_steps')!=4000:
            raise RuntimeError('Pair did not actually run every update')
        decisions['Pair_corrected']=comparisons['P1-P0']['negative_transfer']['fusion_screen_pass']
    interaction=None
    if all(j in summaries for j in ('P0','P2','P3','P4')):
        interaction={k:abilities(summaries['P3'])[k]-abilities(summaries['P2'])[k]
                       -abilities(summaries['P4'])[k]+abilities(summaries['P0'])[k]
                     for k in ('clean','composite','missing_macro')}
    pressure={j:{c:metric(s,c) for c in plan['evaluation']['pressure_diagnostics']} for j,s in summaries.items()}
    return dict(observed_at=now(),complete_jobs=len(rows),rows=rows,matched_comparisons=comparisons,
                ability_floors=floors,mechanism_screen=decisions,
                factorial_interaction_pp=interaction,pressure_diagnostic_only=pressure,
                original_plan=plan['id'],test6_loaded=False,independent_final_loaded=False,
                evidence_level='single_seed_reused_Val2_development_only',
                interpretation='Screen support is not independent confirmation or gradient-causality proof; inspect gradient logs and raw tile counts. No automatic follow-up training.')

read=lambda p:json.loads(p.read_text(encoding='utf-8'))
plan=read(SRC/'plan.json');screen=read(SRC/'screen_result.json')
manifest=read(SRC/'upload_manifest.json');state=read(SRC/'queue_status.json')
files={x['path']:x for x in manifest['files']}
verified=0
for p in SRC.rglob('*'):
    if p.is_file() and p.name!='upload_manifest.json':
        relative=p.relative_to(SRC).as_posix()
        row=files[relative];raw=p.read_bytes()
        assert len(raw)==row['bytes'],relative
        assert hashlib.sha256(raw).hexdigest()==row['sha256'],relative
        verified+=1
summaries={};completes={};audits={};diagnostics={}
matrix_metric_error=0.;pooled=0
plan_sha=hashlib.sha256((SRC/'plan.json').read_bytes()).hexdigest()
code=read(SRC/'code_manifest.json')
source_check=read(ROOT/'source_binding_api.json')
assert len(source_check)==22
assert all(hashlib.sha256(raw.encode('utf-8')).hexdigest()==code['files'][p] for p,raw in source_check.items())
for j in [x['id'] for x in plan['jobs']]:
    base=SRC/'jobs'/j
    complete=read(base/'complete.json');s=read(base/'evaluation/summary.json')
    grad=read(base/'gradient_check.json');capacity=read(base/'model_capacity.json')
    assert state['jobs'][j]['status']=='COMPLETE'
    assert complete['global_step']==4000
    assert complete['signature']['execution_commit']==code['commit']=='0c31167d0fdb57f03459ea18981c1ee02bcee9f2'
    assert complete['signature']['plan_sha256']==plan_sha
    assert complete['signature']['sources']==code['files']
    assert s['signature']['training']==complete['signature']==grad['signature']
    assert complete['evaluation_summary_sha256']==hashlib.sha256((base/'evaluation/summary.json').read_bytes()).hexdigest()
    assert all(grad[k] for k in ('encoder_gradient_nonzero','head_gradient_nonzero','frozen_gradients_absent','teacher_gradients_absent'))
    assert grad['trainable_parameters']==capacity['trainable_parameters']
    assert not s['test6_loaded'] and not s['independent_final_loaded']
    selection={step:read(base/'validation'/('step_%04d.json'%step)) for step in (2000,4000)}
    best=2000 if selection[2000]['pooled']['mIoU_fg5']>=selection[4000]['pooled']['mIoU_fg5'] else 4000
    assert best==complete['selected']['step']
    assert complete['selected']['checkpoint_sha256']==complete['selected_checkpoint_sha256']
    for step,v in selection.items():
        assert v['signature']['training']==complete['signature']
        assert v['signature']['step']==step
        if step==best:assert v['signature']['checkpoint_sha256']==complete['selected_checkpoint_sha256']
    assert complete['selected']['metric']==selection[best]['pooled']['mIoU_fg5']==s['pooled']['clean']['candidate']['noboundary']['mIoU_fg5']
    assert set(s['pooled'])==set(plan['evaluation']['conditions'])
    assert all(set(x)==set(plan['data']['validation']) for x in s['tiles'].values())
    audits[j]=audit_counts(s)
    for condition,models in s['pooled'].items():
        for name,scopes in models.items():
            for scope,row in scopes.items():
                cm=np.asarray(row['cm'],np.int64)
                tp=np.diag(cm);fp=cm.sum(0)-tp;fn=cm.sum(1)-tp
                union=tp+fp+fn
                iou=np.divide(tp,union,out=np.full(6,np.nan),where=union>0)
                assert row['TP']==tp.tolist() and row['FP']==fp.tolist() and row['FN']==fn.tolist()
                for key,n in [('mIoU_fg5',5),('mIoU_6',6)]:
                    error=abs(float(np.nanmean(iou[:n]))-row[key]);assert error<1e-12
                    matrix_metric_error=max(matrix_metric_error,error)
                for partition in ('all','available','missing'):
                    for k in ('valid','harm','rescue'):
                        assert row[partition][k]==sum(tile['results'][name][scope][partition][k] for tile in s['tiles'][condition].values())
                pooled+=1
    ds=[read(p) for p in sorted((base/'gradient_diagnostics').glob('step_*.json'))]
    assert [d['step'] for d in ds]==[1]+list(range(100,4001,100))
    assert all(d['signature']==complete['signature'] for d in ds)
    conflict=[d['step'] for d in ds if d['conflict']]
    stored=screen['gradient_diagnostics_summary'][j]
    assert stored['sampled_steps']==len(ds)
    assert abs(stored['sampled_conflict_fraction']-len(conflict)/len(ds))<1e-12
    assert abs(stored['mean_cosine']-np.mean([d['cosine'] for d in ds]))<1e-12
    assert abs(stored['mean_present_norm']-np.mean([d['present_norm'] for d in ds]))<1e-12
    assert abs(stored['mean_missing_norm']-np.mean([d['missing_norm'] for d in ds]))<1e-12
    if j=='P1':
        assert complete['treatment_counts']['Pair:enabled_steps']==4000
        assert complete['treatment_counts']['Pair:weighted_loss_sum']>0
    else:assert complete['treatment_counts']['Pair:enabled_steps']==0
    if j=='P6':
        assert all(d['missing_norm']==0 and d['missing_pixels']==0 for d in ds)
    else:
        assert all(d['missing_norm']>0 and d['missing_pixels']>0 for d in ds)
    if j in ('P2','P3','P7'):
        assert all(not any(n.startswith(('decoder.','decoder_optical.','detail.')) for n in d['shared_parameters']) for d in ds)
        assert all(d['decoder.gradient_nonzero'] and d['decoder_optical.gradient_nonzero'] for d in ds)
    if j=='P5':
        assert all(any(n.startswith('decoder_optical.') for n in d['shared_parameters']) for d in ds)
    if j in ('P3','P4'):
        assert all(abs(d['applied_missing_norm']-d['projected_missing_norm'])<1e-6 for d in ds)
    if j=='P7':
        assert all(abs(d['applied_missing_norm']-d['projected_missing_norm'])<1e-5 for d in ds)
    diagnostics[j]=dict(samples=len(ds),conflict_steps=conflict,
        conflicts_through_selected_step=[x for x in conflict if x<=best],
        mean_cosine=stored['mean_cosine'],min_cosine=min(d['cosine'] for d in ds),
        mean_present_norm=stored['mean_present_norm'],mean_missing_norm=stored['mean_missing_norm'],
        max_projection_norm_change=max(abs(d['projected_missing_norm']-d['missing_norm']) for d in ds),
        pair_positive_sample_steps=[d['step'] for d in ds if d.get('Pair:weighted_loss_sum',0)>0],
        selection={str(step):v['pooled']['mIoU_fg5']*100 for step,v in selection.items()},
        parameter_counts=capacity)
    summaries[j]=s;completes[j]=complete
new=build_screen(plan,state,summaries,completes)
for key in ('rows','matched_comparisons','ability_floors','mechanism_screen','factorial_interaction_pp','pressure_diagnostic_only'):
    assert new[key]==screen[key],key
pairs=screen['matched_comparisons']
# Independently compute metric gains/guardrails rather than trusting generated screen flags.
RGB=('rgb_down2','rgb_down4','rgb_blur5','rgb_local_down4_q1')
AUX=('aux_down4','aux_noise_std010')
MIS=('aux_zero','aux_local_zero_q1','aux_local_zero_stripe_eighth')
def value(s,c,t=None):
    r=s['pooled'][c]['candidate']['noboundary'] if t is None else s['tiles'][c][t]['results']['candidate']['noboundary']
    cm=np.asarray(r['cm']);tp=np.diag(cm);u=cm.sum(0)+cm.sum(1)-tp
    return float(np.nanmean(np.divide(tp,u,out=np.full(6,np.nan),where=u>0)[:5]))*100
def measurement(s):
    return {'clean':value(s,'clean'),'composite':(value(s,'clean')+np.mean([value(s,c) for c in RGB])+np.mean([value(s,c) for c in AUX]))/3,
            'missing_macro':float(np.mean([value(s,c) for c in MIS])),'aux_zero':value(s,'aux_zero')}
measures={j:measurement(s) for j,s in summaries.items()}
for key,row in pairs.items():
    a,b=key.split('-')
    assert all(abs((measures[a][k]-measures[b][k])-row['delta_pp'][k])<1e-12 for k in measures[a])
    d={k:measures[a][k]-measures[b][k] for k in measures[a]}
    practical=(d['composite']>=.2 and d['missing_macro']>=-.1) or (d['missing_macro']>=.5 and d['composite']>=-.1)
    assert practical==row['practical_gain']
for j,f in screen['ability_floors'].items():
    d={k:measures[j][k]-measures['P0'][k] for k in measures[j]}
    minimum=min(value(summaries[j],c,t)-value(summaries['P0'],c,t) for c in plan['evaluation']['old_development_conditions'] for t in plan['data']['validation'])
    passed=measures[j]['clean']>=86.970670 and d['composite']>=-.1 and d['aux_zero']>=-.1 and d['missing_macro']>=-.1 and minimum>=-.3
    assert passed==f['pass_floor']
assert all(not v for v in screen['mechanism_screen'].values())
# Same exposure counts for all QD treatments, with P6 Q-only using identical Q draws.
counts={j:c['treatment_counts'] for j,c in completes.items()}
for j in counts:
    assert {k:v for k,v in counts[j].items() if k.startswith('Q:')}=={k:v for k,v in counts['P0'].items() if k.startswith('Q:')}
    if j!='P6':
        assert {k:v for k,v in counts[j].items() if k.startswith('D:')}=={k:v for k,v in counts['P0'].items() if k.startswith('D:')}
        assert counts[j]['present_pixels']==counts['P0']['present_pixels']
        assert counts[j]['missing_pixels']==counts['P0']['missing_pixels']
pair_count=counts['P1']
pressure_delta={j:{c:value(summaries[j],c)-value(summaries['P0'],c) for c in plan['evaluation']['pressure_diagnostics']} for j in summaries}
per_tile_pressure={j:{c:{t:value(summaries[j],c,t)-value(summaries['P0'],c,t) for t in plan['data']['validation']}
                      for c in plan['evaluation']['pressure_diagnostics']} for j in ('P2','P3','P7')}
result={'source_commit':'2290b39cad802dd96ac980faedc291f5b0611fea','execution_commit':code['commit'],
        'source_directory':'records/research_d25_missingness_20261002T130253_1358078/evidence_20261002T171201888612_1513281',
        'verification':{'payload_sha_verified':verified,'manifest_files':len(files),'tile_matrices':sum(audits.values()),
                        'pooled_matrices':pooled,'max_metric_error':matrix_metric_error,'diagnostic_files':328,
                        'selection_candidate_metadata_recomputed':8,'complete_bindings_checked':8,'source_SHA_verified':22,
                        'matched_rows_recomputed':len(pairs),'all_four_mechanism_screens_false':True,
                        'prediction_or_checkpoint_bytes_loaded':False,'new_training':False,'new_inference':False},
        'queue':{'started_at':min(r['started_at'] for r in state['jobs'].values()),'completed_at':state['completed_at'],
                 'last_observed_at':state['observed_at'],'status':state['status'],'complete_jobs':8},
        'rows':screen['rows'],'diagnostics':diagnostics,'matched_comparisons':pairs,'ability_floors':screen['ability_floors'],
        'mechanism_screen':screen['mechanism_screen'],'pressure_delta_vs_P0':pressure_delta,
        'per_tile_pressure_delta_vs_P0':per_tile_pressure,
        'pair_actual':{'enabled_steps':pair_count['Pair:enabled_steps'],
                       'penalty_sum':pair_count['Pair:penalty_sum'],
                       'weighted_loss_sum':pair_count['Pair:weighted_loss_sum'],
                       'average_weighted_per_update':pair_count['Pair:weighted_loss_sum']/4000},
        'interpretation':'All four predefined screens failed; close these implementations without automatic sweep. Gradients mostly aligned in 41 sampled steps, not proof of zero conflicts across all updates/layers. Pressure signals diagnostic only.'}
(ROOT/'analysis.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
compact={k:v for k,v in result.items() if k!='diagnostics'}
compact['diagnostics']={j:{k:v for k,v in d.items() if k!='parameter_counts'} for j,d in diagnostics.items()}
(ROOT/'compact_analysis.json').write_text(json.dumps(compact,indent=2,allow_nan=False)+'\n',encoding='utf-8')
print(json.dumps({'verification':result['verification'],'queue':result['queue'],'diagnostics':compact['diagnostics'],
                  'pressure_delta_vs_P0':pressure_delta,'pair_actual':result['pair_actual']},indent=2))
