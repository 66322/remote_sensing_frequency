"""Idempotent detached registration of N1 and 22 conditional reservations."""
import argparse
from datetime import datetime
import hashlib,json,os,subprocess,sys
from pathlib import Path
PREFIX='research_post_ab_followup_'
PARENT='research_post_d30_mechanisms_20261004T000812_2446364'
FILES=['model/rebuild_v1_post_ab_n1.py','model/vitcross_seg_modeling_freq_ablation.py',
       'scripts/post_ab_queue_common.py','scripts/post_ab_n1_data.py','scripts/run_post_ab_n1.py',
       'scripts/summarize_post_ab_n1.py','scripts/control_post_ab.py','scripts/status_post_ab.py',
       'scripts/upload_post_ab_records.py','scripts/enqueue_post_ab.py',
       'scripts/post_d30_data.py','scripts/post_d30_evaluation.py','scripts/post_d30_eval_compat.py',
       'scripts/summarize_post_d30.py','scripts/launch_rebuild_v1_d27.py','tests/test_post_ab_queue.py',
       'docs/protocols/POST_AB_QUEUE_EXECUTION_20261004.md']

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp')
    t.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n');os.replace(t,p)
def live(pid,base):
    try:return str(base).encode() in (Path('/proc')/str(pid)/'cmdline').read_bytes()
    except FileNotFoundError:return False

def controller_pid(base,state):
    if state.get('controller_pid'):return state['controller_pid']
    launch=base/'launch.json'
    return read(launch).get('controller_pid',-1) if launch.exists() else -1

def existing_queue(records):
    matches=[]
    for p in records.glob(PREFIX+'*'):
        if (p/'plan.json').is_file():matches.append(p)
    return sorted(matches)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--commit',required=True)
    ap.add_argument('--directory',type=Path);ap.add_argument('--resume-controller',action='store_true');a=ap.parse_args()
    root=a.root.resolve();root.relative_to(Path('/home/jovyan/zzx'));records=root/'records'
    parent=records/PARENT;previous=read(parent/'queue_status.json')
    print('ORIGINAL_QUEUE_LAST_OBSERVED='+str(previous.get('observed_at')),
          'STATUS='+str(previous.get('status')),'PID='+str(previous.get('controller_pid')),
          'LIVE='+str(live(previous.get('controller_pid',-1),parent)),flush=True)
    import fcntl
    with (records/'post_ab_registration.lock').open('a') as register_lock:
        fcntl.flock(register_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        existing=existing_queue(records)
        if a.resume_controller:
            if a.directory is None:raise RuntimeError('explicit directory required for diagnosed controller resume')
            base=a.directory.resolve();base.relative_to(records)
            if base not in existing:raise RuntimeError('registered queue absent')
            if live(controller_pid(base,read(base/'queue_status.json')),base):
                print('POST_AB_ALREADY_LIVE',base,flush=True);return 0
            commit=read(base/'plan.json')['execution_commit']
            if commit!=subprocess.check_output(['git','-C',str(root),'rev-parse',a.commit+'^{commit}'],text=True).strip():raise RuntimeError('resume commit differs')
        else:
            if existing:
                for base in existing:
                    state=read(base/'queue_status.json')
                    print('POST_AB_ALREADY_REGISTERED',base,state['status'],'LIVE='+str(live(controller_pid(base,state),base)),flush=True)
                print('No duplicate queue created; stopped controller needs diagnosis and explicit resume.',flush=True);return 0
            commit=subprocess.check_output(['git','-C',str(root),'rev-parse',a.commit+'^{commit}'],text=True).strip()
            parent=records/PARENT;parent_plan=read(parent/'plan.json');manifest=read(parent/'code_manifest.json')
            if parent_plan['execution_commit']!='01ec8dee82f7e272f6a650aaf9f3e619a0e7c516' or manifest['commit']!=parent_plan['execution_commit']:raise RuntimeError('unexpected predecessor binding')
            base=records/(PREFIX+datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()));base.mkdir()
            code=base/'code'
            for name,digest in manifest['files'].items():
                source=parent/'code'/name
                if sha(source)!=digest:raise RuntimeError('predecessor immutable snapshot changed '+name)
                dest=code/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(source.read_bytes())
            for name in FILES:
                dest=code/name;dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+name]))
            sys.path[:0]=[str(code/'scripts')]
            from post_ab_queue_common import runtime_plan,validate_plan,initial_state
            plan=runtime_plan(parent_plan,commit,base);validate_plan(plan)
            plan['source_post_d30_plan_sha256']=sha(parent/'plan.json')
            plan['created_at']=datetime.now().astimezone().isoformat()
            write(base/'plan.json',plan);(base/'execution_commit.txt').write_text(commit+'\n')
            write(base/'code_manifest.json',dict(commit=commit,inherited_commit=manifest['commit'],files={p.relative_to(code).as_posix():sha(p) for p in code.rglob('*') if p.is_file()}))
            write(base/'queue_status.json',initial_state(plan))
        code=base/'code';(base/'temporary').mkdir(exist_ok=True);(base/'cache/torch').mkdir(parents=True,exist_ok=True)
        env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(base/'temporary'),XDG_CACHE_HOME=str(base/'cache'),TORCH_HOME=str(base/'cache/torch'))
        env['PYTHONPATH']=os.pathsep.join((str(code),str(code/'scripts')))
        log=base/('nohup_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log')
        command=[sys.executable,'-u','-B',str(code/'scripts/control_post_ab.py'),'--root',str(root),'--directory',str(base)]
        # Equivalent to nohup: new session, ignored terminal SIGHUP, closed stdin and file output.
        with log.open('x') as handle:
            proc=subprocess.Popen(['nohup',*command],cwd=code,env=env,stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
        state=read(base/'queue_status.json');state.update(controller_pid=proc.pid,controller_command=command,controller_log=str(log))
        # Controller owns future state writes; bootstrap records PID separately to avoid races.
        write(base/'launch.json',state);(base/'controller.pid').write_text(str(proc.pid)+'\n')
        print('POST_AB_QUEUE_REGISTERED',base,'PID='+str(proc.pid),'N1_EXECUTABLE=4','CONDITIONAL_RESERVED=22',flush=True)
        print('POST_AB_LOG',log,flush=True)
    return 0
if __name__=='__main__':sys.exit(main())
