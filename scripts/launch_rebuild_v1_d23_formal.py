"""Two-GPU fixed eight-arm 4000-step D23 development screen; no new budget gate."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
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
def stop(process):
    if process.poll() is None:
        os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);process.wait()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--commit',required=True);ap.add_argument('--directory',type=Path,required=True)
    args=ap.parse_args();root=args.root.resolve();root.relative_to(Path('/home/jovyan/zzx').resolve())
    base=args.directory.resolve();base.relative_to(root/'records')
    if not base.name.startswith('research_d23_b_formal_'):raise ValueError('unexpected formal directory')
    if base.exists():
        if {p.name for p in base.iterdir()}!={'launch_formal.py'}:raise ValueError('refuse existing run contents')
    else:base.mkdir()
    commit=subprocess.check_output(['git','-C',str(root),'rev-parse',args.commit+'^{commit}'],text=True).strip()
    code=base/'code'
    for name in FILES:
        raw=subprocess.check_output(['git','-C',str(root),'show',commit+':'+name])
        p=code/name;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(raw)
    lock=json.loads((code/'configs/rebuild_v1/d23_b_runtime_20261001.json').read_text())
    validate_bindings(root,code,lock)
    write(base/'runtime_lock.json',lock);(base/'execution_commit.txt').write_text(commit+'\n')
    plan=dict(source_commit=commit,created_at=datetime.now().astimezone().isoformat(),
      schedule=SCHEDULE,steps_per_arm=4000,seed=42,expert_micro_batch=8,gate_batch=16,
      checkpoint_selection='fixed_final_step_protocol_exception',test6_loaded=False,
      development_scope='Potsdam Val2 3_11/5_10, 14 conditions, NoBoundary fg5',
      expected_runtime_lock_sha256=digest(base/'runtime_lock.json'))
    write(base/'plan.json',plan);(base/'logs').mkdir()
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
             PYTHONDONTWRITEBYTECODE='1')
    running={};pending={g:list(a) for g,a in SCHEDULE.items()};states={};failed=False
    def persist(status):
        write(base/'queue_status.json',dict(status=status,observed_at=datetime.now().astimezone().isoformat(),
          jobs=states,pending=pending,formal_training_requested=True,test6_loaded=False))
    def launch(gpu):
        arm=pending[gpu].pop(0);log=(base/'logs'/(arm+'.log')).open('x')
        p=subprocess.Popen([sys.executable,'-B',str(code/'scripts/run_rebuild_v1_d23.py'),
          '--root',str(root),'--gpu',str(gpu),'--output',str(base/'jobs'/arm),'--mode','formal',
          '--arm',arm,'--runtime-lock',str(base/'runtime_lock.json')],
          env=env,cwd=root,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        running[gpu]=(arm,p,log,time.monotonic())
        states[arm]=dict(gpu=gpu,pid=p.pid,status='PROCESS_STARTED',
          observed_at=datetime.now().astimezone().isoformat())
        print('D23_FORMAL_PROCESS_STARTED',gpu,arm,'pid='+str(p.pid),flush=True)
        persist('RUNNING')
    persist('READY')
    try:
        for gpu in SCHEDULE:launch(gpu)
        heartbeat=time.monotonic()
        while running:
            for gpu,(arm,p,log,started) in list(running.items()):
                if p.poll() is None and time.monotonic()-started>lock['job_wall_seconds']+30:
                    stop(p);states[arm]['reason']='hard wall timeout'
                if p.poll() is not None:
                    log.close();complete=base/'jobs'/arm/'formal_complete.json'
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
                    lines=(base/'logs'/(arm+'.log')).read_text(errors='replace').splitlines()
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
        manifest={a:str(base/'jobs'/a/'evaluation/summary.json') for arms in SCHEDULE.values() for a in arms}
        write(base/'screen_manifest.json',manifest)
        with (base/'screen.log').open('x') as log:
            result=subprocess.run([sys.executable,'-B',str(code/'scripts/summarize_rebuild_v1_d23.py'),
              '--manifest',str(base/'screen_manifest.json'),'--output',str(base/'screen_result.json')],
              env=dict(env,CUDA_VISIBLE_DEVICES=''),cwd=code,stdout=log,stderr=subprocess.STDOUT)
        failed=result.returncode!=0
        persist('SCREEN_AUDIT_FAILED' if failed else 'COMPLETE')
    # Upload even a partial technical failure; never hide raw logs or rerun automatically.
    subprocess.run([sys.executable,'-B',str(code/'scripts/upload_rebuild_v1_d23_formal_records.py'),
      '--root',str(root),'--directory',str(base)],env=env,check=True)
    if failed:raise RuntimeError('formal queue stopped; uploaded evidence requires review')
    print('D23_FORMAL_SCREEN_COMPLETE',str(base),flush=True)
if __name__=='__main__':main()
