"""D25 locked protocol and output boundaries, not resource probing."""
from pathlib import Path
from d24_common import read, write, sha, within, now

PREFIX='records/research_d25_plan_20261002/'
def directories(root,base):
    root=within(root,'/home/jovyan/zzx')
    base=within(base,root/'records')
    if not base.name.startswith('research_d25_missingness_'):
        raise ValueError('unexpected D25 directory')
    return root,base

def validate_plan(plan):
    jobs=plan['jobs']
    if len(jobs)!=8 or {j['id'] for j in jobs}!={'P'+str(i) for i in range(8)}:
        raise ValueError('eight frozen jobs required')
    if sum(j['optimizer_steps'] for j in jobs)!=32000 or plan['physical_gpus']!=[0,1]:
        raise ValueError('budget/device mismatch')
    cfg=plan['training'];data=plan['data']
    if cfg['physical_batch']!=16 or cfg['gradient_accumulation'] or cfg['steps']!=4000:
        raise ValueError('batch/steps changed')
    if data['test6_loaded'] or data['independent_final_loaded']:
        raise ValueError('test/final forbidden')
    if data['validation']!=['3_11','5_10'] or len(data['fit12'])!=12 or set(data['fit12']) & set(data['validation']+data['train_held4']):
        raise ValueError('partition mismatch')
    expected={'P0':('shared','none','QD'),'P1':('shared','none','QD'),
              'P2':('separate','none','QD'),'P3':('separate','project','QD'),
              'P4':('shared','project','QD'),'P5':('average','none','QD'),
              'P6':('shared','none','Q'),'P7':('separate','norm_sham','QD')}
    for j in jobs:
        if j['seed']!=42 or j['optimizer_steps']!=4000 or not j['last4'] or j['gpu'] not in (0,1):
            raise ValueError('job contract changed')
        if (j['decoder_mode'],j['gradient_mode'],j['augmentation'])!=expected[j['id']]:
            raise ValueError('treatment changed')
        if j['pair']!=(j['id']=='P1') or j['optical_only']!=(j['id']=='P6'):
            raise ValueError('objective/input changed')
    return jobs
