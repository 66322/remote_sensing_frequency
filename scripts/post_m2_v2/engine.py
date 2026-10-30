import gc
import json
import os
import statistics
import time
from pathlib import Path
import numpy as np
import torch
from torch.nn import functional as F
import post_m2_a0 as a0
from . import common as c
from . import data as d
from . import evaluate as ev
from .model import Readout

def close_loader(loader,stream):
    # Do not leave persistent data-loader processes between profile candidates/jobs.
    if stream is not None and hasattr(stream,'_shutdown_workers'):stream._shutdown_workers()
    del stream,loader;gc.collect()

def update(encoder,patch,model,opt,batch,micro,arm,rows=None):
    opt.zero_grad(set_to_none=True);denom=int(batch['valid_count'].sum())
    if denom<=0:raise RuntimeError('all-ignored batch')
    loss_sum=torch.zeros((),device='cuda');group=torch.zeros(6,device='cuda');events=[]
    for first in range(0,16,micro):
        marks=[torch.cuda.Event(enable_timing=True) for _ in range(5)];marks[0].record()
        x=batch['rgb'][first:first+micro].to('cuda',non_blocking=True).float()/255
        z=batch['dsm'][first:first+micro].to('cuda',non_blocking=True)
        v=batch['valid'][first:first+micro].to('cuda',non_blocking=True)
        y=batch['gt'][first:first+micro].to('cuda',non_blocking=True).long()
        modes=torch.zeros(len(x),device='cuda',dtype=torch.long)
        if rows is not None:x,z,modes=d.damage(x,z,rows[first:first+micro])
        marks[1].record();feat=a0.extract(encoder,x,patch);marks[2].record()
        with torch.autocast('cuda',dtype=torch.bfloat16):logits=model(feat,x,z,v)
        pixel=F.cross_entropy(logits,y,reduction='none',ignore_index=255)
        loss=pixel.sum()/denom;loss.backward();loss_sum+=loss.detach()
        sample=pixel.detach().flatten(1).sum(1)/(y<6).flatten(1).sum(1).clamp_min(1)
        group[:3].scatter_add_(0,modes,sample);group[3:].scatter_add_(0,modes,torch.ones_like(sample))
        marks[3].record();events.append(marks)
    norm=torch.nn.utils.clip_grad_norm_(model.parameters(),c.CONFIG['clip_norm'],foreach=True)
    opt.step();events[-1][4].record()
    return loss_sum.detach(),group.detach(),norm.detach(),events

def timings(events):
    out=dict(h2d=0.,encoder=0.,decoder_backward=0.,optimizer=0.)
    for e in events:
        for i,n in enumerate(('h2d','encoder','decoder_backward')):out[n]+=e[i].elapsed_time(e[i+1])/1000
    e=events[-1];out['optimizer']=e[3].elapsed_time(e[4])/1000;return out

