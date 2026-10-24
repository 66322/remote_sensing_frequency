"""GPU0 single FIFO: D1, ten registered cells, E. No retry or extra family."""
import argparse,os,subprocess,sys,time
from datetime import datetime
from pathlib import Path
from post_s1_support_common import *
TASKS=['D1']+ORDER+['E']
def device_free(expected_uuid=None):
    rows=subprocess.check_output(['nvidia-smi','-i','0','--query-gpu=index,uuid','--format=csv,noheader'],text=True).strip().splitlines()
    if len(rows)!=1:raise RuntimeError('GPU0 binding not unique')
    index,uuid=[s.strip() for s in rows[0].split(',',1)]
    if index!='0' or expected_uuid is not None and uuid!=expected_uuid:raise RuntimeError('physical GPU0 identity changed')
    text=subprocess.check_output(['nvidia-smi','-i','0','--query-compute-apps=pid','--format=csv,noheader'],text=True)
    for line in text.splitlines():
        if line.strip().isdigit() and (Path('/proc')/line.strip()).exists():raise RuntimeError('GPU0 has competing live process '+line.strip())
    return uuid
def run_fifo(root,base,p,state,env,popen=subprocess.Popen,sleep=time.sleep,clock=time.monotonic,check=device_free,accept=accept_worker):
    uuid=None
    for task in TASKS:
        row=state['jobs'][task]
        if row['status']!='PENDING' or (base/'jobs'/task).exists():raise RuntimeError('partial artifacts require explicit recovery '+task)
        while True:
            try:uuid=check(uuid);break
            except RuntimeError as exc:
                row['device_wait']=str(exc);state.update(status='WAITING_GPU0',observed_at=now());write(base/'queue_status.json',state);sleep(p['runtime']['wait_poll_seconds'])
        row.pop('device_wait',None)
        entry='run_post_s1_support.py' if task in ORDER else 'run_post_s1_support_diagnostics.py'
        command=[sys.executable,'-u','-B',str(base/'code/scripts'/entry),'--root',str(root),'--directory',str(base),'--job',task,'--gpu','0']
        logfile=base/'logs'/(task+'_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log')
        began=clock();timed_out=False;sent_at=None
        with logfile.open('x') as handle:
            proc=popen(command,cwd=base/'code',env=dict(env,CUDA_VISIBLE_DEVICES='0'),stdin=subprocess.DEVNULL,
                stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
            row.update(status='RUNNING',pid=proc.pid,started_at=now(),log_path=str(logfile),command=command)
            state.update(status='RUNNING_'+task,physical_gpu=0,gpu_uuid=uuid,observed_at=now());write(base/'queue_status.json',state)
            print('SUPPORT_START GPU0',task,proc.pid,flush=True)
            while proc.poll() is None:
                progress=base/'jobs'/task/'progress.json'
                if progress.exists():row['progress']=read(progress)
                elapsed=clock()-began;row['elapsed_seconds']=elapsed
                if not timed_out and elapsed>3600*hours(p['runtime']['per_job_timeout_hours']):
                    timed_out=True;sent_at=clock();row.update(timed_out=True,timeout_at=now());print('SUPPORT_HARD_TIMEOUT',task,flush=True);proc.terminate()
                if timed_out and proc.poll() is None and clock()-sent_at>60:proc.kill()
                state['observed_at']=now();write(base/'queue_status.json',state);sleep(p['runtime']['wait_poll_seconds'])
            rc=proc.poll()
        if timed_out:status='TIMEOUT'
        elif rc:status='TECHNICAL_FAILURE'
        else:
            try:accept(base,task,p);status='COMPLETE'
            except BaseException as exc:row['acceptance_error']=str(exc);status='TECHNICAL_FAILURE'
        row.update(status=status,returncode=rc,completed_at=now());state['observed_at']=now();write(base/'queue_status.json',state)
        print('SUPPORT_JOB',task,status,flush=True)
        if status!='COMPLETE':return False
        if task in ('D1','E'):state[task]='COMPLETE'
    return True
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args()
    root,base=dirs(a.root,a.directory);p=validate(read(base/'plan.json'));verify_snapshot(base)
    import fcntl
    with (base/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state=read(base/'queue_status.json');state.update(controller_pid=os.getpid(),observed_at=now());write(base/'queue_status.json',state)
        try:
            if state['CPU']!='PENDING' or any(x['status']!='PENDING' for x in state['jobs'].values()):raise RuntimeError('partial run requires explicit recovery')
            with (root/'records/post_ab_successor.lock').open('a') as lease:
                fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB);write(base/'predecessor_acceptance.json',released(root))
                env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONPATH=os.pathsep.join([str(base/'code'),str(base/'code/scripts')]))
                state.update(status='PREPARING_D0_MASKS',CPU='RUNNING',observed_at=now());write(base/'queue_status.json',state)
                with (base/'preparation.log').open('x') as handle:
                    subprocess.run([sys.executable,'-u','-B',str(base/'code/scripts/prepare_post_s1_support.py'),'--root',str(root),'--directory',str(base)],
                        cwd=base/'code',env=env,stdout=handle,stderr=subprocess.STDOUT,check=True,timeout=3600*hours(p['runtime']['cpu_stage_timeout_hours']))
                state['CPU']='COMPLETE'
                if not run_fifo(root,base,p,state,env):
                    state.update(status='HOLD_TECHNICAL_FAILURE',observed_at=now());write(base/'queue_status.json',state);return 2
                with (base/'summary.log').open('x') as handle:
                    subprocess.run([sys.executable,'-u','-B',str(base/'code/scripts/summarize_post_s1_support.py'),'--directory',str(base)],
                        cwd=base/'code',env=env,stdout=handle,stderr=subprocess.STDOUT,check=True,timeout=3600*hours(p['runtime']['cpu_stage_timeout_hours']))
                screen=read(base/'support_screen.json')
                state.update(status='SUPPORT_COMPLETE_AWAITING_REVIEW',P7_gate=screen['P7_passed'],E_gate=screen['E_passed'],
                    Q=screen['Q_status'],screen_sha256=sha(base/'support_screen.json'),observed_at=now())
                write(base/'queue_status.json',state);print('SUPPORT_COMPLETE_UPLOAD_AND_REVIEW',base,'NO_AUTOMATIC_Q',flush=True);return 0
        except BaseException as exc:
            state.update(status='CONTROLLER_INTERRUPTED',error=str(exc),observed_at=now(),recovery_rule='preserve detached worker; inspect/adopt explicitly, no restart/retry')
            write(base/'queue_status.json',state);raise
if __name__=='__main__':sys.exit(main())
