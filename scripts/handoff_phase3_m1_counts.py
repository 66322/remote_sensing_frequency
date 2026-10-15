"""Explicit count-only handoff. Preserve original run binding, weights and completed evidence."""
import argparse
import gc
import hashlib
import importlib.util
import json
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import time
import traceback
import multiprocessing as mp
from collections import deque
from pathlib import Path

RUN='research_phase3_m1_recovery_20261015T164357_19327'
BINDING={'plan.json':'3bf0d81cadcaeb75e0b14c9c24cdeecabe87bad6e190513d1d3799c4876fc5b0',
         'code_manifest.json':'c2c4dab784d1a14719910fcc162672a557c6a77bbb0c2fa9b98d4865f136a02a'}
PROBE_COMMIT='4bb62d31c9bd45729855155e7889ff59567c8bf0'
PROBE_SHA='762b2769c2d0d6c6fcf9d44e0cae848ac8fb5eedca89b07ff5e90510c677f751'

def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024**2),b''): h.update(chunk)
    return h.hexdigest()
def write(p,z):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); tmp=p.with_name(p.name+'.tmp.'+str(os.getpid()))
    tmp.write_text(json.dumps(z,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n',encoding='utf-8'); os.replace(tmp,p)
def cases(tiles):
    return [dict(kind='RGB_FAULT',tile=t,family=f,realization=i,damage=damage)
            for t in tiles for f in ('pixel','random','gradient','matched') for i in range(1,21) for damage in ('zero','down4')]
def case_id(task): return f"RGB_FAULT_{task['tile']}_{task['family']}_{task['realization']}_{task['damage']}"
def result_path(base,job,task): return Path(base)/'results'/job/(case_id(task)+'.json')

def scan_cases(base,c,models,case_list):
    todo=[]; complete={t:0 for t in c.VAL}; retained={}; calibration=None
    for task in case_list:
        missing=[]
        for job in models:
            p=result_path(base,job,task)
            if not p.exists(): missing.append(job); continue
            z=read(p)
            if z.get('binding')!=c.binding(base) or z.get('case')!=task or z.get('job')!=job:
                raise RuntimeError('existing case identity differs: '+str(p))
            if set(z.get('counts',{}))!={'full','noboundary'}: raise RuntimeError('incomplete existing count record '+str(p))
            for scope in ('full','noboundary'):
                if set(z['counts'][scope])!={'all','healthy','damaged'}: raise RuntimeError('incomplete ROI record')
                for stats in z['counts'][scope].values():
                    if set(stats)!={'dsm','logit_mix','probability_mix'}: raise RuntimeError('incomplete system record')
            retained[p.relative_to(base).as_posix()]=sha(p)
        if missing: todo.append(dict(task=task,models=missing))
        else: complete[task['tile']]+=1
    remaining_tiles={row['task']['tile'] for row in todo}
    for task in case_list:
        if task['tile'] not in remaining_tiles: continue
        for job in models:
            p=result_path(base,job,task)
            if p.exists():
                calibration=dict(task=task,job=job,path=p.relative_to(base).as_posix(),sha256=sha(p)); break
        if calibration: break
    return dict(todo=todo,complete=complete,retained_files=retained,calibration=calibration)

def preserve_check(base,files):
    for name,h in files.items():
        if sha(Path(base)/name)!=h: raise RuntimeError('preserved evidence changed: '+name)

def reset_child_signals():
    signal.signal(signal.SIGTERM,signal.SIG_DFL); signal.signal(signal.SIGINT,signal.SIG_IGN)

def cpu_worker(base,index,commands,events):
    reset_child_signals()
    if hasattr(os,'setsid'): os.setsid()
    import phase3_m1_common as c
    from phase24_ipc import Packet
    from phase3_m1_numeric import analyze
    # Only immutable labels are required in CPU children, not RGB/raw-height arrays.
    for tile in list(c.DATA): c.DATA[tile]={k:v for k,v in c.DATA[tile].items() if k in ('full_gt','noboundary_gt')}
    events.put(dict(kind='CPU_READY',cpu=index))
    while True:
        row=commands.get()
        if row['kind']=='STOP': break
        rp=dp=None
        try:
            if row['kind']!='COUNT': raise RuntimeError('CPU executor only accepts counts, never training')
            rp=Packet.receive(row['rgb']); dp=Packet.receive(row['dsm'])
            counts=analyze(rp.arrays['score'],dp.arrays['score'],row['task']['tile'],
                           rp.arrays['mask'],0,'both',rp.arrays['healthy'])
            rp.close(); dp.close(); rp=dp=None
            events.put(dict(kind='CPU_DONE',cpu=index,cid=row['cid'],job=row['job'],counts=counts))
        except BaseException as exc:
            events.put(dict(kind='CPU_FAILED',cpu=index,cid=row.get('cid'),job=row.get('job'),error=str(exc),traceback=traceback.format_exc()))
        finally:
            if rp is not None: rp.close()
            if dp is not None: dp.close()
    events.put(dict(kind='CPU_EXIT',cpu=index))

def gpu_worker(*args):
    reset_child_signals()
    from phase3_m1_runtime import worker
    worker(*args)

def transport_smoke():
    """Target Linux two-process FD transport and original integer count equality, before stopping old executor."""
    import numpy as np
    import phase3_m1_common as c
    from phase24_ipc import Packet
    from phase3_m1_numeric import analyze
    tile='__count_handoff_smoke__'; gt=(np.arange(19*23).reshape(19,23)%6).astype('uint8')
    score=np.zeros((6,19,23),np.float32)
    for i in range(6): score[i][gt==i]=2
    mask=gt%3==0; healthy=~mask
    c.DATA[tile]=dict(full_gt=gt,noboundary_gt=gt)
    expected=analyze(score,score,tile,mask,healthy_override=healthy)
    ctx=mp.get_context('fork'); commands=ctx.Queue(); events=ctx.Queue()
    workers=[ctx.Process(target=cpu_worker,args=('',i,commands,events)) for i in range(2)]
    rp=dp=None
    try:
        for p in workers: p.start()
        rp=Packet.create(dict(score=score,mask=mask,healthy=healthy)); dp=Packet.create(dict(score=score))
        for i in range(2): commands.put(dict(kind='COUNT',cid='smoke'+str(i),job='smoke',task=dict(tile=tile),rgb=rp.descriptor(),dsm=dp.descriptor()))
        done=0
        while done<2:
            event=events.get(timeout=60)
            if event['kind']=='CPU_FAILED': raise RuntimeError(event['traceback'])
            if event['kind']=='CPU_DONE':
                if event['counts']!=expected: raise RuntimeError('FD/process counter smoke differs')
                done+=1
        for p in workers: commands.put(dict(kind='STOP'))
        for p in workers:
            p.join(timeout=10)
            if p.is_alive(): raise RuntimeError('smoke worker did not exit')
    finally:
        for p in workers:
            if p.pid is not None and p.is_alive(): p.terminate(); p.join(timeout=5)
        if rp is not None: rp.close()
        if dp is not None: dp.close()
        commands.cancel_join_thread(); events.cancel_join_thread(); commands.close(); events.close(); c.DATA.pop(tile,None)

def process_identity(pid):
    p=Path('/proc')/str(pid)
    try:
        cmd=(p/'cmdline').read_bytes().split(b'\0'); stat=(p/'stat').read_text().rsplit(')',1)[1].split()
        if not any(cmd): return None
        return dict(cmd=cmd,start=int(stat[19]),ppid=int(stat[1]))
    except (FileNotFoundError,ProcessLookupError): return None

def validate_old_identity(base,identity):
    return bool(identity and str(Path(base)/'code/scripts/control_phase3_m1.py').encode() in identity['cmd']
                and str(base).encode() in identity['cmd'] and b'--directory' in identity['cmd'])

def signal_identified_controller(base,pid,expected):
    if not validate_old_identity(base,expected) or process_identity(pid)!=expected:
        raise RuntimeError('controller identity changed; no signal sent')
    if hasattr(os,'pidfd_open') and hasattr(signal,'pidfd_send_signal'):
        fd=os.pidfd_open(pid)
        try:
            if process_identity(pid)!=expected: raise RuntimeError('PID changed after pidfd open; no signal sent')
            signal.pidfd_send_signal(fd,signal.SIGTERM)
        finally: os.close(fd)
    else:
        # Require pidfd rather than risk a PID reuse window on a shared root account.
        raise RuntimeError('safe pidfd signalling unavailable; original executor left running')

def gpu_inventory(allowed=()):
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
    selected={int(x.split(',')[0]):[y.strip() for y in x.split(',')] for x in gpu.splitlines() if int(x.split(',')[0]) in (0,1)}
    apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader,nounits'],text=True)
    uuids={x[1] for x in selected.values()}; other=[]
    for line in apps.splitlines():
        cols=[x.strip() for x in line.split(',')]
        if len(cols)==2 and cols[1] in uuids and int(cols[0]) not in allowed: other.append(line)
    if set(selected)!={0,1} or any(float(x[-1])<40000 for x in selected.values()) or other:
        raise RuntimeError('GPU0/1 occupied by another task or insufficient free memory; no other process touched')
    return dict(gpus=gpu,apps=apps)

def attach_resource_probe(base,code):
    source=Path(base).parent/f'phase3_m1_cpu_process_probe_{PROBE_COMMIT}.py'
    dest=Path(code)/'resource_probe.py'
    if not dest.exists():
        if not source.exists() or sha(source)!=PROBE_SHA: raise RuntimeError('verified resource probe missing; original executor left running')
        shutil.copyfile(source,dest)
    if sha(dest)!=PROBE_SHA: raise RuntimeError('resource probe changed')
    spec=importlib.util.spec_from_file_location('_count_handoff_resources',dest); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def verify_static(base,c,models):
    c.verify(base)
    if c.binding(base)!=BINDING: raise RuntimeError('identified run binding differs')
    prepared=read(Path(base)/'prepared.json')
    if prepared['binding']!=c.binding(base) or prepared['stats_sha256']!=sha(Path(base)/'height_statistics.json') or prepared['source_sha256']!=sha(Path(base)/'source_bindings.json'):
        raise RuntimeError('original prepared metadata changed; old executor left running')
    source=read(Path(base)/'source_bindings.json')
    for row in source['weights'].values():
        if sha(row['path'])!=row['sha256']: raise RuntimeError('historical reference endpoint changed')
    if sha(source['pretrained']['path'])!=source['pretrained']['sha256']: raise RuntimeError('pretrained identity changed')
    rows={}
    for job in models:
        if job!='M00_42':
            folder=Path(base)/'jobs'/job; done=read(folder/'complete.json')
            if not c.job_binding_ok(base,job,done) or done['optimizer_updates']!=16000 or sha(folder/'endpoint.pth')!=done['checkpoint_sha256']:
                raise RuntimeError('completed training identity differs '+job)
        rows[job]=read(Path(base)/'primary'/(job+'.json'))
        for tile in c.VAL:
            for availability in ('both','rgb_missing','dsm_missing'):
                if not (Path(base)/'clean'/f'{job}_{tile}_{availability}.json').exists(): raise RuntimeError('static clean evidence missing')
            if not (Path(base)/'scale'/f'{job}_{tile}.json').exists(): raise RuntimeError('static scale evidence missing')
            for damage in ('down4','shift8'):
                if not (Path(base)/'results'/job/f'DSM_FAULT_{tile}_global_0_{damage}.json').exists(): raise RuntimeError('DSM fault evidence missing')
    gate=c.gate(rows)
    if not gate or gate['accepted'] or read(Path(base)/'analysis/amplitude_gate.json')!=dict(gate,binding=c.binding(base)):
        raise RuntimeError('expected unchanged failed amplitude gate, no new training permitted')

def prepare_remaining_inputs(base,c,todo,calibration):
    import io
    import numpy as np
    from PIL import Image
    from prepare_phase24 import source_guard
    from phase24_common import scoped,identity
    old=Path(read(Path(base)/'plan.json')['previous']); source_guard(old)
    prepared=read(Path(base)/'prepared.json')
    if prepared['binding']!=c.binding(base) or prepared['stats_sha256']!=sha(Path(base)/'height_statistics.json') or prepared['source_sha256']!=sha(Path(base)/'source_bindings.json'):
        raise RuntimeError('original prepared input/statistics binding differs')
    c.STATS.clear(); c.STATS.update(read(Path(base)/'height_statistics.json')['values']); c.DATA.clear()
    m=read(old/'input_manifest.json'); tiles={row['task']['tile'] for row in todo}
    if calibration: tiles.add(calibration['task']['tile'])
    audit={}
    for tile in sorted(tiles):
        if tile not in c.VAL: raise RuntimeError('count-only restart cannot load Fit/Test/heldout tiles')
        fields={}
        for name in ('optical','rgb_down4','full_gt','noboundary_gt'):
            row=m['arrays'][tile][name]; f=scoped(row['path'],old/'inputs'); before=identity(f); raw=f.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=row['sha256'] or identity(f)!=before: raise RuntimeError('remaining input changed '+str(f))
            a=np.load(io.BytesIO(raw),allow_pickle=False)
            if list(a.shape)!=row['shape'] or str(a.dtype)!=row['dtype']: raise RuntimeError('remaining input schema differs')
            a.flags.writeable=False; fields[name]=a; audit[str(f)]=row['sha256']
        f=scoped(m['normalization'][tile]['source_path'],'/home/jovyan/zzx'); before=identity(f)
        row=m['source_files'][str(f)]; h=sha(f)
        if h!=row.get('current_sha256',row.get('sha256')): raise RuntimeError('raw DSM changed')
        with Image.open(f) as im:
            if im.mode!='F': raise RuntimeError('raw DSM type differs')
            a=np.array(im,dtype=np.float32)
        if identity(f)!=before or not np.isfinite(a).all(): raise RuntimeError('raw DSM invalid')
        a.flags.writeable=False; fields['height']=a; c.DATA[tile]=fields; audit[str(f)]=h
        print('COUNT_INPUT_VERIFIED',tile,flush=True)
    masks=read(old/'mask_manifest.json'); seen=set()
    for task in [row['task'] for row in todo]+([calibration['task']] if calibration else []):
        row=masks['tiles'][task['tile']][str(task['realization'])][task['family']]['25']; f=scoped(row['path'],read(Path(base)/'plan.json')['root'])
        if str(f) not in seen:
            if sha(f)!=row['sha256']: raise RuntimeError('remaining mask changed')
            seen.add(str(f)); audit[str(f)]=row['sha256']
    write(Path(base)/'analysis/count_engine_input_audit.json',dict(binding=c.binding(base),files=audit,fit_loaded=False,sealed_loaded=False))

class Engine:
    def __init__(self,base,c,models,inventory,registration,workers=32,capacity=8):
        self.base=Path(base); self.c=c; self.models=models; self.inventory=inventory; self.registration=registration
        self.ctx=mp.get_context('fork'); self.events=self.ctx.Queue(); self.cpuq=self.ctx.Queue()
        self.commands={g:self.ctx.Queue() for g in (0,1)}; self.acks={g:self.ctx.Queue() for g in (0,1)}
        self.cpus={}; self.gpus={}; self.ready=set(); self.running={}; self.stopped_gpus=set()
        self.clean={}; self.live={}; self.pending=0; self.failed=[]; self.cpu_ready=set(); self.workers=workers; self.capacity=capacity
        self.done=dict(inventory['complete']); self.gpu_done=dict(self.done); self.new_files=0; self.last_report=0
        self.reg_sha=sha(self.base/'count_engine_registration.json') if (self.base/'count_engine_registration.json').exists() else 'test'
        self.calibrated=False

    def start(self):
        # Fork all CPU/GPU processes before the parent sends queue data/starts FD-sharer threads.
        for i in range(self.workers):
            p=self.ctx.Process(target=cpu_worker,args=(str(self.base),i,self.cpuq,self.events)); self.cpus[i]=p; p.start()
        for g in (0,1):
            p=self.ctx.Process(target=gpu_worker,args=(str(self.base),g,self.commands[g],self.events,self.acks[g])); self.gpus[g]=p; p.start()
        self.report('REBUILDING_REMAINING_TILE_PREDICTIONS')

    def report(self,status='RUNNING'):
        z=dict(status=status,observed_at=self.c.now(),actual_new_updates=176000,pending_training=0,pending_other=0,
            completed_training_jobs=[x['job'] for x in self.c.job_list()],failed_tasks=len(self.failed),
            workers={str(g):dict(pid=p.pid,status='STOPPED' if g in self.stopped_gpus else self.running.get(g,{}).get('kind','READY')) for g,p in self.gpus.items()},
            cpu_processes={str(i):p.pid for i,p in self.cpus.items()},cpu_executor_processes=self.workers,
            count_algorithm='original_unmodified',count_engine_registration_sha256=self.reg_sha,
            pending_cpu=self.pending,ready_gpus=sorted(self.ready),running={str(g):t for g,t in self.running.items()},
            pending_rgb=self.remaining_queue,ephemeral_packets=len(self.live),retained_ram_bytes=sum(p.meta['bytes'] for p in self.clean.values()),
            rgb_cases_counted=self.done,rgb_cases_gpu_done=self.gpu_done,new_count_files=self.new_files)
        write(self.base/'queue_status.json',z); self.last_report=time.monotonic()

    @property
    def remaining_queue(self): return getattr(self,'_remaining',len(self.inventory['todo']))

    def event(self):
        from phase24_ipc import Packet
        try: e=self.events.get(timeout=2)
        except queue.Empty:
            for i,p in self.cpus.items():
                if not p.is_alive(): raise RuntimeError('owned CPU process exited unexpectedly '+str(i))
            for g,p in self.gpus.items():
                if g not in self.stopped_gpus and not p.is_alive(): raise RuntimeError('owned GPU process exited unexpectedly '+str(g))
            if time.monotonic()-self.last_report>10: self.report()
            return
        kind=e['kind']; g=e.get('gpu')
        if kind=='CPU_READY': self.cpu_ready.add(e['cpu'])
        elif kind=='CPU_EXIT': pass
        elif kind=='READY':
            if g not in self.stopped_gpus: self.ready.add(g)
        elif kind=='PACKET':
            p=Packet.receive(e['packet']); task=e['task']; self.acks[g].put(dict(accepted=True))
            if task['kind']=='INFER_CLEAN':
                key=(task['job'],task['tile'])
                if key in self.clean: p.close(); raise RuntimeError('duplicate rebuilt clean packet')
                self.clean[key]=p
            elif task['kind']=='RGB_FAULT':
                cid=case_id(task); item=self.live[cid]; item['packet']=p
                self.gpu_done[task['tile']]+=int(not item.get('calibration'))
                for job in item['models']:
                    self.cpuq.put(dict(kind='COUNT',cid=cid,job=job,task=task,rgb=p.descriptor(),dsm=self.clean[(job,task['tile'])].descriptor()))
                    self.pending+=1
            else: p.close(); raise RuntimeError('count-only executor received unexpected GPU task')
        elif kind=='DONE': self.running.pop(g)
        elif kind in ('FAILED','FATAL','CPU_FAILED'):
            self.failed.append(e); write(self.base/'failures'/('count_engine_'+str(len(self.failed))+'.json'),e)
            raise RuntimeError(e.get('traceback',e.get('error','count engine failed')))
        elif kind=='CPU_DONE':
            self.pending-=1; item=self.live[e['cid']]; task=item['task']
            if item.get('calibration'):
                source=self.inventory['calibration']; path=self.base/source['path']
                if sha(path)!=source['sha256'] or read(path)['counts']!=e['counts']: raise RuntimeError('full-size historical count replay differs')
                write(self.base/'analysis/count_engine_calibration.json',dict(exact=True,source=source,registration_sha256=self.reg_sha,observed_at=self.c.now()))
                self.calibrated=True; print('FULL_TILE_ORIGINAL_COUNTS_EXACT',source['path'],flush=True)
            else:
                if not self.calibrated: raise RuntimeError('cannot publish counts before historical replay passes')
                path=result_path(self.base,e['job'],task)
                if path.exists(): raise RuntimeError('refuse overwriting preserved case '+str(path))
                write(path,dict(case=task,job=e['job'],counts=e['counts'],binding=self.c.binding(self.base),
                               count_engine_registration_sha256=self.reg_sha)); self.new_files+=1
            item['left']-=1
            if item['left']==0:
                item['packet'].close(); del self.live[e['cid']]
                if not item.get('calibration'): self.done[task['tile']]+=1
                self.report()
        else: raise RuntimeError('unknown executor event '+str(kind))

    def send(self,g,task):
        self.ready.remove(g); self.running[g]=task; self.commands[g].put(task)

    def rebuild(self,tile):
        todo=deque(dict(kind='INFER_CLEAN',job=j,tile=tile) for j in self.models)
        while todo or self.running:
            for g in sorted(list(self.ready)):
                if todo: self.send(g,todo.popleft())
            self.event()
        if not all((j,tile) in self.clean for j in self.models): raise RuntimeError('incomplete clean rebuild')
        self.report()

    def count(self,rows,last_tile=False,calibration=False):
        todo=deque(rows)
        while todo or self.running or self.pending or self.live:
            self._remaining=len(todo)
            for g in sorted(list(self.ready)):
                if todo and len(self.live)<self.capacity:
                    row=todo.popleft(); task=row['task']; cid=case_id(task)
                    if cid in self.live: raise RuntimeError('duplicate live case')
                    self.live[cid]=dict(task=task,models=row['models'],left=len(row['models']),calibration=calibration)
                    self.send(g,task)
            if not todo and not self.running and last_tile:
                for g in sorted(list(self.ready)):
                    self.ready.remove(g); self.stopped_gpus.add(g); self.commands[g].put(dict(kind='STOP'))
            self.event()

    def run(self):
        tiles=sorted({r['task']['tile'] for r in self.inventory['todo']})
        for index,tile in enumerate(tiles):
            self.rebuild(tile)
            if not self.calibrated:
                source=self.inventory['calibration']
                if source['task']['tile']!=tile: raise RuntimeError('calibration tile must be first remaining tile')
                self.count([dict(task=source['task'],models=[source['job']])],calibration=True)
            rows=[r for r in self.inventory['todo'] if r['task']['tile']==tile]
            self.count(rows,last_tile=index==len(tiles)-1)
            freed=0
            for key,p in list(self.clean.items()):
                if key[1]==tile: freed+=p.meta['bytes']; p.close(); del self.clean[key]
            write(self.base/'retirement'/f'count_engine_ram_{tile}.json',dict(bytes=freed,all_consumers_finished=True,anonymous_memfd=True,observed_at=self.c.now()))
        return True

    def close(self,failed=False):
        procs=[p for p in [*self.cpus.values(),*self.gpus.values()] if p.pid is not None]
        if not failed:
            for _ in self.cpus: self.cpuq.put(dict(kind='STOP'))
            for g,p in self.gpus.items():
                if g not in self.stopped_gpus and p.is_alive(): self.commands[g].put(dict(kind='STOP'))
        else:
            for p in procs:
                if p.is_alive(): p.terminate()
        deadline=time.monotonic()+30
        for p in procs: p.join(timeout=max(0,deadline-time.monotonic()))
        for p in procs:
            if p.is_alive(): p.terminate(); p.join(timeout=5)
            if p.is_alive(): p.kill(); p.join(timeout=5)
        if any(p.is_alive() for p in procs): raise RuntimeError('owned executor child still live; do not clean caches')
        for item in self.live.values():
            if 'packet' in item: item['packet'].close()
        self.live.clear()
        for p in self.clean.values(): p.close()
        self.clean.clear()
        for q in [self.events,self.cpuq,*self.commands.values(),*self.acks.values()]: q.cancel_join_thread(); q.close()
        write(self.base/'count_engine_ram_retirement.json',dict(all_owned_processes_exited=True,anonymous_packets_remaining=0,observed_at=self.c.now()))

def execute(base,lock_fd):
    import phase3_m1_common as c
    reg=read(base/'count_engine_registration.json'); reg_hash=sha(base/'count_engine_registration.json'); code=Path(reg['code_directory'])
    held=os.fdopen(lock_fd,'a'); engine=None; failed=True
    def stopped(signum,frame): raise InterruptedError('count executor externally stopped '+str(signum))
    signal.signal(signal.SIGTERM,stopped); signal.signal(signal.SIGINT,stopped)
    try:
        for name,h in reg['files'].items():
            if sha(code/name)!=h: raise RuntimeError('count executor source changed')
        if c.binding(base)!=reg['original_binding']: raise RuntimeError('original binding changed')
        c.verify(base)
        if sha(base/reg['inventory_path'])!=reg['inventory_sha256']: raise RuntimeError('handoff inventory changed')
        inventory=read(base/reg['inventory_path']); models=reg['models']
        preserve_check(base,inventory['retained_files'])
        if sha(base/'count_engine_registration.json')!=reg_hash: raise RuntimeError('runtime registration changed')
        if inventory['todo']:
            prepare_remaining_inputs(base,c,inventory['todo'],inventory['calibration'])
            engine=Engine(base,c,models,inventory,reg); engine.start(); engine.run(); engine.close(); engine=None
        preserve_check(base,inventory['retained_files'])
        if sha(base/'count_engine_registration.json')!=reg_hash: raise RuntimeError('runtime registration changed after counting')
        from verify_phase3_m1 import verify_results
        from phase3_m1_numeric import summary
        verification=verify_results(base)
        verification['count_engine_upgrade']=dict(registration_sha256=sha(base/'count_engine_registration.json'),
            execution_commit=reg['commit'],preserved_existing_files=len(inventory['retained_files']),original_math=True,cpu_processes=32,
            full_tile_replay_exact=read(base/'analysis/count_engine_calibration.json')['exact'] if inventory['todo'] else None)
        write(base/'result_verification.json',verification)
        report=summary(base); report['count_engine_upgrade']=verification['count_engine_upgrade']; write(base/'summary.json',report)
        c.retire(base,base/'cache','all count executor CPU/GPU processes exited; runtime cache no remaining consumer')
        c.retire(base,base/'temporary','all count executor consumers exited')
        c.DATA.clear(); c.STATS.clear()
        state='COMPLETE_AWAITING_REVIEW' if verification['all_required_evidence_complete'] else 'FINISHED_WITH_FAILURES'
        write(base/'queue_status.json',dict(status=state,new_updates=176000,count_engine_commit=reg['commit'],observed_at=c.now()))
        failed=False; print('PHASE3_M1_COUNTS_FINISHED',state,base,flush=True)
    except BaseException as exc:
        write(base/'technical_failure.json',dict(error=str(exc),traceback=traceback.format_exc(),count_engine_commit=reg['commit'],automatic_retry=False,observed_at=c.now()))
        raise
    finally:
        if engine is not None: engine.close(failed=True)
        if failed:
            for name in ('cache','temporary'):
                try: c.retire(base,base/name,'owned count processes exited after failure; input/weights/count evidence retained')
                except BaseException as exc: write(base/('count_engine_cleanup_failure_'+name+'.json'),dict(error=str(exc)))
            c.DATA.clear(); c.STATS.clear()
            write(base/'queue_status.json',dict(status='FAILED_OR_INTERRUPTED_NO_RETRY',observed_at=c.now(),count_engine_commit=reg['commit']))
        held.close()

def launch(base,commit):
    import fcntl
    import phase3_m1_common as c
    base=Path(base); root=base.parent.parent
    with (base/'count_engine_handoff.lock').open('a') as switch_lock:
        fcntl.flock(switch_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        marker=base/'count_engine_request.json'
        if marker.exists():
            print('EXISTING_COUNT_HANDOFF_NO_DUPLICATE',read(marker),flush=True)
            print('CURRENT',read(base/'queue_status.json'),flush=True); return
        q=read(base/'queue_status.json'); done=sum(q.get('rgb_cases_counted',{}).values())
        if q['status']!='RUNNING' or done>=280:
            print('NO_HANDOFF: finished or near completion; original executor left running',q['status'],done,flush=True); return
        models=['M00_42']+[r['job'] for r in c.job_list()]
        if q.get('failed_tasks')!=0 or q.get('pending_training')!=0 or q.get('pending_other')!=0 or q.get('actual_new_updates')!=176000:
            raise RuntimeError('only completed training / RGB-only stage may be handed off')
        verify_static(base,c,models)
        before=scan_cases(base,c,models,cases(c.VAL))
        if sum(before['complete'].values())>=280:
            print('NO_HANDOFF: persisted cases already near completion; original executor left running',flush=True); return
        if not before['calibration'] or before['calibration']['task']['tile']!=min(r['task']['tile'] for r in before['todo']):
            print('NO_HANDOFF: no comparable historical case in first remaining tile',flush=True); return
        code=base/'count_engine_code'/commit; code.mkdir(parents=True,exist_ok=True)
        target=code/'handoff_phase3_m1_counts.py'
        shutil.copyfile(Path(__file__).resolve(),target)
        resources=attach_resource_probe(base,code); limits=resources.cpu_limits(); available=resources.memory_available()
        if limits['effective_limit_cpus']<64 or available<40*1024**3:
            print('NO_HANDOFF: insufficient CPU/RAM headroom; original executor left running',limits['effective_limit_cpus'],available,flush=True); return
        old_launch=read(base/'launch.json'); pid=old_launch['controller_pid']; identity=process_identity(pid)
        if pid!=19614 or not validate_old_identity(base,identity): raise RuntimeError('original controller identity differs; no signal sent')
        if not hasattr(os,'pidfd_open') or not hasattr(signal,'pidfd_send_signal'):
            print('NO_HANDOFF: safe pidfd API unavailable; original executor left running',flush=True); return
        owned=[]
        for row in q['workers'].values():
            worker=process_identity(row['pid'])
            if validate_old_identity(base,worker) and worker['ppid']==pid: owned.append(row['pid'])
        gpu_inventory(owned)
        print('PREFLIGHT_RETAINED_CASES',sum(before['complete'].values()),'REMAINING',len(before['todo']),'CPU_PROCESSES=32',flush=True)
        transport_smoke(); print('TARGET_FD_PROCESS_INTEGER_SMOKE_PASSED',flush=True)
        # Recheck after preflight; do not interrupt a run that has reached its final cases.
        q=read(base/'queue_status.json')
        if q['status']!='RUNNING' or sum(q.get('rgb_cases_counted',{}).values())>=280:
            print('NO_HANDOFF: original run reached final stage during preflight',flush=True); return
        stamp=c.now().replace(':','').replace('+','_')
        history=base/'analysis/count_handoff_history'/stamp; history.mkdir(parents=True,exist_ok=False)
        write(marker,dict(status='PREPARED_IDENTIFIED_CONTROLLER_HANDOFF',previous_pid=pid,commit=commit,history=str(history),observed_at=c.now()))
        write(history/'preflight.json',dict(original_binding=c.binding(base),launch=old_launch,
            identity=dict(start=identity['start'],ppid=identity['ppid']),queue=q,resources=limits))
        signal_identified_controller(base,pid,identity)
        print('TERM_SENT_ONLY_TO_IDENTIFIED_EXPERIMENT_CONTROLLER',pid,flush=True)
        with (base/'controller.lock').open('a') as compute_lock:
            deadline=time.monotonic()+240; last_print=0
            while True:
                try: fcntl.flock(compute_lock,fcntl.LOCK_EX|fcntl.LOCK_NB); break
                except BlockingIOError:
                    if time.monotonic()>deadline: raise RuntimeError('original controller lock remains held; no second executor started')
                    if time.monotonic()-last_print>10: print('WAITING_FOR_OWN_CONTROLLER_CLEAN_EXIT',flush=True); last_print=time.monotonic()
                    time.sleep(1)
            exit_deadline=time.monotonic()+15
            while process_identity(pid)==identity and time.monotonic()<exit_deadline: time.sleep(.2)
            if process_identity(pid)==identity: raise RuntimeError('old controller remains live; no second executor started')
            # Old controller's lifecycle must confirm its own children exited before any replacement.
            if not read(base/'ram_retirement.json')['all_owned_gpu_workers_exited']: raise RuntimeError('old GPU workers not retired')
            gpu_inventory()
            for name in ('queue_status.json','launch.json','progress_gpu0.json','progress_gpu1.json','technical_failure.json','ram_retirement.json'):
                if (base/name).exists(): shutil.copyfile(base/name,history/name)
            if (base/'technical_failure.json').exists():
                failure=read(base/'technical_failure.json')
                if failure.get('error')!='external stop 15': raise RuntimeError('unexpected original shutdown failure retained')
                os.replace(base/'technical_failure.json',history/'technical_failure_retained.json')
            inventory=scan_cases(base,c,models,cases(c.VAL)); write(history/'inventory.json',inventory)
            reg=dict(commit=commit,original_binding=c.binding(base),models=models,workers=32,case_capacity=8,
                algorithm='original phase3_m1_numeric.analyze unchanged',code_directory=str(code),
                files={'handoff_phase3_m1_counts.py':sha(target),'resource_probe.py':PROBE_SHA},
                inventory_path=(history/'inventory.json').relative_to(base).as_posix(),inventory_sha256=sha(history/'inventory.json'),history=str(history),observed_at=c.now())
            write(base/'count_engine_registration.json',reg)
            write(base/'count_engine_resource_profile.json',dict(cpu_processes=32,cpu_limits=limits,case_capacity=8,available_bytes_before_handoff=available,algorithm='original unchanged',observed_at=c.now()))
            for name in ('temporary','cache/torch','cache/cuda','cache/triton','cache/kernels'): (base/name).mkdir(parents=True,exist_ok=True)
            from phase24_common import env
            logpath=base/'count_engine_nohup.log'
            write(base/'queue_status.json',dict(status='COUNT_ENGINE_PREPARING_INPUTS',observed_at=c.now(),actual_new_updates=176000,
                pending_training=0,pending_other=0,pending_cpu=0,rgb_cases_counted=inventory['complete'],cpu_executor_processes=32,
                count_engine_commit=commit))
            with logpath.open('x') as log:
                child=subprocess.Popen([sys.executable,'-u','-B',str(target),'--directory',str(base),'--commit',commit,'--run','--lock-fd',str(compute_lock.fileno())],
                    cwd=base/'code',env=env(base),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                    start_new_session=True,pass_fds=(compute_lock.fileno(),))
            write(base/'launch.json',dict(controller_pid=child.pid,log=str(logpath),executor='count_only_32_processes',commit=commit,observed_at=c.now()))
            write(marker,dict(status='LAUNCHED',controller_pid=child.pid,commit=commit,history=str(history),log=str(logpath),observed_at=c.now()))
            print('COUNT_ENGINE_LAUNCHED','PID='+str(child.pid),'RETAINED_CASES='+str(sum(inventory['complete'].values())),'REMAINING='+str(len(inventory['todo'])),flush=True)
            print('LOG:',logpath,flush=True)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--directory',type=Path,required=True); p.add_argument('--commit',required=True)
    p.add_argument('--run',action='store_true'); p.add_argument('--lock-fd',type=int); args=p.parse_args()
    base=args.directory.resolve(); base.relative_to(Path('/home/jovyan/zzx').resolve())
    if base.name!=RUN or not re.fullmatch('[0-9a-f]{40}',args.commit): raise RuntimeError('identified run and immutable code commit required')
    for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[key]='1'
    os.environ['CUDA_VISIBLE_DEVICES']=''; os.environ['PYTHONDONTWRITEBYTECODE']='1'
    sys.path.insert(0,str(base/'code')); sys.path.insert(0,str(base/'code/scripts'))
    if args.run:
        if args.lock_fd is None: raise RuntimeError('replacement requires inherited controller lock')
        execute(base,args.lock_fd)
    else: launch(base,args.commit)

if __name__=='__main__': main()
