"""Immutable inference-only successor contracts; stdlib, no GPU initialization."""
import hashlib,json,math,os
from datetime import datetime
from pathlib import Path
PREFIX='research_post_n2_diagnostics_'
N2_NAME='research_post_ab_followup_n2_20261005T085829_3456726'
N1_NAME='research_post_ab_followup_20261004T185950_3029215'
POST_NAME='research_post_d30_mechanisms_20261004T000812_2446364'
SCIENCE='86b6a70e5c3482314986fb1259e2fccbd0a5a38b'
BASE_SHA='28bc6f8ca5e1221392598b0a6f2d160e8c633a6a9cf63827067df3e7b81a144b'
JOBS=[('E1_A0',0,'A0','E1'),('E1_B1',1,'B1','E1'),('E2_N1-2',0,'N1-2','E2'),('E2_N2-0',1,'N2-0','E2'),('E2_N2-3',0,'N2-3','E2')]
def now():return datetime.now().astimezone().isoformat()
def read(path):return json.loads(Path(path).read_text())
def write(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.writing_'+str(os.getpid()))
    tmp.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n');os.replace(tmp,path)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()
def within(path,parent):
    path=Path(path).resolve();path.relative_to(Path(parent).resolve());return path
def dirs(root,base):
    root=within(root,'/home/jovyan/zzx');base=within(base,root/'records')
    if not base.name.startswith(PREFIX):raise ValueError('unexpected diagnostic directory')
    return root,base
def limit_hours(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:raise ValueError('finite positive timeout required')
    return float(value)
def make_plan(root,base,commit,parent):
    return dict(id='POST_N2_DIAGNOSTICS',execution_commit=commit,predecessor_directory=str(root/'records'/N2_NAME),predecessor_execution_commit=SCIENCE,
        data=parent['data'],experts=parent['experts'],input_manifest_sha256=parent['input_manifest_sha256'],expected_configs=parent['expected_configs'],
        primary=parent['evaluation']['primary'],physical_gpus=[0,1],seed=42,new_optimizer_updates=0,selection='reuse selected checkpoints; never select on new conditions',
        masks=dict(rules=['U','H','L'],reserved_rule='T',fraction=.25,cell=128,block=64,offset_fractions=[.125,.375],score_window=5,component_connectivity=4,whole_tile=True,fit_sample_stride=16),
        E0_models=['A0','B1','N1-0','N1-2']+[f'N2-{i}' for i in range(6)],E0=dict(boundary_radius=4,min_anchor_pixels=100,min_single_correct_pixels=100,boundary_harm_gap_pp=1.,diagnostic_gate_scope='full',small_object_fit_quantile=.25),
        E1=dict(models=['A0','B1'],directions=['rgb','dsm'],rules=['U','H','L'],initial_tile_units=24,gap_pp=.5,trigger_rules=['H','L']),
        E2=dict(models=['N1-2','N2-0','N2-3'],directions=['rgb','dsm'],cases=['clean','false_positive','known_missing','false_negative'],max_tile_units=48,gap_pp=.5),
        runtime=dict(per_job_timeout_hours=8.,cpu_stage_timeout_hours=4.,wait_poll_seconds=30),
        jobs=[dict(id=j,gpu=g,model=m,stage=s) for j,g,m,s in JOBS],automatic_training=False,created_at=now())
def validate(p):
    if p['id']!='POST_N2_DIAGNOSTICS' or p['new_optimizer_updates']!=0 or p['automatic_training'] or p['seed']!=42:raise ValueError('inference-only contract changed')
    if p['physical_gpus']!=[0,1] or p['data']['validation']!=['3_11','5_10'] or p['data']['test6_loaded'] or p['data']['independent_final_loaded']:raise ValueError('scope changed')
    if len(p['data']['fit12'])!=12 or set(p['data']['fit12'])&set(p['data']['validation']):raise ValueError('split overlap')
    if [(j['id'],j['gpu'],j['model'],j['stage']) for j in p['jobs']]!=JOBS:raise ValueError('diagnostic task list changed')
    m=p['masks']
    if m!=dict(rules=['U','H','L'],reserved_rule='T',fraction=.25,cell=128,block=64,offset_fractions=[.125,.375],score_window=5,component_connectivity=4,whole_tile=True,fit_sample_stride=16):raise ValueError('mask contract changed')
    if p['E1']!=dict(models=['A0','B1'],directions=['rgb','dsm'],rules=['U','H','L'],initial_tile_units=24,gap_pp=.5,trigger_rules=['H','L']):raise ValueError('E1 gate changed')
    if p['E2']!=dict(models=['N1-2','N2-0','N2-3'],directions=['rgb','dsm'],cases=['clean','false_positive','known_missing','false_negative'],max_tile_units=48,gap_pp=.5):raise ValueError('E2 changed')
    if p['E0_models']!=['A0','B1','N1-0','N1-2']+[f'N2-{i}' for i in range(6)]:raise ValueError('E0 selection changed')
    if p['E0']!=dict(boundary_radius=4,min_anchor_pixels=100,min_single_correct_pixels=100,boundary_harm_gap_pp=1.,diagnostic_gate_scope='full',small_object_fit_quantile=.25):raise ValueError('E0 changed')
    if Path(p['predecessor_directory']).name!=N2_NAME or p['predecessor_execution_commit']!=SCIENCE:raise ValueError('N2 source changed')
    limit_hours(p['runtime']['per_job_timeout_hours']);limit_hours(p['runtime']['cpu_stage_timeout_hours'])
    if p['runtime']['wait_poll_seconds']!=30:raise ValueError('poll contract changed')
    return p
def model_folder(root,name):
    if name in ('A0','B1'):b=root/'records'/POST_NAME
    elif name in ('N1-0','N1-2'):b=root/'records'/N1_NAME
    elif name in [f'N2-{i}' for i in range(6)]:b=root/'records'/N2_NAME
    else:raise ValueError('unlisted model')
    return b,b/'jobs'/name
def bind_model(root,name,checkpoint=True):
    base,folder=model_folder(root,name);p=read(base/'plan.json');c=read(folder/'complete.json')
    if c['global_step']!=8000 or c['signature']['plan_sha256']!=sha(base/'plan.json') or c['signature']['execution_commit']!=p['execution_commit'] or c.get('test6_loaded',True) or c.get('independent_final_loaded',True):raise RuntimeError('source completion invalid '+name)
    for tag in ('evaluation','fixed8000'):
        if sha(folder/tag/'summary.json')!=c[tag+'_summary_sha256']:raise RuntimeError('source summary changed '+name)
    if checkpoint and sha(folder/'selected.pth')!=c['selected_checkpoint_sha256']:raise RuntimeError('source selected changed '+name)
    if name=='N1-2' and c['selected_checkpoint_sha256']!=BASE_SHA:raise RuntimeError('fixed base changed')
    if name.startswith('N2-') and p['execution_commit']!=SCIENCE:raise RuntimeError('N2 science changed')
    return dict(model=name,directory=str(base),plan_sha256=sha(base/'plan.json'),execution_commit=p['execution_commit'],complete_sha256=sha(folder/'complete.json'),checkpoint_sha256=c['selected_checkpoint_sha256'],selected_step=c['selected']['step']),p,c
def next_job(state,gpu,stage):return next((j for j,g,_,s in JOBS if g==gpu and s==stage and state['jobs'][j]['status']=='PENDING'),None)
def predecessor_verdict(state,controller_live,workers_live,released):
    jobs=state.get('jobs',{})
    if any(r.get('status') in ('TIMEOUT','TECHNICAL_FAILURE') for r in jobs.values()) or state.get('status','').startswith('HOLD'):return 'HOLD_N2_FAILURE'
    if state.get('status')=='N2_COMPLETE_AWAITING_STAGE_PROTOCOL':
        if set(jobs)!=set(f'N2-{i}' for i in range(6)) or any(r['status']!='COMPLETE' for r in jobs.values()):return 'HOLD_INVALID_N2_COMPLETE'
        return 'READY' if not controller_live and not workers_live and released else 'WAITING_N2_RELEASE'
    if not controller_live:return 'HOLD_N2_CONTROLLER_STOPPED'
    return 'WAITING_N2'
def initial_state(p):return dict(status='REGISTERED_WAITING_N2',observed_at=now(),jobs={j['id']:dict(status='PENDING',gpu=j['gpu'],stage=j['stage'],model=j['model']) for j in p['jobs']},E0='PENDING',mask_preparation='PENDING',optimizer_updates=0)
def verify_snapshot(base):
    for name,digest in read(base/'code_manifest.json')['files'].items():
        if sha(base/'code'/name)!=digest:raise RuntimeError('code snapshot changed '+name)
