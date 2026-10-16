"""Phase2 immutable contracts, atomic receipts, resource and source binding."""
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np

FIT = ['2_12','2_10','7_8','3_12','5_12','7_9','6_9','7_7','4_12','6_8','6_12','6_7']
VAL = ['3_11','5_10']
FAMILIES = ['pixel','random','gradient','matched']
PREVIOUS = 'research_phase15_recoverability_20261012T233532_842792'
JOBS = {'A_RGB':16000,'A_DSM':16000,'B0':8000,'B2':8000,'B1':8000,'B3':8000}

def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp.'+str(os.getpid()))
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    os.replace(tmp,path)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024**2),b''):h.update(chunk)
    return h.hexdigest()

def key(*args):
    return int.from_bytes(hashlib.sha256('|'.join(map(str,args)).encode()).digest()[:8],'big')

def digest(array):
    x=np.ascontiguousarray(array)
    return hashlib.sha256(str(x.dtype).encode()+str(x.shape).encode()+x.tobytes()).hexdigest()

def binding(base):
    return {n:sha(Path(base)/n) for n in ('plan.json','code_manifest.json','prepared.json')}

def verify(base, prepared=True):
    base=Path(base);p=read(base/'plan.json')
    if (base/'registration.json').exists():
        registration=read(base/'registration.json')
        if registration['plan_sha256']!=sha(base/'plan.json') or registration['code_sha256']!=sha(base/'code_manifest.json'):
            raise RuntimeError('registration plan/code manifest changed')
    if p['fit12']!=FIT or p['val2']!=VAL or p['gpus']!=[0,1] or p['seed']!=42:
        raise RuntimeError('immutable Phase2 contract changed')
    for name,h in read(base/'code_manifest.json')['files'].items():
        path=(base/'code'/name).resolve();path.relative_to((base/'code').resolve())
        if sha(path)!=h:raise RuntimeError('snapshot changed: '+name)
    if prepared:
        prep=read(base/'prepared.json')
        if prep['plan_sha256']!=sha(base/'plan.json'):raise RuntimeError('prepared plan differs')
        for name,h in prep['receipts'].items():
            if sha(base/name)!=h:raise RuntimeError('prepared binding differs: '+name)
    return p

def array_save(path, array):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp.'+str(os.getpid()))
    with tmp.open('wb') as f:np.save(f,array,allow_pickle=False)
    os.replace(tmp,path)
    return dict(path=str(path),sha256=sha(path),shape=list(array.shape),dtype=str(array.dtype))

def compact_save(path,array,kind):
    shape=list(array.shape)
    if kind=='bool':data=np.packbits(array,bitorder='little')
    elif kind=='labels3':
        labels=np.where(array==255,7,array).astype(np.uint8)
        if (labels>7).any():raise ValueError('three-bit label outside range')
        data=np.stack([np.packbits((labels>>b)&1,bitorder='little') for b in range(3)])
    else:raise ValueError(kind)
    row=array_save(path,data);row.update(storage=kind,original_shape=shape);return row

def compact_load(row):
    if sha(row['path'])!=row['sha256']:raise RuntimeError('case array bytes changed')
    a=np.load(row['path'],mmap_mode='r',allow_pickle=False)
    if 'storage' not in row:return a
    shape=tuple(row['original_shape']);n=int(np.prod(shape))
    if row['storage']=='bool':return np.unpackbits(a,bitorder='little',count=n).reshape(shape).astype(bool)
    out=np.zeros(n,np.uint8)
    for b in range(3):out|=np.unpackbits(a[b],bitorder='little',count=n).astype(np.uint8)<<b
    out[out==7]=255;return out.reshape(shape)

def resources():
    cores=len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else os.cpu_count() or 1
    quota=Path('/sys/fs/cgroup/cpu.max')
    if quota.exists():
        q,period=quota.read_text().split()
        if q!='max':cores=min(cores,max(1,int(q)//int(period)))
    mem=0
    if Path('/proc/meminfo').exists():
        for line in Path('/proc/meminfo').read_text().splitlines():
            if line.startswith('MemAvailable:'):mem=int(line.split()[1])*1024
    limit=Path('/sys/fs/cgroup/memory.max');current=Path('/sys/fs/cgroup/memory.current')
    if limit.exists() and limit.read_text().strip()!='max':
        mem=min(mem,max(0,int(limit.read_text())-int(current.read_text())))
    if not mem:raise RuntimeError('cannot establish available memory')
    reserve=min(18,max(2,cores//2))
    return dict(effective_cores=cores,available_bytes=mem,hot_cache_bytes=min(256*1024**3,mem//2),
                analysis_workers=min(16,max(1,(cores-reserve)//2)),crop_workers=min(8,max(1,cores//4)),
                prefetch_batches=8,observed_at=now())

def live(pid,base):
    try:return str(base).encode() in (Path('/proc')/str(pid)/'cmdline').read_bytes()
    except (FileNotFoundError,ProcessLookupError):return False

def gpu_metrics():
    import torch
    return dict(gpu_allocated_bytes=torch.cuda.memory_allocated(),gpu_reserved_bytes=torch.cuda.memory_reserved(),
                gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated())

def complete(base,folder,extra=None):
    folder=Path(folder)
    files={f.relative_to(folder).as_posix():sha(f) for f in folder.rglob('*')
           if f.is_file() and f.name!='complete.json' and '.tmp.' not in f.name}
    write(folder/'complete.json',dict(binding=binding(base),files=files,completed_at=now(),**(extra or {})))

def check_complete(base,folder):
    folder=Path(folder);r=read(folder/'complete.json')
    if r['binding']!=binding(base):raise RuntimeError('completion source binding changed')
    for n,h in r['files'].items():
        if sha(folder/n)!=h:raise RuntimeError('completed artifact changed: '+n)
    return r

def runtime(base,gpu):
    import torch
    if not torch.cuda.is_available() or os.environ.get('CUDA_VISIBLE_DEVICES')!=str(gpu):
        raise RuntimeError('physical GPU binding differs')
    if torch.__version__!='2.2.2+cu121':raise RuntimeError('expected frozen server Torch 2.2.2+cu121')
    torch.manual_seed(42);np.random.seed(42);torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False
    torch.backends.cuda.matmul.allow_tf32=True;torch.backends.cudnn.allow_tf32=True
    p=verify(base)
    from post_n2_diag_runtime import input_contract
    input_contract(Path(p['root']),read(Path(p['previous'])/'source_plan.json'))

def env(base,gpu=None):
    base=Path(base);code=base/'code'
    value=dict(os.environ,CUDA_VISIBLE_DEVICES='' if gpu is None else str(gpu),
        PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
        CUBLAS_WORKSPACE_CONFIG=':4096:8',XFORMERS_DISABLED='1',
        PYTHONPATH=os.pathsep.join([str(code),str(code/'scripts')]),TMPDIR=str(base/'temporary'),
        TMP=str(base/'temporary'),TEMP=str(base/'temporary'),TORCH_HOME=str(base/'cache/torch'),
        XDG_CACHE_HOME=str(base/'cache'),CUDA_CACHE_PATH=str(base/'cache/cuda'),
        TRITON_CACHE_DIR=str(base/'cache/triton'),PYTORCH_KERNEL_CACHE_PATH=str(base/'cache/kernels'))
    return value
