"""Bind completed predecessor evidence and copy small fixed masks, CPU only."""
import argparse
from pathlib import Path
from post_s1_transfer_common import *
from post_n2_diag_runtime import input_contract

def prepare(root,base):
    p=validate(read(base/'plan.json'));verify_snapshot(base);input_contract(root,p)
    acceptance=inspect_predecessor(root,p,accept=True);write(base/'predecessor_acceptance.json',acceptance)
    pred=Path(p['predecessor_directory']);manifest=read(pred/'mask_manifest.json');tiles={}
    for tile in p['data']['validation']:
        tiles[tile]={}
        for rule,row in manifest['tiles'][tile].items():
            path=within(row['path'],pred)
            if sha(path)!=row['sha256']:raise RuntimeError('predecessor mask changed')
            new=base/'masks'/tile/(rule+'.npz');new.parent.mkdir(parents=True,exist_ok=True);new.write_bytes(path.read_bytes())
            tiles[tile][rule]=dict(row,path=str(new),source_path=str(path))
    write(base/'mask_manifest.json',dict(plan_sha256=sha(base/'plan.json'),tiles=tiles,
        source_manifest_sha256=sha(pred/'mask_manifest.json'),T_read=False,E_reused_development=True))
    # Embed light references. Predictions remain at the immutable accepted source and are checked at use.
    refs={'base_ordinary':root/'records'/SOURCE_NAME/'jobs/S1-0/evaluation/summary.json',
          'base_U':root/'records'/SOURCE_NAME/'jobs/S1-0/support_evaluation/summary.json',
          'R0_U':pred/'R0_U/summary.json','R0_ordinary':pred/'R0_ordinary/summary.json',
          'P7_U':pred/'jobs/P7/support_evaluation/summary.json'}
    e=read(pred/'jobs/E/summary.json')
    for name in ('S1-0','S1-3','R0','P7'):
        row=e['records'][name];path=within(row['path'],pred)
        if sha(path)!=row['sha256']:raise RuntimeError('E reference changed')
        refs['E_'+name]=path
    index={}
    for name,path in refs.items():
        target=base/'references'/(name+'.json');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(path.read_bytes())
        index[name]=dict(path=str(target),sha256=sha(target),source_path=str(path),source_sha256=sha(path))
    write(base/'reference_index.json',index)
    write(base/'preparation_complete.json',dict(plan_sha256=sha(base/'plan.json'),mask_manifest_sha256=sha(base/'mask_manifest.json'),
        reference_index_sha256=sha(base/'reference_index.json'),predecessor_acceptance_sha256=sha(base/'predecessor_acceptance.json'),optimizer_updates=0,observed_at=now()))
    print('TRANSFER_PREPARATION_COMPLETE',flush=True)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();prepare(*dirs(a.root,a.directory))
if __name__=='__main__':main()
