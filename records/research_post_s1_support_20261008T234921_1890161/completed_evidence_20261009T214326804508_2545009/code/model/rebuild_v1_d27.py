"""Frozen bilateral anchors with three dense residual experts and matched routers."""
import hashlib
import random
import torch
from torch import nn
from torch.nn import functional as F
from model.rebuild_v1_d26 import align_feature, valid_at, shift

ARMS=('S0','S1','G0','G1','L0','L1','C0','C1','L1-sh','C1-sh')

def permuted_condition(condition, rgb, dsm):
    # Input fingerprint gives a batch/order-independent key without labels/quality IDs.
    probe=torch.cat((rgb[...,::32,::32].flatten(1),dsm[...,::32,::32].flatten(1)),1).detach().float().cpu().numpy()
    result=[]
    for row,values in zip(condition,probe):
        seed=int.from_bytes(hashlib.sha256(values.tobytes()).digest()[:8],'little')
        perm=list(range(6));random.Random(seed).shuffle(perm)
        a,b=row[:6],row[6:12]
        a,b=a[perm],b[perm]
        result.append(torch.cat((a,b,(a-b).abs(),row[18:]),0))
    return torch.stack(result)

class D27Segmenter(nn.Module):
    def __init__(self,rgb_expert,dsm_expert,arm):
        super().__init__()
        if arm not in ARMS:raise ValueError(arm)
        self.arm=arm;self.rgb_expert=rgb_expert;self.dsm_expert=dsm_expert
        for expert in (rgb_expert,dsm_expert):expert.configure(False)
        self.project_rgb=nn.Conv2d(rgb_expert.channels,128,1)
        self.project_dsm=nn.Conv2d(dsm_expert.channels,128,1)
        self.expert_pool=nn.ModuleList([nn.Sequential(nn.Conv2d(256,128,3,padding=1),nn.GroupNorm(8,128),nn.GELU(),nn.Conv2d(128,6,1)) for _ in range(3)])
        self.router=nn.Sequential(nn.Conv2d(20,64,1),nn.GELU(),nn.Conv2d(64,18,1))
        self.register_buffer('fit_condition',torch.zeros(1,20,1,1))
        self.register_buffer('fit_condition_ready',torch.tensor(False))
        self.monitor=None
        for head in self.expert_pool:
            nn.init.zeros_(head[-1].weight);nn.init.zeros_(head[-1].bias)
        nn.init.zeros_(self.router[-1].weight);nn.init.zeros_(self.router[-1].bias)

    def forward(self,rgb,dsm,rgb_mask,dsm_mask,return_parts=False):
        if rgb_mask.shape!=dsm.shape or dsm_mask.shape!=dsm.shape or rgb_mask.dtype!=torch.bool or dsm_mask.dtype!=torch.bool:
            raise ValueError('aligned boolean masks required')
        rgb=rgb.masked_fill(~rgb_mask[:,None],0);dsm=dsm.masked_fill(~dsm_mask,0)
        with torch.no_grad():
            rlog,rf=self.rgb_expert(rgb,dsm);dlog,df=self.dsm_expert(rgb,dsm)
        shape=((rgb.shape[-2]+3)//4,(rgb.shape[-1]+3)//4)
        rm,dm=valid_at(rgb_mask,shape),valid_at(dsm_mask,shape)
        r=self.project_rgb(align_feature(rf,shape))*rm
        d=self.project_dsm(align_feature(df,shape))*dm
        rp=align_feature(rlog.detach().float().softmax(1),shape)*rm
        dp=align_feature(dlog.detach().float().softmax(1),shape)*dm
        condition=torch.cat((rp,dp,(rp-dp).abs(),rm.float(),dm.float()),1)
        if not bool(self.fit_condition_ready):
            if not self.training:raise RuntimeError('common first clean fit batch statistic required')
            if not (rgb_mask.all() and dsm_mask.all()):raise RuntimeError('initialize on clean complete fit batch')
            with torch.no_grad():
                self.fit_condition.copy_(condition.mean((0,2,3),keepdim=True));self.fit_condition_ready.fill_(True)
        route=condition
        if self.arm.startswith('S'):route=self.fit_condition.expand(condition.shape[0],-1,*shape)
        if self.arm=='C1-sh':route=permuted_condition(route,rgb,dsm)
        weights=self.router(route).reshape(rgb.shape[0],6,3,*shape)
        if self.arm.startswith(('S','G')):weights=weights.mean((-2,-1),keepdim=True).expand_as(weights)
        if not self.arm.startswith('C'):weights=weights.mean(1,keepdim=True).expand_as(weights)
        weights=weights.float().softmax(2)
        if self.arm=='L1-sh':weights=shift(weights)
        residuals=torch.stack([head(torch.cat((r,d),1)) for head in self.expert_pool],2).float()
        if self.monitor is not None:
            with torch.no_grad():
                valid_cells=(rm&dm)[:,0];n=int(valid_cells.sum())
                self.monitor['observed_cells']+=n
                for k in range(3):
                    self.monitor['weight_sums'][k]+=float((weights[:,:,k].mean(1)*valid_cells).sum())
                self.monitor['entropy_sum']+=float((-(weights*weights.clamp_min(1e-8).log()).sum(2).mean(1)*valid_cells).sum())
                votes=(align_feature(rlog.float(),shape)[:,:,None]+residuals).argmax(1)
                self.monitor['expert_disagreement_cells']+=int(((votes[:,0]!=votes[:,1])|(votes[:,0]!=votes[:,2]))[valid_cells].sum())
        increment=(weights*residuals).sum(2)*(rm&dm)
        increment=F.interpolate(increment,rgb.shape[-2:],mode='nearest')
        raw=rlog.float()+increment
        valid=rgb_mask|dsm_mask
        result=torch.where((rgb_mask&dsm_mask)[:,None],raw,torch.where(rgb_mask[:,None],rlog,dlog))
        result=result.masked_fill(~valid[:,None],0)
        if not return_parts:return result
        # Lower-resolution tensors avoid keeping three additional full-resolution graphs.
        return dict(logits=result,rgb=rlog,dsm=dlog,valid=valid,raw=raw,
                    residuals=residuals,route_weights=weights,anchor_low=align_feature(rlog.float(),shape),
                    route_valid=rm&dm)

    def reset_route_stats(self):
        self.monitor=dict(observed_cells=0,weight_sums=[0.,0.,0.],entropy_sum=0.,expert_disagreement_cells=0,
                          sampling='overlapping inference windows including repeated padded tail samples; descriptive only')

    def route_stats(self):
        row=dict(self.monitor);n=row['observed_cells']
        row.update(mean_weights=[v/n if n else None for v in row['weight_sums']],
                   mean_entropy=row['entropy_sum']/n if n else None,
                   expert_disagreement_rate=row['expert_disagreement_cells']/n if n else None)
        self.monitor=None
        return row
