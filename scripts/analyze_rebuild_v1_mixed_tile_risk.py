"""Read-only CPU audit of C0/C1 mixed-degradation tile and class errors."""
import hashlib
import json
import math
import os
from pathlib import Path
from datetime import datetime


ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / 'records/post_d21_mixed_followup_queue_20260930'
COMPACT = ROOT / 'records/post_d21_mixed_followup_compact_20260930'
EVAL = ROOT / 'records/post_d21_day_evaluation_20260929'
RUNS = ROOT / 'runs/rebuild_v1'
CONDITIONS = ('scale2_clean', 'scale4_clean', 'scale2_unseen_blur',
              'scale4_unseen_blur')
CLASSES = ('Impervious', 'Building', 'LowVegetation', 'Tree', 'Car', 'Clutter')
FOCUS = {'potsdam': ('5_10',), 'vaihingen': ('20', '33')}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def matrix(row):
    cm = row['cm']
    if (len(cm) != 6 or any(len(values) != 6 for values in cm) or
            any(type(value) is not int or value < 0 for values in cm for value in values)):
        raise RuntimeError('invalid nonnegative int64 6x6 matrix representation')
    true = [sum(values) for values in cm]
    predicted = [sum(cm[i][j] for i in range(6)) for j in range(6)]
    correct = [cm[i][i] for i in range(6)]
    if (sum(true) != row['metrics']['valid_pixels'] or
            true != row['metrics']['class_true_count'] or
            predicted != row['metrics']['class_predicted_count'] or
            correct != row['metrics']['class_correct_count']):
        raise RuntimeError('matrix count and metadata mismatch')
    iou = []
    for i in range(6):
        union = true[i] + predicted[i] - correct[i]
        iou.append(correct[i] / union if union else None)
    for actual, reported in zip(iou, row['metrics']['per_class_iou']):
        if (actual is None) != (reported is None) or (actual is not None and
                not math.isclose(actual, reported, abs_tol=1e-12, rel_tol=0)):
            raise RuntimeError('per-class IoU recomputation mismatch')
    fg = [value for value in iou[:5] if value is not None]
    if not fg or not math.isclose(sum(fg) / len(fg), row['metrics']['mIoU_fg5'],
                                  abs_tol=1e-12, rel_tol=0):
        raise RuntimeError('foreground IoU recomputation mismatch')
    return dict(cm=cm, true=true, predicted=predicted, correct=correct, iou=iou)


def audit_evaluation(entry):
    if not entry['evaluation_ids']:
        raise RuntimeError('empty development evaluation')
    for condition in CONDITIONS:
        data = entry['conditions'][condition]
        if set(data['tiles']) != {str(tile) for tile in entry['evaluation_ids']}:
            raise RuntimeError('development evaluation tile list mismatch')
        for scope, pooled in data['pooled'].items():
            pooled_cm = matrix(pooled)['cm']
            total = [[0] * 6 for _ in range(6)]
            for tile in entry['evaluation_ids']:
                row = data['tiles'][str(tile)]['scopes'][scope]
                cm = matrix(row)['cm']
                for i in range(6):
                    for j in range(6):
                        total[i][j] += cm[i][j]
            if total != pooled_cm:
                raise RuntimeError('pooled/tile integer matrix mismatch')


def boundary_f1(rows):
    if rows is None:
        return None
    result = {}
    for row in rows:
        predicted, truth = row['predicted'], row['truth']
        precision = row['matched_predicted'] / predicted if predicted else None
        recall = row['matched_truth'] / truth if truth else None
        f1 = (2 * precision * recall / (precision + recall)
              if precision is not None and recall is not None and precision + recall else None)
        result[CLASSES[row['class_id']]] = f1
    return result


def job_files(dataset, arm):
    job_id = f'E_{dataset}_{arm}_scale0_seed42'
    return (RUNS / ('POST_D21_' + job_id) / 'summary.json',
            EVAL / job_id / 'summary.json')


