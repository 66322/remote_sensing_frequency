import random
import time
from pathlib import Path
import numpy as np
from . import common as c

def tile_paths(data,tile):
    if tile not in c.FIT:raise ValueError('outside frozen Fit12 whitelist')
    a,b=map(int,tile.split('_'));p=Path(data)
    return dict(rgb=p/'2_Ortho_RGB'/('top_potsdam_'+tile+'_RGB.tif'),
        dsm=p/'1_DSM/1_DSM'/('dsm_potsdam_%02d_%02d.tif'%(a,b)),
        full=p/'5_Labels_for_participants'/('top_potsdam_'+tile+'_label.tif'),
        nb=p/'5_Labels_for_participants_no_Boundary'/('top_potsdam_'+tile+'_label_noBoundary.tif'))

def decode_label(a):
    y=np.full(a.shape[:2],255,np.uint8);known=np.all(a==0,-1)
    for k,color in enumerate(c.COLORS):
        z=np.all(a==color,-1);y[z]=k;known|=z
    if not known.all():raise RuntimeError('unknown class colour; no silent remap')
    return y

def load_tile(data,tile,scale=None):
    from PIL import Image
    out={};ps=tile_paths(data,tile)
    for name,p in ps.items():
        with Image.open(p) as im:
            if name=='dsm':
                a=np.array(im,dtype=np.float32);nodata=getattr(im,'tag_v2',{}).get(42113)
                valid=np.isfinite(a)
                if nodata is not None:
                    try:valid &= a!=float(str(nodata).strip('\x00'))
                    except ValueError:raise RuntimeError('unrecognised DSM NoData metadata')
                if not valid.any():raise RuntimeError('DSM entirely invalid')
                median=np.median(a[valid]);a[~valid]=median
                # Translation invariant centering is not terrain-normalised DSM.
                a-=median;out['height_valid']=valid
                out['dsm']=a if scale is None else a/np.float32(scale)
            else:
                a=np.array(im.convert('RGB'));out[name]=a if name=='rgb' else decode_label(a)
    shape=out['rgb'].shape[:2]
    if any(v.shape[:2]!=shape for v in out.values()):raise RuntimeError('unaligned tile '+tile)
    if min(shape)<2048:raise RuntimeError('unexpected real tile size')
    for a in out.values():a.flags.writeable=False
    return out

def fit_normalization(data,tiles):
    samples=[];counts={}
    for tile in tiles:
        x=load_tile(data,tile)
        samples.append(x['dsm'][::16,::16].ravel())
        counts[tile]={n:np.bincount(x[n].ravel(),minlength=256).tolist() for n in ('full','nb')}
    q=np.quantile(np.concatenate(samples),[0.05,0.95]);scale=float(q[1]-q[0])
    if not np.isfinite(scale) or scale<=0:raise RuntimeError('invalid fit-only DSM scale')
    return dict(scale=scale,fit_tiles=list(tiles),quantiles=q.tolist(),
        method='per_tile_valid_median_center_then_fixed_fit_sampled_q95_minus_q05',
        nDSM=False,label_counts=counts)

def resident(contract):
    start=time.perf_counter();out={};size=0
    for tile in contract['folds']['train']:
        x=load_tile(contract['data'],tile,contract['normalization']['scale'])
        size+=sum(v.nbytes for v in x.values())
        if size>c.CONFIG['max_resident_tile_bytes']:raise RuntimeError('resident tile RAM cap exceeded')
        out[tile]=x
    return out,dict(tile_load_seconds=time.perf_counter()-start,resident_bytes=size)

class Crops:
    def __init__(self,data,tiles,length):self.data,self.tiles,self.length=data,tuple(tiles),length
    def __len__(self):return self.length
    def __getitem__(self,index):
        import torch
        rng=random.Random(c.key('V2-F0-crop',42,index));t=rng.choice(self.tiles);item=self.data[t]
        h,w=item['full'].shape;b=c.CONFIG['border'];s=c.CONFIG['crop']
        y=rng.randrange(b,h-b-s+1);x=rng.randrange(b,w-b-s+1)
        flips=[rng.randrange(2),rng.randrange(2)]
        def cut(a):
            v=a[y:y+s,x:x+s]
            if flips[0]:v=np.flip(v,0)
            if flips[1]:v=np.flip(v,1)
            return torch.from_numpy(np.ascontiguousarray(v))
        gt=cut(item['full'])
        return dict(rgb=cut(item['rgb']).permute(2,0,1),dsm=cut(item['dsm'])[None],
            valid=cut(item['height_valid'])[None],gt=gt,index=index,valid_count=int((gt<6).sum()))

