"""Nine frozen matched training cells; no GPU initialization."""
import copy,math
from pathlib import Path
from post_n2_diag_common import read,write,sha,now,within,verify_snapshot,BASE_SHA,N1_NAME,bind_model
from post_n5_cross_common import released as old_released
CROSS_NAME='research_post_n5_cross_20261006T235526_442218'
PREFIX='research_post_n3_s1_'
IDS=[f'N3-{i}' for i in range(5)]+[f'S1-{i}' for i in range(4)]
def hours(v):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:raise ValueError('positive finite timeout')
    return float(v)
def directories(root,base):
    root=within(root,'/home/jovyan/zzx');base=within(base,root/'records')
    if not base.name.startswith(PREFIX):raise ValueError('unexpected training directory')
    return root,base
DESIGN=dict(region=dict(stride=16,seeds=64,grid=[8,8],cell_tokens=4,iterations=1,assignment='nearest seed in 3x3 grid neighborhood; fixed seed centroid descriptors',
    costs=dict(spatial_squared_divisor=16,rgb_cosine_factor=2.,dsm_abs_factor=4.),descriptor='detached normalized compress32 late projected RGB; nearest normalized received DSM',
    support='both observed, all16x16 donor pixels valid',messages='own feature aggregation conditioned by other-side region; same two learned 128x128 projections',residual_scale=.1,
    modes=['pixel','grid','rgb_region','dsm_region','bilateral'],rgb_region='DSM own features grouped by RGB descriptor, RGB own features pixel control',
    dsm_region='RGB own features grouped by DSM height, DSM own features pixel control'),
    support=dict(factors=['preserve_feature','retain_fusion'],cells=[[False,False],[True,False],[False,True],[True,True]],
        physical_input='always correctly masked zero; original paired clean/aug crop stream',full_missing_guard='all factors use original full-window safe graph'),
    gates=dict(N3_S_gain_pp=.3,N3_direction_gain_pp=.2,S1_mean_gain_pp=.5,S1_single_gain_pp=.2,clean_missing_floor_pp=-.1,worst_tile_floor_pp=-.2))
def make_plan(root,base,commit,parent):
    p=copy.deepcopy(parent);p.update(id='POST_N3_S1',created_at=now(),execution_commit=commit,protocol='docs/protocols/POST_N3_S1_EXECUTION_20261007.md',
        source_cross_directory=str(root/'records'/CROSS_NAME),directory_pattern='records/research_post_n3_s1_<timestamp>_<pid>',
        initial_checkpoint=dict(path=str(root/'records'/N1_NAME/'jobs/N1-2/selected.pth'),sha256=BASE_SHA),
        design=DESIGN,automatic_followup=False,automatic_training_after_stage=False,unique_training_jobs=9,total_optimizer_steps=72000,
        architecture='fixed N1-2 last4/heads; N3 own feature region messages or S1 support/output factorial; no teacher/restoration')
    p['jobs']=[dict(id=j,gpu=i%2,steps=8000,seed=42,information_entry='late',adaptation='last4_and_heads',geometry_aug=False,
        initial_checkpoint_path=p['initial_checkpoint']['path'],initial_checkpoint_sha256=BASE_SHA) for i,j in enumerate(IDS)]
    p['runtime']=dict(per_job_timeout_hours=12.,cpu_stage_timeout_hours=6.,wait_poll_seconds=5)
    p['training']['steps']=8000
    p['fixed_conditions']=list(dict.fromkeys(parent['evaluation']['primary']+parent['design']['geometry_conditions']+parent['design']['missing_conditions']))
    return p
