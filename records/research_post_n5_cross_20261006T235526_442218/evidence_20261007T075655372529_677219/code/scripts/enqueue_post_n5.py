"""Idempotent N5 registration; checks predecessors before creating GPU work."""
import argparse,datetime,fcntl,os,subprocess,sys
from pathlib import Path
FILES=['scripts/post_n5_common.py','scripts/post_n5_data.py','scripts/post_n5_evaluation.py','scripts/prepare_post_n5.py','scripts/run_post_n5.py','scripts/summarize_post_n5.py','scripts/control_post_n5.py','scripts/status_post_n5.py','scripts/enqueue_post_n5.py','scripts/upload_post_n5_records.py','tests/test_post_n5.py','docs/protocols/POST_N5_EXECUTION_20261006.md']
DIAG='research_post_n2_diagnostics_20261005T131434_3591073'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--commit',required=True);a=ap.parse_args()
    root=a.root.resolve();root.relative_to(Path('/home/jovyan/zzx'));records=root/'records';source=records/DIAG
    sys.path.insert(0,str(source/'code/scripts'))
    from post_n2_diag_common import read,write,sha
    with (records/'post_n5_registration.lock').open('a') as registration:
        fcntl.flock(registration,fcntl.LOCK_EX|fcntl.LOCK_NB)
        old=sorted(b for b in records.glob('research_post_n5_*') if (b/'plan.json').exists())
        if old:
            for b in old:print('N5_ALREADY_REGISTERED',b,read(b/'queue_status.json')['status'],flush=True)
            return 0
        commit=subprocess.check_output(['git','-C',str(root),'rev-parse',a.commit+'^{commit}'],text=True).strip()
        # Load contract alone before allocating a new directory.
        namespace={};text=subprocess.check_output(['git','-C',str(root),'show',commit+':scripts/post_n5_common.py'],text=True)
        exec(compile(text,'post_n5_common.py','exec'),namespace)
        acceptance=namespace['released'](root)
        base=records/('research_post_n5_'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()));base.mkdir();code=base/'code'
        manifest=read(source/'code_manifest.json')
        for name,digest in manifest['files'].items():
            p=source/'code'/name
            if sha(p)!=digest:raise RuntimeError('diagnostic inherited code changed '+name)
            q=code/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
        for name in FILES:
            q=code/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+name]))
        # N1 worker source/helpers used by the new worker must match this snapshot.
        for name in ('scripts/run_post_ab_n1.py','scripts/post_ab_n1_data.py','scripts/summarize_post_ab_n1.py'):
            q=code/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+name]))
        parent=read(records/'research_post_ab_followup_20261004T185950_3029215/plan.json')
        plan=namespace['make_plan'](root,base,commit,parent);namespace['validate'](plan)
        write(base/'plan.json',plan);write(base/'predecessor_registration_snapshot.json',acceptance)
        (base/'execution_commit.txt').write_text(commit+'\n')
        write(base/'code_manifest.json',dict(commit=commit,inherited_diagnostic_commit=manifest['commit'],files={p.relative_to(code).as_posix():sha(p) for p in code.rglob('*') if p.is_file()}))
        for name in ('temporary','cache/torch','logs'):(base/name).mkdir(parents=True,exist_ok=True)
        env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(base/'temporary'),TEMP=str(base/'temporary'),TMP=str(base/'temporary'),XDG_CACHE_HOME=str(base/'cache'),TORCH_HOME=str(base/'cache/torch'))
        env['PYTHONPATH']=os.pathsep.join([str(code),str(code/'scripts')])
        state=namespace['initial_state'](plan);state['status']='CPU_VERIFYING';write(base/'queue_status.json',state)
        try:
            with (base/'cpu_checks.log').open('x') as log:
                subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(code/'tests'),'-p','test_post_n5.py','-v'],cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
        except BaseException as exc:
            state.update(status='HOLD_CPU_CHECKS',error=str(exc));write(base/'queue_status.json',state);raise
        state['status']='REGISTERED';write(base/'queue_status.json',state)
        log=base/('nohup_'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log')
        cmd=[sys.executable,'-u','-B',str(code/'scripts/control_post_n5.py'),'--root',str(root),'--directory',str(base)]
        with log.open('x') as handle:
            proc=subprocess.Popen(['nohup',*cmd],cwd=code,env=env,stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
        write(base/'launch.json',dict(controller_pid=proc.pid,command=cmd,log=str(log)));(base/'controller.pid').write_text(str(proc.pid)+'\n')
        print('N5_QUEUE_REGISTERED',base,'PID='+str(proc.pid),'TRAINING_JOBS=4 GPU=0,1 NEW_STEPS=32000',flush=True);print('N5_LOG',log,flush=True)
    return 0
if __name__=='__main__':sys.exit(main())

