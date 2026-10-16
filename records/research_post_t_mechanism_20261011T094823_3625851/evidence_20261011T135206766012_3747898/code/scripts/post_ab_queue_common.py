"""Conditional reservations and strict first-stage handover contracts."""
import copy
from pathlib import Path
from d24_common import read,write,sha,within,now
PREFIX='research_post_ab_followup_'
PREDECESSOR='research_post_d30_mechanisms_20261004T000812_2446364'
FAMILIES={'N1':4,'N2':6,'N3':5,'N4':4,'N5':4,'N6':3}
NAMES={
 'N1':['late_frozen','depth_scale_frozen','late_last4_heads','depth_scale_last4_heads'],
 'N2':['spatial_relation','height_to_rgb','semantic_to_dsm','bilateral_relation','shuffle_height_relation','shuffle_semantic_relation'],
 'N3':['pixel_aggregation','fixed_grid','rgb_regions','dsm_regions','bilateral_regions'],
 'N4':['original_allocation','fixed_quota','quota_loss_weights','bounded_dynamic_allocation'],
 'N5':['original_missingness','matched_random_missingness','content_missingness','half_random_half_content'],
 'N6':['unimodal_teacher','common_correct_unimodal_teacher','common_correct_multimodal_teacher']}
IDS=[f'{family}-{i}' for family,count in FAMILIES.items() for i in range(count)]
N1=IDS[:4]

def directories(root,base):
    root=within(root,'/home/jovyan/zzx');base=within(base,root/'records')
    if not base.name.startswith(PREFIX):raise ValueError('unexpected successor directory')
    return root,base

def runtime_plan(parent,commit,directory):
    p=copy.deepcopy(parent)
    p.update(id='POST_AB_CONDITIONAL_QUEUE',execution_commit=commit,execution_authorized=True,
             predecessor_directory=str(directory.parent/PREDECESSOR),
             protocol='docs/protocols/POST_AB_QUEUE_EXECUTION_20261004.md',
             unique_training_jobs=26,currently_executable_training_jobs=4,
             total_optimizer_steps=208000,initial_stage_optimizer_steps=32000,
             automatic_followup='N1 only; later stages reserved pending matched implementation and evidence')
    p['jobs']=[]
    for family,count in FAMILIES.items():
        for i in range(count):
            row=dict(id=f'{family}-{i}',phase=family,gpu=i%2,steps=8000,seed=42,
                     name=NAMES[family][i],priority=len(p['jobs']),executable=family=='N1',
                     dependency='original queue COMPLETE and released' if family=='N1' else 'stage result/implementation specified in followup_reservations')
            if family=='N1':row.update(information_entry='encoder_depth_scale' if i%2 else 'late',adaptation='last4_and_heads' if i>=2 else 'frozen')
            p['jobs'].append(row)
    p['runtime']['estimated_hours']=None
    p['runtime']['queue']='Post-D30 released -> offline E0 -> N1 four cells -> evidence handoff; conditional reservations N2-N6'
    p['repeat_resource_probe']=False;p['new_unimodal_training']=0
    p['design']['followup_reservations']={
        'N2':'matched base specified by N1 screen; exact relation implementation pending',
        'N3':'alternative to stacking N2; exact region partition and historical D12 comparison pending',
        'N4':'requires exposure evidence distinct from D8, sampler/update logs and frozen protocol',
        'N5':'requires E1 matched-content missingness gap and frozen train/eval mask definitions',
        'N6':'requires original C2 bilateral gate and frozen matched teacher implementation'}
    p['development_gates']={'N1':dict(vs_N1_1_pp=.3,vs_N1_2_pp=.3,clean_missing_floor_pp=-.1,worst_tile_floor_pp=-.2,tile_same_sign=True,fixed_same_sign=True)}
    return p

def validate_plan(p):
    if [j['id'] for j in p['jobs']]!=IDS:raise ValueError('26 reservations changed')
    t=p['training']
    if t['steps']!=8000 or t['seed']!=42 or t['physical_batch']!=16 or t['gradient_accumulation']:raise ValueError('training differs')
    if p['physical_gpus']!=[0,1] or p['data']['validation']!=['3_11','5_10']:raise ValueError('devices/split differ')
    if p['data']['test6_loaded'] or p['data']['independent_final_loaded']:raise ValueError('final opened')
    if t['validation_steps']!=[4000,8000] or t['selection_states']!=['clean','dsm_missing','rgb_missing']:raise ValueError('selection differs')
    for family,count in FAMILIES.items():
        rows=[j for j in p['jobs'] if j['phase']==family]
        if len(rows)!=count or [j['id'] for j in rows]!=[f'{family}-{i}' for i in range(count)]:raise ValueError('family differs')
        if any(j['gpu']!=i%2 or j['steps']!=8000 or j['seed']!=42 or j['executable']!=(family=='N1') for i,j in enumerate(rows)):raise ValueError('job contract differs')
    for i,j in enumerate(p['jobs'][:4]):
        if j['information_entry']!=('encoder_depth_scale' if i%2 else 'late') or j['adaptation']!=('last4_and_heads' if i>=2 else 'frozen'):raise ValueError('factorial cell changed')
    return p['jobs']

def predecessor_verdict(state,released,workers_live,controller_live):
    jobs=state.get('jobs',{});main=[f'A{i}' for i in range(6)]+[f'B{i}' for i in range(1,7)]+[f'C{i}' for i in range(6)]
    if state.get('status')=='COMPLETE':
        if any(jobs.get(j,{}).get('status')!='COMPLETE' for j in main):return 'HOLD_INVALID_PREDECESSOR_COMPLETE'
        if any(jobs.get(f'F{i}',{}).get('status')!='SKIPPED_GATE' for i in range(4)):return 'HOLD_UNEXPECTED_F_STATUS'
        return 'READY' if released and not workers_live and not controller_live else 'WAITING_PREDECESSOR_RELEASE'
    if any(j.get('status') in ('TECHNICAL_FAILURE','TIMEOUT') for j in jobs.values()) or 'FAILURE' in state.get('status',''):
        return 'HOLD_PREDECESSOR_FAILURE'
    if not controller_live:return 'HOLD_PREDECESSOR_STOPPED'
    return 'WAITING_PREDECESSOR'

def next_job(state,gpu):
    return next((j for j in N1 if state['jobs'][j]['gpu']==gpu and state['jobs'][j]['status']=='PENDING'),None)

def initial_state(plan):
    return dict(status='REGISTERED_WAITING_PREDECESSOR',observed_at=now(),jobs={j['id']:dict(status='PENDING' if j['executable'] else 'RESERVED_PROTOCOL_PENDING',gpu=j['gpu'],phase=j['phase'],executable=j['executable']) for j in plan['jobs']},
                evaluations={'E0':'WAITING_PREDECESSOR','E1':'RESERVED_CONDITION_PROTOCOL_PENDING'})
