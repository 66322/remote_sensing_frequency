"""Deterministic native-pixel objectives and matched weight controls."""
import numpy as np
import torch
from torch.nn import functional as F

def true_value(values,target):
    out=values.new_zeros(target.shape)
    for k in range(values.shape[1]): out=torch.where(target==k,values[:,k],out)
    return out

def stratified(q,entropy,target,bins,keys,mode):
    """Same q multiset per image/class/boundary bin. No gradients through assignment."""
    if mode not in ['shuffle','entropy']: raise ValueError(mode)
    out=q.detach().clone(); small=0
    with torch.no_grad():
        for i in range(len(q)):
            for cls in range(6):
                for b in range(3):
                    index=torch.nonzero(((target[i]==cls)&(bins[i]==b)).flatten(),as_tuple=True)[0]
                    n=len(index)
                    if n<2: small+=n; continue
                    values=q[i].flatten()[index]
                    if mode=='shuffle':
                        rng=np.random.Generator(np.random.PCG64(int(keys[i])+cls*3+b))
                        order=torch.from_numpy(rng.permutation(n)).to(q.device)
                        replacement=values[order]
                    else:
                        order=torch.argsort(entropy[i].flatten()[index],stable=True)
                        replacement=values.clone(); replacement[order]=torch.sort(values,stable=True).values
                    out[i].flatten()[index]=replacement
    return out,small

def objective(logits,target,arm,teacher=None,bins=None,keys=None):
    logp=F.log_softmax(logits.float(),dim=1); valid=target!=255
    if not bool(valid.any()) or bool((valid&((target<0)|(target>5))).any()): raise ValueError('invalid training labels')
    ce=-true_value(logp,target); p=logp.exp(); small=0
    if arm=='D0': return ce[valid].mean(),dict(weight_mean=1.,weight_min=1.,weight_max=1.,effective_fraction=1.)
    with torch.no_grad():
        source=p.detach() if arm=='DSelf' else F.softmax(teacher.float(),dim=1)
        if source.requires_grad: raise RuntimeError('teacher must be stopped')
        q=1-true_value(source,target)
        entropy=-(source*source.clamp_min(1e-30).log()).sum(1)
        if arm in ['DShuffle','DEntropy']:
            q,small=stratified(q,entropy,target,bins,keys,'shuffle' if arm=='DShuffle' else 'entropy')
        w=1+2*q; w=w/w[valid].mean()
    if arm=='DMix':
        # Exact CE of .9 teacher + .1 student, normalized by its stopped mean
        # gradient coefficient; removes the extra global effective-LR confound.
        py=true_value(p,target); ty=true_value(source,target)
        mix=(.9*ty+.1*py).clamp_min(1e-30)
        raw=.5*ce-.5*mix.log()
        coefficient=(.5+.5*.1*py.detach()/mix.detach())
        scale=coefficient[valid].mean().detach()
        loss=raw[valid].mean()/scale
        w=coefficient/scale
        extra=dict(raw_gradient_coefficient_mean=float(scale),normalizer_stopped=True)
    else:
        loss=(ce*w)[valid].mean(); extra={}
    v=w[valid]
    return loss,dict(weight_mean=float(v.mean()),weight_min=float(v.min()),weight_max=float(v.max()),
        effective_fraction=float(v.sum().square()/(v.square().sum()*v.numel())),small_stratum_pixels=small,**extra)

def crop_mask(rgb,dsm,gt,family,seed):
    """512 crop masks: pixel/block/height-gradient/exact class-matched control.

    The crop-sized matched mask uses per-class quotas with block priorities;
    it is explicitly distinct from the legacy full-tile matched geometry.
    """
    from scipy.ndimage import sobel
    rng=np.random.Generator(np.random.PCG64(seed)); h,w=gt.shape; area=h*w//4
    if h%32 or w%32: raise ValueError('mask requires multiple of 32')
    if family=='pixel':
        mask=np.zeros(h*w,bool);mask[rng.choice(h*w,area,replace=False)]=True;return mask.reshape(h,w)
    gradient=np.hypot(sobel(dsm,0),sobel(dsm,1))
    ny,nx=h//32,w//32
    scores=gradient.reshape(ny,32,nx,32).mean((1,3)).flatten()
    if family=='random': chosen=rng.choice(ny*nx,ny*nx//4,replace=False)
    else:
        sd=max(float(scores.std()),1e-12); weights=np.exp(2*np.clip((scores-scores.mean())/sd,-3,3)); weights/=weights.sum()
        chosen=rng.choice(ny*nx,ny*nx//4,replace=False,p=weights)
    blocks=np.zeros(ny*nx,bool);blocks[chosen]=True
    mask=np.repeat(np.repeat(blocks.reshape(ny,nx),32,0),32,1)
    if family!='matched': return mask
    # A class-matched random mask shares exact six-class/ignore quotas with
    # this gradient draw, while random block priorities remove height targeting.
    priority=np.repeat(np.repeat(rng.permutation(ny*nx).reshape(ny,nx),32,0),32,1).astype(np.float64)
    priority+=rng.random((h,w))*.5
    out=np.zeros_like(mask)
    for cls in list(range(6))+[255]:
        index=np.flatnonzero(gt.flatten()==cls); n=int(((gt==cls)&mask).sum())
        if n: out.flat[index[np.argsort(priority.flat[index],kind='stable')[:n]]]=True
    if int(out.sum())!=area: raise RuntimeError('crop mask area mismatch')
    return out

def teacher_view(batch,clean=False):
    """CPU preprocessing can overlap previous GPU work through crop threads."""
    from phase3_m2_common import FAMILIES,key
    x=batch['rgb'].clone(); conditions=[]
    for i,s in enumerate(batch['weight_key']):
        seed=int(s); choice=0 if clean else seed%3; conditions.append(['clean','down2','down4'][choice])
        if not choice: continue
        factor=2 if choice==1 else 4
        image=x[i:i+1]
        low=F.interpolate(image,size=(512//factor,512//factor),mode='bilinear',align_corners=False,antialias=True)
        damaged=F.interpolate(low,size=(512,512),mode='bilinear',align_corners=False)
        mask=crop_mask(x[i].numpy(),batch['dsm'][i].numpy(),batch['gt'][i].numpy(),FAMILIES[(seed//3)%4],key(seed,'crop-mask'))
        x[i,:,mask]=damaged[0,:,mask]
    return x,conditions
