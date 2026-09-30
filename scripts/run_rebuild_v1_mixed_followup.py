"""Run the four predeclared E C0/C1 cells after the 42-job day queue ends."""
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

import day_portfolio_common as p
from analyze_rebuild_v1_day import audit
from run_rebuild_v1_day_queue import available_ram_gib, gpu_info, verify_frozen


OUT = p.ROOT / 'records/post_d21_mixed_followup_queue_20260930'
COMPACT = p.ROOT / 'records/post_d21_mixed_followup_compact_20260930'
IDS = [
    f'E_{dataset}_{arm}_scale0_seed42'
    for dataset in ('potsdam', 'vaihingen')
    for arm in ('bicubic_ce', 'learned_ce')
]


def now():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def selected_jobs():
    available = {job['job_id']: job for job in p.jobs()}
    jobs = [available[name] for name in IDS]
    if any(job['direction'] != 'E' or job['budget_block'] != 'reserve' or
           job['steps'] != 16000 or job['seed'] != 42 for job in jobs):
        raise RuntimeError('follow-up E manifest binding changed')
    return jobs


def prepare():
    if not (p.OUT / 'plan.json').is_file() or not (p.OUT / 'scope.json').is_file():
        raise RuntimeError('original day queue has no frozen plan and scope')
    prior = p.read(p.OUT / 'plan.json')
    verify_frozen(prior)
    scope = p.read(p.OUT / 'scope.json')
    if len(scope['selected_job_ids']) != 42 or any(name in scope['selected_job_ids'] for name in IDS):
        raise RuntimeError('E was included in original scope; follow-up must not duplicate it')
    jobs = selected_jobs()
    devices = gpu_info()
    for gpu in (0, 1):
        if gpu not in devices or devices[gpu]['uuid'] != prior['gpu_uuids'][str(gpu)]:
            raise RuntimeError(f'physical GPU{gpu} mapping changed')
    cfg = p.config()
    disk = shutil.disk_usage(p.ROOT).free / 1024**3
    ram = available_ram_gib()
    if disk < cfg['minimum_free_disk_gib'] or ram < cfg['minimum_available_ram_gib']:
        raise RuntimeError('disk or host RAM below existing protective floor')
    runner = Path(__file__).resolve()
    subprocess.run(['git', 'ls-files', '--error-unmatch', str(runner.relative_to(p.ROOT))],
                   cwd=p.ROOT, check=True, stdout=subprocess.DEVNULL)
    binding = dict(previous_plan_sha256=p.sha(p.OUT / 'plan.json'),
                   previous_scope_sha256=p.sha(p.OUT / 'scope.json'),
                   runner_sha256=p.sha(runner), job_ids=IDS,
                   job_manifest_sha256=p.sha(p.ROOT / cfg['job_manifest']),
                   physical_gpu_uuids=prior['gpu_uuids'],
                   selected_physical_micro_batch=scope['physical_micro_batch'],
                   test6_loaded=False)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / 'plan.json'
    if path.is_file() and p.read(path) != binding:
        raise RuntimeError('follow-up plan changed; preserve existing evidence')
    if not path.is_file():
        p.write(path, binding)
    p.write(OUT / 'preflight.json', dict(observed_at=now(), ready_jobs=len(jobs),
            disk_free_gib=disk, available_ram_gib=ram, gpu=devices,
            downloads_started=False, training_started=False, test6_loaded=False))
    return prior, jobs, binding


