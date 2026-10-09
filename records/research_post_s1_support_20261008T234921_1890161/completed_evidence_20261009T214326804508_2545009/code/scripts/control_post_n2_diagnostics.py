"""Wait for N2 release, audit, prepare E0/masks, then E1 and E2 on GPU0/1."""
import argparse,fcntl,os,subprocess,sys,time
from datetime import datetime
from pathlib import Path
from post_n2_diag_common import *
from d30_common import live_owned,lock_free

def wait_predecessor(base,plan,state,sleep=time.sleep):
    parent=Path(plan['predecessor_directory'])
    while True:
        previous=read(parent/'queue_status.json');live=live_owned(previous.get('controller_pid',-1),parent)
        workers=any(live_owned(row.get('pid',-1),parent) for row in previous.get('jobs',{}).values())
        verdict=predecessor_verdict(previous,live,workers,lock_free(parent))
        state.update(status=verdict,predecessor_status=previous['status'],predecessor_observed_at=previous.get('observed_at'),observed_at=now());write(base/'queue_status.json',state)
        print('DIAG_HANDOVER',verdict,previous['status'],flush=True)
        if verdict=='READY':return True
        if verdict.startswith('HOLD'):return False
        sleep(30)

def job_complete(base,j,plan):
    folder=base/'jobs'/j;c=read(folder/'complete.json')
    if c['optimizer_updates']!=0 or c['signature']['job']['id']!=j or c['signature']['execution_commit']!=plan['execution_commit'] or c['signature']['plan_sha256']!=sha(base/'plan.json') or c['summary_sha256']!=sha(folder/'summary.json') or c['test6_loaded'] or c['independent_final_loaded']:raise RuntimeError('diagnostic completion changed '+j)

