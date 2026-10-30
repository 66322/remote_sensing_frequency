"""D23-B core only: frozen expert extraction, matched gates and loss statistics.
Training/inference orchestration and server resource preflight are separate work.
"""
import math
import torch
from torch import nn
from torch.nn import functional as F

ARMS = ("T0","TS","TF","TSF","TCAP","TSF_CE","TSF_shuffleS","TSF_shuffleF")


def finite(x, name):
    if not bool(torch.isfinite(x).all()):
        raise RuntimeError("nonfinite "+name)


def repeat_channels(x, width):
    return x.repeat(1, math.ceil(width/x.shape[1]), 1, 1)[:,:width]


def output_evidence(z0, z1):
    p0, p1 = z0.softmax(1), z1.softmax(1)
    e0 = -(p0*p0.clamp_min(1e-8).log()).sum(1,keepdim=True)
    e1 = -(p1*p1.clamp_min(1e-8).log()).sum(1,keepdim=True)
    delta = p1.max(1,keepdim=True).values-p0.max(1,keepdim=True).values
    agree = (p0.argmax(1,keepdim=True)==p1.argmax(1,keepdim=True)).to(z0.dtype)
    return torch.cat((z0,z1,e0,e1,delta,agree),1)


def frequency_evidence(optical, dsm):
    if dsm.ndim != 3 or optical.ndim != 4 or optical.shape[0] != dsm.shape[0] or optical.shape[-2:]!=dsm.shape[-2:]:
        raise RuntimeError("optical/DSM shape mismatch")
    h,w=dsm.shape[-2:]
    raw=torch.cat((optical.mean(1,keepdim=True),dsm[:,None]),1)
    raw=F.avg_pool2d(F.pad(raw,(0,(-w)%4,0,(-h)%4),mode="replicate"),4,4)
    low=F.avg_pool2d(F.pad(raw,(2,2,2,2),mode="replicate"),5,1)
    high=raw-low
    return torch.cat((low[:,0:1],high[:,0:1],low[:,1:2],high[:,1:2]),1).detach()


