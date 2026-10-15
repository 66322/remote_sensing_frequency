"""GPU worker; paired 16k experts and immediate RAM handoff, no disk logits."""
import os
import sys
import time
import traceback
import gc
import hashlib
import json
from pathlib import Path
# Absolute script execution exposes scripts/, but not its sibling model/ package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import phase3_m1_common as c
_MODELS={}

def clear_models():
    _MODELS.clear()
    gc.collect()

def cached_model(base,key,loader):
    if key not in _MODELS:
        clear_models(); _MODELS[key]=loader()
    return _MODELS[key]

def make_model(base,seed,stem):
    import torch
    from model.phase2_matched import MatchedExpert
    p=c.read(Path(base)/'plan.json'); source=c.read(Path(p['previous'])/'pretrained.json')
    torch.manual_seed(seed)
    encoder=torch.hub.load(source['repository'],'dinov2_vits14',source='local',pretrained=False)
    encoder.load_state_dict(torch.load(source['path'],map_location='cpu',weights_only=False),strict=True)
    model=MatchedExpert(encoder)
    if stem: model.encoder.patch_embed.proj.requires_grad_(True)
    return model.cuda()

def load_old(base,job):
    import torch
    old=Path(c.read(Path(base)/'plan.json')['previous']); f=old/'jobs'/job/'step_16000.pth'
    st=torch.load(f,map_location='cpu',weights_only=False)
    model=make_model(base,42,False); model.load_state_dict(st['model'],strict=True)
    return model.eval().requires_grad_(False)

def load_job(base,job):
    import torch
    if job=='M00_42': return load_old(base,'A_DSM')
    f=Path(base)/'jobs'/job/'endpoint.pth'; done=c.read(f.parent/'complete.json')
    if not c.job_binding_ok(base,job,done) or c.sha(f)!=done['checkpoint_sha256']: raise RuntimeError('endpoint changed')
    arm,seed=job.split('_'); model=make_model(base,int(seed),c.ARMS[arm][1])
    model.load_state_dict(torch.load(f,map_location='cpu',weights_only=False)['model'],strict=True)
    return model.eval().requires_grad_(False)

def progress(base,gpu,**kw): c.write(Path(base)/f'progress_gpu{gpu}.json',dict(physical_gpu=gpu,observed_at=c.now(),**kw))

def infer(base,gpu,model,image):
    import torch
    from torch.nn import functional as F
    from phase2_infer import coords
    shape=image.shape[:2]; cs=coords(shape); score=torch.zeros((6,*shape),device='cuda',dtype=torch.float32)
    coverage=np.zeros(shape,np.uint16)
    model.eval()
    with torch.inference_mode():
        for start in range(0,len(cs),8):
            use=cs[start:start+8]; n=len(use)
            batch=np.stack([image[y:y+512,x:x+512].transpose(2,0,1) for y,x in use])
            x=torch.from_numpy(batch).cuda()
            if n<8: x=torch.cat((x,x[-1:].expand(8-n,-1,-1,-1)))
            low=model.low(x).float()
            if low.shape[-2:]!=(128,128): raise RuntimeError('native inference grid changed')
            zz=F.interpolate(low,size=(512,512),mode='nearest')
            for i,(y,col) in enumerate(use):
                score[:,y:y+512,col:col+512].add_(zz[i]); coverage[y:y+512,col:col+512]+=1
            if start%80==0 or start+n==len(cs): progress(base,gpu,phase='INFER',windows_done=start+n,windows_total=len(cs))
    if not coverage.all() or not bool(torch.isfinite(score).all()): raise RuntimeError('incomplete/nonfinite stitch')
    return score.cpu().numpy()

def handoff(events,acks,gpu,task,arrays):
    from phase24_ipc import Packet
    packet=Packet.create(arrays)
    events.put(dict(kind='PACKET',gpu=gpu,task=task,packet=packet.descriptor()))
    reply=acks.get()
    packet.close()
    if reply.get('error'): raise RuntimeError(reply['error'])

def validation(base,gpu,model):
    from phase3_m1_numeric import primary
    from phase3_m1_data import normalize
    # Caller sets current arm; no dataset/random state is changed by validation.
    out={}
    for t in c.VAL:
        height=normalize(c.DATA[t]['height'],t,model._m1_rep)
        image=np.repeat(height[...,None],3,-1)
        score=infer(base,gpu,model,image); out[t]=primary(score,t); del score,image,height
    return out

