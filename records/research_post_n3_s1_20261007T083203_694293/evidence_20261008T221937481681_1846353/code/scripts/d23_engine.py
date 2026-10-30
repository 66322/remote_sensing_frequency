"""D23 matched sample stream, gate fitting and uniform-logit full-image stitching."""
import hashlib
import random
from collections import OrderedDict
import numpy as np
import torch
from torch.nn import functional as F

PROBABILITIES={'clean':.2,'rgb_down2':.1,'rgb_down4':.1,'rgb_blur5':.1,
 'rgb_local_down4_q1':.1,'aux_down4':.1,'aux_noise_std010':.1,'aux_zero':.1,'aux_local_zero_q1':.1}
CONDITIONS=tuple(PROBABILITIES)+('rgb_contrast060','aux_shift8','aux_local_zero_stripe_eighth','aux_noise_std020','aux_shift16')
FIXED=('R0','M0_safe','confidence','entropy','logit_average','probability_average')


def key(*values):
    return int.from_bytes(hashlib.sha256('|'.join(map(str,values)).encode()).digest()[:8],'big')


def partition(split):
    train,val,test=map(set,(split['train16'],split['val2'],split['historical_exposed_test6']))
    held={'6_10','7_10','4_11','7_11'}
    if len(train)!=16 or val!={'3_11','5_10'} or train&val or (train|val)&test or not held<=train:
        raise RuntimeError('split mismatch or leakage')
    return [t for t in split['train16'] if t not in held],sorted(held)


class TileCache:
    def __init__(self,loader,allowed,capacity=1):
        self.loader,self.allowed,self.capacity=loader,set(allowed),capacity
        self.items=OrderedDict()
    def get(self,tile):
        if tile not in self.allowed:raise RuntimeError('tile outside permitted phase')
        if tile not in self.items:
            self.items[tile]=self.loader(tile)
            while len(self.items)>self.capacity:self.items.popitem(last=False)
        self.items.move_to_end(tile)
        return self.items[tile]


