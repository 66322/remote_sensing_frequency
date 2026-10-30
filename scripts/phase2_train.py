"""Matched 16k experts and cached 8k fusion heads; no recipe retries."""
import argparse
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from torch.nn import functional as F
from phase2_common import *
from phase2_data import *
from model.phase2_matched import MatchedExpert,FusionHead,optimizer,factor,observables

def segmentation_ce(logits,target):
    """Unweighted FP32 mean CE, without CUDA NLLLoss's nondeterministic reduction.

    Classwise where has no indexed backward accumulation. The denominator counts
    every nonignored pixel across the batch, exactly as reduction='mean'.
    """
    if target.shape!=logits.shape[:1]+logits.shape[2:] or target.dtype!=torch.int64:
        raise ValueError('CE target shape/dtype differs')
    valid=target!=255
    if bool((valid&((target<0)|(target>=logits.shape[1]))).any()):
        raise ValueError('CE target outside class range')
    logp=F.log_softmax(logits.float(),dim=1)
    total=logp.new_zeros(())
    for c in range(logits.shape[1]):
        total=total+torch.where(target==c,-logp[:,c],0.).sum()
    return total/valid.sum()

def smoke_ce(device):
    """Real-device repeatability and CPU-reference check before the costly smoke."""
    x=torch.linspace(-2,2,2*6*7*9,device=device).reshape(2,6,7,9)
    target=(torch.arange(2*7*9,device=device).reshape(2,7,9)%6).long();target[:,0]=255
    results=[]
    for _ in range(2):
        z=x.clone().requires_grad_();loss=segmentation_ce(z,target);loss.backward()
        results.append((loss.detach(),z.grad.detach()))
    if not all(torch.equal(a,b) for a,b in zip(*results)):
        raise RuntimeError('real-device CE repeatability failed')
    ref=x.cpu().requires_grad_();loss=F.cross_entropy(ref,target.cpu(),ignore_index=255);loss.backward()
    torch.testing.assert_close(results[0][0].cpu(),loss.detach(),rtol=1e-6,atol=1e-7)
    torch.testing.assert_close(results[0][1].cpu(),ref.grad,rtol=1e-5,atol=1e-7)
    return dict(formula='classwise_log_softmax_where_mean_valid',repeat_exact=True,cpu_reference_close=True)

