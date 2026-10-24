"""Upload explicit formal D23 JSON/log evidence only, including partial failures."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ARMS=('T0','TS','TF','TSF','TCAP','TSF_CE','TSF_shuffleS','TSF_shuffleF')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(cwd,*args,capture=False):
    return subprocess.run(['git','-C',str(cwd),*args],check=True,text=True,
      stdout=subprocess.PIPE if capture else None).stdout
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--directory',type=Path,required=True);args=ap.parse_args()
    root=args.root.resolve();root.relative_to(Path('/home/jovyan/zzx').resolve())
    base=args.directory.resolve();base.relative_to(root/'records')
    if not base.name.startswith('research_d23_b_formal_'):raise ValueError('unexpected directory')
    names=['execution_commit.txt','plan.json','runtime_lock.json','queue_status.json',
           'screen_manifest.json','screen_result.json','screen.log']
    state=json.loads((base/'queue_status.json').read_text())
    for key in ('screen_manifest','screen_result','screen_log'):
        if state.get(key):names.append(Path(state[key]).resolve().relative_to(base).as_posix())
    names += [p.relative_to(base).as_posix() for p in base.glob('resume_event_*.json')]
    for arm in ARMS:
        row=state.get('jobs',{}).get(arm,{})
        job=Path(row.get('job_directory',base/'jobs'/arm)).resolve().relative_to(base).as_posix()
        logfile=Path(row.get('log_path',base/'logs'/(arm+'.log'))).resolve().relative_to(base).as_posix()
        names += [logfile]+[job+'/'+p for p in (
          'preflight.json','formal_fit_statistics.json','formal_complete.json',
          'training/training_complete.json','evaluation/summary.json')]
    data={}
    for name in dict.fromkeys(names):
        p=(base/name).resolve();p.relative_to(base)
        if not p.is_file():continue
        if p.stat().st_size>5*1024**2:raise ValueError('light evidence too large: '+name)
        raw=p.read_bytes();raw.decode('utf-8')
        if name.endswith('.json'):json.loads(raw)
        data[name]=raw
    if not all(n in data for n in ('execution_commit.txt','plan.json','runtime_lock.json','queue_status.json')):
        raise ValueError('queue binding evidence absent')
    if sum(map(len,data.values()))>32*1024**2:raise ValueError('light upload budget exceeded')
    origin=git(root,'remote','get-url','origin',capture=True).strip()
    if not origin.endswith(('github.com/66322/remote_sensing_frequency.git',
      'github.com/66322/remote_sensing_frequency','github.com:66322/remote_sensing_frequency.git')):
        raise ValueError('unexpected origin')
    branch='rebuild-v1-protocol-20260915';git(root,'fetch','origin',branch)
    parent=git(root,'rev-parse','FETCH_HEAD',capture=True).strip()
    stamp=datetime.now().strftime('%Y%m%dT%H%M%S%f')+'_'+str(os.getpid())
    wt=base/('github_upload_'+stamp);wt.resolve().relative_to(base)
    git(root,'worktree','add','--detach',str(wt),parent)
    relative=Path('records')/base.name/('evidence_'+stamp);target=wt/relative
    target.mkdir(parents=True)
    for name,raw in data.items():
        p=target/name;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(raw)
    manifest=dict(created_at=datetime.now().astimezone().isoformat(),server_directory=str(base),
      base_commit=parent,repository_directory=relative.as_posix(),
      files=[dict(path=n,bytes=len(v),sha256=sha(v)) for n,v in data.items()],
      predictions_and_checkpoints_uploaded=False,upload_launches_training=False)
    with (target/'upload_manifest.json').open('x') as f:
        json.dump(manifest,f,indent=2,allow_nan=False)
    paths=[(relative/n).as_posix() for n in data]+[(relative/'upload_manifest.json').as_posix()]
    git(wt,'add','-f','--',*paths)
    git(wt,'-c','user.name=66322','-c','user.email=57258129+66322@users.noreply.github.com',
      'commit','-m','records: upload D23 eight-arm development screen evidence')
    commit=git(wt,'rev-parse','HEAD',capture=True).strip()
    git(wt,'push','origin','HEAD:refs/heads/'+branch)
    print('D23_GITHUB_COMMIT='+commit)
    print('D23_GITHUB_RECORDS=https://github.com/66322/remote_sensing_frequency/tree/'+commit+'/'+relative.as_posix())
if __name__=='__main__':main()
