"""N1 factorial: fixed-capacity late features versus depth/scale encoder taps."""
import contextlib
import math
import torch
from torch import nn
from torch.nn import functional as F
from model.rebuild_v1_d26 import align_feature, valid_at


def compress(x, width=32):
    """Fixed channel grouping, no unmatched learned capacity across factorial cells."""
    b,c,h,w=x.shape
    if c>=width and c%width==0:
        return x.reshape(b,width,c//width,h,w).mean(2)
    if c<width and width%c==0:
        return x.repeat(1,width//c,1,1)
    raise ValueError('unsupported fixed channel grouping '+str(c))


class N1Segmenter(nn.Module):
    def __init__(self,rgb_expert,dsm_expert,job,teacher=None):
        super().__init__()
        if job['id'] not in ('N1-0','N1-1','N1-2','N1-3'):
            raise ValueError('N1 worker cannot run reserved research stages')
        self.job=job;self.learned_missing=False
        # Evaluation always uses the immutable original anchor pair for scientific partitions.
        self.arm='J0';self.joint=job['adaptation']=='last4_and_heads'
        self.multiscale=job['information_entry']=='encoder_depth_scale'
        self.rgb_expert=rgb_expert;self.dsm_expert=dsm_expert
        for expert in (rgb_expert,dsm_expert):expert.configure(self.joint)
        self.taps={'rgb':{},'dsm':{}}
        self.handles=[]
        for name,blocks in (('rgb',rgb_expert.net.encoder.blocks),('dsm',dsm_expert.net.transformer.encoder.layer)):
            if len(blocks)!=12:raise RuntimeError('expected bound twelve-block encoders')
            for depth in (5,8,11):
                def capture(module,args,output,name=name,depth=depth):
                    self.taps[name][depth]=output[0] if isinstance(output,tuple) else output
                self.handles.append(blocks[depth].register_forward_hook(capture))
        self.project_rgb=nn.ModuleList([nn.Conv2d(32,32,1) for _ in range(3)])
        self.project_dsm=nn.ModuleList([nn.Conv2d(32,32,1) for _ in range(3)])
        self.merge_rgb=nn.Conv2d(96,128,1);self.merge_dsm=nn.Conv2d(96,128,1)
        self.fusion=nn.Sequential(nn.Conv2d(512,128,3,padding=1),nn.GroupNorm(8,128),nn.GELU(),nn.Conv2d(128,6,1))

    def train(self,mode=True):
        super().train(mode)
        self.rgb_expert.train(mode);self.dsm_expert.train(mode)
        return self

    def pyramid(self,name,late,rgb,mask,shape):
        maps=[]
        h,w=rgb.shape[-2:]
        for i,depth in enumerate((5,8,11)):
            if self.multiscale:
                t=self.taps[name][depth]
                if name=='rgb':
                    hh,ww=(h+13)//14,(w+13)//14
                    t=t[:,-hh*ww:]
                else:
                    hh=ww=math.isqrt(t.shape[1])
                    if hh*ww!=t.shape[1]:raise RuntimeError('DSM token grid differs')
                x=t.transpose(1,2).reshape(len(t),t.shape[-1],hh,ww)
            else:x=late
            size=(max(1,shape[0]//(2**i)),max(1,shape[1]//(2**i)))
            x=align_feature(compress(x),size)
            x=getattr(self,'project_'+name)[i](x)*valid_at(mask,size)
            maps.append(F.interpolate(x,shape,mode='nearest'))
        return getattr(self,'merge_'+name)(torch.cat(maps,1))*valid_at(mask,shape)

    def forward(self,rgb,dsm,rgb_mask,dsm_mask,return_parts=False):
        if rgb_mask.shape!=dsm.shape or dsm_mask.shape!=dsm.shape or rgb_mask.dtype!=torch.bool or dsm_mask.dtype!=torch.bool:
            raise ValueError('aligned boolean availability masks required')
        rgb=rgb.masked_fill(~rgb_mask[:,None],0);dsm=dsm.masked_fill(~dsm_mask,0)
        self.taps={'rgb':{},'dsm':{}}
        with contextlib.nullcontext() if self.joint else torch.no_grad():
            rlog,rf=self.rgb_expert(rgb,dsm);dlog,df=self.dsm_expert(rgb,dsm)
        shape=((rgb.shape[-2]+3)//4,(rgb.shape[-1]+3)//4)
        try:
            r=self.pyramid('rgb',rf,rgb,rgb_mask,shape)
            d=self.pyramid('dsm',df,rgb,dsm_mask,shape)
        finally:self.taps={'rgb':{},'dsm':{}}
        raw=F.interpolate(self.fusion(torch.cat((r,d,r,d),1)),rgb.shape[-2:],mode='nearest')
        valid=rgb_mask|dsm_mask
        result=torch.where((rgb_mask&dsm_mask)[:,None],raw,torch.where(rgb_mask[:,None],rlog,dlog)).masked_fill(~valid[:,None],0)
        parts=dict(logits=result,rgb=rlog,dsm=dlog,raw=raw,valid=valid)
        return parts if return_parts else result
