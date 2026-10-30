"""Immutable zero-training design; pure scheduling and atomic evidence IO."""
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

PREFIX = 'research_phase15_recoverability_'
STRUCTURED = 'research_structured_failure_v0_20261012T073410_81887'
PAIRED = 'research_post_t_paired_v2_20261011T182543_3880702'
TILES = ('3_11', '5_10')
FAMILIES = ('pixel', 'random', 'gradient', 'matched')
DSM = ('intact', 'crop_shuffle', 'tile_shuffle', 'zero')
EXPERTS = ('S1', 'S13', 'R16', 'DSM', 'RGB')  # Oracle priority.
PROTOCOL = 'PHASE15_V1_2_EXECUTION'


def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp.' + str(os.getpid()))
    tmp.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def within(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    path.relative_to(root)
    return path


def key(*parts):
    return int.from_bytes(hashlib.sha256(('/'.join(map(str, (PROTOCOL, *parts)))).encode()).digest()[:16], 'little')


def case(model, tile, dsm='intact', realization=0, family='clean', ratio=25):
    return dict(model=model, tile=tile, dsm=dsm, realization=realization, family=family, ratio=ratio)


def case_id(c):
    return '{model}_{tile}_{dsm}_{realization:02d}_{family}_{ratio}'.format(**c)


def jobs():
    rows = []
    for tile in TILES:
        for model in ('S1', 'R16'):
            for ds in DSM:
                c = case(model, tile, ds)
                rows.append(dict(id='ref_' + case_id(c), kind='reference', cases=[c]))
        for model in ('S13', 'DSM'):
            c = case(model, tile)
            rows.append(dict(id='ref_' + case_id(c), kind='reference', cases=[c]))
    # Small immutable batches: both physical cards can process each model.
    for start in (1, 6, 11, 16):
        for tile in TILES:
            for ds in DSM:
                for model in ('S1', 'R16'):
                    rows.append(dict(id=f'A_{start:02d}_{tile}_{ds}_{model}', kind='missing',
                        cases=[case(model, tile, ds, i, f) for i in range(start, start + 5) for f in FAMILIES]))
            rows.append(dict(id=f'D_{start:02d}_{tile}', kind='missing',
                cases=[case('S13', tile, 'intact', i, f) for i in range(start, start + 5) for f in FAMILIES]))
            rows.append(dict(id=f'B_{start:02d}_{tile}', kind='missing',
                cases=[case('S1', tile, 'intact', i, 'pixel', r) for i in range(start, start + 5) for r in (5, 10)]))
    return rows


def ready(state, rows):
    refs = all(state[j['id']]['status'] == 'COMPLETE' for j in rows if j['kind'] == 'reference')
    return [j for j in rows if state[j['id']]['status'] == 'PENDING' and (refs or j['kind'] == 'reference')]


def validate(base):
    base = Path(base)
    p = read(base / 'plan.json')
    if p['protocol'] != PROTOCOL or p['jobs'] != jobs() or p['tiles'] != list(TILES):
        raise RuntimeError('immutable task design changed')
    if p['optimizer_updates'] != 0 or p['physical_gpus'] != [0, 1] or p['wall_deadline_hours'] is not None:
        raise RuntimeError('resource/zero-training contract changed')
    if sha(base / 'plan.json') != read(base / 'registration.json')['plan_sha256']:
        raise RuntimeError('plan changed after registration')
    for name, digest in p['source_files'].items():
        if sha(base / name) != digest:
            raise RuntimeError('source receipt changed: ' + name)
    if 'source_receipts' in p:
        for directory in (Path(p['structured']),Path(p['paired'])):
            receipt=p['source_receipts'][directory.name]
            if sha(directory/'plan.json')!=receipt['plan_sha256'] or sha(directory/'code_manifest.json')!=receipt['code_sha256']:
                raise RuntimeError('immutable original plan/code receipt changed')
    return p


def verify_code(base):
    for name, digest in read(Path(base) / 'code_manifest.json')['files'].items():
        if sha(within(Path(base) / 'code' / name, Path(base) / 'code')) != digest:
            raise RuntimeError('execution code changed: ' + name)


def binding(base):
    return {n: sha(Path(base) / n) for n in ('plan.json', 'code_manifest.json', 'preparation_complete.json')}


def accept_job(base, job):
    row = read(Path(base) / 'jobs' / job['id'] / 'complete.json')
    if row['binding'] != binding(base) or row['optimizer_updates'] != 0 or row['cases'] != [case_id(c) for c in job['cases']]:
        raise RuntimeError('worker completion binding differs')
    for c in job['cases']:
        f = Path(base) / 'cases' / (case_id(c) + '.json')
        if sha(f) != row['records'][case_id(c)]:
            raise RuntimeError('completed record changed')
        r = read(f)
        for artifact in r['arrays'].values():
            if sha(within(artifact['path'], base)) != artifact['sha256']:
                raise RuntimeError('completed array changed')
    return row
