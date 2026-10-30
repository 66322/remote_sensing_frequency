"""Offline M2 analysis, then explicitly authorized removal of bound-run large files.

No Torch, model loading, inference, training, remote upload or hashing. NumPy only.
Reuse the unchanged Linux unlink helper used by the successful first cleanup.
Default: analysis and candidate plan only. --apply: analysis must pass before unlink.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime
import gzip
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import numpy as np

ROOT = Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro')
FIRST = '6374e41bc9b47fdccf9062d8b7e750afa359ef9d'
RECEIPT = 'phase3_m2_final_compaction_20261029.json'
SEEDS = (42, 17, 2026)
ARMS = ('D0', 'DSelf', 'DClean', 'DF', 'DShuffle', 'DEntropy', 'DMix')
CONDITIONS = ('clean', 'down2', 'down4', 'down8', 'blur2', 'noise005', 'dsm_down4', 'dsm_shift8')
ALPHAS = (0, .05, .1, .2, .4, .6, 1)
REGIONS = ('all', 'damaged', 'healthy')
WEIGHTS = {'.pt', '.pth', '.ckpt', '.safetensors'}
RAW_COUNTS = {'case_counts.jsonl.gz', 'all_aggregates.jsonl.gz',
              'publication/F0_counts.jsonl.gz', 'publication/F1_counts.jsonl.gz',
              'publication/F2_counts.jsonl.gz'}
PROTECTED = {'data', 'datasets', 'inputs', 'pretrained', 'source', 'code', 'snapshot', 'frozen_source'}


def emit(phase, **values):
    print(phase, json.dumps(values, ensure_ascii=False), flush=True)


def dumps(x):
    return json.dumps(x, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def metric(cm):
    a = np.asarray(cm, dtype=np.int64)
    d = a.sum(0) + a.sum(1) - a.diagonal()
    iou = [None if d[k] == 0 else float(100 * a[k, k] / d[k]) for k in range(5)]
    # Match phase3_m2_common.cm_metric: all five classes must have support.
    return (None if any(x is None for x in iou) else float(np.mean(iou))), iou


def optional_delta(a, b):
    return None if a is None or b is None else a - b


def flow(joint):
    j = np.asarray(joint, dtype=np.int64)
    right = sum(int(j[g, g, :].sum()) for g in range(5))
    wrong = int(j[:5].sum()) - right
    rescued = sum(int(j[g, :, g].sum() - j[g, g, g]) for g in range(5))
    harmed = sum(int(j[g, g, :].sum() - j[g, g, g]) for g in range(5))
    return [right, wrong, rescued, harmed]


def rates(v):
    right, wrong, rescued, harmed = [int(x) for x in v]
    return dict(rgb_correct=right, rgb_wrong=wrong, rescued=rescued, harmed=harmed,
                rescue_pp=None if not wrong else 100 * rescued / wrong,
                harm_pp=None if not right else 100 * harmed / right,
                net_correct_pixels=rescued-harmed)


def capsule(counts):
    out = {}
    for scope in ('nb', 'full'):
        out[scope] = {}
        for region in REGIONS:
            z = counts[scope][region]
            out[scope][region] = dict(cms=z['cms'], logit_cm=z['logit_cm'],
                                     dsm_flow=flow(z['joint']), fusion_flow=flow(z['fusion_joint']))
    for key in ('aux', 'margin_counts', 'calibration'):
        out[key] = counts[key]
    return out


def arrays(x):
    if isinstance(x, dict):
        return {k: arrays(v) for k, v in x.items()}
    return np.asarray(x) if isinstance(x, list) else x


def add(a, b):
    if isinstance(a, dict):
        for k in a:
            a[k] = add(a[k], b[k])
        return a
    return a + b


def pool_into(groups, key, value):
    if key not in groups:
        groups[key] = arrays(value)
    else:
        add(groups[key], arrays(value))


class Table:
    def __init__(self, path, fields):
        self.path = path
        self.file = (gzip.open(path, 'wt', encoding='utf-8', newline='')
                     if path.suffix == '.gz' else path.open('w', encoding='utf-8', newline=''))
        self.writer = csv.DictWriter(self.file, fields, extrasaction='raise')
        self.writer.writeheader()
        self.rows = 0

    def put(self, **row):
        self.writer.writerow(row)
        self.rows += 1

    def close(self):
        self.file.close()


def keymeta(key):
    r, d, arm, condition = key
    return dict(rseed=r, dseed=d, arm=arm, condition=condition, pairing='same' if r == d else 'cross')


def analyze_aggregates(m2, output):
    groups, folds, seen = {}, {}, set()
    cases = 0
    file = output / 'tile_sufficient_counts.jsonl.gz'
    with gzip.open(file, 'wt', encoding='utf-8', compresslevel=6) as sink:
        with gzip.open(m2 / 'all_aggregates.jsonl.gz', 'rt', encoding='utf-8') as source:
            for line in source:
                z = json.loads(line)
                m = z['metadata']
                key = tuple(m[k] for k in ('rseed', 'dseed', 'arm', 'condition'))
                identity = (m['tile'],) + key
                if identity in seen:
                    raise RuntimeError('Duplicate aggregate identity')
                seen.add(identity)
                expected = 20 if m['condition'] in CONDITIONS[1:6] else 1
                if (m['rseed'] not in SEEDS or m['dseed'] not in SEEDS or
                        m['arm'] not in ARMS or m['condition'] not in CONDITIONS or z['cases'] != expected):
                    raise RuntimeError('Unexpected aggregate identity/coverage')
                cases += z['cases']
                small = capsule(z['counts'])
                sink.write(dumps(dict(metadata=m, cases=z['cases'], counts=small)) + '\n')
                pool_into(groups, key, small)
                if m['rseed'] == m['dseed']:
                    pool_into(folds, (m['fold'],) + key, small)
                if len(seen) % 1000 == 0:
                    emit('AGGREGATE_PROGRESS', groups_read=len(seen))
    tiles = {v[0] for v in seen}
    expected_ids = {(t, r, d, a, cond) for t in tiles for r in SEEDS for d in SEEDS
                    for a in ARMS for cond in CONDITIONS}
    if len(tiles) != 12 or seen != expected_ids or cases != 77868 or len(folds) != 504:
        raise RuntimeError('Aggregate coverage incomplete')
    return groups, folds, dict(aggregates=len(seen), cases=cases, tiles=sorted(tiles))


def analyze_cases(m2, output):
    # Per-case numerical summaries preserve mask family and realization variation.
    # All pairings are covered, avoiding any hidden loss of cross-seed diagnostics.
    fields = ['tile', 'fold', 'rseed', 'dseed', 'arm', 'condition', 'family', 'realization',
              'region', 'rgb_miou', 'dsm_miou', 'fusion_miou', 'rgb_correct', 'rgb_wrong',
              'rescued', 'harmed', 'rescue_pp', 'harm_pp', 'net_correct_pixels']
    table = Table(output / 'per_case_primary_metrics.csv.gz', fields)
    family = {}
    seen = set()
    n = 0
    try:
        with gzip.open(m2 / 'case_counts.jsonl.gz', 'rt', encoding='utf-8') as source:
            for line in source:
                z = json.loads(line)
                m = z['metadata']
                ident = tuple(m[k] for k in fields[:8])
                if ident in seen:
                    raise RuntimeError('Duplicate case identity')
                seen.add(ident)
                meta = {k: m[k] for k in fields[:8]}
                for region in REGIONS:
                    row = z['counts']['nb'][region]
                    cms = row['cms']
                    actual = flow(row['fusion_joint'])
                    table.put(**meta, region=region, rgb_miou=metric(cms[0])[0],
                              dsm_miou=metric(cms[-1])[0], fusion_miou=metric(cms[2])[0], **rates(actual))
                    if m['rseed'] == m['dseed']:
                        key = (m['rseed'], m['arm'], m['condition'], m['family'], region)
                        pool_into(family, key, dict(cms=[cms[i] for i in (0, 2, 6)],
                                                   fusion_flow=actual))
                n += 1
                if n % 5000 == 0:
                    emit('CASE_PROGRESS', cases_read=n, expected=77868)
        if n != 77868:
            raise RuntimeError('Case coverage incomplete')
    finally:
        table.close()
    t = Table(output / 'mask_family_metrics.csv',
              ['seed', 'arm', 'condition', 'family', 'region', 'rgb_miou', 'fusion_miou',
               'dsm_miou', 'rgb_correct', 'rgb_wrong', 'rescued', 'harmed', 'rescue_pp',
               'harm_pp', 'net_correct_pixels'])
    for (seed, arm, cond, fam, region), z in sorted(family.items()):
        t.put(seed=seed, arm=arm, condition=cond, family=fam, region=region,
              rgb_miou=metric(z['cms'][0])[0], fusion_miou=metric(z['cms'][1])[0],
              dsm_miou=metric(z['cms'][2])[0], **rates(z['fusion_flow']))
    t.close()
    family_deltas = []
    for fam in sorted({k[3] for k in family if k[2] == 'down4'}):
        for region in REGIONS:
            values = []
            for s in SEEDS:
                df = metric(family[(s,'DF','down4',fam,region)]['cms'][1])[0]
                d0 = metric(family[(s,'D0','down4',fam,region)]['cms'][1])[0]
                # Some mask-family/ROI subsets lack one of the five foreground
                # classes. Keep their delta undefined, as for other ROI tables.
                values.append(optional_delta(df, d0))
            family_deltas.append(dict(family=fam, region=region,
                                      DF_minus_D0_miou_pp=values,
                                      valid_seed_count=sum(v is not None for v in values)))
    return dict(cases=n, metric_rows=table.rows, mask_family_rows=t.rows, down4_family_deltas=family_deltas)


def export_tables(groups, folds, output):
    base = ['rseed', 'dseed', 'arm', 'condition', 'pairing']
    tables = {
        'alpha': Table(output / 'alpha_roi_class_metrics.csv.gz', base + ['scope', 'region', 'alpha', 'miou'] + ['iou_' + str(i) for i in range(5)]),
        'flow': Table(output / 'actual_fusion_and_dsm_flows.csv', base + ['scope', 'region', 'target', 'rgb_correct', 'rgb_wrong', 'rescued', 'harmed', 'rescue_pp', 'harm_pp', 'net_correct_pixels']),
        'aux': Table(output / 'boundary_and_fulltile_metrics.csv', base + ['support', 'target', 'miou'] + ['iou_' + str(i) for i in range(5)]),
        'cal': Table(output / 'calibration_margin.csv', base + ['diagnostic', 'target', 'alpha', 'pixels', 'value']),
        'fold': Table(output / 'fold_primary_metrics.csv', ['fold'] + base + ['rgb_miou', 'dsm_miou', 'fusion_miou']),
    }
    for key, z in sorted(groups.items()):
        m = keymeta(key)
        for scope in ('nb', 'full'):
            for region in REGIONS:
                row = z[scope][region]
                for alpha, cm in zip(ALPHAS, row['cms']):
                    miou, iou = metric(cm)
                    tables['alpha'].put(**m, scope=scope, region=region, alpha=alpha, miou=miou,
                                        **{'iou_' + str(i): v for i, v in enumerate(iou)})
                for target in ('fusion', 'dsm'):
                    tables['flow'].put(**m, scope=scope, region=region, target=target, **rates(row[target + '_flow']))
        for support, cms in z['aux'].items():
            for target, cm in zip(('rgb', 'dsm', 'fusion'), cms):
                miou, iou = metric(cm)
                tables['aux'].put(**m, support=support, target=target, miou=miou,
                                  **{'iou_' + str(i): v for i, v in enumerate(iou)})
        for target, cal in z['calibration'].items():
            n = int(cal['count'].sum())
            ece = None if not n else float(100 * np.abs(cal['correct']-cal['confidence']).sum()/n)
            nll = None if not n else float(cal['nll_sum']/n)
            for name, value in [('six_class_ECE_percent', ece), ('six_class_NLL_nats', nll)]:
                tables['cal'].put(**m, diagnostic=name, target=target, alpha='', pixels=n, value=value)
        wrong = int(z['nb']['all']['fusion_flow'][1])
        for alpha, v in zip(ALPHAS, z['margin_counts']):
            possible = int(v.sum())
            tables['cal'].put(**m, diagnostic='RGB_wrong_margin_upper_bound_percent', target='fusion',
                              alpha=alpha, pixels=wrong, value=None if not wrong else 100*possible/wrong)
    for key, z in sorted(folds.items()):
        row = z['nb']['all']['cms']
        tables['fold'].put(fold=key[0], **keymeta(key[1:]), rgb_miou=metric(row[0])[0],
                          dsm_miou=metric(row[-1])[0], fusion_miou=metric(row[2])[0])
    for t in tables.values():
        t.close()
    return {k: v.rows for k, v in tables.items()}


def summarize(groups, gates):
    def pooled(seed, arm, cond='down4', region='all'):
        return groups[(seed, seed, arm, cond)]['nb'][region]
    comparisons = {}
    for arm in ARMS:
        if arm == 'DF':
            continue
        rescue = [rates(pooled(s, 'DF')['dsm_flow'])['rescue_pp'] - rates(pooled(s, arm)['dsm_flow'])['rescue_pp'] for s in SEEDS]
        fusion = [metric(pooled(s, 'DF')['cms'][2])[0] - metric(pooled(s, arm)['cms'][2])[0] for s in SEEDS]
        comparisons[arm] = dict(dsm_rescue_delta_pp=rescue, fusion_delta_pp=fusion)
        for name, values in [('G1_rescue_DF-'+arm, rescue), ('G2_fusion_DF-'+arm, fusion)]:
            if name in gates['checks']:
                expected = gates['checks'][name]['values_pp']
                if not np.allclose(values, expected, rtol=0, atol=1e-8):
                    raise RuntimeError('Recomputed primary result disagrees with accepted gate: '+name)
    alpha = []
    for a, i in zip(ALPHAS, range(7)):
        delta = [metric(pooled(s, 'DF')['cms'][i])[0]-metric(pooled(s, 'D0')['cms'][i])[0] for s in SEEDS]
        alpha.append(dict(alpha=a, DF_minus_D0_miou_pp=delta, mean_delta_pp=float(np.mean(delta))))
    actual = {a: [rates(pooled(s, a)['fusion_flow']) for s in SEEDS] for a in ARMS}
    diagnostic = []
    for cond in CONDITIONS:
        for region in REGIONS:
            diffs = []
            for s in SEEDS:
                a = metric(pooled(s,'DF',cond,region)['cms'][2])[0]
                b = metric(pooled(s,'D0',cond,region)['cms'][2])[0]
                diffs.append(None if a is None or b is None else a-b)
            diagnostic.append(dict(condition=cond, region=region, DF_minus_D0_miou_pp=diffs))
    class_deltas = [[metric(pooled(s,'DF')['cms'][2])[1][k]-metric(pooled(s,'D0')['cms'][2])[1][k]
                     for s in SEEDS] for k in range(5)]
    aux = []
    for support in ('boundary','interior','fulltile_nb','fulltile_full'):
        values = [metric(groups[(s,s,'DF','down4')]['aux'][support][2])[0]-
                  metric(groups[(s,s,'D0','down4')]['aux'][support][2])[0] for s in SEEDS]
        aux.append(dict(support=support, DF_minus_D0_miou_pp=values))
    cal = []
    for s in SEEDS:
        for a in ('D0','DF'):
            z = groups[(s,s,a,'down4')]
            for target in ('rgb','dsm','fusion'):
                q = z['calibration'][target]
                n = int(q['count'].sum())
                cal.append(dict(seed=s,arm=a,target=target,six_class_ECE_percent=float(100*np.abs(q['correct']-q['confidence']).sum()/n),six_class_NLL_nats=float(q['nll_sum']/n)))
    margin = [dict(alpha=a, possible_rgb_wrong_fraction_percent=[float(100*groups[(s,s,'DF','down4')]['margin_counts'][i].sum()/pooled(s,'DF')['fusion_flow'][1]) for s in SEEDS]) for i,a in enumerate(ALPHAS)]
    curves = {a: [[metric(pooled(s,a)['cms'][i])[0] for s in SEEDS] for i in range(7)] for a in ARMS}
    return dict(primary_recomputation='MATCHES_ACCEPTED_GATES_WITHIN_1e-8pp', seeds=list(SEEDS),
                alpha_down4_diagnostic=alpha, comparisons_down4=comparisons,
                actual_fusion_flow_down4=actual,
                all_arm_alpha_down4=curves, primary_class_DF_minus_D0_iou_pp=class_deltas,
                primary_condition_roi_deltas=diagnostic, boundary_fulltile_deltas=aux,
                calibration_down4=cal, margin_down4=margin,
                interpretation='Descriptive post-hoc diagnostics only; alpha=.1 remains the registered main result. '
                'No p-values, independent-city claim or retroactive alpha selection. Different flows have different denominators. '
                'Boundary uses full labels; main NB foreground5 differs from six-class calibration.')


def trajectories(m2, output):
    groups = {}
    n = 0
    for p in sorted((m2 / 'trajectory_counts').glob('*/*.json')):
        z = json.loads(p.read_text(encoding='utf-8'))
        m = z['metadata']
        pool_into(groups, (m['job'], m['step']), z['counts'])
        n += 1
    if n != 1728 or len(groups) != 432:
        raise RuntimeError('Expected 1728 trajectory tile counts / 432 job-age groups')
    t = Table(output / 'training_age_metrics.csv', ['job', 'step', 'nb_fg5_miou', 'full_fg5_miou'])
    for (job, step), counts in sorted(groups.items()):
        t.put(job=job, step=step, nb_fg5_miou=metric(counts['nb'])[0], full_fg5_miou=metric(counts['full'])[0])
    t.close()
    trace = Table(output / 'training_trace_summary.csv',
                  ['job', 'logged_rows', 'first_step', 'last_step', 'first_loss', 'last_loss',
                   'max_gradient_norm', 'last_elapsed_seconds', 'last_stable_sec_per_update',
                   'last_weight_mean', 'last_weight_min', 'last_weight_max', 'last_effective_fraction'])
    for folder in sorted((m2/'jobs').iterdir()):
        path = folder/'trajectory.jsonl'
        if not path.is_file():
            continue
        first, last, count, maxnorm = None, None, 0, 0.
        with path.open(encoding='utf-8') as source:
            for line in source:
                row = json.loads(line)
                first = first or row
                last = row
                count += 1
                maxnorm = max(maxnorm, float(row['gradient_norm']))
        if last is None or first['step'] != 1 or last['step'] != 32000:
            raise RuntimeError('Incomplete training trace: '+folder.name)
        trace.put(job=folder.name, logged_rows=count, first_step=first['step'], last_step=last['step'],
                  first_loss=first['loss'], last_loss=last['loss'], max_gradient_norm=maxnorm,
                  last_elapsed_seconds=last.get('elapsed_seconds'), last_stable_sec_per_update=last.get('stable_sec_per_update'),
                  **{'last_'+k: last.get(k) for k in ('weight_mean', 'weight_min', 'weight_max', 'effective_fraction')})
    trace.close()
    if trace.rows != 108:
        raise RuntimeError('Expected 108 completed training traces')
    batches = Table(output/'batch_stream_receipts.csv', ['job','rows','first_step','last_step',
                    'first_batch_hash','last_batch_hash','stream_sha256_from_existing_complete_receipt'])
    for folder in sorted((m2/'jobs').iterdir()):
        path = folder/'batch_hashes.jsonl'
        if not path.is_file():
            continue
        first, last, count = None, None, 0
        with path.open(encoding='utf-8') as source:
            for line in source:
                row = json.loads(line)
                count += 1
                if row['step'] != count:
                    raise RuntimeError('Batch trace step coverage: '+folder.name)
                first = first or row
                last = row
        if count != 32000:
            raise RuntimeError('Batch trace not 32000 rows: '+folder.name)
        complete = json.loads((folder/'complete.json').read_text(encoding='utf-8'))
        batches.put(job=folder.name, rows=count, first_step=first['step'], last_step=last['step'],
                    first_batch_hash=first['hash'], last_batch_hash=last['hash'],
                    stream_sha256_from_existing_complete_receipt=complete['batch_stream_sha256'])
    batches.close()
    if batches.rows != 108:
        raise RuntimeError('Expected 108 batch trace receipts')
    age = []
    for step in (8000,16000,24000,32000):
        deltas = []
        for s in SEEDS:
            values = []
            for arm in ('DF','D0'):
                cm = sum(groups[(f+'_s'+str(s)+'_'+arm,step)]['nb'] for f in ('F0','F1','F2'))
                values.append(metric(cm)[0])
            deltas.append(values[0]-values[1])
        age.append(dict(step=step, DSM_DF_minus_D0_miou_pp=deltas))
    return dict(tile_counts=n, job_age_rows=t.rows,
                training_trace_rows=trace.rows, batch_stream_receipts=batches.rows, dsm_age_deltas=age,
                note='Per-job held-out tiles; teachers have different exclusions. Fixed 32k main endpoint unchanged.')


def candidate_reason(row):
    rel = Path(row['relative'])
    parts = rel.parts
    if not parts or any(p.lower() in PROTECTED for p in parts[:-1]):
        return None
    if rel.suffix.lower() in WEIGHTS:
        return 'authorized_final_run_weight_retirement'
    if rel.name in ('last_resume.tmp', 'endpoint.tmp') and 'jobs' in parts[:-1]:
        return 'inactive_partial_checkpoint'
    if row['run'] == 'm2_directory' and len(parts) == 3 and parts[0] == 'jobs' and parts[2] == 'batch_hashes.jsonl':
        return 'batch_trace_replaced_by_108_checked_receipts'
    if row['run'] == 'm2_directory' and rel.as_posix() in RAW_COUNTS:
        return 'replaced_by_compact_statistics'
    if parts[0] in ('temporary', 'tmp') or (parts[0] == 'cache' and len(parts) > 1 and parts[1] in ('cuda', 'triton', 'kernels')):
        return 'inactive_run_temporary_or_compiler_cache'
    if any(p.lower() in ('predictions', 'inference', 'logits', 'prediction_cache') for p in parts[:-1]) and rel.suffix.lower() in ('.npy', '.npz', '.bin', '.dat', '.tif', '.tiff', '.png'):
        return 'inactive_dense_prediction_artifact'
    return None


def compress_large_logs(h, runs, inv):
    replacements = []
    # Losslessly preserve large batch traces and textual logs, without hashes.
    for row in inv['files']:
        p = Path(row['path'])
        parts = Path(row['relative']).parts
        is_trace = p.name in ('batch_hashes.jsonl', 'trajectory.jsonl') or p.suffix.lower() == '.log' or 'logs' in parts[:-1]
        if not is_trace or any(x.lower() in PROTECTED for x in parts[:-1]):
            continue
        if row['bytes'] < 1024**2 or p.suffix.lower() not in ('.jsonl', '.log', '.txt', '.csv'):
            continue
        if candidate_reason(row) or row['links'] != 1:
            continue
        base = runs[row['run']]
        dest = h.safe(p.with_name(p.name + '.retained.gz'), base)
        if dest.exists():
            raise RuntimeError('Existing replacement requires inspection: '+str(dest))
        count = 0
        with p.open('rb') as src, gzip.open(dest, 'xb', compresslevel=6) as sink:
            while True:
                block = src.read(1024**2)
                if not block:
                    break
                sink.write(block)
                count += len(block)
        observed = 0
        with gzip.open(dest, 'rb') as source:
            while True:
                block = source.read(1024**2)
                if not block:
                    break
                observed += len(block)
        if count != row['bytes'] or observed != row['bytes'] or dest.stat().st_size >= row['bytes']:
            raise RuntimeError('Compressed log did not validate or save space: '+str(p))
        replacements.append(dict(row, reason='lossless_log_compaction', replacement=str(dest)))
    return replacements


def load_helper(path):
    spec = importlib.util.spec_from_file_location('accepted_m2_unlink', path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def recover_predelete_failure(h, records, previous, runs):
    """Permit one explicit retry only for the observed pre-deletion None-metric bug."""
    old = h.read(previous)
    expected_error = repr(TypeError("unsupported operand type(s) for -: 'NoneType' and 'NoneType'"))
    if (old.get('status') != 'STOPPED_NO_AUTOMATIC_RETRY' or
            old.get('error') != expected_error or
            old.get('m2_directory') != str(runs['m2_directory'])):
        raise RuntimeError('Recovery refused: failure identity does not match the known pre-deletion bug')
    output = h.safe(Path(old['output']), records)
    if output.parent != records.resolve() or not output.name.startswith('m2_final_compaction_'):
        raise RuntimeError('Recovery refused: prior output is outside the expected directory')
    if (h.read(output/'cleanup_result.json') != old or
            not (output/'inventory_before.json').is_file() or
            any((output/name).exists() for name in ('cleanup_plan.json', 'deletions.jsonl', 'inventory_after.json')) or
            (records/'phase3_m2_final_compaction_20261029.lock').exists()):
        raise RuntimeError('Recovery refused: prior attempt may have reached deletion or is still active')
    before = h.read(output/'inventory_before.json')
    current = h.inventory(runs)
    identity = lambda x: {(r['path'], r['dev'], r['ino'], r['bytes'], r['mtime_ns'], r['links'])
                          for r in x['files']}
    if (identity(before) != identity(current) or
            before['excluded_symlinks_or_special'] != current['excluded_symlinks_or_special']):
        raise RuntimeError('Recovery refused: bound run files changed since the failed attempt')
    previous.unlink()
    emit('PREDELETE_RECOVERY_VERIFIED', prior_output=str(output),
         files_unchanged=len(current['files']), previous_failure=old['error'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apply', action='store_true')
    p.add_argument('--recover-predelete', action='store_true',
                   help='Explicitly retry only the verified 2026-10-29 None-metric pre-deletion failure')
    p.add_argument('--helper', type=Path, default=ROOT/'records'/('closeout_phase3_m2_storage_'+FIRST+'.py'))
    args = p.parse_args()
    if args.recover_predelete and not args.apply:
        raise RuntimeError('--recover-predelete requires --apply')
    if sys.platform != 'linux':
        raise RuntimeError('Bound Linux server entry point only')
    h = load_helper(args.helper)
    records = ROOT/'records'
    _, runs = h.bound_runs(records)
    h.assert_stopped(runs)
    previous = records/RECEIPT
    if previous.exists():
        old = h.read(previous)
        if old.get('status') == 'COMPLETE' and old.get('m2_directory') == str(runs['m2_directory']):
            emit('ALREADY_COMPACTED', **old)
            return
        if args.recover_predelete:
            recover_predelete_failure(h, records, previous, runs)
        else:
            raise RuntimeError('Existing incomplete receipt: inspect saved journal; no blind rerun')
    elif args.recover_predelete:
        raise RuntimeError('Recovery refused: no previous failed receipt')
    first = h.read(records/h.RECEIPT)
    if first.get('status') != 'COMPLETE' or first['m2_directory'] != str(runs['m2_directory']):
        raise RuntimeError('Accepted first-cleanup receipt missing')
    lock = records/'phase3_m2_final_compaction_20261029.lock'
    fd = os.open(str(lock), os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    output = records/('m2_final_compaction_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()))
    result = dict(status='STARTED', observed_at=h.now(), output=str(output), m2_directory=str(runs['m2_directory']))
    try:
        os.write(fd, str(os.getpid()).encode('ascii'))
        output.mkdir()
        evidence = output/'small_evidence'
        evidence.mkdir()
        h.write(previous, result)
        before = h.inventory(runs)
        h.write(output/'inventory_before.json', before)
        free_before = shutil.disk_usage(records).free
        m2 = runs['m2_directory']
        accepted, _ = h.verify_evidence(m2)
        result['binding'] = accepted['binding']
        emit('PHASE', name='offline_existing_statistics_only', output=str(output))
        groups, folds, coverage = analyze_aggregates(m2, evidence)
        rows = export_tables(groups, folds, evidence)
        summary = summarize(groups, h.read(m2/'publication/gates.json'))
        summary.update(coverage=coverage, table_rows=rows, trajectory=trajectories(m2, evidence))
        summary['case_analysis'] = analyze_cases(m2, evidence)
        summary.update(status='OFFLINE_ANALYSIS_COMPLETE', observed_at=h.now(),
                       original_training='108 jobs / 3456000 updates; no new optimization or inference',
                       upload_status='SERVER_RESULTS_NOT_YET_RECEIVED_BY_GITHUB')
        h.write(evidence/'analysis_summary.json', summary)
        files = [dict(file=f.name, bytes=f.stat().st_size) for f in evidence.iterdir() if f.is_file()]
        if any(f['bytes'] > 16*1024**2 for f in files) or sum(f['bytes'] for f in files) > 48*1024**2:
            raise RuntimeError('Compact evidence exceeds small-file budget; originals retained')
        h.write(evidence/'manifest.json', dict(files=files, total_bytes=sum(f['bytes'] for f in files),
                policy='derived tile CM/flow/calibration/aux counts, all-case numerical summaries and learning ages; '
                'original per-pixel tensors and full joint cubes are intentionally retired; no hashes'))
        # Re-read only the summary and check expected files/sizes before deletion.
        if h.read(evidence/'analysis_summary.json')['coverage']['cases'] != 77868:
            raise RuntimeError('Summary readback mismatch')
        if any((evidence/f['file']).stat().st_size != f['bytes'] for f in files):
            raise RuntimeError('Compact evidence size changed')
        candidates = [dict(row, reason=candidate_reason(row)) for row in before['files'] if candidate_reason(row) and row['links'] == 1]
        # The old duplicate export is outside the four run roots: authorize only
        # its exact receipt-bound archive, never its containing directory.
        old_archive = h.safe(Path(first['archive']['path']), records)
        old_output = h.safe(Path(first['output']), records)
        if old_archive.parent != old_output or old_archive.name != 'M2_light_evidence.tar.gz':
            raise RuntimeError('Unexpected old archive receipt')
        if old_archive.exists():
            extra = h.inventory({'old_export_archive_scope': old_output})['files']
            candidates += [dict(row, reason='superseded_old_duplicate_export') for row in extra
                           if row['path'] == str(old_archive) and row['links'] == 1]
        scopes = dict(runs, old_export_archive_scope=old_output)
        if args.apply:
            candidates += compress_large_logs(h, runs, before)
        candidate_paths = {r['path'] for r in candidates}
        unknown = sorted([r for r in before['files'] if r['bytes'] >= 1024**2 and r['path'] not in candidate_paths], key=lambda r: -r['bytes'])
        plan = dict(status='READY_AFTER_OFFLINE_ANALYSIS', candidates=candidates,
                    candidate_allocated_bytes=sum(r['allocated_bytes'] for r in candidates),
                    candidate_count=len(candidates), unknown_large_retained=unknown,
                    policy='Retire remaining run weights, replaced bulky counts, known predictions/temp and one old duplicate archive; '
                    'losslessly compress large textual logs; never delete unknown files by size alone or shared data/pretrained assets')
        h.write(output/'cleanup_plan.json', plan)
        emit('CLEANUP_PLAN', candidates=len(candidates), allocated_bytes=plan['candidate_allocated_bytes'],
             reasons=dict(Counter(r['reason'] for r in candidates)), unknown_large_retained=len(unknown),
             compact_evidence_bytes=sum(f['bytes'] for f in files))
        if not args.apply:
            result.update(status='ANALYZED_AUDIT_ONLY', cleanup_applied=False)
            # Audit must not consume the one-shot apply receipt.
            previous.unlink()
            h.write(output/'cleanup_result.json', result)
            emit('AUDIT_COMPLETE', **result)
            return
        h.assert_stopped(runs)
        result.update(status='DELETING', cleanup_plan=str(output/'cleanup_plan.json'))
        h.write(previous, result)
        with (output/'deletions.jsonl').open('x', encoding='utf-8') as journal:
            for row in candidates:
                h.delete_checked(row, scopes[row['run']])
                journal.write(dumps(dict(path=row['path'], reason=row['reason'], bytes=row['bytes'],
                                         allocated_bytes=row['allocated_bytes']))+'\n')
                journal.flush()
        after = h.inventory(runs)
        h.write(output/'inventory_after.json', after)
        remaining_weights = [r['path'] for r in after['files'] if candidate_reason(r) == 'authorized_final_run_weight_retirement']
        if remaining_weights:
            raise RuntimeError('Unexpected remaining deletable weights')
        result.update(status='COMPLETE', observed_at=h.now(), cleanup_applied=True, deleted_files=len(candidates),
                      deleted_allocated_bytes=sum(r['allocated_bytes'] for r in candidates),
                      run_allocated_bytes_before=before['unique_allocated_bytes'], run_allocated_bytes_after=after['unique_allocated_bytes'],
                      remaining_run_weights=0, unknown_large_retained=len(unknown),
                      unknown_large_retained_top20=[dict(path=r['path'], bytes=r['bytes']) for r in unknown[:20]],
                      remaining_large_files_top20=[dict(path=r['path'], bytes=r['bytes']) for r in
                            sorted(after['files'], key=lambda r: -r['bytes'])[:20] if r['bytes'] >= 1024**2],
                      small_evidence=str(evidence), compact_evidence_bytes=sum(f['bytes'] for f in files),
                      disk_free_bytes_before=free_before, disk_free_bytes_after=shutil.disk_usage(records).free,
                      retention='code/config/receipts/small numerical evidence and compressed logs; no run checkpoints; '
                      'no model visualization, new inference or J continuation without restoring/retraining weights',
                      upload_status='SERVER_RESULTS_NOT_YET_RECEIVED_BY_GITHUB')
        h.write(output/'cleanup_result.json', result)
        h.write(previous, result)
        emit('FINAL_COMPACTION_COMPLETE', **result)
        # Compact JSON paste relay, not an instruction to download a local archive.
        emit('GITHUB_RELAY_SUMMARY', analysis=summary, cleanup=result)
        emit('SEND_BACK', files=[str(evidence/'analysis_summary.json'), str(output/'cleanup_result.json')],
             note='Paste these two small JSON files or the GITHUB_RELAY_SUMMARY line; then publish actual results through the connected GitHub writer.')
    except BaseException as exc:
        result.update(status='STOPPED_NO_AUTOMATIC_RETRY', observed_at=h.now(), error=repr(exc))
        if output.exists():
            h.write(output/'cleanup_result.json', result)
        h.write(previous, result)
        raise
    finally:
        os.close(fd)
        lock.unlink()


if __name__ == '__main__':
    main()