def analyze(jobs):
    COMPACT.mkdir(parents=True, exist_ok=True)
    summaries = {}
    for job in jobs:
        train_path = p.run_dir(job) / 'summary.json'
        eval_path = p.eval_dir(job) / 'summary.json'
        if not (train_path.is_file() and eval_path.is_file()):
            continue
        train, evaluation = p.read(train_path), p.read(eval_path)
        ck = p.run_dir(job) / 'last_train_state.pth'
        if train['job'] != job or evaluation['job'] != job or train['global_step'] != 16000:
            raise RuntimeError('follow-up training/evaluation job mismatch')
        if p.sha(ck) != train['checkpoint_sha256'] or (
                evaluation['signature']['checkpoint_sha256'] != train['checkpoint_sha256'] or
                evaluation['signature']['training'] != train['signature']):
            raise RuntimeError('follow-up checkpoint/signature mismatch')
        if evaluation['test6_loaded'] is not False or train['test6_loaded'] is not False:
            raise RuntimeError('test boundary violated')
        audit(evaluation)
        shutil.copy2(train_path, COMPACT / (job['job_id'] + '_training.json'))
        shutil.copy2(eval_path, COMPACT / (job['job_id'] + '_evaluation.json'))
        summaries[job['job_id']] = evaluation
    comparisons = []
    for dataset in ('potsdam', 'vaihingen'):
        fixed = summaries.get(f'E_{dataset}_bicubic_ce_scale0_seed42')
        learned = summaries.get(f'E_{dataset}_learned_ce_scale0_seed42')
        if fixed is None or learned is None:
            continue
        if fixed['primary_scope'] != learned['primary_scope']:
            raise RuntimeError('paired primary scope mismatch')
        scope = fixed['primary_scope']
        for condition in ('scale2_clean', 'scale4_clean', 'scale2_unseen_blur',
                          'scale4_unseen_blur'):
            a, b = fixed['conditions'][condition], learned['conditions'][condition]
            delta = 100 * (b['pooled'][scope]['metrics']['mIoU_fg5'] -
                           a['pooled'][scope]['metrics']['mIoU_fg5'])
            tiles = {}
            for tile in a['tiles']:
                if tile not in b['tiles']:
                    raise RuntimeError('paired evaluation tile mismatch')
                av = a['tiles'][tile]['scopes'][scope]['metrics']['mIoU_fg5']
                bv = b['tiles'][tile]['scopes'][scope]['metrics']['mIoU_fg5']
                tiles[tile] = 100 * (bv - av)
            comparisons.append(dict(dataset=dataset, condition=condition,
                                    learned_minus_bicubic_pp=delta,
                                    per_tile_delta_pp=tiles))
    p.write(COMPACT / 'analysis.json', dict(observed_at=now(), completed=len(summaries),
            selected=len(jobs), comparisons=comparisons,
            integer_count_audit='PASS', test6_loaded=False,
            interpretation='single-seed paired development evidence; no independent final claim'))
    for name in ('plan.json', 'preflight.json', 'status.tsv', 'queue_summary.json'):
        path = OUT / name
        if path.is_file():
            shutil.copy2(path, COMPACT / name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prepare-only', action='store_true')
    ap.add_argument('--launch', action='store_true')
    args = ap.parse_args()
    if args.prepare_only == args.launch:
        ap.error('choose exactly one of --prepare-only and --launch')
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'queue.lock').open('a') as own_lock:
        try:
            fcntl.flock(own_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('follow-up queue already active')
        prior, jobs, binding = prepare()
        if args.prepare_only:
            print('PREPARED four E C0/C1 jobs; no training launched', flush=True)
            return 0
        with (p.OUT / 'queue.lock').open('a') as old_lock:
            waiting_logged = False
            while True:
                if (OUT / 'STOP').is_file():
                    print('STOP requested before follow-up launch', flush=True)
                    return 2
                try:
                    fcntl.flock(old_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if not waiting_logged:
                        print('WAITING for original 42-job queue to release GPU0/GPU1', flush=True)
                        waiting_logged = True
                    time.sleep(30)
            summary_path = p.OUT / 'queue_summary.json'
            if not summary_path.is_file():
                raise RuntimeError('original queue exited without a completion summary')
            old_summary = p.read(summary_path)
            if (old_summary['status'] != 'COMPLETE' or old_summary['completed'] != 42 or
                    old_summary['planned'] != 42 or old_summary['failures']):
                raise RuntimeError('original 42-job queue is incomplete; follow-up not started')
            if p.read(OUT / 'plan.json') != binding:
                raise RuntimeError('follow-up plan changed while waiting')
            verify_frozen(prior)
            events_lock = threading.Lock()
            stop = threading.Event()
            active = {}
            failures = []

            def event(name, state, detail=''):
                line = f'{now()}\t{name}\t{state}\t{detail}'
                with events_lock:
                    with (OUT / 'status.tsv').open('a', encoding='utf-8') as handle:
                        handle.write(line + '\n')
                print(line, flush=True)

            def stopped():
                return stop.is_set() or (OUT / 'STOP').is_file()

            def worker(gpu, pending, smoke):
                while not stopped():
                    try:
                        job = pending.get_nowait()
                    except queue.Empty:
                        return
                    name = job['job_id'] + ('_smoke' if smoke else '')
                    try:
                        verify_frozen(prior)
                        if p.read(OUT / 'plan.json') != binding:
                            raise RuntimeError('follow-up plan changed')
                        began = time.monotonic()
                        while not stopped():
                            info = gpu_info()[gpu]
                            if info['uuid'] != prior['gpu_uuids'][str(gpu)]:
                                raise RuntimeError('physical GPU mapping changed')
                            if (info['memory_mib'] <= p.config()['gpu_idle_memory_mib_max'] and
                                    info['utilization'] <= p.config()['gpu_idle_utilization_max']):
                                break
                            if time.monotonic() - began > 12 * 3600:
                                raise RuntimeError(f'GPU{gpu} busy for 12 hours')
                            time.sleep(30)
                        if stopped():
                            return
                        if (shutil.disk_usage(p.ROOT).free / 1024**3 <
                                p.config()['minimum_free_disk_gib'] or
                                available_ram_gib() < p.config()['minimum_available_ram_gib']):
                            raise RuntimeError('disk or RAM below protective floor')
                        env = dict(os.environ, CUDA_VISIBLE_DEVICES=prior['gpu_uuids'][str(gpu)],
                                   CUDA_DEVICE_ORDER='PCI_BUS_ID', DAY_PHYSICAL_GPU=str(gpu))
                        cmd = [sys.executable, '-B', '-u', 'scripts/run_rebuild_v1_day_job.py',
                               '--job-id', job['job_id']]
                        if smoke:
                            cmd.append('--smoke')
                        with events_lock:
                            active[gpu] = dict(job_id=job['job_id'], smoke=smoke,
                                               started_at=now())
                        event(name, 'START', f'physical_gpu={gpu}')
                        with (OUT / (name + '.log')).open('a', encoding='utf-8') as log:
                            code = subprocess.run(cmd, cwd=p.ROOT, env=env, stdout=log,
                                                  stderr=subprocess.STDOUT,
                                                  timeout=p.config()['job_timeout_hours'] * 3600).returncode
                        if code:
                            raise RuntimeError(f'job exit {code}; inspect {name}.log')
                        event(name, 'COMPLETE', f'physical_gpu={gpu}')
                    except Exception as exc:
                        failures.append(dict(job=name, error=str(exc)))
                        event(name, 'FAILED', str(exc))
                        stop.set()
                    finally:
                        with events_lock:
                            active.pop(gpu, None)
                        pending.task_done()

            def batch(smoke):
                pending = queue.Queue()
                for job in jobs:
                    pending.put(job)
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(worker, gpu, pending, smoke) for gpu in (0, 1)]
                    while not all(future.done() for future in futures):
                        with events_lock:
                            current = dict(active)
                        for row in current.values():
                            job = next(j for j in jobs if j['job_id'] == row['job_id'])
                            progress = p.run_dir(job, smoke=smoke) / 'progress.json'
                            if progress.is_file():
                                row['progress'] = p.read(progress)
                        p.write(OUT / 'progress.json', dict(observed_at=now(), active=current,
                                waiting=pending.qsize(), stop_requested=stopped()))
                        concurrent.futures.wait(futures, timeout=30)
                    for future in futures:
                        future.result()
                return not stopped() and pending.empty()

            event('SMOKE', 'START', 'four training-tile E paths; no development labels')
            if not batch(True):
                event('SMOKE', 'INCOMPLETE')
            else:
                event('SMOKE', 'COMPLETE', '4/4')
                event('QUEUE', 'START', 'four paired E jobs; GPU0+GPU1; seed42 only')
                batch(False)
            completed = sum((p.eval_dir(job) / 'summary.json').is_file() for job in jobs)
            if completed == len(jobs) and not failures:
                try:
                    analyze(jobs)
                    event('ANALYSIS', 'COMPLETE', 'integer count audit PASS')
                except Exception as exc:
                    failures.append(dict(job='ANALYSIS', error=str(exc)))
                    event('ANALYSIS', 'FAILED', str(exc))
            result = dict(observed_at=now(), completed=completed, planned=len(jobs),
                          failures=failures, stop_requested=stopped(), test6_loaded=False,
                          status='COMPLETE' if completed == len(jobs) and not failures else 'INCOMPLETE')
            p.write(OUT / 'queue_summary.json', result)
            event('QUEUE', result['status'], f'{completed}/{len(jobs)}')
            COMPACT.mkdir(parents=True, exist_ok=True)
            shutil.copy2(OUT / 'queue_summary.json', COMPACT / 'queue_summary.json')
            shutil.copy2(OUT / 'status.tsv', COMPACT / 'status.tsv')
            return 0 if result['status'] == 'COMPLETE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
