import argparse
import importlib.util
import inspect
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from . import common as c

def prepare(base):
    import numpy as np
    import torch
    from PIL import Image
    import scipy
    import post_m2_a0 as a0
    from . import data as d
    from . import model as m
    from .controller import idle_gpus
    if sys.platform!='linux':raise RuntimeError('target preparation must run on Linux server')
    if platform.python_version()!='3.11.13' or torch.__version__!='2.7.1+cu126':
        raise RuntimeError('expected existing Python3.11.13/Torch2.7.1+cu126; no automatic environment changes')
    if os.environ.get('CONDA_DEFAULT_ENV')!='remote_sensing':raise RuntimeError('activate existing remote_sensing environment')
    code,source=c.source();legacy=a0.contract(argparse.Namespace(root=str(c.ROOT)))
    if set(sum(legacy['folds'].values(),[]))!=c.FIT:raise RuntimeError('frozen F0 whitelist mismatch')
    resources=a0.resource_snapshot()
    if resources['effective_cpu_cores']<12 or resources['cgroup_aware_memory_available_bytes']<24*1024**3:
        raise RuntimeError('insufficient bounded dual-worker RAM/CPU headroom; no disk-logit fallback')
    snapshot=idle_gpus();rows=[];headers={}
    for tile in sum(legacy['folds'].values(),[]):
        shape=None;headers[tile]={}
        for name,path in d.tile_paths(legacy['data'],tile).items():
            st=path.stat();rows.append(dict(tile=tile,field=name,path=str(path),bytes=st.st_size,mtime_ns=st.st_mtime_ns))
            with Image.open(path) as im:
                if shape is not None and im.size!=shape:raise RuntimeError('input grid shape mismatch')
                shape=im.size;scale=getattr(im,'tag_v2',{}).get(33550)
                if scale and any(abs(float(x)-.05)>1e-6 for x in scale[:2]):raise RuntimeError('GSD mismatch')
                headers[tile][name]=dict(size=list(im.size),mode=im.mode,pixel_scale=list(scale) if scale else None)
                if name=='dsm' and im.mode!='F':raise RuntimeError('expected raw floating DSM, not jpg/nDSM')
        a,b=headers[tile]['rgb']['pixel_scale'],headers[tile]['dsm']['pixel_scale']
        if a and b and a!=b:raise RuntimeError('RGB/DSM physical grid mismatch')
    for path in [Path(legacy['d2']['weight']),legacy['m2']/'folds.json',legacy['m2']/'pretrained.json']:
        st=path.stat();rows.append(dict(path=str(path),bytes=st.st_size,mtime_ns=st.st_mtime_ns))
    base=Path(base).resolve();base.relative_to(c.ROOT/'records')
    if (base/'contract.json').exists():raise RuntimeError('prepared contract exists; use status, do not reprepare')
    base.mkdir(parents=True,exist_ok=True);torch.set_num_threads(1)
    t=time.perf_counter();normal=d.fit_normalization(legacy['data'],legacy['folds']['train'])
    # Actual constructor and strict public-weight load, without CUDA or optimizer updates.
    encoder=torch.hub.load(legacy['d2']['repo'],'dinov2_vits14',source='local',pretrained=False)
    state=torch.load(legacy['d2']['weight'],map_location='cpu',weights_only=False);encoder.load_state_dict(state,strict=True)
    origin=inspect.getfile(type(encoder));Path(origin).resolve().relative_to(Path(legacy['d2']['repo']).resolve());params={}
    # Constructor coverage for every actual arm, isolated from other project model namespaces.
    for arm in c.JOBS:
        head=m.Readout(arm);params[arm]=sum(p.numel() for p in head.parameters())
    for group in [('B0','B1','Q1','Q2','Q3'),('G1','G2','G3'),('S1','S2','S3')]:
        if len({params[x] for x in group})!=1:raise RuntimeError('matched trainable capacity mismatch')
    contract=dict(config=c.CONFIG,source=source,data=str(legacy['data']),d2=legacy['d2'],
        folds=legacy['folds'],normalization=normal,input_files=rows,headers=headers,
        environment=dict(python=platform.python_version(),torch=torch.__version__,numpy=np.__version__,scipy=scipy.__version__),
        cpu_preparation=dict(seconds=time.perf_counter()-t,strict_public_weights_loaded=True,model_origin=origin,
            trainable_parameters=params),gpu_snapshot=snapshot,resources=resources,
        gsd_source='https://www.isprs.org/resources/datasets/benchmarks/UrbanSemLab/2d-sem-label-potsdam.aspx',
        observed_at=c.now(),status='CPU_PREPARED_GPU_PROFILE_PENDING',sealed_splits_opened=False)
    c.write(base/'contract.json',contract,once=True)
    estimate=sum(2*n*4 for n in params.values())
    c.write(base/'budget.json',dict(new_full_jobs=11,new_full_updates=88000,original_a0_updates=4000,
        new_a_spatial_updates=4000,first_wave_total_updates=96000,
        maximum_profile_disposable_updates=len(c.PROFILES)*len(c.CONFIG['profile_candidates'])*(c.CONFIG['profile_warmup']+c.CONFIG['profile_measured']),full_endpoint_bytes_estimate=estimate,
        cpu_preparation_updates=0,new_target_optimization_updates=0,wall_time='PROFILE_PENDING'),once=True)
    print('CPU_PREPARED_GPU_PROFILE_PENDING',base,flush=True)

