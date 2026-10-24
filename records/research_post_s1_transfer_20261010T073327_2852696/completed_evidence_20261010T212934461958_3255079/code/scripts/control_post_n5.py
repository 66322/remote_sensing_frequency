"""Four N5 jobs only; hold on failures; no automatic science followup."""
import argparse,fcntl,os,subprocess,sys,time
from datetime import datetime
from pathlib import Path
from post_n5_common import *
def job_complete(base,j,plan):
    f=base/'jobs'/j;c=read(f/'complete.json')
    if c['global_step']!=8000 or c['signature']['job']['id']!=j or c['signature']['execution_commit']!=plan['execution_commit'] or c['signature']['plan_sha256']!=sha(base/'plan.json') or c['signature']['initial_checkpoint_sha256']!=BASE_SHA or c['signature']['mask_manifest_sha256']!=sha(base/'mask_manifest.json') or c['test6_loaded'] or c['independent_final_loaded']:raise RuntimeError('invalid completed binding '+j)
    for tag in ('evaluation','fixed8000','content_evaluation','content_fixed8000'):
        if c[tag+'_summary_sha256']!=sha(f/tag/'summary.json'):raise RuntimeError('summary SHA changed '+j)
    if sha(f/'selected.pth')!=c['selected_checkpoint_sha256']:raise RuntimeError('checkpoint SHA changed')
def run_stage(root,base,plan,state,env,uuids,check_device,popen=subprocess.Popen,sleep=time.sleep):
    active={};limit=3600*hours(plan['runtime']['per_job_timeout_hours'])
    try:
        while True:
            for gpu in sorted((0,1),key=lambda g:g not in active):
                failed=any(r['status'] in ('TECHNICAL_FAILURE','TIMEOUT') for r in state['jobs'].values())
                if gpu not in active and not failed:
                    j=next((j for j in IDS if state['jobs'][j]['gpu']==gpu and state['jobs'][j]['status']=='PENDING'),None)
                    if j:
                        try:check_device(gpu,uuids)
                        except RuntimeError as exc:state['jobs'][j]['device_wait']=str(exc);continue
                        if (base/'jobs'/j).exists():raise RuntimeError('preserve existing job directory; explicit diagnosis required '+j)
                        log=base/'logs'/(j+'_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log');handle=log.open('x')
                        cmd=[sys.executable,'-u','-B',str(base/'code/scripts/run_post_n5.py'),'--root',str(root),'--directory',str(base),'--job',j,'--gpu',str(gpu)]
                        proc=popen(cmd,cwd=base/'code',env=dict(env,CUDA_VISIBLE_DEVICES=str(gpu)),stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
                        active[gpu]=(j,proc,handle);state['jobs'][j].update(status='RUNNING',pid=proc.pid,log_path=str(log),started_at=now())
                        # Persist immediately to close dispatch-before-loop status gaps.
                        write(base/'queue_status.json',state);print('N5_START',gpu,j,proc.pid,flush=True)
                if gpu in active:
                    j,proc,handle=active[gpu];row=state['jobs'][j];progress=base/'jobs'/j/'progress.json'
                    if progress.exists():row['progress']=read(progress)
                    if proc.poll() is None and not row.get('timed_out') and (datetime.now().astimezone()-datetime.fromisoformat(row['started_at'])).total_seconds()>limit:
                        proc.terminate();row['timed_out']=True;row['timeout_at']=now()
                    if proc.poll() is None and row.get('timed_out') and (datetime.now().astimezone()-datetime.fromisoformat(row['timeout_at'])).total_seconds()>60:proc.kill()
                    rc=proc.poll()
                    if rc is not None:
                        if rc==0 and (base/'jobs'/j/'complete.json').exists():job_complete(base,j,plan);status='COMPLETE'
                        else:status='TIMEOUT' if row.get('timed_out') else 'TECHNICAL_FAILURE'
                        row.update(status=status,returncode=rc,completed_at=now());handle.close();del active[gpu];print('N5_JOB',j,status,flush=True)
            state['observed_at']=now();write(base/'queue_status.json',state)
            if not active:
                if any(r['status'] in ('TECHNICAL_FAILURE','TIMEOUT') for r in state['jobs'].values()):return False
                if all(r['status']=='COMPLETE' for r in state['jobs'].values()):return True
            sleep(5)
    finally:
        for _,_,handle in active.values():handle.close()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args()
    root,base=directories(a.root,a.directory);p=read(base/'plan.json');validate(p);verify_snapshot(base)
    with (base/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state=read(base/'queue_status.json');state.update(controller_pid=os.getpid(),observed_at=now());write(base/'queue_status.json',state)
        try:
            if any(r['status']!='PENDING' for r in state['jobs'].values()):raise RuntimeError('existing jobs require explicit recovery; no retry')
            with (root/'records/post_ab_successor.lock').open('a') as lease:
                fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
                provenance=released(root);write(base/'predecessor_acceptance.json',provenance)
                env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONPATH=os.pathsep.join([str(base/'code'),str(base/'code/scripts')]))
                state.update(status='PREPARING_MASKS',observed_at=now());write(base/'queue_status.json',state)
                with (base/'preparation.log').open('x') as log:
                    subprocess.run([sys.executable,'-u','-B',str(base/'code/scripts/prepare_post_n5.py'),'--root',str(root),'--directory',str(base)],cwd=base/'code',env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=3600*hours(p['runtime']['cpu_stage_timeout_hours']))
                from launch_rebuild_v1_d27 import check_device
                uuids={int(x.split(',')[0]):x.split(',')[1].strip() for x in subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid','--format=csv,noheader'],text=True).splitlines()}
                state.update(status='RUNNING_N5',observed_at=now());write(base/'queue_status.json',state)
                if not run_stage(root,base,p,state,env,uuids,check_device):
                    state.update(status='HOLD_TECHNICAL_FAILURE',observed_at=now());write(base/'queue_status.json',state);return 2
                subprocess.run([sys.executable,'-B',str(base/'code/scripts/summarize_post_n5.py'),'--directory',str(base)],cwd=base/'code',env=env,check=True)
                state.update(status='N5_COMPLETE_AWAITING_REVIEW',screen_sha256=sha(base/'n5_screen.json'),observed_at=now());write(base/'queue_status.json',state)
                print('N5_COMPLETE_UPLOAD_AND_REVIEW',base,'NO_AUTOMATIC_N3_R1_N4_R2',flush=True);return 0
        except BaseException as exc:
            state.update(status='CONTROLLER_INTERRUPTED',error=str(exc),observed_at=now(),recovery_rule='workers may remain alive; diagnose/adopt explicitly, never repeat registration');write(base/'queue_status.json',state);raise
if __name__=='__main__':sys.exit(main())
