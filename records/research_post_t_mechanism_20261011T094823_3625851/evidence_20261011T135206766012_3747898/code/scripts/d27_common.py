"""D27 fixed contract; no new resource or data audit."""
from d24_common import read,write,sha,within,now
ARMS=('S0','S1','G0','G1','L0','L1','C0','C1','L1-sh','C1-sh')
def directories(root,base):
    root=within(root,'/home/jovyan/zzx');base=within(base,root/'records')
    if not base.name.startswith('research_d27_safe_routing_'):raise ValueError('unexpected D27 directory')
    return root,base
def validate_plan(plan):
    jobs=plan['jobs'];cfg=plan['training'];data=plan['data']
    if tuple(j['id'] for j in jobs)!=ARMS or any(j['steps']!=8000 or j['seed']!=42 or j['optimizer_steps']!=8000 for j in jobs):raise ValueError('ten fixed arms/80000 updates required')
    if cfg['physical_batch']!=16 or cfg['gradient_accumulation'] or cfg['steps']!=8000 or plan['physical_gpus']!=[0,1]:raise ValueError('budget/devices changed')
    if data['test6_loaded'] or data['independent_final_loaded'] or data['validation']!=['3_11','5_10'] or len(data['fit12'])!=12 or set(data['fit12'])&set(data['validation']+data['train_held4']):raise ValueError('partition/test changed')
    if cfg['validation_steps']!=[4000,8000] or cfg['selection_states']!=['clean','dsm_missing','rgb_missing']:raise ValueError('selection changed')
    if plan['architecture']['residual_experts']!=3 or plan['safety_weights']!={'protect':.1,'recover':.1,'expert_auxiliary':.1}:raise ValueError('mechanism changed')
    if plan['total_optimizer_steps']!=80000 or not plan['nohup'] or plan['new_unimodal_training']!=0:raise ValueError('authorized scope changed')
    return jobs

def parent_terminal(state):
    return state.get('status') in ('COMPLETE','COMPLETE_WITH_TECHNICAL_FAILURES') and len(state.get('jobs',{}))==9 and all(r.get('status') in ('COMPLETE','TECHNICAL_FAILURE','TIMEOUT') for r in state['jobs'].values())
