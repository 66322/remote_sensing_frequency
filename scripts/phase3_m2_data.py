"""Fit12-only headers, frozen folds, resident inputs, deterministic paired crops."""
import hashlib
import json
import random
from pathlib import Path
import numpy as np
import phase3_m2_common as c

COLORS=((255,255,255),(0,0,255),(0,255,255),(0,255,0),(255,255,0),(255,0,0))

def paths(root,tile):
    if tile not in c.FIT: raise ValueError('outside explicit Fit12 whitelist')
    data=Path(c.read(Path(root)/'configs/rebuild_v1/r05_quality_plus_dropout_16k.json')['data_root']).resolve()
    data.relative_to(Path('/home/jovyan/zzx'))
    a,b=map(int,tile.split('_'))
    return dict(rgb=data/'2_Ortho_RGB'/f'top_potsdam_{tile}_RGB.tif',height=data/'1_DSM/1_DSM'/f'dsm_potsdam_{a:02d}_{b:02d}.tif',
        full=data/'5_Labels_for_participants'/f'top_potsdam_{tile}_label.tif',
        nb=data/'5_Labels_for_participants_no_Boundary'/f'top_potsdam_{tile}_label_noBoundary.tif')

def header(path):
    from PIL import Image
    with Image.open(path) as im:
        w,h=im.size; tags=getattr(im,'tag_v2',{})
        matrix=tags.get(34264); tie=tags.get(33922); scale=tags.get(33550); crs=tags.get(34735)
        corners=None
        if matrix and len(matrix)==16:
            corners=[(matrix[0]*x+matrix[1]*y+matrix[3],matrix[4]*x+matrix[5]*y+matrix[7]) for x,y in [(0,0),(w,0),(0,h),(w,h)]]
        elif tie and scale:
            corners=[(tie[3]+(x-tie[0])*scale[0],tie[4]-(y-tie[1])*scale[1]) for x,y in [(0,0),(w,h)]]
        bounds=None if corners is None else [min(x[0] for x in corners),min(x[1] for x in corners),max(x[0] for x in corners),max(x[1] for x in corners)]
        return dict(shape=[h,w],bounds=bounds,crs=list(crs) if crs else None)

def freeze_folds(root):
    meta={t:header(paths(root,t)['rgb']) for t in c.FIT}
    # Even a partial metadata fallback may not ignore a known overlap.
    for i,t in enumerate(c.FIT):
        a=meta[t]
        for u in c.FIT[i+1:]:
            b=meta[u]
            if a['bounds'] is not None and b['bounds'] is not None and a['crs'] is not None and a['crs']==b['crs']:
                x,z=a['bounds'],b['bounds']
                if min(x[2],z[2])-max(x[0],z[0])>1e-5 and min(x[3],z[3])-max(x[1],z[1])>1e-5:
                    raise RuntimeError('overlapping inputs; stop fold freeze: '+t+','+u)
    has=all(x['bounds'] is not None and x['crs'] is not None for x in meta.values())
    if has:
        if len({tuple(x['crs']) for x in meta.values()})!=1: raise RuntimeError('different CRS; explicit transform required')
        for i,t in enumerate(c.FIT):
            a=meta[t]['bounds']
            for u in c.FIT[i+1:]:
                b=meta[u]['bounds']
                if min(a[2],b[2])-max(a[0],b[0])>1e-5 and min(a[3],b[3])-max(a[1],b[1])>1e-5:
                    raise RuntimeError('overlapping inputs; stop fold freeze: '+t+','+u)
        centers={t:((r['bounds'][0]+r['bounds'][2])/2,(r['bounds'][1]+r['bounds'][3])/2) for t,r in meta.items()}
        spans=[max(p[i] for p in centers.values())-min(p[i] for p in centers.values()) for i in [0,1]]
        axis=0 if spans[0]>=spans[1] else 1
        order=sorted(c.FIT,key=lambda t:(centers[t][axis],tuple(map(int,t.split('_')))))
        method='geospatial_centroid_axis_'+str(axis)
    else:
        order=sorted(c.FIT,key=lambda t:tuple(map(int,t.split('_')))); method='natural_tile_id_fallback_not_geographic'
    folds={}
    for i in range(3):
        evaluation=order[4*i:4*i+4]; train=[t for t in order if t not in evaluation]
        folds['F'+str(i)]=dict(evaluation=evaluation,train=train,inner_pairs=[train[j:j+2] for j in range(0,8,2)])
    return dict(method=method,order=order,headers=meta,folds=folds,labels_used=False,metadata_scope='Fit12 RGB headers only')

def labels(array,nb=False):
    gt=np.full(array.shape[:2],255,np.uint8); recognized=np.all(array==0,-1) if nb else np.zeros(gt.shape,bool)
    for i,color in enumerate(COLORS):
        use=np.all(array==color,-1); gt[use]=i; recognized|=use
    if not recognized.all(): raise RuntimeError('unknown label color')
    return gt

def boundary_bins(gt):
    from scipy.ndimage import distance_transform_edt
    edge=np.zeros(gt.shape,bool)
    d=(gt[1:]!=gt[:-1])&(gt[1:]<6)&(gt[:-1]<6); edge[1:]|=d; edge[:-1]|=d
    d=(gt[:,1:]!=gt[:,:-1])&(gt[:,1:]<6)&(gt[:,:-1]<6); edge[:,1:]|=d; edge[:,:-1]|=d
    dist=distance_transform_edt(~edge)
    return np.where(dist<=4,0,np.where(dist<=16,1,2)).astype(np.uint8)

