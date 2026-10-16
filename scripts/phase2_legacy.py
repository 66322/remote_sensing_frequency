"""Zero-GPU Phase2.0 decomposition exclusively from previously completed counts."""
import argparse
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from phase2_common import *

def run(base):
    p=verify(base);old=Path(p['previous']);done=read(old/'analysis/D/complete.json')
    prior={n:sha(old/n) for n in ('plan.json','code_manifest.json','preparation_complete.json')}
    if done['binding']!=prior or len(done['records'])!=160:raise RuntimeError('old D completion differs')
    def fetch(item):
        name,h=item;f=old/'analysis/D'/(name+'.json')
        if sha(f)!=h:raise RuntimeError('old D record changed')
        row=read(f)
        if row['binding']!=prior:raise RuntimeError('old D source binding differs')
        return row
    hist=defaultdict(lambda:np.zeros((6,32),np.int64))
    with ThreadPoolExecutor(max_workers=read(Path(base)/'resource_profile.json')['analysis_workers']) as pool:
        for row in pool.map(fetch,done['records'].items()):
            for region,value in row['result']['joint_correct_by_class'].items():
                hist[(row['tile'],row['family'],region)]+=np.asarray(value,np.int64)
    codes=np.arange(32);decomposition={}
    for (tile,family,region),matrix in hist.items():
        decomposition['/'.join((tile,family,region))]=dict(raw_6x32=matrix.tolist(),total_by_class=matrix.sum(1).tolist(),
            correct_by_expert={n:matrix[:,(codes&(1<<i))!=0].sum(1).tolist() for i,n in enumerate(('S1','S13','R16','DSM','RGB'))},
            any_five_correct_by_class=matrix[:,codes!=0].sum(1).tolist(),
            legacy_exclusive_by_class=matrix[:,((codes&7)==0)&((codes&24)!=0)].sum(1).tolist())
    identity=[];dose=[]
    for f in sorted((old/'cases').glob('S1_*.json')):
        row=read(f);c=row['case']
        if c['family']=='clean':continue
        if row['binding']!=prior or row['own_logit_identity']['dsm_only'] is not True:
            raise RuntimeError('old internal identity differs')
        identity.append(dict(name=f.name,sha256=sha(f)))
        if c['dsm']=='intact' and c['family']=='pixel':
            dose.append(dict(case=c,sha256=sha(f),regions={region:row['scopes']['noboundary'][region]
                for region in ('all','missing','healthy','core5')}))
    if len(identity)!=720 or len(dose)!=120:raise RuntimeError('old identity/dose inventory differs')
    write(Path(base)/'analysis/legacy_decomposition.json',dict(source_binding=prior,old_D_records=160,
        internal_DSM_identity_receipts=720,identity_index_sha256=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest(),
        class_mask_expert_counts=decomposition,ratio_ROI_evidence=dose,optimizer_updates=0,
        interpretation='repeated masks on fixed two tiles; legacy experts are descriptive, no new GPU inference'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);run(p.parse_args().directory.resolve())
