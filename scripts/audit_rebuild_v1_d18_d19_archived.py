"""Audit D18/D19 archived summaries without server imagery or checkpoint access."""
import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'records/rebuild_v1_d18_d19_compact_20260928'
CONFIG = 'configs/rebuild_v1/d18_d19_night_20260927.json'
SOURCE_COMMIT = '5209403c9a25bd7a7a85369e931ee4b44358a0a9'
ARMS = ('P0', 'P1', 'P2', 'C0', 'C1', 'C2', 'C3', 'CP')
TILES = ('3_11', '5_10')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def blob_sha(path):
    content = subprocess.check_output(['git', 'show', f'{SOURCE_COMMIT}:{path}'], cwd=ROOT)
    return hashlib.sha256(content).hexdigest()


def equal(actual, expected):
    if isinstance(expected, dict):
        assert isinstance(actual, dict) and set(actual) == set(expected), (actual, expected)
        for key in expected:
            equal(actual[key], expected[key])
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected)
        for left, right in zip(actual, expected):
            equal(left, right)
    elif isinstance(expected, float):
        assert math.isclose(actual, expected, rel_tol=0, abs_tol=1e-10), (actual, expected)
    else:
        assert actual == expected, (actual, expected)


def matrix(cm):
    assert len(cm) == 6 and all(len(row) == 6 for row in cm)
    assert all(isinstance(value, int) and value >= 0 for row in cm for value in row)
    return cm


def add_matrices(matrices):
    return [[sum(cm[i][j] for cm in matrices) for j in range(6)] for i in range(6)]


def check_metrics(cm, reported):
    matrix(cm)
    total = sum(map(sum, cm))
    assert total == reported['valid_pixels'] and total > 0
    tp = [cm[i][i] for i in range(6)]
    iou = []
    for i in range(6):
        union = sum(cm[i]) + sum(row[i] for row in cm) - tp[i]
        iou.append(tp[i] / union if union else None)
    for actual, expected in zip(reported['per_class_iou'], iou):
        if expected is None:
            assert actual is None
        else:
            assert math.isclose(actual, expected, rel_tol=0, abs_tol=1e-12)
    fg = [value for value in iou[:5] if value is not None]
    assert math.isclose(reported['mIoU_fg5'], sum(fg) / len(fg), rel_tol=0, abs_tol=1e-12)
    assert math.isclose(reported['OA'], sum(tp) / total, rel_tol=0, abs_tol=1e-12)


def check_condition(entry):
    assert set(entry['tiles']) == set(TILES)
    joint = entry['joint_noboundary']
    parts = ('both_correct', 'only_r01_correct', 'only_candidate_correct', 'both_wrong')
    assert joint['valid'] == sum(joint[key] for key in parts)
    for key in ('valid', *parts):
        assert joint[key] == sum(entry['tiles'][tile]['joint_noboundary'][key] for tile in TILES)
    for scope in ('full', 'noboundary'):
        pooled = entry['pooled'][scope]
        for field, metric_field in (('cm', 'metrics'), ('availability_fallback_cm', 'availability_fallback_metrics')):
            tile_objects = [entry['tiles'][tile]['metrics'][scope] for tile in TILES]
            assert pooled[field] == add_matrices([matrix(obj[field]) for obj in tile_objects])
            for obj in [pooled, *tile_objects]:
                check_metrics(obj[field], obj[metric_field])
    cm = entry['pooled']['noboundary']['cm']
    assert joint['valid'] == sum(map(sum, cm))
    assert joint['both_correct'] + joint['only_candidate_correct'] == sum(cm[i][i] for i in range(6))


def scores(summary, cfg):
    values = {name: 100 * entry['pooled']['noboundary']['metrics']['mIoU_fg5']
              for name, entry in summary['conditions'].items()}
    families = {name: sum(values[c] for c in conditions) / len(conditions)
                for name, conditions in cfg['families'].items()}
    return values, families, sum(families.values()) / len(families)


def assess(candidate, controls, baseline, data, cfg):
    if any(arm not in data for arm in (candidate, baseline, *controls)):
        return dict(arm=candidate, status='INCOMPLETE')
    sc = {arm: scores(data[arm], cfg) for arm in (candidate, baseline, *controls)}
    guard = cfg['screen']
    gain = sc[candidate][2] - max(sc[arm][2] for arm in controls)
    families = {name: sc[candidate][1][name] - sc[baseline][1][name]
                for name in cfg['families']}
    tiles = {}
    for tile in TILES:
        delta = {c: 100 * (data[candidate]['conditions'][c]['tiles'][tile]['metrics']['noboundary']['metrics']['mIoU_fg5'] -
                           data[baseline]['conditions'][c]['tiles'][tile]['metrics']['noboundary']['metrics']['mIoU_fg5'])
                 for c in cfg['evaluation_conditions']}
        tiles[tile] = {name: sum(delta[c] for c in conditions) / len(conditions)
                       for name, conditions in cfg['families'].items()}
    checks = dict(gain=gain >= guard['gain_pp'], clean=families['clean'] >= -guard['clean_loss_pp'],
                  families=min(families.values()) >= -guard['family_loss_pp'],
                  tile_clean=all(row['clean'] >= -guard['tile_clean_loss_pp'] for row in tiles.values()),
                  tile_families=all(min(row.values()) >= -guard['tile_family_loss_pp'] for row in tiles.values()))

    def harm_rescue(arm):
        rows = [data[arm]['conditions'][c]['joint_noboundary'] for c in cfg['families']['aux_quality']]
        valid = sum(row['valid'] for row in rows)
        return (sum(row['only_r01_correct'] for row in rows) / valid,
                sum(row['only_candidate_correct'] for row in rows) / valid)

    harm, rescue = harm_rescue(candidate)
    base_harm, base_rescue = harm_rescue(baseline)
    return dict(arm=candidate, status='COMPLETE', passed=all(checks.values()), checks=checks,
                macro_gain_pp=gain, baseline=baseline, controls=controls,
                family_delta_pp=families, tile_family_delta_pp=tiles,
                harm_percent=100 * harm, rescue_percent=100 * rescue,
                negative_transfer_claim_supported=(harm < base_harm and base_rescue > 0 and
                                                   rescue >= guard['rescue_retention'] * base_rescue))


