"""Matched crop streams, native halo shifts, and globally normalized losses."""
import math,random
import numpy as np
import torch
from torch.nn import functional as F
import d23_engine as e
from d26_data import views,ce
from d24_data import Loader,PrefetchedBatches,Crops as OriginalCrops
from model.rebuild_v1_post_d30 import alignment,distillation


def materialize_shift(cache,spec,dx=0,dy=0):
    tile=cache[spec['tile']];h,w=tile['dsm'].shape;p=spec['patch']
    size=max(1,min(round(p/spec['scale']),h,w));halo=math.ceil(4*size/p)+1
    if h<size+2*halo or w<size+2*halo:raise RuntimeError('crop lacks native DSM halo')
    y=min(max(int(spec['fy']*(h-size+1)),halo),h-size-halo)
    x=min(max(int(spec['fx']*(w-size+1)),halo),w-size-halo)
    sx,sy=round(dx*size/p),round(dy*size/p)
    roi=dict(optical=tile['optical'][y:y+size,x:x+size],dsm=tile['dsm'][y-sy:y-sy+size,x-sx:x-sx+size],full_gt=tile['full_gt'][y:y+size,x:x+size])
    local=dict(spec,fy=0.,fx=0.,scale=p/size)
    op,ds,gt,_=e.materialize({spec['tile']:roi},local)
    return op,ds,gt


class Crops(OriginalCrops):
    def __init__(self,tiles,ids,augmentation,plan,start=0,job=None):
        super().__init__(tiles,ids,augmentation,'',start,8000);self.plan=plan;self.job=job
    def __getitem__(self,index):
        step,i=self.start+index//16,index%16
        spec=e.sample_spec(self.ids,e.key(42,'fit',step)*16+i,self.augmentation,512);spec['treatment']='clean'
        op,ds,gt=materialize_shift(self.cache,spec)
        dx=dy=0
        if self.job.get('geometry_aug',False):
            rng=random.Random(e.key(42,'post_D30_geometry',step,i))
            dx,dy=rng.choices([(0,0),(-2,0),(2,0),(-4,0),(4,0),(0,-2),(0,2),(0,-4),(0,4)],weights=[.5]+[.0625]*8)[0]
        if dx or dy:_,shifted,_=materialize_shift(self.cache,spec,dx,dy)
        else:shifted=ds
        op2,ds2,rm,dm,kind=views(op,shifted,self.plan,step,i)
        return dict(rgb=op,aux=ds,gt=gt,rgb2=op2[0],aux2=ds2[0],rm2=rm[0],dm2=dm[0],treatment=kind+';geom='+str((dx,dy)))


def objective(model,batch):
    target=batch['gt'];full=torch.ones_like(target,dtype=torch.bool);counts={};terms=[]
    pairs=(('clean',batch['rgb'],batch['aux'],full,full),('aug',batch['rgb2'],batch['aux2'],batch['rm2'],batch['dm2']))
    if model.learned_missing:
        with torch.no_grad():teacher=model(batch['rgb'],batch['aux'],full,full,return_parts=True)['raw'].detach()
        mode=model.job.get('distill','none');directions=model.job.get('directions',['rgb','dsm'])
        for tag,rgb,ds,rm,dm in pairs:
            # Each student sees ONLY its available modality, including its encoder context.
            for name in ('rgb','dsm'):
                mr=rm if name=='rgb' else torch.zeros_like(rm);md=dm if name=='dsm' else torch.zeros_like(dm)
                with torch.autocast(device_type=rgb.device.type,dtype=torch.bfloat16,enabled=rgb.is_cuda):student=model.single(rgb,ds,mr|md,name)
                valid=mr|md;loss,n=ce(student,target,valid);value=.25*loss
                if mode!='none' and name in directions:value=value+.025*distillation(student,teacher,target,valid,mode)
                terms.append(value);counts[tag+'_'+name+'_pixels']=n
                counts[tag+'_'+name+'_teacher_correct']=int(((teacher.argmax(1)==target)&valid&(target<6)).sum())
        return sum(terms),counts
    for tag,rgb,ds,rm,dm in pairs:
        with torch.autocast(device_type=rgb.device.type,dtype=torch.bfloat16,enabled=rgb.is_cuda):parts=model(rgb,ds,rm,dm,return_parts=True)
        main,n=ce(parts['logits'],target,rm|dm);ar,nr=ce(parts['aux_rgb'],target,rm);ad,nd=ce(parts['aux_dsm'],target,dm)
        value=.5*main+.025*(ar+ad)
        if model.job.get('align','none')!='none':value=value+.5*model.job['align_weight']*alignment(parts,model.job)
        terms.append(value);counts[tag+'_fusion_pixels']=n;counts[tag+'_rgb_aux_pixels']=nr;counts[tag+'_dsm_aux_pixels']=nd
        # Diagnostic second moments of structurally shared/private features (not proof of disentanglement).
        for name in ('rgb','dsm'):
            feature=parts['features_'+name].detach().float()
            counts[tag+'_'+name+'_shared_variance']=float(feature[:,:64].var(unbiased=False))
            counts[tag+'_'+name+'_private_variance']=float(feature[:,64:].var(unbiased=False))
    return sum(terms),counts


def geometry(ds,kind):
    """Whole-tile, inverse nearest sampling; clip outer support, no oracle mask."""
    h,w=ds.shape[-2:];y=torch.arange(h);x=torch.arange(w)
    dy=torch.zeros((h,w),dtype=torch.long);dx=dy.clone()
    if kind=='geom_dx8':dx.fill_(8)
    elif kind=='geom_dy8':dy.fill_(8)
    elif kind=='geom_warp8':
        dx=(8*torch.sin(2*math.pi*y[:,None]/512)).round().long().expand(h,w)
        dy=(8*torch.sin(2*math.pi*x[None,:]/512)).round().long().expand(h,w)
    else:raise ValueError(kind)
    yy=(y[:,None]-dy).clamp(0,h-1);xx=(x[None,:]-dx).clamp(0,w-1)
    return ds[:,yy,xx]


def treatment(op,ds,kind,seed):
    # Inherited D27/D30 diagnostic: present-but-bad DSM is NOT known missing.
    if kind in ('dsm_present_zero','dsm_present_shift_half'):
        mask=torch.ones_like(ds,dtype=torch.bool)
        bad=torch.zeros_like(ds) if kind=='dsm_present_zero' else torch.roll(ds,(ds.shape[-2]//2,ds.shape[-1]//2),(-2,-1))
        return op.clone(),bad,mask,mask.clone()
    from d26_data import treatment as original
    result=[]
    for part in kind.split('+'):
        if part.startswith('geom_'):ds=geometry(ds,part)
        else:result.append(part)
    return original(op,ds,'+'.join(result) or 'clean',seed)
