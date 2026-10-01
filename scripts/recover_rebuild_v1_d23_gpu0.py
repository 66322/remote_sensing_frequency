"""Restart failed TS on GPU0 while the old controller drains the existing TF.

No existing process is signalled. Merge records only after the old controller
and TF have exited, then hand the remaining jobs to the fixed resume queue.
"""
import argparse
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def read(path):return json.loads(Path(path).read_text())


def process_matches(pid,base,worker=False):
    path=Path('/proc')/str(pid)/'cmdline'
    if not path.exists():return False
    try:argv=path.read_bytes().split(b'\0')
    except FileNotFoundError:return False
    prefix=str(base).encode()
    if not any(a==prefix or prefix+b'/' in a for a in argv):return False
    if worker and not any(a.endswith(b'/run_rebuild_v1_d23.py') for a in argv):
        return False
    return True


def complete(job):
    marker=job/'formal_complete.json'
    return marker.is_file() and read(marker).get('global_step')==4000 and (job/'evaluation/summary.json').is_file()


def merge_recovered(state,job,log,pid):
    if state['jobs']['TS'].get('status') not in ('TECHNICAL_FAILURE','COMPLETE'):
        raise RuntimeError('TS status changed during recovery; refuse overwrite')
    state['jobs']['TS']=dict(gpu=0,pid=pid,status='COMPLETE',returncode=0,
      job_directory=str(job),log_path=str(log),observed_at=datetime.now().astimezone().isoformat())
    state.update(status='PARTIAL_RECOVERED',observed_at=datetime.now().astimezone().isoformat())
    return state


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--commit',required=True)
    ap.add_argument('--previous-controller',type=int,required=True)
    args=ap.parse_args();root=args.root.resolve();root.relative_to(Path('/home/jovyan/zzx').resolve())
    base=args.directory.resolve();base.relative_to(root/'records')
    if not base.name.startswith('research_d23_b_formal_'):raise ValueError('unexpected directory')
    import fcntl
    mutex=(base/'gpu0_recovery.lock').open('a')
    fcntl.flock(mutex,fcntl.LOCK_EX|fcntl.LOCK_NB)
    state=read(base/'queue_status.json')
    if state.get('status') not in ('FAILURE_DRAINING','TECHNICAL_FAILURE'):
        raise RuntimeError('expected failed queue; refuse to overlap a running queue')
    if state['jobs'].get('TS',{}).get('status')!='TECHNICAL_FAILURE':
        raise RuntimeError('TS is not the known failed job')
    ts=state['jobs']['TS'];tf=state['jobs'].get('TF')
    if not tf:raise RuntimeError('existing TF record absent')
    old_ts=Path(ts['job_directory']).resolve();old_ts.relative_to(base)
    tf_job=Path(tf['job_directory']).resolve();tf_job.relative_to(base)
    if process_matches(ts.get('pid',-1),base,True):raise RuntimeError('TS worker still exists')
    for arm,row in state['jobs'].items():
        if arm!='TF' and process_matches(row.get('pid',-1),base,True):
            raise RuntimeError('another worker is active: '+arm)
    if not process_matches(tf.get('pid',-1),base,True) and not complete(tf_job):
        raise RuntimeError('TF stopped without completion; inspect its log before recovery')
    stamp=datetime.now().strftime('%Y%m%dT%H%M%S%f')
    code=base/('code_gpu0_recovery_'+stamp);code.mkdir()
    commit=subprocess.check_output(['git','-C',str(root),'rev-parse',args.commit+'^{commit}'],text=True).strip()
    def extract(name):
        p=code/name;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(subprocess.check_output(['git','-C',str(root),'show',commit+':'+name]))
    extract('scripts/launch_rebuild_v1_d23_formal.py')
    spec=importlib.util.spec_from_file_location('fixed_queue',code/'scripts/launch_rebuild_v1_d23_formal.py')
    q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
    for name in q.FILES:extract(name)
    lock=read(base/'runtime_lock.json');q.validate_bindings(root,code,lock)
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
    event=base/('resume_event_gpu0repair_'+stamp+'.json')
    record=dict(controller_commit=commit,previous=state,created_at=datetime.now().astimezone().isoformat(),
                strategy='restart TS alone; retain TF; merge after old controller exits; resume remaining queue')
    q.write(event,record)
    # If TF is already complete and its controller has drained, standard resume
    # can immediately start both cards and needs no temporary single-arm worker.
    if complete(tf_job) and not process_matches(args.previous_controller,base):
        print('D23_RECOVERY_DIRECT_RESUME',flush=True)
    else:
        uuid=next(row['uuid'] for row in lock['gpus'] if row['gpu']==0)
        q.wait_for_gpu(0,uuid)
        job,resume=q.prepare_resume_job(base,'TS',old_ts,'gpu0repair_'+stamp)
        log=base/('TS_gpu0repair_'+stamp+'.log')
        with log.open('x') as stream:
            worker=subprocess.Popen([sys.executable,'-u','-B',str(code/'scripts/run_rebuild_v1_d23.py'),
              '--root',str(root),'--gpu','0','--output',str(job),'--mode','formal','--arm','TS',
              '--runtime-lock',str(base/'runtime_lock.json')]+(['--resume'] if resume else []),
              env=env,cwd=root,stdout=stream,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
            record.update(TS_pid=worker.pid,TS_job_directory=str(job),TS_log=str(log),status='TS_PROCESS_STARTED')
            q.write(event,record)
            print('D23_RECOVERY_TS_STARTED',worker.pid,str(log),flush=True)
            began=heartbeat=time.monotonic()
            while worker.poll() is None:
                if time.monotonic()-began>lock['job_wall_seconds']+30:
                    q.stop(worker);raise RuntimeError('recovery TS wall limit')
                if time.monotonic()-heartbeat>=30:
                    lines=log.read_text(errors='replace').splitlines()
                    print('D23_RECOVERY_PROGRESS',lines[-1] if lines else 'initializing',flush=True)
                    heartbeat=time.monotonic()
                time.sleep(2)
        if worker.returncode!=0 or not complete(job):
            record.update(status='TS_TECHNICAL_FAILURE',returncode=worker.returncode)
            q.write(event,record);raise RuntimeError('TS recovery failed; retained its log; existing TF untouched')
        record.update(status='TS_COMPLETE_WAITING_FOR_TF_AND_OLD_CONTROLLER');q.write(event,record)
        began=heartbeat=time.monotonic()
        while process_matches(tf.get('pid',-1),base,True) or process_matches(args.previous_controller,base):
            if time.monotonic()-began>lock['job_wall_seconds']+120:
                raise RuntimeError('old TF/controller has not exited; no processes interrupted')
            if time.monotonic()-heartbeat>=30:
                print('D23_RECOVERY_WAIT_EXISTING_TF_CONTROLLER',flush=True);heartbeat=time.monotonic()
            time.sleep(2)
        if not complete(tf_job):raise RuntimeError('TF did not complete; retain TS result for review')
        latest=read(base/'queue_status.json')
        q.write(base/'queue_status.json',merge_recovered(latest,job,log,worker.pid))
        record.update(status='MERGED_TS_COMPLETE');q.write(event,record)
    print('D23_RECOVERY_RESUME_REMAINING_QUEUE',flush=True)
    subprocess.run([sys.executable,'-u','-B',str(code/'scripts/launch_rebuild_v1_d23_formal.py'),
      '--root',str(root),'--commit',commit,'--directory',str(base),'--resume-queue'],
      env=env,cwd=root,stdin=subprocess.DEVNULL,check=True)
    mutex.close()


if __name__=='__main__':main()
