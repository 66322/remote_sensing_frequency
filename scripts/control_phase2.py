"""Unique two-GPU controller: fixed core, science-gated dynamic wave, failure hold."""
import argparse
import fcntl
from pathlib import Path
import subprocess
import signal
import sys
import time
from phase2_common import *

def main(base):
    base=Path(base);verify(base,False);state=read(base/'queue_status.json')
    if state['status']!='REGISTERED':raise RuntimeError('controller cannot restart a used queue')
    handles=[];active=[]
    def interrupted(signum,frame):raise InterruptedError('external stop signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    with (base/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        def update(status,**kwargs):
            state.update(status=status,controller_pid=os.getpid(),observed_at=now(),**kwargs);write(base/'queue_status.json',state)
        def wave(status,tasks):
            update(status);running=[]
            for gpu,script,args,name in tasks:
                path=base/'logs'/(name+'.log');log=path.open('x');handles.append(log)
                cmd=[sys.executable,'-u','-B',str(base/'code/scripts'/script),'--directory',str(base),*args]
                if gpu is not None:cmd+=['--gpu',str(gpu)]
                proc=subprocess.Popen(cmd,cwd=base/'code',env=env(base,gpu),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                active.append((name,proc))
                running.append((name,gpu,proc));state['workers'][name]=dict(pid=proc.pid,gpu=gpu,status='RUNNING')
                print('PHASE2_START',name,'GPU',gpu,flush=True)
            while running:
                for name,gpu,proc in list(running):
                    result=proc.poll()
                    if result is None:continue
                    state['workers'][name]['status']='COMPLETE' if result==0 else 'TECHNICAL_FAILURE'
                    if result:
                        for other,_,p in running:
                            if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
                        for _,_,p in running:
                            try:p.wait(timeout=30)
                            except subprocess.TimeoutExpired:p.kill();p.wait()
                        raise RuntimeError(name+' exit='+str(result)+'; see logs/'+name+'.log')
                    print('PHASE2_COMPLETE',name,flush=True);running.remove((name,gpu,proc))
                update(status);time.sleep(2 if running else 0)
            for h in handles:h.flush()
        def train_wave(names,status):
            wave(status,[(g,'phase2_train.py',['--task',n],n+str(g) if names.count(n)>1 else n) for g,n in enumerate(names)])
        def eval_wave(system,age):
            wave('EVALUATING_'+system+'_'+str(age),[(g,'phase2_infer.py',['--system',system,'--age',str(age)],'eval_'+system+'_'+str(age)+'_'+str(g)) for g in (0,1)])
        try:
            wave('PREPARING_RESIDENT_INPUTS',[(None,'prepare_phase2.py',[],'prepare')])
            wave('SMOKE_AND_LEGACY_COUNTS',[(0,'phase2_train.py',['--task','smoke'],'smoke0'),
                 (1,'phase2_train.py',['--task','smoke'],'smoke1'),(None,'phase2_legacy.py',[],'legacy_counts')])
            # Two smoke tasks need distinct logs; compare exact same initialization and scope.
            a=read(base/'smoke/gpu0/result.json');b=read(base/'smoke/gpu1/result.json')
            if a['initial_state_sha256']!=b['initial_state_sha256'] or a['trainable']!=b['trainable']:
                raise RuntimeError('matched initialization or parameter scope differs')
            write(base/'smoke_pass.json',dict(common_initial_state=a['initial_state_sha256'],trainable=a['trainable'],total_trainable=a['total_trainable']))
            train_wave(['A_RGB','A_DSM'],'TRAINING_MATCHED_EXPERTS')
            for name in ('A_RGB','A_DSM'):
                done=check_complete(base,base/'jobs'/name)
                if done['initial_state_sha256']!=read(base/'smoke_pass.json')['common_initial_state']:
                    raise RuntimeError('formal expert initial state differs from smoke')
            from itertools import zip_longest
            with (base/'jobs/A_RGB/batch_hashes.jsonl').open() as a,(base/'jobs/A_DSM/batch_hashes.jsonl').open() as b:
                count=0
                for x,y in zip_longest(a,b):
                    if x!=y:raise RuntimeError('paired expert batch stream differs')
                    count+=1
                if count!=16000:raise RuntimeError('incomplete paired batch hashes')
            write(base/'paired_stream_pass.json',dict(steps=count,common_stream=True))
            eval_wave('average',8000);eval_wave('average',16000)
            # Analysis and cache generation use independent CPU/GPU surfaces concurrently.
            wave('MATCHED_GATES_AND_HEAD_CACHE',[(None,'phase2_analysis.py',['--action','gates'],'gates'),
                (0,'phase2_train.py',['--task','head_cache'],'cache0'),(1,'phase2_train.py',['--task','head_cache'],'cache1')])
            train_wave(['B0','B2'],'TRAINING_STATIC_CONTROLS')
            if sha(base/'jobs/B0/batch_hashes.jsonl')!=sha(base/'jobs/B2/batch_hashes.jsonl'):
                raise RuntimeError('static control head streams differ')
            eval_wave('B0',16000);eval_wave('B2',16000)
            wave('STATIC_RESIDUAL_REVIEW',[(None,'phase2_analysis.py',['--action','static'],'static_gate')])
            if read(base/'analysis/static_gate.json')['allow_dynamic']:
                train_wave(['B1','B3'],'TRAINING_GATED_DYNAMIC')
                for name in ('B1','B3'):
                    if sha(base/'jobs'/name/'batch_hashes.jsonl')!=sha(base/'jobs/B0/batch_hashes.jsonl'):
                        raise RuntimeError('dynamic head stream differs from static')
                eval_wave('B1',16000);eval_wave('B3',16000)
            else:print('PHASE2_DYNAMIC_NOT_DISPATCHED SCIENTIFIC_GATE',flush=True)
            wave('FINAL_COUNTS_AND_SUMMARY',[(None,'phase2_analysis.py',['--action','summary'],'summary')])
            update('PHASE2_COMPLETE_AWAITING_REVIEW');print('PHASE2_COMPLETE NO_AUTOMATIC_FOLLOWUP',flush=True)
        except BaseException as exc:
            for name,proc in active:
                if proc.poll() is None:
                    os.killpg(proc.pid,signal.SIGTERM)
                    state['workers'][name]['status']='INTERRUPTED_HOLD'
            for _,proc in active:
                if proc.poll() is None:
                    try:proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            for name,proc in active:
                if state['workers'][name]['status']=='RUNNING':
                    state['workers'][name]['status']='COMPLETE' if proc.returncode==0 else 'INTERRUPTED_HOLD'
            status='EXTERNAL_INTERRUPTION_HOLD' if isinstance(exc,InterruptedError) else 'TECHNICAL_FAILURE_HOLD'
            update(status,error=str(exc));write(base/'technical_failure.json',dict(error=str(exc),automatic_retry=False,observed_at=now()))
            raise
        finally:
            for h in handles:h.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);main(p.parse_args().directory.resolve())
