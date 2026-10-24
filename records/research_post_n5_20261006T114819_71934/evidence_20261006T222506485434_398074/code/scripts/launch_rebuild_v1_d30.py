"""One nohup D30 controller. Wait D28, replay wave, then four fixed static jobs."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from datetime import datetime
FILES=['scripts/d30_common.py','scripts/d30_data.py','model/rebuild_v1_d30.py',
       'scripts/run_rebuild_v1_d30.py','scripts/replay_rebuild_v1_d30.py',
       'scripts/launch_rebuild_v1_d30.py','scripts/status_rebuild_v1_d30.py',
       'scripts/check_rebuild_v1_d30_handover.py','scripts/summarize_rebuild_v1_d30.py',
       'scripts/upload_rebuild_v1_d30_records.py','tests/test_d30.py',
       'records/research_d30_plan_20261003/plan.json']
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.tmp')
    tmp.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8');os.replace(tmp,p)
def now():return datetime.now().astimezone().isoformat()
def sha(p):
    import hashlib
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(8*1024**2),b''):h.update(block)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True)
    ap.add_argument('--commit',required=True);ap.add_argument('--resume-queue',action='store_true');a=ap.parse_args()
    root=a.root.resolve();root.relative_to(Path('/home/jovyan/zzx'));base=a.directory.resolve();base.relative_to(root/'records')
    if not base.name.startswith('research_d30_loss_decomposition_'):raise ValueError('unexpected directory')
    parent=root/'records/research_d28_pressure_20261003T092243758628_2001983'
    d27=root/'records/research_d27_safe_routing_repair_20261003T092243758628_2001983'
    if not (parent/'plan.json').exists() or not (d27/'plan.json').exists():raise RuntimeError('bound predecessor directories absent')
    base.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=(base/'controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    # One active D30 across independent directories, without altering D28 locks.
    queue_lock=(root/'records/d30_successor.lock').open('a');fcntl.flock(queue_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    commit=subprocess.check_output(['git','-C',str(root),'rev-parse',a.commit+'^{commit}'],text=True).strip();code=base/'code'
    inherited=read(d27/'code_manifest.json')
    if inherited['commit']!='ba7088ec05be7b85dd45e5896a8407506bcca14d':raise RuntimeError('D27 source differs')
    if Path(read(parent/'plan.json')['predecessor_directory']).resolve()!=d27 or read(parent/'plan.json')['execution_commit']!=inherited['commit']:raise RuntimeError('D28 binding differs')
    if not a.resume_queue:
        if code.exists() or (base/'plan.json').exists():raise RuntimeError('existing queue requires --resume-queue')
        for name,digest in inherited['files'].items():
            source=d27/'code'/name
            if sha(source)!=digest:raise RuntimeError('D27 source snapshot changed '+name)
            dest=code/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(source.read_bytes())
        for name in FILES:
            dest=code/name;dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+name]))
        sys.path.insert(0,str(code/'scripts'))
        from d30_common import runtime_plan
        plan=runtime_plan(read(d27/'plan.json'),read(code/'records/research_d30_plan_20261003/plan.json'),commit,parent,d27)
        plan['source_D27_plan_sha256']=sha(d27/'plan.json');plan['created_at']=now()
        write(base/'plan.json',plan);(base/'execution_commit.txt').write_text(commit+'\n')
        write(base/'code_manifest.json',dict(commit=commit,inherited_D27_commit=inherited['commit'],
              files={str(p.relative_to(code)).replace('\\','/'):sha(p) for p in code.rglob('*') if p.is_file()}))
    else:
        plan=read(base/'plan.json')
        if plan['execution_commit']!=commit:raise RuntimeError('resume execution commit changed')
        sys.path.insert(0,str(code/'scripts'))
    from d30_common import validate_plan,live_owned,lock_free,predecessor_verdict,next_job,INITIAL_SHA
    validate_plan(plan)
    for name,digest in read(base/'code_manifest.json')['files'].items():
        if sha(code/name)!=digest:raise RuntimeError('D30 code changed '+name)
    if sha(d27/'plan.json')!=plan['source_D27_plan_sha256']:raise RuntimeError('source D27 plan changed')
    # CPU target/fallback/queue regressions, not a resource or data audit.
    env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
             PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(base/'temporary'),XDG_CACHE_HOME=str(base/'cache'),TORCH_HOME=str(base/'cache/torch'))
    for directory in ('temporary','cache/torch','logs','jobs'):(base/directory).mkdir(parents=True,exist_ok=True)
    state=read(base/'queue_status.json') if (base/'queue_status.json').exists() else dict(jobs={j:dict(status='PENDING',gpu=g) for j,g in
           (('replay_G0',0),('replay_G1',1),('P',0),('R',1),('PR_area',0),('PR_pixel',1))})
    for j,row in state['jobs'].items():
        if live_owned(row.get('pid',-1),base):raise RuntimeError('existing worker alive '+j)
        completed=base/'jobs'/j/'complete.json'
        if completed.exists():
            info=read(completed);signature=info['signature']
            expected_commit=signature.get('execution_commit')
            if expected_commit!=commit:raise RuntimeError('completed execution binding differs '+j)
            if signature.get('plan_sha256')!=sha(base/'plan.json'):raise RuntimeError('completed plan binding differs '+j)
            if j.startswith('replay_'):
                if info['new_tile_evaluations']!=24 or signature['source_sha256']!=sha(base/'code_manifest.json'):raise RuntimeError('replay completion differs')
            elif sha(base/'jobs'/j/'selected.pth')!=info['selected_checkpoint_sha256']:raise RuntimeError('completed checkpoint changed '+j)
            row['status']='COMPLETE'
        elif row.get('status')=='RUNNING':row['status']='PENDING'
    state.update(status='VERIFYING_CPU',controller_pid=os.getpid(),execution_commit=commit,predecessor_directory=str(parent),observed_at=now())
    write(base/'queue_status.json',state)
    try:
        with (base/'cpu_checks.log').open('a') as log:
            subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(code/'tests'),'-p','test_d30.py','-v'],
                           cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,check=True)
    except Exception:
        state.update(status='CPU_CHECK_FAILURE',observed_at=now());write(base/'queue_status.json',state);raise
    print('D30_CPU_CHECKS_PASS',flush=True)
    state['status']='WAITING_D28'
    while True:
        previous=read(parent/'queue_status.json')
        workers=[r.get('pid') for r in previous.get('jobs',{}).values() if live_owned(r.get('pid',-1),parent)]
        free=lock_free(parent)
        verdict=predecessor_verdict(previous,free,bool(workers),live_owned(previous.get('controller_pid',-1),parent))
        state.update(status=verdict,predecessor_status=previous.get('status'),predecessor_observed_at=previous.get('observed_at'),
                     predecessor_lock_free=free,predecessor_live_workers=workers,observed_at=now())
        write(base/'queue_status.json',state)
        if verdict=='READY':
            screen=read(parent/'screen_result.json')
            if screen['status']!='COMPLETE':raise RuntimeError('D28 technical summary invalid')
            for name in previous['jobs']:
                finished=read(parent/'jobs'/name/'complete.json')
                if finished['tile_evaluations']!=34 or finished['test6_loaded']:raise RuntimeError('D28 completion evidence invalid')
            state['D28_summary_sha256']=sha(parent/'screen_result.json');break
        if verdict.startswith('HOLD'):print('D30_'+verdict,flush=True);return 2
        print('D30_WAITING_D28',previous.get('status'),'complete='+str(sum(r.get('status')=='COMPLETE' for r in previous.get('jobs',{}).values()))+'/7',flush=True)
        time.sleep(30)
    # Bind reused controls and original checkpoint interventions before any GPU work.
    if read(d27/'queue_status.json')['status']!='COMPLETE':raise RuntimeError('D27 no longer complete')
    binding=dict(parent_directory=str(d27),source_plan_sha256=sha(d27/'plan.json'),jobs={},files={})
    for arm in ('S0','S1','G0','G1'):
        folder=d27/'jobs'/arm;complete=read(folder/'complete.json')
        sig=complete['signature']
        if sig['execution_commit']!=inherited['commit'] or sig['plan_sha256']!=sha(d27/'plan.json') or sig['sources']!=inherited['files'] or complete['global_step']!=8000:raise RuntimeError('D27 completed job binding differs '+arm)
        if read(folder/'model_capacity.json')['initial_fusion_state_sha256']!=INITIAL_SHA:raise RuntimeError('D27 initialization differs')
        path=folder/'selected.pth'
        if complete['selected']['step']!=4000 or sha(path)!=complete['selected_checkpoint_sha256']:raise RuntimeError('D27 selected checkpoint changed')
        binding['jobs'][arm]=dict(checkpoint_path=str(path),checkpoint_sha256=complete['selected_checkpoint_sha256'],step=4000,complete_sha256=sha(folder/'complete.json'))
        if arm in ('S0','S1'):
            for tag in ('evaluation','fixed8000'):
                for condition in plan['evaluation']['primary']:
                    for tile in plan['data']['validation']:
                        old=folder/tag/condition/(tile+'.json');row=read(old)
                        if row['binding']['training']!=sig:raise RuntimeError('reused control result signature differs')
                        if tag=='evaluation' and row['binding']['selected']['checkpoint_sha256']!=complete['selected_checkpoint_sha256']:raise RuntimeError('reused selected result differs')
                        rel='reused/'+arm+'/'+tag+'/'+condition+'/'+tile+'.json';dest=base/rel
                        dest.parent.mkdir(parents=True,exist_ok=True)
                        raw=old.read_bytes()
                        if dest.exists() and dest.read_bytes()!=raw:raise RuntimeError('conflicting reused result')
                        if not dest.exists():dest.write_bytes(raw)
                        binding['files'][rel]=dict(source=str(old),sha256=sha(old))
    if (base/'reuse_binding.json').exists() and read(base/'reuse_binding.json')!=binding:raise RuntimeError('resume reuse binding changed')
    write(base/'reuse_binding.json',binding)
    from launch_rebuild_v1_d27 import check_device,stop_owned
    uuids={int(line.split(',')[0]):line.split(',')[1].strip() for line in subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid','--format=csv,noheader'],text=True).splitlines()}
    if not all(g in uuids for g in (0,1)):raise RuntimeError('authorized GPU0/1 absent')
    state['gpu_uuids']={str(g):uuids[g] for g in (0,1)}
    active={};last_print=0.;env.pop('CUDA_VISIBLE_DEVICES',None)
    try:
        for phase in ('replay','training'):
            state.update(status='RUNNING',phase=phase)
            while True:
                for gpu in (0,1):
                    if gpu not in active:
                        j=next_job(state,gpu,phase)
                        if j:
                            try:check_device(gpu,uuids)
                            except RuntimeError as exc:
                                state['jobs'][j]['device_wait']=str(exc)
                                if time.monotonic()-last_print>=60:print('D30_DEVICE_WAIT',gpu,str(exc),flush=True)
                                continue
                            log=base/'logs'/(j+'_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log');handle=log.open('x')
                            script='replay_rebuild_v1_d30.py' if phase=='replay' else 'run_rebuild_v1_d30.py'
                            command=[sys.executable,'-u','-B',str(code/'scripts'/script),'--root',str(root),'--directory',str(base),'--job',j,'--gpu',str(gpu)]
                            if phase=='training' and (base/'jobs'/j/'last_train_state.pth').exists():command.append('--resume')
                            process=subprocess.Popen(command,cwd=code,env=dict(env,CUDA_VISIBLE_DEVICES=str(gpu)),stdin=subprocess.DEVNULL,
                                                     stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
                            active[gpu]=(j,process,handle,time.monotonic())
                            state['jobs'][j].update(status='RUNNING',pid=process.pid,started_at=now(),log_path=str(log),command=command)
                            print('D30_STARTED',gpu,j,process.pid,flush=True)
                    if gpu in active:
                        j,process,handle,began=active[gpu];row=state['jobs'][j];progress=base/'jobs'/j/'progress.json'
                        if progress.exists():row['progress']=read(progress)
                        row['elapsed_seconds']=time.monotonic()-began
                        timeout=row['elapsed_seconds']>8*3600
                        if timeout:stop_owned(process)
                        rc=process.poll()
                        if rc is not None:
                            row.update(status='TIMEOUT' if timeout else 'COMPLETE' if rc==0 and (base/'jobs'/j/'complete.json').exists() else 'TECHNICAL_FAILURE',
                                       returncode=rc,completed_at=now())
                            if row['status']!='COMPLETE':row['error_tail']='\n'.join(logtail(row['log_path']))
                            handle.close();del active[gpu];print('D30_JOB_STATUS',j,row['status'],flush=True)
                state['observed_at']=now();write(base/'queue_status.json',state)
                if time.monotonic()-last_print>=60:
                    for gpu,(j,_,_,_) in active.items():print('D30_PROGRESS',gpu,j,state['jobs'][j].get('progress',{}),flush=True)
                    last_print=time.monotonic()
                ids=('replay_G0','replay_G1') if phase=='replay' else ('P','R','PR_area','PR_pixel')
                if not active and not any(state['jobs'][j]['status']=='PENDING' for j in ids):break
                time.sleep(5)
            if any(state['jobs'][j]['status']!='COMPLETE' for j in ids):
                state.update(status='COMPLETE_WITH_TECHNICAL_FAILURES',observed_at=now());write(base/'queue_status.json',state)
                print('D30_HOLD_NO_AUTOMATIC_RETRY',flush=True);return 2
        result=subprocess.run([sys.executable,'-B',str(code/'scripts/summarize_rebuild_v1_d30.py'),'--directory',str(base)],cwd=code,env=env)
        state.update(status='COMPLETE' if result.returncode==0 else 'SUMMARY_TECHNICAL_FAILURE',summary_exit=result.returncode,completed_at=now(),observed_at=now())
        write(base/'queue_status.json',state);print('D30_QUEUE_FINISHED',state['status'],flush=True)
        print('D30_UPLOAD_READY',str(code/'scripts/upload_rebuild_v1_d30_records.py'),flush=True)
        return result.returncode
    except BaseException:
        state.update(status='CONTROLLER_INTERRUPTED',observed_at=now(),error='inspect logs; detached workers may remain alive, do not duplicate')
        write(base/'queue_status.json',state);raise
    finally:
        for _,_,handle,_ in active.values():handle.close()
def logtail(path):
    from collections import deque
    with Path(path).open(errors='replace') as f:return list(deque(f,maxlen=20))
if __name__=='__main__':sys.exit(main())
