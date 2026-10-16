"""Exact RGB initialization, deployable features and differentiable signed residual."""
import math
import torch
from torch import nn
from torch.nn import functional as F

def features_torch(r,d,rgb,ds,rm,dm):
 rp,dp=r.double().softmax(1),d.double().softmax(1)
 entropy=lambda p:-(p*p.clamp_min(1e-300).log()).sum(1)/math.log(6)
 margin=lambda p:p.topk(2,dim=1).values[:,0]-p.topk(2,dim=1).values[:,1]
 norm=lambda z:torch.log1p(((z.double()-z.double().mean(1,keepdim=True)).square().sum(1)).sqrt()).div(8).clamp(0,1)
 a=ds.double();av=dm.double()
 box=lambda x:F.avg_pool2d(F.pad(x[:,None],(2,2,2,2),mode='replicate'),5,1)[:,0]
 weight=box(av);mean=box(a*av)/weight.clamp_min(1e-12)
 std=(box(a*a*av)/weight.clamp_min(1e-12)-mean.square()).clamp_min(0).sqrt()
 gx=F.pad(a[:,:,1:]-a[:,:,:-1],(0,1,0,0),mode='replicate')
 gy=F.pad(a[:,1:]-a[:,:-1],(0,0,0,1),mode='replicate')
 mx=F.pad((dm[:,:,1:]&dm[:,:,:-1]).double(),(0,1,0,0),mode='replicate')
 my=F.pad((dm[:,1:]&dm[:,:-1]).double(),(0,0,0,1),mode='replicate')
 grad=((gx*mx).square()+(gy*my).square()).sqrt()
 zero=box((rgb==0).all(1).double())
 return torch.stack((entropy(rp),entropy(dp),rp.max(1).values,dp.max(1).values,margin(rp),margin(dp),
  norm(r),norm(d),(r.argmax(1)!=d.argmax(1)).double(),(mean/4).clamp(-1,1),(std/4).clamp(0,1),
  (grad/4).clamp(0,1),zero,rm.double(),dm.double()),1).float()

class ProtectedHead(nn.Module):
 def __init__(self,arm):
  super().__init__()
  if arm not in ('T1','T2','T3'):raise ValueError(arm)
  self.arm=arm;self.net=nn.Sequential(nn.Conv2d(15,32,1),nn.GELU(),nn.Conv2d(32,1,1))
  nn.init.zeros_(self.net[-1].weight);nn.init.zeros_(self.net[-1].bias)
 def forward(self,r,d,features,rm,dm):
  features=features.clone()
  if self.arm=='T2':features[:,:13]=0
  if self.arm=='T3':features[:,9:12]=torch.roll(features[:,9:12],(256,256),(-2,-1))
  gate=torch.tanh(self.net(features));z=r+gate*(d-r)
  z=torch.where((rm&dm)[:,None],z,torch.where(rm[:,None],r,d)).masked_fill(~(rm|dm)[:,None],0)
  return z,gate
 def weights(self):
  return dict(w0=self.net[0].weight.detach().cpu().numpy()[:,:,0,0].tolist(),
   b0=self.net[0].bias.detach().cpu().tolist(),w1=self.net[2].weight.detach().cpu().numpy()[0,:,0,0].tolist(),
   b1=float(self.net[2].bias.detach().cpu()[0]),training_precision='FP32',deployment_precision='FP64_post_stitch_numpy')
