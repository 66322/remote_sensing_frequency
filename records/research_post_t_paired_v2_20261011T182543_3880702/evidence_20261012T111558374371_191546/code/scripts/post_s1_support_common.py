"""Frozen single-GPU contracts, provenance and completion guards. No Torch import."""
import copy
from pathlib import Path
from post_n2_diag_common import read,write,sha,now,within,verify_snapshot
from post_n3_s1_common import hours
SOURCE_NAME='research_post_n3_s1_20261007T083203_694293'
SOURCE_COMMIT='0e22438a7131a0a1f28098e675c3367d40236398'
PREFIX='research_post_s1_support_'
SHAS={
 'S1-0':'5a8cd5c40576e1897fbb6a767dd2028016df402c2b3b6ae98994f55ac4cec58f',
 'S1-1':'c51b934c175d6aee8f681e78951ffe7dec28b8e881408ed217426a5865141824',
 'S1-2':'da1714c7af40e0a2e03a0d9278b574734348f8a45ae99123c747cdc16e61e0f0',
 'S1-3':'c8b4d801da2a7a3937589aa3777885de810387a463009d4a8c6e23dc00d8d562'}
ORDER=['P6','P7','P8','P9','P4','P5','P2','P3','P0','P1']
POLICIES=['A1B1C1','A1B0C1','A1B1C0','A1B0C0']
E_KEYS=[f'rgb_{shape}__{quality}' for shape in ('lines64w8','blocks64q25') for quality in ('clean','aux_down4','aux_shift8')]
GATES=dict(rgb_base_pp=2.,mechanism_pp=.3,route_floor_pp=-.2,clean_missing_floor_pp=-.1,worst_tile_floor_pp=-.2,dsm_U_floor_pp=-.1,E_shape_gain_pp=.5,D1_DSM_signal_pp=.5)
def job_card(j):
    if j not in ['P'+str(i) for i in range(10)]:raise ValueError('unregistered arm')
    i=int(j[1:]); frozen=i>=4
    return dict(id=j,gpu=0,steps=8000,seed=42,frozen_base=frozen,
        support_preserved=i in (1,3,5,7,8,9),local_only=i in (2,3,6,7,8,9),
        control='shuffle' if i==8 else 'calibration' if i==9 else 'none',geometry_aug=False)
def dirs(root,base):
    root=within(root,'/home/jovyan/zzx');base=within(base,root/'records')
    if not base.name.startswith(PREFIX):raise ValueError('unexpected directory')
    return root,base
def make_plan(root,base,commit,parent):
    keys=['data','experts','input_manifest_sha256','expected_configs','augmentation','evaluation','training','fixed_conditions']
    p={k:copy.deepcopy(parent[k]) for k in keys}
    p.update(id='POST_S1_SUPPORT',created_at=now(),execution_commit=commit,physical_gpus=[0],max_gpu_workers=1,
        source_directory=str(root/'records'/SOURCE_NAME),source_execution_commit=SOURCE_COMMIT,
        initial_checkpoint=dict(path=str(root/'records'/SOURCE_NAME/'jobs/S1-0/selected.pth'),sha256=SHAS['S1-0']),
        reference_shas=SHAS,jobs=[job_card(j) for j in ORDER],total_optimizer_steps=80000,primary_candidate='P7',
        runtime=dict(per_job_timeout_hours=24.,cpu_stage_timeout_hours=12.,wait_poll_seconds=5),
        design=dict(head=[264,64,6],head_kernel=[1,3],last_zero_init=True,mask_write='native_after_upsample',
            gates=GATES,E_keys=E_KEYS,E_masks=dict(lines_period=64,lines_width=8,lines_axis='x',origin=0,
            blocks_cell=64,blocks_width=32,blocks_height=32,blocks_offset=[16,16]),
            D1_policies=POLICIES,D1_max_new_tile_units=48,E_tile_units=144,
            Q_reserved=4,Q_auto_training=False,Q_requires_protocol_freeze=True),
        automatic_retry=False,new_seeds=False,test_release=False)
    p['training']['selection']='fixed8000; step4000 diagnostic only'
    p['training']['primary_checkpoint_step']=8000
    p['evaluation']['fixed8000']='22 original ordinary conditions; all32 ordinary at fixed8000 in evaluation; U separate'
    return p