def model_digest(model):
    h=hashlib.sha256()
    for n,v in model.state_dict().items():
        h.update(n.encode());h.update(v.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()

def expert(base):
    torch.manual_seed(42)
    source=read(Path(base)/'pretrained.json')
    if sha(source['path'])!=source['sha256']:raise RuntimeError('pretrained binding differs')
    encoder=torch.hub.load(source['repository'],'dinov2_vits14',source='local',pretrained=False)
    encoder.load_state_dict(torch.load(source['path'],map_location='cpu',weights_only=False),strict=True)
    model=MatchedExpert(encoder)
    if len(encoder.blocks)!=12:raise RuntimeError('expected twelve encoder blocks')
    return model.cuda()

def trained(base,job,age=16000):
    folder=Path(base)/'jobs'/job;done=read(folder/'complete.json')
    if done['binding']!=binding(base) or done['optimizer_updates']!=16000:raise RuntimeError('expert completion changed')
    f=folder/('step_%05d.pth'%age)
    receipt=read(folder/('step_%05d.json'%age))
    if receipt['sha256']!=sha(f) or done['files'].get(f.name)!=receipt['sha256']:raise RuntimeError('checkpoint bytes changed')
    st=torch.load(f,map_location='cpu',weights_only=False)
    if st['job']!=job or st['step']!=age or st['binding']!=binding(base):raise RuntimeError('checkpoint identity differs')
    model=expert(base);model.load_state_dict(st['model'],strict=True)
    return model.eval().requires_grad_(False)

def save(base,out,job,model,opt,step,initial,best):
    name='step_%05d'%step;path=out/(name+'.pth');tmp=path.with_suffix('.tmp')
    torch.save(dict(job=job,step=step,binding=binding(base),model=model.state_dict(),optimizer=opt.state_dict(),
                    initial=initial,best=best,rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all()),tmp)
    os.replace(tmp,path);write(out/(name+'.json'),dict(sha256=sha(path),step=step,binding=binding(base)))

def gradients(model):
    missing=[];nonzero=[]
    for n,p in model.named_parameters():
        if p.requires_grad:
            if p.grad is None or not torch.isfinite(p.grad).all():missing.append(n)
            elif bool(p.grad.abs().sum()>0):nonzero.append(n)
        elif p.grad is not None:raise RuntimeError('frozen parameter gradient: '+n)
    if missing:raise RuntimeError('gradient connectivity failed: '+str(missing))
    return nonzero

def smoke(base,gpu):
    ce_check=smoke_ce('cuda')
    model=expert(base);out=Path(base)/'smoke'/('gpu'+str(gpu));out.mkdir(parents=True,exist_ok=False)
    init=model_digest(model);names=[(n,list(p.shape),p.numel()) for n,p in model.named_parameters() if p.requires_grad]
    sample_batch=Crops(base,'phase21',stop=1)
    samples=[sample_batch[i] for i in range(16)]
    batch=torch.stack([x['rgb'] if gpu==0 else x['dsm'][None].repeat(3,1,1) for x in samples]).cuda()
    target=torch.stack([x['gt'] for x in samples]).cuda();model.train()
    with torch.autocast('cuda',dtype=torch.bfloat16):
        low=model.low(batch)
        with torch.no_grad():z=model(batch)
    if not torch.equal(z,F.interpolate(low,size=batch.shape[-2:],mode='nearest')):raise RuntimeError('compact logits not exact')
    train_logits=F.interpolate(low,batch.shape[-2:],mode='nearest')
    loss=segmentation_ce(train_logits,target);loss.backward();nonzero=gradients(model)
    with torch.inference_mode():
        native_rgb=torch.stack([x['rgb'] for x in samples]).cuda();native_ds=torch.stack([x['dsm'] for x in samples]).cuda()
        full=torch.ones_like(native_ds,dtype=torch.bool)
        real_observables=observables(low.detach().float(),low.detach().float(),native_rgb,native_ds,full,full)
        if real_observables.shape!=(16,12,128,128) or not torch.isfinite(real_observables).all():raise RuntimeError('actual observable grid/nonfinite')
    if not any(n.startswith('encoder.blocks.') for n in nonzero):raise RuntimeError('encoder tail has no nonzero gradients')
    for arm in ('B0','B1','B2','B3'):
        head=FusionHead(arm).cuda();r=torch.randn(2,6,8,8,device='cuda');d=torch.randn_like(r)
        obs=torch.rand(2,12,8,8,device='cuda');rm=torch.ones(2,32,32,dtype=torch.bool,device='cuda');dm=rm.clone();rm[:,:16]=False
        zz=head(r,d,obs,rm,dm)
        if not torch.equal(zz.masked_select((~rm&dm)[:,None]),F.interpolate(d,size=(32,32),mode='nearest').masked_select((~rm&dm)[:,None])):
            raise RuntimeError('head exact fallback failed')
    write(out/'result.json',dict(initial_state_sha256=init,trainable=names,total_trainable=sum(n[2] for n in names),
        compact_logit_exact=True,head_fallback_exact=True,gradient_nonzero=nonzero,physical_gpu=gpu,optimizer_updates=0,
        actual_physical_batch=16,actual_observables_finite=True,ce_check=ce_check,**gpu_metrics()))
    complete(base,out,dict(all_passed=True,optimizer_updates=0))

def train_expert(base,job,gpu):
    out=Path(base)/'jobs'/job;out.mkdir(parents=True,exist_ok=False);model=expert(base)
    initial=model_digest(model);opt=optimizer(model,16000);seen=set();best=None
    write(out/'parameters.json',dict(initial_state_sha256=initial,trainable=[(n,list(v.shape),v.numel()) for n,v in model.named_parameters() if v.requires_grad]))
    from d24_data import PrefetchedBatches
    profile=read(Path(base)/'resource_profile.json');dataset=Crops(base,'phase21',stop=16000)
    started=time.monotonic();last=time.monotonic()
    with (out/'batch_hashes.jsonl').open('x',encoding='utf-8') as hashes,(out/'trajectory.jsonl').open('x',encoding='utf-8') as trajectory:
        for step,batch in enumerate(PrefetchedBatches(dataset,16,profile['crop_workers'],profile['prefetch_batches'],True),1):
            wait=time.monotonic()-last;model.train();opt.zero_grad(set_to_none=True)
            image=batch['rgb'] if job=='A_RGB' else batch['dsm'][:,None].repeat(1,3,1,1)
            image=image.cuda(non_blocking=True);gt=batch['gt'].cuda(non_blocking=True)
            for g in opt.param_groups:g['lr']=g['initial_lr']*factor(step,16000)
            with torch.autocast('cuda',dtype=torch.bfloat16):z=model(image)
            loss=segmentation_ce(z,gt);loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(),float('inf'),error_if_nonfinite=True)
            if step==1 or step%500==0:seen.update(gradients(model))
            opt.step()
            token=batch_hash(batch['token']);hashes.write(json.dumps(dict(step=step,batch_hash=token))+'\n')
            if step%20==0 or step==1:
                elapsed=time.monotonic()-started
                row=dict(step=step,loss=float(loss),data_wait_seconds=wait,elapsed_seconds=elapsed,
                         remaining_train_hours=(16000-step)*elapsed/step/3600,physical_gpu=gpu,observed_at=now(),**gpu_metrics())
                trajectory.write(json.dumps(row)+'\n');trajectory.flush();hashes.flush();write(out/'progress.json',row)
            if step%500==0:save(base,out,job,model,opt,step,initial,best)
            if step in (4000,8000,12000,16000):
                from phase2_infer import clean_validation
                scores=clean_validation(base,model,job,out/('validation_%05d'%step))
                if best is None or scores['full_fg5']>best['score']:best=dict(step=step,score=scores['full_fg5'])
                save(base,out,job,model,opt,step,initial,best)
            last=time.monotonic()
    declared={n for n,p in model.named_parameters() if p.requires_grad}
    if declared-seen:raise RuntimeError('declared parameters never observed nonzero: '+str(declared-seen))
    write(out/'selection.json',dict(secondary_clean_selected=best,primary_fixed_endpoint=16000))
    complete(base,out,dict(job=job,optimizer_updates=16000,initial_state_sha256=initial,gradient_contract=True))

