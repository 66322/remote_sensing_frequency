import datetime as dt
import hashlib
import json
import os
import random
from pathlib import Path

ROOT = Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro')
NAME = 'post_m2_multiroute_v2_20261030_r1'
COLORS = ((255,255,255),(0,0,255),(0,255,255),(0,255,0),(255,255,0),(255,0,0))
FIT = {'2_12','2_10','7_8','3_12','5_12','7_9','6_9','7_7','4_12','6_8','6_12','6_7'}
CONDITIONS = ('clean','rgb_down4','rgb_blur','dsm_down4','dsm_shift')
JOBS = ('B0','B1','G1','G2','G3','Q1','Q2','Q3','S1','S2','S3')
# Independent computational paths. G3/S3 add only a fixed roll to G2/S2.
PROFILES = ('B0','B1','G1','G2','Q2','S1','S2')
PROFILE_FOR = dict(B0='B0',B1='B1',G1='G1',G2='G2',G3='G2',Q1='Q2',Q2='Q2',Q3='Q2',S1='S1',S2='S2',S3='S2')
CONFIG = dict(version=2,seed=42,updates=8000,batch=16,crop=512,stride=256,border=512,
    lr=0.0003,weight_decay=0.01,adam_betas=[0.9,0.999],clip_norm=5.0,
    precision='bfloat16_autocast_float32_parameters',supervision='Full_512',
    loss='six_class_unweighted_CE_global_valid_pixel_mean',gsd_m=0.05,
    boundary_tolerance_px=4,boundary_tolerance_m=0.20,calibration_steps=[4000,8000],
    blur_sigma_px=2.0,dsm_shift_px=[16,0],evaluation_damage_side=0.5,
    geometry_grid=64,geometry_kernel=5,geometry_temperature=0.10,
    mismatch_roll_grid_px=[17,23],eval_batch=16,
    profile_candidates=[[4,16]],profile_warmup=1,profile_measured=3,
    profile_timeout_seconds=120,slowdown_factor=2.5,baseline_min_clean_fg5=50.0,
    threads=1,counter_threads=6,worker_prefetch=2,max_resident_tile_bytes=12*1024**3,
    gpu_min_free_mib=40000,task_timeout_hours=24,heartbeat_timeout_seconds=1200)

def now(): return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,v,once=False):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(v,ensure_ascii=False,allow_nan=False,indent=None if p.name=='exposure.json' else 2)+'\n'
    if once:
        with p.open('x',encoding='utf-8') as f:f.write(text)
    else:
        q=p.with_name(p.name+'.tmp.'+str(os.getpid()));q.write_text(text,encoding='utf-8');os.replace(q,p)
def key(*v): return int.from_bytes(hashlib.blake2b('|'.join(map(str,v)).encode(),digest_size=8).digest(),'big')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def seed_all(seed=42):
    import numpy as np
    import torch
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    if torch.cuda.is_available():torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    # Do not trigger the known strict-deterministic CUDA CE/resize failure.
    # Deterministic crops, seeds and kernels are recorded; bitwise GPU identity is not promised.
    torch.use_deterministic_algorithms(False)
def metrics(cm):
    import numpy as np
    a=np.asarray(cm,dtype=np.int64)
    if a.shape!=(6,6) or (a<0).any():raise ValueError('invalid confusion matrix')
    tp=a.diagonal();union=a.sum(0)+a.sum(1)-tp
    iou=np.divide(tp,union,out=np.zeros(6,dtype=float),where=union>0)
    return dict(cm=a.tolist(),valid_pixels=int(a.sum()),support=a.sum(1).tolist(),
        iou=(100*iou).tolist(),fg5=float(100*iou[:5].mean()),miou6=float(100*iou.mean()))
def source():
    p=Path(__file__).resolve().parents[2]
    s=read(p/'SOURCE.json')
    if len(s.get('commit',''))!=40:raise RuntimeError('bootstrap SOURCE.json absent/invalid')
    for n,digest in read(p/'payload_manifest.json')['files'].items():
        if sha(p/n)!=digest:raise RuntimeError('frozen payload changed: '+n)
    return p,s
def runtime_contract(base):
    code,s=source();base=Path(base).resolve();base.relative_to(ROOT/'records')
    p=read(base/'contract.json')
    if p['config']!=CONFIG or p['source']!=s:raise RuntimeError('registered configuration/source changed')
    for row in p['input_files']:
        st=Path(row['path']).stat()
        if st.st_size!=row['bytes'] or st.st_mtime_ns!=row['mtime_ns']:
            raise RuntimeError('input identity changed: '+row['path'])
    return p
def ipc_tmpdir(base):
    # AF_UNIX includes Python's pymp-/listener- suffix; deep run paths overflow it.
    owner=Path('/home/jovyan/zzx').resolve()
    folder=owner/'tmp'/('pm2_'+hashlib.sha256(str(Path(base).resolve()).encode()).hexdigest()[:12])
    folder=folder.resolve();folder.relative_to(owner)
    if len(os.fsencode(str(folder)))>50:raise RuntimeError('IPC temporary directory is too long')
    return str(folder)

def env(gpu,base):
    temporary=ipc_tmpdir(base)
    v=dict(os.environ);v.update(CUDA_VISIBLE_DEVICES=str(gpu),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',
        OPENBLAS_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',XFORMERS_DISABLED='1',
        PYTHONDONTWRITEBYTECODE='1',TORCH_HOME=str(Path(base)/'cache/torch'),
        CUDA_CACHE_PATH=str(Path(base)/'cache/cuda'),TMPDIR=temporary,TEMP=temporary,TMP=temporary)
    return v