def loader(data,tiles,workers,length):
    import torch
    kw=dict(dataset=Crops(data,tiles,length),batch_size=16,num_workers=workers,
        shuffle=False,pin_memory=True,drop_last=True)
    if workers:kw.update(persistent_workers=True,prefetch_factor=2,multiprocessing_context='fork')
    return torch.utils.data.DataLoader(**kw)

def exposure(step,p_rgb=0.5):
    rng=random.Random(c.key('quality-exposure',42,step));rows=[]
    for j in range(16):
        # Clean probability and damage/mask budgets are explicitly recorded.
        mode=0 if rng.random()<0.5 else (1 if rng.random()<p_rgb else 2)
        rows.append(dict(mode=mode,side=rng.choice([128,256]),y=rng.randrange(257),
            x=rng.randrange(257),factor=4))
    return rows

def replay(rows):
    order=list(range(len(rows)));random.Random(c.key('Q3-time-permutation',42)).shuffle(order)
    return [rows[i] for i in order],order

def damage(rgb,dsm,rows):
    import torch
    from torch.nn import functional as F
    a,b=rgb.clone(),dsm.clone();modes=[]
    # At most two batched low-resolution operations; no per-pixel GPU callbacks.
    lowa=F.interpolate(F.interpolate(a,scale_factor=.25,mode='area'),size=a.shape[-2:],mode='bilinear',align_corners=False)
    lowb=F.interpolate(F.interpolate(b,scale_factor=.25,mode='area'),size=b.shape[-2:],mode='bilinear',align_corners=False)
    for j,r in enumerate(rows):
        modes.append(r['mode']);s=r['side'];y=r['y'];x=r['x']
        if r['mode']==1:a[j,:,y:y+s,x:x+s]=lowa[j,:,y:y+s,x:x+s]
        elif r['mode']==2:b[j,:,y:y+s,x:x+s]=lowb[j,:,y:y+s,x:x+s]
    return a,b,torch.tensor(modes,device=rgb.device)

def condition(rgb,dsm,name,tile):
    """One physical intervention per tile, before windowing, shared across all arms."""
    import torch
    from torch.nn import functional as F
    if name=='clean':return rgb,dsm,None
    h,w=rgb.shape[:2];side=int(min(h,w)*c.CONFIG['evaluation_damage_side'])
    rng=random.Random(c.key('V2-eval-ROI',42,tile));border=c.CONFIG['border']
    y=rng.randrange(border,h-border-side+1);x=rng.randrange(border,w-border-side+1)
    a=rgb.copy() if name.startswith('rgb') else rgb
    b=dsm.copy() if name.startswith('dsm') else dsm
    arr=rgb[y:y+side,x:x+side] if name.startswith('rgb') else dsm[y:y+side,x:x+side,None]
    t=torch.from_numpy(np.ascontiguousarray(arr.transpose(2,0,1)))[None].float()
    if name.endswith('down4'):
        t=F.interpolate(F.interpolate(t,scale_factor=.25,mode='area'),size=(side,side),mode='bilinear',align_corners=False)
    elif name=='rgb_blur':
        sigma=c.CONFIG['blur_sigma_px'];axis=torch.arange(-6,7,dtype=torch.float32)
        k=torch.exp(-axis.square()/(2*sigma*sigma));k/=k.sum()
        t=F.conv2d(F.pad(t,(6,6,0,0),mode='replicate'),k[None,None,None,:].expand(3,1,1,-1),groups=3)
        t=F.conv2d(F.pad(t,(0,0,6,6),mode='replicate'),k[None,None,:,None].expand(3,1,-1,1),groups=3)
    elif name=='dsm_shift':
        dy,dx=c.CONFIG['dsm_shift_px']
        whole=torch.from_numpy(np.ascontiguousarray(dsm))[None,None]
        padded=F.pad(whole,(max(dx,0),max(-dx,0),max(dy,0),max(-dy,0)),mode='replicate')
        shifted=padded[:,:,max(-dy,0):max(-dy,0)+h,max(-dx,0):max(-dx,0)+w]
        t=shifted[:,:,y:y+side,x:x+side]
    else:raise ValueError(name)
    v=t[0].permute(1,2,0).numpy()
    if name.startswith('rgb'):a[y:y+side,x:x+side]=v.clip(0,255).round().astype(np.uint8)
    else:b[y:y+side,x:x+side]=v[:,:,0]
    return a,b,(y,x,side)

def condition_valid(valid,name,roi):
    if name!='dsm_shift':return valid
    y,x,s=roi;dy,dx=c.CONFIG['dsm_shift_px'];h,w=valid.shape
    padded=np.pad(valid,((max(dy,0),max(-dy,0)),(max(dx,0),max(-dx,0))),mode='edge')
    shifted=padded[max(-dy,0):max(-dy,0)+h,max(-dx,0):max(-dx,0)+w]
    out=valid.copy();out[y:y+s,x:x+s]=shifted[y:y+s,x:x+s];return out
