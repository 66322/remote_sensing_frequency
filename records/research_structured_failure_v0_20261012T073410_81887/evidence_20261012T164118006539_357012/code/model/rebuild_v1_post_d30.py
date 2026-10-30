"""Shared/private alignment, bounded correspondence, and missing-modality heads.

Labels and corruption IDs are never forward inputs. The 64/64 split is structural,
not a claim that learned factors have been identified.
"""
import torch
from torch import nn
from torch.nn import functional as F
from model.rebuild_v1_d26 import align_feature, valid_at, pack, unpack, shift


def correspondence(query, donor, qm, dm, radius=2, shuffled=False):
    """Normalized soft search; zero padding is excluded, never cyclic donor wrap."""
    b,c,h,w=query.shape;k=2*radius+1
    padded=F.pad(donor,(radius,)*4);mask=F.pad(dm,(radius,)*4)
    patches=torch.stack([padded[...,y:y+h,x:x+w] for y in range(k) for x in range(k)],2)
    valid=torch.stack([mask[...,y:y+h,x:x+w] for y in range(k) for x in range(k)],2)
    similarity=(F.normalize(query.float(),dim=1)[:,:,None]*F.normalize(patches.float(),dim=1)).sum(1)/0.1
    weights=similarity.masked_fill(~valid[:,0],-1e4).softmax(1)*valid[:,0]
    weights=weights/weights.sum(1,keepdim=True).clamp_min(1e-8)
    if shuffled:
        weights=shift(weights)*valid[:,0]
        weights=weights/weights.sum(1,keepdim=True).clamp_min(1e-8)
    result=(patches*weights[:,None].to(patches.dtype)).sum(2)*qm
    return result, weights


class BandBlock(nn.Module):
    def __init__(self):
        super().__init__();self.block=nn.Sequential(nn.Conv2d(512,512,1,groups=4),nn.GELU(),nn.Conv2d(512,512,1,groups=4))
    def forward(self,x,frequency,drop):
        z=pack(x,frequency)
        if drop:
            z=z.reshape(z.shape[0],128,4,*z.shape[-2:])
            z=torch.cat((z[:,:,:1],torch.zeros_like(z[:,:,1:])),2).flatten(1,2)
        base=unpack(z,x.shape[-2:],frequency) if drop else x
        return base+unpack(self.block(z),x.shape[-2:],frequency)


