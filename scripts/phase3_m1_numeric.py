"""Bounded stripe arithmetic; sufficient integer joints without pixel exports."""
import numpy as np
from phase3_m1_common import *

def primary(score,tile):
    out={}
    for scope in ('full','noboundary'):
        gt=DATA[tile][scope+'_gt']; total=np.zeros((6,6),np.int64)
        for y in range(0,gt.shape[0],128):
            sl=slice(y,y+128); total+=cm(gt[sl],score[:,sl].argmax(0),np.ones(gt[sl].shape,bool))
        out[scope]=total.tolist()
    return out

def analyze(r,d,tile,mask=None,border=0,availability='both',healthy_override=None):
    from scipy.special import softmax
    from scipy.ndimage import maximum_filter
    shape=r.shape[1:]
    if d.shape!=r.shape: raise ValueError('unmatched logits')
    if mask is None:
        mask=np.zeros(shape,bool) if availability=='both' else np.ones(shape,bool)
        healthy=~mask
    else:
        healthy=healthy_override if healthy_override is not None else ~maximum_filter(mask,size=17,mode='constant',cval=0).astype(bool)
    sums={s:{roi:{n:np.zeros((6,6,6),np.int64) for n in ('dsm','logit_mix','probability_mix')}
             for roi in ('all','healthy','damaged')} for s in ('full','noboundary')}
    for y in range(0,shape[0],128):
        stop=min(y+128,shape[0]); sl=slice(y,stop)
        rr=r[:,sl].astype(np.float64); dd=d[:,sl].astype(np.float64)
        if not np.isfinite(rr).all() or not np.isfinite(dd).all(): raise RuntimeError('nonfinite logits')
        pr=rr.argmax(0).astype(np.uint8); pd=dd.argmax(0).astype(np.uint8)
        if availability=='rgb_missing': mixed=prob=pd
        elif availability=='dsm_missing': mixed=prob=pr
        else:
            mixed=(.9*rr+.1*dd).argmax(0).astype(np.uint8)
            prob=(.9*softmax(rr,axis=0)+.1*softmax(dd,axis=0)).argmax(0).astype(np.uint8)
        valid=np.ones(pr.shape,bool)
        if border:
            yy=np.arange(y,stop)[:,None]; xx=np.arange(shape[1])[None,:]
            valid &= (yy>=border)&(yy<shape[0]-border)&(xx>=border)&(xx<shape[1]-border)
        rois={'all':valid,'healthy':valid&healthy[sl],'damaged':valid&mask[sl]}
        for scope in sums:
            gt=DATA[tile][scope+'_gt'][sl]
            for roi,support in rois.items():
                for name,p in [('dsm',pd),('logit_mix',mixed),('probability_mix',prob)]:
                    sums[scope][roi][name]+=joint(gt,pr,p,support)
    out={}
    for scope,rois in sums.items():
        out[scope]={}
        for roi,systems in rois.items():
            result={}
            for n,j in systems.items():
                if not np.array_equal(j.sum((1,2)),next(iter(systems.values())).sum((1,2))): raise RuntimeError('joint support mismatch')
                result[n]=dict(joint=j.tolist(),cm=j.sum(1).tolist(),rgb_cm=j.sum(2).tolist(),flow=flow(j))
            out[scope][roi]=result
    return out

def summary(base):
    base=Path(base); prim={}
    for f in sorted((base/'primary').glob('*.json')):
        z=read(f); prim[z['job']]=z
    decision=gate(prim)
    contrasts={}
    for a,b in [('M21','M11'),('M20','M10'),('M11','M10'),('M21','M20'),('M01','M00'),('M10','M00'),('C21','M21')]:
        for seed in (42,17):
            ka,kb=f'{a}_{seed}',f'{b}_{seed}'
            if any(k not in prim or prim[k].get('failed') for k in (ka,kb)): continue
            vals={}
            for tile in VAL+['pooled']:
                matrices=[]
                for k in (ka,kb):
                    matrices.append(sum(np.asarray(prim[k]['tiles'][t]['noboundary'],np.int64) for t in VAL)
                                    if tile=='pooled' else np.asarray(prim[k]['tiles'][tile]['noboundary'],np.int64))
                scores=[metric(m) for m in matrices]
                vals[tile]=None if None in scores else scores[0]-scores[1]
            contrasts[f'{a}-{b}/{seed}']=vals
    completed=[];failed=[]
    for f in (base/'jobs').glob('*/complete.json'): completed.append(read(f))
    for f in (base/'jobs').glob('*/failure.json'): failed.append(dict(job=f.parent.name,**read(f)))
    qualified=read(base/'result_verification.json').get('M00_42_causal_reuse_qualified') if (base/'result_verification.json').exists() else None
    if qualified is False:
        for name in list(contrasts):
            if name.endswith('/42') and '-M00/' in name: del contrasts[name]
    result=dict(binding=binding(base),primary=prim,contrasts_pp=contrasts,legacy_anchor_causal_reuse_qualified=qualified,amplitude_gate=decision,
       completed_jobs=completed,failed_jobs=failed,completed_new_updates=sum(x.get('optimizer_updates',0) for x in completed),
       source_only_rgb_seed=42,sealed_splits_unread=True,scope='Potsdam reused Val2; two DSM seeds, one fixed RGB seed',observed_at=now())
    write(base/'summary.json',result)
    return result

