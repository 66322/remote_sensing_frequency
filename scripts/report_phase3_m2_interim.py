"""Read existing M2 age counts only. No model, dataset pixels, inference or writes."""
import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path


AGES = (8000, 16000, 24000, 32000)
ROOT = Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def checked_cm(value):
    if (not isinstance(value, list) or len(value) != 6 or
            any(not isinstance(row, list) or len(row) != 6 for row in value) or
            any(type(n) is not int or n < 0 for row in value for n in row)):
        raise ValueError('Expected a nonnegative integer 6x6 confusion matrix')
    return value


def pool_tiles(counts, expected):
    if len(expected) != 4 or len(set(expected)) != 4:
        raise ValueError('M2 requires four distinct outer evaluation tiles')
    if set(counts) - set(expected):
        raise ValueError('Unexpected evaluation tile')
    if set(counts) != set(expected):
        return None
    result = {scope: [[0] * 6 for _ in range(6)] for scope in ('nb', 'full')}
    for tile in expected:
        for scope in result:
            cm = checked_cm(counts[tile][scope])
            for i in range(6):
                for j in range(6):
                    result[scope][i][j] += cm[i][j]
    return result


def fg5(cm):
    cm = checked_cm(cm)
    values = []
    for i in range(5):
        denominator = sum(cm[i]) + sum(row[i] for row in cm) - cm[i][i]
        if denominator == 0:
            return None
        values.append(cm[i][i] / denominator)
    return 100 * sum(values) / 5


def annotate_deltas(rows):
    def key(row):
        return row['fold'], row['seed'], row['step'], tuple(sorted(row['tiles']))
    baselines = {key(row): row for row in rows
                 if row['role'] == 'dsm_student' and row['arm'] == 'D0'
                 and row['eligible']}
    for row in rows:
        row['delta_d0_nb_pp'] = None
        if row['role'] != 'dsm_student' or not row['eligible'] or row['step'] != 32000:
            continue
        baseline = baselines.get(key(row))
        if baseline is None:
            continue
        if row['gt_support'] != baseline['gt_support']:
            raise ValueError('Same comparison block has different GT support')
        for field in ('initial_state_sha256', 'sample_stream_sha256'):
            if not row.get(field) or not baseline.get(field):
                break
            if row[field] != baseline[field]:
                raise ValueError('Paired initialization/sample stream mismatch')
        else:
            if row['nb_fg5'] is not None and baseline['nb_fg5'] is not None:
                row['delta_d0_nb_pp'] = row['nb_fg5'] - baseline['nb_fg5']


def collect(base, step):
    base = Path(base)
    if step not in AGES:
        raise ValueError('Unknown registered trajectory age')
    binding = read(base / 'registration.json')['binding']
    folds = read(base / 'folds.json')['folds']
    rows = []
    for parameters in sorted((base / 'jobs').glob('*/parameters.json')):
        folder = parameters.parent
        params = read(parameters)
        job = params['job']
        if params['binding'] != binding or job['id'] != folder.name:
            raise ValueError('Parameter binding mismatch: ' + folder.name)
        if job['role'] not in ('rgb_reference', 'rgb_oof_teacher', 'dsm_student'):
            raise ValueError('Unknown model role')
        expected = folds[job['fold']]['evaluation']
        complete = read(folder / 'complete.json') if (folder / 'complete.json').is_file() else None
        if complete is not None and (complete['binding'] != binding or
                         complete['job'] != job['id'] or
                         complete['optimizer_updates'] != 32000):
            raise ValueError('Endpoint receipt mismatch: ' + folder.name)
        counts, sources = {}, []
        for path in sorted((base / 'trajectory_counts' / job['id']).glob(str(step) + '_*.json')):
            raw = path.read_bytes()
            data = json.loads(raw.decode('utf-8'))
            meta = data['metadata']
            if meta['job'] != job['id'] or meta['step'] != step or meta['tile'] in counts:
                raise ValueError('Trajectory identity/duplicate mismatch: ' + str(path))
            counts[meta['tile']] = data['counts']
            sources.append({'path': str(path.relative_to(base)),
                            'sha256': hashlib.sha256(raw).hexdigest()})
        pooled = pool_tiles(counts, expected)
        eligible = pooled is not None and (step != 32000 or complete is not None)
        row = {k: job[k] for k in ('id', 'role', 'modality', 'fold', 'seed', 'arm')}
        row.update(step=step, tiles=list(expected), covered_tiles=sorted(counts),
                   eligible=eligible, endpoint_receipt=bool(complete),
                   endpoint_sha256_from_receipt=complete['checkpoint_sha256'] if complete else None,
                   initial_state_sha256=complete['initial_state_sha256'] if complete else params.get('initial_state_sha256'),
                   sample_stream_sha256=complete['batch_stream_sha256'] if complete else None,
                   nb_fg5=fg5(pooled['nb']) if eligible else None,
                   full_gt_fg5=fg5(pooled['full']) if eligible else None,
                   gt_support={s: [sum(r) for r in pooled[s]] for s in pooled} if eligible else None,
                   count_sources=sources)
        rows.append(row)
    annotate_deltas(rows)
    return dict(schema_version=1, status='INTERIM_CLEAN_SINGLE_MODAL_ONLY',
                observed_at=datetime.now().astimezone().isoformat(), directory=str(base),
                step=step, binding=binding, rows=rows,
                scope='Outer development tiles; 512-pixel inset; nb fg5 primary, full-GT fg5 diagnostic',
                limitations='No fusion/rescue/harm gates; no checkpoint selection or queue mutation; '
                            'endpoint SHA is referenced from receipt, not freshly rehashed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--step', type=int, choices=AGES, default=32000)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    base = args.directory.resolve()
    if base.parent != ROOT or not base.name.startswith('research_phase3_m2_'):
        parser.error('Read only an explicitly named M2 run under the records root')
    result = collect(base, args.step)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(result['status'], result['observed_at'])
    print('SCOPE:', result['scope'])
    writer = csv.writer(sys.stdout, delimiter='\t', lineterminator='\n')
    writer.writerow(['job', 'role', 'age', 'tiles', 'eligible', 'nb_fg5_%',
                     'full_GT_fg5_%', 'delta_D0_nb_pp'])
    for row in result['rows']:
        def fmt(value):
            return 'NA' if value is None else format(value, '.4f')
        writer.writerow([row['id'], row['role'], row['step'],
                         str(len(row['covered_tiles'])) + '/4', row['eligible'],
                         fmt(row['nb_fg5']), fmt(row['full_gt_fg5']), fmt(row['delta_d0_nb_pp'])])
    print('ELIGIBLE_ROWS', sum(row['eligible'] for row in result['rows']))
    print('NA: incomplete age/endpoint, absent class, no verified 32k D0 pairing, or non-DSM role.')
    print(result['limitations'])


if __name__ == '__main__':
    main()