def prepare(base):
    from PIL import Image
    from concurrent.futures import ThreadPoolExecutor
    base=Path(base); p=c.read(base/'plan.json'); pf=c.resources(); c.DATA.clear()
    # Metadata is frozen before any label pixels are read.
    if c.read(base/'folds.json')!=freeze_folds(p['root']): raise RuntimeError('headers/folds changed')
    entries=[(t,n,f) for t in c.FIT for n,f in paths(p['root'],t).items()]
    def fingerprint(z):
        before=z[2].stat();digest=c.sha(z[2]);after=z[2].stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise RuntimeError('input changed while hashing')
        return dict(tile=z[0],field=z[1],path=str(z[2]),size=after.st_size,mtime_ns=after.st_mtime_ns,sha256=digest)
    with ThreadPoolExecutor(max_workers=min(8,pf['effective_cores'])) as pool:
        hashed=list(pool.map(fingerprint,entries))
    bypath={row['path']:row for row in hashed}
    index={}; stats={}
    for tile in c.FIT:
        item={}
        for n,path in paths(p['root'],tile).items():
            expected=bypath[str(path)];before=path.stat()
            if (before.st_size,before.st_mtime_ns)!=(expected['size'],expected['mtime_ns']):raise RuntimeError('input changed before read')
            with Image.open(path) as im: a=np.array(im if n=='height' else im.convert('RGB'))
            after=path.stat()
            if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise RuntimeError('input changed during read')
            item[n]=a.astype(np.float32)/255 if n=='rgb' else a.astype(np.float32) if n=='height' else labels(a,n=='nb')
        h=item.pop('height')
        if not np.isfinite(h).all(): raise RuntimeError('nonfinite height')
        qs=np.quantile(h,[.05,.5,.95],method='linear'); span=float(qs[2]-qs[0])
        if span<=0: raise RuntimeError('zero robust height span')
        stats[tile]=dict(q05=float(qs[0]),median=float(qs[1]),q95=float(qs[2]),span=span)
        item['dsm']=np.float32(.5)+(h-np.float32(qs[1]))/np.float32(span)
        item['height']=h; item['bin']=boundary_bins(item['full'])
        if any(a.shape[:2]!=h.shape for a in item.values()): raise RuntimeError('unaligned tile')
        for a in item.values(): a.flags.writeable=False
        c.DATA[tile]=item; index[tile]={n:dict(shape=list(a.shape),dtype=str(a.dtype),bytes=a.nbytes) for n,a in item.items()}
        c.write(base/'preparation_progress.json',dict(tile=tile,done=len(c.DATA),total=12,observed_at=c.now()))
        print('M2_INPUT',tile,len(c.DATA),'/12',flush=True)
    pf=c.resources(); resident=sum(a.nbytes for x in c.DATA.values() for a in x.values())
    # 21 DSM logits + clean RGB + bounded 2 in-flight RGB variants + 32 stripe counters.
    maximum=max(x['dsm'].size for x in c.DATA.values())
    evaluation_reserve=maximum*6*4*30+pf['count_workers']*256*max(x['dsm'].shape[1] for x in c.DATA.values())*6*8*5
    if pf['available_bytes']<evaluation_reserve+8*1024**3: raise RuntimeError('RAM insufficient for bounded evaluation; no disk logit fallback')
    pf.update(resident_bytes=resident,evaluation_reserve_bytes=evaluation_reserve,max_live_rgb_cases=2)
    c.write(base/'input_index.json',dict(files=hashed,arrays=index,normalization=stats))
    c.write(base/'resource_profile.json',pf)
    c.write(base/'prepared.json',dict(binding=c.binding(base),input_index_sha256=c.sha(base/'input_index.json'),observed_at=c.now()))
    return pf

class Crops:
    def __init__(self,job,folds,updates=32000): self.job,self.folds,self.updates=job,folds,updates
    def __len__(self): return self.updates*16
    def __getitem__(self,index):
        import torch
        job=self.job; step,i=divmod(index,16); seed=job['seed']
        stream=job['id'] if job['role']=='rgb_oof_teacher' else job['fold']
        rng=random.Random(c.key(seed,'M2-crop',stream,step,i))
        tile=rng.choice(job['train']); item=c.DATA[tile]; h,w=item['dsm'].shape
        y,x=rng.randrange(h-511),rng.randrange(w-511); fh,fv=rng.random()<.5,rng.random()<.5
        spec=dict(tile=tile,y=y,x=x,flip_h=fh,flip_v=fv)
        def crop(a):
            a=a[y:y+512,x:x+512]
            if fh:a=np.flip(a,1)
            if fv:a=np.flip(a,0)
            return np.ascontiguousarray(a)
        gt=crop(item['full']); token=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()+gt.tobytes()).hexdigest()
        inner=next(j for j,pair in enumerate(self.folds['folds'][job['fold']]['inner_pairs']) if tile in pair) if job['role']=='dsm_student' else -1
        spec_key=c.key(seed,job['fold'],'M2-weight',tile,y,x,fh,fv)
        # Stable across arms/repeated crops, independent from crop sampling and shuffle keys.
        result=dict(rgb=torch.from_numpy(crop(item['rgb']).transpose(2,0,1).copy()),
            dsm=torch.from_numpy(crop(item['dsm']).copy()),gt=torch.from_numpy(gt.astype(np.int64)),
            bins=torch.from_numpy(crop(item['bin']).copy()),inner=inner,weight_key=str(spec_key),token=token,
            shuffle_key=str(c.key(seed,job['fold'],'M2-shuffle',tile,y,x,fh,fv)),tile=tile)
        if job['arm'] not in ['D0','DSelf']:
            from phase3_m2_loss import teacher_view
            view,conditions=teacher_view({n:([v] if isinstance(v,str) else v[None]) for n,v in result.items()
                if n in ['rgb','dsm','gt','weight_key']},clean=job['arm']=='DClean')
            result['teacher_rgb']=view[0]; result['teacher_condition']=conditions[0]
        return result
