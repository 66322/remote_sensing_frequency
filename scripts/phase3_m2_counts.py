"""Bounded full-case CPU counters. Memfd handles in, small sufficient counts out."""
import numpy as np
from scipy.special import softmax
import phase3_m2_common as c

def histogram(gt,r,d,keep):
    use=keep&(gt<6)
    return np.bincount((gt[use].astype(np.int64)*6+r[use])*6+d[use],minlength=216).reshape(6,6,6)

def matrix(gt,p,keep):
    use=keep&(gt<6)
    return np.bincount(gt[use].astype(np.int64)*6+p[use],minlength=36).reshape(6,6)

def calibration(gt,prob,keep):
    valid=keep&(gt<6); pred=prob.argmax(0); conf=prob.max(0); index=np.minimum((conf[valid]*15).astype(int),14)
    count=np.bincount(index,minlength=15); correct=np.bincount(index,weights=(pred[valid]==gt[valid]),minlength=15)
    confidence=np.bincount(index,weights=conf[valid],minlength=15)
    nll=0.
    for cls in range(6):nll-=float(np.log(prob[cls][valid&(gt==cls)].clip(1e-30)).sum())
    return dict(count=count,correct=correct.astype(np.int64),confidence=confidence,nll_sum=nll)

def add(a,b):
    if isinstance(a,dict):
        for k in a:a[k]=add(a[k],b[k])
        return a
    return a+b

def lists(value):
    if isinstance(value,dict):return {k:lists(v) for k,v in value.items()}
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    return value

def analyze_arrays(r,d,item,mask,healthy,border=0):
    h,w=item['full'].shape
    result={}
    for scope in ['nb','full']:
        result[scope]={region:dict(joint=np.zeros((6,6,6),np.int64),fusion_joint=np.zeros((6,6,6),np.int64),
            cms=np.zeros((7,6,6),np.int64),logit_cm=np.zeros((6,6),np.int64)) for region in ['all','damaged','healthy']}
    result['aux']=dict(fulltile_nb=np.zeros((3,6,6),np.int64),fulltile_full=np.zeros((3,6,6),np.int64),
        boundary=np.zeros((3,6,6),np.int64),interior=np.zeros((3,6,6),np.int64))
    result['margin_counts']=np.zeros((7,5),np.int64)
    result['calibration']={s:dict(count=np.zeros(15,np.int64),correct=np.zeros(15,np.int64),confidence=np.zeros(15),nll_sum=0.) for s in ['rgb','dsm','fusion']}
    for y in range(0,h,128):
        sl=slice(y,min(y+128,h)); rr=np.asarray(r[:,sl],np.float64);dd=np.asarray(d[:,sl],np.float64)
        if not np.isfinite(rr).all() or not np.isfinite(dd).all():raise ValueError('nonfinite logits')
        rp,dp=softmax(rr,axis=0),softmax(dd,axis=0);rpred=rp.argmax(0);dpred=dp.argmax(0)
        yy=np.arange(y,min(y+128,h))[:,None];xx=np.arange(w)[None,:]
        central=(yy>=512)&(yy<h-512)&(xx>=max(512,border))&(xx<w-512)
        if h<=1024 or w<=1024:raise ValueError('central-512 requires tile >1024')
        validborder=np.broadcast_to(xx>=border,(len(yy),w))
        regions=dict(all=central,damaged=central&mask[sl],healthy=central&healthy[sl])
        preds=[((1-a)*rp+a*dp).argmax(0) for a in c.ALPHAS]
        fpred=preds[2];lpred=(.9*rr+.1*dd).argmax(0)
        for scope in ['nb','full']:
            gt=item[scope][sl]
            for region,support in regions.items():
                row=result[scope][region];row['joint']+=histogram(gt,rpred,dpred,support)
                row['fusion_joint']+=histogram(gt,rpred,fpred,support)
                row['logit_cm']+=matrix(gt,lpred,support)
                for i,pred in enumerate(preds):row['cms'][i]+=matrix(gt,pred,support)
        for name,gt,support in [('fulltile_nb',item['nb'][sl],validborder),('fulltile_full',item['full'][sl],validborder),
                ('boundary',item['full'][sl],central&(item['bin'][sl]==0)),('interior',item['full'][sl],central&(item['bin'][sl]>0))]:
            for i,pred in enumerate([rpred,dpred,fpred]):result['aux'][name][i]+=matrix(gt,pred,support)
        gt=item['nb'][sl]; trueprob=np.zeros(gt.shape)
        for cls in range(6):trueprob[gt==cls]=rp[cls][gt==cls]
        margin=rp.max(0)-trueprob
        wrong=central&(gt<5)&(rpred!=gt)
        for i,a in enumerate(c.ALPHAS):
            possible=wrong&(margin<=(a/(1-a) if a<1 else float('inf')))
            result['margin_counts'][i]+=np.bincount(gt[possible],minlength=6)[:5]
        for name,prob in [('rgb',rp),('dsm',dp),('fusion',.9*rp+.1*dp)]:
            result['calibration'][name]=add(result['calibration'][name],calibration(gt,prob,central))
    return result

