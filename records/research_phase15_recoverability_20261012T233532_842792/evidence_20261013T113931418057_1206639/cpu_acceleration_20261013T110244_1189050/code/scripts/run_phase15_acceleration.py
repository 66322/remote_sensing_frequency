"""Versioned CPU-only remaining-case takeover, preserving original scientific binding."""
import argparse
import concurrent.futures as futures
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time

CACHE={}


def setup(base,attempt):
    global BASE,ATTEMPT
    BASE,ATTEMPT=Path(base),Path(attempt)
    sys.path.insert(0,str(BASE/'code/scripts'));sys.path.insert(0,str(ATTEMPT/'code/scripts'))


def compute(key):
    from phase15_common import read,validate,binding,case
    from prepare_phase15 import load_mask,old_prediction
    from analyze_phase15 import current
    from phase15_fast_counts import fast_oracle_evidence
    import numpy as np
    tile,i,family=key;p=validate(BASE)
    if CACHE.get('tile')!=tile:
        from post_ab_n1_data import Loader
        item=Loader(Path(p['root']),read(BASE/'source_plan.json'))(tile,True)
        thresholds=read(BASE/'calibration.json')['thresholds'];fields={}
        for name in ('dsm_mean','dsm_variance','dsm_gradient'):
            with np.load(BASE/'features'/tile/(name+'.npz'),allow_pickle=False) as z:
                fields[name]=np.digitize(z['value'],thresholds[name]).astype(np.uint8)
        CACHE.clear();CACHE.update(tile=tile,item=item,fields=fields,clean=old_prediction(BASE,'S1',tile),
            dsm=current(BASE,case('DSM',tile)))
    item=CACHE['item'];mask,mb=load_mask(BASE,tile,i,family)
    predictions=[old_prediction(BASE,'S1',tile,i,family),current(BASE,case('S13',tile,'intact',i,family)),
        current(BASE,case('R16',tile,'intact',i,family)),CACHE['dsm'],old_prediction(BASE,'RGB',tile,i,family)]
    entropy=current(BASE,case('S1',tile,'intact',i,family),'entropy')
    from scipy.ndimage import uniform_filter
    op=item['optical'].copy();op[mask]=0
    zero=uniform_filter(np.all(op==0,axis=-1).astype(np.float32),size=9,mode='reflect');del op
    fields=dict(CACHE['fields'],rgb_zero_fraction=np.digitize(zero,(.25,.5,.75)).astype(np.uint8));del zero
    result=fast_oracle_evidence(item['noboundary_gt'],CACHE['clean'],predictions,mask,entropy,fields)
    return dict(binding=binding(BASE),tile=tile,realization=i,family=family,mask_sha256=mb['canonical_sha256'],
        result=result,optimizer_updates=0)


def worker(key):
    from phase15_common import write,sha,now
    row=compute(key);name='%s_%02d_%s'%key;target=BASE/'analysis/D'/(name+'.json')
    if target.exists():raise RuntimeError('refuse overwrite of completed D case')
    row.update(observed_at=now(),acceleration=dict(directory=str(ATTEMPT),code_manifest_sha256=sha(ATTEMPT/'code_manifest.json')))
    write(target,row);return name,sha(target)


