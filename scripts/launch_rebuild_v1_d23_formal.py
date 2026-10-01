"""Two-GPU fixed eight-arm 4000-step D23 development screen; no new budget gate."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time

SCHEDULE={0:('TSF','TS','TCAP','TSF_shuffleS'),1:('T0','TF','TSF_CE','TSF_shuffleF')}
FILES=('scripts/run_rebuild_v1_d23.py','scripts/d23_engine.py','scripts/d23_lifecycle.py',
 'scripts/probe_rebuild_v1_d23_gate.py','scripts/summarize_rebuild_v1_d23.py',
 'scripts/upload_rebuild_v1_d23_formal_records.py','model/rebuild_v1_d23_gate.py',
 'configs/rebuild_v1/d23_b_runtime_20261001.json')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):
    temp=path.with_suffix('.tmp')
    with temp.open('w') as f:json.dump(value,f,indent=2,allow_nan=False)
    os.replace(temp,path)
def validate_bindings(root,code,lock):
    if lock['status']!='FULL_ENGINE_RUNTIME_ADMITTED':raise ValueError('runtime admission absent')
    for name,expected in lock['source_sha256'].items():
        if digest(code/'scripts'/name)!=expected:raise ValueError('source binding changed: '+name)
    if digest(code/'model/rebuild_v1_d23_gate.py')!=lock['gate_source_sha256']:
        raise ValueError('gate source binding changed')
    for p,k in (('configs/rebuild_v1/r05_quality_plus_dropout_16k.json','base_sha256'),
      ('configs/rebuild_v1/potsdam_split_seed20260915.json','split_sha256'),
      ('records/rebuild_v1_d21_queue_20260928/input_manifest.json','input_manifest_sha256')):
        if digest(root/p)!=lock[k]:raise ValueError('input/config binding changed: '+p)
def prepare_resume_job(base,arm,old,stamp):
    old=old.resolve();old.relative_to(base.resolve())
    target=base/'jobs'/(arm+'_resume_'+stamp)
    if not old.exists():return old,False
    target.mkdir(parents=True,exist_ok=False)
    checkpoint=old/'training/last_train_state.pth'
    if not checkpoint.exists():return target,False
    for name in ('preflight.json','formal_fit_statistics.json','training/last_train_state.pth','training/training_complete.json'):
        source=old/name
        if source.exists():
            out=target/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,out)
            if digest(out)!=digest(source):raise RuntimeError('resume copy checksum mismatch')
    # Partial evaluation and normalized cache remain in the old directory.
    return target,True

def stop(process):
    if process.poll() is None:
        os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);process.wait()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--commit',required=True);ap.add_argument('--directory',type=Path,required=True)
    ap.add_argument('--resume-queue',action='store_true')
    args=ap.parse_args();root=args.root.resolve();root.relative_to(Path('/home/jovyan/zzx').resolve())
    base=args.directory.resolve();base.relative_to(root/'records')
    if not base.name.startswith('research_d23_b_formal_'):raise ValueError('unexpected formal directory')
    if args.resume_queue:
        if not (base/'plan.json').exists():raise ValueError('existing queue plan absent')
    elif base.exists():
        if {p.name for p in base.iterdir()}!={'launch_formal.py'}:raise ValueError('refuse existing run contents')
    else:base.mkdir()
    stamp=datetime.now().strftime('%Y%m%dT%H%M%S%f')
    previous=json.loads((base/'queue_status.json').read_text()) if args.resume_queue else {'jobs':{}}
    for row in previous['jobs'].values():
        proc=Path('/proc')/str(row.get('pid',-1))/'cmdline'
        if proc.exists() and str(base).encode() in proc.read_bytes():
            raise RuntimeError('old queue worker is still running; stop foreground launcher first')
    commit=subprocess.check_output(['git','-C',str(root),'rev-parse',args.commit+'^{commit}'],text=True).strip()
    code=base/('code_resume_'+stamp if args.resume_queue else 'code')
    for name in FILES:
        raw=subprocess.check_output(['git','-C',str(root),'show',commit+':'+name])
        p=code/name;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(raw)
    lock=json.loads((base/'runtime_lock.json' if args.resume_queue else code/'configs/rebuild_v1/d23_b_runtime_20261001.json').read_text())
    validate_bindings(root,code,lock)
    if not args.resume_queue:
        write(base/'runtime_lock.json',lock);(base/'execution_commit.txt').write_text(commit+'\n')
    else:
        write(base/('resume_event_'+stamp+'.json'),dict(controller_commit=commit,previous=previous,
          observed_at=datetime.now().astimezone().isoformat(),strategy='copy matching checkpoint, retain old evaluation, skip complete jobs'))
    plan=dict(source_commit=commit,created_at=datetime.now().astimezone().isoformat(),
      schedule=SCHEDULE,steps_per_arm=4000,seed=42,expert_micro_batch=8,gate_batch=16,
      checkpoint_selection='fixed_final_step_protocol_exception',test6_loaded=False,
      development_scope='Potsdam Val2 3_11/5_10, 14 conditions, NoBoundary fg5',
      expected_runtime_lock_sha256=digest(base/'runtime_lock.json'))
    if not args.resume_queue:write(base/'plan.json',plan)
    logs=base/('logs_resume_'+stamp if args.resume_queue else 'logs');logs.mkdir()
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
             PYTHONDONTWRITEBYTECODE='1')
    running={};pending={g:list(a) for g,a in SCHEDULE.items()};states={};failed=False
    job_paths={a:Path(previous['jobs'].get(a,{}).get('job_directory',base/'jobs'/a)) for arms in SCHEDULE.values() for a in arms}
    for gpu,arms in SCHEDULE.items():
        for arm in arms:
            complete=job_paths[arm]/'formal_complete.json'
            if args.resume_queue and complete.exists() and json.loads(complete.read_text()).get('global_step')==4000:
                pending[gpu].remove(arm);states[arm]=dict(gpu=gpu,status='COMPLETE',job_directory=str(job_paths[arm]))
    screen_manifest=base/('screen_manifest_'+stamp+'.json' if args.resume_queue else 'screen_manifest.json')
    screen_result=base/('screen_result_'+stamp+'.json' if args.resume_queue else 'screen_result.json')
    screen_log=logs/'screen.log'
    def persist(status):
        write(base/'queue_status.json',dict(status=status,observed_at=datetime.now().astimezone().isoformat(),
          jobs=states,pending=pending,formal_training_requested=True,test6_loaded=False,
          screen_manifest=str(screen_manifest),screen_result=str(screen_result),screen_log=str(screen_log)))
    def launch(gpu):
        arm=pending[gpu].pop(0)
        out,resume=(prepare_resume_job(base,arm,job_paths[arm],stamp) if args.resume_queue else (job_paths[arm],False))
        job_paths[arm]=out;log=(logs/(arm+'.log')).open('x')
        p=subprocess.Popen([sys.executable,'-B',str(code/'scripts/run_rebuild_v1_d23.py'),
          '--root',str(root),'--gpu',str(gpu),'--output',str(out),'--mode','formal',
          '--arm',arm,'--runtime-lock',str(base/'runtime_lock.json')]+(['--resume'] if resume else []),
          env=env,cwd=root,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        running[gpu]=(arm,p,log,time.monotonic())
        states[arm]=dict(gpu=gpu,pid=p.pid,status='PROCESS_STARTED',job_directory=str(out),log_path=str(logs/(arm+'.log')),
          observed_at=datetime.now().astimezone().isoformat())
        print('D23_FORMAL_PROCESS_STARTED',gpu,arm,'pid='+str(p.pid),flush=True)
        persist('RUNNING')
    persist('READY')
    try:
        for gpu in SCHEDULE:
            if pending[gpu]:launch(gpu)
        heartbeat=time.monotonic()
        while running:
            for gpu,(arm,p,log,started) in list(running.items()):
                if p.poll() is None and time.monotonic()-started>lock['job_wall_seconds']+30:
                    stop(p);states[arm]['reason']='hard wall timeout'
                if p.poll() is not None:
                    log.close();complete=job_paths[arm]/'formal_complete.json'
                    good=p.returncode==0 and complete.exists() and json.loads(complete.read_text()).get('global_step')==4000
                    states[arm].update(status='COMPLETE' if good else 'TECHNICAL_FAILURE',
                      returncode=p.returncode,observed_at=datetime.now().astimezone().isoformat())
                    failed|=not good;del running[gpu]
                    print('D23_FORMAL_JOB_STATUS',arm,states[arm]['status'],flush=True)
                    persist('FAILURE_DRAINING' if failed else 'RUNNING')
            # Inspect both exits before launching replacements; failure stops new jobs.
            if not failed:
                for gpu in SCHEDULE:
                    if gpu not in running and pending[gpu]:launch(gpu)
            if time.monotonic()-heartbeat>=30:
                for gpu,(arm,p,log,started) in running.items():
                    lines=(logs/(arm+'.log')).read_text(errors='replace').splitlines()
                    last=lines[-1][:180] if lines else 'initializing'
                    print('D23_PROGRESS',gpu,arm,'elapsed_minutes=%.1f'%((time.monotonic()-started)/60),last,flush=True)
                heartbeat=time.monotonic()
            time.sleep(2)
    except BaseException:
        for _,p,log,_ in running.values():stop(p);log.close()
        persist('INTERRUPTED')
        raise
    if failed:
        persist('TECHNICAL_FAILURE')
    else:
        manifest={a:str(job_paths[a]/'evaluation/summary.json') for arms in SCHEDULE.values() for a in arms}
        write(screen_manifest,manifest)
        with screen_log.open('x') as log:
            result=subprocess.run([sys.executable,'-B',str(code/'scripts/summarize_rebuild_v1_d23.py'),
              '--manifest',str(screen_manifest),'--output',str(screen_result)],
              env=dict(env,CUDA_VISIBLE_DEVICES=''),cwd=code,stdout=log,stderr=subprocess.STDOUT)
        failed=result.returncode!=0
        persist('SCREEN_AUDIT_FAILED' if failed else 'COMPLETE')
    # Upload even a partial technical failure; never hide raw logs or rerun automatically.
    if sys.stdin.isatty():
        subprocess.run([sys.executable,'-B',str(code/'scripts/upload_rebuild_v1_d23_formal_records.py'),
          '--root',str(root),'--directory',str(base)],env=env,check=True)
    else:
        print('D23_UPLOAD_PENDING: run uploader interactively after completion; credentials are not stored',flush=True)
        print('D23_UPLOAD_SCRIPT='+str(code/'scripts/upload_rebuild_v1_d23_formal_records.py'),flush=True)
    if failed:raise RuntimeError('formal queue stopped; uploaded evidence requires review')
    print('D23_FORMAL_SCREEN_COMPLETE',str(base),flush=True)
if __name__=='__main__':main()
