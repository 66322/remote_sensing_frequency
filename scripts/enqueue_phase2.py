"""User-run unique snapshot registrar, refuses existing Phase2 or active predecessor."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

FILES=['scripts/'+n+'.py' for n in ('phase2_common','phase2_data','phase2_train','phase2_infer','phase2_analysis',
    'phase2_legacy','control_phase2','prepare_phase2','enqueue_phase2','status_phase2','upload_phase2')]
FILES+=['model/phase2_matched.py','tests/test_phase2.py','docs/protocols/PHASE_2_EXECUTION_20261013.md',
        'docs/protocols/PHASE_2_MATCHED_COMPLEMENTARITY_20261013.md']

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--commit',required=True)
    a=p.parse_args();root=a.root.resolve();root.relative_to(Path('/home/jovyan/zzx').resolve())
    records=root/'records'
    import fcntl
    with (records/'phase2_registration.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        existing=sorted(records.glob('research_phase2_matched_*'))
        if existing:
            for d in existing:print('PHASE2_ALREADY_REGISTERED',d,read(d/'queue_status.json')['status'] if (d/'queue_status.json').exists() else 'HOLD_PARTIAL')
            return
        old=records/'research_phase15_recoverability_20261012T233532_842792'
        state=read(old/'queue_status.json')
        if state['status']!='PHASE15_COMPLETE_AWAITING_REVIEW' or any(j['status']!='COMPLETE' for j in state['jobs'].values()):
            raise RuntimeError('original Phase1.5 not complete')
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():continue
            try:
                if str(old).encode() in (proc/'cmdline').read_bytes():raise RuntimeError('predecessor still owns live process '+proc.name)
            except (FileNotFoundError,PermissionError):pass
        with (old/'controller.lock').open('a') as oldlock:fcntl.flock(oldlock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        commit=subprocess.check_output(['git','-C',str(root),'rev-parse',a.commit+'^{commit}'],text=True).strip()
        base=records/('research_phase2_matched_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()));base.mkdir()
        code=base/'code'
        try:
            for n,h in read(old/'code_manifest.json')['files'].items():
                src=(old/'code'/n).resolve();src.relative_to((old/'code').resolve())
                if sha(src)!=h:raise RuntimeError('immutable inherited code changed: '+n)
                target=code/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(src.read_bytes())
            for n in FILES:
                target=code/n;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+n]))
            sys.path.insert(0,str(code/'scripts'));from phase2_common import write,env,FIT,VAL,now
            write(base/'plan.json',dict(root=str(root),previous=str(old),execution_commit=commit,fit12=FIT,val2=VAL,gpus=[0,1],seed=42,
                predecessor_plan_sha256=sha(old/'plan.json'),predecessor_code_sha256=sha(old/'code_manifest.json'),
                training_jobs={'A_RGB':16000,'A_DSM':16000,'B0':8000,'B2':8000,'B1':8000,'B3':8000},
                conditional_jobs=['B1','B3'],core_updates=48000,max_updates=64000,automatic_retry=False,new_seeds=False,
                test6_loaded=False,held4_loaded=False,wall_deadline_hours=None,registered_at=now()))
            write(base/'code_manifest.json',dict(commit=commit,files={f.relative_to(code).as_posix():sha(f) for f in code.rglob('*') if f.is_file()}))
            write(base/'registration.json',dict(plan_sha256=sha(base/'plan.json'),code_sha256=sha(base/'code_manifest.json'),registered_at=now()))
            for n in ('logs','temporary','cache/torch','cache/cuda','cache/triton','cache/kernels','jobs','smoke','analysis'):(base/n).mkdir(parents=True,exist_ok=True)
            with (base/'cpu_checks.log').open('x') as log:
                subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(code/'tests'),'-p','test_phase2.py','-v'],
                    cwd=code,env=env(base),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
            write(base/'queue_status.json',dict(status='REGISTERED',workers={},observed_at=now()))
            logpath=base/('nohup_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log')
            with logpath.open('x') as log:
                proc=subprocess.Popen([sys.executable,'-u','-B',str(code/'scripts/control_phase2.py'),'--directory',str(base)],
                    cwd=code,env=env(base),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            write(base/'launch.json',dict(controller_pid=proc.pid,log=str(logpath)))
            print('PHASE2_REGISTERED',base,'PID='+str(proc.pid),'GPU=0,1 CORE_TRAININGS=4 MAX_TRAININGS=6 CORE_UPDATES=48000 MAX_UPDATES=64000 NO24H_DEADLINE')
            print('PHASE2_LOG',logpath)
        except BaseException as exc:
            (base/'registration_failure.json').write_text(json.dumps(dict(error=str(exc),automatic_retry=False),indent=2)+'\n')
            raise

if __name__=='__main__':main()
