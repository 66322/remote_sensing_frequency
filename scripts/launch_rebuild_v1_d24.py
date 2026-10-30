"""Standalone nohup bootstrap and bounded two-GPU D24 queue. No resource probe."""
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

PREFIX='records/research_d24_overnight_plan_20261001/'
FILES=('model/rebuild_v1_night_screen.py','model/rebuild_v1_d21_detail.py','model/rebuild_v1_d24.py',
       'scripts/d23_engine.py','scripts/d23_lifecycle.py','scripts/d24_common.py',
       'scripts/d24_data.py','scripts/d24_objectives.py','scripts/d24_evaluation.py',
       'scripts/run_rebuild_v1_d24.py','scripts/launch_rebuild_v1_d24.py',
       'scripts/status_rebuild_v1_d24.py','scripts/summarize_rebuild_v1_d24.py',
       'scripts/upload_rebuild_v1_d24_records.py','tests/test_d24.py',PREFIX+'plan.json',PREFIX+'jobs.csv')

def now():return datetime.now().astimezone().isoformat()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):
    temp=path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    os.replace(temp,path)

def next_job(jobs,state,gpu):
    return next((j for j in sorted(jobs,key=lambda j:j['priority'])
                 if j['gpu']==gpu and state['jobs'][j['id']]['status']=='PENDING'),None)

def stop_owned(process):
    if process.poll() is None:
        os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL)
            process.wait()

def is_live(pid,base):
    path=Path('/proc')/str(pid)/'cmdline'
    return path.exists() and str(base).encode() in path.read_bytes()

