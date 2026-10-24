"""CPU-only E/C/D: reuse exact labels and persist integer supports for every mask."""
import argparse
from pathlib import Path
import numpy as np
from phase15_common import *
from phase15_numeric import *
from prepare_phase15 import old_prediction, load_mask, checked_array


def current(base,c,name='prediction'):
    row=read(base/'cases'/(case_id(c)+'.json'))
    if row['binding'] != binding(base):
        raise RuntimeError('analysis case binding differs')
    with np.load(checked_array(row['arrays'][name]),allow_pickle=False) as z:
        return z['value']


def main(base,phase):
    p=validate(base)
    verify_code(base)
    from post_ab_n1_data import Loader
    loader=Loader(Path(p['root']),read(base/'source_plan.json'))
    rows={}
    for tile in TILES:
        item=loader(tile,True)
        gt=item['noboundary_gt']
        clean=old_prediction(base,'S1',tile)
        dsm=current(base,case('DSM',tile)) if phase=='D' else None
        fields = {}
        if phase=='D':
            thresholds=read(base/'calibration.json')['thresholds']
            for name in ('dsm_mean','dsm_variance','dsm_gradient'):
                f=base/'features'/tile/(name+'.npz')
                with np.load(f,allow_pickle=False) as z:
                    fields[name]=np.digitize(z['value'],thresholds[name]).astype(np.uint8)
        for i in range(1,21):
            for family in (FAMILIES[1:] if phase=='E' else FAMILIES):
                name=f'{tile}_{i:02d}_{family}'
                target=base/'analysis'/phase/(name+'.json')
                if target.exists():
                    raise RuntimeError('preserve partial CPU analysis; no automatic retry')
                mask,mb=load_mask(base,tile,i,family)
                s1=old_prediction(base,'S1',tile,i,family)
                if phase=='E':
                    result=profile(gt,clean,s1,mask)
                else:
                    predictions=[s1,current(base,case('S13',tile,'intact',i,family)),current(base,case('R16',tile,'intact',i,family)),
                                 dsm,old_prediction(base,'RGB',tile,i,family)]
                    entropy=current(base,case('S1',tile,'intact',i,family),'entropy')
                    op=item['optical'].copy();op[mask]=0
                    from scipy.ndimage import uniform_filter
                    zero=uniform_filter(np.all(op==0,axis=-1).astype(np.float32),size=9,mode='reflect')
                    fields['rgb_zero_fraction']=np.digitize(zero,(.25,.5,.75)).astype(np.uint8)
                    result=oracle_evidence(gt,clean,predictions,mask,entropy,fields)
                write(target,dict(binding=binding(base),tile=tile,realization=i,family=family,
                    mask_sha256=mb['canonical_sha256'],result=result,optimizer_updates=0,observed_at=now()))
                rows[name]=sha(target)
                write(base/'analysis'/phase/'progress.json',dict(completed_cases=len(rows),tile=tile,realization=i,family=family,observed_at=now()))
    write(base/'analysis'/phase/'complete.json',dict(binding=binding(base),records=rows,optimizer_updates=0,completed_at=now()))


if __name__=='__main__':
    a=argparse.ArgumentParser()
    a.add_argument('--directory',type=Path,required=True)
    a.add_argument('--phase',choices=('E','D'),required=True)
    x=a.parse_args()
    main(x.directory.resolve(),x.phase)
