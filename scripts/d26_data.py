"""Matched keyed crops and independently sampled bilateral quality/missingness."""
import random
import torch
import d23_engine as e
from d24_data import Loader,PrefetchedBatches,Crops as OriginalCrops

def region(h,w,shape):
    if shape=='q1':return slice(h//4,h//4+h//2),slice(w//4,w//4+w//2)
    if shape=='stripe_eighth':return slice(h//4,3*h//8),slice(None)
    if shape=='center_quarter':return slice(3*h//8,5*h//8),slice(None)
    raise ValueError(shape)

def treatment(op,ds,kind,seed):
    op,ds=op.clone(),ds.clone()
    rm,dm=torch.ones_like(ds,dtype=torch.bool),torch.ones_like(ds,dtype=torch.bool)
    for part in kind.split('+'):
        h,w=ds.shape[-2:]
        if part in ('rgb_missing','dsm_missing'):
            (rm if part=='rgb_missing' else dm).zero_()
        elif part.startswith(('rgb_local_','dsm_local_')):
            modality,_,shape=part.split('_',2);y,x=region(h,w,shape)
            (rm if modality=='rgb' else dm)[:,y,x]=False
        elif part=='complementary_halves':rm[:,:,:w//2]=False;dm[:,:,w//2:]=False
        elif part=='both_center_missing':
            y,x=region(h,w,'center_quarter');rm[:,y,x]=False;dm[:,y,x]=False
        else:op,ds,_=e.treatment(op,ds,part,seed)
    return op.masked_fill(~rm[:,None],0),ds.masked_fill(~dm,0),rm,dm

def views(op,ds,plan,step,index):
    cfg=plan['augmentation'];values=[]
    for name in ('rgb','dsm'):
        rng=random.Random(e.key(42,'D26_quality',name,step,index))
        values.append(rng.choice(cfg[name]) if rng.random()<cfg[name+'_probability'] else 'clean')
    rng=random.Random(e.key(42,'D26_availability',step,index))
    available=rng.choices(list(cfg['availability']),weights=list(cfg['availability'].values()))[0]
    if available=='full':available='clean'
    elif available.endswith('_local'):available+='_'+rng.choice(cfg['local_shapes'])
    kind='+'.join(values+[available])
    return (*treatment(op[None],ds[None],kind,e.key(42,'D26_noise',step,index)),kind)

class Crops(OriginalCrops):
    def __init__(self,tiles,ids,augmentation,plan,start=0):
        super().__init__(tiles,ids,augmentation,'',start,8000);self.plan=plan
    def __getitem__(self,index):
        step,i=self.start+index//16,index%16
        spec=e.sample_spec(self.ids,e.key(42,'fit',step)*16+i,self.augmentation,512);spec['treatment']='clean'
        op,ds,gt,_=e.materialize(self.cache,spec)
        op2,ds2,rm,dm,kind=views(op,ds,self.plan,step,i)
        return dict(rgb=op,aux=ds,gt=gt,rgb2=op2[0],aux2=ds2[0],rm2=rm[0],dm2=dm[0],treatment=kind)

def ce(logits,target,valid):
    keep=valid & (target>=0) & (target<6)
    losses=torch.nn.functional.cross_entropy(logits.float(),target,ignore_index=255,reduction='none')
    count=keep.sum()
    return (losses*keep).sum()/count.clamp_min(1),int(count)

def objective(model,batch):
    target=batch['gt'];full=torch.ones_like(target,dtype=torch.bool)
    result=[];counts={}
    # Sequential full physical batches are two views of one update, no accumulation.
    for tag,rgb,ds,rm,dm in (('clean',batch['rgb'],batch['aux'],full,full),('aug',batch['rgb2'],batch['aux2'],batch['rm2'],batch['dm2'])):
        with torch.autocast(device_type=rgb.device.type,dtype=torch.bfloat16,enabled=rgb.device.type=='cuda'):
            parts=model(rgb,ds,rm,dm,return_parts=True)
        fused,n=ce(parts['logits'],target,rm|dm);value=.5*fused;counts[tag+'_fusion_pixels']=n
        if model.arm=='J0':
            r,nr=ce(parts['rgb'],target,rm);d,nd=ce(parts['dsm'],target,dm)
            # .5 views * .5 additional mean(RGB CE, DSM CE).
            value=value+.125*(r+d)
            counts[tag+'_rgb_pixels']=nr;counts[tag+'_dsm_pixels']=nd
        result.append(value)
    return sum(result),counts
