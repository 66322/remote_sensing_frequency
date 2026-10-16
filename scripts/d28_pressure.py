"""Frozen label-free pressure inputs and integer-count pooling. No model/GT input."""
import hashlib
import numpy as np
import torch
from torch.nn import functional as F

def key(tile):
    return int.from_bytes(hashlib.sha256(('203103:'+tile).encode()).digest()[:8],'little')

def masks(shape,tile):
    h,w=shape; quota=h*w//4
    blocks=[(y,x) for y in range(0,h,16) for x in range(0,w,16)]
    order=np.random.default_rng(key(tile)).permutation(len(blocks))
    result=np.zeros((2,h,w),bool); slot=0; remaining=quota
    if quota==0:raise ValueError('tile too small')
    for index in order:
        y,x=blocks[int(index)];yy,xx=np.meshgrid(np.arange(y,min(h,y+16)),np.arange(x,min(w,x+16)),indexing='ij');yy,xx=yy.ravel(),xx.ravel();offset=0
        while offset<len(yy) and slot<2:
            n=min(remaining,len(yy)-offset);result[slot,yy[offset:offset+n],xx[offset:offset+n]]=True;remaining-=n;offset+=n
            if remaining==0:slot+=1;remaining=quota
        if slot==2:break
    assert all(int(m.sum())==quota for m in result) and not (result[0]&result[1]).any()
    metadata=dict(seed=203103,key=key(tile),shape=[h,w],quota=quota,block_size=16,
                  block_order=order.tolist(),sha256=[hashlib.sha256(m.tobytes()).hexdigest() for m in result],
                  intersection_pixels=0,bias_sign=1 if key(tile)%2 else -1)
    return result,metadata

def blur(value,k):
    tensor=torch.from_numpy(np.ascontiguousarray(value))
    t=tensor.permute(2,0,1)[None] if value.ndim==3 else tensor[None,None]
    out=F.avg_pool2d(F.pad(t,(k//2,)*4,mode='reflect'),k,stride=1)[0]
    return out.permute(1,2,0).numpy() if value.ndim==3 else out[0].numpy()

def apply(item,pool,recipe,level,pair,tile,cache=None):
    op,ds=item['optical'],item['dsm'];rm,dm=pool[pair[0]],pool[pair[1]]
    token=(recipe,level)
    if cache is not None and token in cache:ro,dd=cache[token]
    elif recipe=='P1':
        k=5 if level=='mild' else 9;ro,dd=blur(op,k),blur(ds,k)
    elif recipe=='P2':
        factor,bias=(.75,.05) if level=='mild' else (.5,.10)
        mean=op.mean((0,1),keepdims=True);ro=mean+factor*(op-mean)
        dd=np.clip(ds+(1 if key(tile)%2 else -1)*bias,0,1)
    else:raise ValueError(recipe)
    if cache is not None:cache[token]=(ro,dd)
    return dict(item,optical=np.where(rm[...,None],ro,op).astype(np.float32),
                dsm=np.where(dm,dd,ds).astype(np.float32))

def cases():
    return [('clean',None,None,None)]+[(f'{r}_{l}_{a}{b}',r,l,(a,b))
        for r in ('P1','P2') for l in ('mild','strong') for a,b in ((0,0),(0,1),(1,0),(1,1))]

def regions(pool,pair):
    r,d=(np.zeros_like(pool[0]),)*2 if pair is None else (pool[pair[0]],pool[pair[1]])
    return dict(valid=np.ones_like(r),untouched=~(r|d),only_rgb_damaged=r&~d,
                only_dsm_damaged=d&~r,both_damaged=r&d)

def pool_cm(rows):
    # Equal case weights within each regime cancel from IoU; sum raw counts.
    return np.sum([np.asarray(r,np.int64) for r in rows],axis=0,dtype=np.int64)

def terminal(state):
    expected={'S0','S1','G0','G1','L0','L1','C0','C1','L1-sh','C1-sh'}
    return (state.get('status') in ('COMPLETE','COMPLETE_WITH_TECHNICAL_FAILURES')
            and set(state.get('jobs',{}))==expected
            and all(r.get('status') in ('COMPLETE','TECHNICAL_FAILURE','TIMEOUT') for r in state['jobs'].values()))
