"""Native missing-support residual; same S1-0 base and one expert pass."""
import contextlib
import hashlib
import torch
from torch import nn
from torch.nn import functional as F
from model.rebuild_v1_post_ab_n1 import N1Segmenter
from model.rebuild_v1_d26 import valid_at
def state_digest(model,exclude='residual.'):
    h=hashlib.sha256()
    for n,v in model.state_dict().items():
        if not n.startswith(exclude):
            h.update(n.encode());h.update(str(v.dtype).encode());h.update(str(tuple(v.shape)).encode())
            h.update(v.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()
def shuffle_context(x,mask):
    """A label-free bijection in BOTH observed and unobserved strata."""
    support=valid_at(mask,x.shape[-2:])[:,0].detach().cpu().flatten(1)
    result=[];moved=total=0
    for sample in range(len(x)):
        perm=torch.arange(support.shape[1])
        for value in (False,True):
            ids=torch.nonzero(support[sample]==value,as_tuple=False).flatten()
            if len(ids)>1:
                # Fixed seed42 offset with no per-call/global RNG consumption.
                offset=1+42%(len(ids)-1);perm[ids]=torch.roll(ids,offset)
                moved+=int((perm[ids]!=ids).sum())
            total+=len(ids)
        result.append(x[sample].flatten(1).index_select(1,perm.to(x.device)).reshape_as(x[sample]))
    return torch.stack(result),dict(moved_tokens=moved,total_tokens=total)
class SupportResidual(N1Segmenter):
    def __init__(self,rgb_expert,dsm_expert,job,path,digest):
        legacy=dict(id='N1-2',information_entry='late',adaptation='last4_and_heads')
        super().__init__(rgb_expert,dsm_expert,legacy)
        h=hashlib.sha256()
        with open(path,'rb') as f:
            for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
        if h.hexdigest()!=digest:raise RuntimeError('S1-0 checkpoint SHA changed')
        s=torch.load(path,map_location='cpu',weights_only=False)
        if s['global_step']!=8000:raise RuntimeError('base age changed')
        self.load_state_dict(s['model'],strict=True);del s
        self.job=job;self.frozen_base=job['frozen_base'];self.learned_missing=True
        if self.frozen_base:self.requires_grad_(False)
        self.residual=nn.Sequential(nn.Conv2d(264,64,1),nn.GELU(),nn.Conv2d(64,6,3,padding=1))
        nn.init.zeros_(self.residual[-1].weight);nn.init.zeros_(self.residual[-1].bias)
        self.exposure={};self.train(False)
    def train(self,mode=True):
        super().train(mode)
        if getattr(self,'frozen_base',False):
            for name,module in self.named_children():
                if name!='residual':module.eval()
        if hasattr(self,'residual'):self.residual.train(mode)
        return self
    def forward(self,rgb,dsm,rm,dm,return_parts=False):
        if rm.dtype!=torch.bool or dm.dtype!=torch.bool or rm.shape!=dsm.shape or dm.shape!=dsm.shape:raise ValueError('aligned boolean masks')
        rgb=rgb.masked_fill(~rm[:,None],0);dsm=dsm.masked_fill(~dm,0)
        window=rm.flatten(1).any(1)&dm.flatten(1).any(1)
        self.taps={'rgb':{},'dsm':{}}
        with torch.no_grad() if self.frozen_base else contextlib.nullcontext():
            rlog,rf=self.rgb_expert(rgb,dsm);dlog,df=self.dsm_expert(rgb,dsm)
            shape=((rgb.shape[-2]+3)//4,(rgb.shape[-1]+3)//4)
            r=self.pyramid('rgb',rf,rgb,rm,shape);d=self.pyramid('dsm',df,rgb,dm,shape)
            raw=F.interpolate(self.fusion(torch.cat((r,d,r,d),1)),rgb.shape[-2:],mode='nearest')
            valid=rm|dm
            z0=torch.where((rm&dm)[:,None],raw,torch.where(rm[:,None],rlog,dlog)).masked_fill(~valid[:,None],0)
            if self.job['support_preserved']:
                br=torch.where(window[:,None,None],torch.ones_like(rm),rm)
                bd=torch.where(window[:,None,None],torch.ones_like(dm),dm)
                r=self.pyramid('rgb',rf,rgb,br,shape);d=self.pyramid('dsm',df,rgb,bd,shape)
        self.taps={'rgb':{},'dsm':{}}
        shuffled=dict(moved_tokens=0,total_tokens=r.shape[0]*r.shape[-1]*r.shape[-2])
        if self.job['control']=='shuffle':r,shuffled=shuffle_context(r,rm)
        if self.job['control']=='calibration':r=torch.zeros_like(r);d=torch.zeros_like(d)
        z=F.interpolate(z0,shape,mode='nearest')
        masks=F.interpolate(torch.stack((rm,dm),1).float(),shape,mode='nearest')
        features=torch.cat((r,d,z,masks),1)
        delta=F.interpolate(self.residual(features),rgb.shape[-2:],mode='nearest')
        support=((~rm)&dm if self.job['local_only'] else valid)&window[:,None,None]
        result=torch.where(support[:,None],z0+delta,z0).masked_fill(~valid[:,None],0)
        if self.frozen_base and self.job['local_only'] and not torch.equal(result.masked_select((~support)[:,None]),z0.masked_select((~support)[:,None])):raise RuntimeError('native support protection violated')
        self.exposure=dict(residual_support_pixels=int(support.sum()),rgb_missing_observed_dsm_pixels=int(((~rm)&dm&window[:,None,None]).sum()),**shuffled)
        parts=dict(logits=result,rgb=rlog,dsm=dlog,raw=raw,valid=valid,base_logits=z0,residual_support=support)
        return parts if return_parts else result

