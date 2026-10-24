"""Two physical GPU lanes, actual smoke before full list, fail-closed/no retry."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
from phase15_common import *


def start(base,script,args=(),gpu=None,log_name=None):
    code=base/'code'
    env=dict(os.environ,CUDA_VISIBLE_DEVICES='' if gpu is None else str(gpu),PYTHONDONTWRITEBYTECODE='1',
        OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',TMPDIR=str(base/'temporary'),
        TMP=str(base/'temporary'),TEMP=str(base/'temporary'),XDG_CACHE_HOME=str(base/'cache'),
        TORCH_HOME=str(base/'cache/torch'),MPLCONFIGDIR=str(base/'cache/matplotlib'),
        CUDA_CACHE_PATH=str(base/'cache/cuda'),TRITON_CACHE_DIR=str(base/'cache/triton'),PYTORCH_KERNEL_CACHE_PATH=str(base/'cache/torch_kernels'),HF_HOME=str(base/'cache/huggingface'),
        PYTHONPATH=os.pathsep.join([str(code),str(code/'scripts')]))
    cmd=[sys.executable,'-u','-B',str(code/'scripts'/script),'--directory',str(base),*map(str,args)]
    f=base/'logs'/((log_name or script.replace('.py',''))+'.log')
    with f.open('x') as log:
        proc=subprocess.Popen(cmd,cwd=code,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    return proc


def main(base):
    import fcntl
    p=validate(base);verify_code(base)
    lock=(base/'controller.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    state=read(base/'queue_status.json')
    if state['status']!='REGISTERED_PENDING_PREPARATION':
        raise RuntimeError('controller cannot restart/resume failed or completed queue')
    state.update(controller_pid=os.getpid(),optimizer_updates=0)
    children=[];active={};eproc=None
    def report(status=None):
        if status:state['status']=status
        state['observed_at']=now();write(base/'queue_status.json',state)
    def sync(script,args=(),gpu=None,log_name=None,timeout=6*3600):
        proc=start(base,script,args,gpu,log_name);children.append(proc)
        tick=time.monotonic();state['current_stage_pid']=proc.pid
        while proc.poll() is None:
            if eproc is not None and eproc.poll() not in (None,0):
                raise RuntimeError('E CPU profile failed')
            if time.monotonic()-tick>timeout:raise RuntimeError('technical stage timeout; not global scientific deadline')
            report();time.sleep(5)
        if proc.returncode:raise RuntimeError(script+' exit='+str(proc.returncode))
        state.pop('current_stage_pid',None)
    try:
        report('PREPARING_FIXED_CACHE_AND_MAPS')
        sync('prepare_phase15.py')
        report('SMOKE_GPU0')
        eproc=start(base,'analyze_phase15.py',['--phase','E'],log_name='analysis_E');children.append(eproc)
        state['E_pid']=eproc.pid
        sync('smoke_phase15.py',['--gpu','0'],gpu=0,log_name='smoke_gpu0')
        report('SMOKE_GPU1_CROSS_DEVICE')
        sync('smoke_phase15.py',['--gpu','1'],gpu=1,log_name='smoke_gpu1')
        for gpu in (0,1):
            s=read(base/'smoke'/('gpu'+str(gpu))/'complete.json')
            if not s['all_passed'] or s['binding']!=binding(base) or s['optimizer_updates']:
                raise RuntimeError('real smoke receipt failed')
        write(base/'smoke_pass.json',dict(binding=binding(base),passed=True,realization=1,tile='3_11',
            cpu_checks_sha256=sha(base/'cpu_checks.log'),gpu_smoke_sha256={str(g):sha(base/'smoke'/('gpu'+str(g))/'complete.json') for g in (0,1)},
            optimizer_updates=0,no_scientific_selection=True,observed_at=now()))
        report('RUNNING_ZERO_TRAINING')
        while any(x['status']!='COMPLETE' for x in state['jobs'].values()):
            if eproc.poll() not in (None,0):raise RuntimeError('E CPU analysis failed')
            for gpu,(proc,j,tick) in list(active.items()):
                rc=proc.poll()
                if rc is None:
                    if time.monotonic()-tick>6*3600:raise RuntimeError('worker technical timeout '+j['id'])
                    continue
                if rc:
                    state['jobs'][j['id']].update(status='TECHNICAL_FAILURE',exit_code=rc)
                    raise RuntimeError('worker failed '+j['id']+'; no automatic retry')
                accept_job(base,j)
                state['jobs'][j['id']].update(status='COMPLETE',completed_at=now())
                del active[gpu]
                print('PHASE15_JOB_COMPLETE',j['id'],'GPU',gpu,flush=True)
            for gpu in (0,1):
                candidates=ready(state['jobs'],p['jobs'])
                if gpu not in active and candidates:
                    j=candidates[0]
                    proc=start(base,'run_phase15.py',['--job',j['id'],'--gpu',gpu],gpu= gpu,log_name='job_'+j['id'])
                    children.append(proc);active[gpu]=(proc,j,time.monotonic())
                    state['jobs'][j['id']].update(status='RUNNING',gpu=gpu,pid=proc.pid,started_at=now())
                    print('PHASE15_START',j['id'],'GPU',gpu,flush=True)
            report();time.sleep(5)
        while eproc.poll() is None:report('WAITING_CPU_E');time.sleep(5)
        if eproc.returncode:raise RuntimeError('E failed')
        report('CPU_ORACLE_AND_CONDITIONAL_COUNTS')
        sync('analyze_phase15.py',['--phase','D'],log_name='analysis_D',timeout=24*3600)
        report('SUMMARIZING_ALL_FIVE_DIAGNOSTICS')
        sync('summarize_phase15.py',timeout=6*3600)
        state.update(summary_sha256=sha(base/'summary.json'),new_training_dispatched=False)
        report('PHASE15_COMPLETE_AWAITING_REVIEW')
        print('PHASE15_COMPLETE NO_AUTOMATIC_TRAINING',flush=True)
    except BaseException as exc:
        for proc in children:
            if proc.poll() is None:proc.terminate()
        for proc in children:
            if proc.poll() is None:
                try:proc.wait(timeout=30)
                except subprocess.TimeoutExpired:proc.kill();proc.wait()
        for job in state['jobs'].values():
            if job['status']=='RUNNING':job.update(status='TERMINATED_HOLD')
        state.update(error=str(exc),automatic_retry=False,new_training_dispatched=False)
        report('SMOKE_FAILED_HOLD' if not (base/'smoke_pass.json').exists() else 'TECHNICAL_FAILURE_HOLD')
        write(base/'technical_failure.json',dict(error=str(exc),observed_at=now(),no_retry=True))
        raise
    finally:lock.close()


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',type=Path,required=True)
    main(a.parse_args().directory.resolve())