class FrozenExpertPair(nn.Module):
    """Pass existing D21 R0/M0 instances; does not construct/load/share an encoder."""
    def __init__(self,r0,m0):
        super().__init__()
        self.r0,self.m0=r0,m0
        for expert in (self.r0,self.m0):
            expert.requires_grad_(False)
            expert.eval()
            if not hasattr(expert,"decoder") or len(expert.decoder)!=4:
                raise RuntimeError("expected D21 decoder execution chain")
            layer=expert.decoder[3]
            if not isinstance(layer,nn.Conv2d) or layer.in_channels!=128 or layer.out_channels!=6:
                raise RuntimeError("expected final D21 128-to-6 classifier")

    def train(self,mode=True):
        super().train(False)
        return self

    @staticmethod
    def extract(expert,optical,dsm):
        captured={}
        def hook(layer,inputs,output):
            captured["semantic"]=inputs[0].detach()
            captured["low_logits"]=output.detach()
        handle=expert.decoder[3].register_forward_hook(hook)
        try:
            with torch.no_grad():
                logits=expert(optical,dsm).detach()
        finally:
            handle.remove()
        if set(captured)!={"semantic","low_logits"}:
            raise RuntimeError("classifier hook was not executed")
        h,w=optical.shape[-2:]
        if captured["semantic"].shape[1:]!=(128,(h+3)//4,(w+3)//4):
            raise RuntimeError("D21 semantic stride/channel mismatch")
        expected=F.interpolate(captured["low_logits"],size=(h,w),mode="nearest")
        if not torch.equal(logits,expected):
            raise RuntimeError("D21 low/full logits mismatch")
        for name,x in captured.items(): finite(x,name)
        finite(logits,"expert logits")
        return logits,captured["low_logits"],captured["semantic"]

    def forward(self,optical,dsm):
        self.train(False)
        result0=self.extract(self.r0,optical,dsm)
        result1=self.extract(self.m0,optical,dsm)
        return {"z0":result0[0],"z1":result1[0],
                "E":output_evidence(result0[1],result1[1]).detach(),
                "S":torch.cat((result0[2],result1[2]),1).detach(),
                "F":frequency_evidence(optical,dsm)}


class DenseBenefitGate(nn.Module):
    def __init__(self,arm):
        super().__init__()
        if arm not in ARMS: raise ValueError(arm)
        self.arm=arm
        self.layers=nn.Sequential(nn.Conv2d(276,32,1),nn.GELU(),
                                  nn.Conv2d(32,32,3,padding=1),nn.GELU(),nn.Conv2d(32,1,1))
        nn.init.zeros_(self.layers[-1].weight)
        nn.init.zeros_(self.layers[-1].bias)
        self.register_buffer("e_mean",torch.zeros(1,16,1,1))
        self.register_buffer("e_std",torch.ones(1,16,1,1))
        self.register_buffer("stats_ready",torch.tensor(False))

    def set_fit_statistics(self,mean,std):
        mean=torch.as_tensor(mean,dtype=self.e_mean.dtype,device=self.e_mean.device).reshape_as(self.e_mean)
        std=torch.as_tensor(std,dtype=self.e_std.dtype,device=self.e_std.device).reshape_as(self.e_std)
        finite(mean,"fit mean"); finite(std,"fit std")
        if bool((std<0).any()): raise RuntimeError("negative fit std")
        self.e_mean.copy_(mean);self.e_std.copy_(std.clamp_min(1e-6))
        self.stats_ready.fill_(True)

    def inputs(self,E,S,Fq):
        for name,x,width in (("E",E,16),("S",S,256),("F",Fq,4)):
            if x.ndim!=4 or x.shape[1]!=width or x.shape[0]!=E.shape[0] or x.shape[-2:]!=E.shape[-2:]:
                raise RuntimeError("bad gate input "+name)
            finite(x,name)
        E,S,Fq=E.detach(),S.detach(),Fq.detach()
        if self.arm=="TCAP":
            if not bool(self.stats_ready): raise RuntimeError("TCAP requires frozen gate-fit statistics")
            standardized=(E-self.e_mean)/self.e_std
            basis=torch.cat((standardized.square(),standardized.tanh()),1)
            S,Fq=repeat_channels(basis,256),repeat_channels(basis,4)
        else:
            if self.arm not in ("TS","TSF","TSF_CE","TSF_shuffleS","TSF_shuffleF"):
                S=repeat_channels(E,256)
            if self.arm not in ("TF","TSF","TSF_CE","TSF_shuffleS","TSF_shuffleF"):
                Fq=repeat_channels(E,4)
            if self.arm=="TSF_shuffleS":
                S=torch.roll(S,(S.shape[-2]//2,S.shape[-1]//2),(-2,-1))
            if self.arm=="TSF_shuffleF":
                Fq=torch.roll(Fq,(Fq.shape[-2]//2,Fq.shape[-1]//2),(-2,-1))
        x=torch.cat((E,S,Fq),1)
        finite(x,"gate input")
        return x

    def forward(self,E,S,Fq,z0,z1,available):
        if z0.shape!=z1.shape or available.shape!=z0[:,0].shape or available.dtype!=torch.bool:
            raise RuntimeError("logits/boolean availability mismatch")
        raw=F.interpolate(self.layers(self.inputs(E,S,Fq)),size=z0.shape[-2:],mode="nearest")
        g=raw.sigmoid()
        # This operation must also be repeated after complete-image window stitching.
        z=torch.where(available[:,None],z0.detach()+g*(z1.detach()-z0.detach()),z0.detach())
        finite(z,"fused logits")
        return {"logits":z,"gate_logits":raw,"g":g}


def loss_sums(logits,gate_logits,z0,z1,label,available):
    """Return sums/counts so effective-batch denominators survive microbatch changes.
    Only training loss takes labels. No class/threshold search.
    """
    if label.shape!=logits[:,0].shape or available.shape!=label.shape or label.dtype!=torch.long:
        raise RuntimeError("loss shape/label mismatch")
    if bool(((label!=255)&((label<0)|(label>5))).any()): raise RuntimeError("bad class ID")
    valid=label!=255
    ce=F.cross_entropy(logits,label,ignore_index=255,reduction="none")
    p0,p1=z0.detach().argmax(1),z1.detach().argmax(1)
    positive=valid & available & (p1==label) & (p0!=label)
    negative=valid & available & (p0==label) & (p1!=label)
    raw=gate_logits[:,0]
    return {"ce_sum":ce[valid].sum(),"valid":int(valid.sum()),
            "positive_sum":F.softplus(-raw[positive]).sum(),"positive":int(positive.sum()),
            "negative_sum":F.softplus(raw[negative]).sum(),"negative":int(negative.sum())}


def combine_loss_sums(parts,utility_weight=1.0):
    if not parts: raise RuntimeError("empty loss batch")
    def average(sum_key,count_key):
        numerator=sum(p[sum_key] for p in parts)
        count=sum(p[count_key] for p in parts)
        return numerator/max(1,count)
    return average("ce_sum","valid")+utility_weight*0.5*(
        average("positive_sum","positive")+average("negative_sum","negative"))


def fixed_blend(z0,z1,available,kind):
    p0,p1=z0.softmax(1),z1.softmax(1)
    if kind=="R0": selected=z0
    elif kind=="M0_safe": selected=z1
    elif kind=="confidence":
        choose=p1.max(1,keepdim=True).values>p0.max(1,keepdim=True).values
        selected=torch.where(choose,z1,z0)
    elif kind=="entropy":
        h0=-(p0*p0.clamp_min(1e-8).log()).sum(1,keepdim=True)
        h1=-(p1*p1.clamp_min(1e-8).log()).sum(1,keepdim=True)
        selected=torch.where(h1<h0,z1,z0)
    elif kind=="logit_average": selected=0.5*(z0+z1)
    elif kind=="probability_average": selected=(0.5*(p0+p1)).clamp_min(1e-8).log()
    else: raise ValueError(kind)
    return torch.where(available[:,None],selected,z0)