def validate(p):
    if p['id']!='POST_S1_SUPPORT' or p['physical_gpus']!=[0] or p['max_gpu_workers']!=1:raise ValueError('GPU0 single worker required')
    if p['jobs']!=[job_card(j) for j in ORDER] or p['total_optimizer_steps']!=80000 or p['primary_candidate']!='P7':raise ValueError('arm/budget changed')
    t=p['training']
    fixed=dict(steps=8000,seed=42,physical_batch=16,gradient_accumulation=False,views_per_crop=2,head_lr=.0002,encoder_last4_lr=.00002,
        weight_decay=.01,betas=[.9,.999],warmup_steps=100,checkpoint_every=500,validation_steps=[4000,8000],
        selection_states=['clean','dsm_missing','rgb_missing'],primary_checkpoint_step=8000,selection='fixed8000; step4000 diagnostic only',validation_batch=8)
    if any(t[k]!=v for k,v in fixed.items()):raise ValueError('training/selection changed')
    d=p['data']
    if d['validation']!=['3_11','5_10'] or len(d['fit12'])!=12 or set(d['fit12'])&set(d['validation']) or d['test6_loaded'] or d['independent_final_loaded']:raise ValueError('data scope changed')
    if p['initial_checkpoint']['sha256']!=SHAS['S1-0'] or p['reference_shas']!=SHAS or p['source_execution_commit']!=SOURCE_COMMIT or Path(p['source_directory']).name!=SOURCE_NAME:raise ValueError('reference changed')
    if p['automatic_retry'] or p['new_seeds'] or p['test_release']:raise ValueError('release/retry scope changed')
    expected=make_plan(Path('/home/jovyan/zzx/x'),Path('/home/jovyan/zzx/x/records/y'),'x',p)
    if p['design']!=expected['design']:raise ValueError('scientific design changed')
    for k in ('per_job_timeout_hours','cpu_stage_timeout_hours'):hours(p['runtime'][k])
    return p
def source_binding(root,name,checkpoint=True):
    if name not in SHAS:raise ValueError('only four S1 source states')
    source=root/'records'/SOURCE_NAME;folder=source/'jobs'/name;p=read(source/'plan.json');c=read(folder/'complete.json')
    if p['execution_commit']!=SOURCE_COMMIT or c['signature']['execution_commit']!=SOURCE_COMMIT or c['signature']['plan_sha256']!=sha(source/'plan.json') or c['signature']['job']['id']!=name or c['global_step']!=8000 or c['selected']['step']!=8000 or c['selected_checkpoint_sha256']!=SHAS[name] or c['test6_loaded'] or c['independent_final_loaded']:raise RuntimeError('source binding differs '+name)
    for tag in ('evaluation','fixed8000','support_evaluation','support_fixed8000'):
        if sha(folder/tag/'summary.json')!=c[tag+'_summary_sha256']:raise RuntimeError('source summary changed '+name+'/'+tag)
    if checkpoint and sha(folder/'selected.pth')!=SHAS[name]:raise RuntimeError('source checkpoint changed '+name)
    return dict(model=name,checkpoint_sha256=SHAS[name],complete_sha256=sha(folder/'complete.json'),source_plan_sha256=sha(source/'plan.json')),p,c
def released(root):
    from d30_common import live_owned,lock_free
    from post_n3_s1_common import complete_job
    source=root/'records'/SOURCE_NAME;s=read(source/'queue_status.json');p=read(source/'plan.json')
    ids=[f'N3-{i}' for i in range(5)]+[f'S1-{i}' for i in range(4)]
    if s['status']!='N3_S1_COMPLETE_AWAITING_REVIEW' or set(s['jobs'])!=set(ids) or any(x['status']!='COMPLETE' for x in s['jobs'].values()):raise RuntimeError('original queue not complete')
    if live_owned(s.get('controller_pid',-1),source) or any(live_owned(x.get('pid',-1),source) for x in s['jobs'].values()) or not lock_free(source):raise RuntimeError('original queue still owns workers/lock')
    if p['execution_commit']!=SOURCE_COMMIT:raise RuntimeError('original science commit differs')
    verify_snapshot(source)
    for j in ids:complete_job(source,j,p)
    bindings={name:source_binding(root,name)[0] for name in SHAS}
    return dict(last_observed=s['observed_at'],queue_sha256=sha(source/'queue_status.json'),bindings=bindings,checked_at=now())
def initial_state(p):
    return dict(status='REGISTERED',observed_at=now(),CPU='PENDING',D1='PENDING',E='PENDING',
        jobs={j:dict(status='PENDING',gpu=0) for j in ['D1']+ORDER+['E']},Q='RESERVED_NOT_AUTOMATIC')
def signature(base,p,job):
    return dict(execution_commit=p['execution_commit'],plan_sha256=sha(base/'plan.json'),
        code_manifest_sha256=sha(base/'code_manifest.json'),mask_manifest_sha256=sha(base/'mask_manifest.json'),
        initial_checkpoint_sha256=SHAS['S1-0'],job=job,physical_gpu=0,
        primary_checkpoint_step=8000,test6_loaded=False,independent_final_loaded=False)
def accept_worker(base,task,p):
    f=base/'jobs'/task;c=read(f/'complete.json')
    if c['execution_commit']!=p['execution_commit'] or c['plan_sha256']!=sha(base/'plan.json') or c['code_manifest_sha256']!=sha(base/'code_manifest.json'):raise RuntimeError('worker completion binding differs '+task)
    if c['test6_loaded'] or c['independent_final_loaded']:raise RuntimeError('forbidden split')
    for path,digest in c['artifacts'].items():
        if sha(within(f/path,f))!=digest:raise RuntimeError('worker artifact changed '+task+'/'+path)
    if task in ORDER:
        job=next(j for j in p['jobs'] if j['id']==task)
        if c['signature']!=signature(base,p,job) or c['global_step']!=8000 or c['selected']['step']!=8000:raise RuntimeError('training binding differs '+task)
    elif c['optimizer_updates']!=0:raise RuntimeError('diagnostic trained')
    return c