def main():
    queue_path, analysis_path = QUEUE / 'queue_summary.json', COMPACT / 'analysis.json'
    queue, analysis = read(queue_path), read(analysis_path)
    if (queue.get('status') != 'COMPLETE' or queue.get('completed') != 4 or
            queue.get('planned') != 4 or queue.get('failures') or
            analysis.get('completed') != 4 or analysis.get('selected') != 4 or
            analysis.get('integer_count_audit') != 'PASS' or
            queue.get('test6_loaded') is not False or
            analysis.get('test6_loaded') is not False):
        raise RuntimeError('four-job development queue/audit is not complete')
    files = [queue_path, analysis_path, Path(__file__).resolve()]
    paired = {}
    for dataset in FOCUS:
        for arm in ('bicubic_ce', 'learned_ce'):
            train_path, eval_path = job_files(dataset, arm)
            files += [train_path, eval_path]
            train, entry = read(train_path), read(eval_path)
            job_id = f'E_{dataset}_{arm}_scale0_seed42'
            if (train['job']['job_id'] != job_id or entry['job']['job_id'] != job_id or
                    train['global_step'] != 16000 or train['test6_loaded'] is not False or
                    entry['test6_loaded'] is not False or
                    entry['signature']['training'] != train['signature'] or
                    entry['signature']['checkpoint_sha256'] != train['checkpoint_sha256']):
                raise RuntimeError('training/evaluation/checkpoint summary binding mismatch')
            audit_evaluation(entry)
            paired[(dataset, arm)] = entry
    sources = {str(path.relative_to(ROOT)): sha(path) for path in files}
    output_path = COMPACT / 'tile_risk_diagnostics.json'
    if output_path.exists():
        previous = read(output_path)
        if previous.get('source_sha256') != sources:
            raise RuntimeError('existing tile-risk analysis has different input bindings')
        result = previous
    else:
        details, condition_summaries = [], []
        reference = {(r['dataset'], r['condition']): r for r in analysis['comparisons']}
        for dataset, focus_tiles in FOCUS.items():
            fixed, learned = (paired[(dataset, arm)] for arm in ('bicubic_ce', 'learned_ce'))
            if (fixed['primary_scope'] != learned['primary_scope'] or
                    fixed['evaluation_ids'] != learned['evaluation_ids']):
                raise RuntimeError('C0/C1 evaluation split or scope differs')
            scope = fixed['primary_scope']
            for condition in CONDITIONS:
                pair_scores = []
                fixed_tiles = fixed['conditions'][condition]['tiles']
                learned_tiles = learned['conditions'][condition]['tiles']
                if set(fixed_tiles) != set(learned_tiles):
                    raise RuntimeError('C0/C1 tile keys differ')
                for tile in fixed_tiles:
                    frow, lrow = fixed_tiles[tile], learned_tiles[tile]
                    fcm, lcm = (matrix(row['scopes'][scope]) for row in (frow, lrow))
                    if fcm['true'] != lcm['true']:
                        raise RuntimeError('paired ground-truth class counts differ')
                    delta = 100 * (lrow['scopes'][scope]['metrics']['mIoU_fg5'] -
                                   frow['scopes'][scope]['metrics']['mIoU_fg5'])
                    pair_scores.append((tile, delta))
                    if tile not in focus_tiles:
                        continue
                    classes = []
                    for index, name in enumerate(CLASSES):
                        fi, li = fcm['iou'][index], lcm['iou'][index]
                        classes.append(dict(class_id=index, name=name,
                            true_pixels=fcm['true'][index],
                            fixed_iou=fi, learned_iou=li,
                            delta_iou_pp=None if fi is None or li is None else 100 * (li - fi),
                            delta_correct_pixels=lcm['correct'][index] - fcm['correct'][index],
                            delta_false_positive=(lcm['predicted'][index] - lcm['correct'][index]) -
                                                 (fcm['predicted'][index] - fcm['correct'][index]),
                            delta_false_negative=(lcm['true'][index] - lcm['correct'][index]) -
                                                 (fcm['true'][index] - fcm['correct'][index])))
                    details.append(dict(dataset=dataset, tile=tile, condition=condition,
                        primary_scope=scope, delta_fg5_pp=delta, by_class=classes,
                        boundary_f1_fixed=boundary_f1(frow['boundary_counts']),
                        boundary_f1_learned=boundary_f1(lrow['boundary_counts']),
                        reconstruction_fixed=frow['reconstruction'],
                        reconstruction_learned=lrow['reconstruction']))
                fpool = fixed['conditions'][condition]['pooled'][scope]['metrics']['mIoU_fg5']
                lpool = learned['conditions'][condition]['pooled'][scope]['metrics']['mIoU_fg5']
                delta_pool = 100 * (lpool - fpool)
                if not math.isclose(delta_pool,
                                    reference[(dataset, condition)]['learned_minus_bicubic_pp'],
                                    abs_tol=1e-9, rel_tol=0):
                    raise RuntimeError('existing E comparison does not match integer summaries')
                recorded_tiles = reference[(dataset, condition)]['per_tile_delta_pp']
                if (set(recorded_tiles) != set(fixed_tiles) or any(
                        not math.isclose(delta, recorded_tiles[tile], abs_tol=1e-9, rel_tol=0)
                        for tile, delta in pair_scores)):
                    raise RuntimeError('existing E per-tile comparison mismatch')
                condition_summaries.append(dict(dataset=dataset, condition=condition,
                    pooled_delta_pp=delta_pool,
                    negative_tiles=sum(delta < 0 for _, delta in pair_scores),
                    tile_count=len(pair_scores),
                    worst_tiles=[dict(tile=tile, delta_pp=delta)
                        for tile, delta in sorted(pair_scores, key=lambda row: row[1])[:3]]))
        result = dict(observed_at=datetime.now().astimezone().isoformat(timespec='seconds'),
            source_sha256=sources, integer_count_reaudit='PASS',
            checkpoint_summary_binding='PASS; checkpoint binaries not rehashed',
            test6_loaded=False, condition_summaries=condition_summaries,
            focus_details=details,
            boundary_note='boundary counts use FullGT; unavailable for unseen blur conditions',
            reconstruction_note='inference patch pixel weighted; overlapping windows repeated')
        temp = output_path.with_suffix('.tmp')
        temp.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        os.replace(temp, output_path)
    print('TILE RISK AUDIT', result['integer_count_reaudit'], flush=True)
    print('output:', output_path, flush=True)
    for row in result['focus_details']:
        if row['delta_fg5_pp'] < 0:
            losers = sorted((c for c in row['by_class'] if c['delta_iou_pp'] is not None),
                            key=lambda item: item['delta_iou_pp'])[:2]
            print(row['dataset'], row['tile'], row['condition'],
                  f"{row['delta_fg5_pp']:+.3f} pp",
                  'worst classes:', ', '.join(f"{c['name']} {c['delta_iou_pp']:+.2f} pp"
                                            for c in losers), flush=True)


if __name__ == '__main__':
    main()