def restore_checkpoint(base,job,model,opt,initial):
    import torch
    r=c.recovery(base)
    if not r or job not in r['resumed']: return 0,0.
    row=r['resumed'][job]; f=Path(row['path'])
    if c.sha(f)!=row['sha256']: raise RuntimeError('resume checkpoint changed')
    if c.sha(Path(base)/'jobs'/job/'batch_hashes.jsonl')!=row['prefix_sha256']:
        raise RuntimeError('resume stream prefix changed')
    state=torch.load(f,map_location='cpu',weights_only=False)
    if state['binding']!=r['previous_binding'] or state['job']!=job or state['step']!=row['step']:
        raise RuntimeError('resume checkpoint identity differs')
    if c.read(Path(base)/'jobs'/job/'parameters.json')['initial_state_sha256']!=initial:
        raise RuntimeError('resume initialization differs')
    model.load_state_dict(state['model'],strict=True); opt.load_state_dict(state['optimizer'])
    torch.set_rng_state(state['rng']); torch.cuda.set_rng_state_all(state['cuda_rng'])
    c.write(Path(base)/'jobs'/job/'resume_loaded.json',dict(source_sha256=row['sha256'],source_binding=r['previous_binding'],
        step=row['step'],optimizer_restored=True,cpu_cuda_rng_restored=True,sample_stream_start=row['step']+1,
        prefix_sha256=c.sha(Path(base)/'jobs'/job/'batch_hashes.jsonl'),observed_at=c.now()))
    return row['step'],row['elapsed_seconds']

