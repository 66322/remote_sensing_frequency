import random
import time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import torch
from scipy.ndimage import binary_dilation
from . import common as c
from . import data as d

def confusion(pred,truth,mask):
    cm=np.zeros((6,6),np.int64)
    for y in range(0,len(truth),256):
        a,b,m=truth[y:y+256],pred[y:y+256],mask[y:y+256]
        v=m&(a<6)
        cm+=np.bincount(a[v].astype(np.int64)*6+b[v],minlength=36).reshape(6,6)
    return cm

def edges(y,valid,cls=None):
    a=y if cls is None else y==cls;out=np.zeros(y.shape,bool)
    z=(a[1:]!=a[:-1])&valid[1:]&valid[:-1];out[1:]|=z;out[:-1]|=z
    z=(a[:,1:]!=a[:,:-1])&valid[:,1:]&valid[:,:-1];out[:,1:]|=z;out[:,:-1]|=z
    return out

def count_reference(full,border=None,tolerance=None):
    b=c.CONFIG['border'] if border is None else border
    r=c.CONFIG['boundary_tolerance_px'] if tolerance is None else tolerance
    h,w=full.shape;valid=np.zeros((h,w),bool);valid[b:h-b,b:w-b]=True;valid&=full<6
    # Prevent ignore holes from creating artificial correctly matched contours.
    yy,xx=np.mgrid[-r:r+1,-r:r+1];disk=xx*xx+yy*yy<=r*r
    safe=valid & ~binary_dilation(full>=6,structure=disk)
    boundary=binary_dilation(edges(full,valid),structure=disk)&safe
    def one(cls):
        e=edges(full,valid,cls)&safe
        return e,binary_dilation(e,structure=disk),int(e.sum())
    import os
    with ThreadPoolExecutor(max_workers=int(os.getenv('POST_M2_COUNT_THREADS',str(c.CONFIG['counter_threads'])))) as pool:
        truth=list(pool.map(one,range(6)))
    return dict(valid=valid,safe=safe,disk=disk,boundary=boundary,truth=truth)

def counts(pred,full,nb,roi,border=None,tolerance=None,reference=None):
    ref=count_reference(full,border,tolerance) if reference is None else reference
    valid,safe,disk,boundary=(ref[n] for n in ('valid','safe','disk','boundary'))
    region=np.zeros(full.shape,bool)
    if roi is not None:
        y,x,s=roi;region[y:y+s,x:x+s]=True
    result=dict(full=confusion(pred,full,valid),nb=confusion(pred,nb,valid),
        roi=confusion(pred,full,valid&region),healthy=confusion(pred,full,valid&~region),
        boundary_region=confusion(pred,full,boundary),nonboundary=confusion(pred,full,valid&~boundary))
    def one(cls):
        a=edges(pred,valid,cls)&safe;b,near_b,total_b=ref['truth'][cls]
        return [int((a&near_b).sum()),int(a.sum()),
            int((b&binary_dilation(a,structure=disk)).sum()),total_b]
    # Bounded CPU-only consumers; all counters consume the same one prediction.
    import os
    with ThreadPoolExecutor(max_workers=int(os.getenv('POST_M2_COUNT_THREADS',str(c.CONFIG['counter_threads'])))) as pool:boundary_counts=list(pool.map(one,range(6)))
    result={n:c.metrics(v) for n,v in result.items()};result['boundary_counts']=boundary_counts
    result['boundary_f1']=boundary_f1(boundary_counts)
    return result

def boundary_f1(raw):
    a=np.asarray(raw,np.int64)[:5].sum(0);mp,npred,mt,ntruth=map(int,a)
    if not npred or not ntruth:return None
    p=mp/npred;r=mt/ntruth
    return 0.0 if p+r==0 else float(200*p*r/(p+r))

def pool(rows):
    out={}
    for n in ('full','nb','roi','healthy','boundary_region','nonboundary'):
        out[n]=c.metrics(sum((np.asarray(x[n]['cm'],np.int64) for x in rows),np.zeros((6,6),np.int64)))
    out['boundary_counts']=sum((np.asarray(x['boundary_counts'],np.int64) for x in rows),np.zeros((6,4),np.int64)).tolist()
    out['boundary_f1']=boundary_f1(out['boundary_counts']);return out

