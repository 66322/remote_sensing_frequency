"""M2 immutable contracts. No data/model/GPU work at import time."""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import numpy as np

FIT = ['2_12','2_10','7_8','3_12','5_12','7_9','6_9','7_7','4_12','6_8','6_12','6_7']
SEEDS = [42,17,2026]
ARMS = ['D0','DSelf','DClean','DF','DShuffle','DEntropy','DMix']
FAMILIES = ['pixel','random','gradient','matched']
ALPHAS = [0.,.05,.1,.2,.4,.6,1.]
RGB_CONDITIONS = ['clean','down2','down4','down8','blur2','noise005']
DATA = {}

def now(): return datetime.now(timezone(timedelta(hours=8))).isoformat()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp.'+str(os.getpid()))
    tmp.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n',encoding='utf-8')
    os.replace(tmp,path)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024**2),b''): h.update(block)
    return h.hexdigest()
def key(*parts): return int.from_bytes(hashlib.sha256('|'.join(map(str,parts)).encode()).digest()[:8],'big')
def scoped(path, root):
    path,root=Path(path),Path(root).resolve()
    for node in [path,*path.parents]:
        if node==root: break
        if node.is_symlink(): raise RuntimeError('symlink refused: '+str(node))
    out=path.resolve(); out.relative_to(root)
    if out==root: raise RuntimeError('refuse root itself')
    return out
def binding(base): return {n:sha(Path(base)/n) for n in ['plan.json','code_manifest.json','folds.json']}
def verify(base):
    base=Path(base); p=read(base/'plan.json')
    if read(base/'registration.json')['binding']!=binding(base): raise RuntimeError('execution binding changed')
    if p['allowed_pool']!=FIT or p['seeds']!=SEEDS or p['physical_gpus']!=[0,1]: raise RuntimeError('split/seed/GPU contract')
    if p['updates']!=32000 or p['batch']!=16 or p['auto_retry']: raise RuntimeError('budget contract')
    for n,h in read(base/'code_manifest.json')['files'].items():
        if sha(scoped(base/'code'/n,base/'code'))!=h: raise RuntimeError('source changed: '+n)
    return p
def jobs(folds):
    out=[]
    for fold in ['F0','F1','F2']:
        group=folds['folds'][fold]
        for seed in SEEDS:
            stem=f'{fold}_s{seed}_'
            ts=[stem+'T'+str(i) for i in range(4)]
            out.append(dict(id=stem+'R',fold=fold,seed=seed,role='rgb_reference',modality='rgb',arm='D0',train=group['train'],depends_on=[]))
            for i in range(4):
                excluded=group['inner_pairs'][i]
                out.append(dict(id=ts[i],fold=fold,seed=seed,role='rgb_oof_teacher',modality='rgb',arm='D0',inner_pair=i,
                    train=[t for t in group['train'] if t not in excluded],excluded=excluded,depends_on=[]))
            for arm in ARMS:
                out.append(dict(id=stem+arm,fold=fold,seed=seed,role='dsm_student',modality='dsm',arm=arm,
                    train=group['train'],depends_on=[] if arm in ['D0','DSelf'] else ts))
    if len(out)!=108 or len({j['id'] for j in out})!=108: raise RuntimeError('core DAG contract')
    return out
def cm_metric(cm):
    a=np.asarray(cm,np.int64); den=a.sum(0)+a.sum(1)-a.diagonal()
    if a.shape!=(6,6) or (a<0).any(): raise ValueError('invalid CM')
    return None if (den[:5]==0).any() else float(100*np.mean(a.diagonal()[:5]/den[:5]))
def gpu_inventory():
    import subprocess
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,name,memory.total,memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True)
    apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,process_name,used_memory','--format=csv,noheader,nounits'],text=True)
    rows={int(r.split(',')[0]):[x.strip() for x in r.split(',')] for r in gpu.splitlines()}
    selected={g:rows[g] for g in [0,1] if g in rows}
    ready=set(selected)=={0,1} and all(float(r[4])>=40000 and r[1] not in apps for r in selected.values())
    return dict(gpus=gpu,compute_apps=apps,selected=selected,ready=ready,observed_at=now())
def environment(base,gpu=None):
    v=dict(os.environ); base=Path(base)
    v.update(CUDA_VISIBLE_DEVICES='' if gpu is None else str(gpu),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',
        OPENBLAS_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',CUBLAS_WORKSPACE_CONFIG=':4096:8',
        XFORMERS_DISABLED='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(base/'temporary'),TMP=str(base/'temporary'),TEMP=str(base/'temporary'),
        TORCH_HOME=str(base/'cache/torch'),XDG_CACHE_HOME=str(base/'cache'),CUDA_CACHE_PATH=str(base/'cache/cuda'),
        TRITON_CACHE_DIR=str(base/'cache/triton'),PYTORCH_KERNEL_CACHE_PATH=str(base/'cache/kernels'))
    v['PYTHONPATH']=os.pathsep.join([str(base/'code'),str(base/'code/scripts')])
    return v
def resources():
    cores=len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else os.cpu_count() or 1
    f=Path('/sys/fs/cgroup/cpu.max')
    if f.exists():
        quota,period=f.read_text().split()
        if quota!='max': cores=min(cores,max(1,int(quota)//int(period)))
    mem=next((int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')),0)
    limit,current=Path('/sys/fs/cgroup/memory.max'),Path('/sys/fs/cgroup/memory.current')
    if limit.exists() and limit.read_text().strip()!='max': mem=min(mem,max(0,int(limit.read_text())-int(current.read_text())))
    return dict(effective_cores=cores,available_bytes=mem,crop_workers=min(8,max(1,cores//12)),
        count_workers=min(32,max(1,cores-20)),numerical_threads=1,observed_at=now())