def train(base,gpu,task,events,acks):
    import torch
    from phase2_train import segmentation_ce,model_digest,gradients
    from model.phase2_matched import optimizer,factor
    from d24_data import PrefetchedBatches
    from phase3_m1_data import Crops
    base=Path(base); arm=task['arm']; seed=task['seed']; job=task['job']; folder=base/'jobs'/job
    r=c.recovery(base); resuming=bool(r and job in r['resumed'])
    if resuming:
        if (folder/'complete.json').exists(): raise RuntimeError('refuse retraining completed job')
    else: folder.mkdir(parents=True,exist_ok=False)
    clear_models()
    model=make_model(base,seed,c.ARMS[arm][1]); model._m1_rep=c.ARMS[arm][0]
    initial=model_digest(model); opt=optimizer(model,16000)
    frozen={n:p.detach().clone() for n,p in model.named_parameters() if not p.requires_grad}
    names=[(n,list(p.shape),p.numel()) for n,p in model.named_parameters() if p.requires_grad]
    start_step,elapsed_before=restore_checkpoint(base,job,model,opt,initial)
    c.write(folder/'parameters.json',dict(binding=c.binding(base),job=job,seed=seed,initial_state_sha256=initial,
       trainable=names,stem_trainable=c.ARMS[arm][1],input_representation=model._m1_rep,updates=16000,batch=16,physical_gpu=gpu))
    if seed==42:
        expected=c.read(Path(c.read(base/'plan.json')['previous'])/'jobs/A_DSM/parameters.json')['initial_state_sha256']
        c.write(folder/'legacy_initial_check.json',dict(exact=initial==expected,expected=expected,actual=initial))
    pf=c.read(base/'resource_profile.json'); started=time.monotonic(); seen=set()
    stream=PrefetchedBatches(Crops(arm,seed,start_step),16,pf['crop_workers'],4,True)
    with (folder/'batch_hashes.jsonl').open('a' if resuming else 'x') as hashes,(folder/'trajectory.jsonl').open('a' if resuming else 'x') as trajectory:
        for step,batch in enumerate(stream,start_step+1):
            model.train(); opt.zero_grad(set_to_none=True)
            image=batch['dsm'][:,None].repeat(1,3,1,1).cuda(non_blocking=True); target=batch['gt'].cuda(non_blocking=True)
            for group in opt.param_groups: group['lr']=group['initial_lr']*factor(step,16000)
            with torch.autocast('cuda',dtype=torch.bfloat16): z=model(image)
            loss=segmentation_ce(z,target); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(),float('inf'),error_if_nonfinite=True)
            if step==start_step+1 or step%500==0: seen.update(gradients(model))
            before=model.encoder.patch_embed.proj.weight.detach().clone() if step==start_step+1 and c.ARMS[arm][1] else None
            opt.step()
            if before is not None:
                if torch.equal(before,model.encoder.patch_embed.proj.weight): raise RuntimeError('stem did not update')
                c.write(folder/('resume_gradient_path.json' if resuming else 'gradient_path.json'),dict(stem_changed=True,early8_weights_frozen=True,step=step))
            token=hashlib.sha256('|'.join(batch['token']).encode()).hexdigest()
            hashes.write(json.dumps(dict(step=step,batch_hash=token))+'\n')
            if step==start_step+1 or step%20==0:
                row=dict(step=step,loss=float(loss),elapsed_seconds=elapsed_before+time.monotonic()-started,
                         remaining_train_hours=(16000-step)*(time.monotonic()-started)/(step-start_step)/3600)
                trajectory.write(json.dumps(row)+'\n'); trajectory.flush(); hashes.flush()
                c.write(folder/'progress.json',dict(row,observed_at=c.now(),physical_gpu=gpu))
                progress(base,gpu,phase='TRAIN',job=job,**row)
                if step==start_step+1 or step%500==0: print('M1_TRAIN',gpu,job,step,row,flush=True)
            if step%1000==0 and step<16000:
                f=folder/'last_resume.pth'; tmp=f.with_suffix('.tmp')
                torch.save(dict(model=model.state_dict(),optimizer=opt.state_dict(),step=step,job=job,
                     binding=c.binding(base),rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all()),tmp); os.replace(tmp,f)
            if step in (4000,8000,12000): c.write(folder/f'validation_{step:05d}.json',dict(step=step,tiles=validation(base,gpu,model)))
    if {n for n,p in model.named_parameters() if p.requires_grad}-seen: raise RuntimeError('trainable parameter never connected')
    if any(not torch.equal(p,frozen[n]) for n,p in model.named_parameters() if n in frozen): raise RuntimeError('frozen parameters changed')
    del frozen,opt
    endpoint=folder/'endpoint.pth'; torch.save(dict(model=model.state_dict(),step=16000,job=job,seed=seed,binding=c.binding(base)),endpoint)
    c.write(folder/'complete.json',dict(binding=c.binding(base),job=job,optimizer_updates=16000,
        checkpoint_sha256=c.sha(endpoint),initial_state_sha256=initial,frozen_parameters_unchanged=True,
        trainable_gradients_connected=True,physical_gpu=gpu,elapsed_train_seconds=elapsed_before+time.monotonic()-started,
        resumed_from_step=start_step,completed_at=c.now()))
    # Each clean packet is handed to CPU immediately; GPU does not wait for counting.
    from phase3_m1_data import normalize
    for t in c.VAL:
        height=normalize(c.DATA[t]['height'],t,c.ARMS[arm][0]); image=np.repeat(height[...,None],3,-1)
        score=infer(base,gpu,model,image)
        handoff(events,acks,gpu,dict(kind='DSM_CLEAN',job=job,tile=t),dict(score=score))
        del score,image,height
    del model; gc.collect(); torch.cuda.empty_cache()

