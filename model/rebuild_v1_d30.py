"""Checkpoint-only forced mixtures; no extra parameters or trainable branches."""
import torch
from torch.nn import functional as F
from model.rebuild_v1_d27 import D27Segmenter
MODES=('original','uniform','expert0','expert1','expert2')
class ForcedMixture(D27Segmenter):
    def __init__(self,rgb,dsm,arm,mode):
        super().__init__(rgb,dsm,arm)
        if mode not in MODES:raise ValueError(mode)
        self.mode=mode
    def forward(self,rgb,dsm,rm,dm,return_parts=False):
        if self.mode=='original':return super().forward(rgb,dsm,rm,dm,return_parts)
        monitor=self.monitor;self.monitor=None
        try:parts=super().forward(rgb,dsm,rm,dm,True)
        finally:self.monitor=monitor
        w=torch.full_like(parts['route_weights'],1/3) if self.mode=='uniform' else torch.zeros_like(parts['route_weights'])
        if self.mode.startswith('expert'):w[:,:,int(self.mode[-1])]=1
        valid_low=parts['route_valid']
        increment=(w*parts['residuals']).sum(2)*valid_low
        raw=parts['rgb'].float()+F.interpolate(increment,rgb.shape[-2:],mode='nearest')
        result=torch.where((rm&dm)[:,None],raw,torch.where(rm[:,None],parts['rgb'],parts['dsm']))
        result=result.masked_fill(~(rm|dm)[:,None],0)
        parts.update(logits=result,raw=raw,route_weights=w)
        if monitor is not None:
            cells=valid_low[:,0];n=int(cells.sum());monitor['observed_cells']+=n
            for k in range(3):monitor['weight_sums'][k]+=float((w[:,:,k].mean(1)*cells).sum())
            monitor['entropy_sum']+=float((-(w*w.clamp_min(1e-8).log()).sum(2).mean(1)*cells).sum())
            votes=(parts['anchor_low'][:,:,None]+parts['residuals']).argmax(1)
            monitor['expert_disagreement_cells']+=int(((votes[:,0]!=votes[:,1])|(votes[:,0]!=votes[:,2]))[cells].sum())
        return parts if return_parts else result

