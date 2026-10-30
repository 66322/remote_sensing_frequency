"""Bind frozen original U masks for matched extra evaluation; zero training."""
import argparse
from pathlib import Path
from post_n3_s1_common import *
from post_n2_diag_runtime import input_contract
from prepare_post_n5_cross import decode_mask
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args()
    root,base=directories(a.root,a.directory);p=read(base/'plan.json');validate_plan(p);verify_snapshot(base);input_contract(root,p)
    provenance=released(root);source=root/'records'/CROSS_NAME;original=read(source/'mask_manifest.json');tiles={}
    for tile in p['data']['validation']:
        row=original['tiles'][tile]['U'];mask=decode_mask(row,source)
        target=base/'masks'/tile/'U.npz';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(Path(row['path']).read_bytes())
        tiles[tile]={'U':dict(row,path=str(target),source_mask=dict(path=row['path'],sha256=row['sha256']))}
        write(base/'preparation_progress.json',dict(tile=tile,observed_at=now()));del mask
    write(base/'mask_manifest.json',dict(plan_sha256=sha(base/'plan.json'),tiles=tiles,source_manifest_sha256=sha(source/'mask_manifest.json'),T_read=False))
    write(base/'preparation_complete.json',dict(plan_sha256=sha(base/'plan.json'),mask_manifest_sha256=sha(base/'mask_manifest.json'),predecessors=provenance,optimizer_updates=0,observed_at=now()))
if __name__=='__main__':main()
