"""Matched continuations: region ownership N3 and context-support S1."""
import hashlib
import torch
from torch import nn
from torch.nn import functional as F
from model.rebuild_v1_post_ab_n1 import N1Segmenter,compress
from model.rebuild_v1_d26 import valid_at
N3_MODES=['pixel','grid','rgb_region','dsm_region','bilateral']
def grouped(x,assignment,valid):
    # Dense masked matrix products avoid nondeterministic CUDA scatter reductions.
    weight=F.one_hot(assignment,num_classes=64).transpose(1,2).float()*valid.flatten(1)[:,None].float()
    sums=torch.bmm(x.flatten(2).float(),weight.transpose(1,2))
    means=sums/weight.sum(2)[:,None].clamp_min(1)
    return torch.bmm(means,weight).reshape_as(x).to(x.dtype)
def assign_regions(feature,height,valid,kind):
    b,c,h,w=feature.shape
    if h%4 or w%4 or (h//4)*(w//4)!=64:raise ValueError('64 seeds at stride16 require 32x32 native512 grid')
    yy,xx=torch.meshgrid(torch.arange(h,device=feature.device),torch.arange(w,device=feature.device),indexing='ij')
    ids=((yy//4)*(w//4)+xx//4).flatten()[None].expand(b,-1)
    if kind=='grid':return ids
    if kind not in ('rgb','dsm'):raise ValueError('region kind')
    with torch.no_grad():
        v=valid[:,None].float();n=F.avg_pool2d(v,4,4)*16
        desc=F.normalize(compress(feature.detach().float()),dim=1,eps=1e-6) if kind=='rgb' else height.detach().float()
        centers=F.avg_pool2d(desc*v,4,4)*16/n.clamp_min(1)
        if kind=='rgb':centers=F.normalize(centers,dim=1,eps=1e-6)
        gy,gx=torch.meshgrid(torch.arange(h//4,device=feature.device),torch.arange(w//4,device=feature.device),indexing='ij')
        sy,sx=gy.flatten()*4+1.5,gx.flatten()*4+1.5
        spatial=((yy.flatten()[None]-sy[:,None])**2+(xx.flatten()[None]-sx[:,None])**2)/16
        nearby=(abs(yy.flatten()[None]//4-gy.flatten()[:,None])<=1)&(abs(xx.flatten()[None]//4-gx.flatten()[:,None])<=1)
        if kind=='rgb':
            content=2*(1-torch.bmm(centers.flatten(2).transpose(1,2),desc.flatten(2)))
        else:content=4*(centers.flatten(2).transpose(1,2)-desc.flatten(2)).abs()
        cost=spatial[None]+content
        allowed=nearby[None]&(n.flatten(1)>0)[:,:,None]
        result=cost.masked_fill(~allowed,1e6).argmin(1)
        return result
class RegionBlock(nn.Module):
    def __init__(self,mode):
        super().__init__()
        if mode not in N3_MODES:raise ValueError('N3 mode')
        self.mode=mode;self.rgb_message=nn.Conv2d(128,128,1,bias=False);self.dsm_message=nn.Conv2d(128,128,1,bias=False)
    def forward(self,r,d,height,both):
        shape=r.shape[-2:];rr=F.avg_pool2d(r,4,4);dd=F.avg_pool2d(d,4,4)
        valid=F.avg_pool2d(both[:,None].float(),4,4)[:,0]>=1
        hh=F.interpolate(height[:,None].float(),rr.shape[-2:],mode='nearest')
        ar,ad=rr*valid[:,None],dd*valid[:,None]
        if self.mode=='grid':
            ids=assign_regions(rr,hh,valid,'grid');ar=grouped(rr,ids,valid);ad=grouped(dd,ids,valid)
        if self.mode in ('rgb_region','bilateral'):
            ids=assign_regions(rr,hh,valid,'rgb');ad=grouped(dd,ids,valid)
        if self.mode in ('dsm_region','bilateral'):
            ids=assign_regions(rr,hh,valid,'dsm');ar=grouped(rr,ids,valid)
        mr=self.rgb_message(ar)*valid[:,None];md=self.dsm_message(ad)*valid[:,None]
        return r+.1*F.interpolate(mr,shape,mode='nearest'),d+.1*F.interpolate(md,shape,mode='nearest')
class Continuation(N1Segmenter):
    def __init__(self,rgb_expert,dsm_expert,job,teacher=None):
        if job['id'] not in [f'N3-{i}' for i in range(5)]+[f'S1-{i}' for i in range(4)]:raise ValueError('unregistered continuation')
        legacy=dict(job,id='N1-2',information_entry='late',adaptation='last4_and_heads')
        super().__init__(rgb_expert,dsm_expert,legacy,teacher)
        h=hashlib.sha256()
        with open(job['initial_checkpoint_path'],'rb') as f:
            for z in iter(lambda:f.read(8*1024**2),b''):h.update(z)
        if h.hexdigest()!=job['initial_checkpoint_sha256']:raise RuntimeError('fixed N1-2 state changed')
        state=torch.load(job['initial_checkpoint_path'],map_location='cpu',weights_only=False)
        if state['global_step']!=8000:raise RuntimeError('initial age differs')
        self.load_state_dict(state['model'],strict=True);del state
        self.job=job;self.family=job['id'].split('-')[0];i=int(job['id'].split('-')[1])
        self.support_preserved=self.family=='S1' and i in (1,3)
        self.fusion_retained=self.family=='S1' and i in (2,3)
        self.learned_missing=self.fusion_retained
        if self.family=='N3':self.region=RegionBlock(N3_MODES[i])
    def forward(self,rgb,dsm,rgb_mask,dsm_mask,return_parts=False):
        if rgb_mask.dtype!=torch.bool or dsm_mask.dtype!=torch.bool or rgb_mask.shape!=dsm.shape or dsm_mask.shape!=dsm.shape:raise ValueError('boolean aligned availability masks required')
        rgb=rgb.masked_fill(~rgb_mask[:,None],0);dsm=dsm.masked_fill(~dsm_mask,0)
        rg=rgb_mask.flatten(1).any(1)[:,None,None];dg=dsm_mask.flatten(1).any(1)[:,None,None];local_window=rg&dg
        br=torch.where(local_window,torch.ones_like(rgb_mask),rgb_mask) if self.support_preserved else rgb_mask
        bd=torch.where(local_window,torch.ones_like(dsm_mask),dsm_mask) if self.support_preserved else dsm_mask
        self.taps={'rgb':{},'dsm':{}}
        rlog,rf=self.rgb_expert(rgb,dsm);dlog,df=self.dsm_expert(rgb,dsm)
        shape=((rgb.shape[-2]+3)//4,(rgb.shape[-1]+3)//4)
        try:r=self.pyramid('rgb',rf,rgb,br,shape);d=self.pyramid('dsm',df,rgb,bd,shape)
        finally:self.taps={'rgb':{},'dsm':{}}
        if self.family=='N3':
            both=valid_at(rgb_mask,shape).bool()[:,0]&valid_at(dsm_mask,shape).bool()[:,0]
            r,d=self.region(r,d,dsm,both)
        raw=F.interpolate(self.fusion(torch.cat((r,d,r,d),1)),rgb.shape[-2:],mode='nearest')
        safe=torch.where(rgb_mask[:,None],rlog,dlog)
        hard=torch.where((rgb_mask&dsm_mask)[:,None],raw,safe)
        result=torch.where(local_window[:,None],raw,hard) if self.fusion_retained else hard
        valid=rgb_mask|dsm_mask;result=result.masked_fill(~valid[:,None],0)
        parts=dict(logits=result,rgb=rlog,dsm=dlog,raw=raw,valid=valid)
        return parts if return_parts else result
