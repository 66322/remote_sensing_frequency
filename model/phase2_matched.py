"""Matched single-modal experts and co-located static/conditional logit heads."""
import torch
from torch import nn
from torch.nn import functional as F
from model.rebuild_v1_d24 import D24Segmenter

class MatchedExpert(D24Segmenter):
    def __init__(self,encoder):
        super().__init__(encoder,optical_only=True,last4=True,prototype=False)
        self.detail=None
        self.requires_grad_(False)
        for block in self.encoder.blocks[8:12]:block.requires_grad_(True)
        self.rgb.requires_grad_(True);self.decoder.requires_grad_(True)
    def low(self,image):
        return self.decoder(self.encode(image))
    def forward(self,image):
        return F.interpolate(self.low(image),image.shape[-2:],mode='nearest')

def factor(step,budget):
    if not 1<=step<=budget:raise ValueError('step outside schedule')
    return .1+.9*step/100 if step<=100 else (budget-step)/(budget-100)

def optimizer(model,budget):
    groups=[]
    for enc,lr in ((True,2e-5),(False,2e-4)):
        pairs=[(n,p) for n,p in model.named_parameters() if p.requires_grad and n.startswith('encoder.')==enc]
        if pairs:groups.append(dict(params=[p for _,p in pairs],names=[n for n,_ in pairs],lr=lr,initial_lr=lr))
    return torch.optim.AdamW(groups,betas=(.9,.999),weight_decay=.01,eps=1e-8)

def local_stats(x,available=None):
    available=torch.ones_like(x) if available is None else available.float()
    box=lambda a:F.avg_pool2d(F.pad(a,(2,2,2,2),mode='replicate'),5,1)
    weight=box(available)
    mean=box(x*available)/weight.clamp_min(1e-12)
    sq=box(x*x*available)/weight.clamp_min(1e-12)
    return mean,(sq-mean*mean).clamp_min(0).sqrt()

def observables(r,d,rgb,ds,rm,dm):
    rp,dp=r.softmax(1),d.softmax(1)
    entropy=lambda p:-(p*p.clamp_min(1e-12).log()).sum(1,keepdim=True)/1.791759469228055
    margin=lambda p:p.topk(2,dim=1).values.diff(dim=1).neg()
    # Statistics at native input pixels, then deterministic average reduction to head grid.
    gray=rgb.mean(1,keepdim=True);_,rs=local_stats(gray,rm[:,None])
    mean,std=local_stats(ds[:,None],dm[:,None])
    gx=F.pad(ds[:,:,1:]-ds[:,:,:-1],(0,1,0,0),mode='replicate')
    gy=F.pad(ds[:,1:,:]-ds[:,:-1,:],(0,0,0,1),mode='replicate')
    mx=F.pad((dm[:,:,1:]&dm[:,:,:-1]).float(),(0,1,0,0),mode='replicate')
    my=F.pad((dm[:,1:,:]&dm[:,:-1,:]).float(),(0,0,0,1),mode='replicate')
    grad=((gx*mx).square()+(gy*my).square()).sqrt()[:,None]
    reduce=lambda a:F.adaptive_avg_pool2d(a,r.shape[-2:])
    return torch.cat((entropy(rp),entropy(dp),margin(rp),margin(dp),(rp-dp).abs().sum(1,keepdim=True),
        (r.argmax(1,keepdim=True)!=d.argmax(1,keepdim=True)).float(),reduce(rs),reduce(mean),reduce(std),
        reduce(grad),reduce(rm[:,None].float()),reduce(dm[:,None].float())),1)

class FusionHead(nn.Module):
    def __init__(self,arm):
        super().__init__()
        if arm not in ('B0','B1','B2','B3'):raise ValueError(arm)
        self.arm=arm;self.temperature=nn.Parameter(torch.zeros(2))
        if arm=='B0':self.bias=nn.Parameter(torch.zeros(1,6,1,1));self.net=None
        else:
            self.net=nn.Sequential(nn.Conv2d(12,32,1),nn.GELU(),nn.Conv2d(32,6,1))
            nn.init.zeros_(self.net[-1].weight);nn.init.zeros_(self.net[-1].bias)
    def low(self,r,d,obs):
        if self.arm=='B2':obs=torch.cat((torch.zeros_like(obs[:,:10]),obs[:,10:]),1)
        if self.arm=='B3':
            obs=obs.clone();obs[:,7:10]=torch.roll(obs[:,7:10],(obs.shape[-2]//2,obs.shape[-1]//2),(-2,-1))
        w=torch.sigmoid(self.bias if self.net is None else self.net(obs))
        t=self.temperature.exp().clamp(.25,4)
        return w*r/t[0]+(1-w)*d/t[1]
    def forward(self,r,d,obs,rm,dm):
        size=rm.shape[-2:];a=F.interpolate(r,size,mode='nearest');b=F.interpolate(d,size,mode='nearest')
        z=F.interpolate(self.low(r,d,obs),size,mode='nearest')
        return torch.where((rm&dm)[:,None],z,torch.where(rm[:,None],a,b)).masked_fill(~(rm|dm)[:,None],0)
