"""D27-matched two-view objective; independently controlled protect/recover."""
import itertools
import torch
from torch.nn import functional as F
from d27_data import Loader,Crops,PrefetchedBatches,training_batch,strata,safety
from d26_data import ce
VARIANTS=('S0','S1','P','R','PR_area','PR_pixel')

def recovery(logits,target,rgb,dsm,rm,dm,mode):
    valid=rm&dm&(target>=0)&(target<6)
    mask=valid&(rgb.detach().argmax(1)!=target)&(dsm.detach().argmax(1)==target)
    loss=F.cross_entropy(logits.float(),target,ignore_index=255,reduction='none')
    n=int(mask.sum());den=int(valid.sum())
    if mode=='PR_pixel':value=(loss*mask).sum()/mask.sum().clamp_min(1)
    else:
        values=[loss[mask&(target==c)].mean() for c in range(6) if (mask&(target==c)).any()]
        value=sum(values)/len(values) if values else logits.sum()*0
        if mode=='PR_area':value=value*(n/max(den,1))
    return value,dict(both_valid_pixels=den,recover_pixels=n,
                     recover_class_counts=[int((mask&(target==c)).sum()) for c in range(6)],
                     recover_fraction=n/max(den,1))

def objective(model,batch,diagnostics=False):
    variant=getattr(model,'loss_variant',model.arm)
    if variant not in VARIANTS:raise ValueError(variant)
    target=batch['gt'];full=torch.ones_like(target,dtype=torch.bool)
    result=[];counts={};logs={};component_losses={}
    for tag,rgb,ds,rm,dm in (('clean',batch['rgb'],batch['aux'],full,full),
                            ('aug',batch['rgb2'],batch['aux2'],batch['rm2'],batch['dm2'])):
        with torch.autocast(device_type=rgb.device.type,dtype=torch.bfloat16,enabled=rgb.device.type=='cuda'):
            parts=model(rgb,ds,rm,dm,return_parts=True)
        fused,n=ce(parts['logits'],target,rm|dm)
        chosen=strata(batch['treatment'],tag,target.device)
        small=F.interpolate(target[:,None].float(),parts['residuals'].shape[-2:],mode='nearest')[:,0].long()
        valid=parts['route_valid'][:,0]&(small<6);auxiliaries=[]
        for k in range(3):
            logits=parts['anchor_low']+parts['residuals'][:,:,k]
            aux,naux=ce(logits,small,valid&chosen[:,k,None,None]);auxiliaries.append(aux)
            counts[tag+'_expert%d_pixels'%k]=naux
        aux=sum(auxiliaries)/3
        # The same addition order preserves S0/S1 numeric and gradient equivalence.
        aux_weighted=.1*sum(auxiliaries)/3
        value=fused+aux_weighted
        protect,recover_original,ns=safety(parts['logits'],parts['rgb'],parts['dsm'],target,rm,dm)
        recover,detail=recovery(parts['logits'],target,parts['rgb'],parts['dsm'],rm,dm,variant)
        if variant in ('S1','R','P'):recover=recover_original
        wp=.1 if variant in ('S1','P','PR_area','PR_pixel') else 0.
        wr=.1 if variant in ('S1','R','PR_area','PR_pixel') else 0.
        if wp and wr:value=value+wp*protect+wr*recover
        elif wp:value=value+wp*protect
        elif wr:value=value+wr*recover
        counts.update({tag+'_'+k:v for k,v in ns.items()})
        counts[tag+'_both_valid_pixels']=detail['both_valid_pixels']
        counts[tag+'_fusion_pixels']=n
        weights=parts['route_weights'].detach()
        counts[tag+'_route_entropy_sum']=float(-(weights*weights.clamp_min(1e-8).log()).sum(2).mean())
        for k in range(3):counts[tag+'_route%d_sum'%k]=float(weights[:,:,k].mean())
        result.append(.5*value)
        if diagnostics:
            raw={'ce':fused,'aux':aux,'protect':protect,'recover':recover}
            weighted={'ce':fused,'aux':aux_weighted,'protect':wp*protect,'recover':wr*recover}
            logs[tag]=dict(raw={k:float(v.detach()) for k,v in raw.items()},
                           weighted={k:float(v.detach()) for k,v in weighted.items()},
                           weights=dict(protect=wp,recover=wr,aux=.1),
                           denominators=dict(fusion_pixels=n,protect_pixels=ns['protect_pixels'],**detail))
            for k,v in weighted.items():component_losses[k]=component_losses.get(k,0)+.5*v
    if diagnostics:return sum(result),counts,logs,component_losses
    return sum(result),counts

def gradient_components(model,components):
    params=[p for p in model.parameters() if p.requires_grad]
    gradients={}
    for name,value in components.items():
        gradients[name]=torch.autograd.grad(value,params,retain_graph=True,allow_unused=True)
    norms={k:float(torch.sqrt(sum((g.detach().double().square().sum() for g in gs if g is not None),torch.tensor(0.,device=params[0].device)))) for k,gs in gradients.items()}
    cosines={}
    for a,b in itertools.combinations(gradients,2):
        dot=sum((ga.detach().double().mul(gb.detach().double()).sum() for ga,gb in zip(gradients[a],gradients[b]) if ga is not None and gb is not None),torch.tensor(0.,device=params[0].device))
        den=norms[a]*norms[b];cosines[a+'__'+b]=float(dot)/den if den else None
    return dict(weighted_gradient_norms=norms,cosines=cosines,
                diagnostic_only=True,optimizer_gradients_unchanged=True)
