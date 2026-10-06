"""Explicit evaluation overlay on immutable 01ec8de execution snapshots."""
import copy,hashlib,json,os
from pathlib import Path
import torch
ORIGINAL='01ec8dee82f7e272f6a650aaf9f3e619a0e7c516'
DIAGNOSTICS=('dsm_present_zero','dsm_present_shift_half')

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()
def compatible(original):
    def treatment(op,ds,kind,seed):
        if kind in DIAGNOSTICS:
            mask=torch.ones_like(ds,dtype=torch.bool)
            bad=torch.zeros_like(ds) if kind==DIAGNOSTICS[0] else torch.roll(ds,(ds.shape[-2]//2,ds.shape[-1]//2),(-2,-1))
            return op.clone(),bad,mask,mask.clone()
        return original(op,ds,kind,seed)
    return treatment

def evaluation_conditions(plan):
    cfg=plan['evaluation']
    return cfg['primary']+cfg['missing']+sum(cfg['local'].values(),[])+cfg['diagnostic']

def check_conditions(plan,original):
    # Exercise EVERY actual runtime condition before any worker; no data/GPU probe.
    op=torch.arange(3*32*32,dtype=torch.float32).reshape(1,3,32,32)/(3*32*32)
    ds=torch.arange(32*32,dtype=torch.float32).reshape(1,32,32)/(32*32)
    patched=compatible(original);names=evaluation_conditions(plan)
    if len(names)!=len(set(names)):raise RuntimeError('duplicate evaluation condition')
    for kind in names:
        a,b,rm,dm=patched(op,ds,kind,42)
        if a.shape!=op.shape or b.shape!=ds.shape or rm.shape!=ds.shape or dm.shape!=ds.shape or rm.dtype!=torch.bool or dm.dtype!=torch.bool:raise RuntimeError('bad condition interface '+kind)
        if not torch.isfinite(a).all() or not torch.isfinite(b).all():raise RuntimeError('nonfinite treatment '+kind)
    return names

def repairable_row(job,row,base):
    if row.get('status') not in ('TECHNICAL_FAILURE','TIMEOUT'):return False
    if job not in ('A0','A1','A2','A3','A4','A5'):raise RuntimeError('unknown failed job '+job)
    path=Path(row['log_path']).resolve();path.relative_to(base.resolve())
    from collections import deque
    with path.open(errors='replace') as f:tail='\n'.join(deque(f,maxlen=60))
    if 'ValueError: dsm_present_zero' not in tail:raise RuntimeError('failure differs from diagnosed evaluation compatibility '+job)
    if row.get('progress',{}).get('step')!=8000:raise RuntimeError('refuse training restart for failed A '+job)
    if not (base/'jobs'/job/'last_train_state.pth').is_file():raise RuntimeError('trained checkpoint missing '+job)
    return True

def reuse_equal_age(base,folder,state,write):
    """Only add missing selected records when selected == exact fixed8000 checkpoint."""
    best=state['best'];plan=read(base/'plan.json')
    if best['step']!=8000:return []
    final=folder/'checkpoints/step_8000.pth'
    if sha(final)!=best['checkpoint_sha256'] or sha(folder/'selected.pth')!=best['checkpoint_sha256']:raise RuntimeError('equal-age checkpoint binding differs')
    binding=dict(training=state['signature'],selected=best);reused=[]
    names=list(dict.fromkeys(plan['design']['geometry_conditions']+plan['design']['missing_conditions']))
    names=[n for n in names if n not in plan['evaluation']['primary']]
    for kind in names:
        for tile in plan['data']['validation']:
            target=folder/'evaluation'/kind/(tile+'.json')
            if target.exists():
                if read(target)['binding']!=binding:raise RuntimeError('preserve conflicting selected evaluation')
                continue
            source=folder/'fixed8000'/kind/(tile+'.json')
            if not source.exists():continue
            row=copy.deepcopy(read(source))
            if row['binding']['checkpoint_sha256']!=best['checkpoint_sha256'] or row['binding']['training']!=state['signature']:raise RuntimeError('fixed record not identical checkpoint')
            for name,digest in row['predictions'].items():
                old=source.parent/name/(tile+'.npy');new=target.parent/name/(tile+'.npy')
                if sha(old)!=digest:raise RuntimeError('source prediction changed')
                new.parent.mkdir(parents=True,exist_ok=True)
                if new.exists():
                    if sha(new)!=digest:raise RuntimeError('conflicting prediction')
                else:os.link(old,new)
            row['binding']=binding;row['reused_from']=dict(path=str(source),sha256=sha(source),reason='identical selected=fixed8000 checkpoint; no new inference')
            write(target,row);reused.append(str(target))
    return reused

def transform_controller(source,worker):
    needle="elif row.get('status') in ('TECHNICAL_FAILURE','TIMEOUT'):raise RuntimeError('technical failure needs explicit diagnosis '+j)"
    if source.count(needle)!=1:raise RuntimeError('controller repair site changed')
    source=source.replace(needle,"elif row.get('status') in ('TECHNICAL_FAILURE','TIMEOUT'):\n            if repairable_row(j,row,base):row['status']='PENDING'")
    needle="str(code/'scripts/run_post_d30.py')"
    if source.count(needle)!=1:raise RuntimeError('worker dispatch site changed')
    return source.replace(needle,repr(str(worker)))
