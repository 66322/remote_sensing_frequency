"""Idempotent diagnostic registration. No GPU/data access before N2 release."""
import argparse,datetime,fcntl,os,subprocess,sys
from pathlib import Path
FILES=['scripts/post_n2_diag_common.py','scripts/post_n2_masks.py','scripts/post_n2_diag_runtime.py','scripts/run_post_n2_diagnostics.py',
 'scripts/control_post_n2_diagnostics.py','scripts/enqueue_post_n2_diagnostics.py','scripts/status_post_n2_diagnostics.py','scripts/summarize_post_n2_diagnostics.py',
 'scripts/upload_post_n2_diagnostics_records.py','tests/test_post_n2_diagnostics.py','docs/protocols/POST_N2_DIAGNOSTICS_EXECUTION_20261005.md']
N2_NAME='research_post_ab_followup_n2_20261005T085829_3456726'
SCIENCE='86b6a70e5c3482314986fb1259e2fccbd0a5a38b'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--commit',required=True);a=ap.parse_args()
    root=a.root.resolve();root.relative_to(Path('/home/jovyan/zzx'));records=root/'records';parent=records/N2_NAME
    sys.path.insert(0,str(parent/'code/scripts'))
    from post_ab_queue_common import read,write,sha
    from d30_common import live_owned
    with (records/'post_n2_diagnostic_registration.lock').open('a') as registration:
        fcntl.flock(registration,fcntl.LOCK_EX|fcntl.LOCK_NB)
        existing=sorted(x for x in records.glob('research_post_n2_diagnostics_*') if (x/'plan.json').exists())
        if existing:
            for b in existing:print('DIAG_ALREADY_REGISTERED',b,read(b/'queue_status.json')['status'],flush=True)
            return 0
        source_plan=read(parent/'plan.json');source_manifest=read(parent/'code_manifest.json');previous=read(parent/'queue_status.json')
        if source_plan['execution_commit']!=SCIENCE or source_manifest['commit']!=SCIENCE:raise RuntimeError('N2 scientific binding differs')
        print('DIAG_PREDECESSOR_LAST_OBSERVED',previous.get('observed_at'),previous['status'],'PID='+str(previous.get('controller_pid')),'LIVE='+str(live_owned(previous.get('controller_pid',-1),parent)),flush=True)
        commit=subprocess.check_output(['git','-C',str(root),'rev-parse',a.commit+'^{commit}'],text=True).strip()
        base=records/('research_post_n2_diagnostics_'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()));base.mkdir();code=base/'code'
        for name,digest in source_manifest['files'].items():
            src=parent/'code'/name
            if sha(src)!=digest:raise RuntimeError('immutable N2 code changed '+name)
            dst=code/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes())
        for name in FILES:
            dst=code/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+name]))
        sys.path.insert(0,str(code/'scripts'))
        from post_n2_diag_common import make_plan,validate,initial_state
        plan=validate(make_plan(root,base,commit,source_plan));write(base/'plan.json',plan)
        (base/'execution_commit.txt').write_text(commit+'\n');write(base/'code_manifest.json',dict(commit=commit,inherited_science=SCIENCE,files={p.relative_to(code).as_posix():sha(p) for p in code.rglob('*') if p.is_file()}))
        for name in ('temporary','cache/torch','logs'):(base/name).mkdir(parents=True,exist_ok=True)
        env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(base/'temporary'),XDG_CACHE_HOME=str(base/'cache'),TORCH_HOME=str(base/'cache/torch'))
        env['PYTHONPATH']=os.pathsep.join([str(code),str(code/'scripts')])
        checking=initial_state(plan);checking['status']='CPU_VERIFYING';write(base/'queue_status.json',checking)
        try:
            with (base/'cpu_checks.log').open('x') as log:
                subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(code/'tests'),'-p','test_post_n2_diagnostics.py','-v'],cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
        except BaseException as exc:
            checking.update(status='HOLD_CPU_CHECKS',error=str(exc));write(base/'queue_status.json',checking);raise
        write(base/'queue_status.json',initial_state(plan));write(base/'predecessor_registration_snapshot.json',dict(directory=str(parent),plan_sha256=sha(parent/'plan.json'),manifest_sha256=sha(parent/'code_manifest.json'),queue=previous,observed_at=datetime.datetime.now().astimezone().isoformat(),launches_predecessor=False))
        log=base/('nohup_'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log');cmd=[sys.executable,'-u','-B',str(code/'scripts/control_post_n2_diagnostics.py'),'--root',str(root),'--directory',str(base)]
        with log.open('x') as h:proc=subprocess.Popen(['nohup',*cmd],cwd=code,env=env,stdin=subprocess.DEVNULL,stdout=h,stderr=subprocess.STDOUT,start_new_session=True)
        write(base/'launch.json',dict(controller_pid=proc.pid,command=cmd,log=str(log)));(base/'controller.pid').write_text(str(proc.pid)+'\n')
        print('POST_N2_DIAGNOSTICS_REGISTERED',base,'PID='+str(proc.pid),'E1_MODELS=2 E2_MODELS=3 NEW_TRAINING=0',flush=True);print('POST_N2_DIAGNOSTICS_LOG',log,flush=True)
    return 0
if __name__=='__main__':sys.exit(main())
