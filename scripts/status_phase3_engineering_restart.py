"""Read-only current status for the explicitly bound engineering restart."""
import argparse
from collections import deque
from datetime import datetime
import json
from pathlib import Path
import subprocess

ROOT = Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro')
LATCH = 'phase3_engineering_restart_20261024_once.json'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def snapshot(records):
    records = Path(records).resolve()
    latch = records / LATCH
    if not latch.exists():
        return dict(status='NOT_REGISTERED_OR_BOOTSTRAP_STILL_CHECKING')
    result = dict(bootstrap_receipt=read(latch), observed_at=datetime.now().astimezone().isoformat())
    for key in ('m2_directory', 'combined_directory'):
        base = Path(result['bootstrap_receipt'][key]).resolve()
        if base.parent != records:
            raise RuntimeError('status target outside records')
        row = dict(directory=str(base))
        for name in ('queue_status.json', 'preparation_progress.json', 'runtime_revision_failure.json',
                     'runtime_revision_entry_failure.json', 'controller_failure.json'):
            if (base / name).exists():
                row[name] = read(base / name)
        if key == 'm2_directory':
            progress = sorted((base / 'jobs').glob('*/progress.json'), key=lambda p: p.stat().st_mtime)
            row['jobs_with_progress'] = len(progress)
            row['latest_training_progress'] = [dict(job=p.parent.name, **read(p)) for p in progress[-2:]]
            failures = sorted((base / 'failures').glob('*.json'), key=lambda p: p.stat().st_mtime)
            row['job_failure_count'] = len(failures)
            row['first_job_failures'] = [read(p) for p in failures[:2]]
        result[key] = row
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tail', type=int, default=40)
    args = parser.parse_args()
    if not 0 <= args.tail <= 200:
        raise RuntimeError('tail must be between 0 and 200')
    state = snapshot(ROOT / 'records')
    print(json.dumps(state, ensure_ascii=False, indent=2), flush=True)
    if 'bootstrap_receipt' not in state:
        return
    receipt = state['bootstrap_receipt']
    pids = [str(receipt[k]) for k in ('m2_controller_pid', 'combined_controller_pid') if receipt.get(k)]
    if pids:
        subprocess.run(['ps', '-p', ','.join(pids), '-o', 'pid,ppid,stat,etime,%cpu,%mem,args'], check=False)
    for key in ('m2_directory', 'combined_directory'):
        log = Path(receipt[key]) / 'nohup.log'
        if log.exists() and args.tail:
            print('\nLOG', log, flush=True)
            with log.open(encoding='utf-8', errors='replace') as source:
                print(''.join(deque(source, maxlen=args.tail)), flush=True)
    subprocess.run(['nvidia-smi', '-i', '0,1'], check=False)


if __name__ == '__main__':
    main()
