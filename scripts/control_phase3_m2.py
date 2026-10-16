"""Shared two-GPU ready queue, bounded memfd evaluation, 32-process counters."""
import argparse
import gc
import gzip
import json
import multiprocessing as mp
import os
import queue
import sys
import time
import traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import phase3_m2_common as c
from phase3_m2_counts import count_task,primary_task,mask_task,mask_design_task
from phase3_m2_analysis import Sink,finalize

class Evaluation:
    """One outer tile resident; 21 DSM logits, 3 clean RGB, <=2 fault RGB."""
    def __init__(self,base,fold,jobs,submit):
        from phase24_ipc import Packet
        self.base,self.fold,self.submit=Path(base),fold,submit
        self.jobs=jobs; self.tiles=list(c.read(self.base/'folds.json')['folds'][fold]['evaluation'])
        self.todo=[]; self.packet={};self.masks={};self.live={};self.counts=0;self.pending_masks=0
        self.done=False;self.Packet=Packet;self.tile=None;self.stage=None;self.start_tile()
    def start_tile(self):
        from scipy.ndimage import maximum_filter
        self.tile=self.tiles.pop(0);self.stage='clean';self.variant=[];self.todo=[];self.packet={};self.masks={};self.live={};self.counts=0
        shape=c.DATA[self.tile]['full'].shape;z=np.zeros(shape,bool);o=np.ones(shape,bool)
        self.zero=self.Packet.create(dict(mask=z,healthy=o));self.whole=self.Packet.create(dict(mask=o,healthy=z))
        self.pending_masks=5
        for i in range(1,6):self.submit(mask_task,dict(tile=self.tile,realization=i,base=str(self.base)))
        selected=[j for j in self.jobs if j['fold']==self.fold and j['role'] in ['rgb_reference','dsm_student']]
        for j in selected:self.todo.append(self.task(j,'clean'))
        self.clean_submitted=False;self.protect_index=0
    def task(self,job,condition,family='none',realization=0):
        tid=f"E_{self.tile}_{job['id']}_{condition}_{family}_{realization}"
        return dict(kind='INFER',task_id=tid,job=job,tile=self.tile,condition=condition,family=family,realization=realization)
    def clean_rgb(self):return [j for j in self.jobs if j['fold']==self.fold and j['role']=='rgb_reference']
    def dsm(self):return [j for j in self.jobs if j['fold']==self.fold and j['role']=='dsm_student']
    def metadata(self,rjob,djob,condition,family,realization):
        return dict(tile=self.tile,fold=self.fold,rseed=rjob['seed'],dseed=djob['seed'],arm=djob['arm'],condition=condition,family=family,realization=realization)
    def count(self,rpacket,dpacket,mask,rjob,djob,condition,family,realization,lease=None):
        self.counts+=1
        task=dict(r=rpacket.descriptor(),d=dpacket.descriptor(),mask=mask.descriptor(),tile=self.tile,border=8 if condition=='dsm_shift8' else 0,
            metadata=self.metadata(rjob,djob,condition,family,realization))
        self.submit(count_task,task,dict(session=self,lease=lease))
    def receive_prediction(self,meta,packet):
        byid={j['id']:j for j in self.jobs};job=byid[meta['job']]
        if meta['condition']=='clean':self.packet[job['id']]=packet
        elif job['modality']=='rgb':
            lease=meta['task_id'];self.live[lease].update(packet=packet,remaining=21)
            for djob in self.dsm():self.count(packet,self.packet[djob['id']],self.masks[(meta['family'],meta['realization'])],job,djob,meta['condition'],meta['family'],meta['realization'],lease)
        else:
            lease=meta['task_id'];self.live[lease]=dict(packet=packet,remaining=3)
            for rjob in self.clean_rgb():self.count(self.packet[rjob['id']],packet,self.whole,rjob,job,meta['condition'],'none',0,lease)
        self.advance()
    def receive_masks(self,result):
        for family in c.FAMILIES:
            self.masks[(family,result['realization'])]=self.Packet.receive(result['packets'][family])
        c.write(self.base/'mask_design'/f"{self.tile}_{result['realization']}.json",dict(tile=self.tile,realization=result['realization'],metadata=result['metadata']))
        self.pending_masks-=1;self.advance()
    def count_finished(self,lease):
        self.counts-=1
        if lease is not None:
            self.live[lease]['remaining']-=1
            if not self.live[lease]['remaining']:
                self.live[lease]['packet'].close();del self.live[lease]
        self.advance()
    def advance(self):
        if self.done:return
        if self.stage=='clean' and len(self.packet)==24 and not self.pending_masks and not self.clean_submitted:
            self.clean_submitted=True
            for rjob in self.clean_rgb():
                for djob in self.dsm():self.count(self.packet[rjob['id']],self.packet[djob['id']],self.zero,rjob,djob,'clean','none',0)
            self.variant=[self.task(rjob,condition,family,i) for rjob in self.clean_rgb()
                for condition in c.RGB_CONDITIONS[1:] for family in c.FAMILIES for i in range(1,6)]
            self.stage='rgb_fault'
        if self.stage=='rgb_fault' and not self.variant and not self.live and not self.counts and not self.todo:
            for djob in self.dsm():self.packet.pop(djob['id']).close()
            for p in self.masks.values():p.close()
            self.masks.clear();self.stage='dsm_fault'
            self.todo=[self.task(j,cond) for cond in ['dsm_down4','dsm_shift8'] for j in self.dsm()]
        if self.stage=='dsm_fault' and not self.todo and not self.live and not self.counts:
            # A task dispatched but not yet delivered also has an explicit lease.
            for p in self.packet.values():p.close()
            self.packet.clear();self.zero.close();self.whole.close()
            if self.tiles:self.start_tile()
            else:self.done=True;self.stage='done'
    def next_task(self,cpu_pending):
        if self.done:return None
        if self.stage=='rgb_fault':
            if self.variant and len(self.live)<2 and cpu_pending<96:
                task=self.variant.pop(0);task['mask_packet']=self.masks[(task['family'],task['realization'])].descriptor()
                self.live[task['task_id']]=dict(packet=None,remaining=None)
                return task
            return None
        if self.todo:
            if self.stage=='dsm_fault' and len(self.live)>=4:return None
            task=self.todo.pop(0)
            if self.stage=='dsm_fault':self.live[task['task_id']]=dict(packet=None,remaining=None)
            return task
        return None
    def close(self):
        for p in self.packet.values():p.close()
        for p in self.masks.values():p.close()
        for row in self.live.values():
            if row.get('packet'):row['packet'].close()
        if self.zero.fd is not None:self.zero.close()
        if self.whole.fd is not None:self.whole.close()

