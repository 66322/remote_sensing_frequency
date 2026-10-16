"""D25 matched availability decoders. Forward accepts images and known mask only."""
import copy
import torch
from torch.nn import functional as F
from model.rebuild_v1_d24 import D24Segmenter
from model.rebuild_v1_d21_detail import detail_channels

class D25Segmenter(D24Segmenter):
    def __init__(self, encoder, decoder_mode='shared', optical_only=False):
        if decoder_mode not in ('shared','separate','average'):
            raise ValueError(decoder_mode)
        # Keep M0 structure until bound M0 weights are loaded.
        super().__init__(encoder, optical_only=False, last4=True, prototype=False)
        self.optical_only = optical_only
        self.decoder_mode = decoder_mode
        self.decoder_optical = None

    def initialize(self, state):
        self.load_state_dict(state, strict=True)
        if self.decoder_mode != 'shared':
            self.decoder_optical = copy.deepcopy(self.decoder)
        if self.optical_only:
            self.detail = None

    def shared_parameter_names(self):
        prefixes = ('encoder.', 'rgb.', 'decoder.', 'decoder_optical.') if self.decoder_mode != 'separate' else ('encoder.', 'rgb.')
        return {n for n,p in self.named_parameters() if p.requires_grad and n.startswith(prefixes)}

    def decode(self, feature, optical=False):
        if self.decoder_mode == 'average':
            return .5*(self.decoder(feature)+self.decoder_optical(feature))
        if optical and self.decoder_mode == 'separate':
            return self.decoder_optical(feature)
        return self.decoder(feature)

    def forward(self, rgb, aux, available=None, return_parts=False):
        h,w=rgb.shape[-2:]
        feature=self.encode(rgb)
        own=F.interpolate(self.decode(feature, optical=True),(h,w),mode='nearest')
        if self.optical_only:
            return (own,own,feature,torch.zeros_like(feature)) if return_parts else own
        if available is None or available.shape != aux.shape or available.dtype != torch.bool:
            raise ValueError('explicit boolean aligned availability required')
        pad=(0,(-w)%4,0,(-h)%4)
        low_mask=F.avg_pool2d(F.pad(available[:,None].float(),pad,mode='replicate'),4,4)==1
        secondary=self.detail(detail_channels(aux.masked_fill(~available,0),'M0'))*low_mask
        fused=F.interpolate(self.decode(feature+secondary),(h,w),mode='nearest')
        result=torch.where(available[:,None],fused,own)
        return (result,own,feature,secondary) if return_parts else result
