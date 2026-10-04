"""One detached controller: D30 release -> A -> B -> C -> conditional F."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from datetime import datetime
FILES=['model/rebuild_v1_post_d30.py','scripts/post_d30_common.py','scripts/post_d30_data.py',
       'scripts/post_d30_evaluation.py','scripts/run_post_d30.py','scripts/summarize_post_d30.py',
       'scripts/launch_post_d30.py','scripts/status_post_d30.py','scripts/upload_post_d30_records.py',
       'tests/test_post_d30.py','scripts/post_d30_eval_compat.py','records/research_post_d30_design_20261003/plan.json']
PREFIX='research_post_d30_mechanisms_'
PREDECESSOR='research_d30_loss_decomposition_20261003T205144_2349167'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);temp=p.with_name(p.name+'.tmp')
    temp.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n');os.replace(temp,p)
def now():return datetime.now().astimezone().isoformat()
def sha(p):
    import hashlib
    digest=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):digest.update(b)
    return digest.hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True)
    ap.add_argument('--commit',required=True);ap.add_argument('--resume-queue',action='store_true');a=ap.parse_args()
    root=a.root.resolve();root.relative_to(Path('/home/jovyan/zzx'));base=a.directory.resolve();base.relative_to(root/'records')
    if not base.name.startswith(PREFIX):raise ValueError('unexpected queue directory')
    parent=root/'records'/PREDECESSOR;base.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=(base/'controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    common_lock=(root/'records/post_d30_successor.lock').open('a');fcntl.flock(common_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    commit=subprocess.check_output(['git','-C',str(root),'rev-parse',a.commit+'^{commit}'],text=True).strip();code=base/'code'
    inherited=read(parent/'code_manifest.json');original_plan=read(parent/'plan.json')
    if inherited['commit']!='9db12dfb7ee85dff91dd6c246c7f161b60aca603' or original_plan['execution_commit']!=inherited['commit']:raise RuntimeError('D30 predecessor source changed')
    if not a.resume_queue:
        if code.exists() or (base/'plan.json').exists():raise RuntimeError('existing queue requires --resume-queue')
        for name,digest in inherited['files'].items():
            source=parent/'code'/name
            if sha(source)!=digest:raise RuntimeError('source snapshot changed '+name)
            dest=code/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(source.read_bytes())
        for name in FILES:
            dest=code/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+name]))
        sys.path.insert(0,str(code/'scripts'))
        from post_d30_common import runtime_plan
        plan=runtime_plan(original_plan,read(code/'records/research_post_d30_design_20261003/plan.json'),commit,base)
        teacher=root/'records/research_d26_bidirectional_20261002T191253_1513109/jobs/B0/selected.pth'
        finished=read(teacher.parent/'complete.json')
        if finished['selected']['step']!=4000 or sha(teacher)!=finished['selected_checkpoint_sha256']:raise RuntimeError('bound D26 B0 selected teacher changed')
        plan['teacher']=dict(path=str(teacher),sha256=finished['selected_checkpoint_sha256'],step=4000,complete_sha256=sha(teacher.parent/'complete.json'))
        plan['source_D30_plan_sha256']=sha(parent/'plan.json');plan['created_at']=now()
        write(base/'plan.json',plan);(base/'execution_commit.txt').write_text(commit+'\n')
        write(base/'code_manifest.json',dict(commit=commit,inherited_D30_commit=inherited['commit'],files={p.relative_to(code).as_posix():sha(p) for p in code.rglob('*') if p.is_file()}))
    else:
        plan=read(base/'plan.json')
        if plan['execution_commit']!=commit:raise RuntimeError('resume execution binding changed')
        sys.path.insert(0,str(code/'scripts'))
    from post_d30_common import validate_plan,predecessor_verdict,next_job,PHASES
    from d30_common import live_owned,lock_free
    validate_plan(plan)
    for name,digest in read(base/'code_manifest.json')['files'].items():
        if sha(code/name)!=digest:raise RuntimeError('immutable snapshot changed '+name)
    if sha(parent/'plan.json')!=plan['source_D30_plan_sha256']:raise RuntimeError('source D30 plan changed')
    sys.path.insert(0,str(code))
    from post_d30_eval_compat import check_conditions
    from post_d30_data import treatment
    checked=check_conditions(plan,treatment)
    print('PORTFOLIO_CONDITION_INTERFACE_PASS',len(checked),flush=True)
    for d in ('temporary','cache/torch','logs','jobs'):(base/d).mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(base/'temporary'),XDG_CACHE_HOME=str(base/'cache'),TORCH_HOME=str(base/'cache/torch'))
    state=read(base/'queue_status.json') if (base/'queue_status.json').exists() else dict(jobs={j['id']:dict(status='PENDING',gpu=j['gpu'],phase=j['phase']) for j in plan['jobs']})
    for j,row in state['jobs'].items():
        if live_owned(row.get('pid',-1),base):raise RuntimeError('detached worker still live '+j)
        path=base/'jobs'/j/'complete.json'
        if path.exists():
            record=read(path)
            if record['signature']['execution_commit']!=commit or record['signature']['plan_sha256']!=sha(base/'plan.json') or record['global_step']!=8000:raise RuntimeError('completed binding differs '+j)
            if sha(path.parent/'selected.pth')!=record['selected_checkpoint_sha256']:raise RuntimeError('completed checkpoint changed '+j)
            row['status']='COMPLETE'
        elif row.get('status')=='RUNNING':row['status']='PENDING'
        elif row.get('status') in ('TECHNICAL_FAILURE','TIMEOUT'):raise RuntimeError('technical failure needs explicit diagnosis '+j)
    state.update(status='VERIFYING_CPU',controller_pid=os.getpid(),execution_commit=commit,predecessor_directory=str(parent),observed_at=now());write(base/'queue_status.json',state)
    with (base/'cpu_checks.log').open('a') as log:
        try:subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(code/'tests'),'-p','test_post_d30.py','-v'],cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,check=True)
        except Exception:
            state.update(status='CPU_CHECK_FAILURE',observed_at=now());write(base/'queue_status.json',state);raise
    print('PORTFOLIO_CPU_CHECKS_PASS',flush=True)
    while True:
        previous=read(parent/'queue_status.json');workers=[r.get('pid') for r in previous['jobs'].values() if live_owned(r.get('pid',-1),parent)]
        verdict=predecessor_verdict(previous,lock_free(parent),bool(workers),live_owned(previous.get('controller_pid',-1),parent))
        state.update(status=verdict,predecessor_status=previous.get('status'),predecessor_observed_at=previous.get('observed_at'),predecessor_live_workers=workers,observed_at=now());write(base/'queue_status.json',state)
        if verdict=='READY':
            summary=read(parent/'screen_result.json')
            if summary['status']!='COMPLETE' or summary['test6_loaded']:raise RuntimeError('D30 summary not valid')
            binding=dict(directory=str(parent),queue_sha256=sha(parent/'queue_status.json'),summary_sha256=sha(parent/'screen_result.json'),completion={})
            for name in previous['jobs']:
                path=parent/'jobs'/name/'complete.json';r=read(path)
                if r['test6_loaded'] or r['signature']['execution_commit']!=inherited['commit']:raise RuntimeError('D30 job completion differs')
                if name.startswith('replay_') and r['new_tile_evaluations']!=24:raise RuntimeError('D30 replay count differs')
                if not name.startswith('replay_') and r['global_step']!=8000:raise RuntimeError('D30 training not complete')
                binding['completion'][name]=sha(path)
            write(base/'predecessor_binding.json',binding);break
        if verdict.startswith('HOLD'):print('PORTFOLIO_'+verdict,flush=True);return 2
        print('PORTFOLIO_WAITING_D30',previous['status'],flush=True);time.sleep(30)
    from launch_rebuild_v1_d27 import check_device
    uuids={int(x.split(',')[0]):x.split(',')[1].strip() for x in subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid','--format=csv,noheader'],text=True).splitlines()}
    if not all(g in uuids for g in (0,1)):raise RuntimeError('authorized GPU0/1 absent')
    state['gpu_uuids']={str(g):uuids[g] for g in (0,1)};active={};last_print=0.;env.pop('CUDA_VISIBLE_DEVICES',None)
    try:
        for phase,ids in PHASES.items():
            if phase=='F':
                frozen=read(base/'portfolio_screen.json')
                if not frozen['screens']['B3']['passed']:
                    for j in ids:state['jobs'][j].update(status='SKIPPED_GATE',reason='B3 frozen development gate did not pass')
                    state.update(conditional_F='SKIPPED_GATE',observed_at=now());write(base/'queue_status.json',state);print('PORTFOLIO_F_SKIPPED_GATE',flush=True);break
            state.update(status='RUNNING',phase=phase)
            while True:
                for gpu in (0,1):
                    if gpu not in active:
                        j=next_job(state,gpu,phase)
                        if j:
                            try:check_device(gpu,uuids)
                            except RuntimeError as exc:
                                state['jobs'][j]['device_wait']=str(exc)
                                if time.monotonic()-last_print>=60:print('PORTFOLIO_DEVICE_WAIT',gpu,str(exc),flush=True)
                                continue
                            path=base/'logs'/(j+'_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log');handle=path.open('x')
                            command=[sys.executable,'-u','-B',str(code/'scripts/run_post_d30.py'),'--root',str(root),'--directory',str(base),'--job',j,'--gpu',str(gpu)]
                            if (base/'jobs'/j/'last_train_state.pth').exists():command.append('--resume')
                            proc=subprocess.Popen(command,cwd=code,env=dict(env,CUDA_VISIBLE_DEVICES=str(gpu)),stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
                            active[gpu]=(j,proc,handle,time.monotonic());state['jobs'][j].update(status='RUNNING',pid=proc.pid,started_at=now(),log_path=str(path),command=command)
                            print('PORTFOLIO_STARTED',gpu,j,proc.pid,flush=True)
                    if gpu in active:
                        j,proc,handle,began=active[gpu];row=state['jobs'][j];path=base/'jobs'/j/'progress.json'
                        if path.exists():row['progress']=read(path)
                        row['elapsed_seconds']=time.monotonic()-began;rc=proc.poll()
                        if rc is not None:
                            row.update(status='COMPLETE' if rc==0 and (base/'jobs'/j/'complete.json').exists() else 'TECHNICAL_FAILURE',returncode=rc,completed_at=now())
                            handle.close();del active[gpu];print('PORTFOLIO_JOB_STATUS',j,row['status'],flush=True)
                state['observed_at']=now();write(base/'queue_status.json',state)
                if time.monotonic()-last_print>=60:
                    for gpu,(j,_,_,_) in active.items():print('PORTFOLIO_PROGRESS',gpu,j,state['jobs'][j].get('progress',{}),flush=True)
                    last_print=time.monotonic()
                if not active and not any(state['jobs'][j]['status']=='PENDING' for j in ids):break
                time.sleep(5)
            if any(state['jobs'][j]['status']!='COMPLETE' for j in ids):
                state.update(status='COMPLETE_WITH_TECHNICAL_FAILURES',observed_at=now());write(base/'queue_status.json',state);return 2
            subprocess.run([sys.executable,'-B',str(code/'scripts/summarize_post_d30.py'),'--directory',str(base)],cwd=code,env=env,check=True)
        state.update(status='COMPLETE',completed_at=now(),observed_at=now());write(base/'queue_status.json',state)
        print('PORTFOLIO_QUEUE_FINISHED COMPLETE',flush=True);print('PORTFOLIO_UPLOAD_READY',code/'scripts/upload_post_d30_records.py',flush=True);return 0
    except BaseException:
        state.update(status='CONTROLLER_INTERRUPTED',observed_at=now(),error='detached workers may remain alive; inspect before resume');write(base/'queue_status.json',state);raise
    finally:
        for _,_,handle,_ in active.values():handle.close()
if __name__=='__main__':sys.exit(main())
