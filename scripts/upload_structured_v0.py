"""Explicit light evidence upload after completion; arrays stay on server."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from structured_v0_common import *
from upload_post_t_paired_v2 import encode_record, git


def main(base,root,prepare_only):
    base=base.resolve();root=root.resolve()
    root.relative_to(Path('/home/jovyan/zzx'));base.relative_to(root/'records')
    p=validate(base);verify_code(base)
    state=read(base/'queue_status.json')
    from d30_common import live_owned,lock_free
    if state['status']!='STRUCTURED_COMPLETE_AWAITING_REVIEW' or any(r['status']!='COMPLETE' for r in state['jobs'].values()):
        raise RuntimeError('complete queue required')
    if live_owned(state.get('controller_pid',-1),base) or any(live_owned(r.get('pid',-1),base) for r in state['jobs'].values()) or not lock_free(base):
        raise RuntimeError('wait for controller and worker exit')
    if sha(base/'summary.json')!=state['summary_sha256']:
        raise RuntimeError('summary changed')
    for job in JOBS:
        accept(base,job)
    data={};sources=[];artifacts=[]
    for f in sorted(base.rglob('*')):
        if not f.is_file() or any(x.startswith('github_upload_') for x in f.relative_to(base).parts):
            continue
        name=f.relative_to(base).as_posix()
        if f.suffix=='.npz':
            artifacts.append(dict(path=str(f),bytes=f.stat().st_size,sha256=sha(f),storage='server_only'))
        elif f.suffix in ('.json','.jsonl','.log','.py','.md','.txt') and not name.startswith(('cache/','temporary/')):
            raw=f.read_bytes();raw.decode('utf-8')
            encoded=encode_record(raw) if f.suffix in ('.json','.jsonl') else raw
            data[name]=encoded
            sources.append(dict(path=name,original_bytes=len(raw),original_sha256=hashlib.sha256(raw).hexdigest(),encoded=raw!=encoded))
    for tile,groups in read(base/'mask_manifest.json')['tiles'].items():
        for families in groups.values():
            for row in families.values():
                if sha(row['path'])!=row['file_sha256']:
                    raise RuntimeError('mask archive changed')
    data['server_artifact_index.json']=(json.dumps(dict(artifacts=artifacts),indent=2)+'\n').encode()
    total=sum(map(len,data.values()))
    print('STRUCTURED_LIGHT_BYTES',total,'FILES',len(data),'ARRAYS_SERVER_ONLY',len(artifacts),flush=True)
    if total>512*1024**2:
        raise RuntimeError('light evidence exceeds fixed limit')
    if prepare_only:
        return
    origin=git(root,'remote','get-url','origin',capture=True).strip()
    if origin not in ('https://github.com/66322/remote_sensing_frequency','https://github.com/66322/remote_sensing_frequency.git','git@github.com:66322/remote_sensing_frequency.git'):
        raise RuntimeError('unexpected origin')
    branch='rebuild-v1-protocol-20260915'
    git(root,'fetch','origin',branch)
    parent=git(root,'rev-parse','FETCH_HEAD',capture=True).strip()
    stamp=datetime.now().strftime('%Y%m%dT%H%M%S%f')+'_'+str(os.getpid())
    work=base/('github_upload_'+stamp)
    git(root,'worktree','add','--detach',str(work),parent)
    relative=Path('records')/base.name/('evidence_'+stamp)
    manifest=dict(files=[dict(path=n,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in data.items()],
        source_files=sources,record_encoding='gzip-base64-exact-v1',server_directory=str(base),arrays_uploaded=False,optimizer_updates=0)
    data['upload_manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    paths=[]
    for n,b in data.items():
        f=work/relative/n;f.parent.mkdir(parents=True,exist_ok=True)
        with f.open('xb') as h:h.write(b)
        paths.append((relative/n).as_posix())
    # Batch explicit paths to avoid OS command-line limits; never stage the worktree wholesale.
    for start in range(0,len(paths),150):
        git(work,'add','-f','--',*paths[start:start+150])
    git(work,'-c','user.name=66322','-c','user.email=57258129+66322@users.noreply.github.com','commit','-m','records: upload structured failure v0 fixed inference evidence')
    commit=git(work,'rev-parse','HEAD',capture=True).strip()
    git(work,'push','origin','HEAD:refs/heads/'+branch)
    print('STRUCTURED_GITHUB_COMMIT='+commit)
    print('STRUCTURED_GITHUB_RECORDS=https://github.com/66322/remote_sensing_frequency/tree/'+commit+'/'+relative.as_posix())


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',type=Path,required=True);a.add_argument('--root',type=Path,required=True);a.add_argument('--prepare-only',action='store_true')
    args=a.parse_args();main(args.directory,args.root,args.prepare_only)
