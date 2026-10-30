"""Publish existing compact evidence only, using existing authentication; no recomputation."""
import base64
import json
import os
from pathlib import Path
import subprocess
import urllib.request
from . import common as c

REPO='66322/remote_sensing_frequency';BRANCH='rebuild-v1-protocol-20260915'

def credential():
    for name in ('GH_TOKEN','GITHUB_TOKEN'):
        if os.environ.get(name):return os.environ[name]
    try:return subprocess.check_output(['gh','auth','token','--hostname','github.com'],stderr=subprocess.DEVNULL,text=True,timeout=10).strip()
    except (OSError,subprocess.SubprocessError):pass
    try:
        row=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',
            env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never'),capture_output=True,text=True,timeout=10)
        if row.returncode==0:return dict(x.split('=',1) for x in row.stdout.splitlines() if '=' in x).get('password')
    except (OSError,subprocess.SubprocessError):pass
    return None

def publish(base):
    base=Path(base);token=credential()
    if not token:
        c.write(base/'upload_pending.json',dict(status='EXISTING_AUTH_UNAVAILABLE',no_recompute=True,observed_at=c.now()))
        print('COMPUTATION_RETAINED_UPLOAD_PENDING_EXISTING_AUTH');return
    def api(method,path,value=None):
        request=urllib.request.Request('https://api.github.com/repos/'+REPO+'/'+path,method=method,
            data=None if value is None else json.dumps(value).encode(),headers={'Authorization':'Bearer '+token,
                'Accept':'application/vnd.github+json','Content-Type':'application/json','User-Agent':'PostM2-v2-compact'})
        with urllib.request.urlopen(request,timeout=30) as r:return json.load(r)
    publication=base/'publication';prefix='records/'+base.name;entries=[]
    for p in sorted(publication.rglob('*')):
        if not p.is_file():continue
        data=p.read_bytes()
        if len(data)>25*1024**2:raise RuntimeError('unexpected large publication file')
        blob=api('POST','git/blobs',dict(encoding='base64',content=base64.b64encode(data).decode('ascii')))
        entries.append(dict(path=prefix+'/'+p.relative_to(publication).as_posix(),mode='100644',type='blob',sha=blob['sha']))
    parent=api('GET','git/ref/heads/'+BRANCH)['object']['sha'];tree=api('GET','git/commits/'+parent)['tree']['sha']
    newtree=api('POST','git/trees',dict(base_tree=tree,tree=entries))['sha']
    commit=api('POST','git/commits',dict(message='Archive Post-M2 v2 compact execution evidence',tree=newtree,parents=[parent]))['sha']
    if api('GET','git/ref/heads/'+BRANCH)['object']['sha']!=parent:raise RuntimeError('branch advanced; upload existing files later, no force/recompute')
    api('PATCH','git/refs/heads/'+BRANCH,dict(sha=commit,force=False))
    for name in ('summary.json','gates.json'):
        row=api('GET','contents/'+prefix+'/'+name+'?ref='+commit)
        if base64.b64decode(row['content'])!=(publication/name).read_bytes():raise RuntimeError('key result readback mismatch')
    c.write(base/'github_upload_receipt.json',dict(commit=commit,files=len(entries),key_results_read_back=True,observed_at=c.now()))
    print('GITHUB_COMPACT_RESULTS',commit)
