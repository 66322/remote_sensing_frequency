"""A spatial-readout extension; old A0 script, outputs and pair contract remain frozen."""
import argparse
import gc
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
import traceback

def a0_contract(a0,c):
    legacy=a0.contract(argparse.Namespace(root=str(c.ROOT)),require_d3=True)
    selected=os.getenv('POST_M2_A0_RECORDS')
    if selected:
        folder=Path(selected).resolve();folder.relative_to((c.ROOT/'records').resolve())
        if folder!=Path(legacy['out']).resolve():
            ready=c.read(folder/'repair_ready.json')
            if ready.get('scientific_source_commit')!='c22a046407daf42064cbb161429f2648c9b86d66':raise RuntimeError('repaired A0 scientific source differs')
            legacy['out']=folder
    return legacy

def execute(base,kind,phase):
    import numpy as np
    import torch
    import post_m2_a0 as a0
    from . import common as c
    from .model import SpatialProbe
    from .engine import close_loader
    base=Path(base);_,source=c.source();legacy=a0_contract(a0,c)
    a0.ensure_gpu(kind);torch.set_num_threads(1);c.seed_all()
    old=a0.read(legacy['out']/('profile_'+kind+'.json'))
    if old['code_commit']!='c22a046407daf42064cbb161429f2648c9b86d66':raise RuntimeError('A0 profile source mismatch')
    folder=base/'a_spatial'/kind;folder.mkdir(parents=True,exist_ok=True)
    c.write(folder/(phase+'_started.json'),dict(source=source,observed_at=c.now(),kind=kind,a0_source_run=str(legacy['out'])),once=True)
    encoder,patch=a0.load_encoder(legacy,kind);result=None
    if phase in ('profile','train'):
        arrays=a0.arrays(legacy,legacy['folds']['train']);history=[]
        if phase=='profile':
            start=time.perf_counter();candidates=[];resources=a0.resource_snapshot()
            # Reuse each encoder's accepted A0 tuning; no repeat configuration sweep.
            for workers,micro in [(old['selected_train']['workers'],old['selected_train']['micro'])]:
                if workers>resources['max_loader_workers_per_gpu']:continue
                c.seed_all();head=SpatialProbe().cuda();opt=torch.optim.AdamW(head.parameters(),lr=1e-4,weight_decay=.01)
                nsteps=c.CONFIG['profile_warmup']+c.CONFIG['profile_measured']
                loader=a0.loader(arrays,legacy['folds']['train'],workers,16*nsteps);stream=iter(loader);rows=[]
                torch.cuda.reset_peak_memory_stats()
                try:
                    for step in range(nsteps):
                        if time.perf_counter()-start>c.CONFIG['profile_timeout_seconds']:raise RuntimeError('spatial profile timeout')
                        t=time.perf_counter();batch=next(stream);a0.one_update(encoder,patch,head,opt,batch,micro);torch.cuda.synchronize()
                        if step>=c.CONFIG['profile_warmup']:rows.append(time.perf_counter()-t)
                    candidates.append(dict(workers=workers,micro=micro,median_seconds=statistics.median(rows),updates=nsteps,
                        peak_allocated=torch.cuda.max_memory_allocated(),peak_reserved=torch.cuda.max_memory_reserved()))
                finally:close_loader(loader,stream)
                del head,opt
            head=SpatialProbe().cuda();tile=arrays[legacy['folds']['train'][0]]
            pred,secs,n,timing=a0.predict_tile(encoder,patch,head,tile['rgb'],16)
            t=time.perf_counter();a0.cm_tile(pred,tile['nb']);timing['counts_seconds']=time.perf_counter()-t
            result=dict(status='REAL_SPATIAL_PROFILE_PASSED',profile_mode='minimal_sanity_timing',timing_scope='indicative short check; reuse original encoder tuning',kind=kind,source=source,candidates=candidates,
                selected=min(candidates,key=lambda x:x['median_seconds']),evaluation=dict(seconds=secs,windows=n,timing=timing),
                disposable_updates=sum(x['updates'] for x in candidates),observed_at=c.now())
        else:
            # The original pair has already run. This is a separately versioned 2x2 readout diagnostic.
            for k in ('dino2','dino3'):
                if a0.read(legacy['out']/k/'train_complete.json')['status']!='TRAINED_HEAD_ONLY':raise RuntimeError('complete original A0 pair first')
            profile=c.read(folder/'profile_result.json');cfg=profile['selected'];c.seed_all()
            head=SpatialProbe().cuda();opt=torch.optim.AdamW(head.parameters(),lr=1e-4,weight_decay=.01)
            loader=a0.loader(arrays,legacy['folds']['train'],cfg['workers'],16*2000);stream=iter(loader);t0=time.perf_counter()
            try:
                for step in range(1,2001):
                    loss=a0.one_update(encoder,patch,head,opt,next(stream),cfg['micro'])
                    if step==1 or step%100==0:
                        torch.cuda.synchronize();row=dict(step=step,loss=float(loss),seconds=time.perf_counter()-t0)
                        if not np.isfinite(row['loss']):raise RuntimeError('nonfinite spatial loss')
                        history.append(row);c.write(folder/'progress.json',row)
                        if step==500 and row['seconds']>2.5*500*cfg['median_seconds']:raise RuntimeError('spatial training slowdown')
                torch.save(dict(state=head.state_dict(),kind=kind,source=source,step=2000),folder/'head_2000.pt')
            finally:close_loader(loader,stream)
            c.write(folder/'trajectory.json',history,once=True)
            learned=statistics.median(x['loss'] for x in history[:5])>statistics.median(x['loss'] for x in history[-5:])
            result=dict(status='TRAINED_SPATIAL_HEAD' if learned else 'INVALID_PROBE',kind=kind,updates=2000,
                source=source,observed_at=c.now(),learned=learned,seconds=time.perf_counter()-t0)
    elif phase in ('calibration','outer'):
        from .model import SpatialProbe
        if c.read(folder/'train_result.json')['status']!='TRAINED_SPATIAL_HEAD':raise RuntimeError('spatial head not learned')
        if phase=='outer' and c.read(base/'a_spatial/screen.json')['status']!='READY_SPATIAL_OUTER':raise RuntimeError('spatial calibration gate closed')
        head=SpatialProbe().cuda();head.load_state_dict(torch.load(folder/'head_2000.pt',map_location='cpu',weights_only=False)['state'],strict=True)
        pooled=np.zeros((6,6),np.int64);rows=[]
        for tile in legacy['folds'][phase]:
            item=a0.arrays(legacy,[tile])[tile];pred,secs,n,timing=a0.predict_tile(encoder,patch,head,item['rgb'],16)
            cm=a0.cm_tile(pred,item['nb']);pooled+=cm;rows.append(dict(tile=tile,seconds=secs,**a0.metrics(cm)))
            c.write(folder/('progress_'+phase+'.json'),dict(tile=tile,done=len(rows),observed_at=c.now()))
        result=dict(status='EVALUATION_COMPLETE',kind=kind,phase=phase,tiles=rows,pooled=a0.metrics(pooled),source=source,observed_at=c.now())
    if result is None:raise ValueError(phase)
    c.write(folder/(phase+'_result.json'),result,once=True)

