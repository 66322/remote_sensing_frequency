"""Explicit A input / B all feature support / C local output intervention."""
import hashlib
import torch
from torch import nn
from torch.nn import functional as F
from model.rebuild_v1_d26 import valid_at
def digest(t):
    t=t.detach().cpu().contiguous()
    h=hashlib.sha256()
    h.update(str(tuple(t.shape)).encode());h.update(str(t.dtype).encode())
    h.update(t.numpy().tobytes())
    return h.hexdigest()
class CrossPaths(nn.Module):
    def __init__(self,base,path):
        super().__init__();self.base=base;self.arm='J0';self.learned_missing=True
        self.set_path(path);self.trace=None
    def set_path(self,path):
        if path not in [f'A{a}B{b}C{c}' for a in (0,1) for b in (0,1) for c in (0,1)]:raise ValueError('unlisted intervention')
        self.path=path;self.A=int(path[1]);self.B=int(path[3]);self.C=int(path[5]);self.trace=None
    def forward(self,rgb,dsm,rgb_mask,dsm_mask,return_parts=False):
        if rgb_mask.dtype!=torch.bool or dsm_mask.dtype!=torch.bool or rgb_mask.shape!=dsm.shape or dsm_mask.shape!=dsm.shape:raise ValueError('aligned boolean masks required')
        # Entire reported-missing modality retains the original safe graph.
        # This guard is per 512px window, not a claim about the whole scene.
        rg=rgb_mask.flatten(1).any(1)[:,None,None];dg=dsm_mask.flatten(1).any(1)[:,None,None]
        safe_window=rg&dg
        clear_r=rgb_mask if self.A else torch.where(safe_window,torch.ones_like(rgb_mask),rgb_mask)
        clear_d=dsm_mask if self.A else torch.where(safe_window,torch.ones_like(dsm_mask),dsm_mask)
        received_r,received_d=rgb,dsm
        rgb=rgb.masked_fill(~clear_r[:,None],0);dsm=dsm.masked_fill(~clear_d,0)
        br=rgb_mask if self.B else torch.where(safe_window,torch.ones_like(rgb_mask),rgb_mask)
        bd=dsm_mask if self.B else torch.where(safe_window,torch.ones_like(dsm_mask),dsm_mask)
        base=self.base;base.taps={'rgb':{},'dsm':{}}
        rlog,rf=base.rgb_expert(rgb,dsm);dlog,df=base.dsm_expert(rgb,dsm)
        shape=((rgb.shape[-2]+3)//4,(rgb.shape[-1]+3)//4)
        try:
            r=base.pyramid('rgb',rf,rgb,br,shape);d=base.pyramid('dsm',df,rgb,bd,shape)
        finally:base.taps={'rgb':{},'dsm':{}}
        both=valid_at(br,shape).bool()[:,0]&valid_at(bd,shape).bool()[:,0]
        # N2 has an additional center+donor mask; B controls it explicitly.
        if hasattr(base,'relation'):r,d=base.relation(r,d,dsm,both)
        raw=F.interpolate(base.fusion(torch.cat((r,d,r,d),1)),rgb.shape[-2:],mode='nearest')
        safe=torch.where(rgb_mask[:,None],rlog,dlog)
        hard=torch.where((rgb_mask&dsm_mask)[:,None],raw,safe)
        valid=rgb_mask|dsm_mask
        result=hard if self.C else torch.where((rg&dg)[:,None],raw,hard)
        result=result.masked_fill(~valid[:,None],0)
        if self.trace is None:
            self.trace=dict(path=self.path,trace_scope='first padded native512 batch only; not whole-scene activation hash',
                received_rgb=digest(received_r),received_dsm=digest(received_d),
                expert_rgb=digest(rgb),expert_dsm=digest(dsm),
                reported_rgb=digest(rgb_mask),reported_dsm=digest(dsm_mask),
                pyramid_rgb_support=digest(br),pyramid_dsm_support=digest(bd),
                relation_support=digest(both) if hasattr(base,'relation') else None,
                rgb_feature=digest(r),dsm_feature=digest(d),raw_logits=digest(raw),output_logits=digest(result),
                full_missing_safe_guard=True)
        parts=dict(logits=result,rgb=rlog,dsm=dlog,raw=raw,valid=valid)
        return parts if return_parts else result
