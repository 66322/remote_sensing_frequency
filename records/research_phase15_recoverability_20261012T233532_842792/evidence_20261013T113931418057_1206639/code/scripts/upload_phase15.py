"""Explicit foreground light upload; includes failure/smoke originals, no compute."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from phase15_common import *
from upload_post_t_paired_v2 import encode_record,git


def main(base,root,prepare_only=False):
    root=within(root,'/home/jovyan/zzx');base=within(base,root/'records')
    validate(base);verify_code(base)
    from d30_common import live_owned,lock_free
    s=read(base/'queue_status.json')
    if s['status'] not in ('PHASE15_COMPLETE_AWAITING_REVIEW','SMOKE_FAILED_HOLD','TECHNICAL_FAILURE_HOLD','HOLD_REGISTRATION'):
        raise RuntimeError('only complete/held evidence, no mutable running snapshot')
    if live_owned(s.get('controller_pid',-1),base) or any(live_owned(r.get('pid',-1),base) for r in s['jobs'].values()):
        raise RuntimeError('wait for all owned processes to exit')
    if (base/'controller.lock').exists() and not lock_free(base):raise RuntimeError('controller lock held')
    if s['status']=='PHASE15_COMPLETE_AWAITING_REVIEW':
        if sha(base/'summary.json')!=s['summary_sha256']:raise RuntimeError('summary changed')
        for j in jobs():accept_job(base,j)
    data={};sources=[];arrays=[]
    for f in sorted(base.rglob('*')):
        name=f.relative_to(base).as_posix()
        if not f.is_file() or any(x.startswith('github_upload_') for x in f.relative_to(base).parts) or name.startswith(('cache/','temporary/')):
            continue
        if f.suffix in ('.npz','.npy','.png','.svg'):
            arrays.append(dict(path=str(f),bytes=f.stat().st_size,sha256=sha(f),storage='server_only'));continue
        if f.suffix not in ('.json','.jsonl','.log','.py','.md','.txt'):continue
        raw=f.read_bytes();raw.decode('utf-8')
        encoded=encode_record(raw) if f.suffix in ('.json','.jsonl') else raw
        data[name]=encoded;sources.append(dict(path=name,original_bytes=len(raw),original_sha256=hashlib.sha256(raw).hexdigest(),encoded=raw!=encoded))
    data['server_artifact_index.json']=(json.dumps(dict(artifacts=arrays),indent=2)+'\n').encode()
    total=sum(map(len,data.values()))
    if total>512*1024**2 or any(len(v)>32*1024**2 for v in data.values()):raise RuntimeError('light archive bound exceeded; preserve all evidence')
    print('PHASE15_LIGHT_BYTES',total,'FILES',len(data),'ARRAYS_SERVER_ONLY',len(arrays))
    if prepare_only:return
    origin=git(root,'remote','get-url','origin',capture=True).strip()
    if origin not in ('https://github.com/66322/remote_sensing_frequency','https://github.com/66322/remote_sensing_frequency.git','git@github.com:66322/remote_sensing_frequency.git'):
        raise RuntimeError('unexpected repository')
    branch='rebuild-v1-protocol-20260915';git(root,'fetch','origin',branch)
    parent=git(root,'rev-parse','FETCH_HEAD',capture=True).strip()
    stamp=datetime.now().strftime('%Y%m%dT%H%M%S%f')+'_'+str(os.getpid())
    work=base/('github_upload_'+stamp);git(root,'worktree','add','--detach',str(work),parent)
    relative=Path('records')/base.name/('evidence_'+stamp)
    manifest=dict(files=[dict(path=n,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in data.items()],
        source_files=sources,record_encoding='gzip-base64-exact-v1',server_directory=str(base),arrays_uploaded=False,
        optimizer_updates=0,queue_status=s['status'])
    data['upload_manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    paths=[]
    for n,b in data.items():
        f=work/relative/n;f.parent.mkdir(parents=True,exist_ok=True)
        with f.open('xb') as h:h.write(b)
        paths.append((relative/n).as_posix())
    for start in range(0,len(paths),150):git(work,'add','-f','--',*paths[start:start+150])
    git(work,'-c','user.name=66322','-c','user.email=57258129+66322@users.noreply.github.com','commit','-m','records: Phase1.5 zero-training evidence '+s['status'])
    commit=git(work,'rev-parse','HEAD',capture=True).strip();git(work,'push','origin','HEAD:refs/heads/'+branch)
    print('PHASE15_GITHUB_COMMIT='+commit)
    print('PHASE15_GITHUB_RECORDS=https://github.com/66322/remote_sensing_frequency/tree/'+commit+'/'+relative.as_posix())


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',type=Path,required=True);a.add_argument('--root',type=Path,required=True)
    a.add_argument('--prepare-only',action='store_true');x=a.parse_args();main(x.directory,x.root,x.prepare_only)