def check_device(gpu,uuids):
    # Only check competing processes, not memory/utilization thresholds or budgets.
    text=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid',
                                  '--format=csv,noheader'],text=True)
    for line in text.splitlines():
        if ',' not in line:continue
        uuid,pid=(v.strip() for v in line.split(',',1))
        if uuid==uuids[gpu] and pid.isdigit() and (Path('/proc')/pid).exists():
            raise RuntimeError('GPU %d has another live process %s; no process will be killed'%(gpu,pid))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--directory',type=Path,required=True)
    ap.add_argument('--commit',required=True)
    ap.add_argument('--resume-queue',action='store_true')
    args=ap.parse_args()
    root=args.root.resolve();root.relative_to(Path('/home/jovyan/zzx').resolve())
    base=args.directory.resolve();base.relative_to(root/'records')
    if not base.name.startswith('research_d24_overnight_'):raise ValueError('unexpected directory')
    base.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=(base/'controller.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    commit=subprocess.check_output(['git','-C',str(root),'rev-parse',args.commit+'^{commit}'],text=True).strip()
    code=base/'code'
    if args.resume_queue:
        binding=read(base/'code_manifest.json')
        if binding['commit']!=commit:raise ValueError('resume must use the original execution commit')
        for name,digest in binding['files'].items():
            if sha(code/name)!=digest:raise ValueError('resume snapshot changed: '+name)
    else:
        if (base/'plan.json').exists() or code.exists():
            raise ValueError('existing queue requires --resume-queue; no output is overwritten')
        binding=dict(commit=commit,files={})
        for name in FILES:
            raw=subprocess.check_output(['git','-C',str(root),'show',commit+':'+name])
            target=code/name;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as f:f.write(raw)
            binding['files'][name]=sha(target)
        write(base/'code_manifest.json',binding)
        plan=read(code/PREFIX/'plan.json')
        plan['execution_commit']=commit
        plan['created_at']=now()
        plan['status']='EXECUTION_CONFIGURED'
        write(base/'plan.json',plan)
        (base/'execution_commit.txt').write_text(commit+'\n')
    plan=read(base/'plan.json')
    # Validate the scientific contract using the snapshotted standard-library helper.
    sys.path.insert(0,str(code/'scripts'))
    from d24_common import validate_plan
    jobs=validate_plan(plan)
    state=read(base/'queue_status.json') if args.resume_queue else dict(jobs={})
    for job in jobs:
        row=state['jobs'].get(job['id'],{})
        if is_live(row.get('pid',-1),base):raise RuntimeError('old worker still alive: '+job['id'])
        complete=base/'jobs'/job['id']/'complete.json'
        if complete.exists():
            info=read(complete)
            if info['signature']['execution_commit']!=commit or sha(base/'jobs'/job['id']/'selected.pth')!=info['selected_checkpoint_sha256']:
                raise RuntimeError('completed job binding/checksum changed')
            row['status']='COMPLETE'
        elif args.resume_queue and row.get('status') in ('TECHNICAL_FAILURE','TIMEOUT'):
            # Failed jobs need a diagnosed correction; don't silently retry them.
            pass
        else:row['status']='PENDING'
        row.update(gpu=job['gpu'],job_directory=str(base/'jobs'/job['id']))
        state['jobs'][job['id']]=row
    state.update(status='RUNNING',controller_pid=os.getpid(),execution_commit=commit,observed_at=now())
    uuids={}
    text=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid','--format=csv,noheader'],text=True)
    for line in text.splitlines():
        index,uuid=(v.strip() for v in line.split(',',1));uuids[int(index)]=uuid
    if not all(g in uuids for g in (0,1)):raise RuntimeError('authorized GPU0/1 absent')
    state['gpu_uuids']={str(g):uuids[g] for g in (0,1)}
    active={}
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
             PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(base/'temporary'))
    (base/'temporary').mkdir(exist_ok=True)
    (base/'logs').mkdir(exist_ok=True)
    (base/'jobs').mkdir(exist_ok=True)
    last_print=0
    try:
        while True:
            for gpu in (0,1):
                if gpu not in active:
                    job=next_job(jobs,state,gpu)
                    if job is None:continue
                    row=state['jobs'][job['id']]
                    try:check_device(gpu,uuids)
                    except Exception as exc:
                        row.update(status='TECHNICAL_FAILURE',error=str(exc),completed_at=now())
                        print('D24_START_FAILURE',job['id'],str(exc),flush=True)
                        continue
                    stamp=datetime.now().strftime('%Y%m%dT%H%M%S%f')
                    logfile=base/'logs'/(job['id']+'_'+stamp+'.log')
                    handle=logfile.open('x')
                    command=[sys.executable,'-u','-B',str(code/'scripts/run_rebuild_v1_d24.py'),
                             '--root',str(root),'--directory',str(base),'--job',job['id']]
                    if (base/'jobs'/job['id']/'last_train_state.pth').exists():command.append('--resume')
                    process=subprocess.Popen(command,cwd=code,env=dict(env,CUDA_VISIBLE_DEVICES=str(gpu)),
                           stdout=handle,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
                    row.update(status='RUNNING',pid=process.pid,started_at=now(),log_path=str(logfile),command=command)
                    active[gpu]=dict(process=process,handle=handle,job=job,began=time.monotonic())
                    print('D24_STARTED',gpu,job['id'],'pid='+str(process.pid),flush=True)
                item=active.get(gpu)
                if not item:continue
                process,job=item['process'],item['job']
                row=state['jobs'][job['id']]
                elapsed=time.monotonic()-item['began']
                progress=base/'jobs'/job['id']/'progress.json'
                if progress.exists():row['progress']=read(progress)
                row['elapsed_seconds']=elapsed
                timeout=elapsed>plan['runtime']['per_job_timeout_hours']*3600
                if timeout:stop_owned(process)
                code_exit=process.poll()
                if code_exit is not None:
                    complete=base/'jobs'/job['id']/'complete.json'
                    row.update(returncode=code_exit,completed_at=now(),elapsed_seconds=elapsed,
                               status='TIMEOUT' if timeout else 'COMPLETE' if code_exit==0 and complete.exists() else 'TECHNICAL_FAILURE')
                    if row['status']=='COMPLETE':
                        row['selected']=read(complete)['selected']
                    else:
                        row['error_tail']='\n'.join(Path(row['log_path']).read_text(errors='replace').splitlines()[-20:])
                    item['handle'].close();del active[gpu]
                    print('D24_JOB_STATUS',job['id'],row['status'],flush=True)
            state['observed_at']=now()
            write(base/'queue_status.json',state)
            if time.monotonic()-last_print>=60:
                for gpu,item in active.items():
                    row=state['jobs'][item['job']['id']];p=row.get('progress',{})
                    print('D24_PROGRESS',gpu,item['job']['id'],p.get('phase','initializing'),
                          'step='+str(p.get('step',0)),'elapsed_minutes=%.1f'%(row['elapsed_seconds']/60),flush=True)
                last_print=time.monotonic()
            if not active and not any(r['status']=='PENDING' for r in state['jobs'].values()):break
            time.sleep(5)
        state['status']='COMPLETE' if all(r['status']=='COMPLETE' for r in state['jobs'].values()) else 'COMPLETE_WITH_TECHNICAL_FAILURES'
        state['completed_at']=now();state['observed_at']=now()
        write(base/'queue_status.json',state)
        result=subprocess.run([sys.executable,'-B',str(code/'scripts/summarize_rebuild_v1_d24.py'),
                               '--directory',str(base)],cwd=code)
        print('D24_QUEUE_FINISHED',state['status'],'summary_exit='+str(result.returncode),flush=True)
        print('D24_UPLOAD_READY',str(code/'scripts/upload_rebuild_v1_d24_records.py'),flush=True)
        return 0 if state['status']=='COMPLETE' and result.returncode==0 else 2
    except BaseException:
        state.update(status='CONTROLLER_INTERRUPTED',observed_at=now(),
                     interruption='workers in detached sessions may still be alive; never launch a duplicate queue')
        write(base/'queue_status.json',state)
        # Detached workers are intentionally preserved on terminal/controller interruption.
        raise
    finally:
        for item in active.values():item['handle'].close()

if __name__=='__main__':sys.exit(main())
