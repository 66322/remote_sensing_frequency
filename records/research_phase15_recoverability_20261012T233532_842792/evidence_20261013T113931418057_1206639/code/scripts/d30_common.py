"""D30 contract and safe predecessor handover; standard library only."""
import copy
from pathlib import Path
from d24_common import read, write, sha, within, now
D27_COMMIT = 'ba7088ec05be7b85dd45e5896a8407506bcca14d'
D27_NAME = 'research_d27_safe_routing_repair_20261003T092243758628_2001983'
D28_NAME = 'research_d28_pressure_20261003T092243758628_2001983'
INITIAL_SHA = '16abcd8338a0fae16584d6a70030cb1db5c8a3df741ba7076da77e12e9432281'
TRAIN_IDS = ('P', 'R', 'PR_area', 'PR_pixel')
REPLAY_IDS = ('replay_G0', 'replay_G1')
D28_IDS = {'RGB_anchor','DSM_anchor','D26_B0','D27_S1','D27_G0','D27_G1','D27_L1'}

def directories(root, base):
    root=within(root,'/home/jovyan/zzx');base=within(base,root/'records')
    if not base.name.startswith('research_d30_loss_decomposition_'):raise ValueError('unexpected D30 directory')
    return root,base

def runtime_plan(parent, design, commit, predecessor, source_dir):
    from d27_common import validate_plan as validate_parent
    validate_parent(parent)
    if parent['execution_commit'] != D27_COMMIT:raise ValueError('D27 execution changed')
    p=copy.deepcopy(parent)
    p.update(id='D30_LOSS_DECOMPOSITION',status='EXECUTION_CONFIGURED',execution_commit=commit,
             parent_D27_directory=str(source_dir),predecessor_directory=str(predecessor),
             design=design,source_D27_plan_sha256=None,unique_training_jobs=4,total_optimizer_steps=32000,
             directory_pattern='records/research_d30_loss_decomposition_<timestamp>_<pid>',
             automatic_followup=False)
    p['jobs']=[dict(id=j,steps=8000,seed=42,optimizer_steps=8000,gpu=g,priority=i)
               for i,(j,g) in enumerate(zip(TRAIN_IDS,(0,1,0,1)))]
    p['runtime']['queue']='D28 COMPLETE and released lock, replay wave then two training lanes GPU0/1'
    p['runtime']['estimated_hours']=[3.5,4.5]
    p['development_gates']=design['analysis']['continuation_screen']
    p['initial_fusion_sha256']=INITIAL_SHA
    return p

def validate_plan(p):
    if tuple(j['id'] for j in p['jobs'])!=TRAIN_IDS:raise ValueError('four fixed D30 jobs required')
    t=p['training']
    if t['steps']!=8000 or t['physical_batch']!=16 or t['gradient_accumulation'] or t['seed']!=42:raise ValueError('training budget changed')
    if p['physical_gpus']!=[0,1] or p['total_optimizer_steps']!=32000:raise ValueError('devices/updates changed')
    if [j['gpu'] for j in p['jobs']]!=[0,1,0,1] or any(j['steps']!=8000 or j['seed']!=42 for j in p['jobs']):raise ValueError('job contract changed')
    if p['data']['validation']!=['3_11','5_10'] or p['data']['test6_loaded'] or p['data']['independent_final_loaded']:raise ValueError('evaluation scope changed')
    if t['validation_steps']!=[4000,8000] or t['selection_states']!=['clean','dsm_missing','rgb_missing']:raise ValueError('selection changed')
    if p['initial_fusion_sha256']!=INITIAL_SHA:raise ValueError('initialization binding changed')
    return p['jobs']

def live_owned(pid, base):
    p=Path('/proc')/str(pid)/'cmdline'
    try:return p.is_file() and str(base).encode() in p.read_bytes()
    except FileNotFoundError:return False

def lock_free(parent):
    import fcntl
    p=Path(parent)/'controller.lock'
    if not p.is_file():raise RuntimeError('predecessor lock missing')
    with p.open('r') as f:
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return False
        return True

def predecessor_verdict(state, released, workers_live, controller_live):
    if state.get('status')=='COMPLETE_WITH_TECHNICAL_FAILURES':return 'HOLD_PREDECESSOR_FAILURE'
    if state.get('status')=='COMPLETE':
        if set(state.get('jobs',{}))!=D28_IDS or any(r.get('status')!='COMPLETE' for r in state['jobs'].values()):
            return 'HOLD_INVALID_COMPLETE'
        return 'READY' if released and not workers_live else 'WAITING_D28_RELEASE'
    if not controller_live:return 'HOLD_PREDECESSOR_STOPPED'
    return 'WAITING_D28'

def next_job(state, gpu, phase):
    ids=REPLAY_IDS if phase=='replay' else TRAIN_IDS
    return next((j for j in ids if state['jobs'][j]['gpu']==gpu and state['jobs'][j]['status']=='PENDING'),None)