def status(base):
    base=Path(base);out=dict(base=str(base),observed_at=c.now(),server_state='only_existing_receipts_are_reported')
    for name in ('contract','profile_complete','train_complete','profile_first_failure','train_first_failure','blocked_routes'):
        p=base/(name+'.json')
        if p.exists():out[name]=c.read(p)
    for gpu in (0,1):
        p=base/('heartbeat_gpu%s.json'%gpu)
        if p.exists():out['heartbeat_gpu'+str(gpu)]=c.read(p)
    # Keep terminal output small: full contract remains on server/GitHub compact export.
    if 'contract' in out:
        out['contract']={k:out['contract'][k] for k in ('status','source','observed_at')}
    print(__import__('json').dumps(out,ensure_ascii=False,indent=2))

def main():
    p=argparse.ArgumentParser(description='No implicit downloads/installs/retries; physical GPUs0/1 only.')
    p.add_argument('action',choices=['prepare','profile','run','pipeline','worker','status','summarize','export','publish','a-spatial','a-spatial-worker'])
    p.add_argument('--base',default=str(c.ROOT/'records'/c.NAME));p.add_argument('--gpu',type=int,choices=[0,1])
    p.add_argument('--kind',choices=['dino2','dino3'])
    p.add_argument('--phase',choices=['profile','train','calibration','screen','outer'],default='profile')
    args=p.parse_args();base=Path(args.base)
    if args.action!='status':
        base.resolve().relative_to(c.ROOT/'records')
        for rel in ('cache/torch','cache/cuda'):(base/rel).mkdir(parents=True,exist_ok=True)
        import tempfile
        temporary=c.ipc_tmpdir(base);Path(temporary).mkdir(parents=True,exist_ok=True);tempfile.tempdir=temporary
        os.environ.update(TMPDIR=temporary,TEMP=temporary,TMP=temporary,TORCH_HOME=str(base/'cache/torch'),CUDA_CACHE_PATH=str(base/'cache/cuda'))
    if args.action=='pipeline':
        from .controller import run
        from .report import export
        from .publish import publish
        base.mkdir(parents=True,exist_ok=True)
        c.write(base/'pipeline_started.json',dict(observed_at=c.now(),pid=os.getpid()),once=True)
        try:
            prepare(base)
            run(base,'profile')
            run(base,'train')
        except BaseException:
            import traceback
            c.write(base/'pipeline_first_failure.json',dict(traceback=traceback.format_exc(),observed_at=c.now()),once=True)
            try:export(base)
            except Exception:pass
            raise
        export(base)
        try:publish(base)
        except Exception as exc:c.write(base/'upload_pending.json',dict(status='UPLOAD_FAILED_NO_RECOMPUTE',error=type(exc).__name__,observed_at=c.now()))
    elif args.action=='prepare':prepare(base)
    elif args.action in ('profile','run'):
        from .controller import run
        run(base,'profile' if args.action=='profile' else 'train')
        if args.action=='run':
            from .report import export
            export(base)
            try:
                from .publish import publish
                publish(base)
            except Exception as exc:
                c.write(base/'upload_pending.json',dict(status='UPLOAD_FAILED_NO_RECOMPUTE',error=type(exc).__name__,observed_at=c.now()))
    elif args.action=='worker':
        try:
            from .engine import worker
            worker(base,args.gpu)
        except BaseException:
            import traceback
            c.write(base/('worker_first_failure_gpu%s.json'%args.gpu),dict(traceback=traceback.format_exc(),pid=os.getpid(),observed_at=c.now()),once=True)
            raise
    elif args.action=='status':status(base)
    elif args.action=='a-spatial':
        from .spatial import run
        run(base,args.phase)
    elif args.action=='a-spatial-worker':
        from .spatial import execute
        execute(base,args.kind,args.phase)
    elif args.action=='publish':
        from .report import export
        from .publish import publish
        export(base);publish(base)
    else:
        from .report import summarize,export
        (summarize if args.action=='summarize' else export)(base)