def run_profile(contract,encoder,patch,arrays,arm,base,heartbeat):
    if (base/'profiles'/(arm+'.json')).exists():raise RuntimeError('profile already recorded; no duplicate disposable updates')
    torch.set_num_threads(1);c.seed_all();start=time.perf_counter();candidates=[];resources=a0.resource_snapshot()
    selected_model=None
    for workers,micro in c.CONFIG['profile_candidates']:
        if workers>resources['max_loader_workers_per_gpu']:continue
        if time.perf_counter()-start>c.CONFIG['profile_timeout_seconds']:raise RuntimeError('bounded profile time exceeded')
        heartbeat(stage='profile',job=arm,workers=workers,micro=micro)
        c.seed_all();model=Readout(arm).cuda();opt=torch.optim.AdamW(model.parameters(),lr=c.CONFIG['lr'],weight_decay=c.CONFIG['weight_decay'])
        nsteps=c.CONFIG['profile_warmup']+c.CONFIG['profile_measured']
        loader=d.loader(arrays,contract['folds']['train'],workers,16*nsteps);stream=iter(loader)
        torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();samples=[];segments=[]
        try:
            for step in range(nsteps):
                if time.perf_counter()-start>c.CONFIG['profile_timeout_seconds']:raise RuntimeError('bounded profile time exceeded')
                t=time.perf_counter();batch=next(stream);wait=time.perf_counter()-t;t=time.perf_counter()
                loss,group,norm,events=update(encoder,patch,model,opt,batch,micro,arm,d.exposure(step) if arm.startswith('Q') else None)
                torch.cuda.synchronize()
                if not bool(torch.isfinite(loss)) or not bool(torch.isfinite(norm)):raise RuntimeError('nonfinite real profile update')
                compute=time.perf_counter()-t
                if step>=c.CONFIG['profile_warmup']:samples.append(dict(wait=wait,compute=compute,total=wait+compute));segments.append(timings(events))
            candidates.append(dict(workers=workers,micro=micro,steps=nsteps,warmup=c.CONFIG['profile_warmup'],measured=c.CONFIG['profile_measured'],
                median_seconds=statistics.median(x['total'] for x in samples),
                median_wait_seconds=statistics.median(x['wait'] for x in samples),
                segment_means={n:statistics.mean(x[n] for x in segments) for n in segments[0]},
                peak_allocated=torch.cuda.max_memory_allocated(),peak_reserved=torch.cuda.max_memory_reserved()))
        finally:close_loader(loader,stream)
        del model,opt;torch.cuda.empty_cache()
    if not candidates:raise RuntimeError('no supported throughput candidate')
    selected=min(candidates,key=lambda x:x['median_seconds'])
    if selected['median_wait_seconds']>max(.05,selected['median_seconds']*.5):
        c.write(base/'profiles'/(arm+'_resource_gap.json'),dict(candidates=candidates,selected=selected,
            reason='data waiting dominates even fastest measured configuration',observed_at=c.now()),once=True)
        raise RuntimeError('resource optimization required before formal queue: input wait dominates')
    heartbeat(stage='profile_evaluation',job=arm)
    c.seed_all();model=Readout(arm).cuda();tile=contract['folds']['train'][0];item=arrays[tile]
    pred,timing=ev.predict(encoder,patch,model,item['rgb'],item['dsm'],item['height_valid'],16,a0.extract)
    t=time.perf_counter();ev.counts(pred,item['full'],item['nb'],None);timing['counts_seconds']=time.perf_counter()-t
    import resource
    result=dict(status='REAL_PATH_PROFILE_PASSED',profile_mode='minimal_sanity_timing',timing_scope='indicative short check; not a configuration search or precise benchmark',arm=arm,observed_at=c.now(),source=contract['source'],
        candidates=candidates,selected=selected,evaluation=timing,wall_seconds=time.perf_counter()-start,
        disposable_updates=sum(x['steps'] for x in candidates),resources=resources,
        parameter_count=sum(p.numel() for p in model.parameters()),
        endpoint_bytes_estimate=2*sum(p.numel()*p.element_size() for p in model.parameters()),
        worker_lifetime_cpu_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    c.write(base/'profiles'/(arm+'.json'),result,once=True);del pred,model;return result

def train(contract,encoder,patch,arrays,arm,base,heartbeat):
    folder=base/'jobs'/arm;folder.mkdir(parents=True,exist_ok=True)
    c.write(folder/'started.json',dict(observed_at=c.now(),source=contract['source'],pid=os.getpid()),once=True)
    prof=c.read(base/'profiles'/(c.PROFILE_FOR[arm]+'.json'));cfg=c.read(base/'execution_tuning.json')['paths'][c.PROFILE_FOR[arm]]
    replay_rows=None;permutation=None
    if arm=='Q3':
        rows=c.read(base/'jobs/Q2/exposure.json')['rows'];replay_rows,permutation=d.replay(rows)
        c.write(folder/'replay_binding.json',dict(source='Q2/exposure.json',permutation=permutation,
            equality='exact_multiset_of_damage_descriptors_with_time_permuted'),once=True)
    c.seed_all();model=Readout(arm).cuda();model.train();torch.cuda.reset_peak_memory_stats()
    opt=torch.optim.AdamW(model.parameters(),lr=c.CONFIG['lr'],weight_decay=c.CONFIG['weight_decay'],betas=tuple(c.CONFIG['adam_betas']))
    loader=d.loader(arrays,contract['folds']['train'],cfg['workers'],16*c.CONFIG['updates']);stream=iter(loader)
    start=time.perf_counter();train_seconds=0.;waits=[];losses=[];history=[];panels={};exposures=[];p_rgb=.5;rolling=torch.zeros(6,device='cuda')
    logsum=torch.zeros((),device='cuda');event_samples=[];last_log=start
    try:
        for step in range(1,c.CONFIG['updates']+1):
            t=time.perf_counter();batch=next(stream);wait=time.perf_counter()-t;waits.append(wait)
            rows=None
            if arm.startswith('Q'):
                rows=replay_rows[step-1] if arm=='Q3' else d.exposure(step-1,p_rgb if arm=='Q2' else .5)
                exposures.append(rows)
            t=time.perf_counter();loss,group,norm,events=update(encoder,patch,model,opt,batch,cfg['micro'],arm,rows)
            logsum+=loss;rolling+=group;train_seconds+=time.perf_counter()-t+wait
            if step==1 or step%100==0:
                torch.cuda.synchronize();elapsed=time.perf_counter()-last_log;count=1 if step==1 else 99 if step==100 else 100
                values=torch.cat((logsum[None],rolling,norm[None])).cpu().tolist()
                if not all(np.isfinite(values)):raise RuntimeError('nonfinite training loss/gradient')
                mean=values[0]/count;losses.append(mean)
                if arm=='Q2':
                    # Training-only losses; no new forward, calibration or outer feedback.
                    rgb_loss=values[2]/max(values[5],1);dsm_loss=values[3]/max(values[6],1)
                    if values[5] and values[6]:p_rgb=float(np.clip(rgb_loss/max(rgb_loss+dsm_loss,1e-8),.25,.75))
                record=dict(step=step,loss=mean,wall_since_last_log=elapsed,mean_data_wait=float(np.mean(waits)),
                    last_sample_segments=timings(events),p_rgb=p_rgb,gradient_norm=values[-1],
                    peak_allocated=torch.cuda.max_memory_allocated(),peak_reserved=torch.cuda.max_memory_reserved())
                with (folder/'trajectory.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(record)+'\n')
                history.append(record);heartbeat(stage='training',job=arm,**record)
                if step>=100 and elapsed/count>c.CONFIG['slowdown_factor']*cfg['median_seconds']:
                    raise RuntimeError('training >2.5x profile; stop affected dispatch for resource diagnosis')
                logsum.zero_();rolling.zero_();waits=[];last_log=time.perf_counter()
            if step in c.CONFIG['calibration_steps']:
                target=folder/('head_%s.pt'%step)
                torch.save(dict(arm=arm,step=step,state=model.state_dict(),source=contract['source'],config=c.CONFIG),target)
                panel=ev.panel(contract,encoder,patch,model,a0.extract,'calibration',16,base,arm,step,heartbeat,prof)
                panels[step]=panel;c.write(folder/('calibration_%s.json'%step),panel,once=True)
                model.train();last_log=time.perf_counter()
        if arm=='Q2':c.write(folder/'exposure.json',dict(rows=exposures,seed=42,schedule_update=100),once=True)
        if exposures:
            from collections import Counter
            total=Counter(str(r['mode']) for rows in exposures for r in rows)
            c.write(folder/'exposure_summary.json',dict(mode_counts=dict(total),samples=16*8000,
                exact_schedule='Q2/exposure.json' if arm=='Q3' else 'exposure.json' if arm=='Q2' else 'deterministically_regenerable_from_code_seed42',
                time_permutation='replay_binding.json' if arm=='Q3' else None),once=True)
        learned=len(losses)>2 and np.mean(losses[-3:])<np.mean(losses[:3])
        selected=max(panels,key=lambda k:(ev.objective(arm,panels[k]),-k))
        clean=panels[selected]['pooled']['clean']['full']['fg5']
        if not learned or (arm in ('B0','B1') and clean<c.CONFIG['baseline_min_clean_fg5']):
            result=dict(status='INVALID_LEARNING_NOT_SCIENTIFIC_NEGATIVE',arm=arm,learned=bool(learned),clean_fg5=clean,
                selected_step=selected,updates=8000,observed_at=c.now())
            c.write(folder/'result.json',result,once=True);return result
        state=torch.load(folder/('head_%s.pt'%selected),map_location='cpu',weights_only=False);model.load_state_dict(state['state'],strict=True)
        outer=ev.panel(contract,encoder,patch,model,a0.extract,'outer',16,base,arm,selected,heartbeat,prof)
        c.write(folder/'outer_selected.json',outer,once=True)
        # Final fixed-age audit is reused if it is the selected endpoint.
        if selected!=8000:
            state=torch.load(folder/'head_8000.pt',map_location='cpu',weights_only=False);model.load_state_dict(state['state'],strict=True)
            final=ev.panel(contract,encoder,patch,model,a0.extract,'outer',16,base,arm,8000,heartbeat,prof)
            c.write(folder/'outer_final.json',final,once=True)
        result=dict(status='COMPLETE',arm=arm,updates=8000,learned=True,selected_step=selected,clean_calibration_fg5=clean,
            selected_objective=ev.objective(arm,panels[selected]),source=contract['source'],observed_at=c.now(),
            wall_seconds=time.perf_counter()-start,training_submission_seconds=train_seconds,profile=prof['arm'],
            parameter_count=sum(p.numel() for p in model.parameters()))
        c.write(folder/'result.json',result,once=True);return result
    finally:close_loader(loader,stream)

def worker(base,gpu):
    import sys
    base=Path(base);contract=c.runtime_contract(base);torch.set_num_threads(1)
    _,device=a0.ensure_gpu('dino2')
    os.environ['POST_M2_COUNT_THREADS']=str(min(c.CONFIG['counter_threads'],max(1,a0.resource_snapshot()['effective_cpu_cores']//4)))
    def heartbeat(**v):c.write(base/('heartbeat_gpu%s.json'%gpu),dict(observed_at=c.now(),pid=os.getpid(),**v))
    heartbeat(stage='loading_shared_model_and_fit_tiles')
    t=time.perf_counter();arrays,loading=d.resident(contract);encoder,patch=a0.load_encoder(dict(d2=contract['d2']),'dino2')
    loading.update(model_and_data_wall_seconds=time.perf_counter()-t,gpu=gpu,pid=os.getpid())
    c.write(base/('worker_gpu%s.json'%gpu),loading)
    print('WORKER_READY',gpu,flush=True)
    for line in sys.stdin:
        task=json.loads(line);arm=task['arm'];heartbeat(stage='task_started',job=arm,task_id=task['id'])
        result=(run_profile if task['phase']=='profile' else train)(contract,encoder,patch,arrays,arm,base,heartbeat)
        c.write(base/'tasks'/(task['id']+'.json'),result,once=True)
        gc.collect();torch.cuda.empty_cache();heartbeat(stage='idle',last_job=arm)
