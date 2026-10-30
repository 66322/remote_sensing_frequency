"""Small provenance and atomic IO helpers shared by D24 commands."""
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

SCOPE = Path('/home/jovyan/zzx')


def now():
    return datetime.now().astimezone().isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(8 * 1024 ** 2), b''):
            value.update(block)
    return value.hexdigest()


def within(path, parent):
    path = Path(path).resolve()
    path.relative_to(Path(parent).resolve())
    return path


def directories(root, base):
    root = within(root, SCOPE)
    base = within(base, root / 'records')
    if not base.name.startswith('research_d24_overnight_'):
        raise ValueError('unexpected D24 directory')
    return root, base


def validate_plan(plan):
    jobs = plan['jobs']
    ids = {j['id'] for j in jobs}
    if len(ids) != 15 or len(jobs) != 15 or sum(j['optimizer_steps'] for j in jobs) != 60000:
        raise ValueError('D24 job budget mismatch')
    if plan['aliases'] != {'D3': 'A2'} or plan['physical_gpus'] != [0, 1]:
        raise ValueError('D24 alias/device mismatch')
    if plan['data']['test6_loaded'] or plan['data']['independent_final_loaded']:
        raise ValueError('test loading forbidden')
    if plan['training']['physical_batch'] != 16 or plan['training']['gradient_accumulation']:
        raise ValueError('D24 physical batch contract mismatch')
    if set(plan['data']['fit12']) & set(plan['data']['validation'] + plan['data']['train_held4']):
        raise ValueError('tile partition mismatch')
    for job in jobs:
        if job['seed'] != 42 or job['optimizer_steps'] != 4000 or job['gpu'] not in (0, 1):
            raise ValueError('job contract mismatch')
        for control in [job.get('control')] + job.get('additional_controls', []):
            if control and control not in ids:
                raise ValueError('missing matched control')
    return jobs
