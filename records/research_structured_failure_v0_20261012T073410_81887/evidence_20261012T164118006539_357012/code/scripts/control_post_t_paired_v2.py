"""Two independent GPU slots; released-card work migrates through the common queue."""
import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from post_t_paired_v2_common import *
from post_t_paired_v2_runtime import blocked, dependencies_ready


def device_free(gpu, expected=None):
    rows = subprocess.check_output(['nvidia-smi', '-i', str(gpu), '--query-gpu=index,uuid,name', '--format=csv,noheader'], text=True).strip().splitlines()
    if len(rows) != 1:
        raise RuntimeError('ambiguous physical GPU')
    index, uuid, name = [s.strip() for s in rows[0].split(',', 2)]
    if index != str(gpu) or expected is not None and expected != uuid:
        raise RuntimeError('physical GPU identity changed')
    if 'H100' not in name:
        raise RuntimeError('cross-card continuation requires the declared H100 hardware')
    output = subprocess.check_output(['nvidia-smi', '-i', str(gpu), '--query-compute-apps=pid', '--format=csv,noheader'], text=True)
    if any(line.strip().isdigit() and (Path('/proc') / line.strip()).exists() for line in output.splitlines()):
        return None
    return uuid


def runnable(state):
    # Saved continuations precede fresh work, subject to the original stage barriers.
    return [n for status in ('PAUSED_USER', 'PENDING') for n in ORDER
            if state['jobs'][n]['status'] == status and dependencies_ready(n, state)]


