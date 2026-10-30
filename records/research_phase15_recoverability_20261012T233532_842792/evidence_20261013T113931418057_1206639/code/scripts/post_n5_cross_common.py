"""Frozen inference-only post-N5 contracts; no GPU imports."""
import copy,math
from pathlib import Path
from post_n2_diag_common import read,write,sha,now,within,verify_snapshot,N1_NAME,N2_NAME
from post_n5_common import released as old_released,DIAG_NAME
N5_NAME='research_post_n5_20261006T114819_71934'
PREFIX='research_post_n5_cross_'
JOBS=[('E4_N1-2',0,'N1-2'),('E4_N2-0',1,'N2-0'),('E4_N2-3',0,'N2-3')]
PATHS=[f'A{a}B{b}C{c}' for a in (0,1) for b in (0,1) for c in (0,1)]
def dirs(root,base):
    root=within(root,'/home/jovyan/zzx');base=within(base,root/'records')
    if not base.name.startswith(PREFIX):raise ValueError('unexpected cross diagnostic directory')
    return root,base
def hours(v):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:raise ValueError('positive finite timeout required')
    return float(v)
def make_plan(root,base,commit,parent):
    return dict(id='POST_N5_CROSS_DIAGNOSTICS',created_at=now(),execution_commit=commit,
        data=copy.deepcopy(parent['data']),experts=copy.deepcopy(parent['experts']),
        input_manifest_sha256=parent['input_manifest_sha256'],expected_configs=copy.deepcopy(parent['expected_configs']),
        source_N5_directory=str(root/'records'/N5_NAME),source_diag_directory=str(root/'records'/DIAG_NAME),
        jobs=[dict(id=j,gpu=g,model=m) for j,g,m in JOBS],paths=PATHS,
        E4=dict(cases=['known_missing','false_positive'],directions=['rgb','dsm'],rule='U',gap_pp=.5,
            gate_models=['N1-2','N2-0'],gate_direction='rgb',max_tile_units=192),
        E3=dict(models=['A0','B1','N5-0','N5-3'],rules=['U','H','L'],directions=['rgb','dsm'],
            class_ids=list(range(5)),boundary_radius=4,min_stratum_pixels=100,weight_source='whole valid fg5 tile; Full boundary partition',
            standardization_scope='noboundary',labels_forward=False),
        E0=dict(boundary_radius=4,min_anchor_pixels=100,min_single_correct_pixels=100,boundary_harm_gap_pp=1.,diagnostic_gate_scope='full'),
        physical_gpus=[0,1],seed=42,new_optimizer_updates=0,automatic_training=False,
        selection='read-only selected checkpoints; no new selection',
        runtime=dict(per_job_timeout_hours=8.,cpu_stage_timeout_hours=6.,wait_poll_seconds=5))
def validate(p):
    if p['id']!='POST_N5_CROSS_DIAGNOSTICS' or p['seed']!=42 or p['new_optimizer_updates']!=0 or p['automatic_training']:raise ValueError('diagnostic scope changed')
    if [(x['id'],x['gpu'],x['model']) for x in p['jobs']]!=JOBS or p['paths']!=PATHS or p['physical_gpus']!=[0,1]:raise ValueError('dispatch changed')
    d=p['data']
    if d['validation']!=['3_11','5_10'] or len(d['fit12'])!=12 or set(d['fit12'])&set(d['validation']) or d['test6_loaded'] or d['independent_final_loaded']:raise ValueError('data scope changed')
    expected=make_plan(Path('/home/jovyan/zzx/x'),Path('/home/jovyan/zzx/x/records/y'),'x',p)
    for key in ('E0','E3','E4'):
        if p[key]!=expected[key]:raise ValueError('fixed '+key+' contract changed')
    if Path(p['source_N5_directory']).name!=N5_NAME or Path(p['source_diag_directory']).name!=DIAG_NAME:raise ValueError('source directory changed')
    for key in ('per_job_timeout_hours','cpu_stage_timeout_hours'):hours(p['runtime'][key])
    if p['runtime']['wait_poll_seconds']!=5:raise ValueError('poll changed')
    return p
def initial_state(p):
    return dict(status='REGISTERED',observed_at=now(),optimizer_updates=0,CPU='PENDING',
        jobs={j['id']:dict(status='PENDING',gpu=j['gpu'],model=j['model']) for j in p['jobs']})
def n5_binding(root,name):
    if name not in ('N5-0','N5-3'):raise ValueError('fixed N5 models only')
    base=root/'records'/N5_NAME;folder=base/'jobs'/name;p=read(base/'plan.json');c=read(folder/'complete.json')
    if p['execution_commit']!='2e565cca04d84d8605a96105d12fb6c0871e464d' or c['signature']['execution_commit']!=p['execution_commit'] or c['signature']['plan_sha256']!=sha(base/'plan.json') or c['signature']['job']['id']!=name or c['global_step']!=8000 or c['test6_loaded'] or c['independent_final_loaded']:raise RuntimeError('N5 source binding invalid')
    for tag in ('evaluation','fixed8000','content_evaluation','content_fixed8000'):
        if c[tag+'_summary_sha256']!=sha(folder/tag/'summary.json'):raise RuntimeError('N5 source summary changed')
    return dict(directory=str(base),model=name,complete_sha256=sha(folder/'complete.json'),
        plan_sha256=sha(base/'plan.json'),selected_checkpoint_sha256=c['selected_checkpoint_sha256']),p,c
def released(root):
    from d30_common import live_owned,lock_free
    previous=old_released(root);base=root/'records'/N5_NAME;s=read(base/'queue_status.json')
    if s['status']!='N5_COMPLETE_AWAITING_REVIEW' or set(s['jobs'])!={f'N5-{i}' for i in range(4)} or any(x['status']!='COMPLETE' for x in s['jobs'].values()):raise RuntimeError('N5 incomplete; do not launch duplicate successors')
    if live_owned(s.get('controller_pid',-1),base) or any(live_owned(x.get('pid',-1),base) for x in s['jobs'].values()) or not lock_free(base):raise RuntimeError('N5 still owned/live')
    # Bind all four N5 completions, including two not reanalysed spatially.
    p=read(base/'plan.json')
    for i in range(4):
        folder=base/'jobs'/f'N5-{i}';c=read(folder/'complete.json')
        if c['signature']['plan_sha256']!=sha(base/'plan.json') or c['signature']['execution_commit']!=p['execution_commit'] or c['global_step']!=8000 or c['test6_loaded'] or c['independent_final_loaded']:raise RuntimeError('N5 completion changed')
        for tag in ('evaluation','fixed8000','content_evaluation','content_fixed8000'):
            if sha(folder/tag/'summary.json')!=c[tag+'_summary_sha256']:raise RuntimeError('N5 summary changed')
    return dict(previous=previous,N5_queue_sha256=sha(base/'queue_status.json'),N5_observed_at=s['observed_at'],checked_at=now())
def complete_job(base,j,p):
    folder=base/'jobs'/j;c=read(folder/'complete.json')
    signature=c['signature'];job=next(x for x in p['jobs'] if x['id']==j)
    if signature['job']!=job or signature['plan_sha256']!=sha(base/'plan.json') or signature['code_manifest_sha256']!=sha(base/'code_manifest.json') or signature['execution_commit']!=p['execution_commit'] or c['optimizer_updates']!=0 or c['inference_tile_units']!=64 or c['test6_loaded'] or c['independent_final_loaded']:raise RuntimeError('invalid worker completion '+j)
    if c['summary_sha256']!=sha(folder/'summary.json'):raise RuntimeError('worker summary changed')
    return c
