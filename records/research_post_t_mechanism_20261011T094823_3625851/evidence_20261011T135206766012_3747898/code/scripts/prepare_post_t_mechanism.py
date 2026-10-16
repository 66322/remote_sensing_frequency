"""CPU binding only; no reads from a still-running predecessor worker."""
import argparse
from pathlib import Path
from post_t_mechanism_common import *
from post_n2_diag_runtime import input_contract
def prepare(root,base):
    p=validate(read(base/'plan.json'));verify_snapshot(base);input_contract(root,p)
    write(base/'predecessor_acceptance.json',inspect_predecessor(root,p,accept=True))
    pred=Path(p['predecessor_directory']);source=read(pred/'mask_manifest.json');tiles={}
    for t in p['data']['validation']:
        tiles[t]={}
        for rule,row in source['tiles'][t].items():
            old=within(row['path'],pred)
            if sha(old)!=row['sha256']:raise RuntimeError('mask changed')
            target=base/'masks'/t/(rule+'.npz');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(old.read_bytes())
            tiles[t][rule]=dict(row,path=str(target),source_path=str(old))
    write(base/'mask_manifest.json',dict(plan_sha256=sha(base/'plan.json'),tiles=tiles,source_manifest_sha256=sha(pred/'mask_manifest.json'),T_read=False))
    index={}
    for name,row in read(pred/'reference_index.json').items():
        old=within(row['path'],pred)
        if sha(old)!=row['sha256']:raise RuntimeError('reference changed')
        target=base/'references'/(name+'.json');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(old.read_bytes())
        index[name]=dict(row,path=str(target),sha256=sha(target))
    write(base/'reference_index.json',index)
    write(base/'preparation_complete.json',dict(plan_sha256=sha(base/'plan.json'),mask_manifest_sha256=sha(base/'mask_manifest.json'),reference_index_sha256=sha(base/'reference_index.json'),optimizer_updates=0))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();prepare(*dirs(a.root,a.directory))
if __name__=='__main__':main()
