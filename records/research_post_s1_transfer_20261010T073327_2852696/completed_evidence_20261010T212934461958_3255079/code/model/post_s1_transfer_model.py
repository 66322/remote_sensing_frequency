"""Private decoder transfer on frozen S1-0 late features; one expert pass."""
import copy
import hashlib
import torch
from torch import nn
from torch.nn import functional as F
from model.rebuild_v1_post_ab_n1 import N1Segmenter,compress
from model.rebuild_v1_d26 import valid_at,align_feature
from model.post_s1_support_model import state_digest as _digest

HEADS=('project_rgb','project_dsm','merge_rgb','merge_dsm','fusion')
def state_digest(model):return _digest(model,exclude='branch.')
def checkpoint(path,digest):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    if h.hexdigest()!=digest:raise RuntimeError('checkpoint SHA changed')
    s=torch.load(path,map_location='cpu',weights_only=False)
    if s['global_step']!=8000:raise RuntimeError('donor/base age changed')
    return s['model']

class PrivateDecoder(N1Segmenter):
    def __init__(self,rgb_expert,dsm_expert,job,path,digest,donor=None):
        super().__init__(rgb_expert,dsm_expert,dict(id='N1-2',information_entry='late',adaptation='last4_and_heads'))
        self.load_state_dict(checkpoint(path,digest),strict=True)
        self.requires_grad_(False)
        self.branch=nn.ModuleDict({n:copy.deepcopy(getattr(self,n)) for n in HEADS})
        self.branch.requires_grad_(True)
        if job['donor']=='random':
            for m in self.branch.modules():
                if isinstance(m,(nn.Conv2d,nn.GroupNorm)):m.reset_parameters()
        else:
            if donor is None:raise ValueError('bound donor required')
            source=checkpoint(donor['path'],donor['sha256'])
            heads={n:v for n,v in source.items() if n.split('.')[0] in HEADS}
            self.branch.load_state_dict(heads,strict=True)
            del source
        self.job=job;self.frozen_base=True;self.learned_missing=True;self.exposure={};self.train(False)
    def train(self,mode=True):
        super().train(mode)
        for n,m in self.named_children():m.train(mode if n=='branch' else False)
        return self
    def branch_pyramid(self,name,late,mask,shape):
        maps=[]
        for i in range(3):
            size=tuple(max(1,s//2**i) for s in shape)
            x=align_feature(compress(late),size)
            x=self.branch['project_'+name][i](x)*valid_at(mask,size)
            maps.append(F.interpolate(x,shape,mode='nearest'))
        return self.branch['merge_'+name](torch.cat(maps,1))*valid_at(mask,shape)
    def forward(self,rgb,dsm,rm,dm,return_parts=False):
        if rm.dtype!=torch.bool or dm.dtype!=torch.bool or rm.shape!=dsm.shape or dm.shape!=dsm.shape:raise ValueError('aligned boolean masks')
        rgb=rgb.masked_fill(~rm[:,None],0);dsm=dsm.masked_fill(~dm,0)
        window=rm.flatten(1).any(1)&dm.flatten(1).any(1)
        self.taps={'rgb':{},'dsm':{}}
        with torch.no_grad():
            rlog,rf=self.rgb_expert(rgb,dsm);dlog,df=self.dsm_expert(rgb,dsm)
            shape=tuple((s+3)//4 for s in rgb.shape[-2:])
            r=self.pyramid('rgb',rf,rgb,rm,shape);d=self.pyramid('dsm',df,rgb,dm,shape)
            raw=F.interpolate(self.fusion(torch.cat((r,d,r,d),1)),rgb.shape[-2:],mode='nearest')
            valid=rm|dm
            z0=torch.where((rm&dm)[:,None],raw,torch.where(rm[:,None],rlog,dlog)).masked_fill(~valid[:,None],0)
        self.taps={'rgb':{},'dsm':{}}
        br,bd=rm,dm
        if self.job['support_preserved']:
            br=torch.where(window[:,None,None],torch.ones_like(rm),rm)
            bd=torch.where(window[:,None,None],torch.ones_like(dm),dm)
        r=self.branch_pyramid('rgb',rf,br,shape);d=self.branch_pyramid('dsm',df,bd,shape)
        branch=F.interpolate(self.branch['fusion'](torch.cat((r,d,r,d),1)),rgb.shape[-2:],mode='nearest')
        support=(~rm)&dm&window[:,None,None]
        result=torch.where(support[:,None],branch,z0).masked_fill(~valid[:,None],0)
        self.exposure=dict(residual_support_pixels=int(support.sum()),moved_tokens=0,total_tokens=r.shape[0]*r.shape[-2]*r.shape[-1])
        parts=dict(logits=result,rgb=rlog,dsm=dlog,raw=raw,valid=valid,base_logits=z0,residual_support=support)
        return parts if return_parts else result