def execute(base,gpu,task,events,acks):
    import torch
    from phase3_m1_data import normalize
    tile=task.get('tile'); kind=task['kind']; old=Path(c.read(Path(base)/'plan.json')['previous'])
    if kind=='RELEASE_FIT': return c.release_fit(base,'gpu'+str(gpu))
    if kind=='TRAIN': return train(base,gpu,task,events,acks)
    model=cached_model(base,'RGB',lambda:load_old(base,'A_RGB')) if kind.startswith('RGB') else cached_model(base,task['job'],lambda:load_job(base,task['job']))
    if kind=='SCALE':
        from torch.nn import functional as F
        rows=[]; rep=c.ARMS[task['job'].split('_')[0]][0]
        normalized={}; saved=c.STATS[tile]
        for gsd in (5,10):
            c.STATS[tile]=saved if gsd==5 else saved['gsd10']
            normalized[gsd]=normalize(c.DATA[tile]['height' if gsd==5 else 'height_gsd10'],tile,rep)
        c.STATS[tile]=saved
        with torch.inference_mode():
            for yy in (1024,2304,3584,4864):
                for xx in (1024,2304,3584,4864):
                    for gsd,side in ((5,512),(10,512),(5,1024),(10,1024)):
                        factor=gsd//5; cy,cx=yy//factor,xx//factor; half=side//factor//2
                        crop=normalized[gsd][cy-half:cy+half,cx-half:cx+half]
                        x=torch.from_numpy(crop.copy())[None,None].cuda().repeat(1,3,1,1)
                        z=F.interpolate(model(x).float(),size=(side,side),mode='nearest').argmax(1)[0].cpu().numpy().astype(np.uint8)
                        k=side//2; pred=z[k-128:k+128,k-128:k+128]
                        gt=c.DATA[tile]['noboundary_gt'][yy-128:yy+128,xx-128:xx+128]
                        rows.append(dict(y=yy,x=xx,gsd_cm=gsd,fov_m=side*.05,cm=c.cm(gt,pred,np.ones(gt.shape,bool)).tolist()))
        c.write(Path(base)/'scale'/f"{task['job']}_{tile}.json",dict(job=task['job'],tile=tile,rows=rows,common_roi_native=256,fixed_training_S=c.STATS['_S']))
    else:
        mask=None
        if kind.startswith('RGB'):
            image=np.array(c.DATA[tile]['optical'])
            if kind=='RGB_FAULT':
                from phase15_numeric import decode_mask
                row=c.read(old/'mask_manifest.json')['tiles'][tile][str(task['realization'])][task['family']]['25']
                mask=decode_mask(row['path'])
                image[mask]=0 if task['damage']=='zero' else c.DATA[tile]['rgb_down4'][mask]
        else:
            raw=c.DATA[tile]['height']; arm=task['job'].split('_')[0]
            if kind=='DSM_FAULT':
                if task['damage']=='down4':
                    from phase2_data import down4
                    with torch.inference_mode(): raw=down4(torch.from_numpy(raw.copy())[None,None])[0,0].numpy()
                else: raw=np.pad(raw,((0,0),(8,0)),mode='edge')[:,:raw.shape[1]]
                # Observed damaged input, not hidden pre-damage statistics.
                q=np.quantile(raw,[.05,.5,.95],method='linear'); saved=c.STATS[tile]
                c.STATS[tile]=dict(min=float(raw.min()),max=float(raw.max()),median=float(q[1]),span=float(q[2]-q[0]))
            height=normalize(raw,tile,c.ARMS[arm][0]); image=np.repeat(height[...,None],3,-1)
            if kind=='DSM_FAULT': c.STATS[tile]=saved
        score=infer(base,gpu,model,image)
        if kind=='DSM_FAULT': mask=np.ones(score.shape[1:],bool)
        extra={}
        if mask is not None:
            from scipy.ndimage import maximum_filter
            extra=dict(mask=mask,healthy=~maximum_filter(mask,size=17,mode='constant',cval=0).astype(bool))
        handoff(events,acks,gpu,task,dict(score=score,**extra))
        del image,score
    del model; gc.collect(); torch.cuda.empty_cache()

def worker(base,gpu,tasks,events,acks):
    os.setsid()
    from phase24_common import env
    os.environ.update(env(base,gpu))
    import torch
    torch.set_num_threads(1); torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark=False; torch.backends.cuda.matmul.allow_tf32=True; torch.backends.cudnn.allow_tf32=True
    try:
        if torch.__version__!='2.2.2+cu121' or not torch.cuda.is_available(): raise RuntimeError('expected original Torch2.2.2+cu121 CUDA runtime')
        events.put(dict(kind='READY',gpu=gpu))
        while True:
            task=tasks.get()
            if task['kind']=='STOP': break
            try:
                execute(base,gpu,task,events,acks)
                events.put(dict(kind='DONE',gpu=gpu,task=task))
            except BaseException as exc:
                failure=dict(error=str(exc),traceback=traceback.format_exc(),task=task,automatic_retry=False,observed_at=c.now())
                if task['kind']=='TRAIN':
                    folder=Path(base)/'jobs'/task['job']; c.write(folder/'failure.json',failure)
                    # A train-complete marker alone is insufficient if post-train evaluation failed.
                c.write(Path(base)/'failures'/(str(c.key(task))+'.json'),failure)
                events.put(dict(kind='FAILED',gpu=gpu,task=task,error=str(exc)))
                gc.collect(); torch.cuda.empty_cache()
            events.put(dict(kind='READY',gpu=gpu))
    except BaseException as exc:
        events.put(dict(kind='FATAL',gpu=gpu,error=str(exc),traceback=traceback.format_exc()))
    finally:
        clear_models(); torch.cuda.empty_cache()
        c.write(Path(base)/f'worker{gpu}_exit.json',dict(gpu=gpu,observed_at=c.now()))

