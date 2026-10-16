"""Same clean crops; exactly quarter missing on matched native slots."""
import numpy as np
import torch
from pathlib import Path
from post_ab_n1_data import objective
from post_d30_data import Crops as Original,materialize_shift
from d24_data import Loader,PrefetchedBatches
from d26_data import views
import d23_engine as e
from post_n2_diag_common import read,sha
from post_n5_common import MASK_CONTRACT,CROP_CONTRACT
from post_n2_masks import quarter_mask,scores
def make_mask(item,rule,tile):
    fields=scores(item['optical'],item['dsm'],5) if rule!='U' else {}
    if rule=='T':
        # Exact H geometry and argmax, with luminance local std as score.
        return quarter_mask(item['dsm'].shape,'H',fields['L'],tile)
    return quarter_mask(item['dsm'].shape,rule,fields.get(rule),tile)
def load_mask(base,tile,rule):
    row=read(Path(base)/'mask_manifest.json')['tiles'][tile][rule];path=Path(row['path'])
    path.resolve().relative_to(Path(base).resolve())
    if sha(path)!=row['sha256']:raise RuntimeError('mask SHA differs')
    with np.load(path,allow_pickle=False) as z:
        shape=tuple(int(x) for x in z['shape']);mask=np.unpackbits(z['bits'],bitorder='little',count=int(np.prod(shape))).reshape(shape).astype(bool)
    if int(mask.sum())*4!=mask.size:raise RuntimeError('mask area differs')
    return mask,row
def rule_at(job,step):
    if job=='N5-0':return None
    return CROP_CONTRACT['rules'][job][step%4]
def native_roi(tile,spec):
    h,w=tile['dsm'].shape
    y=min(int(spec['fy']*((h-512)//128+1)),(h-512)//128)*128
    x=min(int(spec['fx']*((w-512)//128+1)),(w-512)//128)*128
    if min(h,w)<512:raise ValueError('tile too small')
    return y,x
def native_sample(tile,spec,missing=None):
    y,x=native_roi(tile,spec);p=512
    op=torch.from_numpy(np.ascontiguousarray(tile['optical'][y:y+p,x:x+p].transpose(2,0,1)))
    ds=torch.from_numpy(np.ascontiguousarray(tile['dsm'][y:y+p,x:x+p]));gt=torch.from_numpy(np.ascontiguousarray(tile['full_gt'][y:y+p,x:x+p]).astype(np.int64))
    m=None if missing is None else torch.from_numpy(np.ascontiguousarray(missing[y:y+p,x:x+p]))
    for flip,axis in ((spec['vflip'],-2),(spec['hflip'],-1)):
        if flip:
            op,ds,gt=(v.flip(axis) for v in (op,ds,gt))
            if m is not None:m=m.flip(axis)
    if m is not None and int(m.sum())!=65536:raise RuntimeError('native crop quarter area changed')
    return op,ds,gt,m
class Crops(Original):
    def __init__(self,tiles,ids,augmentation,plan,start=0,job=None,base=None):
        super().__init__(tiles,ids,augmentation,plan,start,job)
        self.masks={t:{r:load_mask(base,t,r)[0] for r in ('U','H','L')} for t in ids}
    def __getitem__(self,index):
        step,i=self.start+index//16,index%16
        if i<8:return super().__getitem__(index)
        spec=e.sample_spec(self.ids,e.key(42,'fit',step)*16+i,self.augmentation,512);spec['treatment']='clean'
        rule=rule_at(self.job['id'],step);missing=None if rule is None else self.masks[spec['tile']][rule]
        op,ds,gt,m=native_sample(self.cache[spec['tile']],spec,missing)
        if rule is None:op2,ds2,rm,dm,kind=views(op,ds,self.plan,step,i)
        else:
            op2,ds2=op[None].clone(),ds[None].clone();rm=torch.ones_like(ds2,dtype=torch.bool);dm=rm.clone()
            direction='rgb' if i%2==0 else 'dsm'
            if direction=='rgb':op2=op2.masked_fill(m[None,None],0);rm=~m[None]
            else:ds2=ds2.masked_fill(m[None],0);dm=~m[None]
            kind='N5_'+direction+'_'+rule
        return dict(rgb=op,aux=ds,gt=gt,rgb2=op2[0],aux2=ds2[0],rm2=rm[0],dm2=dm[0],treatment=kind+';geom=(0, 0)')

