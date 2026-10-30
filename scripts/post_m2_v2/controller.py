import datetime as dt
import json
import os
import signal
import subprocess
import sys
import time
import traceback
from pathlib import Path
from . import common as c

DEPENDENCIES=dict(B0=[],B1=[],G1=['B0','B1'],Q1=['B0','B1'],S1=['B0','B1'],
    G2=['G1'],G3=['G1'],Q2=['Q1'],Q3=['Q2'],S2=['S1'],S3=['S1'])
# Prioritise the only data-producing chain Q1->Q2->Q3, while other ready routes fill slots.
ORDER=('B0','B1','Q1','S1','Q2','G1','Q3','S2','S3','G2','G3')

def runnable(pending,completed,dependencies):
    return [j for j in pending if all(x in completed and completed[x]['status']=='COMPLETE' for x in dependencies[j])]

def gpu_snapshot():
    rows=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,name,memory.free,utilization.gpu',
        '--format=csv,noheader,nounits'],text=True,timeout=15)
    apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory',
        '--format=csv,noheader,nounits'],text=True,timeout=15)
    use={int(row.split(',')[0]):[x.strip() for x in row.split(',')] for row in rows.splitlines() if int(row.split(',')[0]) in (0,1)}
    return dict(gpus=use,compute_apps=apps,observed_at=c.now())

def idle_gpus():
    row=gpu_snapshot()
    if set(row['gpus'])!={0,1}:raise RuntimeError('authorized physical GPU0/1 absent')
    if any('H100' not in r[2] or float(r[3])<c.CONFIG['gpu_min_free_mib'] or r[1] in row['compute_apps'] for r in row['gpus'].values()):
        raise RuntimeError('GPU0/1 unavailable or busy; do not occupy/wait/restart existing tasks')
    return row

def stop_owned(workers):
    # Each worker owns a separate process group containing its own loaders only.
    for p in workers.values():
        if p.poll() is None:
            try:os.killpg(p.pid,signal.SIGTERM)
            except ProcessLookupError:pass
    deadline=time.monotonic()+10
    for p in workers.values():
        try:p.wait(timeout=max(.1,deadline-time.monotonic()))
        except subprocess.TimeoutExpired:
            try:os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            p.wait(timeout=10)

