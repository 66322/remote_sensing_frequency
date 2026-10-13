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

def ce_replacement_guard(directory):
    """Only the initial zero-update CUDA-NLL smoke defect may be replaced."""
    d=Path(directory);s=read(d/'queue_status.json');p=read(d/'plan.json')
    if s['status']!='TECHNICAL_FAILURE_HOLD' or s.get('error')!='smoke0 exit=1; see logs/smoke0.log':
        raise RuntimeError('not the narrowly authorized CE smoke failure')
    if p['execution_commit']!='f01f9e94f1e9bdcc9c126b5bc3ffb2a7d3b492f5':
        raise RuntimeError('unexpected failed execution source')
    seal=read(d/'registration.json')
    if seal['plan_sha256']!=sha(d/'plan.json') or seal['code_sha256']!=sha(d/'code_manifest.json'):
        raise RuntimeError('failed snapshot binding changed')
    for n,h in read(d/'code_manifest.json')['files'].items():
        f=(d/'code'/n).resolve();f.relative_to((d/'code').resolve())
        if sha(f)!=h:raise RuntimeError('failed source changed: '+n)
    marker='nll_loss2d_forward_out_cuda_template does not have a deterministic implementation'
    for g in (0,1):
        if marker not in (d/'logs'/('smoke%d.log'%g)).read_text():
            raise RuntimeError('both GPU smoke logs must confirm the same CE defect')
    if any((d/'jobs').iterdir()) or list(d.rglob('*.pth')) or (d/'smoke_pass.json').exists():
        raise RuntimeError('training or passed smoke evidence exists; refuse replacement')
    return dict(directory=str(d),plan_sha256=sha(d/'plan.json'),code_sha256=sha(d/'code_manifest.json'),
                technical_failure_sha256=sha(d/'technical_failure.json'),optimizer_updates=0,
                reason='CUDA NLLLoss deterministic reduction; same CE objective')

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--commit',required=True)
    p.add_argument('--replace-ce-bug-directory',type=Path)
    a=p.parse_args();root=a.root.resolve();root.relative_to(Path('/home/jovyan/zzx').resolve())
    records=root/'records'
    import fcntl
    with (records/'phase2_registration.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        existing=sorted(records.glob('research_phase2_matched_*'))
        replacement=None
        if a.replace_ce_bug_directory is not None:
            failed=a.replace_ce_bug_directory.resolve();failed.relative_to(records)
            if existing!=[failed]:raise RuntimeError('replacement requires exactly the original Phase2 directory')
            replacement=ce_replacement_guard(failed)
            ids=[read(failed/'launch.json')['controller_pid']]+[v['pid'] for v in read(failed/'queue_status.json')['workers'].values()]
            for pid in ids:
                try:
                    if str(failed).encode() in (Path('/proc')/str(pid)/'cmdline').read_bytes():
                        raise RuntimeError('failed queue still owns process '+str(pid))
                except FileNotFoundError:pass
            with (failed/'controller.lock').open('a') as failedlock:fcntl.flock(failedlock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            existing=[]
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
            if replacement:
                plan=read(base/'plan.json');plan['technical_replacement_of']=replacement;write(base/'plan.json',plan)
                write(base/'technical_replacement.json',replacement)
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
            if replacement:
                write(failed/'replacement_registered.json',dict(directory=str(base),commit=commit,registered_at=now(),reason=replacement['reason']))
                print('PHASE2_TECHNICAL_REPLACEMENT_OF',failed)
            print('PHASE2_REGISTERED',base,'PID='+str(proc.pid),'GPU=0,1 CORE_TRAININGS=4 MAX_TRAININGS=6 CORE_UPDATES=48000 MAX_UPDATES=64000 NO24H_DEADLINE')
            print('PHASE2_LOG',logpath)
        except BaseException as exc:
            (base/'registration_failure.json').write_text(json.dumps(dict(error=str(exc),automatic_retry=False),indent=2)+'\n')
            raise

if __name__=='__main__':main()