class PortfolioSegmenter(nn.Module):
    def __init__(self,rgb_expert,dsm_expert,job,teacher=None):
        super().__init__();self.arm=job['id'];self.job=job;self.learned_missing=self.arm.startswith('C')
        self.teacher=teacher
        if self.learned_missing:
            if teacher is None:raise ValueError('bound B0 teacher required')
            teacher.requires_grad_(False);teacher.eval()
            self.single_rgb=nn.Sequential(nn.Conv2d(rgb_expert.channels,128,1),nn.GroupNorm(8,128),nn.GELU(),nn.Conv2d(128,6,1))
            self.single_dsm=nn.Sequential(nn.Conv2d(dsm_expert.channels,128,1),nn.GroupNorm(8,128),nn.GELU(),nn.Conv2d(128,6,1))
            for head in (self.single_rgb,self.single_dsm):
                nn.init.normal_(head[-1].weight,std=.001);nn.init.zeros_(head[-1].bias)
        else:
            self.rgb_expert=rgb_expert;self.dsm_expert=dsm_expert
            for expert in (rgb_expert,dsm_expert):expert.configure(False)
            self.project_rgb=nn.Conv2d(rgb_expert.channels,128,1);self.project_dsm=nn.Conv2d(dsm_expert.channels,128,1)
            self.fusion=nn.Sequential(nn.Conv2d(512,128,3,padding=1),nn.GroupNorm(8,128),nn.GELU(),nn.Conv2d(128,6,1))
            self.predict_rgb=nn.Sequential(nn.Conv2d(128,128,3,padding=1),nn.GELU(),nn.Conv2d(128,128,1))
            self.predict_dsm=nn.Sequential(nn.Conv2d(128,128,3,padding=1),nn.GELU(),nn.Conv2d(128,128,1))
            self.aux_rgb=nn.Conv2d(64,6,1);self.aux_dsm=nn.Conv2d(64,6,1)
            if self.arm.startswith('F'):self.bands=nn.ModuleList([BandBlock(),BandBlock()])
    def train(self,mode=True):
        super().train(mode)
        if self.teacher is not None:self.teacher.eval()
        return self
    def single(self,rgb,dsm,mask,name):
        """Training-only single path: do not execute the unused expert or fusion."""
        if not self.learned_missing or name not in ('rgb','dsm'):raise ValueError('C single path only')
        rgb=rgb.masked_fill(~mask[:,None],0) if name=='rgb' else torch.zeros_like(rgb)
        dsm=dsm.masked_fill(~mask,0) if name=='dsm' else torch.zeros_like(dsm)
        expert=getattr(self.teacher,name+'_expert');head=getattr(self,'single_'+name)
        with torch.no_grad():logits,feature=expert(rgb,dsm)
        shape=((rgb.shape[-2]+3)//4,(rgb.shape[-1]+3)//4)
        feature=align_feature(feature,shape)*valid_at(mask,shape)
        return (logits+F.interpolate(head(feature),rgb.shape[-2:],mode='nearest')).masked_fill(~mask[:,None],0)
    def forward(self,rgb,dsm,rgb_mask,dsm_mask,return_parts=False):
        if rgb_mask.dtype!=torch.bool or dsm_mask.dtype!=torch.bool or rgb_mask.shape!=dsm.shape or dsm_mask.shape!=dsm.shape:raise ValueError('boolean availability masks required')
        rgb=rgb.masked_fill(~rgb_mask[:,None],0);dsm=dsm.masked_fill(~dsm_mask,0)
        r_ex=self.teacher.rgb_expert if self.learned_missing else self.rgb_expert
        d_ex=self.teacher.dsm_expert if self.learned_missing else self.dsm_expert
        with torch.no_grad():rlog,rf=r_ex(rgb,dsm);dlog,df=d_ex(rgb,dsm)
        shape=((rgb.shape[-2]+3)//4,(rgb.shape[-1]+3)//4)
        rf,df=align_feature(rf,shape),align_feature(df,shape)
        rm,dm=valid_at(rgb_mask,shape),valid_at(dsm_mask,shape)
        valid=rgb_mask|dsm_mask
        if self.learned_missing:
            # Reproduce B0 full-input graph using captured frozen features; no second expert pass.
            with torch.no_grad():
                r=self.teacher.project_rgb(rf)*rm;d=self.teacher.project_dsm(df)*dm
                raw=F.interpolate(self.teacher.fusion(torch.cat((r,d,r,d),1)),rgb.shape[-2:],mode='nearest')
            sr=rlog+F.interpolate(self.single_rgb(rf*rm),rgb.shape[-2:],mode='nearest')
            sd=dlog+F.interpolate(self.single_dsm(df*dm),rgb.shape[-2:],mode='nearest')
            result=torch.where((rgb_mask&dsm_mask)[:,None],raw,torch.where(rgb_mask[:,None],sr,sd)).masked_fill(~valid[:,None],0)
            parts=dict(logits=result,rgb=rlog,dsm=dlog,raw=raw,valid=valid,student_rgb=sr,student_dsm=sd)
        else:
            r=self.project_rgb(rf)*rm;d=self.project_dsm(df)*dm
            if self.arm.startswith('F'):
                r=self.bands[0](r,self.arm!='F0',self.arm=='F3')*rm
                d=self.bands[1](d,self.arm!='F0',self.arm=='F2')*dm
            rs,ds=r[:,:64],d[:,:64];rd,dr=rs,ds
            if self.job.get('radius',0):
                dr,_=correspondence(rs,ds,rm,dm,self.job['radius'],self.job.get('shuffle',False))
                rd,_=correspondence(ds,rs,dm,rm,self.job['radius'],self.job.get('shuffle',False))
            pr=self.predict_rgb(torch.cat((dr,d[:,64:]),1))*rm*dm
            pd=self.predict_dsm(torch.cat((rd,r[:,64:]),1))*rm*dm
            raw=F.interpolate(self.fusion(torch.cat((r,d,pr,pd),1)),rgb.shape[-2:],mode='nearest')
            result=torch.where((rgb_mask&dsm_mask)[:,None],raw,torch.where(rgb_mask[:,None],rlog,dlog)).masked_fill(~valid[:,None],0)
            parts=dict(logits=result,rgb=rlog,dsm=dlog,raw=raw,valid=valid,features_rgb=r,features_dsm=d,pred_rgb=pr,pred_dsm=pd,
                       feature_valid=rm&dm,aux_rgb=F.interpolate(self.aux_rgb(rs),rgb.shape[-2:],mode='nearest'),aux_dsm=F.interpolate(self.aux_dsm(ds),rgb.shape[-2:],mode='nearest'))
        return parts if return_parts else parts['logits']


def masked_mean(values,mask,denominator=None):
    denom=mask.sum() if denominator is None else denominator
    return (values*mask).sum()/denom.clamp_min(1)


def alignment(parts,job):
    width=128 if job.get('align')=='all' else 64;terms=[]
    mask=parts['feature_valid'][:,0]
    for name in ('rgb','dsm'):
        target=parts['features_'+name][:,:width].detach()
        if job.get('align')=='shuffled':target=shift(target);mask_used=mask&shift(mask)
        else:mask_used=mask
        loss=1-F.cosine_similarity(parts['pred_'+name][:,:width].float(),target.float(),dim=1)
        terms.append(masked_mean(loss,mask_used,mask.sum()))
    return sum(terms)/2


def distillation(student,teacher,target,valid,mode):
    """Denominator is ALL valid labels, including for teacher-correct masking."""
    valid=valid&(target<6)&(target>=0);correct=valid&(teacher.detach().argmax(1)==target)
    if mode=='hard':return masked_mean(F.cross_entropy(student.float(),target,ignore_index=255,reduction='none'),correct,valid.sum())
    loss=F.kl_div(F.log_softmax(student.float()/2,1),F.softmax(teacher.detach().float()/2,1),reduction='none').sum(1)*4
    return masked_mean(loss,correct if mode=='correct' else valid,valid.sum())
