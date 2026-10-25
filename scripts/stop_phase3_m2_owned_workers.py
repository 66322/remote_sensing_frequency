"""Inspect or explicitly abort the bound M2 run to release its two GPUs.

This is an abort, not a pause/resume implementation. It never starts work or
signals a PID that is not both a child of the verified M2 controller and a
compute process on one of the two registered GPU UUIDs.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import time


ROOT = Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro')
RECORDS = ROOT / 'records'
M2 = RECORDS / 'research_phase3_m2_revision_20261024T092814_2738345'
COMBINED = RECORDS / 'research_phase3_combined_revision_20261024T092814_2738345'
LATCH = RECORDS / 'phase3_engineering_restart_20261024_once.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def proc_args(pid):
    return [x.decode('utf-8') for x in Path('/proc', str(pid), 'cmdline').read_bytes().split(b'\0') if x]


def proc_parent(pid):
    for line in Path('/proc', str(pid), 'status').read_text(encoding='utf-8').splitlines():
        if line.startswith('PPid:'):
            return int(line.split(':', 1)[1].strip())
    raise RuntimeError('process parent missing: ' + str(pid))


def bound_entry(pid, mode, directory):
    args = proc_args(pid)
    for key, value in (('--mode', mode), ('--directory', str(directory))):
        if key not in args or args[args.index(key) + 1] != value:
            raise RuntimeError('unexpected process command line for ' + mode + ': ' + str(pid))


def gpu_apps():
    output = subprocess.check_output(
        ['nvidia-smi', '--query-compute-apps=pid,gpu_uuid', '--format=csv,noheader,nounits'],
        text=True, timeout=20)
    rows = []
    for line in output.splitlines():
        parts = [part.strip() for part in line.split(',')]
        if len(parts) != 2:
            raise RuntimeError('unexpected nvidia-smi compute row: ' + line)
        rows.append((int(parts[0]), parts[1]))
    return rows


def inspect():
    latch = read(LATCH)
    if (latch.get('status') != 'CONTROLLERS_LAUNCHED'
            or latch.get('m2_directory') != str(M2)
            or latch.get('combined_directory') != str(COMBINED)):
        raise RuntimeError('single-launch receipt does not bind this exact run')
    status = read(M2 / 'queue_status.json')
    if status.get('status') != 'RUNNING':
        raise RuntimeError('M2 is not RUNNING; inspect status before any signal')
    m2_pid = int(latch['m2_controller_pid'])
    combined_pid = int(latch['combined_controller_pid'])
    bound_entry(m2_pid, 'm2', M2)
    bound_entry(combined_pid, 'combined', COMBINED)
    inventory = read(M2 / 'gpu_inventory_launch.json')['selected']
    uuids = {int(gpu): inventory[str(gpu)][1] for gpu in (0, 1)}
    apps = gpu_apps()
    workers = {}
    for gpu, uuid in uuids.items():
        matches = [pid for pid, current_uuid in apps if current_uuid == uuid]
        if len(matches) != 1:
            raise RuntimeError('GPU ' + str(gpu) + ' has ' + str(len(matches))
                               + ' compute processes; exact single-owner check failed')
        worker_pid = matches[0]
        if proc_parent(worker_pid) != m2_pid:
            raise RuntimeError('GPU ' + str(gpu) + ' compute PID is not owned by M2 controller')
        bound_entry(worker_pid, 'm2', M2)
        workers[gpu] = worker_pid
    return dict(m2_controller_pid=m2_pid, combined_controller_pid=combined_pid,
                workers=workers, gpu_uuids=uuids, queue_status=status)


def abort_current_run(snapshot):
    # Recheck the exact target immediately before signalling it.
    target = snapshot['workers'][0]
    if proc_parent(target) != snapshot['m2_controller_pid']:
        raise RuntimeError('GPU 0 worker parent changed before abort')
    bound_entry(target, 'm2', M2)
    stamp = datetime.now(timezone.utc).astimezone().strftime('%Y%m%dT%H%M%S%z')
    marker = M2 / ('manual_abort_intent_' + stamp + '.json')
    marker.write_text(json.dumps(dict(reason='user_requested_release_gpu0_gpu1',
                                      resumable=False, automatic_retry=False,
                                      m2_controller_pid=snapshot['m2_controller_pid'],
                                      combined_controller_pid=snapshot['combined_controller_pid'],
                                      gpu_workers=snapshot['workers'],
                                      observed_at=datetime.now(timezone.utc).astimezone().isoformat()),
                                 ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.kill(target, signal.SIGTERM)
    print('M2_ABORT_REQUESTED', marker, 'signalled_owned_gpu0_worker', target, flush=True)
    # The original controller detects this worker exit and cleans its own other
    # worker, CPU pool, and packets. Never kill unrelated GPU processes here.
    deadline = time.monotonic() + 120
    owned = set(snapshot['workers'].values())
    while time.monotonic() < deadline:
        remaining = [pid for pid, _ in gpu_apps() if pid in owned]
        if not remaining:
            print('OWNED_GPU_WORKERS_RELEASED', flush=True)
            break
        time.sleep(2)
    else:
        print('OWNED_GPU_WORKERS_STILL_PRESENT_MANUAL_REVIEW_REQUIRED', remaining, flush=True)
    print('M2_STATUS_AFTER_SIGNAL', json.dumps(read(M2 / 'queue_status.json'), ensure_ascii=False), flush=True)
    print('COMBINED_MAY_STOP_AFTER_ITS_NEXT_FIVE_MINUTE_POLL', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--inspect', action='store_true', help='read-only ownership check')
    action.add_argument('--abort-current-run', action='store_true',
                        help='irreversibly stop this M2 attempt and release its GPUs')
    args = parser.parse_args()
    snapshot = inspect()
    print('BOUND_M2_OWNERSHIP', json.dumps(snapshot, ensure_ascii=False), flush=True)
    if args.abort_current_run:
        abort_current_run(snapshot)


if __name__ == '__main__':
    main()