def resize_restore(x,factor):
    h,w=x.shape[-2:]
    low=F.interpolate(x,size=(max(1,h//factor),max(1,w//factor)),mode='bilinear',align_corners=False,antialias=True)
    return F.interpolate(low,size=(h,w),mode='bilinear',align_corners=False)


def treatment(op,ds,kind,seed,numpy_noise=False):
    """On CPU, full-image damage before windows; training calls once per keyed sample."""
    if kind not in CONDITIONS:raise ValueError(kind)
    op,ds=op.clone(),ds.clone();mask=torch.ones_like(ds,dtype=torch.bool)
    h,w=ds.shape[-2:];ys,xs=slice(h//4,h//4+h//2),slice(w//4,w//4+w//2)
    if kind=='rgb_contrast060':op=((op-.5)*.6+.5).clamp(0,1)
    elif kind=='rgb_blur5':op=F.avg_pool2d(F.pad(op,(2,2,2,2),mode='reflect'),5,1)
    elif kind.startswith('rgb_'):
        damaged=resize_restore(op,2 if kind=='rgb_down2' else 4)
        if kind=='rgb_local_down4_q1':op[:,:,ys,xs]=damaged[:,:,ys,xs]
        else:op=damaged
    elif kind=='aux_down4':ds=resize_restore(ds[:,None],4)[:,0]
    elif kind.startswith('aux_noise'):
        if numpy_noise:
            noise=torch.from_numpy(np.random.Generator(np.random.PCG64(seed)).standard_normal(tuple(ds.shape),dtype=np.float32))
        else:noise=torch.randn(ds.shape,generator=torch.Generator().manual_seed(seed))
        ds=(ds+(.2 if kind=='aux_noise_std020' else .1)*noise).clamp(0,1)
    elif kind=='aux_zero':ds.zero_();mask.zero_()
    elif kind=='aux_local_zero_q1':ds[:,ys,xs]=0;mask[:,ys,xs]=False
    elif kind=='aux_local_zero_stripe_eighth':ds[:,h//4:3*h//8,:]=0;mask[:,h//4:3*h//8,:]=False
    elif kind in ('aux_shift8','aux_shift16'):
        shift=16 if kind=='aux_shift16' else 8
        ds=F.pad(ds[:,None],(shift,0,0,0),mode='replicate')[:,0,:,:w]
    return op,ds,mask


def sample_spec(ids,index,augmentation,patch=512,seed=42):
    rng=random.Random(key(seed,'sample',index))
    return dict(tile=rng.choice(ids),scale=rng.uniform(augmentation['random_scale_min'],augmentation['random_scale_max']),
                fy=rng.random(),fx=rng.random(),vflip=rng.random()<augmentation['vertical_flip_p'],
                hflip=rng.random()<augmentation['horizontal_flip_p'],
                treatment=rng.choices(list(PROBABILITIES),weights=list(PROBABILITIES.values()))[0],
                treatment_seed=key(seed,'treatment',index),index=index,patch=patch)


def materialize(cache,spec):
    tile=cache.get(spec['tile']);h,w=tile['dsm'].shape;p=spec['patch']
    size=max(1,min(round(p/spec['scale']),h,w))
    y=min(int(spec['fy']*(h-size+1)),h-size);x=min(int(spec['fx']*(w-size+1)),w-size)
    op=torch.from_numpy(np.ascontiguousarray(tile['optical'][y:y+size,x:x+size].transpose(2,0,1)))[None]
    ds=torch.from_numpy(np.ascontiguousarray(tile['dsm'][y:y+size,x:x+size]))[None,None]
    gt=torch.from_numpy(np.ascontiguousarray(tile['full_gt'][y:y+size,x:x+size]).astype(np.int64))[None,None]
    for flip,axis in ((spec['vflip'],-2),(spec['hflip'],-1)):
        if flip:op,ds,gt=(a.flip(axis) for a in (op,ds,gt))
    if size!=p:
        op=F.interpolate(op,size=(p,p),mode='bilinear',align_corners=False)
        ds=F.interpolate(ds,size=(p,p),mode='bilinear',align_corners=False)
        gt=F.interpolate(gt.float(),size=(p,p),mode='nearest').long()
    ds,gt=ds[:,0],gt[:,0]
    treated=treatment(op,ds,spec['treatment'],spec['treatment_seed'])
    return op[0],ds[0],gt[0],tuple(v[0] for v in treated)


def logical_batch(cache,ids,step,augmentation,patch=512,batch=16,stream='fit'):
    # Stream purpose is part of the key; neither arm nor microbatch enters the key.
    base=key(42,stream,step)*batch
    samples=[materialize(cache,sample_spec(ids,base+i,augmentation,patch)) for i in range(batch)]
    op,ds,gt=(torch.stack([s[i] for s in samples]) for i in range(3))
    treated=tuple(torch.stack([s[3][i] for s in samples]) for i in range(3))
    return (op,ds,torch.ones_like(ds,dtype=torch.bool)),treated,gt


def slices(batch,micro):
    return [slice(i,min(i+micro,batch)) for i in range(0,batch,micro)]


def utility_counts(inp,label,mask):
    p0,p1=inp['z0'].argmax(1),inp['z1'].argmax(1);valid=label!=255
    return dict(valid=int(valid.sum()),positive=int((valid&mask&(p1==label)&(p0!=label)).sum()),
                negative=int((valid&mask&(p0==label)&(p1!=label)).sum()))


def fit_update(pair,gate,optimizer,logical,loss_sums,micro=8,device='cuda',combine=None):
    if combine is None:raise ValueError('combined effective-batch loss required')
    clean,treated,labels=logical;parts=[]
    # H100 path: frozen experts at canonical micro8, gate at batch16, one backward.
    optimizer.zero_grad(set_to_none=True)
    for view in (clean,treated):
        chunks=[]
        for sl in slices(len(labels),micro):
            op,ds=(x[sl].to(device) for x in view[:2])
            chunks.append(pair(op,ds))
        inp={name:torch.cat([c[name] for c in chunks]) for name in chunks[0]}
        del chunks
        mask=view[2].to(device);gt=labels.to(device)
        out=gate(inp['E'],inp['S'],inp['F'],inp['z0'],inp['z1'],mask)
        if not torch.equal(out['logits'].permute(0,2,3,1)[~mask],inp['z0'].permute(0,2,3,1)[~mask]):
            raise RuntimeError('crop fallback changed')
        parts.append(loss_sums(out['logits'],out['gate_logits'],inp['z0'],inp['z1'],gt,mask))
        del inp,out
    loss=combine(parts,utility_weight=0. if gate.arm=='TSF_CE' else 1.)
    if not torch.isfinite(loss):raise RuntimeError('nonfinite combined loss')
    loss.backward()
    torch.nn.utils.clip_grad_norm_(gate.parameters(),float('inf'),error_if_nonfinite=True)
    if any(p.grad is not None for p in pair.parameters()):raise RuntimeError('expert gradient')
    optimizer.step()
    return float(loss.detach()),{name:sum(p[name] for p in parts) for name in ('valid','positive','negative')}


def fit_update_low_memory(pair,gate,optimizer,logical,loss_sums,micro=8,device='cuda'):
    clean,treated,labels=logical;chunks=slices(len(labels),micro)
    totals=dict(valid=0,positive=0,negative=0)
    # Two passes: global denominators, then backprop; never cache whole-batch S.
    for view in (clean,treated):
        for sl in chunks:
            op,ds,mask=(x[sl].to(device) for x in view);gt=labels[sl].to(device)
            inp=pair(op,ds)
            for name,value in utility_counts(inp,gt,mask).items():totals[name]+=value
            del inp
    optimizer.zero_grad(set_to_none=True);value=0.;second=dict(valid=0,positive=0,negative=0)
    for view in (clean,treated):
        for sl in chunks:
            op,ds,mask=(x[sl].to(device) for x in view);gt=labels[sl].to(device)
            inp=pair(op,ds);out=gate(inp['E'],inp['S'],inp['F'],inp['z0'],inp['z1'],mask)
            parts=loss_sums(out['logits'],out['gate_logits'],inp['z0'],inp['z1'],gt,mask)
            loss=parts['ce_sum']/max(1,totals['valid'])
            if gate.arm!='TSF_CE':loss=loss+.5*(parts['positive_sum']/max(1,totals['positive'])+parts['negative_sum']/max(1,totals['negative']))
            if not torch.isfinite(loss):raise RuntimeError('nonfinite loss')
            loss.backward();value+=float(loss.detach())
            for name in second:second[name]+=parts[name]
            if not torch.equal(out['logits'].permute(0,2,3,1)[~mask],inp['z0'].permute(0,2,3,1)[~mask]):
                raise RuntimeError('crop fallback changed')
            del inp,out,parts,loss
    if second!=totals:raise RuntimeError('expert utility changed between denominator/backprop passes')
    torch.nn.utils.clip_grad_norm_(gate.parameters(),float('inf'),error_if_nonfinite=True)
    if any(p.grad is not None for p in pair.parameters()):raise RuntimeError('expert gradient')
    optimizer.step()
    return value,totals


class Moments:
    def __init__(self):self.n=0;self.mean=None;self.m2=None
    def add(self,E):
        x=E.detach().double().cpu().permute(1,0,2,3).reshape(16,-1)
        n=x.shape[1];mean=x.mean(1);m2=((x-mean[:,None])**2).sum(1)
        if self.n:
            delta=mean-self.mean;total=self.n+n
            self.m2+=m2+delta.square()*self.n*n/total;self.mean+=delta*n/total
        else:self.mean,self.m2=mean,m2
        self.n+=n
    def result(self):
        if not self.n:raise RuntimeError('empty fit statistics')
        return dict(count=self.n,mean=self.mean.tolist(),std=(self.m2/self.n).clamp_min(0).sqrt().tolist())


def positions(length,patch,stride):
    if length<patch:raise ValueError('image smaller than patch')
    p=list(range(0,length-patch+1,stride))
    if p[-1]!=length-patch:p.append(length-patch)
    return p


def infer(pair,gates,optical,dsm,available,fixed_blend,patch=512,stride=256,batch=8,device='cuda',guard=lambda:None,diagnostics=None):
    """Original D21 uses uniform sum of window logits (no averaging before argmax)."""
    h,w=dsm.shape;coords=[(y,x) for y in positions(h,patch,stride) for x in positions(w,patch,stride)]
    names=list(gates)
    if 'R0' not in names:names.insert(0,'R0')
    scores={name:np.zeros((6,h,w),np.float32) for name in names}
    coverage=np.zeros((h,w),np.uint16)
    for gate in gates.values():
        if gate is not None:gate.eval()
    with torch.inference_mode():
        for start in range(0,len(coords),batch):
            cs=coords[start:start+batch]
            op=torch.from_numpy(np.stack([optical[y:y+patch,x:x+patch].transpose(2,0,1) for y,x in cs])).to(device)
            ds=torch.from_numpy(np.stack([dsm[y:y+patch,x:x+patch] for y,x in cs])).to(device)
            mask=torch.from_numpy(np.stack([available[y:y+patch,x:x+patch] for y,x in cs])).to(device)
            # Duplicate last window to keep expert computation at the selected batch shape.
            real=len(cs)
            if real<batch:
                op=torch.cat((op,op[-1:].expand(batch-real,-1,-1,-1)))
                ds=torch.cat((ds,ds[-1:].expand(batch-real,-1,-1)))
                mask=torch.cat((mask,mask[-1:].expand(batch-real,-1,-1)))
            inp=pair(op,ds)
            for name in names:
                gate=gates.get(name)
                if gate is None:output=fixed_blend(inp['z0'],inp['z1'],mask,name)
                else:
                    result=gate(inp['E'],inp['S'],inp['F'],inp['z0'],inp['z1'],mask);output=result['logits']
                    if diagnostics is not None:
                        values=result['g'][:real].detach().cpu()
                        row=diagnostics.setdefault(name,dict(count=0,sum=0.,histogram=[0]*10,scope='window_pixels_with_overlap'))
                        row['count']+=values.numel();row['sum']+=float(values.double().sum())
                        hist=torch.histc(values,bins=10,min=0,max=1).long().tolist()
                        row['histogram']=[a+b for a,b in zip(row['histogram'],hist)]
                    del result
                values=output[:real].cpu().numpy()
                for z,(y,x) in zip(values,cs):scores[name][:,y:y+patch,x:x+patch]+=z
                del output,values
            for y,x in cs:coverage[y:y+patch,x:x+patch]+=1
            del inp;guard()
    if not coverage.all():raise RuntimeError('uncovered image pixels')
    for name,score in scores.items():
        if not np.isfinite(score).all():raise RuntimeError('nonfinite stitched logits')
        score[:,~available]=scores['R0'][:,~available]
        if not np.array_equal(score[:,~available],scores['R0'][:,~available]):raise RuntimeError('post-stitch fallback changed')
    return scores


def count_result(gt,pred,reference,available):
    valid=(gt>=0)&(gt<6);g=gt[valid].astype(np.int64);p=pred[valid].astype(np.int64)
    if ((p<0)|(p>5)).any():raise RuntimeError('bad prediction')
    cm=np.bincount(6*g+p,minlength=36).reshape(6,6).astype(np.int64)
    correct=pred==gt;r_correct=reference==gt
    def risk(region):
        keep=valid&region
        return dict(valid=int(keep.sum()),harm=int((keep&r_correct&~correct).sum()),rescue=int((keep&~r_correct&correct).sum()))
    tp=np.diag(cm);support=cm.sum(1);fp=cm.sum(0)-tp;fn=support-tp;union=tp+fp+fn
    iou=np.divide(tp,union,out=np.full(6,np.nan),where=union>0)
    return dict(cm=cm.tolist(),support=support.tolist(),TP=tp.tolist(),FP=fp.tolist(),FN=fn.tolist(),
                mIoU_fg5=float(np.nanmean(iou[:5])) if np.isfinite(iou[:5]).any() else None,
                mIoU_6=float(np.nanmean(iou)) if np.isfinite(iou).any() else None,
                all=risk(np.ones_like(valid)),available=risk(available),missing=risk(~available),
                by_class={str(c):risk(gt==c) for c in range(6)})
