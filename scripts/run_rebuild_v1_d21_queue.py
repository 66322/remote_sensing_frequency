"""Bounded two-GPU D21 queue. Resume by running the same committed launcher."""
import argparse
import concurrent.futures
from datetime import datetime
import fcntl
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time
import d21_common as p


def gpu_info():
    lines = subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid,memory.used,utilization.gpu',
                                    '--format=csv,noheader,nounits'], text=True).splitlines()
    return {int(v[0]): dict(uuid=v[1], memory=int(v[2]), utilization=int(v[3]))
            for v in ([x.strip() for x in line.split(',')] for line in lines)}


def available_ram_gib():
    rows = dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
    return int(rows['MemAvailable'].split()[0]) / 1024**2


def prepare():
    cfg = p.config()
    p.ROOT.resolve().relative_to(Path('/home/jovyan/zzx').resolve())
    remaining = sum(not (p.eval_dir(job)/'summary.json').is_file() for job in p.jobs())
    required_gib = 12 + (cfg['minimum_free_disk_gib']-12)*remaining/48
    if shutil.disk_usage(p.ROOT).free < required_gib*1024**3:
        raise RuntimeError(f'need {required_gib:.1f} GiB free disk for remaining checkpoints and predictions')
    if available_ram_gib() < cfg['minimum_available_ram_gib']:
        raise RuntimeError('insufficient available host RAM for two data loaders')
    devices = gpu_info()
    if not {0,1}.issubset(devices):
        raise RuntimeError('physical GPU0/GPU1 unavailable')
    source = p.snapshot()
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=p.ROOT,text=True).strip()
    manifest_path = p.OUT/'input_manifest.json'
    if manifest_path.is_file():
        manifest = p.read(manifest_path)
        if [row['path'] for row in manifest['files']] != [str(x) for x in p.input_paths()]:
            raise RuntimeError('input file list changed')
        p.verify_inputs(manifest)
    else:
        files = []
        for path in p.input_paths():
            path.resolve().relative_to(Path('/home/jovyan/zzx').resolve())
            stat = path.stat()
            files.append(dict(path=str(path), size=stat.st_size, mtime_ns=stat.st_mtime_ns, sha256=p.sha(path)))
            print('INPUT', len(files), path.name, flush=True)
        p.write(manifest_path, dict(files=files, datasets=p.datasets(), test6_loaded=False,
                integrity_policy='SHA256 at preparation; size/mtime checked before each job'))
    plan = dict(source_sha256=source, input_manifest_sha256=p.sha(manifest_path), jobs=p.jobs(),
                gpu_uuids={str(g): devices[g]['uuid'] for g in (0,1)}, physical_gpus=[0,1],
                python=sys.executable, test6_loaded=False)
    plan_path = p.OUT/'plan.json'
    if plan_path.is_file():
        if p.read(plan_path) != plan:
            raise RuntimeError('frozen plan changed; do not overwrite existing D21 runs')
    else:
        p.write(plan_path, plan)
    p.write(p.OUT/'preflight.json', dict(observed_at=datetime.now().astimezone().isoformat(),
        git_commit=commit, files=len(p.input_paths()), jobs=len(p.jobs()),
        available_ram_gib=available_ram_gib(), disk_free_gib=shutil.disk_usage(p.ROOT).free/1024**3,
        gpu=devices, training_started=False))
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_d21_detail.py','-v'],
                   cwd=p.ROOT, check=True)
    subprocess.run([sys.executable,'-B','-c',
        'import sys; sys.path.insert(0,"scripts"); import run_rebuild_v1_d21_job; import d18_d19_night as p; p.binding("P0", True); print("ENVIRONMENT AND DINO BINDING PASS")'],
        cwd=p.ROOT, check=True)
    return cfg, plan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prepare-only', action='store_true')
    args = ap.parse_args()
    p.OUT.mkdir(parents=True, exist_ok=True)
    with (p.OUT/'queue.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print('D21 queue already active', flush=True)
            return 3
        cfg, plan = prepare()
        if args.prepare_only:
            print('D21 PREPARED: 48 jobs; no training launched', flush=True)
            return 0
        stop, mutex = threading.Event(), threading.Lock()
        active, failures = {}, []
        def event(job, state, detail=''):
            line = f'{datetime.now().astimezone().isoformat(timespec="seconds")}\t{job}\t{state}\t{detail}'
            with mutex:
                with (p.OUT/'status.tsv').open('a',encoding='utf-8') as file:
                    file.write(line+'\n')
            print(line, flush=True)
        def stopped():
            return stop.is_set() or (p.OUT/'STOP').exists()
        def check_frozen():
            if any(p.sha(p.ROOT/name) != value for name,value in plan['source_sha256'].items()):
                raise RuntimeError('source changed; stop new launches')
            p.verify_inputs(p.read(p.OUT/'input_manifest.json'))
        def wait_idle(gpu):
            began = time.monotonic()
            while not stopped():
                info = gpu_info()[gpu]
                if info['uuid'] != plan['gpu_uuids'][str(gpu)]:
                    raise RuntimeError('physical GPU mapping changed')
                if info['memory'] <= cfg['gpu_idle_memory_mib_max'] and info['utilization'] <= cfg['gpu_idle_utilization_max']:
                    return True
                if time.monotonic()-began > cfg['gpu_wait_hours']*3600:
                    raise RuntimeError(f'GPU{gpu} remains busy; never terminate another job')
                stop.wait(30)
            return False
        def worker(gpu, pending, smoke):
            while not stopped():
                try:
                    job = pending.get_nowait()
                except queue.Empty:
                    return
                name = p.key(job,smoke)
                try:
                    check_frozen()
                    if not wait_idle(gpu):
                        return
                    if shutil.disk_usage(p.ROOT).free < 12*1024**3:
                        raise RuntimeError('free disk below 12 GiB; pause before next job')
                    if available_ram_gib() < 20:
                        raise RuntimeError('available RAM below 20 GiB before loading dataset')
                    env = dict(os.environ, CUDA_VISIBLE_DEVICES=plan['gpu_uuids'][str(gpu)],
                               D21_PHYSICAL_GPU=str(gpu), CUDA_DEVICE_ORDER='PCI_BUS_ID')
                    cmd = [sys.executable,'-B','-u','scripts/run_rebuild_v1_d21_job.py',
                           '--dataset',job['dataset'],'--arm',job['arm'],'--seed',str(job['seed'])]
                    if smoke:
                        cmd.append('--smoke')
                    with mutex:
                        active[gpu] = dict(job=job, smoke=smoke, started_at=datetime.now().astimezone().isoformat())
                    event(name, 'START', f'physical_gpu={gpu}')
                    with (p.OUT/f'{name}.log').open('a',encoding='utf-8') as log:
                        result = subprocess.run(cmd, cwd=p.ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                                timeout=cfg['job_timeout_hours']*3600)
                    if result.returncode:
                        raise RuntimeError(f'job exit {result.returncode}; inspect {name}.log')
                    event(name, 'COMPLETE', f'physical_gpu={gpu}')
                except Exception as exc:
                    with mutex:
                        failures.append(dict(job=name,error=str(exc)))
                    event(name,'FAILED',str(exc))
                    stop.set()
                finally:
                    with mutex:
                        active.pop(gpu,None)
                    pending.task_done()
        def batch(jobs, smoke=False):
            pending = queue.Queue()
            for job in jobs:
                pending.put(job)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(worker, gpu, pending, smoke) for gpu in (0,1)]
                while not all(f.done() for f in futures):
                    with mutex:
                        current = dict(active)
                    for row in current.values():
                        progress = p.run_dir(row['job'],row['smoke'])/'progress.json'
                        if progress.is_file():
                            row['progress'] = p.read(progress)
                    p.write(p.OUT/'progress.json',dict(observed_at=datetime.now().astimezone().isoformat(),
                        active=current, waiting=pending.qsize(), stop_requested=stopped()))
                    concurrent.futures.wait(futures, timeout=30)
                for future in futures:
                    future.result()
            return not stopped() and pending.empty()
        event('QUEUE','START','48 formal jobs; fixed 16000 steps; GPU0+GPU1')
        smoke_jobs = [dict(dataset=d,arm=a,seed=42) for a in cfg['arms'] for d in cfg['datasets']]
        passed = batch(smoke_jobs, smoke=True)
        if passed:
            event('SMOKE','COMPLETE','all 16 arm/dataset paths; final checkpoint reload; train crops only')
            for seed in cfg['seeds']:
                if not batch([job for job in p.jobs() if job['seed'] == seed]):
                    break
                event(f'SEED{seed}','COMPLETE','16 matched jobs; metrics never decide whether other seeds run')
                subprocess.run([sys.executable,'-B','scripts/analyze_rebuild_v1_d21.py'],cwd=p.ROOT,check=True)
        subprocess.run([sys.executable,'-B','scripts/analyze_rebuild_v1_d21.py'],cwd=p.ROOT,check=True)
        completed = sum((p.eval_dir(job)/'summary.json').is_file() for job in p.jobs())
        p.write(p.OUT/'queue_summary.json', dict(observed_at=datetime.now().astimezone().isoformat(),
            completed=completed, planned=48, failures=failures, stop_requested=stopped(),
            test6_loaded=False, status='COMPLETE' if completed == 48 else 'INCOMPLETE'))
        event('QUEUE','COMPLETE' if completed == 48 else 'INCOMPLETE',f'{completed}/48')
        shutil.copy2(p.OUT/'queue_summary.json',p.COMPACT/'queue_summary.json')
        shutil.copy2(p.OUT/'status.tsv',p.COMPACT/'status.tsv')
        return 0 if completed == 48 else 2


if __name__ == '__main__':
    raise SystemExit(main())
