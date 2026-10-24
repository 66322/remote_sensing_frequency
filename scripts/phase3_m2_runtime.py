"""One persistent worker per authorized GPU. No CUDA initialization in parent."""
import gc
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import phase3_m2_common as c

def make_model(base,job,load=False):
    import torch
    from model.phase2_matched import MatchedExpert
    source=c.read(Path(base)/'pretrained.json')
    seed=job['seed'] if job['role']!='rgb_oof_teacher' else c.key(job['seed'],job['fold'],job['inner_pair'],'teacher-init')%(2**63-1)
    torch.manual_seed(seed)
    encoder=torch.hub.load(source['repository'],'dinov2_vits14',source='local',pretrained=False)
    if not load:
        import io
        raw=Path(source['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=source['sha256']:raise RuntimeError('public pretrained bytes changed')
        encoder.load_state_dict(torch.load(io.BytesIO(raw),map_location='cpu',weights_only=False),strict=True)
        del raw
    model=MatchedExpert(encoder)
    if job['modality']=='dsm': model.encoder.patch_embed.proj.requires_grad_(True)
    if load:
        folder=Path(base)/'jobs'/job['id']; done=c.read(folder/'complete.json')
        if done['binding']!=c.binding(base) or c.sha(folder/'endpoint.pth')!=done['checkpoint_sha256']: raise RuntimeError('endpoint changed')
        st=torch.load(folder/'endpoint.pth',map_location='cpu',weights_only=False)
        if st['job']!=job['id'] or st['step']!=32000: raise RuntimeError('checkpoint identity')
        model.load_state_dict(st['model'],strict=True)
    return model.cuda()

def infer(model,image,progress=None):
    import torch
    from torch.nn import functional as F
    h,w=image.shape[:2]
    positions=lambda n:sorted(set(list(range(0,n-511,256))+[n-512]))
    coords=[(y,x) for y in positions(h) for x in positions(w)]
    score=torch.zeros((6,h,w),device='cuda',dtype=torch.float32); coverage=np.zeros((h,w),np.uint8)
    model.eval()
    with torch.inference_mode():
        for start in range(0,len(coords),8):
            use=coords[start:start+8]; n=len(use)
            x=torch.from_numpy(np.stack([image[y:y+512,col:col+512].transpose(2,0,1) for y,col in use])).cuda()
            if n<8:x=torch.cat([x,x[-1:].expand(8-n,-1,-1,-1)])
            low=model.low(x).float()
            if low.shape[-2:]!=(128,128):raise RuntimeError('inference grid changed')
            z=F.interpolate(low,size=(512,512),mode='nearest')
            for i,(y,col) in enumerate(use):score[:,y:y+512,col:col+512].add_(z[i]);coverage[y:y+512,col:col+512]+=1
            if progress and (start%80==0 or start+n==len(coords)):progress(start+n,len(coords))
    if not coverage.all() or not bool(torch.isfinite(score).all()):raise RuntimeError('invalid stitch')
    return score.cpu().numpy()

def emit(base,gpu,events,acks,metadata,arrays):
    from phase24_ipc import Packet
    packet=Packet.create(arrays)
    try:
        events.put(dict(kind='PACKET',gpu=gpu,metadata=metadata,packet=packet.descriptor()))
        answer=acks.get()
        if answer.get('error'):raise RuntimeError(answer['error'])
    finally:packet.close()

def trajectory(base,gpu,job,model,step,events,acks):
    folds=c.read(Path(base)/'folds.json')
    for tile in folds['folds'][job['fold']]['evaluation']:
        item=c.DATA[tile]; image=item['rgb'] if job['modality']=='rgb' else np.repeat(item['dsm'][...,None],3,-1)
        score=infer(model,image)
        emit(base,gpu,events,acks,dict(kind='trajectory',job=job['id'],tile=tile,step=step),dict(score=score))
        del score,image

def train(base,gpu,job,events,acks,uuid):
    import torch
    from model.phase2_matched import optimizer
    from phase2_train import model_digest,gradients
    from phase3_m2_data import Crops
    from d24_data import PrefetchedBatches
    from phase3_m2_loss import objective
    base=Path(base); folder=base/'jobs'/job['id']; folder.mkdir(parents=True,exist_ok=False)
    folds=c.read(base/'folds.json'); pf=c.read(base/'resource_profile.json')
    model=make_model(base,job); initial=model_digest(model); opt=optimizer(model,32000)
    teachers={}
    if job['arm'] not in ['D0','DSelf']:
        alljobs={j['id']:j for j in c.jobs(folds)}
        for dep in job['depends_on']:teachers[alljobs[dep]['inner_pair']]=make_model(base,alljobs[dep],True).eval().requires_grad_(False)
    # Loading frozen teachers must not change the student's dropout RNG stream.
    torch.manual_seed(c.key(job['seed'],job['fold'],'student-optimization')%(2**63-1))
    frozen={n:p.detach().cpu().clone() for n,p in model.named_parameters() if not p.requires_grad}
    connected=set(); source_pairs={}
    for i,pair in enumerate(folds['folds'][job['fold']]['inner_pairs']):
        source_pairs[str(i)]=dict(student_tiles=pair,teacher=next((d for d in job['depends_on'] if d.endswith('T'+str(i))),None),
            teacher_train=[t for t in job['train'] if t not in pair])
    c.write(folder/'parameters.json',dict(binding=c.binding(base),job=job,initial_state_sha256=initial,teacher_binding=source_pairs,
        trainable=[(n,list(p.shape)) for n,p in model.named_parameters() if p.requires_grad],
        optimizer=[dict(names=g['names'],initial_lr=g['initial_lr']) for g in opt.param_groups],
        schedule='M1 progress mapping: warmup 200 updates; linear to zero at 32000',physical_gpu=gpu,gpu_uuid=uuid))
    started=time.monotonic();last_timing=started;last_step=0;stable_times=[]
    samples=PrefetchedBatches(Crops(job,folds),16,pf['crop_workers'],3,True)
    with (folder/'batch_hashes.jsonl').open('x') as hashes,(folder/'trajectory.jsonl').open('x') as log:
        for step,batch in enumerate(samples,1):
            model.train(); opt.zero_grad(set_to_none=True)
            factor=.1+.9*step/200 if step<=200 else (32000-step)/(32000-200)
            for g in opt.param_groups:g['lr']=g['initial_lr']*factor
            image=(batch['rgb'] if job['modality']=='rgb' else batch['dsm'][:,None].repeat(1,3,1,1)).cuda(non_blocking=True)
            target=batch['gt'].cuda(non_blocking=True); teacher=None
            if teachers:
                view=batch['teacher_rgb'].cuda(non_blocking=True)
                teacher=torch.empty((16,6,512,512),device='cuda',dtype=torch.float32)
                with torch.inference_mode():
                    for i,tm in teachers.items():
                        index=torch.nonzero(batch['inner']==i,as_tuple=True)[0]
                        if len(index):teacher[index.to('cuda')]=tm(view[index.to('cuda')]).float()
                if teacher.requires_grad:raise RuntimeError('teacher gradient leak')
            with torch.autocast('cuda',dtype=torch.bfloat16):z=model(image)
            loss,diagnostics=objective(z,target,job['arm'],teacher,batch['bins'].cuda(non_blocking=True),batch['shuffle_key'])
            loss.backward()
            norm=torch.nn.utils.clip_grad_norm_(model.parameters(),float('inf'),error_if_nonfinite=True)
            if step==1 or step%500==0:connected.update(gradients(model))
            before=model.encoder.patch_embed.proj.weight.detach().clone() if step==1 and job['modality']=='dsm' else None
            opt.step()
            if before is not None and torch.equal(before,model.encoder.patch_embed.proj.weight):raise RuntimeError('stem did not update')
            hashes.write(json.dumps(dict(step=step,hash=hashlib.sha256('|'.join(batch['token']).encode()).hexdigest()))+'\n')
            if step==1 or step%20==0:
                measured=time.monotonic()
                if step>=1000 and last_step not in [8000,16000,24000]:
                    stable_times.append((measured-last_timing)/(step-last_step));stable_times=stable_times[-50:]
                last_timing,last_step=measured,step
                row=dict(step=step,loss=float(loss),gradient_norm=float(norm),activation_abs_mean=float(z.detach().float().abs().mean()),
                    elapsed_seconds=time.monotonic()-started,stable_sec_per_update=float(np.median(stable_times)) if stable_times else None,
                    remaining_training_hours=(32000-step)*float(np.median(stable_times))/3600 if stable_times else None,
                    lr=[g['lr'] for g in opt.param_groups],**diagnostics)
                log.write(json.dumps(row)+'\n');log.flush();hashes.flush()
                c.write(folder/'progress.json',dict(row,physical_gpu=gpu,gpu_uuid=uuid,observed_at=c.now()))
                if step==1 or step%500==0:print('M2_TRAIN',job['id'],step,row,flush=True)
            if step%1000==0 and step<32000:
                tmp=folder/'last_resume.tmp';torch.save(dict(job=job['id'],binding=c.binding(base),step=step,model=model.state_dict(),
                    optimizer=opt.state_dict(),rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all()),tmp)
                os.replace(tmp,folder/'last_resume.pth')
            if step in [8000,16000,24000]:trajectory(base,gpu,job,model,step,events,acks)
    if {n for n,p in model.named_parameters() if p.requires_grad}-connected:raise RuntimeError('disconnected parameters')
    if any(not torch.equal(p.detach().cpu(),frozen[n]) for n,p in model.named_parameters() if n in frozen):raise RuntimeError('frozen parameter update')
    if any(p.grad is not None for tm in teachers.values() for p in tm.parameters()):raise RuntimeError('teacher acquired gradient')
    endpoint=folder/'endpoint.pth';torch.save(dict(job=job['id'],step=32000,seed=job['seed'],binding=c.binding(base),model=model.state_dict()),endpoint)
    c.write(folder/'complete.json',dict(binding=c.binding(base),job=job['id'],optimizer_updates=32000,initial_state_sha256=initial,
        checkpoint_sha256=c.sha(endpoint),batch_stream_sha256=c.sha(folder/'batch_hashes.jsonl'),physical_gpu=gpu,gpu_uuid=uuid,
        gradient_paths_checked=True,frozen_weights_unchanged=True,teacher_stopped=True,elapsed_seconds=time.monotonic()-started,observed_at=c.now()))
    del opt,teachers,frozen;gc.collect();torch.cuda.empty_cache()
    trajectory(base,gpu,job,model,32000,events,acks)
    del model;gc.collect();torch.cuda.empty_cache()

def damaged_rgb(item,condition,mask,seed):
    import torch
    from torch.nn import functional as F
    from scipy.ndimage import gaussian_filter
    x=np.array(item['rgb'],copy=True)
    if condition.startswith('down'):
        k=int(condition[4:]);a=torch.from_numpy(x.transpose(2,0,1)[None])
        low=F.interpolate(a,size=(x.shape[0]//k,x.shape[1]//k),mode='bilinear',align_corners=False,antialias=True)
        a=F.interpolate(low,size=x.shape[:2],mode='bilinear',align_corners=False)[0].numpy().transpose(1,2,0)
        x[mask]=a[mask]
    elif condition=='blur2':x[mask]=gaussian_filter(x,sigma=(2,2,0),mode='reflect')[mask]
    elif condition=='noise005':
        rng=np.random.Generator(np.random.PCG64(seed)); x[mask]=np.clip(x[mask]+rng.normal(0,.05,(int(mask.sum()),3)).astype(np.float32),0,1)
    return x

def infer_task(base,gpu,task,events,acks,cache):
    import torch
    from torch.nn import functional as F
    from phase24_ipc import Packet
    job=task['job']; tile=task['tile']; item=c.DATA[tile]
    if cache.get('id')!=job['id']:
        cache.clear();gc.collect();torch.cuda.empty_cache();cache['model']=make_model(base,job,True).eval().requires_grad_(False);cache['id']=job['id']
    packet=Packet.receive(task['mask_packet']) if 'mask_packet' in task else None
    try:
        condition=task['condition']
        if job['modality']=='rgb':
            image=item['rgb'] if condition=='clean' else damaged_rgb(item,condition,packet.arrays['mask'],c.key(tile,task.get('family'),task.get('realization'),'noise'))
        else:
            ds=item['dsm']
            if condition!='clean':
                raw=item['height']
                if condition=='dsm_down4':
                    low=F.interpolate(torch.from_numpy(raw.copy())[None,None],size=(raw.shape[0]//4,raw.shape[1]//4),mode='bilinear',align_corners=False,antialias=True)
                    raw=F.interpolate(low,size=raw.shape,mode='bilinear',align_corners=False)[0,0].numpy()
                elif condition=='dsm_shift8':raw=np.pad(raw,((0,0),(8,0)),mode='edge')[:,:raw.shape[1]]
                else:raise ValueError(condition)
                q=np.quantile(raw,[.05,.5,.95],method='linear');ds=np.float32(.5)+(raw-np.float32(q[1]))/np.float32(q[2]-q[0])
            image=np.repeat(ds[...,None],3,-1)
        score=infer(cache['model'],image,lambda done,total:c.write(Path(base)/f'gpu{gpu}.json',dict(job=job['id'],tile=tile,condition=condition,windows=done,total=total,observed_at=c.now())))
        metadata={n:v for n,v in task.items() if n not in ['mask_packet','job']};metadata.update(job=job['id'],kind='prediction')
        emit(base,gpu,events,acks,metadata,dict(score=score))
        del score,image
    finally:
        if packet:packet.close()

def worker(base,gpu,uuid,tasks,events,acks):
    os.environ.update(c.environment(base,uuid));os.setsid()
    import torch
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark=False;torch.backends.cuda.matmul.allow_tf32=True;torch.backends.cudnn.allow_tf32=True
    cache={}
    try:
        if torch.__version__!='2.2.2+cu121' or not torch.cuda.is_available():raise RuntimeError('expected original Torch2.2.2+cu121 CUDA environment')
        events.put(dict(kind='READY',gpu=gpu,gpu_uuid=uuid))
        while True:
            task=tasks.get()
            if task['kind']=='STOP':break
            try:
                if task['kind']=='TRAIN':
                    cache.clear();gc.collect();torch.cuda.empty_cache();train(base,gpu,task['job'],events,acks,uuid)
                else:infer_task(base,gpu,task,events,acks,cache)
                events.put(dict(kind='DONE',gpu=gpu,task_id=task['task_id']))
            except BaseException as exc:
                failure=dict(task_id=task['task_id'],error=str(exc),traceback=traceback.format_exc(),automatic_retry=False,observed_at=c.now())
                c.write(Path(base)/'failures'/(task['task_id']+'.json'),failure);events.put(dict(kind='FAILED',gpu=gpu,task_id=task['task_id'],error=str(exc)))
    except BaseException as exc:
        events.put(dict(kind='WORKER_FAILED',gpu=gpu,error=str(exc),traceback=traceback.format_exc()))
    finally:
        cache.clear();gc.collect();torch.cuda.empty_cache();events.put(dict(kind='EXIT',gpu=gpu))
