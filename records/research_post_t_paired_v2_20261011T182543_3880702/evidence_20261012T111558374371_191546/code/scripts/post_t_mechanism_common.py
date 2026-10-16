"""Fixed inference-only attribution and learning-curve successor, physical GPU0."""
import copy,itertools
from pathlib import Path
import post_s1_transfer_common as previous
from post_s1_support_common import read,write,sha,now,within,verify_snapshot,hours,SHAS,SOURCE_NAME,E_KEYS
PREFIX='research_post_t_mechanism_'
PREDECESSOR='research_post_s1_transfer_20261010T073327_2852696'
PREDECESSOR_COMMIT='4bf69489f789e998b7bf3181d3b3057c6ff7c04e'
KEYS=['rgb_U','dsm_U']+E_KEYS
def cards():
    out=[]
    for rgb,dsm,head,context in itertools.product((0,3),(0,3),(0,3),(False,True)):
        out.append(dict(id=f'M{rgb}{dsm}{head}_'+('context' if context else 'masked'),gpu=0,kind='module',rgb=rgb,dsm=dsm,head=head,context=context,keys=KEYS,optimizer_updates=0))
    return out+[dict(id='L_'+j,gpu=0,kind='trajectory',source_job=j,step=4000,keys=['rgb_U','dsm_U'],optimizer_updates=0) for j in previous.ORDER]
ORDER=[j['id'] for j in cards()]
def dirs(root,base):
    root=within(root,'/home/jovyan/zzx');base=within(base,root/'records')
    if not base.name.startswith(PREFIX):raise ValueError('unexpected directory')
    return root,base
def make_plan(root,base,commit,parent):
    previous.validate(parent)
    p=copy.deepcopy(parent);pred=root/'records'/PREDECESSOR
    p.update(id='POST_T_MECHANISM',execution_commit=commit,created_at=now(),jobs=cards(),total_optimizer_steps=0,
      primary_candidate=None,parent_transfer_plan=copy.deepcopy(parent),predecessor_directory=str(pred),
      predecessor_execution_commit=PREDECESSOR_COMMIT,predecessor_plan_sha256=sha(pred/'plan.json') if (pred/'plan.json').exists() else 'fixture',
      predecessor_code_manifest_sha256=sha(pred/'code_manifest.json') if (pred/'code_manifest.json').exists() else 'fixture',
      design=dict(question='R0 functional module compatibility and observed training trajectory',new_training=False,
        module_factors=['RGB expert weights','DSM expert weights','decoder weights','feature support'],
        interpretation='unaligned module swaps test compatibility; cannot prove information absent',
        budget_signal_pp=.3,feature_signal_pp=.3,diagnostic_not_method_gate=True,no_automatic_training=True,
        E_keys=E_KEYS),runtime=dict(per_job_timeout_hours=12.,cpu_stage_timeout_hours=12.,wait_poll_seconds=30))
    return p
def validate(p):
    parent=previous.validate(p['parent_transfer_plan'])
    if parent['execution_commit']!=PREDECESSOR_COMMIT:raise ValueError('wrong parent')
    for k in ('data','experts','input_manifest_sha256','expected_configs','training','augmentation','evaluation','initial_checkpoint','reference_shas','source_directory','source_execution_commit','donors','physical_gpus','max_gpu_workers','automatic_retry','new_seeds','test_release'):
        if p[k]!=parent[k]:raise ValueError('inherited contract changed '+k)
    if p['id']!='POST_T_MECHANISM' or p['jobs']!=cards() or p['total_optimizer_steps']!=0 or p['primary_candidate'] is not None:raise ValueError('fixed diagnostic plan changed')
    if p['physical_gpus']!=[0] or p['max_gpu_workers']!=1:raise ValueError('GPU0 only')
    expected=make_plan(Path('/home/jovyan/zzx/x'),Path('/home/jovyan/zzx/x/records/y'),'fixture',parent)
    if p['design']!=expected['design'] or p['runtime']!=expected['runtime']:raise ValueError('design/runtime changed')
    if Path(p['predecessor_directory']).name!=PREDECESSOR or p['predecessor_execution_commit']!=PREDECESSOR_COMMIT:raise ValueError('parent changed')
    return p
