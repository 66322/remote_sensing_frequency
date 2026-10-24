"""Same D26 crops/views; paired protection and unique-information recovery."""
import torch
from torch.nn import functional as F
from d26_data import Loader,Crops,PrefetchedBatches,ce
from d26_data import treatment as original_treatment

def treatment(op,ds,kind,seed):
    if kind=='dsm_present_zero':
        mask=torch.ones_like(ds,dtype=torch.bool)
        return op.clone(),torch.zeros_like(ds),mask,mask.clone()
    if kind=='dsm_present_shift_half':
        mask=torch.ones_like(ds,dtype=torch.bool)
        return op.clone(),torch.roll(ds,(ds.shape[-2]//2,ds.shape[-1]//2),(-2,-1)),mask,mask.clone()
    return original_treatment(op,ds,kind,seed)

def region_mean(loss,mask):
    count=mask.sum()
    return (loss*mask).sum()/count.clamp_min(1),int(count)

def balanced_ce(logits,target,mask):
    loss=F.cross_entropy(logits.float(),target,ignore_index=255,reduction='none')
    values=[]
    for c in range(6):
        region=mask&(target==c)
        if region.any():values.append(loss[region].mean())
    return sum(values)/len(values) if values else logits.sum()*0

def safety(logits,rgb,dsm,target,rm,dm):
    valid=rm&dm&(target>=0)&(target<6)
    rc=rgb.detach().argmax(1)==target;dc=dsm.detach().argmax(1)==target
    loss=F.cross_entropy(logits.float(),target,ignore_index=255,reduction='none')
    rloss=F.cross_entropy(rgb.detach().float(),target,ignore_index=255,reduction='none')
    protect,n=region_mean((loss-rloss).relu(),valid&rc)
    recover=balanced_ce(logits,target,valid&~rc&dc)
    return protect,recover,dict(protect_pixels=n,recover_pixels=int((valid&~rc&dc).sum()))

def strata(kinds,tag,device):
    if tag=='clean':return torch.tensor([[True,False,False]]*len(kinds),device=device)
    rows=[]
    for kind in kinds:
        # Quality family ID is used only for common expert auxiliary supervision.
        parts=kind.split('+');rq=any(x.startswith('rgb_') and 'missing' not in x and 'local_' not in x for x in parts)
        dq=any(x.startswith('aux_') for x in parts)
        rows.append([not rq and not dq,dq,rq])
    return torch.tensor(rows,device=device)

def training_batch(batch, device='cuda'):
    """Move tensors while retaining treatment metadata required by the loss."""
    kinds = batch['treatment']
    if len(kinds) != batch['rgb'].shape[0] or not all(isinstance(k, str) for k in kinds):
        raise ValueError('treatment metadata must match the physical batch')
    moved = {k: v.to(device=device, non_blocking=True)
             for k, v in batch.items() if torch.is_tensor(v)}
    moved['treatment'] = list(kinds)
    return moved

def objective(model,batch):
    target=batch['gt'];full=torch.ones_like(target,dtype=torch.bool);result=[];counts={}
    for tag,rgb,ds,rm,dm in (('clean',batch['rgb'],batch['aux'],full,full),('aug',batch['rgb2'],batch['aux2'],batch['rm2'],batch['dm2'])):
        with torch.autocast(device_type=rgb.device.type,dtype=torch.bfloat16,enabled=rgb.device.type=='cuda'):
            parts=model(rgb,ds,rm,dm,return_parts=True)
        fused,n=ce(parts['logits'],target,rm|dm);value=fused
        chosen=strata(batch['treatment'],tag,target.device)
        small=F.interpolate(target[:,None].float(),parts['residuals'].shape[-2:],mode='nearest')[:,0].long()
        valid=parts['route_valid'][:,0]&(small<6)
        auxiliaries=[]
        for k in range(3):
            logits=parts['anchor_low']+parts['residuals'][:,:,k]
            aux,naux=ce(logits,small,valid&chosen[:,k,None,None]);auxiliaries.append(aux)
            counts[tag+'_expert%d_pixels'%k]=naux
        value=value+.1*sum(auxiliaries)/3
        if model.arm not in ('S0','G0','L0','C0'):
            protect,recover,ns=safety(parts['logits'],parts['rgb'],parts['dsm'],target,rm,dm)
            value=value+.1*protect+.1*recover
            counts.update({tag+'_'+k:v for k,v in ns.items()})
        counts[tag+'_fusion_pixels']=n
        weights=parts['route_weights'].detach()
        counts[tag+'_route_entropy_sum']=float(-(weights*weights.clamp_min(1e-8).log()).sum(2).mean())
        for k in range(3):counts[tag+'_route%d_sum'%k]=float(weights[:,:,k].mean())
        result.append(.5*value)
    return sum(result),counts
