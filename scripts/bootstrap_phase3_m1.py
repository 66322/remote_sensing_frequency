"""Fixed-commit, one-time registration and detached launch. Standard library only."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from datetime import datetime,timezone,timedelta

def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(data): return hashlib.sha256(data).hexdigest()
def download(commit,path):
    with urllib.request.urlopen('https://raw.githubusercontent.com/66322/remote_sensing_frequency/'+commit+'/'+path,timeout=90) as r: return r.read()

def validate_superseded(records, target):
    """Allow this known pre-training import failure only; preserve its entire record."""
    target=Path(target)
    if target.is_symlink(): raise RuntimeError('refuse symlink predecessor')
    target=target.resolve()
    if target.parent!=Path(records).resolve() or target.name!='research_phase3_m1_20261015T142532_2652995':
        raise RuntimeError('only the identified failed launch can be superseded')
    if read(target/'queue_status.json')['status']!='FAILED_OR_INTERRUPTED_NO_RETRY':
        raise RuntimeError('predecessor is not terminal failed')
    if read(target/'plan.json')['execution_commit']!='c46a9d8a129198d73e744b02ade62784283a50e1':
        raise RuntimeError('unexpected predecessor code')
    failures=[read(f) for f in (target/'failures').glob('*.json')]
    if not failures or any(f.get('error')!="No module named 'model'" or f.get('task',{}).get('kind')!='RGB_CLEAN' for f in failures):
        raise RuntimeError('unexpected failure; no automatic recovery')
    if any((target/'jobs').iterdir()): raise RuntimeError('training artifacts exist; preserve without replacement')
    retired=read(target/'ram_retirement.json')
    if not retired['all_owned_gpu_workers_exited'] or not retired['all_cpu_consumers_exited']:
        raise RuntimeError('predecessor workers have not exited')
    pid=int(read(target/'launch.json')['controller_pid'])
    try:
        if (Path('/proc')/str(pid)/'cmdline').read_bytes(): raise RuntimeError('predecessor PID is live; do not signal it')
    except FileNotFoundError: pass
    return target

def main():
    p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,required=True); p.add_argument('--commit',required=True)
    p.add_argument('--supersede-failed',type=Path)
    args=p.parse_args(); root=args.root.resolve(); root.relative_to(Path('/home/jovyan/zzx').resolve())
    print('PHASE3_M1_REGISTRATION_BEGIN',root,args.commit,flush=True)
    if not re.fullmatch('[0-9a-f]{40}',args.commit): raise ValueError('immutable full SHA required')
    import fcntl
    records=root/'records'; records.mkdir(exist_ok=True)
    with (records/'phase3_m1_registration.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        superseded=validate_superseded(records,args.supersede_failed) if args.supersede_failed else None
        previous=[d for d in sorted(records.glob('research_phase3_m1_*')) if d.resolve()!=superseded]
        if previous:
            for d in previous:
                print('EXISTING_PHASE3_M1_NO_DUPLICATE',d)
                for n in ('queue_status.json','registration_failure.json'):
                    if (d/n).exists(): print(n,(d/n).read_text())
            return
        gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
        selected={int(x.split(',')[0]):[y.strip() for y in x.split(',')] for x in gpu.splitlines() if int(x.split(',')[0]) in (0,1)}
        apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader,nounits'],text=True)
        if set(selected)!={0,1} or any(float(x[-1])<40000 or x[1] in apps for x in selected.values()):
            print('GPU0_OR_1_BUSY_NO_NEW_QUEUE_REGISTERED'); return
        predecessor=records/'research_phase24_protected_20261014T193915_2149100'
        if read(predecessor/'github_upload_receipt.json')['all_parts_readback'] is not True: raise RuntimeError('Phase2.4 upload receipt missing')
        source_manifest=read(predecessor/'code_manifest.json')
        print('DOWNLOADING_FIXED_EXECUTION_MANIFEST',flush=True)
        manifest=json.loads(download(args.commit,'configs/phase3_m1_execution_manifest.json'))
        stamp=datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%dT%H%M%S')
        base=records/f'research_phase3_m1_{stamp}_{os.getpid()}'; base.mkdir(); code=base/'code'
        try:
            print('COPYING_VERIFIED_INHERITED_SOURCE',len(source_manifest['files']),flush=True)
            for name,h in source_manifest['files'].items():
                source=(predecessor/'code'/name).resolve(); source.relative_to((predecessor/'code').resolve())
                data=source.read_bytes()
                if digest(data)!=h: raise RuntimeError('inherited immutable source changed: '+name)
                target=code/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
            for name,h in manifest['files'].items():
                print('FETCH_SOURCE',name,flush=True)
                data=download(args.commit,name)
                if digest(data)!=h: raise RuntimeError('downloaded source hash differs: '+name)
                target=(code/name).resolve(); target.relative_to(code.resolve()); target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
            for n in ('logs','jobs','primary','clean','results','scale','analysis','failures','skipped','retirement','temporary','cache/torch','cache/cuda','cache/triton','cache/kernels'):
                (base/n).mkdir(parents=True,exist_ok=True)
            sys.path.insert(0,str(code/'scripts'))
            import phase3_m1_common as c
            plan=dict(root=str(root),previous=str(records/'research_phase2_matched_20261013T151120_1310582'),
                execution_commit=args.commit,fit12=c.FIT,val2=c.VAL,gpus=[0,1],seeds=[42,17],updates=16000,batch=16,
                max_new_trainings=13,max_new_updates=208000,automatic_retry=False,wall_deadline_hours=None,
                pixel_array_disk_cache=False,point_cloud_loaded=False,test6_loaded=False,held4_loaded=False,
                lifecycle='lease-based memfd retirement; successful rolling optimizer deleted after endpoint+counts; runtime cache removed at final exit',
                fusion='FP64 fixed post-stitch sum logits 0.9/0.1, plus same-coverage probability sensitivity; no per-window rounding claim',
                GPU_scheduling='shared ready queue; no seed affinity barrier',registered_at=c.now())
            c.write(base/'plan.json',plan)
            files={f.relative_to(code).as_posix():digest(f.read_bytes()) for f in code.rglob('*') if f.is_file()}
            c.write(base/'code_manifest.json',dict(commit=args.commit,inherited_phase24_commit=source_manifest['commit'],files=files))
            c.write(base/'registration.json',dict(binding=c.binding(base),download_manifest=manifest,observed_at=c.now()))
            from phase24_common import env
            execution_env=env(base)
            execution_env['PYTHONPATH']=os.pathsep.join((str(code),str(code/'scripts')))
            print('CHECKING_REAL_MODEL_IMPORTS_BEFORE_INPUT_PREPARATION',flush=True)
            with (base/'import_checks.log').open('x') as log:
                subprocess.run([sys.executable,'-B','-c',
                    'import phase3_m1_runtime; from model.phase2_matched import MatchedExpert, optimizer; from d24_data import PrefetchedBatches; from phase2_infer import coords; print("M1_REAL_MODEL_IMPORTS_OK")'],
                    cwd=code,env=execution_env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
            if superseded:
                c.write(base/'supersedes_failed_launch.json',dict(previous=str(superseded),reason="No module named 'model' before training",previous_binding=c.binding(superseded),previous_record_preserved=True,observed_at=c.now()))
            print('CHECKING_LINUX_RAM_TRANSPORT',flush=True)
            with (base/'cpu_checks.log').open('x') as log:
                subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(code/'tests'),'-p','test_phase3_m1.py','-k','memfd','-v'],
                     cwd=code,env=execution_env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
            c.write(base/'registration_checks.json',dict(targeted_linux_memfd_passed=True,local_logic_checks='16 applicable checks passed; one Linux transport deferred; fixed-source review receipt in records/phase3_m1_implementation_review_20261015.json; unchanged logic not redundantly rerun',log_sha256=c.sha(base/'cpu_checks.log'),real_GPU_checks='first actual update verifies gradient and stem change; counts bridge checks legacy endpoint',observed_at=c.now()))
            c.write(base/'gpu_inventory.json',dict(gpus=gpu,apps=apps,observed_at=c.now()))
            c.write(base/'queue_status.json',dict(status='REGISTERED',observed_at=c.now()))
            logpath=base/'nohup.log'
            print('STARTING_DETACHED_CONTROLLER',base,flush=True)
            with logpath.open('x') as log:
                proc=subprocess.Popen([sys.executable,'-u','-B',str(code/'scripts/control_phase3_m1.py'),'--directory',str(base)],
                    cwd=code,env=execution_env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            c.write(base/'launch.json',dict(controller_pid=proc.pid,log=str(logpath),observed_at=c.now()))
            print('PHASE3_M1_LAUNCHED',base,'PID='+str(proc.pid),'GPU=0,1 NO24H_DEADLINE')
            print('STATUS:',sys.executable,'-B',code/'scripts/status_phase3_m1.py','--directory',base)
            print('LOG:',logpath)
        except BaseException as exc:
            (base/'registration_failure.json').write_text(json.dumps(dict(error=str(exc),automatic_retry=False))+'\n'); raise

if __name__=='__main__': main()

