"""Install separate controller fix; adopt the original queue, never restart workers."""
import argparse,datetime,fcntl,json,os,subprocess,sys,time
from pathlib import Path
SCIENCE='86b6a70e5c3482314986fb1259e2fccbd0a5a38b'
NAME='research_post_ab_followup_n2_20261005T085829_3456726'
FILES=['scripts/control_post_ab_n2.py','scripts/post_ab_n2_recovery.py','scripts/status_post_ab.py','tests/test_post_ab_n2_recovery.py']
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--directory',type=Path,required=True);p.add_argument('--commit',required=True);a=p.parse_args()
    root=a.root.resolve();root.relative_to(Path('/home/jovyan/zzx'));base=a.directory.resolve()
    if base!=root/'records'/NAME:raise RuntimeError('unexpected recovery directory')
    sys.path.insert(0,str(base/'code/scripts'))
    from post_ab_queue_common import read,write,sha,now
    from d30_common import live_owned
    with (base/'controller_recovery.lock').open('a') as guard:
        fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state=read(base/'queue_status.json')
        recorded_pid=int((base/'controller.pid').read_text().strip()) if (base/'controller.pid').exists() else -1
        if live_owned(state.get('controller_pid',-1),base) or live_owned(recorded_pid,base):
            print('N2_CONTROLLER_ALREADY_LIVE',state['controller_pid']);return 0
        # Locks prove the old controller and any other successor are released.
        lock=(base/'controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        common=(root/'records/post_ab_successor.lock').open('a');fcntl.flock(common,fcntl.LOCK_EX|fcntl.LOCK_NB)
        plan=read(base/'plan.json');manifest=read(base/'code_manifest.json')
        if plan['execution_commit']!=SCIENCE or manifest['commit']!=SCIENCE or (base/'execution_commit.txt').read_text().strip()!=SCIENCE:raise RuntimeError('science binding changed')
        for name,digest in manifest['files'].items():
            if sha(base/'code'/name)!=digest:raise RuntimeError('immutable source changed '+name)
        from post_ab_n2_common import validate_plan
        validate_plan(plan)
        if state['status']=='N2_COMPLETE_AWAITING_STAGE_PROTOCOL':
            print('N2_ALREADY_COMPLETE; no controller restart');return 0
        commit=subprocess.check_output(['git','-C',str(root),'rev-parse',a.commit+'^{commit}'],text=True).strip()
        repair=base/('controller_repair_'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()));repair.mkdir()
        for name in FILES:
            dst=repair/name;dst.parent.mkdir(parents=True,exist_ok=True)
            dst.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+name]))
        write(repair/'queue_status_before.json',state)
        sys.path.insert(0,str(repair/'scripts'))
        from post_ab_n2_recovery import reconcile,unknown_workers,timeout_hours
        unknown_workers(base,{r.get('pid',-1) for r in state['jobs'].values()})
        try:adopted,completed=reconcile(base,plan,state)
        except Exception as exc:
            write(repair/'hold.json',dict(reason=str(exc),observed_at=now(),workers_restarted=0))
            print('N2_RECOVERY_HOLD',str(exc),flush=True)
            for job,row in state['jobs'].items():
                if row['status']=='RUNNING':
                    progress=base/'jobs'/job/'progress.json'
                    if progress.exists():print('WORKER_PROGRESS',job,progress.read_text(),flush=True)
                    log=Path(row.get('log_path',''))
                    if log.is_file():
                        log.resolve().relative_to(base);print('WORKER_LOG',job,'\n'+'\n'.join(log.read_text(errors='replace').splitlines()[-60:]),flush=True)
            return 2
        env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(base/'temporary'),XDG_CACHE_HOME=str(base/'cache'),TORCH_HOME=str(base/'cache/torch'))
        env['PYTHONPATH']=os.pathsep.join([str(repair/'scripts'),str(base/'code'),str(base/'code/scripts')])
        with (repair/'cpu_checks.log').open('x') as log:
            subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(repair/'tests'),'-p','test_post_ab_n2_recovery.py','-v'],cwd=repair,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
        write(repair/'repair_manifest.json',dict(fix_commit=commit,science_execution_commit=SCIENCE,plan_sha256=sha(base/'plan.json'),original_code_manifest_sha256=sha(base/'code_manifest.json'),files={n:sha(repair/n) for n in FILES},adopted_workers={p.job:p.pid for p in adopted.values()},accepted_complete=completed,effective_per_job_timeout_hours=timeout_hours(plan['runtime'].get('per_job_timeout_hours')),workers_restarted=0,observed_at=now()))
        # Child takes these same controller/successor locks before any dispatch.
        lock.close();common.close()
        log=repair/'nohup_controller.log';cmd=[sys.executable,'-u','-B',str(repair/'scripts/control_post_ab_n2.py'),'--root',str(root),'--directory',str(base)]
        with log.open('x') as h:
            proc=subprocess.Popen(['nohup',*cmd],cwd=base/'code',env=env,stdin=subprocess.DEVNULL,stdout=h,stderr=subprocess.STDOUT,start_new_session=True)
        write(repair/'launch.json',dict(controller_pid=proc.pid,command=cmd,log=str(log)))
        # Publish PID immediately so a second installer sees this controller.
        (base/'controller.pid').write_text(str(proc.pid)+'\n')
        print('N2_CONTROLLER_REPAIR_REGISTERED',repair,'PID='+str(proc.pid),'ADOPT='+str({p.job:p.pid for p in adopted.values()}),'ACCEPT_COMPLETE='+str(completed),flush=True)
        time.sleep(2)
        print('N2_REPAIR_LOG',log,flush=True);print('\n'.join(log.read_text(errors='replace').splitlines()[-30:]),flush=True)
        if proc.poll() is not None and proc.returncode!=0:return proc.returncode
    return 0
if __name__=='__main__':sys.exit(main())