def run(base,phase):
    import fcntl
    import post_m2_a0 as a0
    from . import common as c
    from .controller import idle_gpus,stop_owned
    base=Path(base);base.resolve().relative_to(c.ROOT/'records');base.mkdir(parents=True,exist_ok=True)
    legacy=a0_contract(a0,c)
    if phase=='screen':
        rows=[c.read(base/'a_spatial'/k/'calibration_result.json') for k in ('dino2','dino3')]
        eligible=all(x['pooled']['nb_fg5_miou']>=50 for x in rows)
        c.write(base/'a_spatial/screen.json',dict(status='READY_SPATIAL_OUTER' if eligible else 'INVALID_PROBE',
            dino3_minus_dino2_pp=rows[1]['pooled']['nb_fg5_miou']-rows[0]['pooled']['nb_fg5_miou'],
            rule='both spatial heads learned and both inner fg5 >=50; independent of A0 linear positivity',observed_at=c.now()),once=True)
        return
    with (base/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);idle_gpus()
        for kind in ('dino2','dino3'):
            if c.read(legacy['out']/('profile_'+kind+'.json'))['code_commit']!='c22a046407daf42064cbb161429f2648c9b86d66':raise RuntimeError('original model checks missing')
        c.write(base/('a_spatial_'+phase+'_started.json'),dict(observed_at=c.now()),once=True)
        workers={};handles=[];entry=Path(__file__).resolve().parents[1]/'post_m2_multiroute.py';started=time.monotonic()
        try:
            for gpu,kind in enumerate(('dino2','dino3')):
                f=(base/('a_spatial_%s_%s.log'%(phase,kind))).open('x');handles.append(f)
                workers[gpu]=subprocess.Popen([sys.executable,'-u','-B',str(entry),'a-spatial-worker','--base',str(base),
                    '--kind',kind,'--phase',phase],stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,
                    env=c.env(gpu,base),start_new_session=True)
            while True:
                values=[p.poll() for p in workers.values()]
                if any(x is not None and x!=0 for x in values):raise RuntimeError('spatial pair first failure; inspect own original log')
                if all(x==0 for x in values):break
                if time.monotonic()-started>(720 if phase=='profile' else 24*3600):raise RuntimeError('spatial pair timeout')
                time.sleep(.5)
            c.write(base/('a_spatial_'+phase+'_complete.json'),dict(observed_at=c.now()),once=True)
        except BaseException:
            c.write(base/('a_spatial_'+phase+'_failure.json'),dict(traceback=traceback.format_exc(),observed_at=c.now()),once=True);raise
        finally:
            stop_owned(workers)
            for f in handles:f.close()
