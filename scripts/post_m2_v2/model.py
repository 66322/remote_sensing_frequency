import torch
from torch import nn
from torch.nn import functional as F
from . import common as c

def block(a,b,stride=1):
    return nn.Sequential(nn.Conv2d(a,b,3,stride=stride,padding=1,bias=False),nn.GroupNorm(8,b),nn.GELU())

class Readout(nn.Module):
    """Full 512 supervision. All auxiliary parameters participate in forward/backward."""
    def __init__(self,arm):
        super().__init__();self.arm=arm
        self.project=nn.Conv2d(384,96,1)
        self.rgb=nn.Sequential(block(3,32,2),block(32,48,2))
        # B0 has an equally trainable RGB-derived slot; B1 uses centred DSM+validity.
        self.aux=nn.Sequential(block(2,32,2),block(32,48,2))
        self.fuse=nn.Sequential(block(192,96),block(96,96))
        if arm.startswith('G'):
            self.query=nn.Conv2d(96,16,1);self.key=nn.Conv2d(96,16,1)
            self.relation_out=nn.Conv2d(96,96,1)
        if arm.startswith('S'):
            self.guide=nn.Sequential(block(2,32),nn.Conv2d(32,96,1))
            self.refine=nn.Sequential(block(96,96),block(96,96))
        self.classifier=nn.Conv2d(96,6,1)

    def geometry(self,z,rgb,dsm,valid):
        n,ch,h,w=z.shape;k=c.CONFIG['geometry_kernel'];pad=k//2
        hmap=F.interpolate(dsm-dsm.mean((-2,-1),keepdim=True),size=(h,w),mode='area')
        good=F.interpolate(valid.float(),size=(h,w),mode='area')>.999
        if self.arm=='G3':
            shifts=tuple(c.CONFIG['mismatch_roll_grid_px']);hmap=torch.roll(hmap,shifts,(-2,-1));good=torch.roll(good,shifts,(-2,-1))
        # Replication avoids artificial zero-height edges; masks disable invalid pairs.
        def neighbours(x):return F.unfold(F.pad(x,(pad,pad,pad,pad),mode='replicate'),k).reshape(n,x.shape[1],k*k,h,w)
        q=self.query(z)[:,:,None];keys=neighbours(self.key(z))
        affin=(q*keys).sum(1)/(16**.5)
        dh=(neighbours(hmap)-hmap[:,:,None]).abs()[:,0]
        allowed=neighbours(good.float())[:,0]*good.float()
        if self.arm=='G1':reliability=torch.ones_like(dh)
        else:
            # Observable agreement, never GT errors. No extra trainable capacity.
            grey=F.interpolate(rgb.mean(1,keepdim=True),size=(h,w),mode='area')
            dr=(neighbours(grey)-grey[:,:,None]).abs()[:,0]
            reliability=torch.exp(-4*(dh.clamp(0,1)-dr.clamp(0,1)).abs())
        weight=torch.softmax((affin-dh/c.CONFIG['geometry_temperature']*reliability).masked_fill(allowed<.5,-1e4),dim=1)
        result=(neighbours(z)*weight[:,None]).sum(2)
        return z+self.relation_out(result)

    def forward(self,feat,rgb,dsm,valid):
        size=rgb.shape[-2:];r=self.rgb(rgb)
        if self.arm=='B0':
            grey=rgb.mean(1,keepdim=True);aux=torch.cat((grey,grey-F.avg_pool2d(grey,3,1,1)),1)
        else:aux=torch.cat((dsm,valid.float()),1)
        a=self.aux(aux);f=F.interpolate(self.project(feat),size=r.shape[-2:],mode='bilinear',align_corners=False)
        z=self.fuse(torch.cat((f,r,a),1))
        if self.arm.startswith('G'):
            small=F.interpolate(z,size=(c.CONFIG['geometry_grid'],)*2,mode='area')
            z=z+F.interpolate(self.geometry(small,rgb,dsm,valid)-small,size=z.shape[-2:],mode='bilinear',align_corners=False)
        if self.arm.startswith('S'):
            grey=rgb.mean(1,keepdim=True);local_rgb=grey-F.avg_pool2d(grey,5,1,2)
            height=dsm-F.avg_pool2d(dsm,5,1,2)
            if self.arm=='S1':second=F.avg_pool2d(local_rgb,3,1,1)
            else:
                if self.arm=='S3':height=torch.roll(height,(136,184),(-2,-1))
                second=height
            guide=F.interpolate(torch.cat((local_rgb,second),1),size=z.shape[-2:],mode='area')
            z=self.refine(z+self.guide(guide))
        return F.interpolate(self.classifier(z).float(),size=size,mode='bilinear',align_corners=False)

class SpatialProbe(nn.Module):
    def __init__(self):
        super().__init__();self.net=nn.Sequential(nn.Conv2d(384,48,1),nn.GELU(),
            nn.Conv2d(48,48,3,padding=1,groups=48),nn.GELU(),nn.Conv2d(48,6,1))
    def forward(self,x):return self.net(x)