def run(base,phase):
    import fcntl
    base=Path(base);contract=c.runtime_contract(base)
    with (base/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if phase=='train':
            tuning=c.read(base/'execution_tuning.json')
            if tuning['source']!=contract['source']:raise RuntimeError('tuning source differs')
            for arm in c.PROFILES:
                r=c.read(base/'profiles'/(arm+'.json'))
                if r['status']!='REAL_PATH_PROFILE_PASSED' or r['source']!=contract['source']:
                    raise RuntimeError('profile/source not ready: '+arm)
        snapshot=idle_gpus()
        c.write(base/(phase+'_started.json'),dict(observed_at=c.now(),pid=os.getpid(),gpu=snapshot),once=True)
        pending=list(c.PROFILES if phase=='profile' else ORDER);completed={};workers={};active={};files=[]
        code=Path(__file__).resolve().parents[1]/'post_m2_multiroute.py';serial=0;last_telemetry=0
        try:
            for gpu in (0,1):
                log=(base/('%s_gpu%s.log'%(phase,gpu))).open('x',encoding='utf-8');files.append(log)
                p=subprocess.Popen([sys.executable,'-u','-B',str(code),'worker','--base',str(base),'--gpu',str(gpu)],
                    stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True,env=c.env(gpu,base),start_new_session=True)
                workers[gpu]=p
            while pending or active:
                for gpu,p in workers.items():
                    if (base/('worker_first_failure_gpu%s.json'%gpu)).exists():raise RuntimeError('worker failure receipt; original stack preserved before thread shutdown')
                    if p.poll() is not None:raise RuntimeError('worker exited; inspect first original stack in '+phase+'_gpu'+str(gpu)+'.log')
                for gpu,task in list(active.items()):
                    path=base/'tasks'/(task['id']+'.json')
                    if path.exists():
                        result=c.read(path);completed[task['arm']]=result;del active[gpu]
                        if phase=='train' and task['arm'] in ('B0','B1') and result['status']!='COMPLETE':
                            raise RuntimeError('baseline not learned: invalid prerequisite, no scientific negative')
                        c.write(base/(phase+'_progress.json'),dict(completed=completed,pending=pending,active=active,observed_at=c.now()))
                    elif time.monotonic()-task['started_monotonic']>(c.CONFIG['profile_timeout_seconds']+120 if phase=='profile' else c.CONFIG['task_timeout_hours']*3600):
                        raise RuntimeError('task hard timeout')
                    else:
                        hb=base/('heartbeat_gpu%s.json'%gpu)
                        if (hb.exists() and time.time()-hb.stat().st_mtime>c.CONFIG['heartbeat_timeout_seconds']) or (not hb.exists() and time.monotonic()-task['started_monotonic']>c.CONFIG['heartbeat_timeout_seconds']):
                            raise RuntimeError('no progress heartbeat; resource/code wait requires diagnosis')
                if time.monotonic()-last_telemetry>=10:
                    with (base/(phase+'_resources.jsonl')).open('a',encoding='utf-8') as f:f.write(json.dumps(gpu_snapshot())+'\n')
                    last_telemetry=time.monotonic()
                options=list(pending) if phase=='profile' else runnable(pending,completed,DEPENDENCIES)
                for gpu in workers:
                    if gpu in active or not options:continue
                    arm=options.pop(0);pending.remove(arm);serial+=1
                    task=dict(id='%s_%02d_%s'%(phase,serial,arm),arm=arm,phase=phase,started_monotonic=time.monotonic())
                    active[gpu]=task;workers[gpu].stdin.write(json.dumps(task)+'\n');workers[gpu].stdin.flush()
                    print('DISPATCH',phase,arm,'physical_gpu',gpu,flush=True)
                if pending and not active and not options:
                    # Invalid route prerequisites close descendants; no infinite data/teacher wait.
                    c.write(base/'blocked_routes.json',dict(jobs=pending,reason='invalid own prerequisite',observed_at=c.now()))
                    break
                time.sleep(.5)
            c.write(base/(phase+'_complete.json'),dict(status='COMPLETE' if not pending else 'COMPLETE_WITH_INVALID_ROUTES',
                jobs=completed,blocked=pending,observed_at=c.now(),source=contract['source']),once=True)
            if phase=='profile':
                paths={}
                for group in [('B0','B1','Q2'),('G1','G2'),('S1','S2')]:
                    profiles={a:c.read(base/'profiles'/(a+'.json')) for a in group}
                    micros=set.intersection(*[{x['micro'] for x in p['candidates']} for p in profiles.values()])
                    choose=lambda a,m:min((x for x in profiles[a]['candidates'] if x['micro']==m),key=lambda x:x['median_seconds'])
                    micro=min(micros,key=lambda m:sum(choose(a,m)['median_seconds'] for a in group))
                    for a in group:
                        cfg=choose(a,micro)
                        if cfg['median_wait_seconds']>max(.05,cfg['median_seconds']*.5):raise RuntimeError('matched configuration has unresolved input wait')
                        paths[a]=cfg
                c.write(base/'execution_tuning.json',dict(paths=paths,source=contract['source'],
                    rule='common microbatch within each matched mechanism group; independently measured loader workers',observed_at=c.now()),once=True)
                estimates={}
                for arm in c.JOBS:
                    row=c.read(base/'profiles'/(c.PROFILE_FOR[arm]+'.json'));selected=paths[c.PROFILE_FOR[arm]]
                    case=row['evaluation']['total_seconds']+row['evaluation']['counts_seconds']
                    estimates[arm]=dict(training_seconds=8000*selected['median_seconds'],
                        calibration_cases=20,selected_outer_cases=20,extra_final_cases_max=20,
                        conservative_evaluation_seconds_range=[40*case,60*case])
                c.write(base/'measured_budget.json',dict(jobs=estimates,observed_at=c.now(),
                    total_training_seconds=sum(x['training_seconds'] for x in estimates.values()),
                    note='evaluation bound conservatively adds CPU counting despite overlap; dual-GPU completion depends on DAG, not simple division by two'),once=True)
        except BaseException as exc:
            c.write(base/(phase+'_first_failure.json'),dict(observed_at=c.now(),error=str(exc),traceback=traceback.format_exc(),
                active=active,pending=pending,completed=list(completed),auto_retry=False),once=True)
            raise
        finally:
            stop_owned(workers)
            for f in files:f.close()
