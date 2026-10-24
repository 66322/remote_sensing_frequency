"""Dual-GPU dynamic queue with parallel RAM-only stripes and gated paired training."""
import os, sys, time, signal, traceback, multiprocessing as mp
from pathlib import Path
from collections import deque
from concurrent.futures import ProcessPoolExecutor,ThreadPoolExecutor
import numpy as np
import phase24_common as common
from phase24_common import *

def cpu_stripe(descriptor,start,stop,c,quota,lock,heads):
 from phase24_ipc import Packet
 from phase24_numeric import stripe
 packet=Packet.receive(descriptor)
 try:return stripe(packet.arrays,start,stop,c,quota,lock,heads)
 finally:packet.close()

class Controller:
 def __init__(self,base,resource):
  self.base=Path(base);self.p=read(self.base/'plan.json');self.resource=resource
  self.context=mp.get_context('fork');self.events=self.context.Queue()
  self.tasks={g:self.context.Queue() for g in (0,1)};self.acks={g:self.context.Queue() for g in (0,1)}
  self.workers={};self.ready=set();self.training={};self.trained=[];self.samples=[];self.sample_bytes=0
  self.rows={};self.finished=set();self.pending_cpu=0;self.benchmarked=False
  self.state=dict(status='STARTING_GPU_WORKERS',observed_at=now(),workers={},completed={},pending_cpu_cases=0,
   automatic_retry=False,new_seeds=False,max_trainings=4,max_updates=32000,packet_arrays_on_disk=False)
  self.last_heartbeat=0
  # No Torch import in this parent before any fork.
  from phase24_runtime import worker
  for g in (0,1):
   proc=self.context.Process(target=worker,args=(str(self.base),g,self.tasks[g],self.events,self.acks[g]),name='phase24_gpu'+str(g))
   proc.start();self.workers[g]=proc;self.state['workers'][str(g)]=dict(pid=proc.pid,gpu=g,status='INITIALIZING')
  self.null_cpu=ProcessPoolExecutor(max_workers=2,mp_context=self.context)
  for f in [self.null_cpu.submit(int,i) for i in range(2)]:f.result()
  self.null_io=ThreadPoolExecutor(max_workers=1)
  self.cpu=self.make_cpu(resource['analysis_worker_candidates'][0])
  self.io=ThreadPoolExecutor(max_workers=2)
  self.report()
 def make_cpu(self,n):
  pool=ProcessPoolExecutor(max_workers=n,mp_context=self.context)
  # Start workers before fitting threads operate on BLAS; no CUDA in parent.
  futures=[pool.submit(int,i) for i in range(n)]
  for f in futures:f.result()
  return pool
 def report(self,status=None):
  if status:self.state['status']=status
  self.state.update(observed_at=now(),pending_cpu_cases=self.pending_cpu,sample_ram_bytes=self.sample_bytes,
   analysis_workers=getattr(self,'selected_cpu',self.resource['analysis_worker_candidates'][0]),
   completed={k:len(v) for k,v in self.rows.items()},trained_heads=list(self.trained))
  if hasattr(self,'wave_ids'):
   done=len(self.wave_ids&self.finished);elapsed=time.monotonic()-self.wave_started
   self.state.update(stage_cases_done=done,stage_cases_total=len(self.wave_ids),stage_elapsed_seconds=elapsed,
    stage_remaining_hours=None if done<20 else (len(self.wave_ids)-done)*elapsed/done/3600,
    ETA_basis='current whole pipeline throughput; conditional future stages excluded')
  write(self.base/'queue_status.json',self.state);self.last_heartbeat=time.monotonic()
 def process(self,event):
  kind=event['kind'];g=event.get('gpu')
  if kind=='ERROR':raise RuntimeError('GPU '+str(g)+': '+event['error']+'\n'+event['traceback'])
  if kind=='READY':
   self.ready.add(g);self.state['workers'][str(g)]['status']='READY'
  elif kind=='TRAIN_COMPLETE':
   arm=event['arm'];self.trained.append(arm);self.training.pop(g,None)
   self.state['workers'][str(g)]['status']='TRAIN_COMPLETE'
  elif kind=='PACKET':
   if not self.benchmarked:self.benchmark(event)
   self.pending_cpu+=1;self.io.submit(self.analyze,event)
  elif kind=='ANALYSIS_COMPLETE':
   row=event['row'];stage=event['stage'];self.rows.setdefault(stage,[]).append(row)
   self.finished.add(stage+'/'+cid(row['case']));self.pending_cpu-=1
   if event['sample'] is not None:
    sample=event['sample'];size=sum(v.nbytes for v in sample.values())
    self.sample_bytes+=size
    if self.sample_bytes>1024**3:raise RuntimeError('registered diagnostic sample RAM cap exceeded')
    self.samples.append((row['case'],sample))
   if len(self.rows[stage])%20==0:print('PHASE24_CASES',stage,len(self.rows[stage]),flush=True)
  elif kind=='ANALYSIS_ERROR':raise RuntimeError(event['error']+'\n'+event['traceback'])
  if time.monotonic()-self.last_heartbeat>3:self.report()
 def benchmark(self,event):
  from phase24_ipc import Packet
  from phase24_numeric import combine
  packet=Packet.receive(event['packet']);event['packet']=packet.descriptor()
  c=event['case'];h=packet.arrays['rm'].shape[0];parts=[(i,min(i+128,h)) for i in range(0,h,128)]
  reference=None;records=[]
  try:
   for n in self.resource['analysis_worker_candidates']:
    if getattr(self,'benchmark_cpu_n',None)!=n:
     self.cpu.shutdown(wait=True);self.cpu=self.make_cpu(n);self.benchmark_cpu_n=n
    self.report('CPU_EQUIVALENCE_AND_THROUGHPUT_BENCHMARK')
    warm=[self.cpu.submit(cpu_stripe,packet.descriptor(),a,b,c,0,None,None) for a,b in parts]
    warm_counts,_=combine([f.result() for f in warm])
    started=time.monotonic()
    futures=[self.cpu.submit(cpu_stripe,packet.descriptor(),a,b,c,0,None,None) for a,b in parts]
    counts,_=combine([f.result() for f in futures]);elapsed=time.monotonic()-started
    fingerprint=hashlib.sha256(json.dumps(counts,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    warm_sha=hashlib.sha256(json.dumps(warm_counts,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if warm_sha!=fingerprint:raise RuntimeError('CPU replay was not deterministic')
    if reference is not None and fingerprint!=reference:raise RuntimeError('CPU worker count changed integer/diagnostic results')
    reference=fingerprint;records.append(dict(workers=n,statistics_seconds=elapsed,result_sha256=fingerprint))
   chosen=min(records,key=lambda x:x['statistics_seconds'])['workers']
   if self.benchmark_cpu_n!=chosen:
    self.cpu.shutdown(wait=True);self.cpu=self.make_cpu(chosen)
   self.selected_cpu=chosen;self.benchmarked=True
   write(self.base/'cpu_benchmark.json',dict(binding=binding(self.base),records=records,selected_workers=chosen,
    same_anonymous_RAM_case=True,additional_expert_forwards=0,numerical_threads_per_worker=1,observed_at=now()))
  finally:packet.close()
 def analyze(self,event):
  from phase24_ipc import Packet
  from phase24_numeric import combine
  from phase24_analysis import bridge
  packet=None
  try:
   packet=Packet.receive(event['packet']);c=event['case'];h=packet.arrays['rm'].shape[0];quota=event['quota']
   started=time.monotonic();jobs=[]
   for a in range(0,h,128):
    b=min(h,a+128);n=(b*quota)//h-(a*quota)//h
    jobs.append(self.cpu.submit(cpu_stripe,packet.descriptor(),a,b,c,n,event['lock'],event['heads']))
   out,sample=combine([f.result() for f in jobs])
   if out['fallback_errors']:raise RuntimeError('single-available exact fallback failed')
   locked=event['lock']
   lock_receipt=None if locked is None else dict(source=locked['source'],target=locked['target'],
     path='fits/source_'+locked['source']+'.json',sha256=sha(self.base/'fits'/('source_'+locked['source']+'.json')))
   row=dict(out,case=c,stage=event['stage'],binding=binding(self.base),physical_gpu=event['gpu'],observed_at=now(),
    cpu_statistics_seconds=time.monotonic()-started,lock=lock_receipt,checkpoint_age=16000,segmentation_optimizer_updates=0)
   if event['stage']=='SMOKE':
    bridge(self.p['previous'],row)
    if not event['checks'] or not all(v['logits_exact'] for v in event['checks'].values()):raise RuntimeError('missing exact stitch proof')
    row['original_CM_bridge']=True;row['stitch_reference']=event['checks']
   target=self.base/'results'/event['stage']/(cid(c)+'.json');write(target,row)
   self.events.put(dict(kind='ANALYSIS_COMPLETE',stage=event['stage'],row=row,sample=sample))
   self.acks[event['gpu']].put(dict(id=event['id'],last_consumer_complete=True))
  except BaseException as exc:
   self.acks[event['gpu']].put(dict(id=event['id'],error=str(exc)))
   self.events.put(dict(kind='ANALYSIS_ERROR',error=str(exc),traceback=traceback.format_exc()))
  finally:
   if packet is not None:packet.close()
 def pump(self):
  from queue import Empty
  try:self.process(self.events.get(timeout=3))
  except Empty:
   for g,p in self.workers.items():
    if not p.is_alive():raise RuntimeError('GPU worker '+str(g)+' exited before completion')
   self.report()
 def wave(self,stage,commands):
  todo=deque(commands);ids={stage+'/'+cid(x['case']) for x in commands if x['kind']=='INFER'}
  self.wave_ids=ids;self.wave_started=time.monotonic();self.report(stage)
  arms={x['arm'] for x in commands if x['kind']=='TRAIN'};started=time.monotonic()
  while todo or not ids.issubset(self.finished) or not arms.issubset(set(self.trained)):
   while todo and self.ready:
    eligible=next((i for i,x in enumerate(todo) if x.get('forced_gpu') is None or x['forced_gpu'] in self.ready),None)
    if eligible is None:break
    cmd=todo[eligible];del todo[eligible]
    g=cmd['forced_gpu'] if cmd.get('forced_gpu') is not None else min(self.ready)
    self.ready.remove(g);self.tasks[g].put(cmd)
    self.state['workers'][str(g)]['status']=cmd['kind']+':'+(cmd.get('arm') or cid(cmd['case']))
    if cmd['kind']=='TRAIN':self.training[g]=cmd['arm']
   self.pump()
  write(self.base/'analysis'/(stage+'_complete.json'),dict(binding=binding(self.base),cases=len(ids),training_jobs=sorted(arms),
    elapsed_seconds=time.monotonic()-started,completed_at=now()))
 def command(self,stage,c,smoke=False,lock=None,heads=None,t0=False,quota=False):
  systems=['average','B0','B2']+(['T0','T0_4000'] if t0 else [])
  q=100000 if quota and c['panel']=='clean' else (2800 if quota and c['panel']=='P-U' else 0)
  return dict(kind='INFER',stage=stage,case=c,systems=systems,smoke=smoke,lock=lock,heads=heads,quota=q)
 def start_t0(self):
  while 0 not in self.ready:self.pump()
  self.ready.remove(0);self.tasks[0].put(dict(kind='TRAIN',arm='T0'))
  self.training[0]='T0';self.state['workers']['0']['status']='TRAIN:T0';self.report()
 def shutdown(self,failed=False):
  if failed:
   for g,p in self.workers.items():
    if p.is_alive():
     try:os.killpg(p.pid,signal.SIGTERM)
     except ProcessLookupError:pass
  else:
   for g in self.workers:self.tasks[g].put(dict(kind='STOP'))
  for p in self.workers.values():p.join(timeout=60)
  for p in self.workers.values():
   if p.is_alive():p.terminate();p.join(timeout=10)
  self.io.shutdown(wait=True,cancel_futures=True);self.cpu.shutdown(wait=True,cancel_futures=True)
  self.null_io.shutdown(wait=True,cancel_futures=True);self.null_cpu.shutdown(wait=True,cancel_futures=True)
  for q in [self.events,*self.tasks.values(),*self.acks.values()]:
   q.cancel_join_thread();q.close()
  self.samples.clear()
  write(self.base/'ram_retirement.json',dict(binding=binding(self.base),all_GPU_workers_exited=all(not p.is_alive() for p in self.workers.values()),
   temporary_pixel_arrays_on_disk=0,transport='memfd; all consumer/producer processes closed',
   sampled_fit_arrays_released=True,observed_at=now()))
 def weights(self,arms):
  out={}
  for n in arms:
   folder=self.base/'jobs'/n;receipt=read(folder/'complete.json')
   if receipt['binding']!=binding(self.base):raise RuntimeError('head source differs')
   if n=='T0':continue
   for age,f,h in [('', 'endpoint_weights.json',receipt['weights_sha256']),('_4000','trajectory_04000_weights.json',receipt['trajectory_weights_sha256'])]:
    if sha(folder/f)!=h:raise RuntimeError('head parameter export differs')
    out[n+age]=read(folder/f)
  return out
 def retire_training_temps(self):
  receipt=[]
  for n in self.trained:
   folder=self.base/'jobs'/n
   for name in ('last_resume.pth','last_resume.json','last_resume_weights.json','trajectory_04000.pth'):
    f=scoped(folder/name,self.base)
    if not f.exists():continue
    before=identity(f);row=dict(path=f.relative_to(self.base).as_posix(),sha256=sha(f),identity=before,bytes=f.stat().st_size)
    if identity(f)!=before:raise RuntimeError('temporary artifact changed before retirement')
    f.unlink();receipt.append(row)
  write(self.base/'training_artifact_retirement.json',dict(binding=binding(self.base),deleted=receipt,
   reason='4k counts/trajectory retained, full endpoint evaluated; no registered future consumer',observed_at=now()))

def main(base):
 base=Path(base).resolve();base.relative_to(Path('/home/jovyan/zzx').resolve())
 import fcntl
 lock=(base/'controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 controller=None;failed=True
 def interrupted(signum,frame):raise InterruptedError('external stop signal '+str(signum))
 signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
 if read(base/'queue_status.json')['status']!='REGISTERED':raise RuntimeError('used queue cannot restart automatically')
 try:
  from prepare_phase24 import prepare
  from phase24_analysis import d0,null_case,summarize_null,gate,trajectory_summary,paired_summary
  from phase24_fit import fit_fold
  p=verify(base);write(base/'queue_status.json',dict(status='PREPARING_SHARED_INPUTS',observed_at=now(),workers={}))
  resource=prepare(base);rows=panel(p['fixed_conditions']);core=[c for c in rows if c['panel'] in ('clean','P-U')]
  controller=Controller(base,resource);smokes=smoke_cases(rows)
  d0_future=controller.null_io.submit(d0,p['previous'],base)
  commands=[dict(controller.command('SMOKE',c,True,quota=True),forced_gpu=i%2) for i,c in enumerate(smokes)]
  controller.wave('SMOKE',commands)
  if any(sum(r['physical_gpu']==g for r in controller.rows['SMOKE'])!=6 for g in (0,1)):raise RuntimeError('both GPUs require exactly 6 smoke cases')
  write(base/'smoke_pass.json',dict(binding=binding(base),real_cases=12,gpus=[0,1],original_CM_exact=True,
   GPU_CPU_stitch_bitwise_exact=True,cpu_worker_equivalence=True,optimizer_updates=0,observed_at=now()))
  # D0 uses only already verified counts; alignment null never controls training gates.
  oldrows=d0_future.result();null_ref={dr:max(scores(oldrows,'rgb',direction=dr),scores(oldrows,'dsm',direction=dr)) for dr in ('rgb','dsm')}
  write(base/'analysis/null_reference.json',null_ref)
  null_future=controller.null_io.submit(lambda: list(controller.null_cpu.map(null_case,oldrows,chunksize=1)))
  reused=[r for r in controller.rows['SMOKE'] if r['case']['panel'] in ('clean','P-U')]
  controller.rows['D1']=list(reused);done={cid(r['case']) for r in reused}
  controller.wave('D1',[controller.command('D1',c,quota=True) for c in core if cid(c) not in done])
  if len(controller.rows['D1'])!=642:raise RuntimeError('core diagnostic count differs')
  controller.start_t0()
  controller.report('CPU_SOURCE_ONLY_FITS_AND_T0')
  with ThreadPoolExecutor(max_workers=2) as fits:
   futures={t:fits.submit(fit_fold,t,[(c,z) for c,z in controller.samples if c['tile']==t]) for t in VAL}
   locks={}
   for t,f in futures.items():
    result=f.result();write(base/'fits'/('source_'+t+'.json'),dict(result,binding=binding(base),observed_at=now()))
    locks[result['target']]=result
  controller.samples.clear();controller.sample_bytes=0
  write(base/'fit_sample_retirement.json',dict(binding=binding(base),last_consumers='both source fits',
    sample_rows_ceiling=2000000,array_files_created=0,released=True,observed_at=now()))
  controller.wave('D2',[controller.command('D2',c,lock=locks[c['tile']]) for c in core])
  extra=[c for c in rows if c['panel'] not in ('clean','P-U')]
  controller.wave('D3',[controller.command('D3',c,lock=locks[c['tile']]) for c in extra])
  evalrows=controller.rows['D2']+controller.rows['D3']
  calibrated=gate(evalrows,'calibrated');probe=gate(evalrows,'probe')
  write(base/'analysis/deployment_gate.json',dict(binding=binding(base),calibrated=calibrated,probe=probe,
   original_Phase2_L_unchanged=True,allow_paired_heads=not calibrated['accepted'] and probe['accepted']))
  while 'T0' not in controller.trained:controller.pump()
  arms=['T0']
  if not calibrated['accepted'] and probe['accepted']:
   controller.wave('TRAIN_PAIRED',[dict(kind='TRAIN',arm=n,forced_gpu=g) for g,n in enumerate(('T1','T2'))]);arms+=['T1','T2']
  else:write(base/'analysis/paired_heads_not_dispatched.json',dict(reason='calibration sufficient' if calibrated['accepted'] else 'current deployable probe gate not passed',
   segmentation_optimizer_updates=0,new_seeds=False,observed_at=now()))
  controller.wave('E',[controller.command('E',c,lock=locks[c['tile']],heads=controller.weights(arms),t0=True) for c in rows])
  end=controller.rows['E'];signal_gate=None;stat_control=None
  if 'T1' in arms:
   signal_gate=gate(end,'T1');delta=scores(end,'T1')-scores(end,'T2')
   tiles={t:scores(end,'T1',tile=t)-scores(end,'T2',tile=t) for t in VAL}
   allow=signal_gate['accepted'] and delta>=.3 and all(v>0 for v in tiles.values())
   stat_control=dict(T1_vs_T2_pp=delta,tile=tiles,allow_statistics_control=allow)
   write(base/'analysis/paired_head_gate.json',dict(binding=binding(base),signal=signal_gate,capacity_control=stat_control))
   if allow:
    controller.wave('TRAIN_SHIFT',[dict(kind='TRAIN',arm='T3',forced_gpu=0)]);arms+=['T3']
    controller.wave('E_T3',[controller.command('E_T3',c,lock=locks[c['tile']],heads=controller.weights(['T3'])) for c in rows])
    indexed={cid(r['case']):r for r in controller.rows['E_T3']}
    for r in end:
     row=indexed[cid(r['case'])]
     for scope in ('full','noboundary'):
      for n in ('T3','T3_4000'):r['matrices'][scope][n]=row['matrices'][scope][n]
    stat_control.update(T1_vs_T3_pp=scores(end,'T1')-scores(end,'T3'),
      tile_T1_vs_T3={t:scores(end,'T1',tile=t)-scores(end,'T3',tile=t) for t in VAL})
  summarize_null(null_future.result(),base)
  summary=dict(binding=binding(base),results=trajectory_summary(end),deployment_gate=read(base/'analysis/deployment_gate.json'),
   signal_gate=signal_gate,statistics_control=stat_control,trained_heads=arms,total_optimizer_updates=len(arms)*8000,
   old_expert_optimizer_updates=0,seed=42,no_new_seeds=True,test6_loaded=False,held4_loaded=False,
   primary='Potsdam Fit12/Val2 NoBoundary mIoU_fg5, fixed endpoint, conditions macro after pooled tile CM',
   paired_mask_intervals={n:paired_summary(end,n,'reference') for n in arms},
   observed_at=now(),no_automatic_followup=True)
  write(base/'summary.json',summary)
  # Verify persisted counts before deleting trajectory/resume artifacts.
  evidence=[]
  for stage,values in controller.rows.items():
   for r in values:
    f=base/'results'/stage/(cid(r['case'])+'.json')
    if not f.exists():continue
    raw=read(f)
    if raw['binding']!=binding(base):raise RuntimeError('persisted integer evidence binding differs')
    evidence.append(dict(path=f.relative_to(base).as_posix(),sha256=sha(f),bytes=f.stat().st_size))
  write(base/'evidence_index.json',dict(binding=binding(base),records=evidence,summary_sha256=sha(base/'summary.json'),
   sample_population='guarded source interiors; target full-tile metrics from integer CMs'))
  from verify_phase24_results import verify_results
  verify_results(base)
  controller.retire_training_temps();controller.shutdown(False);failed=False
  controller.report('PHASE24_COMPLETE_AWAITING_REVIEW')
  print('PHASE24_COMPLETE NO_AUTOMATIC_EXPERT_TRAINING',base,flush=True)
  print('UPLOAD_READY',base/'code/scripts/upload_phase24.py',flush=True)
 except BaseException as exc:
  write(base/'technical_failure.json',dict(error=str(exc),traceback=traceback.format_exc(),observed_at=now(),automatic_retry=False))
  if controller is not None:
   controller.shutdown(True);controller.state['error']=str(exc);controller.report('TECHNICAL_FAILURE_HOLD')
  else:write(base/'queue_status.json',dict(status='TECHNICAL_FAILURE_HOLD',error=str(exc),observed_at=now(),workers={}))
  raise
 finally:lock.close()

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);main(p.parse_args().directory)