def main(base,attempt):
    import fcntl
    setup(base,attempt)
    tick=time.monotonic()
    while not (ATTEMPT/'launch.json').exists():
        if time.monotonic()-tick>30:raise RuntimeError('launcher receipt missing; preserve staged takeover')
        time.sleep(.1)
    from phase15_common import read,write,sha,now,binding,validate,verify_code,TILES,FAMILIES
    from prepare_phase15 import load_mask
    from d30_common import live_owned
    with (BASE/'controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        verify_code(BASE);p=validate(BASE);manifest=read(ATTEMPT/'code_manifest.json')
        for n,d in manifest['files'].items():
            if sha(ATTEMPT/'code'/n)!=d:raise RuntimeError('acceleration snapshot changed')
        state=read(BASE/'queue_status.json')
        if state['status']!='CPU_ACCELERATION_REGISTERED':raise RuntimeError('not registered for takeover')
        state.update(controller_pid=os.getpid(),error=None,automatic_retry=False)
        def report(status):
            state.update(status=status,observed_at=now());write(BASE/'queue_status.json',state)
        try:
            keys=[(t,i,f) for t in TILES for i in range(1,21) for f in FAMILIES]
            rows={};done=[];pending=[]
            for k in keys:
                name='%s_%02d_%s'%k;path=BASE/'analysis/D'/(name+'.json')
                if path.exists():
                    row=read(path);mask,mb=load_mask(BASE,*k)
                    if row['binding']!=binding(BASE) or (row['tile'],row['realization'],row['family'])!=k or row['mask_sha256']!=mb['canonical_sha256'] or row['optimizer_updates']!=0:
                        raise RuntimeError('existing D case binding changed')
                    rows[name]=sha(path);done.append(k)
                else:pending.append(k)
            report('CPU_ACCELERATION_EQUIVALENCE_CHECK')
            # Compare against real completed original results, never replace them.
            selected=[]
            for family in ('pixel','matched'):
                candidates=[k for k in done if k[2]==family]
                if not candidates:raise RuntimeError('missing original reference for exact equality check')
                selected.append(candidates[0])
            proofs=[]
            for k in selected:
                candidate=compute(k);name='%s_%02d_%s'%k;path=BASE/'analysis/D'/(name+'.json')
                old=read(path)
                if candidate['result']!=old['result']:raise RuntimeError('real original vs fast statistics mismatch')
                proofs.append(dict(case=name,original_sha256=sha(path),all_result_fields_exact=True))
            CACHE.clear()
            write(ATTEMPT/'real_equivalence.json',dict(checks=proofs,passed=True,observed_at=now(),original_binding=binding(BASE)))
            report('CPU_ORACLE_AND_CONDITIONAL_COUNTS')
            count=len(rows);started=time.monotonic();workers=read(ATTEMPT/'takeover.json')['workers']
            with futures.ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn'),initializer=setup,initargs=(str(BASE),str(ATTEMPT))) as pool:
                active={};todo=iter(pending)
                def fill():
                    for _ in range(workers-len(active)):
                        k=next(todo,None)
                        if k is not None:active[pool.submit(worker,k)]=k
                fill()
                while active:
                    ready,_=futures.wait(active,timeout=5,return_when=futures.FIRST_COMPLETED)
                    for task in ready:
                        k=active.pop(task);name,digest=task.result();rows[name]=digest
                        write(BASE/'analysis/D/progress.json',dict(completed_cases=len(rows),total_cases=160,tile=k[0],realization=k[1],family=k[2],
                            observed_at=now(),parallel_workers=workers,preserved_completed_cases=count,
                            new_completed_cases=len(rows)-count,elapsed_accelerated_seconds=time.monotonic()-started))
                    fill();report('CPU_ORACLE_AND_CONDITIONAL_COUNTS')
                    if time.monotonic()-started>24*3600:raise RuntimeError('CPU acceleration technical timeout')
            receipt=BASE/'analysis/D/complete.json'
            if receipt.exists():
                saved=read(receipt)
                if saved['binding']!=binding(BASE) or saved['records']!=rows or saved['optimizer_updates']!=0:
                    raise RuntimeError('existing D completion receipt differs; preserve it')
            else:
                write(receipt,dict(binding=binding(BASE),records=rows,optimizer_updates=0,
                    completed_at=now(),acceleration_directory=str(ATTEMPT),real_equivalence_sha256=sha(ATTEMPT/'real_equivalence.json')))
            report('SUMMARIZING_ALL_FIVE_DIAGNOSTICS')
            with (ATTEMPT/'summary.log').open('x') as log:
                subprocess.run([sys.executable,'-u','-B',str(BASE/'code/scripts/summarize_phase15.py'),'--directory',str(BASE)],
                    env=os.environ.copy(),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=6*3600)
            state.update(summary_sha256=sha(BASE/'summary.json'),new_training_dispatched=False)
            report('PHASE15_COMPLETE_AWAITING_REVIEW');print('PHASE15_COMPLETE NO_AUTOMATIC_TRAINING',flush=True)
        except BaseException as exc:
            state.update(error=str(exc),new_training_dispatched=False)
            write(ATTEMPT/'failure.json',dict(error=str(exc),observed_at=now(),automatic_retry=False))
            report('TECHNICAL_FAILURE_HOLD');raise


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',type=Path,required=True);a.add_argument('--attempt',type=Path,required=True)
    x=a.parse_args();main(x.directory.resolve(),x.attempt.resolve())
