"""Two independent experts, bidirectional feature interactions and known-mask fallback.

No labels, quality identifiers or estimated reliability enter forward.
"""
import contextlib
import torch
from torch import nn
from torch.nn import functional as F

ARMS=('J0','B0','CAP','X','XS','XF','XSF','XSF-shS','XSF-shF')

def shift(x):
    return torch.roll(x,(x.shape[-2]//2,x.shape[-1]//2),(-2,-1))

def pack(x,frequency=False):
    # Four polyphase blocks per channel. Zero padding also supports odd sizes.
    x=F.pad(x,(0,x.shape[-1]%2,0,x.shape[-2]%2))
    a,b,c,d=x[...,::2,::2],x[...,::2,1::2],x[...,1::2,::2],x[...,1::2,1::2]
    if frequency:a,b,c,d=(a+b+c+d)/2,(a-b+c-d)/2,(a+b-c-d)/2,(a-b-c+d)/2
    return torch.stack((a,b,c,d),2).flatten(1,2)

def unpack(x,shape,frequency=False):
    b,c,h,w=x.shape
    a,v,u,z=x.reshape(b,c//4,4,h,w).unbind(2)
    if frequency:a,v,u,z=(a+v+u+z)/2,(a-v+u-z)/2,(a+v-u-z)/2,(a-v-u+z)/2
    return F.pixel_shuffle(torch.stack((a,v,u,z),2).flatten(1,2),2)[...,:shape[0],:shape[1]]

def valid_at(mask,shape):
    return F.adaptive_avg_pool2d(mask[:,None].float(),shape)==1

def align_feature(feature,shape):
    if feature.shape[-2:]==shape:return feature
    h,w=feature.shape[-2:]
    if h%shape[0]==0 and w%shape[1]==0:
        return F.avg_pool2d(feature,(h//shape[0],w//shape[1]))
    return F.interpolate(feature,shape,mode='nearest')

class Expert(nn.Module):
    """A pre-classifier hook preserves the original complete forward and logits."""
    def __init__(self,net,classifier,kind):
        super().__init__();self.net=net;self.kind=kind;self.feature=None
        classifier.register_forward_pre_hook(self.capture)
        self.channels=classifier.in_channels
    def capture(self,module,args):self.feature=args[0]
    def forward(self,rgb,dsm):
        logits=self.net(rgb,dsm) if self.kind=='rgb' else self.net(dsm[:,None].repeat(1,3,1,1))
        feature=self.feature;self.feature=None
        if feature is None or logits.shape[1]!=6:raise RuntimeError('expert feature/logit interface failed')
        return logits,feature
    def configure(self,joint):
        self.requires_grad_(False)
        if joint:
            net=self.net
            blocks=net.encoder.blocks if self.kind=='rgb' else net.transformer.encoder.layer
            for block in blocks[-4:]:block.requires_grad_(True)
            net.decoder.requires_grad_(True)
            if self.kind=='rgb':net.rgb.requires_grad_(True)
            else:net.segmentation_head.requires_grad_(True)
        self.eval()
    def train(self,mode=True):
        # Frozen early dropout and all BN statistics stay in evaluation mode.
        super().train(False)
        if mode:
            for module in self.net.modules():
                if not isinstance(module,nn.modules.batchnorm._BatchNorm) and any(p.requires_grad for p in module.parameters(recurse=False)):
                    module.training=True
        return self

class Interaction(nn.Module):
    def __init__(self,channels=128):
        super().__init__()
        self.mix=nn.Conv2d(channels*8,channels*2,3,padding=1,groups=4)
        self.condition=nn.Conv2d(18,channels*2,1)
        self.out=nn.Conv2d(channels*2,channels*4,1,groups=4)
        self.gate=nn.Conv2d(channels*2,channels*4,1,groups=4)
    def forward(self,receiver,donor,condition,valid,frequency=False,shuffle_high=False):
        a,b=pack(receiver,frequency),pack(donor,frequency)
        vm=F.avg_pool2d(F.pad(valid.float(),(0,valid.shape[-1]%2,0,valid.shape[-2]%2)),2)==1
        if shuffle_high:
            bands=b.reshape(b.shape[0],-1,4,*b.shape[-2:])
            b=torch.cat((bands[:,:,0:1],shift(bands[:,:,1:])),2).flatten(1,2)
            vm=vm & shift(vm)
        # Every 3x3 coefficient neighborhood must be valid in both modalities.
        safe=F.max_pool2d((~vm).float(),3,1,1)==0
        # Fixed reduction supports deterministic CUDA backward for noS slots.
        cond=F.avg_pool2d(F.pad(condition,(0,condition.shape[-1]%2,0,condition.shape[-2]%2)),2)
        # Interleave recipient/donor coefficients so each convolution group sees both.
        pair=torch.stack((a,b),2).flatten(1,2)
        h=F.gelu(self.mix(pair)+self.condition(cond))
        increment=self.out(h)*torch.sigmoid(self.gate(h))*safe
        return unpack(increment,receiver.shape[-2:],frequency)*valid

class D26Segmenter(nn.Module):
    def __init__(self,rgb_expert,dsm_expert,arm):
        super().__init__()
        if arm not in ARMS:raise ValueError(arm)
        self.arm=arm;self.rgb_expert=rgb_expert;self.dsm_expert=dsm_expert
        for expert in (rgb_expert,dsm_expert):expert.configure(arm=='J0')
        self.project_rgb=nn.Conv2d(rgb_expert.channels,128,1)
        self.project_dsm=nn.Conv2d(dsm_expert.channels,128,1)
        self.fusion=nn.Sequential(nn.Conv2d(512,128,3,padding=1),nn.GroupNorm(8,128),nn.GELU(),nn.Conv2d(128,6,1))
        self.interactions=None if arm in ('J0','B0') else nn.ModuleList([Interaction() for _ in range(4)])
    def forward(self,rgb,dsm,rgb_mask,dsm_mask,return_parts=False):
        if rgb_mask.shape!=dsm.shape or dsm_mask.shape!=dsm.shape or rgb_mask.dtype!=torch.bool or dsm_mask.dtype!=torch.bool:
            raise ValueError('two aligned boolean masks required')
        rgb=rgb.masked_fill(~rgb_mask[:,None],0);dsm=dsm.masked_fill(~dsm_mask,0)
        with contextlib.nullcontext() if self.arm=='J0' else torch.no_grad():
            rlog,rf=self.rgb_expert(rgb,dsm);dlog,df=self.dsm_expert(rgb,dsm)
        shape=((rgb.shape[-2]+3)//4,(rgb.shape[-1]+3)//4)
        r=self.project_rgb(align_feature(rf,shape))
        d=self.project_dsm(align_feature(df,shape))
        rm,dm=valid_at(rgb_mask,shape),valid_at(dsm_mask,shape)
        r,d=r*rm,d*dm
        dr,rd=torch.zeros_like(r),torch.zeros_like(d)
        if self.interactions is not None:
            frequency=self.arm in ('XF','XSF','XSF-shS','XSF-shF')
            semantic=self.arm in ('XS','XSF','XSF-shS','XSF-shF')
            if semantic:
                rp=align_feature(rlog.detach().float().softmax(1),shape)*rm
                dp=align_feature(dlog.detach().float().softmax(1),shape)*dm
            else:rp,dp=r[:,:6],d[:,:6]
            condition=torch.cat((rp,dp,(rp-dp).abs()),1)
            cv=rm & dm
            if self.arm=='XSF-shS':condition=shift(condition);cv=cv & shift(cv)
            for scale in range(2):
                rs,ds=r,d
                vr,vd=rm,dm
                cs=condition;vs=cv
                if scale:
                    rs,ds=F.avg_pool2d(r,2),F.avg_pool2d(d,2)
                    vr,vd=F.avg_pool2d(rm.float(),2)==1,F.avg_pool2d(dm.float(),2)==1
                    cs=F.avg_pool2d(condition,2);vs=F.avg_pool2d(cv.float(),2)==1
                if self.arm=='CAP':
                    # Same learned blocks, each sees only its own modality.
                    cr=torch.cat((rs[:,:6],rs[:,6:12],rs[:,12:18]),1)
                    cd=torch.cat((ds[:,:6],ds[:,6:12],ds[:,12:18]),1)
                    ir=self.interactions[scale*2](rs,rs,cr,vr)
                    idm=self.interactions[scale*2+1](ds,ds,cd,vd)
                else:
                    ir=self.interactions[scale*2](rs,ds,cs,vs,frequency,self.arm=='XSF-shF')
                    idm=self.interactions[scale*2+1](ds,rs,cs,vs,frequency,self.arm=='XSF-shF')
                dr=dr+F.interpolate(ir,shape,mode='nearest')/2
                rd=rd+F.interpolate(idm,shape,mode='nearest')/2
        raw=F.interpolate(self.fusion(torch.cat((r,d,r+dr,d+rd),1)),rgb.shape[-2:],mode='nearest')
        valid=rgb_mask | dsm_mask
        result=torch.where((rgb_mask & dsm_mask)[:,None],raw,torch.where(rgb_mask[:,None],rlog,dlog))
        result=result.masked_fill(~valid[:,None],0)
        return dict(logits=result,rgb=rlog,dsm=dlog,valid=valid,raw=raw,dr=dr,rd=rd) if return_parts else result

def build_experts(root,states):
    """Imports are delayed so synthetic tests do not need legacy dependencies."""
    import copy,json
    from model.rebuild_v1_d25 import D25Segmenter
    from model.rebuild_v1_optical_only import VisionTransformerOpticalOnly
    from model.vitcross_seg_modeling_freqfusion import CONFIGS
    cfg=json.loads((root/'configs/rebuild_v1/d18_d19_night_20260927.json').read_text())['dino']
    encoder=torch.hub.load(str(root/cfg['repository_dir']),'dinov2_vits14',source='local',pretrained=False)
    rgb=D25Segmenter(encoder,'shared',True);rgb.detail=None
    rgb.load_state_dict(states['rgb'],strict=True)
    config=copy.deepcopy(CONFIGS['R50-ViT-B_16']);config.n_classes=6;config.n_skip=3;config.patches.grid=(32,32)
    dsm=VisionTransformerOpticalOnly(config,img_size=512,num_classes=6)
    dsm.load_state_dict(states['dsm'],strict=True)
    return Expert(rgb,rgb.decoder[-1],'rgb'),Expert(dsm,dsm.segmentation_head[0],'dsm')
