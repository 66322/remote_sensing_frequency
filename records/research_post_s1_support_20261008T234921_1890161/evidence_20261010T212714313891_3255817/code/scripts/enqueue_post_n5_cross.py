"""Idempotent diagnostic registration, local Git snapshots, nohup controller."""
import argparse,datetime,os,subprocess,sys
from pathlib import Path
N5_NAME='research_post_n5_20261006T114819_71934'
FILES=['scripts/post_n5_cross_common.py','model/post_n5_cross_paths.py','scripts/prepare_post_n5_cross.py','scripts/run_post_n5_cross.py','scripts/summarize_post_n5_cross.py','scripts/control_post_n5_cross.py','scripts/status_post_n5_cross.py','scripts/enqueue_post_n5_cross.py','scripts/upload_post_n5_cross_records.py','tests/test_post_n5_cross.py','docs/protocols/POST_N5_CROSS_DIAGNOSTICS_EXECUTION_20261006.md']
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--commit',required=True);a=ap.parse_args()
    root=a.root.resolve();root.relative_to(Path('/home/jovyan/zzx'));records=root/'records';source=records/N5_NAME
    sys.path.insert(0,str(source/'code/scripts'))
    from post_n2_diag_common import read,write,sha
    import fcntl
    with (records/'post_n5_cross_registration.lock').open('a') as registration:
        fcntl.flock(registration,fcntl.LOCK_EX|fcntl.LOCK_NB)
        old=sorted(p for p in records.glob('research_post_n5_cross_*') if (p/'plan.json').exists())
        if old:
            for p in old:
                state=read(p/'queue_status.json') if (p/'queue_status.json').exists() else {'status':'HOLD_INCOMPLETE_REGISTRATION'}
                print('CROSS_ALREADY_REGISTERED',p,state['status'],flush=True)
            return 0
        commit=subprocess.check_output(['git','-C',str(root),'rev-parse',a.commit+'^{commit}'],text=True).strip()
        ns={};text=subprocess.check_output(['git','-C',str(root),'show',commit+':scripts/post_n5_cross_common.py'],text=True)
        exec(compile(text,'post_n5_cross_common.py','exec'),ns);acceptance=ns['released'](root)
        # Shared lease is checked before allocating a successor, then controller
        # rechecks source liveness and lease immediately before starting work.
        with (records/'post_ab_successor.lock').open('a') as lease:
            fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
            base=records/('research_post_n5_cross_'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()))
            base.mkdir();code=base/'code';manifest=read(source/'code_manifest.json')
            for name,digest in manifest['files'].items():
                oldpath=source/'code'/name
                if sha(oldpath)!=digest:raise RuntimeError('inherited source changed '+name)
                new=code/name;new.parent.mkdir(parents=True,exist_ok=True);new.write_bytes(oldpath.read_bytes())
            for name in FILES:
                new=code/name;new.parent.mkdir(parents=True,exist_ok=True)
                new.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+name]))
            parent=read(source/'plan.json');plan=ns['make_plan'](root,base,commit,parent);ns['validate'](plan)
            write(base/'plan.json',plan);write(base/'registration_acceptance.json',acceptance)
            (base/'execution_commit.txt').write_text(commit+'\n')
            write(base/'code_manifest.json',dict(commit=commit,inherited_N5_commit=manifest['commit'],files={p.relative_to(code).as_posix():sha(p) for p in code.rglob('*') if p.is_file()}))
            for name in ('temporary','cache/torch','logs'):(base/name).mkdir(parents=True,exist_ok=True)
            env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(base/'temporary'),TEMP=str(base/'temporary'),TMP=str(base/'temporary'),XDG_CACHE_HOME=str(base/'cache'),TORCH_HOME=str(base/'cache/torch'),
                PYTHONPATH=os.pathsep.join([str(code),str(code/'scripts')]))
            state=ns['initial_state'](plan);state['status']='CPU_VERIFYING';write(base/'queue_status.json',state)
            try:
                with (base/'cpu_checks.log').open('x') as log:
                    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(code/'tests'),'-p','test_post_n5_cross.py','-v'],cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
            except BaseException as exc:
                state.update(status='HOLD_CPU_CHECKS',error=str(exc));write(base/'queue_status.json',state);raise
            state['status']='REGISTERED';write(base/'queue_status.json',state)
        log=base/('nohup_'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log')
        cmd=[sys.executable,'-u','-B',str(code/'scripts/control_post_n5_cross.py'),'--root',str(root),'--directory',str(base)]
        with log.open('x') as handle:
            proc=subprocess.Popen(['nohup',*cmd],cwd=code,env=env,stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
        write(base/'launch.json',dict(controller_pid=proc.pid,command=cmd,log=str(log)));(base/'controller.pid').write_text(str(proc.pid)+'\n')
        print('CROSS_DIAGNOSTICS_REGISTERED',base,'PID='+str(proc.pid),'NEW_TRAINING=0 E4_TILE_UNITS=192 GPU=0,1',flush=True)
        print('CROSS_LOG',log,flush=True)
    return 0
if __name__=='__main__':sys.exit(main())
