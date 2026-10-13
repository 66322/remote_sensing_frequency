"""Fixed evaluation-only successor; no optimizer or adaptive expansion."""
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

PREFIX = 'research_structured_failure_v0_'
PREDECESSOR = 'research_post_t_paired_v2_20261011T182543_3880702'
EXECUTION = '44e4df5afbaeb603e6441e7ef14ff09f228bc027'
TILES = ('3_11', '5_10')
MODELS = ('RGB', 'S1', 'MASKED', 'CONTEXT')
FAMILIES = ('pixel', 'random', 'gradient', 'matched')
JOBS = ['clean_' + t for t in TILES] + ['pair_%02d_%s' % (i, t) for i in range(1, 21) for t in TILES]


def now():
    return datetime.now().astimezone().isoformat()


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def write(p, value):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + '.tmp.' + str(os.getpid()))
    tmp.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, p)


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024**2), b''):
            h.update(b)
    return h.hexdigest()


def verify_code(base):
    for n, h in read(base / 'code_manifest.json')['files'].items():
        path = (base / 'code' / n).resolve()
        path.relative_to((base / 'code').resolve())
        if sha(path) != h:
            raise RuntimeError('snapshot changed: ' + n)


def validate(base):
    p = read(base / 'plan.json')
    if p['protocol'] != 'STRUCTURED_V0_1' or p['jobs'] != JOBS or p['optimizer_updates'] != 0:
        raise RuntimeError('plan differs')
    if p['tiles'] != list(TILES) or p['models'] != list(MODELS) or p['families'] != list(FAMILIES):
        raise RuntimeError('scope differs')
    if sha(base / 'plan.json') != read(base / 'registration.json')['plan_sha256']:
        raise RuntimeError('plan binding changed')
    if sha(base / 'source_plan.json') != p['source_plan_sha256']:
        raise RuntimeError('source scientific plan changed')
    return p


def blocked(base, gpu):
    p = read(base / 'plan.json')
    # The latest explicit request wins, across the original and successor queue.
    rows = []
    for folder in (Path(p['predecessor']), base):
        f = folder / 'control' / ('gpu_%d.json' % gpu)
        if f.exists():
            row = read(f)
            rows.append((datetime.fromisoformat(row['requested_at']), bool(row['blocked'])))
    return max(rows, key=lambda x: x[0])[1] if rows else False


class Released(Exception):
    pass


def poll(base, gpu):
    if (base / 'control/stop_all.json').exists():
        raise Released('technical HOLD')
    if blocked(base, gpu):
        raise Released('user GPU release')


def ready_jobs(state):
    clean = all(state['jobs']['clean_' + t]['status'] == 'COMPLETE' for t in TILES)
    return [n for status in ('PAUSED_USER', 'PENDING') for n in JOBS
            if state['jobs'][n]['status'] == status and (n.startswith('clean_') or clean)]


def accept(base, job):
    row = read(base / 'jobs' / job / 'complete.json')
    if row['job'] != job or row['plan_sha256'] != sha(base / 'plan.json') or row['optimizer_updates'] != 0:
        raise RuntimeError('job binding differs')
    if row['code_sha256'] != sha(base / 'code_manifest.json') or row['mask_manifest_sha256'] != sha(base / 'mask_manifest.json'):
        raise RuntimeError('job snapshot differs')
    expected = 4 if job.startswith('clean_') else 16
    if len(row['records']) != expected:
        raise RuntimeError('incomplete output group')
    if sha(base/'jobs'/job/'input_binding.json') != row['input_binding_sha256']:
        raise RuntimeError('input binding changed')
    if job.startswith('clean_'):
        f = base/'jobs'/job/'endpoint_checks.json'
        if sha(f) != row['endpoint_checks_sha256']:
            raise RuntimeError('endpoint check changed')
        checks = read(f)['checks']
        if len(checks) != 3 or not all(x['exact'] for x in checks):
            raise RuntimeError('endpoint not reproduced')
    for name, digest in row['records'].items():
        f = base / 'jobs' / job / name
        if sha(f) != digest:
            raise RuntimeError('case record changed')
        case = read(f)
        if sha(f.parent / case['prediction_file']) != case['prediction_sha256']:
            raise RuntimeError('prediction changed')
    return row