def build_head_cache(base,gpu):
    r=trained(base,'A_RGB');d=trained(base,'A_DSM');profile=read(Path(base)/'resource_profile.json')
    from d24_data import PrefetchedBatches
    start,stop=(0,4000) if gpu==0 else (4000,8000)
    dataset=Crops(base,'phase23',start,stop);folder=Path(base)/'head_cache';folder.mkdir(exist_ok=True)
    with torch.inference_mode():
        for step,batch in enumerate(PrefetchedBatches(dataset,16,profile['crop_workers'],profile['prefetch_batches'],True),start+1):
            batch={k:v.cuda(non_blocking=True) if torch.is_tensor(v) else v for k,v in batch.items()}
            rgb,ds,rm,dm,kinds=training_view(batch,step)
            a=r.low(rgb).float();b=d.low(ds[:,None].repeat(1,3,1,1)).float();obs=observables(a,b,rgb,ds,rm,dm)
            # Uncompressed NPZ permits one read per cached batch; no repeated expert forward in heads.
            path=folder/('%05d.npz'%step);tmp=path.with_suffix('.tmp')
            with tmp.open('wb') as f:np.savez(f,r=a.cpu().numpy(),d=b.cpu().numpy(),obs=obs.cpu().numpy(),
                gt=batch['gt'].cpu().numpy().astype(np.uint8),rm=np.packbits(rm.cpu().numpy(),bitorder='little'),
                dm=np.packbits(dm.cpu().numpy(),bitorder='little'))
            os.replace(tmp,path)
            write(folder/('%05d.json'%step),dict(sha256=sha(path),batch_hash=batch_hash(batch['token']),treatments=kinds,binding=binding(base)))
            if step%20==0:write(Path(base)/('head_cache_gpu'+str(gpu)+'.json'),dict(step=step,target=stop,observed_at=now(),physical_gpu=gpu))
    complete(base,Path(base)/('cache_lane'+str(gpu)),dict(start=start+1,stop=stop))

