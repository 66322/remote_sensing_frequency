"""CPU preparation after registration freezes complete protocol; no training."""
import argparse
from pathlib import Path
import numpy as np
from post_n5_common import *
from post_n5_data import make_mask
from d24_data import Loader
from post_n2_diag_runtime import input_contract
def prepare(root,base):
    plan=read(base/'plan.json');validate(plan);verify_snapshot(base);input_contract(root,plan)
    loader=Loader(root,plan);tiles={}
    for tile in plan['data']['fit12']+plan['data']['validation']:
        item=loader(tile,tile in plan['data']['validation']);tiles[tile]={}
        # T never generated for fit12; validation T only after frozen plan exists.
        for rule in ('U','H','L','T') if tile in plan['data']['validation'] else ('U','H','L'):
            mask,boxes=make_mask(item,rule,tile);path=base/'masks'/tile/(rule+'.npz');path.parent.mkdir(parents=True,exist_ok=True)
            np.savez_compressed(path,bits=np.packbits(mask.ravel(),bitorder='little'),shape=np.array(mask.shape,np.int64))
            tiles[tile][rule]=dict(path=str(path),sha256=sha(path),shape=list(mask.shape),missing_pixels=int(mask.sum()),blocks=boxes)
            write(base/'preparation_progress.json',dict(tile=tile,rule=rule,observed_at=now()))
            del mask
        sigs=[[(b[2],b[3]) for b in tiles[tile][r]['blocks']] for r in tiles[tile]]
        if any(s!=sigs[0] for s in sigs):raise RuntimeError('paired geometry differs')
        print('N5_MASKS_COMPLETE',tile,flush=True);del item
    write(base/'mask_manifest.json',dict(plan_sha256=sha(base/'plan.json'),tiles=tiles,input_binding=loader.verified,T_generated_after_plan_freeze=True,T_training=False))
    write(base/'preparation_complete.json',dict(plan_sha256=sha(base/'plan.json'),mask_manifest_sha256=sha(base/'mask_manifest.json'),optimizer_updates=0,observed_at=now()))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args()
    root,base=directories(a.root,a.directory);prepare(root,base)
if __name__=='__main__':main()

