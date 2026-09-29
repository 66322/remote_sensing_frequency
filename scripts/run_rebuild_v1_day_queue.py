"""Prepare, profile, freeze scope, then run the post-D21 portfolio on GPU0/1."""
import argparse
import concurrent.futures
import csv
from datetime import datetime
import fcntl
import os
from pathlib import Path
import queue
import random
import shutil
import subprocess
import sys
import threading
import time

import day_portfolio_common as p


def now():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def gpu_info():
    lines=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.used,utilization.gpu',
        '--format=csv,noheader,nounits'],text=True).splitlines()
    return {int(x[0]):dict(uuid=x[1],memory_mib=int(x[2]),utilization=int(x[3]))
        for x in ([v.strip() for v in line.split(',')] for line in lines)}


def available_ram_gib():
    lines=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
    return int(lines['MemAvailable'].split()[0])/1024**2


def run_profile(cmd,env,gpu,log_path,telemetry_path,timeout):
    done=threading.Event()
    with log_path.open('a',encoding='utf-8') as log, telemetry_path.open('w',newline='',encoding='utf-8') as output:
        writer=csv.DictWriter(output,fieldnames=['observed_at','physical_gpu','gpu_util_percent',
            'gpu_memory_used_mib','gpu_power_w','process_rss_kib','host_available_ram_gib'])
        writer.writeheader()
        process=subprocess.Popen(cmd,cwd=p.ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        def monitor():
            while not done.is_set():
                try:
                    lines=subprocess.check_output(['nvidia-smi',
                        '--query-gpu=index,utilization.gpu,memory.used,power.draw',
                        '--format=csv,noheader,nounits'],text=True,timeout=10).splitlines()
                    item=next(v for v in ([x.strip() for x in line.split(',')] for line in lines)
                              if int(v[0])==gpu)
                    status=Path(f'/proc/{process.pid}/status')
                    rss=''
                    if status.is_file():
                        rss=next((line.split(':',1)[1].strip().split()[0]
                            for line in status.read_text().splitlines() if line.startswith('VmRSS:')),'')
                    writer.writerow(dict(observed_at=now(),physical_gpu=gpu,gpu_util_percent=item[1],
                        gpu_memory_used_mib=item[2],gpu_power_w=item[3],
                        process_rss_kib=rss,host_available_ram_gib=available_ram_gib()))
                    output.flush()
                except Exception as exc:
                    log.write('telemetry sample unavailable: '+str(exc)+'\n')
                    log.flush()
                done.wait(2)
        thread=threading.Thread(target=monitor,daemon=True)
        thread.start()
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            raise
        finally:
            done.set()
            thread.join(timeout=15)


def prepare():
    cfg=p.config()
    if not {0,1}.issubset(gpu_info()):
        raise RuntimeError('physical GPU0 and GPU1 are required')
    if available_ram_gib()<cfg['minimum_available_ram_gib']:
        raise RuntimeError('available host RAM below the 20 GiB protective floor')
    if shutil.disk_usage(p.ROOT).free/1024**3<cfg['minimum_free_disk_gib']:
        raise RuntimeError('free disk below the 25 GiB protective floor')
    subprocess.run([sys.executable,'-B','-m','unittest','tests.test_day_portfolio','-v'],
                   cwd=p.ROOT,check=True)
    # Binding checks only local pre-existing artifacts; no network or installer is called.
    subprocess.run([sys.executable,'-B','-c',
        'import sys; sys.path.insert(0,"scripts"); import d18_d19_night as d; d.binding("P0",False); print("DINO BINDING PASS")'],
        cwd=p.ROOT,check=True)
    source=p.source_snapshot()
    manifest_path=p.OUT/'input_manifest.json'
    if manifest_path.is_file():
        manifest=p.read(manifest_path)
        if [row['path'] for row in manifest['files']]!=[str(x) for x in p.input_paths()]:
            raise RuntimeError('input list changed')
        p.verify_inputs(manifest)
    else:
        old=p.d21.OUT/'input_manifest.json'
        if old.is_file():
            manifest=p.read(old)
            if [row['path'] for row in manifest['files']]!=[str(x) for x in p.input_paths()]:
                raise RuntimeError('D21 input list changed')
            p.verify_inputs(manifest)
        else:
            files=[]
            for path in p.input_paths():
                if not path.is_file():
                    raise FileNotFoundError(f'missing existing dataset asset: {path}; no automatic download')
                stat=path.stat()
                files.append(dict(path=str(path),size=stat.st_size,mtime_ns=stat.st_mtime_ns,
                                  sha256=p.sha(path)))
                print('INPUT',len(files),path.name,flush=True)
            manifest=dict(files=files,datasets=p.datasets(),test6_loaded=False,
                integrity_policy='SHA256 at preparation; size/mtime before every job')
        p.write(manifest_path,manifest)
    for job in p.jobs():
        if job['direction'] in ('A','B'):
            from run_rebuild_v1_day_job import anchor
            anchor(job)
    devices=gpu_info()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=p.ROOT,text=True).strip()
    plan=dict(source_sha256=source,input_manifest_sha256=p.sha(manifest_path),
        jobs_sha256=p.sha(p.ROOT/cfg['job_manifest']),
        gpu_uuids={str(g):devices[g]['uuid'] for g in (0,1)},physical_gpus=[0,1],
        python=sys.executable,git_commit=commit,test6_loaded=False)
    path=p.OUT/'plan.json'
    if path.is_file():
        if p.read(path)!=plan:
            raise RuntimeError('frozen queue plan changed; keep existing evidence and use a new run id')
    else:
        p.write(path,plan)
    p.write(p.OUT/'preflight.json',dict(observed_at=now(),git_commit=commit,
        files=len(manifest['files']),main_jobs=42,reserve_jobs=8,
        available_ram_gib=available_ram_gib(),disk_free_gib=shutil.disk_usage(p.ROOT).free/1024**3,
        gpu=devices,training_started=False,downloads_started=False,
        missing_assets=[],test6_loaded=False))
    print('PREPARED 42 main + 8 reserve candidates; no training launched',flush=True)
    return plan


