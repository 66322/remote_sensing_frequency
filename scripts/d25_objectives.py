"""Availability-partitioned CE and one-sided shared-gradient diagnostics."""
import contextlib
import torch
from d24_objectives import pixel_ce, ce, anchored_pair, verify_gradients

def partition_ce(clean_logits, aug_logits, gt, mask):
    clean,valid=pixel_ce(clean_logits,gt)
    aug,valid2=pixel_ce(aug_logits,gt)
    dc=valid.sum().clamp_min(1)
    da=valid2.sum().clamp_min(1)
    present=.5*(clean*valid).sum()/dc+.5*(aug*(valid2&mask)).sum()/da
    missing=.5*(aug*(valid2&~mask)).sum()/da
    return present,missing,{'present_pixels':int(valid.sum()+(valid2&mask).sum()),
                           'missing_pixels':int((valid2&~mask).sum())}

def objective(model, teachers, job, batch, plan, mixed=True):
    context=torch.autocast('cuda',dtype=torch.bfloat16) if mixed else contextlib.nullcontext()
    with context:
        clean=model(batch['rgb'],batch['aux'],torch.ones_like(batch['aux'],dtype=torch.bool),return_parts=True)
        aug=model(batch['rgb2'],batch['aux2'],batch['mask2'],return_parts=True)
    mask=torch.ones_like(batch['mask2']) if job['optical_only'] else batch['mask2']
    present,missing,counts=partition_ce(clean[0],aug[0],batch['gt'],mask)
    if job['pair']:
        with torch.no_grad():
            reference=teachers['R0'](batch['rgb'],batch['aux'])
        pair=anchored_pair(clean[0],reference,batch['gt'])
        weighted=plan['pair']['weight']*pair
        present=present+weighted
        counts.update({'Pair:enabled_steps':1,'Pair:penalty_sum':float(pair.detach()),
                       'Pair:weighted_loss_sum':float(weighted.detach())})
    else:
        counts.update({'Pair:enabled_steps':0,'Pair:weighted_loss_sum':0.})
    return present,missing,counts

def transform_shared(gp,gm,mode,eps=1e-12,report=True):
    if mode not in ('none','project','norm_sham'):
        raise ValueError('unknown gradient mode')
    # Sum reductions in FP32 without materializing one extra giant concatenation.
    zero=gp[0].new_zeros(())
    dot=sum((a*b).sum() for a,b in zip(gp,gm))
    np2=sum(a.square().sum() for a in gp)
    nm2=sum(b.square().sum() for b in gm)
    coefficient=torch.where((dot<0)&(np2>eps),dot/(np2+eps),zero)
    projected=[b-coefficient*a for a,b in zip(gp,gm)]
    projected_norm=sum(x.square().sum() for x in projected).sqrt()
    scale=torch.where(nm2>0,projected_norm/nm2.sqrt().clamp_min(eps),zero)
    if mode=='project':result=projected
    elif mode=='norm_sham':result=[b*scale for b in gm]
    else:result=gm
    stats=None if not report else {'cosine':float((dot/(np2*nm2).sqrt().clamp_min(eps)).detach()),
           'present_norm':float(np2.sqrt().detach()),'missing_norm':float(nm2.sqrt().detach()),
           'conflict':int(bool((dot<0)&(np2>eps)&(nm2>0))),
           'projected_missing_norm':float(projected_norm.detach()),
           'applied_missing_norm':float(sum(x.square().sum() for x in result).sqrt().detach()),
           'norm_sham_scale':float(scale.detach())}
    return result,stats

def backward(model,present,missing,mode,diagnose=False):
    if mode=='none' and not diagnose:
        (present+missing).backward()
        return None
    named=[(n,p) for n,p in model.named_parameters() if p.requires_grad]
    params=[p for _,p in named]
    a=torch.autograd.grad(present,params,allow_unused=True,retain_graph=True)
    b=torch.autograd.grad(missing,params,allow_unused=True)
    shared=model.shared_parameter_names()
    indices=[i for i,(n,p) in enumerate(named) if n in shared]
    if not indices:raise RuntimeError('no shared trainable parameters')
    gp=[torch.zeros_like(params[i]) if a[i] is None else a[i].float() for i in indices]
    gm=[torch.zeros_like(params[i]) if b[i] is None else b[i].float() for i in indices]
    changed,stats=transform_shared(gp,gm,mode,report=diagnose)
    mapped=dict(zip(indices,changed))
    for i,p in enumerate(params):
        if a[i] is None and b[i] is None:
            p.grad=None
            continue
        left=torch.zeros_like(p) if a[i] is None else a[i].float()
        right=mapped[i] if i in mapped else (torch.zeros_like(p) if b[i] is None else b[i].float())
        p.grad=(left+right).to(p.dtype)
    if not diagnose:return None
    stats.update(shared_parameters=[named[i][0] for i in indices],
                 shared_numel=sum(params[i].numel() for i in indices))
    for prefix in ('decoder.','decoder_optical.','detail.','rgb.'):
        stats[prefix+'gradient_nonzero']=any(p.grad is not None and bool(p.grad.abs().sum()>0)
                                              for n,p in named if n.startswith(prefix))
    return stats
