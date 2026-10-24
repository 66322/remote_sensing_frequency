"""Explicit interactive upload of D24 light records; never launches training."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

def git(root,*args,capture=False):
    return subprocess.run(['git','-C',str(root),*args],check=True,text=True,
                          stdout=subprocess.PIPE if capture else None).stdout

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--directory',type=Path,required=True);args=ap.parse_args()
    root=args.root.resolve();root.relative_to(Path('/home/jovyan/zzx').resolve())
    base=args.directory.resolve();base.relative_to(root/'records')
    if not base.name.startswith('research_d24_overnight_'):raise ValueError('unexpected directory')
    plan=json.loads((base/'plan.json').read_text())
    names=['plan.json','execution_commit.txt','code_manifest.json','queue_status.json','screen_result.json','results.csv']
    names+=[p.relative_to(base).as_posix() for p in base.glob('nohup*.log')]
    names+=[p.relative_to(base).as_posix() for p in (base/'logs').glob('*.log')]
    artifacts=[]
    for job in plan['jobs']:
        folder=base/'jobs'/job['id']
        if not folder.exists():continue
        names+=[p.relative_to(base).as_posix() for p in folder.rglob('*.json')]
        for path in folder.rglob('*.pth'):
            row=dict(path=str(path),bytes=path.stat().st_size,storage='server_only')
            if path.name=='selected.pth' and (folder/'complete.json').exists():
                row['sha256']=json.loads((folder/'complete.json').read_text())['selected_checkpoint_sha256']
            if path.name=='last_train_state.pth' and (folder/'complete.json').exists():
                row['sha256']=json.loads((folder/'complete.json').read_text()).get('last_checkpoint_sha256')
            artifacts.append(row)
        for record in (folder/'evaluation').glob('*/*.json'):
            row=json.loads(record.read_text())
            for name,digest in row.get('predictions',{}).items():
                path=record.parent/name/(row['tile']+'.npy')
                artifacts.append(dict(path=str(path),bytes=path.stat().st_size,sha256=digest,storage='server_only'))
    raw_index=(json.dumps(dict(server_directory=str(base),artifacts=artifacts),indent=2)+'\n').encode()
    data={'server_artifact_index.json':raw_index}
    for name in dict.fromkeys(names):
        path=(base/name).resolve();path.relative_to(base)
        if not path.is_file():continue
        raw=path.read_bytes();raw.decode('utf-8')
        if name.endswith('.json'):json.loads(raw)
        if len(raw)>20*1024**2:raise ValueError('unexpected oversized text record: '+name)
        data[name]=raw
    if sum(map(len,data.values()))>128*1024**2:raise ValueError('unexpected oversized light bundle')
    if not all(name in data for name in ('plan.json','execution_commit.txt','code_manifest.json','queue_status.json')):
        raise ValueError('queue provenance missing')
    origin=git(root,'remote','get-url','origin',capture=True).strip()
    if origin not in ('https://github.com/66322/remote_sensing_frequency.git',
                       'https://github.com/66322/remote_sensing_frequency',
                       'git@github.com:66322/remote_sensing_frequency.git'):
        raise ValueError('unexpected origin')
    branch='rebuild-v1-protocol-20260915'
    git(root,'fetch','origin',branch)
    parent=git(root,'rev-parse','FETCH_HEAD',capture=True).strip()
    stamp=datetime.now().strftime('%Y%m%dT%H%M%S%f')+'_'+str(os.getpid())
    worktree=base/('github_upload_'+stamp)
    git(root,'worktree','add','--detach',str(worktree),parent)
    relative=Path('records')/base.name/('evidence_'+stamp)
    target=worktree/relative;target.mkdir(parents=True)
    for name,raw in data.items():
        path=target/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as f:f.write(raw)
    manifest=dict(created_at=datetime.now().astimezone().isoformat(),server_directory=str(base),base_commit=parent,
                  files=[dict(path=n,bytes=len(v),sha256=hashlib.sha256(v).hexdigest()) for n,v in data.items()],
                  predictions_and_checkpoints_uploaded=False,upload_launches_training=False)
    (target/'upload_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    paths=[(relative/n).as_posix() for n in data]+[(relative/'upload_manifest.json').as_posix()]
    git(worktree,'add','-f','--',*paths)
    git(worktree,'-c','user.name=66322','-c','user.email=57258129+66322@users.noreply.github.com',
        'commit','-m','records: upload D24 overnight portfolio light evidence')
    commit=git(worktree,'rev-parse','HEAD',capture=True).strip()
    git(worktree,'push','origin','HEAD:refs/heads/'+branch)
    print('D24_GITHUB_COMMIT='+commit)
    print('D24_GITHUB_RECORDS=https://github.com/66322/remote_sensing_frequency/tree/'+commit+'/'+relative.as_posix())
    print('D24_UPLOAD_FILES='+str(len(data)+1))
if __name__=='__main__':main()