def predict(encoder,patch,model,rgb,dsm,valid,batch_size,extract):
    h,w=rgb.shape[:2];s=c.CONFIG['crop'];stride=c.CONFIG['stride']
    axis=lambda n:sorted(set(list(range(0,n-s+1,stride))+[n-s]))
    positions=[(y,x) for y in axis(h) for x in axis(w)]
    t=time.perf_counter();score=torch.zeros((6,h,w),device='cuda',dtype=torch.float32)
    coverage=torch.zeros((h,w),device='cuda',dtype=torch.int16)
    model.eval();cpu_pack=0.;marks=[]
    with torch.inference_mode():
        for first in range(0,len(positions),batch_size):
            use=positions[first:first+batch_size];p=time.perf_counter()
            packed={n:torch.from_numpy(np.stack([a[y:y+s,x:x+s] for y,x in use])).pin_memory()
                for n,a in (('rgb',rgb),('dsm',dsm),('valid',valid))}
            cpu_pack+=time.perf_counter()-p;events=[torch.cuda.Event(enable_timing=True) for _ in range(5)]
            events[0].record();x=packed['rgb'].permute(0,3,1,2).to('cuda',non_blocking=True).float()/255
            z=packed['dsm'][:,None].to('cuda',non_blocking=True);v=packed['valid'][:,None].to('cuda',non_blocking=True)
            events[1].record();feat=extract(encoder,x,patch);events[2].record()
            with torch.autocast('cuda',dtype=torch.bfloat16):pred=model(feat,x,z,v)
            events[3].record()
            for j,(y,x0) in enumerate(use):
                score[:,y:y+s,x0:x0+s].add_(pred[j]);coverage[y:y+s,x0:x0+s].add_(1)
            events[4].record();marks.append(events)
        out=score.argmax(0).byte().cpu().numpy();torch.cuda.synchronize()
    if bool((coverage==0).any()):raise RuntimeError('sliding window coverage hole')
    result=dict(total_seconds=time.perf_counter()-t,cpu_pack_seconds=cpu_pack,windows=len(positions))
    for i,name in enumerate(('h2d','encoder','decoder','stitch')):
        result[name+'_seconds']=sum(e[i].elapsed_time(e[i+1]) for e in marks)/1000
    del score,coverage;return out,result

def panel(contract,encoder,patch,model,extract,split,batch_size,base,job,step,heartbeat,profile=None):
    if split not in ('calibration','outer'):raise ValueError('sealed splits prohibited')
    per={n:[] for n in c.CONDITIONS};bytile={};started=time.perf_counter();pending=[]
    # CPU counters overlap the next GPU prediction; at most two compact predictions in flight.
    pooler=ThreadPoolExecutor(max_workers=1)
    def collect(entry):
        tile,name,future,timing=entry;t=time.perf_counter();row,seconds=future.result()
        timing.update(counts_seconds=seconds,counter_backpressure_seconds=time.perf_counter()-t)
        row['timing']=timing;bytile[tile][name]=row;per[name].append(row)
        c.write(base/'jobs'/job/('%s_%s_%s_%s.json'%(split,step,tile,name)),row,once=True)
    def count_async(pred,full,nb,roi,reference):
        t=time.perf_counter();row=counts(pred,full,nb,roi,reference=reference.result());return row,time.perf_counter()-t
    for tile in contract['folds'][split]:
        heartbeat(stage='evaluation_loading',job=job,tile=tile,step=step)
        t=time.perf_counter();item=d.load_tile(contract['data'],tile,contract['normalization']['scale']);load_seconds=time.perf_counter()-t
        bytile[tile]={}
        # Reuse GT boundaries/dilations across five conditions; overlap one-time construction with GPU work.
        reference=pooler.submit(count_reference,item['full'])
        for name in c.CONDITIONS:
            heartbeat(stage='evaluation',job=job,tile=tile,condition=name,step=step)
            t=time.perf_counter();rgb,dsm,roi=d.condition(item['rgb'],item['dsm'],name,tile);prep=time.perf_counter()-t
            observed_valid=d.condition_valid(item['height_valid'],name,roi)
            pred,timing=predict(encoder,patch,model,rgb,dsm,observed_valid,batch_size,extract)
            if profile and timing['total_seconds']/timing['windows'] > 2.5*profile['evaluation']['total_seconds']/profile['evaluation']['windows']:
                raise RuntimeError('evaluation throughput >2.5x profile; stop and inspect resource contention')
            timing.update(input_load_seconds=load_seconds,condition_seconds=prep)
            pending.append((tile,name,pooler.submit(count_async,pred,item['full'],item['nb'],roi,reference),timing))
            if len(pending)>=2:collect(pending.pop(0))
            del pred,rgb,dsm
        del item
    try:
        for entry in pending:collect(entry)
    finally:pooler.shutdown(wait=True,cancel_futures=True)
    return dict(split=split,step=step,tiles=bytile,pooled={n:pool(rows) for n,rows in per.items()},seconds=time.perf_counter()-started)

def objective(arm,panel):
    p=panel['pooled']
    if arm.startswith('S'):
        value=p['clean']['boundary_f1']
        if value is None:raise RuntimeError('boundary score undefined')
        return value
    if arm.startswith('G'):return p['dsm_shift']['full']['fg5']
    if arm.startswith('Q'):return (p['dsm_shift']['full']['fg5']+p['rgb_blur']['full']['fg5'])/2
    return p['clean']['full']['fg5']
