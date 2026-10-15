"""Work-conserving GPU queue, bounded asynchronous counts, explicit RAM leases."""
import argparse
import sys
import os
import signal
import time
import traceback
import multiprocessing as mp
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import phase3_m1_common as c

class Controller:
    def __init__(self,base,pf):
        self.base=Path(base); self.p=c.read(self.base/'plan.json'); self.pf=pf
        self.ctx=mp.get_context('fork'); self.events=self.ctx.Queue()
        self.commands={g:self.ctx.Queue() for g in (0,1)}; self.acks={g:self.ctx.Queue() for g in (0,1)}
        self.ready=set(); self.running={}; self.cache={}; self.pending=0; self.ephemeral={}
        self.rows={}; self.primary_parts={}; self.train_done=set(); self.failures=[]
        self.counter_decided=False; self.rgb_started=False; self.rgb_done={t:0 for t in c.VAL}
        self.fit_release_pending=set(); self.fit_release_started=False; self.stopped_gpus=set()
        self.rgb_cpu_done={t:0 for t in c.VAL}; self.last_report=0; self.sequence=0
        self.bootstrap=deque(dict(kind='RGB_CLEAN',tile=t) for t in c.VAL)
        self.train=deque(c.job_list()); self.other=deque(dict(kind='INFER_CLEAN',job='M00_42',tile=t) for t in c.VAL)
        self.rgb=deque(); self.known_jobs=['M00_42']
        self.state=dict(status='INITIALIZING',workers={},automatic_retry=False,actual_new_updates=0)
        recovery=c.recovery(self.base)
        if recovery:
            self.train_done=set(recovery['completed'])
            self.train=deque(t for t in self.train if t['job'] not in self.train_done)
            # Prior pixel arrays were anonymous RAM and did not survive reboot.
            for job in sorted(self.train_done):
                self.known_jobs.append(job)
                self.other.extend(dict(kind='INFER_CLEAN',job=job,tile=t) for t in c.VAL)
                self.append_diagnostics(job)
            self.state['actual_new_updates']=16000*len(self.train_done)
            self.state['inherited_completed_jobs']=sorted(self.train_done)
        # No CUDA exists in this parent. Fork every GPU before starting thread pools.
        from phase3_m1_runtime import worker
        self.workers={}
        for g in (0,1):
            proc=self.ctx.Process(target=worker,args=(str(base),g,self.commands[g],self.events,self.acks[g]))
            proc.start(); self.workers[g]=proc
            self.state['workers'][str(g)]=dict(pid=proc.pid,status='INITIALIZING')
        self.cpu=ThreadPoolExecutor(max_workers=pf['analysis_threads'])
        self.report()

    def report(self,status=None):
        if status: self.state['status']=status
        self.state.update(observed_at=c.now(),pending_cpu=self.pending,ready_gpus=sorted(self.ready),
             running={str(g):t for g,t in self.running.items()},pending_training=len(self.train),pending_other=len(self.other),
             pending_rgb=len(self.rgb),retained_ram_bytes=sum(z['packet'].meta['bytes'] for z in self.cache.values()),
             ephemeral_packets=len(self.ephemeral),completed_training_jobs=sorted(self.train_done),
             failed_tasks=len(self.failures),rgb_cases_gpu_done=self.rgb_done,rgb_cases_counted=self.rgb_cpu_done)
        c.write(self.base/'queue_status.json',self.state); self.last_report=time.monotonic()

    def lease(self,keys):
        for key in keys: self.cache[key]['users']+=1
    def release(self,keys):
        for key in keys:
            self.cache[key]['users']-=1
            if self.cache[key]['users']<0: raise RuntimeError('negative RAM lease')
        self.retire_ram()
    def retire_ram(self,force=False):
        for key,z in list(self.cache.items()):
            tile=key.split('/')[-1]
            if z['users']==0 and (force or self.rgb_cpu_done[tile]==160):
                size=z['packet'].meta['bytes']; z['packet'].close(); del self.cache[key]
                c.write(self.base/'retirement'/('ram_'+key.replace('/','_')+'.json'),
                    dict(kind='anonymous_memfd',key=key,bytes=size,last_consumer_finished=True,observed_at=c.now()))

    def submit(self,fn,meta,*args,keys=(),eid=None):
        self.pending+=1; self.lease(keys)
        f=self.cpu.submit(fn,*args)
        def done(future):
            try: event=dict(kind='CPU',result=future.result(),meta=meta,keys=keys,eid=eid)
            except BaseException as exc: event=dict(kind='CPU_ERROR',error=str(exc),traceback=traceback.format_exc(),meta=meta,keys=keys,eid=eid)
            self.events.put(event)
        f.add_done_callback(done)

    def pairs(self,packet,task,targets):
        from phase3_m1_numeric import analyze
        token=str(self.sequence); self.sequence+=1
        self.ephemeral[token]=dict(packet=packet,left=len(targets),task=task)
        if not targets:
            packet.close(); del self.ephemeral[token]
            if task['kind']=='RGB_FAULT': self.rgb_cpu_done[task['tile']]+=1
            return
        tile=task['tile']
        for job in targets:
            if task['kind']=='DSM_FAULT':
                keys=['RGB/'+tile]; r=self.cache[keys[0]]['packet'].arrays['score']; d=packet.arrays['score']
            else:
                keys=[job+'/'+tile]; r=packet.arrays['score']; d=self.cache[keys[0]]['packet'].arrays['score']
            mask=packet.arrays.get('mask'); border=8 if task.get('damage')=='shift8' else 0
            self.submit(analyze,dict(type='PAIR',task=task,job=job),r,d,tile,mask,border,'both',packet.arrays.get('healthy'),keys=keys,eid=token)

    def clean_pairs(self,job,tile):
        from phase3_m1_numeric import analyze
        kr,kd='RGB/'+tile,job+'/'+tile
        if kr not in self.cache or kd not in self.cache: return
        marker=self.base/'clean'/f'{job}_{tile}.scheduled.json'
        if marker.exists(): return
        c.write(marker,dict(job=job,tile=tile,observed_at=c.now()))
        r=self.cache[kr]['packet'].arrays['score']; d=self.cache[kd]['packet'].arrays['score']
        for availability in ('both','rgb_missing','dsm_missing'):
            self.submit(analyze,dict(type='CLEAN_PAIR',job=job,tile=tile,availability=availability),
                        r,d,tile,None,0,availability,keys=[kr,kd])

    def collect_packet(self,event):
        from phase24_ipc import Packet
        packet=Packet.receive(event['packet']); task=event['task']; gpu=event['gpu']; kind=task['kind']; tile=task['tile']
        self.acks[gpu].put(dict(accepted=True))  # Handoff, not CPU completion: immediately free GPU lane.
        if kind in ('RGB_CLEAN','DSM_CLEAN','INFER_CLEAN'):
            key=('RGB' if kind=='RGB_CLEAN' else task['job'])+'/'+tile
            if key in self.cache: packet.close(); raise RuntimeError('duplicate clean packet '+key)
            self.cache[key]=dict(packet=packet,users=0)
            if kind!='RGB_CLEAN':
                from phase3_m1_numeric import primary
                self.submit(primary,dict(type='PRIMARY',job=task['job'],tile=tile),packet.arrays['score'],tile,keys=[key])
                self.clean_pairs(task['job'],tile)
            else:
                for job in self.known_jobs: self.clean_pairs(job,tile)
        elif kind=='DSM_FAULT': self.pairs(packet,task,[task['job']])
        elif kind=='RGB_FAULT':
            self.rgb_done[tile]+=1
            targets=[j for j in self.known_jobs if j+'/'+tile in self.cache]
            self.pairs(packet,task,targets)
        else: packet.close(); raise RuntimeError('unknown packet task')

    def store_primary(self,job,tile,result):
        parts=self.primary_parts.setdefault(job,{})
        if tile in parts: raise RuntimeError('duplicate primary tile')
        parts[tile]=result
        if set(parts)==set(c.VAL):
            row=dict(job=job,tiles=parts,binding=c.binding(self.base),observed_at=c.now())
            if job=='M00_42': row['historical_reuse']=True
            self.rows[job]=row; c.write(self.base/'primary'/f'{job}.json',row)
            self.retire_resume(job)
    def retire_resume(self,job):
        if job in self.train_done and job in self.rows and not self.rows[job].get('failed'):
            folder=self.base/'jobs'/job
            done=c.read(folder/'complete.json')
            if c.sha(folder/'endpoint.pth')!=done['checkpoint_sha256']: raise RuntimeError('endpoint changed before optimizer retirement')
            c.retire(self.base,folder/'last_resume.pth','16k endpoint and clean integer evidence persisted; no remaining optimizer consumer')

    def cpu_event(self,event):
        self.pending-=1; meta=event['meta']
        if event['kind']=='CPU_ERROR':
            self.failures.append(event); c.write(self.base/'failures'/f'cpu_{self.sequence}.json',event); self.sequence+=1
        elif meta['type']=='PRIMARY': self.store_primary(meta['job'],meta['tile'],event['result'])
        elif meta['type']=='CLEAN_PAIR':
            f=self.base/'clean'/f"{meta['job']}_{meta['tile']}_{meta['availability']}.json"
            c.write(f,dict(meta,counts=event['result'],binding=c.binding(self.base)))
        else:
            task=meta['task']; cid=f"{task['kind']}_{task['tile']}_{task.get('family','global')}_{task.get('realization',0)}_{task['damage']}"
            c.write(self.base/'results'/meta['job']/(cid+'.json'),dict(case=task,job=meta['job'],counts=event['result'],binding=c.binding(self.base)))
        self.release(event['keys'])
        if event.get('eid') is not None:
            item=self.ephemeral[event['eid']]; item['left']-=1
            if item['left']==0:
                task=item['task']; item['packet'].close(); del self.ephemeral[event['eid']]
                if task['kind']=='RGB_FAULT': self.rgb_cpu_done[task['tile']]+=1
                self.retire_ram()

    def append_diagnostics(self,job):
        for tile in c.VAL:
            self.other.append(dict(kind='SCALE',job=job,tile=tile))
            for damage in ('down4','shift8'): self.other.append(dict(kind='DSM_FAULT',job=job,tile=tile,damage=damage))

    def maybe_counter(self):
        if self.counter_decided: return
        gate=c.gate(self.rows)
        if gate is None: return
        recovery=c.recovery(self.base)
        if recovery and recovery.get('previous_gate') is not None:
            expected={k:v for k,v in recovery['previous_gate'].items() if k!='binding'}
            if gate!=expected: raise RuntimeError('recomputed pre-reboot amplitude gate differs; do not change dispatch')
        self.counter_decided=True; c.write(self.base/'analysis/amplitude_gate.json',dict(gate,binding=c.binding(self.base)))
        if gate['accepted']:
            for seed in (42,17): self.train.appendleft(dict(kind='TRAIN',job=f'C21_{seed}',arm='C21',seed=seed))
        else:
            for seed in (42,17): c.write(self.base/'skipped'/f'C21_{seed}.json',dict(reason='prespecified amplitude gate not passed',optimizer_updates=0))

    def start_rgb(self):
        if self.rgb_started: return
        self.rgb_started=True
        for tile in c.VAL:
            for family in ('pixel','random','gradient','matched'):
                for i in range(1,21):
                    for damage in ('zero','down4'):
                        self.rgb.append(dict(kind='RGB_FAULT',tile=tile,family=family,realization=i,damage=damage))
        self.report('SHARED_RGB_FORWARD_AND_PARALLEL_COUNTS')

    def run(self):
        from queue import Empty
        self.append_diagnostics('M00_42')
        while True:
            self.maybe_counter()
            if self.counter_decided and not self.train and not any(t['kind']=='TRAIN' for t in self.running.values()) and not self.fit_release_started:
                self.fit_release_started=True; self.fit_release_pending={0,1}; c.release_fit(self.base,'parent')
            if not self.bootstrap and not self.train and not self.other and not self.running:
                if not self.counter_decided:
                    if self.pending==0:
                        self.counter_decided=True
                        for seed in (42,17): c.write(self.base/'skipped'/f'C21_{seed}.json',dict(reason='required primary evidence incomplete',optimizer_updates=0))
                if self.counter_decided: self.start_rgb()
            for gpu in sorted(list(self.ready)):
                task=None
                if self.bootstrap: task=self.bootstrap.popleft()
                elif self.train: task=self.train.popleft()
                elif gpu in self.fit_release_pending:
                    self.fit_release_pending.remove(gpu); task=dict(kind='RELEASE_FIT')
                elif self.other: task=self.other.popleft()
                elif self.rgb and len(self.ephemeral)<4: task=self.rgb.popleft()
                if task:
                    self.ready.remove(gpu); self.running[gpu]=task; self.commands[gpu].put(task)
                    print('M1_TASK_START',gpu,task,flush=True)
                    self.state['workers'][str(gpu)]['status']=task['kind']; self.report('RUNNING')
                elif self.rgb_started and not self.rgb and not self.other and self.counter_decided:
                    # Remaining consumers are CPU-only; release this GPU/process immediately.
                    self.ready.remove(gpu); self.stopped_gpus.add(gpu); self.commands[gpu].put(dict(kind='STOP'))
            if self.rgb_started and not self.running and not self.rgb and not self.pending: break
            try: event=self.events.get(timeout=2)
            except Empty:
                for gpu,proc in self.workers.items():
                    if not proc.is_alive() and gpu not in self.stopped_gpus: raise RuntimeError(f'GPU worker {gpu} exited unexpectedly')
                if time.monotonic()-self.last_report>10: self.report()
                continue
            kind=event['kind']; gpu=event.get('gpu')
            if kind=='READY': self.ready.add(gpu)
            elif kind=='PACKET': self.collect_packet(event)
            elif kind in ('CPU','CPU_ERROR'): self.cpu_event(event)
            elif kind=='FATAL': raise RuntimeError(event['error']+'\n'+event['traceback'])
            elif kind in ('DONE','FAILED'):
                task=self.running.pop(gpu)
                print('M1_TASK_'+kind,gpu,task,flush=True)
                if kind=='FAILED':
                    self.failures.append(event)
                    if task['kind']=='TRAIN':
                        self.rows[task['job']]=dict(failed=True,reason=event['error'])
                        c.write(self.base/'primary'/f"{task['job']}.json",dict(job=task['job'],**self.rows[task['job']]))
                    if task['kind']=='RGB_FAULT':
                        # Failed case is explicit; release RAM only when all submitted consumers are done.
                        self.rgb_done[task['tile']]+=1; self.rgb_cpu_done[task['tile']]+=1
                    if task['kind']=='RGB_CLEAN': raise RuntimeError('fixed RGB reference could not be prepared')
                elif task['kind']=='TRAIN':
                    job=task['job']; self.train_done.add(job); self.known_jobs.append(job)
                    self.state['actual_new_updates']+=16000; self.append_diagnostics(job); self.retire_resume(job)
                self.report()
        return not self.failures

    def close(self,failed=False):
        for gpu,proc in self.workers.items():
            if proc.is_alive():
                if failed: proc.terminate()
                else: self.commands[gpu].put(dict(kind='STOP'))
        for proc in self.workers.values():
            proc.join(timeout=30)
            if proc.is_alive(): proc.terminate(); proc.join(timeout=10)
            if proc.is_alive(): proc.kill(); proc.join(timeout=10)
        if any(p.is_alive() for p in self.workers.values()):
            c.write(self.base/'cleanup_blocked_live_worker.json',dict(pids=[p.pid for p in self.workers.values() if p.is_alive()],observed_at=c.now()))
            raise RuntimeError('owned worker still alive; preserve caches and recovery state')
        self.cpu.shutdown(wait=True,cancel_futures=failed)
        for item in self.ephemeral.values(): item['packet'].close()
        self.ephemeral.clear()
        # All workers and CPU consumers are gone, including failed/interrupted paths.
        for z in self.cache.values(): z['users']=0
        self.retire_ram(force=True)
        c.write(self.base/'ram_retirement.json',dict(all_owned_gpu_workers_exited=all(not p.is_alive() for p in self.workers.values()),
            all_cpu_consumers_exited=True,memfd_packets_remaining=0,pixel_array_disk_cache=False,observed_at=c.now()))
        for q in [self.events,*self.commands.values(),*self.acks.values()]: q.cancel_join_thread(); q.close()