def run(base):
    import fcntl
    base=Path(base).resolve();lock=(base/'controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    plan=c.verify(base);inventory=c.gpu_inventory();c.write(base/'gpu_inventory_launch.json',inventory)
    if not inventory['ready']:c.write(base/'queue_status.json',dict(status='GPU_BUSY_NOT_STARTED',observed_at=c.now()));return
    # Parent remains CPU-only. Limit CPU numerical libraries before forking.
    os.environ.update(c.environment(base));import torch;torch.set_num_threads(1)
    from phase3_m2_data import prepare
    from phase3_m2_runtime import worker
    from phase24_ipc import Packet,ensure_abstract_resource_sharer
    pf=prepare(base);folds=c.read(base/'folds.json');jobs=c.jobs(folds);ctx=mp.get_context('fork')
    fresh=c.gpu_inventory();c.write(base/'gpu_inventory_before_workers.json',fresh)
    if not fresh['ready'] or any(fresh['selected'][g][1]!=inventory['selected'][g][1] for g in [0,1]):
        c.write(base/'queue_status.json',dict(status='GPU_BECAME_BUSY_NOT_TRAINED',observed_at=c.now()));return
    events=ctx.Queue();tasks={g:ctx.Queue() for g in [0,1]};acks={g:ctx.Queue() for g in [0,1]}
    workers={g:ctx.Process(target=worker,args=(str(base),g,inventory['selected'][g][1],tasks[g],events,acks[g])) for g in [0,1]}
    # Fork GPU workers before pool management threads start. CUDA is initialized
    # only in these children; CPU pool inherits read-only inputs via COW.
    for w in workers.values():w.start()
    pool=ctx.Pool(pf['count_workers']);received=queue.Queue();pending=0;failure=[]
    original_cpu_pids={p.pid for p in pool._pool}
    sink=Sink(base);idle=set();active={};completed=set();failed=set();evaluated=set();session=None;held={};last=0.;retired=set()
    def submit(function,task,context=None):
        nonlocal pending
        pending+=1
        pool.apply_async(function,(task,),callback=lambda value:received.put((True,value,context)),error_callback=lambda error:received.put((False,str(error),context)))
    # Use the otherwise idle early CPU phase to validate ALL outcome-blind mask
    # designs. Save only compact primitives/seeds; later reconstruction avoids
    # repeating expensive matching, without holding all 12 tiles' masks in RAM.
    mask_queue=[dict(tile=tile,realization=i) for tile in c.FIT for i in range(1,6)]
    mask_design_inflight=min(8,pf['count_workers'])
    for _ in range(mask_design_inflight):submit(mask_design_task,mask_queue.pop(0))
    try:
        while True:
            # Drain bounded CPU results before granting more prediction leases.
            for _ in range(32):
                try:ok,value,context=received.get_nowait()
                except queue.Empty:break
                pending-=1
                if not ok:raise RuntimeError('CPU task failed without retry: '+value)
                if value['kind']=='mask_design':
                    c.write(base/'mask_design'/f"{value['tile']}_{value['realization']}.json",{k:v for k,v in value.items() if k!='kind'})
                    mask_design_inflight-=1
                    if mask_queue:submit(mask_design_task,mask_queue.pop(0));mask_design_inflight+=1
                elif value['kind']=='masks':session.receive_masks(value)
                elif value['kind']=='trajectory':
                    sink.accept(value);held.pop(context['held']).close()
                else:
                    sink.accept(value);context['session'].count_finished(context['lease'])
            if session and session.done:
                evaluated.add(session.fold);session.close();session=None;gc.collect()
            if session is None:
                for fold in ['F0','F1','F2']:
                    ids={j['id'] for j in jobs if j['fold']==fold}
                    mask_ready=not mask_queue and not mask_design_inflight and all((base/'mask_design'/f'{t}_{i}.json').exists() for t in folds['folds'][fold]['evaluation'] for i in range(1,6))
                    if fold not in evaluated and ids<=completed and mask_ready:
                        session=Evaluation(base,fold,jobs,submit);break
                    if ids&failed:evaluated.add(fold)
            ready=[j for j in jobs if j['id'] not in completed|failed and j['id'] not in [a.get('job',{}).get('id') for a in active.values() if a['kind']=='TRAIN'] and set(j['depends_on'])<=completed]
            # Fixed within-cell random ordering prevents a method/card affinity;
            # R/teachers are prioritized to make each OOF cell usable early.
            ready.sort(key=lambda j:(int(j['fold'][1:]),c.SEEDS.index(j['seed']),
                0 if j['role'] in ['rgb_reference','rgb_oof_teacher'] else 1,c.key(20261015,j['id'])))
            for jobid in completed-retired:
                if len(sink.trajectory_by_job.get(jobid,set()))==16:
                    rolling=c.scoped(base/'jobs'/jobid/'last_resume.pth',base)
                    if rolling.exists():
                        st=rolling.stat();receipt=dict(path=str(rolling.relative_to(base)),bytes=st.st_size,
                            endpoint_sha256=c.read(rolling.parent/'complete.json')['checkpoint_sha256'],
                            reason='successful 32k endpoint and all four trajectory ages counted; no remaining recovery consumer',observed_at=c.now())
                        c.write(base/'retirement'/(jobid+'.json'),dict(status='PREPARED',**receipt));rolling.unlink()
                        c.write(base/'retirement'/(jobid+'.json'),dict(status='RETIRED',**receipt))
                    retired.add(jobid)
            for job in jobs:
                if set(job['depends_on'])&failed and job['id'] not in completed|failed:
                    failed.add(job['id']);c.write(base/'skipped'/(job['id']+'.json'),dict(reason='failed dependency',automatic_retry=False))
            for gpu in list(sorted(idle)):
                task=session.next_task(pending) if session else None
                if task is None and ready:
                    job=ready.pop(0);task=dict(kind='TRAIN',job=job,task_id='T_'+job['id'])
                if task:
                    active[gpu]=task;idle.remove(gpu);tasks[gpu].put(task)
            if len(completed|failed)==108 and len(evaluated)==3 and not active and not pending:break
            try:event=events.get(timeout=.2)
            except queue.Empty:event=None
            if event:
                kind=event['kind'];gpu=event['gpu']
                if kind=='READY':idle.add(gpu)
                elif kind=='PACKET':
                    packet=Packet.receive(event['packet']);meta=event['metadata'];acks[gpu].put(dict(received=True))
                    if meta['kind']=='trajectory':
                        name=f"{meta['job']}_{meta['step']}_{meta['tile']}";held[name]=packet
                        submit(primary_task,dict(packet=packet.descriptor(),metadata=meta),dict(held=name))
                    else:session.receive_prediction(meta,packet)
                elif kind in ['DONE','FAILED']:
                    task=active.pop(gpu);idle.add(gpu)
                    if kind=='FAILED':
                        failure.append(dict(task=event['task_id'],error=event['error']))
                        if task['kind']=='TRAIN':failed.add(task['job']['id'])
                        else:raise RuntimeError('evaluation failed; preserve partial output, no retry')
                    elif task['kind']=='TRAIN':completed.add(task['job']['id'])
                elif kind=='WORKER_FAILED':raise RuntimeError(event['error'])
                elif kind=='EXIT' and len(completed|failed)<108:raise RuntimeError('GPU worker exited early')
            for gpu,w in workers.items():
                if w.exitcode is not None and (gpu in active or len(completed|failed)<108):raise RuntimeError('GPU worker died: '+str(gpu))
            if {p.pid for p in pool._pool}!=original_cpu_pids:raise RuntimeError('CPU worker died/replaced; no task retry or indefinite wait')
            if time.monotonic()-last>15:
                c.write(base/'queue_status.json',dict(status='RUNNING',completed_trainings=len(completed),failed_or_blocked=len(failed),
                    active={str(g):t['task_id'] for g,t in active.items()},cpu_tasks=pending,counted_cases=len(sink.cases),
                    evaluation=None if session is None else dict(fold=session.fold,tile=session.tile,stage=session.stage,live_variants=len(session.live)),
                    count_workers=pf['count_workers'],observed_at=c.now()));last=time.monotonic()
        for gpu in workers:tasks[gpu].put(dict(kind='STOP'))
        for w in workers.values():w.join()
        pool.close();pool.join();sink.close()
        summary=finalize(base,sink,failure)
        c.write(base/'queue_status.json',dict(status=summary['status'],observed_at=c.now(),publication=str(base/'publication')))
        c.write(base/'ram_retirement.json',dict(all_owned_gpu_workers_exited=all(w.exitcode==0 for w in workers.values()),all_cpu_consumers_exited=True,
            anonymous_packets_remaining=0,source_files_deleted=False,observed_at=c.now()))
        print('M2_FINISHED',summary['status'],summary['gates'],flush=True)
        # Upload is a separate process using existing credentials only. Failure
        # leaves a ready publication directory and never re-enters computation.
        import subprocess
        subprocess.run([sys.executable,'-B',str(base/'code/scripts/upload_phase3_m2.py'),'--directory',str(base)],check=False)
    except BaseException as exc:
        c.write(base/'controller_failure.json',dict(error=str(exc),traceback=traceback.format_exc(),automatic_retry=False,observed_at=c.now()))
        c.write(base/'queue_status.json',dict(status='FAILED_NO_RETRY',error=str(exc),observed_at=c.now()))
        # Signal only children created and owned by this controller. Never find
        # or terminate processes by name, and never touch another tmux/session.
        for w in workers.values():
            if w.is_alive():w.terminate()
        for w in workers.values():w.join()
        pool.terminate();pool.join();sink.close()
        for packet in held.values():packet.close()
        if session:session.close()
        raise
    finally:
        c.DATA.clear();gc.collect();lock.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);run(p.parse_args().directory)