def verify_frozen(plan):
    if any(p.sha(p.ROOT/name)!=value for name,value in plan['source_sha256'].items()):
        raise RuntimeError('source or config changed since preparation')
    p.verify_inputs(p.read(p.OUT/'input_manifest.json'))
    if p.sha(p.OUT/'input_manifest.json')!=plan['input_manifest_sha256']:
        raise RuntimeError('input manifest changed')
    scope=p.OUT/'scope.json'
    if scope.is_file():
        stamp=p.OUT/'scope.sha256'
        if not stamp.is_file() or p.sha(scope)!=stamp.read_text(encoding='utf-8').strip():
            raise RuntimeError('frozen scope changed')


def select_scope():
    path=p.OUT/'scope.json'
    if path.is_file():
        return p.read(path)
    jobs=p.jobs()
    micro_profile=p.read(p.OUT/'microbatch_profile.json')
    physical_micro_batch=micro_profile['selected_physical_micro_batch']
    sample={}
    sample_eval={}
    patterns={
        'A_frozen':'A_potsdam_R0_frozen_scale0_seed42',
        'A_last4':'A_potsdam_M0_last4_scale0_seed42',
        'B':'B_potsdam_low_high_dsm_scale0_seed42',
        'C0':'C_potsdam_bicubic_ce_scale4_seed42',
        'Clearned':'C_potsdam_learned_pixel_high_ce_scale4_seed42',
        'D':'D_potsdam_learned_pixel_high_ce_dsm_scale4_seed42',
    }
    for family,job_id in patterns.items():
        job=next(j for j in jobs if j['job_id']==job_id)
        info=p.read(p.run_dir(job,profile=True,profile_micro_batch=physical_micro_batch)/'summary.json')
        if info['global_step']!=p.config()['profile_steps']:
            raise RuntimeError('incomplete throughput profile '+job_id)
        sample[family]=info['steady_step_median_seconds']
        sample_eval[family]=info['profile_full_train_tile_evaluation']['full_train_tile_evaluation_seconds']
    def family(job):
        if job['direction']=='A':
            return 'A_last4' if job['arm'].endswith('last4') else 'A_frozen'
        if job['direction']=='B':
            return 'B'
        if job['direction']=='D':
            return 'D'
        return 'C0' if job['arm']=='bicubic_ce' else 'Clearned'
    main=[j for j in jobs if j['budget_block']=='main']
    reserve=[j for j in jobs if j['budget_block']=='reserve']
    main_train_hours=sum(j['steps']*sample[family(j)] for j in main)/2/3600
    main_eval_hours=sum(sample_eval[family(j)]*len(p.datasets()[j['dataset']]['dev'])*
        len(p.config()['evaluation_conditions_ab' if j['direction'] in ('A','B') else 'evaluation_conditions_cde'])
        for j in main)/2/3600
    # Estimate excludes first-load, checkpoint I/O and contention; report it as a rough projection.
    estimated_main_hours=main_train_hours+main_eval_hours
    include_reserve=estimated_main_hours<24
    selected=main+(reserve if include_reserve else [])
    scope=dict(frozen_at=now(),profile_seconds_per_step=sample,
        profile_full_train_tile_eval_seconds=sample_eval,
        physical_micro_batch=physical_micro_batch,
        estimated_main_training_hours_lower_bound=main_train_hours,
        estimated_main_evaluation_hours=main_eval_hours,
        estimated_main_hours_before_io=estimated_main_hours,
        include_full_reserve_block=include_reserve,
        selected_job_ids=[j['job_id'] for j in selected],
        decision_rule='include all E if measured main train plus train-tile-scaled dev evaluation <24h; before any dev accuracy',
        test6_loaded=False)
    p.write(path,scope)
    (p.OUT/'scope.sha256').write_text(p.sha(path)+'\n',encoding='utf-8')
    print('SCOPE FROZEN',len(selected),'jobs; main estimated train+eval',estimated_main_hours,'hours',flush=True)
    return scope


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--prepare-only',action='store_true')
    ap.add_argument('--profile-only',action='store_true')
    args=ap.parse_args()
    p.OUT.mkdir(parents=True,exist_ok=True)
    with (p.OUT/'queue.lock').open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print('portfolio queue already active',flush=True)
            return 3
        plan=prepare()
        if args.prepare_only:
            return 0
        stop=threading.Event()
        mutex=threading.Lock()
        active={}
        failures=[]
        def event(job,state,detail=''):
            line=f'{now()}\t{job}\t{state}\t{detail}'
            with mutex:
                with (p.OUT/'status.tsv').open('a',encoding='utf-8') as file:
                    file.write(line+'\n')
            print(line,flush=True)
        def stopped():
            return stop.is_set() or (p.OUT/'STOP').exists()
        def wait_idle(gpu):
            began=time.monotonic()
            while not stopped():
                info=gpu_info()[gpu]
                if info['uuid']!=plan['gpu_uuids'][str(gpu)]:
                    raise RuntimeError('physical GPU mapping changed')
                if info['memory_mib']<=p.config()['gpu_idle_memory_mib_max'] and info['utilization']<=p.config()['gpu_idle_utilization_max']:
                    return True
                if time.monotonic()-began>12*3600:
                    raise RuntimeError(f'GPU{gpu} busy for 12 hours; no other jobs terminated')
                stop.wait(30)
            return False
        def worker(gpu,pending,mode,micro_batch=None):
            while not stopped():
                try:
                    job=pending.get_nowait()
                except queue.Empty:
                    return
                name=job['job_id']+('_'+mode+('_mb'+str(micro_batch) if mode=='profile' else '')
                    if mode!='formal' else '')
                try:
                    verify_frozen(plan)
                    if not wait_idle(gpu):
                        return
                    if shutil.disk_usage(p.ROOT).free/1024**3<p.config()['minimum_free_disk_gib']:
                        raise RuntimeError('disk below protective floor before next job')
                    if available_ram_gib()<p.config()['minimum_available_ram_gib']:
                        raise RuntimeError('RAM below protective floor before next job')
                    env=dict(os.environ,CUDA_VISIBLE_DEVICES=plan['gpu_uuids'][str(gpu)],
                             CUDA_DEVICE_ORDER='PCI_BUS_ID',DAY_PHYSICAL_GPU=str(gpu))
                    cmd=[sys.executable,'-B','-u','scripts/run_rebuild_v1_day_job.py','--job-id',job['job_id']]
                    if mode!='formal':
                        cmd.append('--'+mode)
                    if micro_batch is not None:
                        cmd.extend(['--micro-batch',str(micro_batch)])
                    with mutex:
                        active[gpu]=dict(job_id=job['job_id'],mode=mode,micro_batch=micro_batch,started_at=now())
                    event(name,'START',f'physical_gpu={gpu}')
                    if mode=='profile':
                        returncode=run_profile(cmd,env,gpu,p.OUT/f'{name}.log',
                            p.OUT/f'{name}_telemetry.csv',p.config()['job_timeout_hours']*3600)
                    else:
                        with (p.OUT/f'{name}.log').open('a',encoding='utf-8') as log:
                            result=subprocess.run(cmd,cwd=p.ROOT,env=env,stdout=log,
                                stderr=subprocess.STDOUT,timeout=p.config()['job_timeout_hours']*3600)
                        returncode=result.returncode
                    if returncode:
                        raise RuntimeError(f'job exit {returncode}; inspect {name}.log')
                    event(name,'COMPLETE',f'physical_gpu={gpu}')
                except Exception as exc:
                    failures.append(dict(job=name,error=str(exc)))
                    event(name,'FAILED',str(exc))
                    stop.set()
                finally:
                    with mutex:
                        active.pop(gpu,None)
                    pending.task_done()
        def batch(jobs,mode,micro_batch=None):
            pending=queue.Queue()
            for job in jobs:
                pending.put(job)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                futures=[pool.submit(worker,gpu,pending,mode,micro_batch) for gpu in (0,1)]
                while not all(f.done() for f in futures):
                    with mutex:
                        current=dict(active)
                    for row in current.values():
                        job=next(j for j in p.jobs() if j['job_id']==row['job_id'])
                        progress=p.run_dir(job,smoke=mode=='smoke',profile=mode=='profile',
                            profile_micro_batch=micro_batch)/'progress.json'
                        if progress.is_file():
                            row['progress']=p.read(progress)
                    p.write(p.OUT/'progress.json',dict(observed_at=now(),active=current,
                        waiting=pending.qsize(),stop_requested=stopped()))
                    concurrent.futures.wait(futures,timeout=30)
                for future in futures:
                    future.result()
            return not stopped() and pending.empty()
        all_jobs=p.jobs()
        ids=['A_potsdam_R0_frozen_scale0_seed42','A_potsdam_M0_last4_scale0_seed42',
             'B_potsdam_low_high_dsm_scale0_seed42','C_potsdam_bicubic_ce_scale4_seed42',
             'C_potsdam_learned_pixel_high_ce_scale4_seed42',
             'D_potsdam_learned_pixel_high_ce_dsm_scale4_seed42']
        profile_jobs=[next(j for j in all_jobs if j['job_id']==name) for name in ids]
        micro_path=p.OUT/'microbatch_profile.json'
        if micro_path.is_file():
            micro_profile=p.read(micro_path)
        else:
            hardest=profile_jobs[-1]
            variants=[]
            event('MICROBATCH','START','D end-to-end path, physical batch 2/4/8/16; effective batch 16')
            for micro_batch in (2,4,8,16):
                verify_frozen(plan)
                if not wait_idle(0):
                    return 2
                env=dict(os.environ,CUDA_VISIBLE_DEVICES=plan['gpu_uuids']['0'],
                    CUDA_DEVICE_ORDER='PCI_BUS_ID',DAY_PHYSICAL_GPU='0')
                name=hardest['job_id']+'_profile_mb'+str(micro_batch)
                cmd=[sys.executable,'-B','-u','scripts/run_rebuild_v1_day_job.py',
                    '--job-id',hardest['job_id'],'--profile','--micro-batch',str(micro_batch)]
                returncode=run_profile(cmd,env,0,p.OUT/f'{name}.log',
                    p.OUT/f'{name}_telemetry.csv',p.config()['job_timeout_hours']*3600)
                if returncode:
                    tail=(p.OUT/f'{name}.log').read_text(encoding='utf-8',errors='replace')[-4000:].lower()
                    if 'out of memory' in tail:
                        variants.append(dict(micro_batch=micro_batch,feasible=False,reason='CUDA OOM'))
                        event(name,'OOM','larger variants skipped')
                        break
                    raise RuntimeError(f'microbatch probe failed: {name}; inspect log')
                info=p.read(p.run_dir(hardest,profile=True,profile_micro_batch=micro_batch)/'summary.json')
                seconds=info['steady_step_median_seconds']
                peak=info['gpu_peak_memory_mib']
                variants.append(dict(micro_batch=micro_batch,feasible=peak<70*1024,
                    seconds_per_step=seconds,gpu_peak_memory_mib=peak))
                event(name,'COMPLETE',f'{seconds:.3f}s/step; peak {peak:.0f}MiB')
            feasible=[v for v in variants if v['feasible']]
            if not feasible:
                raise RuntimeError('no microbatch fits the 70 GiB protective peak')
            best=min(feasible,key=lambda row:row['seconds_per_step'])
            micro_profile=dict(observed_at=now(),variants=variants,
                selected_physical_micro_batch=best['micro_batch'],
                effective_batch=16,selection='fastest feasible D path under 70 GiB peak')
            p.write(micro_path,micro_profile)
        physical_micro_batch=micro_profile['selected_physical_micro_batch']
        event('PROFILE','START',f'6 representative paths; physical microbatch {physical_micro_batch}')
        if not batch(profile_jobs,'profile',physical_micro_batch):
            return 2
        scope=select_scope()
        if args.profile_only:
            event('PROFILE','COMPLETE',f"scope frozen: {len(scope['selected_job_ids'])} jobs; no formal training")
            return 0
        selected=[next(j for j in all_jobs if j['job_id']==name) for name in scope['selected_job_ids']]
        event('SMOKE','START',f'{len(selected)} training-crop paths; no development labels')
        if not batch(selected,'smoke'):
            return 2
        event('SMOKE','COMPLETE',f'{len(selected)} paths')
        event('QUEUE','START',f'{len(selected)} formal jobs; GPU0+GPU1; seed42 only')
        for direction in ('A','B','C','D','E'):
            block=[j for j in selected if j['direction']==direction]
            if not block:
                continue
            random.Random(4200+ord(direction)).shuffle(block)
            if not batch(block,'formal'):
                break
            event(direction,'COMPLETE',f'{len(block)} paired cells; accuracy did not control continuation')
            subprocess.run([sys.executable,'-B','scripts/analyze_rebuild_v1_day.py'],
                           cwd=p.ROOT,check=True)
        completed=sum(p.eval_dir(job).joinpath('summary.json').is_file() for job in selected)
        summary=dict(observed_at=now(),completed=completed,planned=len(selected),
            failures=failures,stop_requested=stopped(),test6_loaded=False,
            status='COMPLETE' if completed==len(selected) else 'INCOMPLETE')
        p.write(p.OUT/'queue_summary.json',summary)
        event('QUEUE',summary['status'],f'{completed}/{len(selected)}')
        p.COMPACT.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p.OUT/'queue_summary.json',p.COMPACT/'queue_summary.json')
        shutil.copy2(p.OUT/'status.tsv',p.COMPACT/'status.tsv')
        subprocess.run([sys.executable,'-B','scripts/analyze_rebuild_v1_day.py'],
                       cwd=p.ROOT,check=True)
        return 0 if completed==len(selected) else 2


if __name__=='__main__':
    raise SystemExit(main())
