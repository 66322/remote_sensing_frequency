"""Ten preregistered decoder-transfer cells and strict predecessor handover."""
import copy
from pathlib import Path
import post_s1_support_common as old
from post_s1_support_common import read,write,sha,now,within,verify_snapshot,SHAS,SOURCE_NAME,SOURCE_COMMIT,source_binding,E_KEYS,hours
PREFIX='research_post_s1_transfer_'
PREDECESSOR='research_post_s1_support_20261008T234921_1890161'
PREDECESSOR_COMMIT='2c5e7d6f383cfe454415d4e106179930264f1141'
ORDER=['T'+str(i) for i in range(10)]
GATES=dict(base_pp=2.,matched_pp=.3,route_floor_pp=-.2,protect_floor_pp=-.1,worst_tile_floor_pp=-.2,shape_pp=.5)

def job_card(j):
    if j not in ORDER:raise ValueError('unregistered decoder arm')
    i=int(j[1:]);return dict(id=j,gpu=0,steps=8000,seed=42,donor='S1-'+str(i//2) if i<8 else 'random',
        frozen_base=True,support_preserved=bool(i%2),local_only=True,control='none',geometry_aug=False)
def dirs(root,base):
    root=within(root,'/home/jovyan/zzx');base=within(base,root/'records')
    if not base.name.startswith(PREFIX):raise ValueError('unexpected directory')
    return root,base
def make_plan(root,base,commit,parent):
    p=old.make_plan(root,base,commit,parent)
    pred=root/'records'/PREDECESSOR
    p.update(id='POST_S1_TRANSFER',jobs=[job_card(j) for j in ORDER],primary_candidate='T7',
        predecessor_directory=str(pred),predecessor_execution_commit=PREDECESSOR_COMMIT,
        predecessor_plan_sha256=sha(pred/'plan.json') if (pred/'plan.json').exists() else 'fixture',
        predecessor_code_manifest_sha256=sha(pred/'code_manifest.json') if (pred/'code_manifest.json').exists() else 'fixture',
        donors={name:dict(path=str(root/'records'/SOURCE_NAME/'jobs'/name/'selected.pth'),sha256=digest) for name,digest in SHAS.items()},
        design=dict(factors=['decoder_initialization','feature_support'],decoder='private project/merge/fusion; direct local logits',
            frozen_base='S1-0 including experts and original fusion',gates=GATES,E_keys=E_KEYS,
            step0='rgb_U,dsm_U diagnostic only; no selection',stress_scope='repeated development stress, not independent test',
            teacher=False,shared_encoder_passes=1,output_support='known partial RGB missing AND observed DSM; native overwrite',
            no_followup=True))
    p['runtime']['wait_poll_seconds']=30
    return p
def validate(p):
    projected=old.make_plan(Path('/home/jovyan/zzx/x'),Path('/home/jovyan/zzx/x/records/y'),'x',p)
    # Check the actual inherited data/training/source controls, not a newly constructed substitute.
    for k in ('training','data','initial_checkpoint','reference_shas','source_directory','source_execution_commit','physical_gpus','max_gpu_workers','automatic_retry','new_seeds','test_release','runtime'):
        projected[k]=copy.deepcopy(p[k])
    old.validate(projected)
    if p['id']!='POST_S1_TRANSFER' or p['jobs']!=[job_card(j) for j in ORDER] or p['total_optimizer_steps']!=80000 or p['primary_candidate']!='T7':raise ValueError('fixed arm/budget changed')
    expect=make_plan(Path('/home/jovyan/zzx/x'),Path('/home/jovyan/zzx/x/records/y'),'x',p)
    if p['design']!=expect['design']:raise ValueError('transfer scientific design changed')
    if Path(p['predecessor_directory']).name!=PREDECESSOR or p['predecessor_execution_commit']!=PREDECESSOR_COMMIT:raise ValueError('predecessor changed')
    if set(p['donors'])!=set(SHAS) or any(p['donors'][n]['sha256']!=v for n,v in SHAS.items()):raise ValueError('donor SHA changed')
    return p
def predecessor_verdict(state,controller_live,workers_live,released):
    expected={'D1','E',*old.ORDER}
    status=state.get('status','')
    if status=='SUPPORT_COMPLETE_AWAITING_REVIEW':
        if set(state.get('jobs',{}))!=expected or state.get('CPU')!='COMPLETE' or any(x.get('status')!='COMPLETE' for x in state['jobs'].values()):return 'HOLD_INVALID_COMPLETE'
        return 'READY' if not controller_live and not workers_live and released else 'WAITING_PREDECESSOR_RELEASE'
    if status.startswith(('HOLD','CONTROLLER_INTERRUPTED')) or any(x.get('status') in ('TECHNICAL_FAILURE','TIMEOUT') for x in state.get('jobs',{}).values()):return 'HOLD_PREDECESSOR_FAILURE'
    return 'WAITING_PREDECESSOR' if controller_live else 'HOLD_PREDECESSOR_STOPPED'
def inspect_predecessor(root,p,accept=False):
    from d30_common import live_owned,lock_free
    pred=within(p['predecessor_directory'],root/'records');s=read(pred/'queue_status.json');q=read(pred/'plan.json')
    if q['execution_commit']!=PREDECESSOR_COMMIT or sha(pred/'plan.json')!=p['predecessor_plan_sha256'] or sha(pred/'code_manifest.json')!=p['predecessor_code_manifest_sha256']:raise RuntimeError('predecessor binding changed')
    active=live_owned(s.get('controller_pid',-1),pred)
    workers=any(live_owned(r.get('pid',-1),pred) for r in s.get('jobs',{}).values())
    released=lock_free(pred) if (pred/'controller.lock').exists() else False
    verdict=predecessor_verdict(s,active,workers,released)
    result=dict(verdict=verdict,last_observed=s.get('observed_at'),status=s['status'],controller_live=active,workers_live=workers,checked_at=now())
    if accept:
        if verdict!='READY':raise RuntimeError('predecessor not safely released '+verdict)
        old.validate(q);verify_snapshot(pred)
        for j in ['D1']+old.ORDER+['E']:old.accept_worker(pred,j,q)
        if sha(pred/'support_screen.json')!=s['screen_sha256']:raise RuntimeError('predecessor stage summary changed')
        result.update(queue_sha256=sha(pred/'queue_status.json'),screen_sha256=s['screen_sha256'],
            scientific_gate_required=False,source_bindings={n:source_binding(root,n)[0] for n in SHAS})
    return result
def initial_state(p):
    return dict(status='REGISTERED',observed_at=now(),CPU='PENDING',jobs={j:dict(status='PENDING',gpu=0) for j in ORDER})
def signature(base,p,job):
    return dict(execution_commit=p['execution_commit'],plan_sha256=sha(base/'plan.json'),code_manifest_sha256=sha(base/'code_manifest.json'),
        mask_manifest_sha256=sha(base/'mask_manifest.json'),initial_checkpoint_sha256=SHAS['S1-0'],
        donor_checkpoint_sha256=None if job['donor']=='random' else SHAS[job['donor']],job=job,physical_gpu=0,
        primary_checkpoint_step=8000,test6_loaded=False,independent_final_loaded=False)
def accept_worker(base,task,p):
    f=base/'jobs'/task;c=read(f/'complete.json');job=next(j for j in p['jobs'] if j['id']==task)
    if c['execution_commit']!=p['execution_commit'] or c['plan_sha256']!=sha(base/'plan.json') or c['code_manifest_sha256']!=sha(base/'code_manifest.json') or c['signature']!=signature(base,p,job):raise RuntimeError('worker binding changed')
    if c['global_step']!=8000 or c['optimizer_updates']!=8000 or c['selected']['step']!=8000 or c['test6_loaded'] or c['independent_final_loaded']:raise RuntimeError('age/scope changed')
    required={'selected.pth','last_train_state.pth','checkpoints/step_8000.pth','evaluation/summary.json','fixed8000/summary.json','support_evaluation/summary.json','stress_evaluation/summary.json','initial_evaluation/summary.json','model_capacity.json','input_binding.json','protection.json'}
    if not required.issubset(c['artifacts']):raise RuntimeError('missing acceptance artifacts')
    for n,h in c['artifacts'].items():
        if sha(within(f/n,f))!=h:raise RuntimeError('worker artifact changed '+task+'/'+n)
    return c
