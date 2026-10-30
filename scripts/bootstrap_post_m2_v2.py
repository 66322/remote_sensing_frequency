#!/usr/bin/env python3
"""Download one small frozen payload. No git clone, weights, data or package installation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.request

ROOT=Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro')
NAME='post_m2_multiroute_v2_20261030_r1'
PREFIX='https://raw.githubusercontent.com/66322/remote_sensing_frequency/'

def fetch(url):
    with urllib.request.urlopen(url,timeout=30) as r:return r.read()

def install(commit,target,fetcher=fetch):
    if not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('exact published commit required')
    target=Path(target);url=PREFIX+commit+'/'
    raw=fetcher(url+'records/post_m2_multiroute_v2_20261030_release/payload_manifest.json')
    manifest=json.loads(raw);target.mkdir(parents=True,exist_ok=True)
    if (target/'SOURCE.json').exists():raise RuntimeError('frozen payload already installed; use its entry/status instead')
    for name,digest in manifest['files'].items():
        rel=Path(name)
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('unsafe manifest path')
        path=target/rel;path.resolve().relative_to(target.resolve())
        data=fetcher(url+name)
        if hashlib.sha256(data).hexdigest()!=digest:raise RuntimeError('small code payload mismatch: '+name)
        path.parent.mkdir(parents=True,exist_ok=True)
        # A partially downloaded identical file may be retained; changed content is never overwritten.
        if path.exists() and path.read_bytes()!=data:raise RuntimeError('existing different payload file: '+name)
        path.write_bytes(data)
    (target/'payload_manifest.json').write_bytes(raw)
    (target/'SOURCE.json').write_text(json.dumps(dict(commit=commit,release=NAME,manifest_path=
        'records/post_m2_multiroute_v2_20261030_release/payload_manifest.json'))+'\n',encoding='utf-8')
    print('FROZEN_PAYLOAD_READY',target,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--start',action='store_true');args=p.parse_args()
    target=ROOT/'execution'/NAME;install(args.commit,target)
    if args.start:
        import os,subprocess,sys
        base=ROOT/'records'/NAME;base.mkdir(parents=True,exist_ok=True)
        env=dict(os.environ,OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
            NUMEXPR_NUM_THREADS='1',XFORMERS_DISABLED='1',PYTHONDONTWRITEBYTECODE='1')
        with (base/'pipeline.log').open('x',encoding='utf-8') as log:
            proc=subprocess.Popen([sys.executable,'-u','-B',str(target/'scripts/post_m2_multiroute.py'),'pipeline'],
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        (base/'pipeline.pid').write_text(str(proc.pid)+'\n')
        print('PIPELINE_DISPATCHED_NOT_TRAINING_PROOF',proc.pid,'log',base/'pipeline.log',flush=True)
