"""Fixed local relation propagation; no labels or degradation IDs enter relations."""
import torch
from torch import nn
from torch.nn import functional as F

MODES=('spatial','height','semantic','bilateral','shuffle_height','shuffle_semantic')
def patches(x):
    b,c,h,w=x.shape
    return F.unfold(x,3,padding=1).reshape(b,c,9,h,w)

def affinities(rgb,height,valid,mode):
    if mode not in MODES:raise ValueError('unregistered relation mode')
    # float32 relation normalization avoids bf16 softmax accumulation ambiguity.
    b,_,h,w=rgb.shape
    distance=rgb.new_tensor([-1.,-.5,-1.,-.5,0.,-.5,-1.,-.5,-1.],dtype=torch.float32).view(1,9,1,1)
    neighbor=patches(valid[:,None].float())[:,0].bool()
    pair=neighbor & valid[:,None]
    hh=height.float();hr=(-(patches(hh)[:,0]-hh[:,0,None]).abs()*4.).masked_fill(~pair,0.)
    rr=F.normalize(rgb.detach().float(),dim=1,eps=1e-6)
    sr=(((patches(rr)*rr[:,:,None]).sum(1)-1.)*2.).masked_fill(~pair,0.)
    if mode=='shuffle_height':hr=torch.roll(hr,(h//2,w//2),(-2,-1))
    if mode=='shuffle_semantic':sr=torch.roll(sr,(h//2,w//2),(-2,-1))
    use_h=mode in ('height','bilateral','shuffle_height','shuffle_semantic')
    use_s=mode in ('semantic','bilateral','shuffle_height','shuffle_semantic')
    # Missing center has an all-zero propagation; masked donors never participate.
    def normalize(score):
        z=(distance+(score if score is not None else 0.)).masked_fill(~pair,-1e4)
        weights=z.softmax(1)*pair
        return weights/weights.sum(1,keepdim=True).clamp_min(1e-12)
    return normalize(hr if use_h else None),normalize(sr if use_s else None)

class RelationPropagation(nn.Module):
    def __init__(self,mode):
        super().__init__()
        if mode not in MODES:raise ValueError('unregistered mode')
        self.mode=mode
        self.rgb_message=nn.Conv2d(128,128,1,bias=False)
        self.dsm_message=nn.Conv2d(128,128,1,bias=False)
    def forward(self,r,d,height,valid):
        # N1 late maps at stride4 -> fixed stride16, one 3x3 propagation -> nearest return.
        shape=r.shape[-2:]
        rr=F.avg_pool2d(r,4,4);dd=F.avg_pool2d(d,4,4)
        vv=F.avg_pool2d(valid[:,None].float(),4,4)[:,0]>=1.
        hh=F.interpolate(height[:,None].float(),rr.shape[-2:],mode='nearest')
        wr,wd=affinities(rr,hh,vv,self.mode)
        ar=(patches(rr)*wr[:,None].to(rr.dtype)).sum(2)
        ad=(patches(dd)*wd[:,None].to(dd.dtype)).sum(2)
        mr=self.rgb_message(ar)*vv[:,None];md=self.dsm_message(ad)*vv[:,None]
        return r+.1*F.interpolate(mr,shape,mode='nearest'),d+.1*F.interpolate(md,shape,mode='nearest')