def main(base):
    base=Path(base).resolve(); base.relative_to(Path('/home/jovyan/zzx').resolve())
    import fcntl
    with (base/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if c.read(base/'queue_status.json')['status']!='REGISTERED': raise RuntimeError('no automatic queue restart')
        controller=None; failed=True
        def stopped(signum,frame): raise InterruptedError('external stop '+str(signum))
        signal.signal(signal.SIGTERM,stopped); signal.signal(signal.SIGINT,stopped)
        try:
            from phase3_m1_data import prepare
            c.verify(base); c.write(base/'queue_status.json',dict(status='PREPARING_INPUTS',observed_at=c.now()))
            print('PHASE3_M1_PREPARING_SHARED_INPUTS',base,flush=True)
            pf=prepare(base); controller=Controller(base,pf); success=controller.run()
            from phase3_m1_numeric import summary
            summary(base)
            controller.close(False); controller=None
            from verify_phase3_m1 import verify_results
            verification=verify_results(base)
            success=success and verification['all_required_evidence_complete']
            summary(base)  # Include verified legacy-anchor qualification, not a guessed causal pairing.
            c.retire(base,base/'cache','all GPU workers exited; compiler/runtime caches have no remaining consumer')
            c.retire(base,base/'temporary','all CPU/GPU consumers exited')
            c.DATA.clear(); c.STATS.clear()
            c.write(base/'queue_status.json',dict(status='COMPLETE_AWAITING_REVIEW' if success else 'FINISHED_WITH_FAILURES',observed_at=c.now(),new_updates=c.read(base/'summary.json')['completed_new_updates']))
            failed=False; print('PHASE3_M1_FINISHED',base,flush=True)
        except BaseException as exc:
            c.write(base/'technical_failure.json',dict(error=str(exc),traceback=traceback.format_exc(),automatic_retry=False,observed_at=c.now()))
            raise
        finally:
            if controller is not None: controller.close(failed)
            if failed:
                for name in ('cache','temporary'):
                    try: c.retire(base,base/name,'all owned processes exited after failure; logs and rolling job recovery state retained')
                    except BaseException as exc: c.write(base/('cleanup_failure_'+name+'.json'),dict(error=str(exc)))
                c.write(base/'queue_status.json',dict(status='FAILED_OR_INTERRUPTED_NO_RETRY',observed_at=c.now()))
            c.DATA.clear(); c.STATS.clear()

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--directory',type=Path,required=True); main(p.parse_args().directory)

