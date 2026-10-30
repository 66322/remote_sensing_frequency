"""Finite two-lane diagnostics, failure holds and explicit recovery only."""
import argparse,os,subprocess,sys,time
from datetime import datetime
from pathlib import Path
from post_n3_s1_common import *
def run_stage(root,base,p,state,env,uuids,check_device,popen=subprocess.Popen,sleep=time.sleep,clock=time.monotonic,accept=complete_job):
    active={};limit=3600*hours(p['runtime']['per_job_timeout_hours'])
    try:
        while True:
            for gpu in sorted((0,1),key=lambda g:g not in active):
                failed=any(x['status'] in ('TECHNICAL_FAILURE','TIMEOUT') for x in state['jobs'].values())
                if gpu not in active and not failed:
                    j=next((x['id'] for x in p['jobs'] if x['gpu']==gpu and state['jobs'][x['id']]['status']=='PENDING'),None)
                    if j:
                        try:check_device(gpu,uuids)
                        except RuntimeError as exc:state['jobs'][j]['device_wait']=str(exc);continue
                        if (base/'jobs'/j).exists():raise RuntimeError('existing worker directory requires explicit recovery '+j)
                        log=base/'logs'/(j+'_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log');handle=log.open('x')
                        cmd=[sys.executable,'-u','-B',str(base/'code/scripts/run_post_n3_s1.py'),'--root',str(root),'--directory',str(base),'--job',j,'--gpu',str(gpu)]
                        try:proc=popen(cmd,cwd=base/'code',env=dict(env,CUDA_VISIBLE_DEVICES=str(gpu)),stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
                        except BaseException:handle.close();raise
                        active[gpu]=dict(job=j,process=proc,handle=handle,started=clock(),timeout_started=None)
                        state['jobs'][j].update(status='RUNNING',pid=proc.pid,started_at=now(),log_path=str(log))
                        write(base/'queue_status.json',state);print('N3_S1_START',gpu,j,proc.pid,flush=True)
                if gpu in active:
                    task=active[gpu];j=task['job'];proc=task['process'];row=state['jobs'][j]
                    progress=base/'jobs'/j/'progress.json'
                    if progress.exists():row['progress']=read(progress)
                    rc=proc.poll()
                    if rc is None and task['timeout_started'] is None and clock()-task['started']>limit:
                        proc.terminate();task['timeout_started']=clock();row.update(timed_out=True,timeout_at=now())
                    if rc is None and task['timeout_started'] is not None and clock()-task['timeout_started']>60:proc.kill()
                    rc=proc.poll()
                    if rc is not None:
                        if row.get('timed_out'):status='TIMEOUT'
                        elif rc==0:
                            accept(base,j,p);status='COMPLETE'
                        else:status='TECHNICAL_FAILURE'
                        row.update(status=status,returncode=rc,completed_at=now());task['handle'].close();del active[gpu]
                        print('N3_S1_JOB',j,status,flush=True)
            state['observed_at']=now();write(base/'queue_status.json',state)
            if not active:
                if any(x['status'] in ('TECHNICAL_FAILURE','TIMEOUT') for x in state['jobs'].values()):return False
                if all(x['status']=='COMPLETE' for x in state['jobs'].values()):return True
            sleep(p['runtime']['wait_poll_seconds'])
    finally:
        for t in active.values():t['handle'].close()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args()
    root,base=directories(a.root,a.directory);p=read(base/'plan.json');validate_plan(p);verify_snapshot(base)
    import fcntl
    with (base/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state=read(base/'queue_status.json');state.update(controller_pid=os.getpid(),observed_at=now());write(base/'queue_status.json',state)
        try:
            if state['CPU']!='PENDING' or any(x['status']!='PENDING' for x in state['jobs'].values()):raise RuntimeError('partial controller run requires explicit recovery; no retry')
            with (root/'records/post_ab_successor.lock').open('a') as lease:
                fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
                write(base/'predecessor_acceptance.json',released(root))
                env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONPATH=os.pathsep.join([str(base/'code'),str(base/'code/scripts')]))
                state.update(status='PREPARING_FIXED_MASKS',CPU='RUNNING',observed_at=now());write(base/'queue_status.json',state)
                with (base/'preparation.log').open('x') as log:
                    subprocess.run([sys.executable,'-u','-B',str(base/'code/scripts/prepare_post_n3_s1.py'),'--root',str(root),'--directory',str(base)],cwd=base/'code',env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=3600*hours(p['runtime']['cpu_stage_timeout_hours']))
                state.update(CPU='COMPLETE',status='RUNNING_N3_S1',observed_at=now());write(base/'queue_status.json',state)
                from launch_rebuild_v1_d27 import check_device
                uuids={int(x.split(',')[0]):x.split(',')[1].strip() for x in subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid','--format=csv,noheader'],text=True).splitlines()}
                if not {0,1}.issubset(uuids):raise RuntimeError('authorized physical GPUs absent')
                state['gpu_uuids']={str(g):uuids[g] for g in (0,1)}
                if not run_stage(root,base,p,state,env,uuids,check_device):
                    state.update(status='HOLD_TECHNICAL_FAILURE',observed_at=now());write(base/'queue_status.json',state);return 2
                # Run summary as a standalone entry to exercise its imports/exit path.
                subprocess.run([sys.executable,'-u','-B',str(base/'code/scripts/summarize_post_n3_s1.py'),'--directory',str(base)],cwd=base/'code',env=env,check=True,timeout=3600*hours(p['runtime']['cpu_stage_timeout_hours']))
                s=read(base/'n3_s1_screen.json');state.update(status='N3_S1_COMPLETE_AWAITING_REVIEW',screen_sha256=sha(base/'n3_s1_screen.json'),N3_gate=s['N3']['passed'],S1_gate=s['S1']['passed'],observed_at=now())
                write(base/'queue_status.json',state);print('N3_S1_COMPLETE_UPLOAD_AND_REVIEW',base,'NO_AUTOMATIC_FOLLOWUP',flush=True);return 0
        except BaseException as exc:
            state.update(status='CONTROLLER_INTERRUPTED',error=str(exc),observed_at=now(),recovery_rule='preserve detached workers; diagnose/adopt explicitly; no restart/retry')
            write(base/'queue_status.json',state);raise
if __name__=='__main__':sys.exit(main())