def run_stage(root,base,plan,state,stage,env,uuids,check_device,popen=subprocess.Popen,sleep=time.sleep):
    active={};limit=3600*limit_hours(plan['runtime']['per_job_timeout_hours'])
    try:
        while True:
            for gpu in sorted((0,1),key=lambda g:g not in active):
                failed=any(r['status'] in ('TECHNICAL_FAILURE','TIMEOUT') for r in state['jobs'].values())
                if gpu not in active and not failed:
                    j=next_job(state,gpu,stage)
                    if j:
                        try:check_device(gpu,uuids)
                        except RuntimeError as exc:state['jobs'][j]['device_wait']=str(exc);continue
                        if (base/'jobs'/j).exists():raise RuntimeError('preserve existing job directory; explicit diagnosis required '+j)
                        log=base/'logs'/(j+'_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log');handle=log.open('x')
                        cmd=[sys.executable,'-u','-B',str(base/'code/scripts/run_post_n2_diagnostics.py'),'--root',str(root),'--directory',str(base),'--job',j,'--gpu',str(gpu)]
                        proc=popen(cmd,cwd=base/'code',env=dict(env,CUDA_VISIBLE_DEVICES=str(gpu)),stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
                        active[gpu]=(j,proc,handle);state['jobs'][j].update(status='RUNNING',pid=proc.pid,log_path=str(log),started_at=now())
                        # Persist immediately to close dispatch-before-loop status gaps.
                        write(base/'queue_status.json',state);print('DIAG_START',gpu,j,proc.pid,flush=True)
                if gpu in active:
                    j,proc,handle=active[gpu];row=state['jobs'][j];progress=base/'jobs'/j/'progress.json'
                    if progress.exists():row['progress']=read(progress)
                    if proc.poll() is None and not row.get('timed_out') and (datetime.now().astimezone()-datetime.fromisoformat(row['started_at'])).total_seconds()>limit:
                        proc.terminate();row['timed_out']=True
                    rc=proc.poll()
                    if rc is not None:
                        if rc==0 and (base/'jobs'/j/'complete.json').exists():job_complete(base,j,plan);status='COMPLETE'
                        else:status='TIMEOUT' if row.get('timed_out') else 'TECHNICAL_FAILURE'
                        row.update(status=status,returncode=rc,completed_at=now());handle.close();del active[gpu];print('DIAG_JOB',j,status,flush=True)
            state['observed_at']=now();write(base/'queue_status.json',state)
            if not active:
                if any(r['status'] in ('TECHNICAL_FAILURE','TIMEOUT') for r in state['jobs'].values()):return False
                if all(r['status']=='COMPLETE' for r in state['jobs'].values() if r['stage']==stage):return True
            sleep(5)
    finally:
        for _,_,handle in active.values():handle.close()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();root,base=dirs(a.root,a.directory)
    plan=validate(read(base/'plan.json'));verify_snapshot(base)
    lock=(base/'controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    state=read(base/'queue_status.json');state.update(controller_pid=os.getpid(),observed_at=now());write(base/'queue_status.json',state)
    common=None
    try:
        # No automatic controller resume: preserve alive or partially evaluated jobs.
        if any(r['status']!='PENDING' or live_owned(r.get('pid',-1),base) for r in state['jobs'].values()):raise RuntimeError('existing diagnostic jobs require explicit recovery')
        if not wait_predecessor(base,plan,state):return 2
        common=(root/'records/post_ab_successor.lock').open('a')
        while True:
            try:fcntl.flock(common,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:
                state.update(status='WAITING_SUCCESSOR_LOCK',observed_at=now());write(base/'queue_status.json',state);time.sleep(30)
        # Recheck after acquiring the shared lease; no source restart race.
        parent=Path(plan['predecessor_directory']);previous=read(parent/'queue_status.json')
        verdict=predecessor_verdict(previous,live_owned(previous.get('controller_pid',-1),parent),any(live_owned(r.get('pid',-1),parent) for r in previous['jobs'].values()),lock_free(parent))
        if verdict!='READY':raise RuntimeError('predecessor release changed after successor lock; '+verdict)
        env=dict(os.environ,CUDA_VISIBLE_DEVICES='');env['PYTHONPATH']=os.pathsep.join([str(base/'code'),str(base/'code/scripts')])
        state.update(status='CPU_AUDIT_AND_E0',E0='RUNNING',mask_preparation='RUNNING',observed_at=now());write(base/'queue_status.json',state)
        with (base/'cpu_preparation.log').open('x') as log:
            subprocess.run([sys.executable,'-u','-B',str(base/'code/scripts/post_n2_diag_runtime.py'),'--root',str(root),'--directory',str(base)],cwd=base/'code',env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=3600*limit_hours(plan['runtime']['cpu_stage_timeout_hours']))
        state.update(E0='COMPLETE',mask_preparation='COMPLETE');write(base/'queue_status.json',state)
        from launch_rebuild_v1_d27 import check_device
        uuids={int(x.split(',')[0]):x.split(',')[1].strip() for x in subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid','--format=csv,noheader'],text=True).splitlines()}
        if 0 not in uuids or 1 not in uuids:raise RuntimeError('authorized GPUs absent')
        state['gpu_uuids']={str(g):uuids[g] for g in (0,1)}
        for stage in ('E1','E2'):
            state.update(status='RUNNING_'+stage,observed_at=now());write(base/'queue_status.json',state)
            if not run_stage(root,base,plan,state,stage,env,uuids,check_device):
                state.update(status='HOLD_DIAGNOSTIC_TECHNICAL_FAILURE');write(base/'queue_status.json',state);return 2
        subprocess.run([sys.executable,'-B',str(base/'code/scripts/summarize_post_n2_diagnostics.py'),'--directory',str(base)],cwd=base/'code',env=env,check=True)
        screen=read(base/'diagnostic_screen.json');state.update(status='DIAGNOSTICS_COMPLETE_AWAITING_REVIEW',N5_problem_trigger=screen['E1']['N5_problem_trigger'],N3_problem_trigger=screen['E0']['N3_problem_trigger'],observed_at=now())
        write(base/'queue_status.json',state);print('DIAG_COMPLETE_UPLOAD_AND_REVIEW',base,'NO_AUTOMATIC_TRAINING',flush=True);return 0
    except BaseException as exc:
        state.update(status='CONTROLLER_INTERRUPTED',error=str(exc),observed_at=now(),recovery_rule='diagnose first; detached workers may remain alive; never auto-retry');write(base/'queue_status.json',state);raise
    finally:
        if common is not None:common.close()
        lock.close()
if __name__=='__main__':sys.exit(main())
