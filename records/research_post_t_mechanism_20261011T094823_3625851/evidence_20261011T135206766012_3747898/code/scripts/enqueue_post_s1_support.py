"""Idempotent server registration, immutable snapshot, CPU checks, nohup GPU0 FIFO."""
import argparse,datetime,os,subprocess,sys
from pathlib import Path
SOURCE='research_post_n3_s1_20261007T083203_694293'
FILES=['model/post_s1_support_model.py','scripts/post_s1_support_common.py',
 'scripts/post_s1_support_evaluation.py','scripts/prepare_post_s1_support.py','scripts/run_post_s1_support.py',
 'scripts/run_post_s1_support_diagnostics.py','scripts/control_post_s1_support.py','scripts/status_post_s1_support.py',
 'scripts/summarize_post_s1_support.py','scripts/enqueue_post_s1_support.py','scripts/upload_post_s1_support_records.py',
 'tests/test_post_s1_support.py','docs/protocols/POST_S1_SUPPORT_EXECUTION_20261008.md',
 'docs/protocols/POST_S1_SUPPORT_GPU0_PLAN_20261008.md']
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--commit',required=True);a=ap.parse_args()
    root=a.root.resolve();root.relative_to(Path('/home/jovyan/zzx').resolve());records=root/'records';source=records/SOURCE
    sys.path.insert(0,str(source/'code/scripts'))
    from post_n2_diag_common import read,write,sha
    import fcntl
    with (records/'post_s1_support_registration.lock').open('a') as registration:
        fcntl.flock(registration,fcntl.LOCK_EX|fcntl.LOCK_NB)
        existing=sorted(p for p in records.glob('research_post_s1_support_*') if (p/'plan.json').exists())
        if existing:
            for p in existing:
                s=read(p/'queue_status.json') if (p/'queue_status.json').exists() else dict(status='HOLD_INCOMPLETE_REGISTRATION')
                print('SUPPORT_ALREADY_REGISTERED',p,s['status'],flush=True)
            return 0
        commit=subprocess.check_output(['git','-C',str(root),'rev-parse',a.commit+'^{commit}'],text=True).strip()
        ns={};content=subprocess.check_output(['git','-C',str(root),'show',commit+':scripts/post_s1_support_common.py'],text=True)
        exec(compile(content,'post_s1_support_common.py','exec'),ns)
        acceptance=ns['released'](root)
        print('SUPPORT_PREDECESSOR_LAST_OBSERVED',acceptance['last_observed'],'COMPLETE RELEASED',flush=True)
        with (records/'post_ab_successor.lock').open('a') as lease:
            fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
            # Reject any partial directory too: registration failures must be diagnosed.
            partial=sorted(records.glob('research_post_s1_support_*'))
            if partial:raise RuntimeError('partial registration exists; explicit recovery required '+str(partial))
            base=records/('research_post_s1_support_'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()))
            base.mkdir();code=base/'code';manifest=read(source/'code_manifest.json')
            for name,digest in manifest['files'].items():
                old=source/'code'/name
                if sha(old)!=digest:raise RuntimeError('inherited source changed '+name)
                new=code/name;new.parent.mkdir(parents=True,exist_ok=True);new.write_bytes(old.read_bytes())
            for name in FILES:
                new=code/name;new.parent.mkdir(parents=True,exist_ok=True)
                new.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+name]))
            parent=read(source/'plan.json');p=ns['make_plan'](root,base,commit,parent);ns['validate'](p)
            write(base/'plan.json',p);write(base/'registration_acceptance.json',acceptance)
            (base/'execution_commit.txt').write_text(commit+'\n')
            write(base/'code_manifest.json',dict(commit=commit,inherited_source_commit=manifest['commit'],
                files={p.relative_to(code).as_posix():sha(p) for p in code.rglob('*') if p.is_file()}))
            for name in ('temporary','cache/torch','logs'):(base/name).mkdir(parents=True,exist_ok=True)
            env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
                PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(base/'temporary'),TEMP=str(base/'temporary'),TMP=str(base/'temporary'),
                XDG_CACHE_HOME=str(base/'cache'),TORCH_HOME=str(base/'cache/torch'),PYTHONPATH=os.pathsep.join([str(code),str(code/'scripts')]))
            state=ns['initial_state'](p);state['status']='CPU_VERIFYING';write(base/'queue_status.json',state)
            try:
                with (base/'cpu_checks.log').open('x') as handle:
                    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(code/'tests'),'-p','test_post_s1_support.py','-v'],
                        cwd=code,env=env,stdout=handle,stderr=subprocess.STDOUT,check=True,timeout=600)
            except BaseException as exc:
                state.update(status='HOLD_CPU_CHECKS',error=str(exc),observed_at=ns['now']());write(base/'queue_status.json',state);raise
            state['status']='REGISTERED';write(base/'queue_status.json',state)
        log=base/('nohup_'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log')
        cmd=[sys.executable,'-u','-B',str(code/'scripts/control_post_s1_support.py'),'--root',str(root),'--directory',str(base)]
        with log.open('x') as handle:
            process=subprocess.Popen(['nohup',*cmd],cwd=code,env=env,stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
        write(base/'launch.json',dict(controller_pid=process.pid,command=cmd,log=str(log),physical_gpus=[0]))
        (base/'controller.pid').write_text(str(process.pid)+'\n')
        print('SUPPORT_QUEUE_REGISTERED',base,'PID='+str(process.pid),'GPU=0 ONLY TRAINING_JOBS=10 NEW_STEPS=80000 Q_RESERVED_NOT_RUNNABLE=4',flush=True)
        print('SUPPORT_LOG',log,flush=True)
    return 0
if __name__=='__main__':sys.exit(main())

