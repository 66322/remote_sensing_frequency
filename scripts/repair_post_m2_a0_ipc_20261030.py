#!/usr/bin/env python3
"""Explicit A0 IPC repair: preserve evidence, stop only verified old owners, prepare once.

prepare never starts training; start is a separate, explicit user action.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time

ROOT=Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro')
OLD=ROOT/'records/post_m2_a0_capability_20261029'
NEW=ROOT/'records/post_m2_a0_ipcfix_20261030'
SCRIPT=Path(__file__).with_name('post_m2_a0_ipcfix_20261030.py')
ORIGINAL=OLD/'post_m2_a0.py'
SCIENCE='c22a046407daf42064cbb161429f2648c9b86d66'
ORIGINAL_BLOB='f480fc67915764f0e706eb20af851adf076e6c40'
OLD_LOG=OLD/'formal_continuation_20261030T171015_2273418.log'
SHORT=Path('/home/jovyan/zzx/tmp/a0_ipc')
KINDS=('dino2','dino3')
KNOWN_CHILDREN={2426731:'dino2',2426732:'dino3'}

def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def read(path):return json.loads(Path(path).read_text())
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')

def process(pid):
    p=Path('/proc')/str(pid)
    try:
        raw=(p/'stat').read_text();fields=raw[raw.rfind(')')+2:].split()
        argv=(p/'cmdline').read_bytes().decode(errors='replace').rstrip('\0').split('\0')
        return dict(pid=pid,ppid=int(fields[1]),state=fields[0],start_ticks=fields[19],argv=argv,
                    stdout=os.readlink(p/'fd/1') if (p/'fd/1').exists() else '')
    except (FileNotFoundError,ProcessLookupError,PermissionError):return None

def child_matches(info,kind):
    if not info:return False
    args=info['argv']
    return str(ORIGINAL) in args and 'train' in args and '--kind' in args and kind in args and info['stdout']==str(OLD/('pair_train_'+kind+'.log'))

def active_same(info):
    current=process(info['pid'])
    return bool(current and current['state']!='Z' and current['start_ticks']==info['start_ticks'])

def owned_snapshot():
    owned={};controllers=set()
    for pid,kind in KNOWN_CHILDREN.items():
        info=process(pid)
        if child_matches(info,kind):
            owned[pid]=info
            parent=process(info['ppid'])
            if parent and str(ORIGINAL) in parent['argv'] and 'pair' in parent['argv'] and 'train' in parent['argv'] and parent['stdout']==str(OLD_LOG):
                owned[parent['pid']]=parent;controllers.add(parent['pid'])
    info=process(2426676)
    if info and str(OLD/'continue_post_m2_a0_20261030.sh') in info['argv'] and info['stdout']==str(OLD_LOG):
        owned[info['pid']]=info;controllers.add(info['pid'])
    all_processes={}
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            info=process(int(p.name))
            if info:all_processes[info['pid']]=info
    changed=True
    while changed:
        changed=False
        for pid,info in all_processes.items():
            if pid not in owned and info['ppid'] in owned:
                owned[pid]=info;changed=True
    return owned,controllers

def stop_owned(owned,controllers):
    # Signal only this snapshot's exact process identities; never kill by name or PGID.
    order=list(controllers)+[p for p in owned if p not in controllers]
    for pid in order:
        if active_same(owned[pid]):
            try:os.kill(pid,signal.SIGTERM)
            except ProcessLookupError:pass
    deadline=time.monotonic()+5
    while time.monotonic()<deadline and any(active_same(x) for x in owned.values()):time.sleep(.1)
    killed=[]
    for pid,info in owned.items():
        if active_same(info):
            try:os.kill(pid,signal.SIGKILL);killed.append(pid)
            except ProcessLookupError:pass
    deadline=time.monotonic()+3
    while time.monotonic()<deadline and any(active_same(x) for x in owned.values()):time.sleep(.1)
    remaining=[p for p,x in owned.items() if active_same(x)]
    if remaining:raise RuntimeError('Owned old processes still alive: '+str(remaining))
    return dict(stopped_pids=list(owned),sigkill_pids=killed,remaining_owned_pids=remaining)

def observed_updates():
    result={};partial=False
    for kind in KINDS:
        folder=OLD/kind;progress=read(folder/'progress.json') if (folder/'progress.json').is_file() else None
        names=[n for n in ('trajectory.json','train_complete.json','head_2000.pth','calibration_result.json','outer_result.json') if (folder/n).exists()]
        logfile=OLD/('pair_train_'+kind+'.log');text=logfile.read_text(errors='replace') if logfile.exists() else ''
        steps=[int(x) for x in re.findall(r'A0_TRAIN[^\n]*"step"\s*:\s*(\d+)',text)]
        if progress:steps.append(int(progress.get('step',0)))
        partial=partial or bool(names) or any(x>0 for x in steps)
        result[kind]=dict(last_logged_step=max(steps,default=None),progress=progress,formal_artifacts=names,
                          af_unix_error_observed='AF_UNIX path too long' in text,
                          update_evidence='NO_SUCCESSFUL_UPDATE_OBSERVED' if not names and not steps else 'PARTIAL_OR_COMPLETED_FORMAL_EVIDENCE')
    return result,partial

def environment(commit):
    env=dict(os.environ,TMPDIR=str(SHORT),TEMP=str(SHORT),TMP=str(SHORT),
        POST_M2_CODE_COMMIT=SCIENCE,POST_M2_EXECUTION_PATCH_COMMIT=commit,
        POST_M2_DINO3_REPO=str(ROOT/'external/dinov3_6876159'),
        POST_M2_DINO3_WEIGHTS=str(ROOT/'pretrained/dinov3/dinov3_vits16_pretrain_lvd1689m-08c60483.pth'),
        TORCH_HOME=str(ROOT/'cache/torch'),XDG_CACHE_HOME=str(ROOT/'cache'),CUDA_CACHE_PATH=str(ROOT/'cache/cuda'),
        OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
    return env

def prepare(commit):
    if sys.platform!='linux':raise RuntimeError('Repair preparation is for the existing Linux server only')
    if not SCRIPT.is_file():raise RuntimeError('Download the separate repaired A0 source first')
    data=ORIGINAL.read_bytes()
    if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=ORIGINAL_BLOB:
        raise RuntimeError('Original frozen A0 source differs; do not overwrite it')
    if NEW.exists():raise RuntimeError('Repair directory already exists; use status, do not repeat preparation')
    evidence,partial=observed_updates()
    if not all(x['af_unix_error_observed'] for x in evidence.values()):raise RuntimeError('Expected error not found in both original logs; inspect the original failure')
    NEW.mkdir(parents=True)
    owned,controllers=owned_snapshot()
    write(NEW/'repair_prepare_started.json',dict(observed_at=now(),commit=commit,old_run=str(OLD),
        process_snapshot=owned,update_evidence_before_stop=evidence,reason='Observed AF_UNIX IPC failure; stop only verified owners to prevent indefinite wait'))
    result=stop_owned(owned,controllers)
    evidence,partial=observed_updates()
    write(NEW/'old_failure_stop_receipt.json',dict(observed_at=now(),**result,update_evidence_after_stop=evidence,
        originals_preserved=True,exact_total_failed_attempt_updates='UNKNOWN; absence of a progress record alone is not proof of zero updates'))
    if partial:
        write(NEW/'blocked_partial_training.json',dict(status='PARTIAL_FORMAL_EVIDENCE_REQUIRES_REVIEW_NO_REPLAY',evidence=evidence))
        raise RuntimeError('Old formal updates or endpoint observed. Old processes stopped, records preserved; do not replay training automatically.')
    SHORT.mkdir(parents=True,exist_ok=True);SHORT.resolve().relative_to(Path('/home/jovyan/zzx'))
    if len(os.fsencode(str(SHORT.resolve())))>50:raise RuntimeError('Short temp path resolves too long')
    os.environ.update(TMPDIR=str(SHORT),TEMP=str(SHORT),TMP=str(SHORT));tempfile.tempdir=str(SHORT)
    from multiprocessing.connection import Listener
    with Listener(family='AF_UNIX') as listener:
        address=listener.address
        if len(os.fsencode(address))>=108:raise RuntimeError('Actual multiprocessing socket path too long')
    # Exactly one CPU tensor batch exercises the failing FD-sharing path; no CUDA/optimizer/model.
    cpu_test='''import json,torch
from torch.utils.data import DataLoader,TensorDataset
loader=DataLoader(TensorDataset(torch.ones(4,2)),batch_size=2,num_workers=1,timeout=10)
stream=iter(loader)
try:
    batch=next(stream)[0]
    assert tuple(batch.shape)==(2,2) and batch.sum().item()==4
    print(json.dumps(dict(status="ONE_CPU_TENSOR_IPC_PASSED",cuda_used=False,optimizer_updates=0)))
finally:stream._shutdown_workers()
'''
    check=subprocess.run([sys.executable,'-B','-c',cpu_test],env=environment(commit),capture_output=True,text=True,timeout=30)
    write(NEW/'cpu_ipc_check.json',dict(observed_at=now(),socket_address=address,address_bytes=len(os.fsencode(address)),
        returncode=check.returncode,stdout=check.stdout,stderr=check.stderr,optimizer_updates=0))
    if check.returncode:raise RuntimeError('CPU tensor IPC failed; see cpu_ipc_check.json; no training started')
    for kind in KINDS:
        raw=(OLD/('profile_'+kind+'.json')).read_bytes();value=json.loads(raw)
        if value['code_commit']!=SCIENCE or value['status']!='PROFILE_COMPLETED_NO_SCIENTIFIC_RESULT':raise RuntimeError('Original profile mismatch')
        (NEW/('profile_'+kind+'.json')).write_bytes(raw)
    ready=dict(status='IPC_REPAIR_PREPARED_NO_TRAINING_STARTED',observed_at=now(),commit=commit,
        scientific_source_commit=SCIENCE,execution_patch_commit=commit,new_run=str(NEW),
        original_profiles_reused_from=str(OLD),short_tmpdir=str(SHORT),loader_timeout_seconds=30,
        probe_optimizer_updates=0,successful_old_updates_observed=False,exact_old_update_count_known=False,
        automatic_training_start=False,original_files_changed=False)
    write(NEW/'repair_ready.json',ready);print(json.dumps(ready,ensure_ascii=False,indent=2))

def run(commit):
    ready=read(NEW/'repair_ready.json')
    if ready['commit']!=commit:raise RuntimeError('Prepared execution patch differs')
    if (NEW/'blocked_partial_training.json').exists():raise RuntimeError('Old partial training requires review')
    write(NEW/'repair_run_started.json',dict(observed_at=now(),pid=os.getpid(),execution_patch_commit=commit))
    env=environment(commit)
    for args in (['pair','--phase','train'],['pair','--phase','evaluate','--split','calibration'],['screen']):
        subprocess.run([sys.executable,'-u','-B',str(SCRIPT)]+args,env=env,check=True)
    result=read(NEW/'calibration_screen.json')
    if result['status']=='READY_FOR_OUTER_DEVELOPMENT_EVALUATION':
        subprocess.run([sys.executable,'-u','-B',str(SCRIPT),'pair','--phase','evaluate','--split','outer'],env=env,check=True)
    elif result['status'] not in ('INVALID_PROBE','NO_INCREMENT_STOP_A_ROUTE'):raise RuntimeError('Unknown screen')
    subprocess.run([sys.executable,'-B',str(SCRIPT),'status'],env=env,check=True)
    write(NEW/'repair_run_complete.json',dict(observed_at=now(),screen=result['status'],execution_patch_commit=commit))

def start(commit):
    ready=read(NEW/'repair_ready.json')
    if ready['commit']!=commit:raise RuntimeError('Prepared execution patch differs')
    if any((NEW/p).exists() for p in ('repair_dispatch.json','repair_run_started.json','blocked_partial_training.json')):raise RuntimeError('Already dispatched or blocked; use status')
    evidence,partial=observed_updates()
    if partial:raise RuntimeError('Original formal evidence changed; do not replay')
    owned,_=owned_snapshot()
    if any(active_same(x) for x in owned.values()):raise RuntimeError('Original owned processes still active')
    full=ROOT/'records/post_m2_multiroute_v2_20261030_r1'
    pid=read(full/'pipeline_started.json')['pid'] if (full/'pipeline_started.json').is_file() else int((full/'pipeline.pid').read_text()) if (full/'pipeline.pid').is_file() else None
    if pid:
        info=process(int(pid))
        if info and info['state']!='Z' and any('post_m2_multiroute.py' in x for x in info['argv']):raise RuntimeError('Full pipeline already active; no competing dispatch')
    log=NEW/'repair_continuation.log'
    with log.open('x') as out:
        proc=subprocess.Popen([sys.executable,'-u','-B',str(Path(__file__).resolve()),'run','--commit',commit],
            env=environment(commit),stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
    receipt=dict(status='REPAIRED_ENTRY_DISPATCHED_NOT_TRAINING_PROOF',observed_at=now(),pid=proc.pid,log=str(log),execution_patch_commit=commit)
    write(NEW/'repair_dispatch.json',receipt);print(json.dumps(receipt,ensure_ascii=False,indent=2))

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','start','run','status'));p.add_argument('--commit')
    args=p.parse_args()
    if args.action=='status':
        print(json.dumps({name:read(NEW/name) for name in ('repair_ready.json','blocked_partial_training.json','repair_dispatch.json','repair_run_started.json','repair_run_complete.json') if (NEW/name).is_file()},indent=2));return
    if not re.fullmatch('[0-9a-f]{40}',args.commit or ''):p.error('Exact repair commit required')
    try:globals()[args.action](args.commit)
    except BaseException:
        import traceback
        if NEW.is_dir():
            name=NEW/(args.action+'_first_failure.txt')
            if not name.exists():name.write_text(traceback.format_exc())
        raise

if __name__=='__main__':main()