def validate_plan(p):
    if p['id']!='POST_N3_S1' or [j['id'] for j in p['jobs']]!=IDS or [j['gpu'] for j in p['jobs']]!=[i%2 for i in range(9)]:raise ValueError('nine arms/GPU contract changed')
    t=p['training']
    if t['steps']!=8000 or t['seed']!=42 or t['physical_batch']!=16 or t['gradient_accumulation'] or t['validation_steps']!=[4000,8000] or t['selection_states']!=['clean','dsm_missing','rgb_missing']:raise ValueError('training/selection changed')
    if p['data']['validation']!=['3_11','5_10'] or len(p['data']['fit12'])!=12 or set(p['data']['fit12'])&set(p['data']['validation']) or p['data']['test6_loaded'] or p['data']['independent_final_loaded'] or p['physical_gpus']!=[0,1]:raise ValueError('scope changed')
    if p['design']!=DESIGN or p['initial_checkpoint']['sha256']!=BASE_SHA or p['total_optimizer_steps']!=72000 or p['automatic_training_after_stage']:raise ValueError('design/base/budget changed')
    for i,j in enumerate(p['jobs']):
        if j!=dict(id=IDS[i],gpu=i%2,steps=8000,seed=42,information_entry='late',adaptation='last4_and_heads',geometry_aug=False,initial_checkpoint_path=p['initial_checkpoint']['path'],initial_checkpoint_sha256=BASE_SHA):raise ValueError('arm changed')
    for k in ('per_job_timeout_hours','cpu_stage_timeout_hours'):hours(p['runtime'][k])
    return p['jobs']
def initial_state(p):return dict(status='REGISTERED',observed_at=now(),CPU='PENDING',jobs={j['id']:dict(status='PENDING',gpu=j['gpu']) for j in p['jobs']})
def complete_job(base,j,p):
    f=base/'jobs'/j;c=read(f/'complete.json')
    if c['global_step']!=8000 or c['signature']['job']['id']!=j or c['signature']['execution_commit']!=p['execution_commit'] or c['signature']['plan_sha256']!=sha(base/'plan.json') or c['signature']['initial_checkpoint_sha256']!=BASE_SHA or c['signature']['mask_manifest_sha256']!=sha(base/'mask_manifest.json') or c['test6_loaded'] or c['independent_final_loaded']:raise RuntimeError('completed scientific binding differs '+j)
    for tag in ('evaluation','fixed8000','support_evaluation','support_fixed8000'):
        if c[tag+'_summary_sha256']!=sha(f/tag/'summary.json'):raise RuntimeError('summary changed '+j)
    if sha(f/'selected.pth')!=c['selected_checkpoint_sha256']:raise RuntimeError('selected state changed')
    return c
def released(root):
    from d30_common import live_owned,lock_free
    old=old_released(root);base=root/'records'/CROSS_NAME;s=read(base/'queue_status.json')
    if s['status']!='CROSS_DIAGNOSTICS_COMPLETE_AWAITING_REVIEW' or set(s['jobs'])!={'E4_N1-2','E4_N2-0','E4_N2-3'} or any(r['status']!='COMPLETE' for r in s['jobs'].values()):raise RuntimeError('cross not complete')
    if live_owned(s.get('controller_pid',-1),base) or any(live_owned(x.get('pid',-1),base) for x in s['jobs'].values()) or not lock_free(base):raise RuntimeError('cross still owned/live')
    screen=read(base/'cross_screen.json');prep=read(base/'cpu_preparation_complete.json')
    if screen['recommended_next_families']!=['N3','S1'] or screen['E4']['output']['trigger'] or not screen['E4']['feature']['trigger'] or not screen['N3_problem_trigger']:raise RuntimeError('audited fixed stage gate changed')
    if screen['plan_sha256']!=sha(base/'plan.json') or screen['preparation_sha256']!=sha(base/'cpu_preparation_complete.json'):raise RuntimeError('cross screen binding changed')
    for key,name in [('plan_sha256','plan.json'),('masks_sha256','mask_manifest.json'),('E3_sha256','e3_screen.json'),('boundary_sha256','boundary_screen.json')]:
        if prep[key]!=sha(base/name):raise RuntimeError('cross preparation changed')
    for j in ('E4_N1-2','E4_N2-0','E4_N2-3'):
        f=base/'jobs'/j;c=read(f/'complete.json')
        if c['summary_sha256']!=sha(f/'summary.json') or screen['complete_bindings'][j]!=sha(f/'complete.json'):raise RuntimeError('cross completion changed')
    binding,_,_=bind_model(root,'N1-2')
    return dict(old=old,cross_screen_sha256=sha(base/'cross_screen.json'),cross_queue_sha256=sha(base/'queue_status.json'),N1_base_binding=binding,checked_at=now())
