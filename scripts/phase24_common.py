"""Immutable contracts for Phase2.4. Never mutate the inherited Phase2 snapshot."""
import hashlib, json, os, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import numpy as np

FIT=['2_12','2_10','7_8','3_12','5_12','7_9','6_9','7_7','4_12','6_8','6_12','6_7']
VAL=['3_11','5_10']
FAMILIES=['pixel','random','gradient','matched']
OLD='research_phase2_matched_20261013T151120_1310582'
OLD_BINDING={'plan.json':'a4928fe58d25aa0ab1d3438db5686f5967333ea245bfdf365846ffc53e5ba2b3',
 'code_manifest.json':'09d70a32b20dc18a3c51cf1b78c35255d55cc61df0cc20cbb52c315400f47711',
 'prepared.json':'2772f2eb27cd77ff69f2ea89e5692c46667ff34158437bfeb60a300beb1c4e7e'}
FEATURES=['entropy_r','entropy_d','maxprob_r','maxprob_d','margin_r','margin_d',
 'center_norm_r','center_norm_d','disagreement','dsm_mean','dsm_std','dsm_gradient',
 'rgb_zero_fraction','available_r','available_d']
DATA={}
def now():return datetime.now(timezone(timedelta(hours=8))).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 t=p.with_name(p.name+'.tmp.'+str(os.getpid()))
 t.write_text(json.dumps(x,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n',encoding='utf-8')
 os.replace(t,p)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
def key(*x):return int.from_bytes(hashlib.sha256('|'.join(map(str,x)).encode()).digest()[:8],'big')
def scoped(p,root):
 p=Path(p);r=Path(root).resolve();q=p.resolve();q.relative_to(r)
 if p.is_symlink():raise RuntimeError('symlink not allowed: '+str(p))
 return q
def identity(p):
 st=Path(p).stat();return [st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns]
def binding(base):return {n:sha(Path(base)/n) for n in ('plan.json','code_manifest.json')}
def verify(base):
 base=Path(base);p=read(base/'plan.json');r=read(base/'registration.json')
 if r['binding']!=binding(base):raise RuntimeError('registered binding changed')
 if p['fit12']!=FIT or p['val2']!=VAL or p['gpus']!=[0,1] or p['seed']!=42:raise RuntimeError('split/GPU/seed changed')
 if p['max_head_updates']!=32000 or p['automatic_retry'] or p['new_seeds']:raise RuntimeError('budget changed')
 for n,h in read(base/'code_manifest.json')['files'].items():
  f=scoped(base/'code'/n,base/'code')
  if sha(f)!=h:raise RuntimeError('snapshot changed: '+n)
 return p
def live(pid,base=None):
 try:
  cmd=(Path('/proc')/str(pid)/'cmdline').read_bytes()
  return bool(cmd) and (base is None or str(base).encode() in cmd)
 except (FileNotFoundError,ProcessLookupError):return False
def profile():
 cores=len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else (os.cpu_count() or 1)
 c=Path('/sys/fs/cgroup/cpu.max')
 if c.exists():
  q,period=c.read_text().split()
  if q!='max':cores=min(cores,max(1,int(q)//int(period)))
 mem=0
 f=Path('/proc/meminfo')
 if f.exists():
  mem=next(int(x.split()[1])*1024 for x in f.read_text().splitlines() if x.startswith('MemAvailable:'))
 lim=Path('/sys/fs/cgroup/memory.max');cur=Path('/sys/fs/cgroup/memory.current')
 if lim.exists() and lim.read_text().strip()!='max':mem=min(mem,max(0,int(lim.read_text())-int(cur.read_text())))
 cap=min(128*1024**3,mem//4)
 return dict(effective_cores=cores,available_bytes=mem,ram_cap_bytes=cap,
  analysis_worker_candidates=[n for n in (16,24,32) if n<=max(1,cores-24)] or [max(1,cores//2)],
  numerical_threads_per_worker=1,crop_workers=min(8,max(1,cores//8)),prefetch_batches=4,
  gpu_case_slots_per_worker=2,sample_cap_bytes=1024**3,disk_array_cache=False,
  emergency_disk_cap_bytes=0,observed_at=now())
def env(base,gpu=None):
 base=Path(base);v=dict(os.environ)
 v.update(CUDA_VISIBLE_DEVICES='' if gpu is None else str(gpu),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',
  OPENBLAS_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',
  CUBLAS_WORKSPACE_CONFIG=':4096:8',XFORMERS_DISABLED='1',
  TMPDIR=str(base/'temporary'),TMP=str(base/'temporary'),TEMP=str(base/'temporary'),
  TORCH_HOME=str(base/'cache/torch'),XDG_CACHE_HOME=str(base/'cache'),
  CUDA_CACHE_PATH=str(base/'cache/cuda'),TRITON_CACHE_DIR=str(base/'cache/triton'),
  PYTORCH_KERNEL_CACHE_PATH=str(base/'cache/kernels'))
 return v
def cid(c):return '_'.join(str(c[n]) for n in ('tile','panel','direction','family','realization','ratio','damage'))
def panel(conditions):
 rows=[]
 for tile in VAL:
  rows.append(dict(tile=tile,panel='clean',direction='none',family='clean',realization=0,ratio=0,damage='clean'))
  for dr in ('rgb','dsm'):
   for fam in FAMILIES:
    for i in range(1,21):
     c=dict(tile=tile,direction=dr,family=fam,realization=i,ratio=25)
     rows.append(dict(c,panel='P-M',damage='zero'))
     rows.extend(dict(c,panel='P-U',damage=d) for d in ('zero','down4'))
   for ratio in (5,10):
    for i in range(1,21):rows.append(dict(tile=tile,direction=dr,family='pixel',realization=i,ratio=ratio,panel='dose',damage='zero'))
  for d in conditions:
   if d!='clean':rows.append(dict(tile=tile,panel='ordinary',direction='none',family=d,realization=0,ratio=0,damage=d))
 if len(rows)!=1164 or len({cid(c) for c in rows})!=1164:raise RuntimeError('original panel differs')
 return rows
def smoke_cases(rows):
 use=[c for c in rows if c['panel']=='clean' or
  (c['panel']=='P-U' and c['family']=='pixel' and c['realization']==1) or
  (c['panel']=='P-M' and c['family']=='pixel' and c['realization']==1 and
   (c['tile'],c['direction']) in [('3_11','rgb'),('5_10','dsm')])]
 if len(use)!=12:raise RuntimeError('smoke panel differs')
 return use
def original_counts(old,c,system='average'):
 f=Path(old)/'evaluation'/(system+'_16000')/cid(c)/'counts.json'
 z=read(f);receipt=read(f.parent/'complete.json')
 if z['binding']!=OLD_BINDING or receipt['files']['counts.json']!=sha(f):raise RuntimeError('old counts changed')
 return z
def metric(a):
 a=np.asarray(a);den=a.sum(0)+a.sum(1)-a.diagonal()
 v=den[:5]>0
 return float((a.diagonal()[:5][v]/den[:5][v]).mean()*100) if v.any() else None
def groupkey(c):return tuple(c[n] for n in ('panel','direction','family','realization','ratio','damage'))
def scores(rows,system,panel_name='P-U',direction=None,tile=None,region='all'):
 from collections import defaultdict
 pool={}
 for row in rows:
  c=row['case']
  if c['panel']!=panel_name or (direction and c['direction']!=direction) or (tile and c['tile']!=tile):continue
  m=np.asarray(row['matrices']['noboundary'][system][region],np.int64)
  k=groupkey(c);pool[k]=pool.get(k,np.zeros((6,6),np.int64))+m
 values=[metric(x) for x in pool.values()];values=[x for x in values if x is not None]
 return float(np.mean(values)) if values else None
