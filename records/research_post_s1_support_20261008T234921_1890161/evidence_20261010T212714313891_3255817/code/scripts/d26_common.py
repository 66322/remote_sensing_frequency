"""Frozen D26 contract and standard-library record helpers."""
from pathlib import Path
from d24_common import read,write,sha,within,now

PREFIX='records/research_d26_plan_20261002/'
ARMS=('J0','B0','CAP','X','XS','XF','XSF','XSF-shS','XSF-shF')
def directories(root,base):
    root=within(root,'/home/jovyan/zzx');base=within(base,root/'records')
    if not base.name.startswith('research_d26_bidirectional_'):raise ValueError('unexpected D26 directory')
    return root,base
def validate_plan(plan):
    jobs=plan['jobs'];cfg=plan['training'];data=plan['data']
    if tuple(j['id'] for j in jobs)!=ARMS or any(j['steps']!=8000 or j['seed']!=42 or j['optimizer_steps']!=8000 for j in jobs):raise ValueError('nine fixed arms/72000 updates required')
    if cfg['physical_batch']!=16 or cfg['gradient_accumulation'] or cfg['steps']!=8000 or plan['physical_gpus']!=[0,1]:raise ValueError('batch/budget/devices changed')
    if data['test6_loaded'] or data['independent_final_loaded'] or data['validation']!=['3_11','5_10'] or len(data['fit12'])!=12 or set(data['fit12'])&set(data['validation']+data['train_held4']):raise ValueError('partition/test gate changed')
    if cfg['validation_steps']!=[4000,8000] or cfg['selection_states']!=['clean','dsm_missing','rgb_missing']:raise ValueError('selection changed')
    return jobs