def predecessor_verdict(state,controller_live,workers_live,released):
    status=state.get('status','')
    if status=='TRANSFER_COMPLETE_AWAITING_REVIEW':
        if state.get('CPU')!='COMPLETE' or set(state.get('jobs',{}))!=set(previous.ORDER) or any(x.get('status')!='COMPLETE' for x in state['jobs'].values()):return 'HOLD_INVALID_COMPLETE'
        return 'READY' if not controller_live and not workers_live and released else 'WAITING_PREDECESSOR_RELEASE'
    if status.startswith(('HOLD','CONTROLLER_INTERRUPTED')) or any(x.get('status') in ('TECHNICAL_FAILURE','TIMEOUT') for x in state.get('jobs',{}).values()):return 'HOLD_PREDECESSOR_FAILURE'
    return 'WAITING_PREDECESSOR' if controller_live else 'HOLD_PREDECESSOR_STOPPED'
def inspect_predecessor(root,p,accept=False):
    from d30_common import live_owned,lock_free
    pred=within(p['predecessor_directory'],root/'records');s=read(pred/'queue_status.json');q=read(pred/'plan.json')
    if q!=p['parent_transfer_plan'] or sha(pred/'plan.json')!=p['predecessor_plan_sha256'] or sha(pred/'code_manifest.json')!=p['predecessor_code_manifest_sha256']:raise RuntimeError('predecessor binding changed')
    active=live_owned(s.get('controller_pid',-1),pred);workers=any(live_owned(r.get('pid',-1),pred) for r in s.get('jobs',{}).values())
    released=lock_free(pred) if (pred/'controller.lock').exists() else False
    verdict=predecessor_verdict(s,active,workers,released)
    result=dict(verdict=verdict,last_observed=s.get('observed_at'),status=s['status'],controller_live=active,workers_live=workers,checked_at=now())
    if accept:
        if verdict!='READY':raise RuntimeError('predecessor not safely released '+verdict)
        previous.validate(q);verify_snapshot(pred)
        for j in previous.ORDER:
            previous.accept_worker(pred,j,q)
            v=read(pred/'jobs'/j/'validation/step_4000.json');point=pred/'jobs'/j/'checkpoints/step_4000.pth'
            if v['binding']['training']!=previous.signature(pred,q,next(x for x in q['jobs'] if x['id']==j)) or v['binding']['step']!=4000 or sha(point)!=v['binding']['checkpoint_sha256']:raise RuntimeError('midpoint checkpoint changed '+j)
        if sha(pred/'transfer_screen.json')!=s['screen_sha256']:raise RuntimeError('parent screen changed')
        result.update(queue_sha256=sha(pred/'queue_status.json'),screen_sha256=s['screen_sha256'],scientific_gate_required=False)
    return result
def initial_state(p):return dict(status='REGISTERED',observed_at=now(),CPU='PENDING',jobs={j:dict(status='PENDING',gpu=0) for j in ORDER})
def accept_worker(base,task,p):
    out=base/'jobs'/task;c=read(out/'complete.json')
    if c['execution_commit']!=p['execution_commit'] or c['plan_sha256']!=sha(base/'plan.json') or c['code_manifest_sha256']!=sha(base/'code_manifest.json') or c['optimizer_updates']!=0 or c['test6_loaded'] or c['independent_final_loaded']:raise RuntimeError('worker binding differs')
    if c['job']!=next(j for j in p['jobs'] if j['id']==task):raise RuntimeError('job changed')
    if not {'summary.json','checkpoint_binding.json'}.issubset(c['artifacts']):raise RuntimeError('missing artifacts')
    for n,h in c['artifacts'].items():
        if sha(within(out/n,out))!=h:raise RuntimeError('worker artifact changed '+task+'/'+n)
    return c
