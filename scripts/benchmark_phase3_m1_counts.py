"""Independent CPU-only A/B probe. Does not alter a running experiment or its results."""
import argparse
import gc
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

_FORK_ENV=None
_FORK_FAST=False

def process_invoke(pair):
    """Linux fork inherits read-only arrays; task/result IPC contains only indices/digests."""
    c,original,r,d,tile,masks,health=_FORK_ENV
    i,j=pair
    z=fast_analyze(c,r[i],d[j],tile,masks[i],healthy_override=health[i]) if _FORK_FAST else original.analyze(r[i],d[j],tile,masks[i],healthy_override=health[i])
    return hashlib.sha256(json.dumps(z,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def fast_analyze(c,r,d,tile,mask=None,border=0,availability='both',healthy_override=None):
    """Same FP64 predictions; categorize ROIs in one histogram instead of three."""
    import numpy as np
    from scipy.special import softmax
    from scipy.ndimage import maximum_filter
    shape=r.shape[1:]
    if d.shape!=r.shape: raise ValueError('unmatched logits')
    if mask is None:
        mask=np.zeros(shape,bool) if availability=='both' else np.ones(shape,bool)
        healthy=~mask
    else:
        healthy=healthy_override if healthy_override is not None else ~maximum_filter(mask,size=17,mode='constant',cval=0).astype(bool)
    sums={s:{roi:{n:np.zeros((6,6,6),np.int64) for n in ('dsm','logit_mix','probability_mix')}
             for roi in ('all','healthy','damaged')} for s in ('full','noboundary')}
    for y in range(0,shape[0],128):
        stop=min(y+128,shape[0]); sl=slice(y,stop)
        rr=r[:,sl].astype(np.float64); dd=d[:,sl].astype(np.float64)
        if not np.isfinite(rr).all() or not np.isfinite(dd).all(): raise RuntimeError('nonfinite logits')
        pr=rr.argmax(0).astype(np.uint8); pd=dd.argmax(0).astype(np.uint8)
        if availability=='rgb_missing': mixed=prob=pd
        elif availability=='dsm_missing': mixed=prob=pr
        else:
            mixed=(.9*rr+.1*dd).argmax(0).astype(np.uint8)
            prob=(.9*softmax(rr,axis=0)+.1*softmax(dd,axis=0)).argmax(0).astype(np.uint8)
        valid=np.ones(pr.shape,bool)
        if border:
            yy=np.arange(y,stop)[:,None]; xx=np.arange(shape[1])[None,:]
            valid &= (yy>=border)&(yy<shape[0]-border)&(xx>=border)&(xx<shape[1]-border)
        # Two bits also handle overlap; no assumption that healthy/damaged partition all pixels.
        category=healthy[sl].astype(np.int64)+2*mask[sl].astype(np.int64)
        for scope in sums:
            gt=c.DATA[tile][scope+'_gt'][sl]; use=valid&(gt<6)
            shared=category[use]*216+gt[use].astype(np.int64)*36+pr[use].astype(np.int64)*6
            for name,pred in [('dsm',pd),('logit_mix',mixed),('probability_mix',prob)]:
                groups=np.bincount(shared+pred[use],minlength=4*216).reshape(4,6,6,6)
                sums[scope]['all'][name]+=groups.sum(0)
                sums[scope]['healthy'][name]+=groups[1]+groups[3]
                sums[scope]['damaged'][name]+=groups[2]+groups[3]
    out={}
    for scope,rois in sums.items():
        out[scope]={}
        for roi,systems in rois.items():
            result={}
            for name,j in systems.items():
                if not np.array_equal(j.sum((1,2)),next(iter(systems.values())).sum((1,2))): raise RuntimeError('joint support mismatch')
                result[name]=dict(joint=j.tolist(),cm=j.sum(1).tolist(),rgb_cm=j.sum(2).tolist(),flow=c.flow(j))
            out[scope][roi]=result
    return out

def cpu_limits():
    """Inspect v1 as well as v2; the experiment's older profile inspected v2 only."""
    affinity=len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else (os.cpu_count() or 1)
    found={}; quotas=[]; candidates=set()
    mounts=[Path(x) for x in ('/sys/fs/cgroup','/sys/fs/cgroup/cpu','/sys/fs/cgroup/cpu,cpuacct')]
    groups=[]
    if Path('/proc/self/cgroup').exists():
        for line in Path('/proc/self/cgroup').read_text().splitlines():
            _,controllers,group=line.split(':',2)
            if not controllers or 'cpu' in controllers.split(','): groups.append(group)
    for mount in mounts:
        candidates.add(mount)
        for group in groups:
            path=mount/group.lstrip('/')
            for node in (path,*path.parents):
                if node==mount or mount in node.parents: candidates.add(node)
    for path in sorted(candidates,key=str):
        for name in ('cpu.max','cpu.cfs_quota_us','cpu.cfs_period_us','cpu.stat'):
            f=path/name
            if f.exists(): found[str(f)]=f.read_text().strip()
        if (path/'cpu.max').exists():
            q,period=(path/'cpu.max').read_text().split()
            if q!='max': quotas.append(int(q)/int(period))
        if (path/'cpu.cfs_quota_us').exists() and (path/'cpu.cfs_period_us').exists():
            q=int((path/'cpu.cfs_quota_us').read_text()); period=int((path/'cpu.cfs_period_us').read_text())
            if q>0: quotas.append(q/period)
    return dict(affinity_cpus=affinity,effective_limit_cpus=min([affinity,*quotas]),files=found)

def memory_available():
    f=Path('/proc/meminfo')
    if not f.exists(): return 0
    available=next(int(x.split()[1])*1024 for x in f.read_text().splitlines() if x.startswith('MemAvailable:'))
    mounts=[Path('/sys/fs/cgroup'),Path('/sys/fs/cgroup/memory')]; groups=[]; candidates=set(mounts)
    if Path('/proc/self/cgroup').exists():
        for line in Path('/proc/self/cgroup').read_text().splitlines():
            _,controllers,group=line.split(':',2)
            if not controllers or 'memory' in controllers.split(','): groups.append(group)
    for mount in mounts:
        for group in groups:
            path=mount/group.lstrip('/')
            for node in (path,*path.parents):
                if node==mount or mount in node.parents: candidates.add(node)
    for path in candidates:
        for limit_name,used_name in (('memory.max','memory.current'),('memory.limit_in_bytes','memory.usage_in_bytes')):
            limit,used=path/limit_name,path/used_name
            if limit.exists() and used.exists() and limit.read_text().strip()!='max':
                available=min(available,max(0,int(limit.read_text())-int(used.read_text())))
    return available

def main():
    global _FORK_ENV,_FORK_FAST
    p=argparse.ArgumentParser(); p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--processes',action='store_true',help='Add read-only fork process pools instead of repeating thread scaling')
    args=p.parse_args()
    if args.processes and sys.platform!='linux': raise RuntimeError('read-only fork comparison requires Linux')
    base=args.directory.resolve()
    if base.name!='research_phase3_m1_recovery_20261015T164357_19327': raise RuntimeError('identified live run required')
    q=json.loads((base/'queue_status.json').read_text()); counts=q.get('rgb_cases_counted')
    done=sum(counts.values()) if counts is not None else None
    print('CURRENT',q['status'],'COUNTED',done,'/320','PENDING_CPU',q.get('pending_cpu'),flush=True)
    limits=cpu_limits(); print('CPU_LIMITS',json.dumps(limits,ensure_ascii=False),flush=True)
    if q['status']!='RUNNING' or done is None or done>=280:
        print('NO_BENCHMARK: finished or too near completion to justify a concurrent probe',flush=True); return
    current=json.loads((base/'resource_profile.json').read_text())['analysis_threads']
    if limits['effective_limit_cpus']<=current:
        print('NO_CONCURRENCY_EXPANSION: CPU quota does not exceed current thread count',flush=True); return
    required_gib=16 if args.processes else 12
    if memory_available()<required_gib*1024**3:
        print('NO_BENCHMARK: less than',required_gib,'GiB spare host/container RAM',flush=True); return
    pid=json.loads((base/'launch.json').read_text())['controller_pid']
    cmd=(Path('/proc')/str(pid)/'cmdline').read_bytes()
    if str(base).encode() not in cmd or b'control_phase3_m1.py' not in cmd: raise RuntimeError('controller PID no longer matches')
    # Import scientific routines in this separate CPU process; never attach to the live executor.
    for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[k]='1'
    os.environ['CUDA_VISIBLE_DEVICES']=''; os.environ['PYTHONDONTWRITEBYTECODE']='1'
    sys.path.insert(0,str(base/'code')); sys.path.insert(0,str(base/'code/scripts'))
    import numpy as np
    import phase3_m1_common as c
    import phase3_m1_numeric as original
    expected=json.loads((base/'code_manifest.json').read_text())['files']['scripts/phase3_m1_numeric.py']
    if hashlib.sha256((base/'code/scripts/phase3_m1_numeric.py').read_bytes()).hexdigest()!=expected: raise RuntimeError('original counter source changed')
    max_workers=min(32,int(limits['effective_limit_cpus'])-current)
    candidates=[n for n in (16,24,32) if n<=max_workers]
    if not candidates:
        print('NO_BENCHMARK: insufficient spare CPU quota for a 16-thread comparison',flush=True); return
    rng=np.random.default_rng(20261015); shape=(256,6000); tile='__benchmark_only__'
    r=[rng.integers(-12,13,size=(6,*shape),dtype=np.int16).astype(np.float32) for _ in range(4)]
    d=[rng.integers(-12,13,size=(6,*shape),dtype=np.int16).astype(np.float32) for _ in range(12)]
    full=rng.integers(0,6,size=shape,dtype=np.uint8); nb=full.copy(); nb[:,::17]=255
    c.DATA[tile]=dict(full_gt=full,noboundary_gt=nb)
    masks=[]; health=[]
    from scipy.ndimage import maximum_filter
    for i in range(4):
        mask=np.zeros(shape,bool); mask[:,i*1500:(i+1)*1500]=True
        masks.append(mask); health.append(~maximum_filter(mask,size=17,mode='constant',cval=0).astype(bool))
    warm='__benchmark_warmup__'
    c.DATA[warm]=dict(full_gt=full[:32,:128],noboundary_gt=nb[:32,:128])
    a=original.analyze(r[0][:,:32,:128],d[0][:,:32,:128],warm,masks[0][:32,:128],healthy_override=health[0][:32,:128])
    z=fast_analyze(c,r[0][:,:32,:128],d[0][:,:32,:128],warm,masks[0][:32,:128],healthy_override=health[0][:32,:128])
    if a!=z: raise RuntimeError('warmup evidence differs')
    c.DATA.pop(warm)
    jobs=[(i,j) for i in range(4) for j in range(12)]
    for arr in [*r,*d,full,nb,*masks,*health]: arr.flags.writeable=False
    _FORK_ENV=(c,original,r,d,tile,masks,health)
    def invoke(pair,fast):
        i,j=pair
        z=fast_analyze(c,r[i],d[j],tile,masks[i],healthy_override=health[i]) if fast else original.analyze(r[i],d[j],tile,masks[i],healthy_override=health[i])
        return hashlib.sha256(json.dumps(z,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    baseline=None; rows=[]
    configs=[('threads',False,n) for n in candidates]+[('threads',True,n) for n in candidates]
    if args.processes:
        import multiprocessing as mp
        import resource
        configs=[('threads',False,16)]+[("processes",fast,n) for fast in (False,True) for n in candidates if n in (16,32)]
        print('FORK_ARRAYS_READ_ONLY: only benchmark-owned children; no prediction-array IPC or live-run process access',flush=True)
    print('BENCH_BEGIN: synthetic 256x6000 strips, 4 cases x12 models; no model/data/GPU work',flush=True)
    try:
        for repeat in range(2):
            sequence=configs if repeat==0 else list(reversed(configs))
            for execution,fast,workers in sequence:
                gc.collect(); started=time.monotonic(); cpu_started=time.process_time()
                if execution=='threads':
                    with ThreadPoolExecutor(max_workers=workers) as pool: results=list(pool.map(lambda pair:invoke(pair,fast),jobs))
                    cpu_used=time.process_time()-cpu_started
                else:
                    _FORK_FAST=fast
                    before=resource.getrusage(resource.RUSAGE_CHILDREN); pool=mp.get_context('fork').Pool(workers)
                    try:
                        results=pool.map(process_invoke,jobs,chunksize=1)
                        pool.close(); pool.join()
                    except BaseException:
                        pool.terminate(); pool.join(); raise
                    after=resource.getrusage(resource.RUSAGE_CHILDREN)
                    cpu_used=(after.ru_utime+after.ru_stime)-(before.ru_utime+before.ru_stime)
                seconds=time.monotonic()-started
                if baseline is None: baseline=results
                if results!=baseline: raise RuntimeError('A/B integer evidence differs; reject optimization')
                row=dict(execution=execution,counter='grouped_roi' if fast else 'original',workers=workers,repeat=repeat,seconds=round(seconds,3),
                         cpu_cores=round(cpu_used/seconds,2),integer_evidence_exact=True)
                rows.append(row); print('BENCH',json.dumps(row),flush=True)
        medians=[]
        for execution,fast,workers in configs:
            values=[x['seconds'] for x in rows if x['execution']==execution and x['counter']==('grouped_roi' if fast else 'original') and x['workers']==workers]
            medians.append(dict(execution=execution,counter='grouped_roi' if fast else 'original',workers=workers,seconds=sum(values)/len(values)))
        ref=next(x['seconds'] for x in medians if x['execution']=='threads' and x['counter']=='original' and x['workers']==16)
        for row in medians: row['speedup_vs_original16']=round(ref/row['seconds'],3)
        print('BENCH_SUMMARY',json.dumps(medians),flush=True)
        print('PROBE_ONLY: live run was not restarted, signalled, modified or cleaned; benchmark children joined; synthetic scaling is not a full-tile ETA',flush=True)
    finally:
        c.DATA.pop(tile,None)
        _FORK_ENV=None

if __name__=='__main__': main()
