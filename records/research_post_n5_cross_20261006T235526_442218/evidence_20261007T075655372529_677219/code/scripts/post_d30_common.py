"""Standard-library contracts for the post-D30 mechanism portfolio."""
import copy
from pathlib import Path
from d24_common import read,write,sha,within,now
PREDECESSOR='research_d30_loss_decomposition_20261003T205144_2349167'
PREFIX='research_post_d30_mechanisms_'
PHASES={'A':['A0','A1','A2','A3','A4','A5'],'B':['B1','B2','B3','B4','B5','B6'],
        'C':['C0','C1','C2','C3','C4','C5'],'F':['F0','F1','F2','F3']}
IDS=sum(PHASES.values(),[])

def directories(root,base):
    root=within(root,'/home/jovyan/zzx');base=within(base,root/'records')
    if not base.name.startswith(PREFIX):raise ValueError('unexpected portfolio directory')
    return root,base

def runtime_plan(parent,design,commit,base):
    p=copy.deepcopy(parent)
    p.update(id='POST_D30_MECHANISMS',execution_commit=commit,design=design,jobs=design['jobs'],
             unique_training_jobs=18,total_optimizer_steps=144000,conditional_optimizer_steps=32000,
             predecessor_directory=str(base.parent/PREDECESSOR),automatic_followup='F only if frozen B3 gate passes')
    p['protocol']='docs/protocols/POST_D30_EXECUTION_20261003.md'
    p['status']='EXECUTION_CONFIGURED'
    p.pop('initial_fusion_sha256',None);p.pop('primary_candidate',None)
    p['runtime']['queue']='D30 released -> A -> B -> C -> conditional F, GPU0/1 only'
    # Isolate NEW small-shift augmentation from historical aux_shift8. All new arms share this quality stream.
    p['augmentation']['dsm']=['aux_down4','aux_noise_std010'];p['architecture']=design['architecture']
    existing=set(p['evaluation']['primary']+p['evaluation']['missing']+sum(p['evaluation']['local'].values(),[])+p['evaluation']['diagnostic'])
    p['evaluation']['diagnostic']+=[c for c in design['geometry_conditions']+design['missing_conditions'] if c not in existing]
    p['training']['selection_states']=['clean','dsm_missing','rgb_missing']
    p['runtime']['estimated_hours']=[17,25];p['runtime']['per_job_timeout_hours']=None;p['development_gates']=design['gates']
    p['repeat_resource_probe']=False;p['new_unimodal_training']=0
    return p

def validate_plan(p):
    if [j['id'] for j in p['jobs']]!=IDS:raise ValueError('frozen 18+4 jobs differ')
    t=p['training']
    if t['steps']!=8000 or t['physical_batch']!=16 or t['gradient_accumulation'] or t['seed']!=42:raise ValueError('matched training differs')
    if p['physical_gpus']!=[0,1] or p['data']['validation']!=['3_11','5_10']:raise ValueError('devices/split differ')
    if p['data']['test6_loaded'] or p['data']['independent_final_loaded']:raise ValueError('unopened final evaluation')
    if t['validation_steps']!=[4000,8000] or t['selection_states']!=['clean','dsm_missing','rgb_missing']:raise ValueError('checkpoint selection differs')
    if any(j['gpu'] not in (0,1) or j['steps']!=8000 or j['seed']!=42 for j in p['jobs']):raise ValueError('job device/budget differs')
    return p['jobs']

def predecessor_verdict(state,released,live_workers,controller_live):
    expected={'replay_G0','replay_G1','P','R','PR_area','PR_pixel'}
    if state.get('status')=='COMPLETE':
        if set(state.get('jobs',{}))!=expected or any(r['status']!='COMPLETE' for r in state['jobs'].values()):return 'HOLD_INVALID_PREDECESSOR_COMPLETE'
        return 'READY' if released and not live_workers else 'WAITING_D30_RELEASE'
    if 'FAILURE' in state.get('status','') or not controller_live:return 'HOLD_D30_STOPPED_OR_FAILED'
    return 'WAITING_D30'

def next_job(state,gpu,phase):
    return next((j for j in PHASES[phase] if state['jobs'][j]['gpu']==gpu and state['jobs'][j]['status']=='PENDING'),None)
