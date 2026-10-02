"""Four locked pressure diagnostics; never used for selection."""
import torch
from torch.nn import functional as F
import d23_engine as e

EXTRA=('rgb_down4+aux_zero','rgb_down4+aux_noise_std010',
       'aux_local_zero_center_quarter','aux_shift24')

def treatment(op,ds,kind,seed,numpy_noise=False):
    if kind not in EXTRA:
        return e.treatment(op,ds,kind,seed,numpy_noise=numpy_noise)
    if kind.startswith('rgb_down4+'):
        op,ds,_=e.treatment(op,ds,'rgb_down4',seed)
        return e.treatment(op,ds,kind.split('+')[1],seed)
    op,ds=op.clone(),ds.clone()
    mask=torch.ones_like(ds,dtype=torch.bool)
    h,w=ds.shape[-2:]
    if kind=='aux_local_zero_center_quarter':
        ds[:,3*h//8:5*h//8,:]=0
        mask[:,3*h//8:5*h//8,:]=False
    else:
        ds=F.pad(ds[:,None],(24,0,0,0),mode='replicate')[:,0,:,:w]
    return op,ds,mask
