"""All four cells share identical crops, availability and auxiliary CE."""
import torch
from post_d30_data import Loader,Crops,PrefetchedBatches,treatment
from d26_data import ce

def objective(model,batch):
    full=torch.ones_like(batch['gt'],dtype=torch.bool);terms=[];counts={}
    for tag,rgb,ds,rm,dm in (('clean',batch['rgb'],batch['aux'],full,full),('aug',batch['rgb2'],batch['aux2'],batch['rm2'],batch['dm2'])):
        with torch.autocast(device_type=rgb.device.type,dtype=torch.bfloat16,enabled=rgb.is_cuda):
            parts=model(rgb,ds,rm,dm,return_parts=True)
        main,n=ce(parts['logits'],batch['gt'],rm|dm)
        r,nr=ce(parts['rgb'],batch['gt'],rm);d,nd=ce(parts['dsm'],batch['gt'],dm)
        terms.append(.5*main+.125*(r+d))
        counts.update({tag+'_fusion_pixels':n,tag+'_rgb_pixels':nr,tag+'_dsm_pixels':nd})
    return sum(terms),counts
