"""Explicit recovery of the identified rebooted run; preserve its immutable history."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from datetime import datetime,timezone,timedelta

SOURCE_NAME='research_phase3_m1_20261015T143433_2657574'
SOURCE_COMMIT='9abfaadae4d045086bda0861b588a73881139aaa'
SOURCE_BINDING={'plan.json':'14ae36fa8b449200da2ea2d25d17b5c9c40129cabb63fa19e4d668b935f268c9',
                'code_manifest.json':'ab7bbdc4ac6ee036b73e8f361cab62c25ce78ed1464741c7fbd9722743cba7fd'}

def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024**2),b''): h.update(chunk)
    return h.hexdigest()
def write(p,value):
    p=Path(p); tmp=p.with_name(p.name+'.tmp.'+str(os.getpid()))
    tmp.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2)+'\n',encoding='utf-8')
    os.replace(tmp,p)
def download(commit,path):
    with urllib.request.urlopen('https://raw.githubusercontent.com/66322/remote_sensing_frequency/'+commit+'/'+path,timeout=90) as r:
        return r.read()
def scope(p,root):
    p=Path(p)
    if p.is_symlink(): raise RuntimeError('symlink refused: '+str(p))
    p=p.resolve(); p.relative_to(Path(root).resolve()); return p

def save_stream_prefix(source,target,step):
    """Only committed optimizer steps enter the continued scientific sample stream."""
    with Path(source).open('rb') as old,Path(target).open('xb') as out:
        for expected in range(1,step+1):
            line=old.readline(); row=json.loads(line)
            if row['step']!=expected or not isinstance(row.get('batch_hash'),str): raise RuntimeError('invalid saved batch prefix')
            out.write(line if line.endswith(b'\n') else line+b'\n')
    return sha(target)

def save_trajectory_prefix(source,target,step):
    elapsed=None; previous=0
    with Path(source).open('rb') as old,Path(target).open('xb') as out:
        for line in old:
            row=json.loads(line)
            if row['step']>step: break
            if row['step']<=previous: raise RuntimeError('invalid saved trajectory order')
            previous=row['step']; elapsed=row['elapsed_seconds']
            out.write(line if line.endswith(b'\n') else line+b'\n')
            if previous==step: break  # Any interrupted tail is outside the committed prefix.
    if previous!=step: raise RuntimeError('checkpoint step missing from saved trajectory')
    return elapsed

def copy_jobs(source,base):
    import torch
    completed={}; resumed={}; old_binding={n:sha(source/n) for n in SOURCE_BINDING}
    allowed={f'{a}_{s}' for a in ('M00','M01','M10','M11','M20','M21') for s in (42,17)}-{'M00_42'}
    for folder in sorted((source/'jobs').iterdir()):
        if not folder.is_dir() or folder.name not in allowed: raise RuntimeError('unexpected training artifact '+str(folder))
        if (folder/'failure.json').exists(): raise RuntimeError('technical task failure needs separate review')
        job=folder.name; dest=base/'jobs'/job; dest.mkdir()
        done=folder/'complete.json'
        if done.exists():
            z=read(done)
            if z['job']!=job or z['binding']!=old_binding or z['optimizer_updates']!=16000 or sha(folder/'endpoint.pth')!=z['checkpoint_sha256']:
                raise RuntimeError('completed endpoint failed validation '+job)
            files={}
            for f in sorted(folder.iterdir()):
                scope(f,folder)
                if not f.is_file(): raise RuntimeError('unexpected nested job data')
                # Successful rolling files have no future optimizer consumer.
                if f.suffix=='.tmp' or f.name=='last_resume.pth': continue
                h=sha(f)
                if f.name=='endpoint.pth':
                    try: os.link(f,dest/f.name)
                    except OSError: shutil.copyfile(f,dest/f.name)
                else: shutil.copyfile(f,dest/f.name)
                if sha(dest/f.name)!=h: raise RuntimeError('copied complete evidence differs')
                files[f.name]=h
            completed[job]=dict(files=files,source=str(folder))
            print('REUSE_COMPLETED_NO_TRAIN',job,flush=True)
        else:
            f=folder/'last_resume.pth'; h=sha(f)
            state=torch.load(f,map_location='cpu',weights_only=False); step=state['step']
            if sha(f)!=h or state['job']!=job or state['binding']!=old_binding or not 0<step<16000 or step%1000:
                raise RuntimeError('rolling checkpoint identity invalid '+job)
            if not all(k in state for k in ('model','optimizer','rng','cuda_rng')): raise RuntimeError('rolling state incomplete')
            if len(state['cuda_rng'])!=1: raise RuntimeError('expected one visible CUDA device per saved worker')
            prefix=save_stream_prefix(folder/'batch_hashes.jsonl',dest/'batch_hashes.jsonl',step)
            elapsed=save_trajectory_prefix(folder/'trajectory.jsonl',dest/'trajectory.jsonl',step)
            for name in ('parameters.json','legacy_initial_check.json','gradient_path.json'):
                if (folder/name).exists(): shutil.copyfile(folder/name,dest/name)
            for p in folder.glob('validation_*.json'):
                if int(p.stem.split('_')[-1])<=step:
                    read(p); shutil.copyfile(p,dest/p.name)
            observed=read(folder/'progress.json').get('step',step)
            write(dest/'progress.json',dict(step=step,status='CHECKPOINT_READY_TO_RESUME',last_observed_before_reboot=observed))
            resumed[job]=dict(path=str(f),sha256=h,step=step,elapsed_seconds=elapsed,
                             prefix_sha256=prefix,last_observed_step=observed,replayed_since_checkpoint=max(0,observed-step))
            print('RESUME_CHECKPOINT',job,'STEP='+str(step),'LAST_OBSERVED='+str(observed),flush=True)
            del state
    return completed,resumed

def main():
    p=argparse.ArgumentParser(); p.add_argument('--directory',type=Path,required=True); p.add_argument('--commit',required=True)
    args=p.parse_args(); source=args.directory.resolve(); root=source.parent.parent; records=source.parent
    source.relative_to(Path('/home/jovyan/zzx').resolve())
    if source.name!=SOURCE_NAME or not re.fullmatch('[0-9a-f]{40}',args.commit): raise RuntimeError('identified source and immutable commit required')
    print('PHASE3_M1_RECOVERY_BEGIN',source,args.commit,flush=True)
    import fcntl
    with (records/'phase3_m1_registration.lock').open('a') as registration_lock, (source/'controller.lock').open('a') as source_lock:
        fcntl.flock(registration_lock,fcntl.LOCK_EX|fcntl.LOCK_NB); fcntl.flock(source_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        marker=records/('phase3_m1_recovery_of_'+SOURCE_NAME+'.json')
        if marker.exists():
            old=read(marker); print('EXISTING_RECOVERY_NO_DUPLICATE',old,flush=True)
            b=Path(old['directory'])
            for name in ('queue_status.json','registration_failure.json'):
                if (b/name).exists(): print(name,(b/name).read_text(),flush=True)
            return
        if {n:sha(source/n) for n in SOURCE_BINDING}!=SOURCE_BINDING: raise RuntimeError('original plan/code binding differs')
        old_plan=read(source/'plan.json')
        if old_plan['execution_commit']!=SOURCE_COMMIT or read(source/'queue_status.json')['status']!='RUNNING': raise RuntimeError('unexpected source state')
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit() or int(proc.name)==os.getpid(): continue
            try:
                cmd=(proc/'cmdline').read_bytes()
                if str(source).encode() in cmd and b'control_phase3_m1.py' in cmd: raise RuntimeError('original worker is live; no signals sent')
            except (FileNotFoundError,PermissionError,ProcessLookupError): pass
        gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
        selected={int(x.split(',')[0]):[s.strip() for s in x.split(',')] for x in gpu.splitlines() if int(x.split(',')[0]) in (0,1)}
        apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader,nounits'],text=True)
        if set(selected)!={0,1} or any(float(x[-1])<40000 or x[1] in apps for x in selected.values()):
            print('GPU0_OR_1_BUSY_NO_RECOVERY_STARTED',flush=True); return
        manifest=json.loads(download(args.commit,'configs/phase3_m1_execution_manifest.json'))
        stamp=datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%dT%H%M%S')
        base=records/f'research_phase3_m1_recovery_{stamp}_{os.getpid()}'; base.mkdir(); code=base/'code'
        write(marker,dict(directory=str(base),source=str(source),commit=args.commit))
        try:
            for name,h in read(source/'code_manifest.json')['files'].items():
                f=scope(source/'code'/name,source/'code')
                if sha(f)!=h: raise RuntimeError('source code changed '+name)
                target=code/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(f,target)
            for name,h in manifest['files'].items():
                print('FETCH_RECOVERY_SOURCE',name,flush=True); data=download(args.commit,name)
                if hashlib.sha256(data).hexdigest()!=h: raise RuntimeError('recovery source differs '+name)
                target=scope(code/name,code); target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
            for name in ('logs','jobs','primary','clean','results','scale','analysis','failures','skipped','retirement','temporary','cache/torch','cache/cuda','cache/triton','cache/kernels'):
                (base/name).mkdir(parents=True,exist_ok=True)
            # CPU-only registration must not initialize CUDA before the detached controller forks.
            os.environ['CUDA_VISIBLE_DEVICES']=''
            sys.path.insert(0,str(code)); sys.path.insert(0,str(code/'scripts'))
            completed,resumed=copy_jobs(source,base)
            if len(completed)!=7 or set(resumed)!={'M20_17','M01_42'}: raise RuntimeError('source inventory differs from reported seven complete/two interrupted jobs')
            recovery=dict(source_directory=str(source),previous_binding=SOURCE_BINDING,completed=completed,resumed=resumed,
                source_state=read(source/'queue_status.json'),previous_gate=read(source/'analysis/amplitude_gate.json') if (source/'analysis/amplitude_gate.json').exists() else None,
                original_directory_preserved=True,recompute_lost_anonymous_arrays=True,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
            write(base/'recovery_manifest.json',recovery)
            plan=dict(old_plan,execution_commit=args.commit,recovery_source=str(source),recovery_manifest_sha256=sha(base/'recovery_manifest.json'))
            write(base/'plan.json',plan)
            files={f.relative_to(code).as_posix():sha(f) for f in code.rglob('*') if f.is_file()}
            write(base/'code_manifest.json',dict(commit=args.commit,inherited_execution_commit=SOURCE_COMMIT,files=files))
            import phase3_m1_common as c
            write(base/'registration.json',dict(binding=c.binding(base),download_manifest=manifest,recovery=True,observed_at=c.now()))
            c.verify(base)
            from phase24_common import env
            execution_env=env(base); execution_env['PYTHONPATH']=os.pathsep.join((str(code),str(code/'scripts')))
            print('CHECKING_RECOVERY_IMPORTS_AND_LINUX_TRANSPORT',flush=True)
            with (base/'cpu_checks.log').open('x') as log:
                subprocess.run([sys.executable,'-B','-c','import phase3_m1_runtime; from model.phase2_matched import MatchedExpert, optimizer; from d24_data import PrefetchedBatches; from phase2_infer import coords; print("REAL_MODEL_IMPORTS_OK")'],cwd=code,env=execution_env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
                subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(code/'tests'),'-p','test_phase3_m1.py','-k','memfd','-v'],cwd=code,env=execution_env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
            write(base/'registration_checks.json',dict(cpu_model_imports=True,target_linux_memfd=True,checkpoint_tensors_loaded_on_cpu=True,observed_at=c.now()))
            write(base/'gpu_inventory.json',dict(gpus=gpu,apps=apps,observed_at=c.now()))
            write(base/'queue_status.json',dict(status='REGISTERED',observed_at=c.now()))
            logpath=base/'nohup.log'
            with logpath.open('x') as log:
                proc=subprocess.Popen([sys.executable,'-u','-B',str(code/'scripts/control_phase3_m1.py'),'--directory',str(base)],cwd=code,env=execution_env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            write(base/'launch.json',dict(controller_pid=proc.pid,log=str(logpath),observed_at=c.now()))
            print('PHASE3_M1_RECOVERY_LAUNCHED',base,'PID='+str(proc.pid),'GPU=0,1',flush=True)
            print('STATUS:',sys.executable,'-B',code/'scripts/status_phase3_m1.py','--directory',base,flush=True)
            print('LOG:',logpath,flush=True)
        except BaseException as exc:
            write(base/'registration_failure.json',dict(error=str(exc),automatic_retry=False)); raise

if __name__=='__main__': main()
