"""Frozen six-cell N2 stage; old 26 reservations are not mutated or restarted."""
import copy
from post_ab_n2_recovery import timeout_hours
from pathlib import Path
from post_ab_queue_common import read,write,sha,within,now,predecessor_verdict
PREFIX='research_post_ab_followup_n2_'
N2=[f'N2-{i}' for i in range(6)]
MODES=['spatial','height','semantic','bilateral','shuffle_height','shuffle_semantic']
BASE_SHA='28bc6f8ca5e1221392598b0a6f2d160e8c633a6a9cf63827067df3e7b81a144b'
N1_PLAN_SHA='be8a81b8b1c24833d5221b23dce30c949061a05923725c4126342f956c43359f'
def directories(root,base):
    root=within(root,'/home/jovyan/zzx');base=within(base,root/'records')
    if not base.name.startswith(PREFIX):raise ValueError('unexpected N2 directory')
    return root,base
def runtime_plan(parent,commit,base):
    p=copy.deepcopy(parent)
    src=base.parent/'research_post_ab_followup_20261004T185950_3029215'
    p.update(id='POST_AB_N2_RELATION',execution_commit=commit,protocol='docs/protocols/POST_AB_N2_EXECUTION_20261005.md',
        unique_training_jobs=6,currently_executable_training_jobs=6,total_optimizer_steps=48000,initial_stage_optimizer_steps=48000,
        automatic_followup='N2 only; review before N3/N4/N5',source_N1_directory=str(src),source_N1_plan_sha256=N1_PLAN_SHA)
    p['jobs']=[dict(id=j,phase='N2',gpu=i%2,steps=8000,seed=42,priority=i,executable=True,
        name=MODES[i],relation_mode=MODES[i],information_entry='late',adaptation='last4_and_heads',
        initial_checkpoint_path=str(src/'jobs/N1-2/selected.pth'),initial_checkpoint_sha256=BASE_SHA,
        dependency='N1 complete/raw counts audited; fixed N1-2 base') for i,j in enumerate(N2)]
    p['relation_contract']=dict(stride=16,window=3,height_coefficient=4.,semantic_coefficient=2.,residual_scale=.1,
        shuffle='half_grid_roll_affinity_fields',semantic_gradient='detached',both_valid_required=True)
    p['development_gates']={'N2':dict(vs_spatial_pp=.3,directional_and_shuffle_pp=.2,clean_missing_floor_pp=-.1,worst_tile_floor_pp=-.2)}
    p['runtime']['estimated_hours']=None
    p['runtime']['per_job_timeout_hours']=8
    p['runtime']['queue']='GPU0 N2-0/2/4; GPU1 N2-1/3/5, one worker per card'
    p.setdefault('design',{}).setdefault('followup_reservations',{})['N2']='activated six-cell matched N1-2 stage; see POST_AB_N2_EXECUTION_20261005.md'
    p['new_unimodal_training']=0
    return p
def validate_plan(p):
    timeout_hours(p['runtime'].get('per_job_timeout_hours'))
    if [j['id'] for j in p['jobs']]!=N2:raise ValueError('six N2 arms changed')
    t=p['training']
    if t['steps']!=8000 or t['seed']!=42 or t['physical_batch']!=16 or t['gradient_accumulation']:raise ValueError('budget changed')
    if p['physical_gpus']!=[0,1] or p['data']['validation']!=['3_11','5_10']:raise ValueError('devices/split changed')
    if p['data']['test6_loaded'] or p['data']['independent_final_loaded']:raise ValueError('final opened')
    if t['validation_steps']!=[4000,8000] or t['selection_states']!=['clean','dsm_missing','rgb_missing']:raise ValueError('selection changed')
    if p['source_N1_plan_sha256']!=N1_PLAN_SHA:raise ValueError('N1 binding changed')
    if p['relation_contract']!=dict(stride=16,window=3,height_coefficient=4.,semantic_coefficient=2.,residual_scale=.1,
        shuffle='half_grid_roll_affinity_fields',semantic_gradient='detached',both_valid_required=True):raise ValueError('relation settings changed')
    for i,j in enumerate(p['jobs']):
        if j['relation_mode']!=MODES[i] or j['gpu']!=i%2 or j['steps']!=8000 or j['seed']!=42 or not j['executable']:raise ValueError('arm contract changed')
        if j['information_entry']!='late' or j['adaptation']!='last4_and_heads' or j['initial_checkpoint_sha256']!=BASE_SHA:raise ValueError('base changed')
        if Path(j['initial_checkpoint_path'])!=Path(p['source_N1_directory'])/'jobs/N1-2/selected.pth':raise ValueError('base path changed')
    return p['jobs']
def next_job(state,gpu):
    return next((j for j in N2 if state['jobs'][j]['gpu']==gpu and state['jobs'][j]['status']=='PENDING'),None)
def initial_state(p):
    return dict(status='REGISTERED_N2',observed_at=now(),jobs={j['id']:dict(status='PENDING',gpu=j['gpu'],phase='N2') for j in p['jobs']},evaluations={})

