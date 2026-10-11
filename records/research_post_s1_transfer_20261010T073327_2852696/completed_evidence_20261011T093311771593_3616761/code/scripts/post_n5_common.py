"""Frozen N5 contract; no tensor/GPU imports."""
import copy,math
from pathlib import Path
from post_n2_diag_common import read,write,sha,now,within,BASE_SHA,N1_NAME,N2_NAME,bind_model,verify_snapshot
PREFIX='research_post_n5_'
DIAG_NAME='research_post_n2_diagnostics_20261005T131434_3591073'
IDS=['N5-'+str(i) for i in range(4)]
MASK_CONTRACT=dict(rules=['U','H','L','T'],cell=128,fraction=.25,window=5,T='maximum luminance local standard deviation; same geometry as H/L',train_rules=['U','H','L'])
CROP_CONTRACT=dict(replaced_sample_indices=list(range(8,16)),native_patch=512,origin_multiple=128,flip='original keyed flips; no interpolation for replaced slots',rules={'N5-1':['U']*4,'N5-2':['H','L','H','L'],'N5-3':['U','U','H','L']},direction='sample index even rgb, odd dsm',cycle='zero-based training step modulo four')
GATE=dict(T_mean_gain_pp=.5,clean_full_missing_floor_pp=-.1,old_random_mean_floor_pp=-.1,worst_primary_tile_floor_pp=-.2,both_tiles_positive=True,fixed_main_positive=True)
def directories(root,base):
    root=within(root,'/home/jovyan/zzx');base=within(base,root/'records')
    if not base.name.startswith(PREFIX):raise ValueError('unexpected N5 directory')
    return root,base
def hours(v):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:raise ValueError('positive finite timeout required')
    return float(v)
def make_plan(root,base,commit,parent):
    p=copy.deepcopy(parent)
    p.update(id='POST_N5',execution_commit=commit,protocol='docs/protocols/POST_N5_EXECUTION_20261006.md',unique_training_jobs=4,total_optimizer_steps=32000,
        initial_checkpoint=dict(path=str(root/'records'/N1_NAME/'jobs/N1-2/selected.pth'),sha256=BASE_SHA),
        predecessor_directory=str(root/'records'/DIAG_NAME),mask_contract=MASK_CONTRACT,crop_contract=CROP_CONTRACT,N5_gate=GATE,automatic_training_after_N5=False)
    p['jobs']=[dict(id=j,gpu=i%2,steps=8000,seed=42,information_entry='late',adaptation='last4_and_heads',geometry_aug=False) for i,j in enumerate(IDS)]
    p['runtime']=dict(per_job_timeout_hours=12.,cpu_stage_timeout_hours=6.,wait_poll_seconds=30)
    p['training']['steps']=8000
    p['N5_old_random_conditions']=list(dict.fromkeys(p['evaluation']['missing']+sum(p['evaluation']['local'].values(),[])))
    return p
def validate(p):
    if p['id']!='POST_N5' or [j['id'] for j in p['jobs']]!=IDS or [j['gpu'] for j in p['jobs']]!=[0,1,0,1]:raise ValueError('N5 job list changed')
    t=p['training']
    if t['steps']!=8000 or t['seed']!=42 or t['physical_batch']!=16 or t['gradient_accumulation'] or t['validation_steps']!=[4000,8000] or t['selection_states']!=['clean','dsm_missing','rgb_missing']:raise ValueError('training/selection changed')
    if p['physical_gpus']!=[0,1] or p['data']['validation']!=['3_11','5_10'] or len(p['data']['fit12'])!=12 or set(p['data']['fit12'])&set(p['data']['validation']) or p['data']['test6_loaded'] or p['data']['independent_final_loaded']:raise ValueError('scope changed')
    if p['initial_checkpoint']['sha256']!=BASE_SHA or p['mask_contract']!=MASK_CONTRACT or p['crop_contract']!=CROP_CONTRACT or p['N5_gate']!=GATE or p['total_optimizer_steps']!=32000 or p['automatic_training_after_N5']:raise ValueError('science contract changed')
    if Path(p['predecessor_directory']).name!=DIAG_NAME:raise ValueError('predecessor changed')
    for i,j in enumerate(p['jobs']):
        if j!=dict(id=IDS[i],gpu=i%2,steps=8000,seed=42,information_entry='late',adaptation='last4_and_heads',geometry_aug=False):raise ValueError('arm contract changed')
    hours(p['runtime']['per_job_timeout_hours']);hours(p['runtime']['cpu_stage_timeout_hours'])
    return p['jobs']
def initial_state(p):
    return dict(status='REGISTERED',observed_at=now(),jobs={j['id']:dict(status='PENDING',gpu=j['gpu']) for j in p['jobs']})
def released(root):
    from d30_common import live_owned,lock_free
    parents=[root/'records'/N1_NAME,root/'records'/N2_NAME,root/'records'/DIAG_NAME]
    expected=['N1_COMPLETE_AWAITING_STAGE_PROTOCOL','N2_COMPLETE_AWAITING_STAGE_PROTOCOL','DIAGNOSTICS_COMPLETE_AWAITING_REVIEW']
    rows=[]
    for base,status in zip(parents,expected):
        state=read(base/'queue_status.json')
        if state['status']!=status:raise RuntimeError('predecessor not accepted complete '+str(base))
        if live_owned(state.get('controller_pid',-1),base) or any(live_owned(r.get('pid',-1),base) for r in state['jobs'].values()) or not lock_free(base):raise RuntimeError('predecessor not released '+str(base))
        rows.append(dict(directory=str(base),queue_sha256=sha(base/'queue_status.json'),observed_at=state.get('observed_at'),status=status))
    diag=parents[-1];screen=read(diag/'diagnostic_screen.json')
    if screen['E1']['N5_problem_trigger'] is not True:raise RuntimeError('N5 problem gate is false')
    prep=read(diag/'cpu_preparation_complete.json')
    for key,name in [('plan_sha256','plan.json'),('masks_sha256','mask_manifest.json'),('E0_sha256','e0_screen.json'),('source_audit_sha256','n2_source_audit.json')]:
        if prep[key]!=sha(diag/name):raise RuntimeError('diagnostic provenance changed')
    for j in ('E1_A0','E1_B1','E2_N1-2','E2_N2-0','E2_N2-3'):
        c=read(diag/'jobs'/j/'complete.json')
        if c['optimizer_updates']!=0 or c['summary_sha256']!=sha(diag/'jobs'/j/'summary.json'):raise RuntimeError('diagnostic incomplete '+j)
    for i in range(6):bind_model(root,'N2-'+str(i),checkpoint=False)
    binding,_,_=bind_model(root,'N1-2')
    return dict(predecessors=rows,base_binding=binding,diagnostic_screen_sha256=sha(diag/'diagnostic_screen.json'))

