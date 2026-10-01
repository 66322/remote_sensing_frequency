"""Matched CE, anchored task ordering and fixed-teacher spatial KD."""
import contextlib
import torch
from torch.nn import functional as F


def pixel_ce(logits, label):
    valid = (label >= 0) & (label < 6)
    target = label.clamp(0, 5)
    values = -F.log_softmax(logits.float(), 1).gather(1, target[:, None])[:, 0]
    return values, valid


def ce(logits, label, balanced=False):
    values, valid = pixel_ce(logits, label)
    if not bool(valid.any()):
        return logits.float().sum() * 0
    if not balanced:
        return values[valid].mean()
    return torch.stack([values[valid & (label == c)].mean() for c in range(6)
                        if bool((valid & (label == c)).any())]).mean()


def crop_ce(logits, label):
    values, valid = pixel_ce(logits, label)
    return (values * valid).sum((1, 2)) / valid.sum((1, 2)).clamp_min(1)


def anchored_pair(logits, reference_logits, label):
    return (crop_ce(logits, label) - crop_ce(reference_logits.detach(), label)).clamp_min(0).mean()


def rescue_mask(teacher, reference, label):
    return ((label >= 0) & (label < 6) & (teacher.argmax(1) == label)
            & (reference.argmax(1) != label))


def shuffled_mask(selected, valid):
    result = torch.zeros_like(selected)
    h, w = selected.shape[-2:]
    for i in range(len(selected)):
        indices = torch.nonzero(valid[i].flatten(), as_tuple=False)[:, 0]
        if len(indices):
            shift = ((h // 2) * w + w // 3) % len(indices)
            result[i].view(-1)[indices] = torch.roll(selected[i].flatten()[indices], shift)
    if not torch.equal(result.sum((1, 2)), selected.sum((1, 2))):
        raise RuntimeError('shuffled region count changed')
    return result


def kd(student, teacher, selected, temperature=2.):
    if not bool(selected.any()):
        return student.float().sum() * 0
    logp = F.log_softmax(student.float() / temperature, 1)
    target = F.softmax(teacher.detach().float() / temperature, 1)
    values = (target * (target.clamp_min(1e-12).log() - logp)).sum(1) * temperature ** 2
    return values[selected].mean()


def step_objective(model, teachers, job, tensors, plan, mixed=True):
    gt=tensors['gt']
    clean_mask=torch.ones_like(tensors['aux'],dtype=torch.bool)
    context=torch.autocast('cuda',dtype=torch.bfloat16) if mixed else contextlib.nullcontext()
    with context:
        clean=model(tensors['rgb'],tensors['aux'],clean_mask,return_parts=True)
        aug=model(tensors['rgb2'],tensors['aux2'],tensors['mask2'],return_parts=True)
    balanced=job['objective']=='classbalanced_CE'
    loss=.5*(ce(clean[0],gt,balanced)+ce(aug[0],gt,balanced))
    counts={}
    if job['route']=='A':
        with torch.no_grad():reference=teachers['R0'](tensors['rgb'],tensors['aux'])
        active='Pair' in job['objective']
        ordering=anchored_pair(clean[0] if active else clean[0].detach(),reference,gt)
        counts['Pair:penalty_sum']=float(ordering.detach())
        counts['Pair:steps']=1
        if active:loss=loss+plan['pair']['weight']*ordering
    elif job['route']=='C':
        distill=[]
        for view,result,rgb,aux in (('clean',clean,tensors['rgb'],tensors['aux']),
                                   ('aug',aug,tensors['rgb2'],tensors['aux2'])):
            with torch.no_grad():
                teacher=teachers['M0'](rgb,aux)
                reference=teachers['R0'](rgb,aux)
            valid=(gt>=0)&(gt<6)
            selected=rescue_mask(teacher,reference,gt)
            if job['id']=='C1':selected=valid
            elif job['id']=='C3':selected=shuffled_mask(selected,valid)
            count=int(selected.sum())
            counts['KD:'+view+':selected_pixels']=count
            counts['KD:'+view+':valid_pixels']=int(valid.sum())
            counts['KD:'+view+':empty_views']=int(count==0)
            value=kd(result[0] if job['id']!='C0' else result[0].detach(),teacher,selected,plan['KD']['temperature'])
            counts['KD:'+view+':loss_sum']=float(value.detach())
            distill.append(value)
        if job['id']!='C0':loss=loss+plan['KD']['weight']*.5*(distill[0]+distill[1])
    return loss,clean[2],clean[3],counts


def verify_gradients(model, teachers):
    trainable = {name: p for name, p in model.named_parameters() if p.requires_grad}
    unexpected = [name for name, p in model.named_parameters() if not p.requires_grad and p.grad is not None]
    head = [p for name, p in trainable.items() if not name.startswith('encoder.')]
    encoder = [p for name, p in trainable.items() if name.startswith('encoder.')]
    active = lambda rows: any(p.grad is not None and bool(p.grad.detach().abs().sum() > 0) for p in rows)
    if unexpected or not active(head) or (encoder and not active(encoder)):
        raise RuntimeError('gradient range mismatch: ' + str(unexpected))
    if any(p.grad is not None or p.requires_grad for teacher in teachers for p in teacher.parameters()):
        raise RuntimeError('teacher gradient/trainability detected')
    return dict(trainable_parameters=sum(p.numel() for p in trainable.values()),
                encoder_gradient_nonzero=active(encoder), head_gradient_nonzero=active(head),
                frozen_gradients_absent=True, teacher_gradients_absent=True)
