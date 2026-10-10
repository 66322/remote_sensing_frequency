"""Six matched relation arms initialized from the fixed N1-2 selected state."""
import contextlib,hashlib
import torch
from torch.nn import functional as F
from model.rebuild_v1_post_ab_n1 import N1Segmenter
from model.post_ab_n2_relation import RelationPropagation,MODES
from model.rebuild_v1_d26 import valid_at

class N2Segmenter(N1Segmenter):
    def __init__(self,rgb_expert,dsm_expert,job,teacher=None):
        if job['id'] not in [f'N2-{i}' for i in range(6)] or job['relation_mode']!=MODES[int(job['id'].split('-')[1])]:
            raise ValueError('unregistered N2 arm')
        legacy=dict(job,id='N1-2',information_entry='late',adaptation='last4_and_heads')
        super().__init__(rgb_expert,dsm_expert,legacy,teacher)
        path=job['initial_checkpoint_path']
        h=hashlib.sha256()
        with open(path,'rb') as f:
            for chunk in iter(lambda:f.read(8*1024**2),b''):h.update(chunk)
        if h.hexdigest()!=job['initial_checkpoint_sha256']:raise RuntimeError('matched N1-2 base changed')
        state=torch.load(path,map_location='cpu',weights_only=False)
        if state['global_step']!=8000:raise RuntimeError('matched N1-2 selected age differs')
        self.load_state_dict(state['model'],strict=True)
        del state
        self.job=job;self.relation=RelationPropagation(job['relation_mode'])

    def forward(self,rgb,dsm,rgb_mask,dsm_mask,return_parts=False):
        if rgb_mask.shape!=dsm.shape or dsm_mask.shape!=dsm.shape or rgb_mask.dtype!=torch.bool or dsm_mask.dtype!=torch.bool:
            raise ValueError('aligned boolean availability masks required')
        rgb=rgb.masked_fill(~rgb_mask[:,None],0);dsm=dsm.masked_fill(~dsm_mask,0)
        self.taps={'rgb':{},'dsm':{}}
        rlog,rf=self.rgb_expert(rgb,dsm);dlog,df=self.dsm_expert(rgb,dsm)
        shape=((rgb.shape[-2]+3)//4,(rgb.shape[-1]+3)//4)
        try:
            r=self.pyramid('rgb',rf,rgb,rgb_mask,shape)
            d=self.pyramid('dsm',df,rgb,dsm_mask,shape)
        finally:self.taps={'rgb':{},'dsm':{}}
        both=valid_at(rgb_mask,shape).bool()[:,0] & valid_at(dsm_mask,shape).bool()[:,0]
        r,d=self.relation(r,d,dsm,both)
        raw=F.interpolate(self.fusion(torch.cat((r,d,r,d),1)),rgb.shape[-2:],mode='nearest')
        valid=rgb_mask|dsm_mask
        result=torch.where((rgb_mask&dsm_mask)[:,None],raw,torch.where(rgb_mask[:,None],rlog,dlog)).masked_fill(~valid[:,None],0)
        parts=dict(logits=result,rgb=rlog,dsm=dlog,raw=raw,valid=valid)
        return parts if return_parts else result