def cache_host(base,step):
    import io
    f=Path(base)/'head_cache'/('%05d.npz'%step);receipt=read(f.with_suffix('.json'))
    raw=f.read_bytes()
    if receipt['binding']!=binding(base) or hashlib.sha256(raw).hexdigest()!=receipt['sha256']:raise RuntimeError('head cache changed')
    with np.load(io.BytesIO(raw),allow_pickle=False) as z:
        result={n:torch.from_numpy(z[n]).pin_memory() for n in ('r','d','obs')}
        result['gt']=torch.from_numpy(z['gt'].astype(np.int64)).pin_memory()
        for n in ('rm','dm'):
            result[n]=torch.from_numpy(np.unpackbits(z[n],bitorder='little',count=16*512*512).reshape(16,512,512).astype(bool)).pin_memory()
    return result,receipt['batch_hash']

def train_head(base,job,gpu):
    out=Path(base)/'jobs'/job;out.mkdir(parents=True,exist_ok=False);torch.manual_seed(42)
    model=FusionHead(job).cuda();initial=model_digest(model);opt=optimizer(model,8000);start=time.monotonic()
    write(out/'parameters.json',dict(initial_state_sha256=initial,total_trainable=sum(p.numel() for p in model.parameters()),
        trainable=[(n,list(p.shape),p.numel()) for n,p in model.named_parameters()],experts_frozen=True,
        head_precision='FP32',common_cache_binding=binding(base)))
    # Read-ahead shares host memory; CUDA transfers remain in the main worker.
    from concurrent.futures import ThreadPoolExecutor
    from collections import deque
    with (out/'batch_hashes.jsonl').open('x',encoding='utf-8') as hashes,ThreadPoolExecutor(max_workers=4) as pool:
        ready=deque(pool.submit(cache_host,base,s) for s in range(1,9));next_step=9
        for step in range(1,8001):
            t=time.monotonic();x,token=ready.popleft().result();wait=time.monotonic()-t
            if next_step<=8000:ready.append(pool.submit(cache_host,base,next_step));next_step+=1
            x={n:a.cuda(non_blocking=True) for n,a in x.items()}
            opt.zero_grad(set_to_none=True)
            for g in opt.param_groups:g['lr']=g['initial_lr']*factor(step,8000)
            z=model(x['r'],x['d'],x['obs'],x['rm'],x['dm']);loss=segmentation_ce(z,x['gt'])
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),float('inf'),error_if_nonfinite=True);opt.step()
            hashes.write(json.dumps(dict(step=step,batch_hash=token))+'\n')
            if step==1 or step%20==0:
                write(out/'progress.json',dict(step=step,target=8000,loss=float(loss),data_wait_seconds=wait,
                     elapsed_seconds=time.monotonic()-start,physical_gpu=gpu,observed_at=now(),**gpu_metrics()));hashes.flush()
            if step%500==0:save(base,out,job,model,opt,step,initial,None)
    complete(base,out,dict(job=job,optimizer_updates=8000,initial_state_sha256=initial,experts_frozen=True))

def load_head(base,job):
    if job=='average':return None
    folder=Path(base)/'jobs'/job;done=read(folder/'complete.json')
    if done['binding']!=binding(base) or done['optimizer_updates']!=8000:raise RuntimeError('head completion changed')
    path=folder/'step_08000.pth'
    if sha(path)!=read(folder/'step_08000.json')['sha256'] or done['files'].get(path.name)!=sha(path):raise RuntimeError('head checkpoint changed')
    st=torch.load(path,map_location='cpu',weights_only=False)
    if st['binding']!=binding(base) or st['step']!=8000:raise RuntimeError('head age/source changed')
    model=FusionHead(job).cuda();model.load_state_dict(st['model']);return model.eval().requires_grad_(False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--gpu',type=int,required=True);parser.add_argument('--task',required=True)
    args=parser.parse_args();base=args.directory.resolve();runtime(base,args.gpu)
    if args.task=='smoke':smoke(base,args.gpu)
    elif args.task in ('A_RGB','A_DSM'):train_expert(base,args.task,args.gpu)
    elif args.task=='head_cache':build_head_cache(base,args.gpu)
    elif args.task in ('B0','B1','B2','B3'):train_head(base,args.task,args.gpu)
    else:raise ValueError(args.task)