def main():
    cfg = read(ROOT / CONFIG)
    historical_config = json.loads(subprocess.check_output(
        ['git', 'show', f'{SOURCE_COMMIT}:{CONFIG}'], cwd=ROOT))
    equal(cfg, historical_config)
    config_sha = blob_sha(CONFIG)
    decision = read(BASE / 'decision.json')
    equal(read(BASE / 'conditional_gate.json'), decision)
    equal(read(BASE / 'user_reported_decision.json'), decision)

    lines = (BASE / 'status.tsv').read_text(encoding='utf-8').splitlines()
    starts = [i for i, line in enumerate(lines) if '\tQUEUE\tSTART\t' in line]
    assert len(starts) >= 1
    final = lines[starts[-1]:]
    assert final[0].endswith(SOURCE_COMMIT)
    assert '\tQUEUE\tFINISHED\t' in final[-1]
    assert 'formal_attempted=8 formal_complete=8 failures=0' in final[-1]
    for arm in ARMS:
        for kind in ('TRAIN', 'EVAL'):
            assert any(f'\t{kind}_PILOT_{arm}_42\tCOMPLETE\t0' in line for line in final)
    for arm in ('C4', 'C5'):
        assert any(f'\tPILOT_{arm}\tSKIPPED\t' in line for line in final)

    data = {}
    hashes = {CONFIG: config_sha}
    for arm in ARMS:
        s = read(BASE / f'server_{arm}_seed42_summary.json')
        assert (s['arm'], s['seed'], s['smoke'], s['val2_loaded'], s['test6_loaded']) == (arm, 42, False, True, False)
        assert s['clean_reproduction_pass'] is True
        assert s['config_sha256'] == s['signature']['training']['config_sha256'] == config_sha
        assert s['signature']['training']['split_sha256'] == blob_sha(cfg['split_file'])
        assert s['signature']['training']['base_config_sha256'] == blob_sha(
            'configs/rebuild_v1/r05_quality_plus_dropout_16k.json')
        assert set(s['conditions']) == set(cfg['evaluation_conditions'] + cfg['diagnostics'])
        assert s['physical_gpu'] in ('0', '1')
        assert any(f'\tTRAIN_PILOT_{arm}_42\tSTART\tgpu={s["physical_gpu"]}' in line for line in final)
        for group in (s['signature']['training']['sources'], s['signature']['evaluation_sources']):
            for path, digest in group.items():
                if path not in hashes:
                    hashes[path] = blob_sha(path)
                assert hashes[path] == digest, path
        for entry in s['conditions'].values():
            check_condition(entry)
        data[arm] = s
    assert data['P1']['trainable_parameters'] == data['P2']['trainable_parameters']
    assert len({data[a]['signature']['training']['anchor_sha256'] for a in ('P0', 'P1', 'P2')}) == 1
    assert len({data[a]['signature']['training']['anchor_sha256'] for a in ('C0', 'C1', 'C2', 'C3', 'CP')}) == 1
    assert len({data[a]['signature']['reference_sha256'] for a in ARMS}) == 1

    rows = [assess(arm, controls, baseline, data, cfg) for arm, controls, baseline in (
        ('P2', ['P0', 'P1'], 'P0'), ('C2', ['C0', 'CP'], 'C0'),
        ('C3', ['C1', 'CP'], 'C0'), ('C4', ['C3', 'C5'], 'C0'))]
    equal(decision['decisions'], rows)
    score_rows = [dict(arm=arm, macro_percent=scores(data[arm], cfg)[2], families=scores(data[arm], cfg)[1])
                  for arm in cfg['arms'] if arm in data]
    equal(decision['score_rows'], score_rows)
    assert decision['status'] == 'COMPLETE' and decision['seed'] == 42
    assert decision['test6_loaded'] is False and decision['val2_exploratory'] is True
    assert decision['config_sha256'] == config_sha
    assert decision['missing_base'] == decision['missing_conditional'] == []
    assert decision['conditional_trigger'] is False and decision['conditional_completed'] == []
    assert decision['candidates'] == ['P2']

    audit = dict(status='PASS', source_commit=SOURCE_COMMIT, summaries=len(data),
                 queue_final_line=final[-1], previous_queue_starts=len(starts) - 1,
                 candidates=decision['candidates'], config_sha256=config_sha,
                 checks=['final queue segment and all formal train/eval completions',
                         'historical Git blob source/config hashes and matched anchors',
                         'full and NoBoundary pooled/tile integer confusion matrices',
                         'per-class IoU, fg5 mIoU, OA and paired correctness counts',
                         'all score rows and frozen decision fields independently recomputed'],
                 limitation='Archived summaries were checked offline. Server checkpoint, dataset and split bytes were not independently rehashed or re-inferred; repeatedly used Val2 remains exploratory.')
    (BASE / 'offline_audit.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
    print('D18/D19 ARCHIVE AUDIT PASS: 8 summaries; decision reproduced; P2 only candidate')


if __name__ == '__main__':
    main()