def validate_counts(row):
    """Independent identities, not a replay of the pixel counting loop."""
    for scope in ['nb','full']:
        regions=row[scope]
        for region,z in regions.items():
            j=np.asarray(z['joint'],np.int64);f=np.asarray(z['fusion_joint'],np.int64);cms=np.asarray(z['cms'],np.int64)
            if (j<0).any() or (f<0).any() or (cms<0).any():raise ValueError('negative counts')
            if not np.array_equal(j.sum(2),f.sum(2)):raise ValueError('RGB joint marginal')
            if not np.array_equal(j.sum(2),cms[0]):raise ValueError('alpha0 RGB fallback')
            if not np.array_equal(j.sum(1),cms[-1]):raise ValueError('alpha1 DSM fallback')
            if not np.array_equal(f.sum(1),cms[2]):raise ValueError('primary fusion marginal')
            for cm in cms:
                if not np.array_equal(cm.sum(1),j.sum((1,2))):raise ValueError('GT support differs by alpha')
        if int(np.asarray(regions['damaged']['joint']).sum())+int(np.asarray(regions['healthy']['joint']).sum())>int(np.asarray(regions['all']['joint']).sum()):raise ValueError('ROI containment')
    return True

def count_task(task):
    from phase24_ipc import Packet
    packets=[]
    try:
        for name in ['r','d','mask']:packets.append(Packet.receive(task[name]))
        r,d,m=packets
        result=analyze_arrays(r.arrays['score'],d.arrays['score'],c.DATA[task['tile']],m.arrays['mask'],m.arrays['healthy'],task.get('border',0))
        validate_counts(result)
        return dict(kind='count',metadata=task['metadata'],counts=lists(result))
    finally:
        for packet in packets:packet.close()

def primary_task(task):
    from phase24_ipc import Packet
    packet=Packet.receive(task['packet'])
    try:
        score=packet.arrays['score']; item=c.DATA[task['metadata']['tile']];h,w=item['full'].shape
        out={scope:np.zeros((6,6),np.int64) for scope in ['nb','full']}
        for y in range(512,h-512,128):
            sl=slice(y,min(y+128,h-512));pred=score[:,sl,512:w-512].argmax(0)
            for scope in out:out[scope]+=matrix(item[scope][sl,512:w-512],pred,np.ones(pred.shape,bool))
        return dict(kind='trajectory',metadata=task['metadata'],counts=lists(out))
    finally:packet.close()

def mask_design_task(task):
    from structured_v0_masks import generate
    tile,realization=task['tile'],task['realization'];item=c.DATA[tile]
    masks,metadata=generate(dict(dsm=item['dsm'],full_gt=item['full'],noboundary_gt=item['nb']),tile,realization)
    return dict(kind='mask_design',tile=tile,realization=realization,metadata=metadata)

def reconstruct_masks(tile,realization,item,metadata):
    from structured_v0_masks import raster,rng_for,canonical
    shape=item['full'].shape;out={}
    for family in c.FAMILIES:
        if family=='pixel':
            a=np.zeros(shape,bool);a.flat[rng_for(tile,realization,'pixel').choice(a.size,a.size//4,replace=False)]=True
        else:a=raster(shape,np.asarray(metadata[family]['primitives'],np.int64))
        if canonical(a)!=metadata[family]['canonical_sha256'] or int(a.sum())!=a.size//4:raise RuntimeError('frozen mask reconstruction differs')
        out[family]=a
    return out

def mask_task(task):
    from pathlib import Path
    from phase24_ipc import Packet
    from scipy.ndimage import maximum_filter
    tile,realization=task['tile'],task['realization'];item=c.DATA[tile]
    metadata=c.read(Path(task['base'])/'mask_design'/f'{tile}_{realization}.json')['metadata']
    masks=reconstruct_masks(tile,realization,item,metadata)
    packets={}
    try:
        for family,mask in masks.items():
            healthy=~maximum_filter(mask,size=17,mode='constant',cval=0).astype(bool)
            packets[family]=Packet.create(dict(mask=mask,healthy=healthy))
        return dict(kind='masks',tile=tile,realization=realization,packets={n:p.descriptor() for n,p in packets.items()},metadata=metadata)
    finally:
        for p in packets.values():p.close()
