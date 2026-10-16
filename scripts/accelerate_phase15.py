"""Explicit versioned CPU takeover only; no GPU or scientific task additions."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

FILES=['scripts/phase15_fast_counts.py','scripts/run_phase15_acceleration.py',
       'scripts/accelerate_phase15.py','tests/test_phase15_acceleration.py']


def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def assert_stage(s):
    if s['status']!='CPU_ORACLE_AND_CONDITIONAL_COUNTS' or len(s['jobs'])!=100 or any(j['status']!='COMPLETE' for j in s['jobs'].values()):
        raise RuntimeError('takeover only allowed for D CPU after all 100 GPU jobs complete')


def choose_workers(requested,available_bytes,cpu_count):
    budget=(available_bytes-8*1024**3)//(12*1024**3)
    workers=min(requested,4,cpu_count,int(budget))
    if workers<1:raise RuntimeError('insufficient available RAM for safe CPU takeover; keep old task')
    return workers


def cmdline(pid):
    try:return (Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
    except FileNotFoundError:return []


def available_memory():
    available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
    for limit_path,used_path in (('/sys/fs/cgroup/memory.max','/sys/fs/cgroup/memory.current'),
                               ('/sys/fs/cgroup/memory/memory.limit_in_bytes','/sys/fs/cgroup/memory/memory.usage_in_bytes')):
        try:
            limit=Path(limit_path).read_text().strip()
            if limit!='max':available=min(available,max(0,int(limit)-int(Path(used_path).read_text())))
        except (FileNotFoundError,ValueError):pass
    return available


def main():
    import fcntl
    a=argparse.ArgumentParser();a.add_argument('--directory',type=Path,required=True);a.add_argument('--root',type=Path,required=True)
    a.add_argument('--commit',required=True);a.add_argument('--workers',type=int,default=2)
    x=a.parse_args();base=x.directory.resolve();root=x.root.resolve()
    root.relative_to(Path('/home/jovyan/zzx').resolve());base.relative_to(root/'records')
    if base.name!='research_phase15_recoverability_20261012T233532_842792':raise RuntimeError('unexpected Phase15 attempt')
    if x.workers not in range(1,5):raise RuntimeError('workers must be 1..4')
    sys.path.insert(0,str(base/'code/scripts'))
    from phase15_common import validate,verify_code,write,now
    from d30_common import live_owned,lock_free
    with (base/'cpu_acceleration_registration.lock').open('a') as guard:
        fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        existing=list(base.glob('cpu_acceleration_*_*'))
        if existing:
            print('CPU_ACCELERATION_ALREADY_PREPARED',*[str(v) for v in existing]);return
        validate(base);verify_code(base);state=read(base/'queue_status.json')
        if state['status']=='PHASE15_COMPLETE_AWAITING_REVIEW':print('ALREADY_COMPLETE no takeover needed');return
        assert_stage(state)
        if (base/'analysis/D/complete.json').exists():raise RuntimeError('D already complete; wait for original summary')
        if not live_owned(state['controller_pid'],base):raise RuntimeError('original controller not live; diagnose separately')
        available=available_memory()
        cpus=len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else os.cpu_count()
        workers=choose_workers(x.workers,available,cpus)
        commit=subprocess.check_output(['git','-C',str(root),'rev-parse',x.commit+'^{commit}'],text=True).strip()
        attempt=base/('cpu_acceleration_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()))
        attempt.mkdir();code=attempt/'code'
        for name in FILES:
            path=code/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+name]))
        write(attempt/'code_manifest.json',dict(commit=commit,files={name:sha(code/name) for name in FILES}))
        for name in ('temporary','cache'):(attempt/name).mkdir()
        env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',
            OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
            TMPDIR=str(attempt/'temporary'),TMP=str(attempt/'temporary'),TEMP=str(attempt/'temporary'),
            XDG_CACHE_HOME=str(attempt/'cache'),TORCH_HOME=str(attempt/'cache/torch'),HF_HOME=str(attempt/'cache/huggingface'),
            MPLCONFIGDIR=str(attempt/'cache/matplotlib'),
            PYTHONPATH=os.pathsep.join([str(code/'scripts'),str(base/'code/scripts'),str(base/'code')]))
        with (attempt/'cpu_equivalence_checks.log').open('x') as log:
            subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(code/'tests'),'-p','test_phase15_acceleration.py','-v'],
                cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=900)
        # Recheck after CPU proof: only the exact D child is authorized to stop.
        state=read(base/'queue_status.json');assert_stage(state)
        if (base/'analysis/D/complete.json').exists():print('D_COMPLETE no interruption; let original summarize');return
        child=state.get('current_stage_pid',-1);controller=state['controller_pid'];args=cmdline(child)
        if (str(base).encode() not in args or b'D' not in args or b'--phase' not in args or
            not any(v.endswith(b'/analyze_phase15.py') for v in args) or not live_owned(controller,base)):
            raise RuntimeError('D child identity differs; old process left untouched')
        write(attempt/'original_state_before_stop.json',state)
        if (base/'analysis/D/progress.json').exists():
            (attempt/'original_D_progress_before_stop.json').write_bytes((base/'analysis/D/progress.json').read_bytes())
        print('CPU_ACCELERATION_CONTROLLED_STOP_D',child,'PRESERVE_COMPLETED_CASES',flush=True)
        os.kill(child,signal.SIGTERM)
        tick=time.monotonic()
        while live_owned(child,base) or live_owned(controller,base):
            if time.monotonic()-tick>60:raise RuntimeError('old process not exited; do not start another worker')
            time.sleep(1)
        if not lock_free(base):raise RuntimeError('original controller lock not released')
        stopped=read(base/'queue_status.json')
        if stopped['status']!='TECHNICAL_FAILURE_HOLD' or any(j['status']!='COMPLETE' for j in stopped['jobs'].values()):
            raise RuntimeError('unexpected stop state; preserve and diagnose')
        write(attempt/'original_state_after_controlled_stop.json',stopped)
        if (base/'technical_failure.json').exists():
            (attempt/'controlled_stop_failure_receipt.json').write_bytes((base/'technical_failure.json').read_bytes())
        write(attempt/'takeover.json',dict(original_directory=str(base),original_plan_sha256=sha(base/'plan.json'),
            original_code_sha256=sha(base/'code_manifest.json'),workers=workers,available_memory_bytes=available,
            memory_policy='12GiB per worker + 8GiB reserve; max4; CPU affinity bounded',
            optimizer_updates=0,new_cases_added=0,gpu_jobs_repeated=0,automatic_retry=False,
            interrupted_inflight_case_may_be_reprocessed=True,registered_at=now(),execution_commit=commit))
        stopped.update(status='CPU_ACCELERATION_REGISTERED',observed_at=now(),error=None,
            acceleration_directory=str(attempt),automatic_retry=False,new_training_dispatched=False)
        write(base/'queue_status.json',stopped)
        logpath=attempt/'controller.log'
        cmd=[sys.executable,'-u','-B',str(code/'scripts/run_phase15_acceleration.py'),'--directory',str(base),'--attempt',str(attempt)]
        with logpath.open('x') as log:
            proc=subprocess.Popen(['nohup',*cmd],cwd=code,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        stopped.update(controller_pid=proc.pid);write(base/'queue_status.json',stopped)
        write(attempt/'launch.json',dict(controller_pid=proc.pid,command=cmd,log=str(logpath)))
        print('CPU_ACCELERATION_REGISTERED',attempt,'PID='+str(proc.pid),'WORKERS='+str(workers),flush=True)
        print('CPU_ACCELERATION_LOG',logpath,flush=True)


if __name__=='__main__':main()
