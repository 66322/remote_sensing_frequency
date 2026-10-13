"""Register once while predecessor runs; detached controller waits without GPU work."""
import argparse,datetime,os,subprocess,sys
from pathlib import Path
SOURCE='research_post_s1_transfer_20261010T073327_2852696'
FILES=['model/post_t_mechanism.py', 'scripts/post_t_mechanism_common.py', 'scripts/prepare_post_t_mechanism.py', 'scripts/run_post_t_mechanism.py', 'scripts/control_post_t_mechanism.py', 'scripts/status_post_t_mechanism.py', 'scripts/summarize_post_t_mechanism.py', 'scripts/enqueue_post_t_mechanism.py', 'scripts/upload_post_t_mechanism_records.py', 'tests/test_post_t_mechanism.py', 'docs/protocols/POST_T_MECHANISM_GPU0_20261010.md']

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--commit',required=True);a=ap.parse_args()
    root=a.root.resolve();root.relative_to(Path('/home/jovyan/zzx').resolve());records=root/'records';source=records/SOURCE
    sys.path.insert(0,str(source/'code/scripts'))
    from post_n2_diag_common import read,write,sha
    import fcntl
    with (records/'post_t_mechanism_registration.lock').open('a') as registration:
        fcntl.flock(registration,fcntl.LOCK_EX|fcntl.LOCK_NB)
        existing=sorted(records.glob('research_post_t_mechanism_*'))
        if existing:
            for b in existing:
                state=read(b/'queue_status.json') if (b/'queue_status.json').exists() else {'status':'HOLD_INCOMPLETE_REGISTRATION'}
                print('MECHANISM_ALREADY_REGISTERED',b,state['status'],flush=True)
            return 0
        commit=subprocess.check_output(['git','-C',str(root),'rev-parse',a.commit+'^{commit}'],text=True).strip()
        content=subprocess.check_output(['git','-C',str(root),'show',commit+':scripts/post_t_mechanism_common.py'],text=True)
        ns={};exec(compile(content,'post_t_mechanism_common.py','exec'),ns)
        parent=read(source/'plan.json')
        if parent['execution_commit']!=ns['PREDECESSOR_COMMIT']:raise RuntimeError('wrong predecessor execution')
        base=records/('research_post_t_mechanism_'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()))
        p=ns['make_plan'](root,base,commit,parent);ns['validate'](p)
        observation=ns['inspect_predecessor'](root,p)
        if observation['verdict'].startswith('HOLD'):raise RuntimeError('predecessor requires attention '+str(observation))
        # No shared GPU lease here: current controller is allowed to keep running.
        base.mkdir();code=base/'code';manifest=read(source/'code_manifest.json')
        for name,digest in manifest['files'].items():
            old=(source/'code'/name).resolve();old.relative_to(source/'code')
            if sha(old)!=digest:raise RuntimeError('inherited source changed '+name)
            new=code/name;new.parent.mkdir(parents=True,exist_ok=True);new.write_bytes(old.read_bytes())
        for name in FILES:
            new=code/name;new.parent.mkdir(parents=True,exist_ok=True)
            new.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+name]))
        write(base/'plan.json',p);write(base/'registration_observation.json',observation)
        (base/'execution_commit.txt').write_text(commit+'\n')
        write(base/'code_manifest.json',dict(commit=commit,inherited_source_commit=manifest['commit'],
            files={f.relative_to(code).as_posix():sha(f) for f in code.rglob('*') if f.is_file()}))
        for name in ('temporary','cache/torch','logs'):(base/name).mkdir(parents=True,exist_ok=True)
        env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
            PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(base/'temporary'),TEMP=str(base/'temporary'),TMP=str(base/'temporary'),
            XDG_CACHE_HOME=str(base/'cache'),TORCH_HOME=str(base/'cache/torch'),PYTHONPATH=os.pathsep.join([str(code),str(code/'scripts')]))
        state=ns['initial_state'](p);state['status']='CPU_VERIFYING';write(base/'queue_status.json',state)
        try:
            with (base/'cpu_checks.log').open('x') as log:
                subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(code/'tests'),'-p','test_post_t_mechanism.py','-v'],
                    cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
        except BaseException as exc:
            state.update(status='HOLD_CPU_CHECKS',error=str(exc),observed_at=ns['now']());write(base/'queue_status.json',state);raise
        state['status']='REGISTERED';write(base/'queue_status.json',state)
        log=base/('nohup_'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log')
        cmd=[sys.executable,'-u','-B',str(code/'scripts/control_post_t_mechanism.py'),'--root',str(root),'--directory',str(base)]
        with log.open('x') as handle:
            proc=subprocess.Popen(['nohup',*cmd],cwd=code,env=env,stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
        write(base/'launch.json',dict(controller_pid=proc.pid,command=cmd,log=str(log),physical_gpus=[0]))
        (base/'controller.pid').write_text(str(proc.pid)+'\n')
        print('MECHANISM_QUEUE_REGISTERED',base,'PID='+str(proc.pid),'GPU=0 ONLY DIAGNOSTIC_JOBS=26 NEW_STEPS=0',flush=True)
        print('MECHANISM_PREDECESSOR_LAST_OBSERVED',observation['last_observed'],observation['status'],observation['verdict'],flush=True)
        print('MECHANISM_LOG',log,flush=True)
    return 0
if __name__=='__main__':sys.exit(main())