def dispatch(root, base, p, state, env, popen=subprocess.Popen, clock=time.monotonic,
             sleep=time.sleep, check=device_free, accept=accept_worker):
    active = {}
    uuids = state.setdefault('gpu_uuids', {})
    failed = False
    while True:
        for gpu, session in list(active.items()):
            n, proc, handle, began, prior = session
            row = state['jobs'][n]
            progress = base / 'jobs' / n / 'progress.json'
            if progress.exists():
                row['progress'] = read(progress)
            row['active_seconds'] = prior + clock() - began
            if proc.poll() is None and row['active_seconds'] > 3600 * card(n)['timeout_hours']:
                if not row.get('timeout_sent'):
                    row.update(timeout_sent=True, terminate_at=clock())
                    proc.terminate()
                elif clock() - row['terminate_at'] > 60:
                    proc.kill()
            rc = proc.poll()
            if rc is None:
                continue
            handle.close()
            del active[gpu]
            row.update(returncode=rc, session_ended_at=now())
            try:
                if row.get('timeout_sent'):
                    raise RuntimeError('hard per-job active-time timeout')
                if rc in (0, 75) and (base / 'jobs' / n / 'complete.json').exists():
                    accept(base, n, p)
                    row.update(status='COMPLETE', completed_at=now())
                elif rc == 75 and (base / 'jobs' / n / 'paused.json').exists():
                    row.update(status='PAUSED_USER', continuation_queued=True)
                else:
                    raise RuntimeError('worker exit ' + str(rc))
            except BaseException as exc:
                row.update(status='TECHNICAL_FAILURE', error=str(exc))
                failed = True
                write(base / 'control/stop_all.json', dict(stop=True, reason=str(exc), at=now()))
            print('PAIRED_JOB', n, row['status'], 'GPU', gpu, flush=True)
        if failed:
            state['status'] = 'HOLD_TECHNICAL_FAILURE_RELEASING_WORKERS' if active else 'HOLD_TECHNICAL_FAILURE'
            write(base / 'queue_status.json', dict(state, observed_at=now()))
            if not active:
                return False
        else:
            if all(r['status'] == 'COMPLETE' for r in state['jobs'].values()):
                return True
            if not state.get('budget8_pairing_verified') and all(state['jobs'][n]['status'] == 'COMPLETE' for n in ('H8', 'F8', 'R8')):
                from summarize_post_t_paired_v2 import audit_streams
                pairing = audit_streams(base, ['H8', 'F8', 'R8'])
                write(base / 'budget8_pairing.json', pairing)
                state['budget8_pairing_verified'] = True
            for gpu in (0, 1):
                if gpu in active or blocked(base, gpu):
                    continue
                candidates = runnable(state)
                if not candidates:
                    continue
                uuid = check(gpu, uuids.get(str(gpu)))
                if uuid is None:
                    continue
                uuids[str(gpu)] = uuid
                n = candidates[0]
                row = state['jobs'][n]
                resume = row['status'] == 'PAUSED_USER'
                folder = base / 'jobs' / n
                if folder.exists() and not resume:
                    raise RuntimeError('partial directory cannot be silently restarted: ' + n)
                entry = 'run_post_t_paired_v2.py' if n in TRAIN_ORDER else 'run_post_t_content_v2.py'
                command = [sys.executable, '-u', '-B', str(base / 'code/scripts' / entry), '--root', str(root),
                           '--directory', str(base), '--job', n, '--gpu', str(gpu)]
                if resume:
                    command.append('--resume')
                log = base / 'logs' / (n + '_' + datetime.now().strftime('%Y%m%dT%H%M%S%f') + '.log')
                handle = log.open('x')
                worker = popen(command, cwd=base / 'code', env=dict(env, CUDA_VISIBLE_DEVICES=str(gpu)),
                               stdin=subprocess.DEVNULL, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
                prior = row.get('active_seconds', 0.)
                active[gpu] = (n, worker, handle, clock(), prior)
                row.update(status='RUNNING', gpu=gpu, pid=worker.pid, command=command, log_path=str(log),
                           session_started_at=now(), continuation_queued=False)
                row.setdefault('sessions', []).append(dict(gpu=gpu, uuid=uuid, pid=worker.pid, resume=resume, log=str(log), started_at=now()))
                print('PAIRED_START', n, 'GPU', gpu, 'RESUME', resume, flush=True)
            state['status'] = 'RUNNING' if active else 'WAITING_AVAILABLE_GPU'
            state['gpu_blocked'] = {str(g): blocked(base, g) for g in (0, 1)}
            state['observed_at'] = now()
            write(base / 'queue_status.json', state)
        sleep(p['runtime']['wait_poll_seconds'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--directory', type=Path, required=True)
    a = ap.parse_args()
    root, base = dirs(a.root, a.directory)
    p = validate(read(base / 'plan.json'))
    verify_snapshot(base)
    import fcntl
    with (base / 'controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = read(base / 'queue_status.json')
        state.update(controller_pid=os.getpid(), observed_at=now())
        if state['CPU'] != 'PENDING' or any(r['status'] != 'PENDING' for r in state['jobs'].values()):
            raise RuntimeError('controller reattachment is not automatic; preserve running workers')
        try:
            observation = inspect_predecessor(root, p, accept=True)
            state['predecessor'] = observation
            with (root / 'records/post_ab_successor.lock').open('a') as lease:
                while True:
                    try:
                        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        state.update(status='WAITING_GLOBAL_LEASE', observed_at=now())
                        write(base / 'queue_status.json', state)
                        time.sleep(10)
                env = dict(os.environ, CUDA_VISIBLE_DEVICES='', PYTHONPATH=os.pathsep.join([str(base / 'code'), str(base / 'code/scripts')]))
                state.update(status='PREPARING_BOUND_REFERENCES', CPU='RUNNING', observed_at=now())
                write(base / 'queue_status.json', state)
                with (base / 'preparation.log').open('x') as log:
                    subprocess.run([sys.executable, '-u', '-B', str(base / 'code/scripts/prepare_post_t_paired_v2.py'), '--root', str(root), '--directory', str(base)],
                                   cwd=base / 'code', env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=14400)
                state['CPU'] = 'COMPLETE'
                if not dispatch(root, base, p, state, env):
                    return 2
                with (base / 'summary.log').open('x') as log:
                    subprocess.run([sys.executable, '-u', '-B', str(base / 'code/scripts/summarize_post_t_paired_v2.py'), '--directory', str(base)],
                                   cwd=base / 'code', env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=14400)
                state.update(status='PAIRED_COMPLETE_AWAITING_REVIEW', screen_sha256=sha(base / 'paired_screen.json'), observed_at=now())
                write(base / 'queue_status.json', state)
                print('PAIRED_COMPLETE_NO_FURTHER_DISPATCH', base, flush=True)
                return 0
        except BaseException as exc:
            state.update(status='CONTROLLER_INTERRUPTED', error=str(exc), observed_at=now(),
                         recovery_rule='inspect existing workers; no duplicate controller or recipe retry')
            write(base / 'queue_status.json', state)
            raise


if __name__ == '__main__':
    sys.exit(main())
