"""Wait without touching data/CUDA, then hold one global lease and two GPU slots."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
from structured_v0_common import *


def predecessor_verdict(state, controller_live, workers_live, lock_free):
    if state['status'] == 'PAIRED_COMPLETE_AWAITING_REVIEW':
        if len(state['jobs']) != 8 or any(r['status'] != 'COMPLETE' for r in state['jobs'].values()):
            return 'HOLD_INVALID_PREDECESSOR'
        return 'READY' if not controller_live and not workers_live and lock_free else 'WAITING_PREDECESSOR_RELEASE'
    if 'HOLD' in state['status'] or 'INTERRUPTED' in state['status'] or not controller_live:
        return 'HOLD_PREDECESSOR'
    return 'WAITING_PREDECESSOR'


def observe(p):
    from d30_common import live_owned, lock_free
    pred = Path(p['predecessor'])
    state = read(pred/'queue_status.json')
    c = live_owned(state.get('controller_pid', -1), pred)
    w = any(live_owned(r.get('pid', -1), pred) for r in state['jobs'].values())
    free = lock_free(pred) if (pred/'controller.lock').exists() else False
    return dict(verdict=predecessor_verdict(state, c, w, free), predecessor_status=state['status'],
                predecessor_observed=state['observed_at'], controller_live=c, workers_live=w,
                lock_free=free, checked_at=now())


def dispatch(base, state, env, popen=subprocess.Popen, sleep=time.sleep, available=None, clock=time.monotonic):
    if available is None:
        from control_post_t_paired_v2 import device_free
        available = device_free
    active = {}
    try:
        while True:
            for gpu, (job, proc, log, began, prior) in list(active.items()):
                row = state['jobs'][job]
                row['active_seconds'] = prior + clock()-began
                f = base/'jobs'/job/'progress.json'
                if f.exists():
                    row['progress'] = read(f)
                if row['active_seconds'] > 8*3600:
                    raise RuntimeError('job exceeded fixed 8h active-time limit: '+job)
                rc = proc.poll()
                if rc is None:
                    continue
                log.close()
                del active[gpu]
                row['returncode'] = rc
                if rc in (0, 75) and (base/'jobs'/job/'complete.json').exists():
                    accept(base, job)
                    row['status'] = 'COMPLETE'
                elif rc == 75 and (base/'jobs'/job/'paused.json').exists():
                    row['status'] = 'PAUSED_USER'
                else:
                    row['status'] = 'TECHNICAL_FAILURE'
                    raise RuntimeError('worker failed, no retry: '+job)
                print('STRUCTURED_JOB', job, row['status'], 'GPU', gpu, flush=True)
            if all(r['status'] == 'COMPLETE' for r in state['jobs'].values()):
                return
            for gpu in (0, 1):
                if gpu in active or blocked(base, gpu):
                    continue
                jobs = ready_jobs(state)
                if not jobs:
                    continue
                uuid = available(gpu, state.setdefault('gpu_uuids', {}).get(str(gpu)))
                if uuid is None:
                    continue
                state['gpu_uuids'][str(gpu)] = uuid
                job = jobs[0]
                row = state['jobs'][job]
                resume = row['status'] == 'PAUSED_USER'
                if (base/'jobs'/job).exists() and not resume:
                    raise RuntimeError('partial job directory, no automatic retry: '+job)
                cmd = [sys.executable, '-u', '-B', str(base/'code/scripts/run_structured_v0.py'),
                       '--directory', str(base), '--job', job, '--gpu', str(gpu)]
                if resume:
                    cmd.append('--resume')
                path = base/'logs'/('%s_%s.log' % (job, time.time_ns()))
                log = path.open('x')
                proc = popen(cmd, cwd=base/'code', env=dict(env, CUDA_VISIBLE_DEVICES=str(gpu)),
                             stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                active[gpu] = (job, proc, log, clock(), row.get('active_seconds', 0))
                row.update(status='RUNNING', gpu=gpu, pid=proc.pid, log=str(path))
                row.setdefault('sessions', []).append(dict(gpu=gpu, uuid=uuid, pid=proc.pid, resume=resume, started_at=now()))
                print('STRUCTURED_START', job, 'GPU', gpu, 'RESUME', resume, flush=True)
            state.update(status='RUNNING' if active else 'WAITING_AVAILABLE_GPU', observed_at=now(),
                         gpu_blocked={str(g):blocked(base, g) for g in (0,1)})
            write(base/'queue_status.json', state)
            sleep(10)
    except BaseException as exc:
        write(base/'control/stop_all.json', dict(reason=str(exc), observed_at=now()))
        state.update(status='HOLD_RELEASING_WORKERS', error=str(exc), observed_at=now())
        write(base/'queue_status.json', state)
        for gpu, (job, proc, log, began, prior) in active.items():
            try:
                proc.wait(timeout=300)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:
                    proc.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            log.close()
        raise


def main(base):
    import fcntl
    p = validate(base)
    verify_code(base)
    with (base/'controller.lock').open('a') as controller:
        fcntl.flock(controller, fcntl.LOCK_EX|fcntl.LOCK_NB)
        state = read(base/'queue_status.json')
        if any(r['status'] != 'PENDING' for r in state['jobs'].values()):
            raise RuntimeError('no automatic controller reattachment')
        state.update(controller_pid=os.getpid(), status='WAITING_PREDECESSOR', observed_at=now())
        write(base/'queue_status.json', state)
        try:
            while True:
                observation = observe(p)
                state.update(status=observation['verdict'], predecessor=observation, observed_at=now())
                write(base/'queue_status.json', state)
                if observation['verdict'].startswith('HOLD'):
                    raise RuntimeError('predecessor requires inspection: '+str(observation))
                if observation['verdict'] == 'READY':
                    break
                time.sleep(30)
            pred = Path(p['predecessor'])
            if sha(pred/'plan.json') != p['predecessor_plan_sha256'] or sha(pred/'code_manifest.json') != p['predecessor_code_sha256']:
                raise RuntimeError('predecessor binding changed')
            with (Path(p['root'])/'records/post_ab_successor.lock').open('a') as lease:
                while True:
                    try:
                        fcntl.flock(lease, fcntl.LOCK_EX|fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        state.update(status='WAITING_GLOBAL_LEASE', observed_at=now())
                        write(base/'queue_status.json', state)
                        time.sleep(30)
                if observe(p)['verdict'] != 'READY':
                    raise RuntimeError('predecessor changed while acquiring lease')
                from post_t_paired_v2_common import validate as check_old, accept_worker
                old = read(pred/'plan.json')
                check_old(old)
                for job in old['jobs']:
                    accept_worker(pred, job['id'], old)
                oldstate = read(pred/'queue_status.json')
                if sha(pred/'paired_screen.json') != oldstate['screen_sha256']:
                    raise RuntimeError('predecessor screen changed')
                write(base/'predecessor_receipt.json', dict(observation=observe(p), technical_acceptance=True,
                      independent_scientific_review=False, screen_sha256=oldstate['screen_sha256']))
                env = dict(os.environ, CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
                state.update(status='CPU_PREPARING_MASKS', observed_at=now())
                write(base/'queue_status.json', state)
                with (base/'preparation.log').open('x') as log:
                    subprocess.run([sys.executable, '-u', '-B', str(base/'code/scripts/prepare_structured_v0.py'), '--directory', str(base)],
                        cwd=base/'code', env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=4*3600)
                dispatch(base, state, env)
                state.update(status='SUMMARIZING', observed_at=now())
                write(base/'queue_status.json', state)
                with (base/'summary.log').open('x') as log:
                    subprocess.run([sys.executable, '-u', '-B', str(base/'code/scripts/summarize_structured_v0.py'), '--directory', str(base)],
                        cwd=base/'code', env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=3600)
                state.update(status='STRUCTURED_COMPLETE_AWAITING_REVIEW', summary_sha256=sha(base/'summary.json'), observed_at=now())
                write(base/'queue_status.json', state)
                print('STRUCTURED_COMPLETE_NO_FURTHER_DISPATCH', base, flush=True)
        except BaseException as exc:
            state.update(status='HOLD_TECHNICAL_FAILURE', error=str(exc), observed_at=now())
            write(base/'queue_status.json', state)
            raise


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--directory', type=Path, required=True)
    main(a.parse_args().directory.resolve())
