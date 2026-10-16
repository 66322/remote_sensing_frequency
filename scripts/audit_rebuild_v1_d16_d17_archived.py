"""Audit archived pilot counts, bindings and decisions without loading imagery."""
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'records/rebuild_v1_d16_d17_compact_20260927'
CONFIG = ROOT / 'configs/rebuild_v1/d16_d17_portfolio_20260926.json'
ARMS = ('A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'B1', 'B2')
SOURCE_COMMIT = '8cf6f0a'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def blob_sha(path):
    blob = subprocess.check_output(['git', 'show', f'{SOURCE_COMMIT}:{path}'], cwd=ROOT)
    return hashlib.sha256(blob).hexdigest()


def metrics(cm):
    raw = np.asarray(cm)
    assert raw.shape == (6, 6) and np.issubdtype(raw.dtype, np.integer)
    assert (raw >= 0).all()
    cm = raw.astype(np.int64)
    tp = np.diag(cm).astype(float)
    union = cm.sum(0) + cm.sum(1) - tp
    iou = np.divide(tp, union, out=np.full(6, np.nan), where=union > 0)
    return cm, iou


def same(a, b):
    if isinstance(a, dict):
        assert set(a) == set(b)
        for key in a:
            same(a[key], b[key])
    elif isinstance(a, list):
        assert len(a) == len(b)
        for x, y in zip(a, b):
            same(x, y)
    elif isinstance(a, float):
        assert math.isclose(a, b, rel_tol=0, abs_tol=1e-10), (a, b)
    else:
        assert a == b, (a, b)


def main():
    cfg = read(CONFIG)
    config_path = str(CONFIG.relative_to(ROOT)).replace('\\', '/')
    historical_config = json.loads(subprocess.check_output(['git', 'show', f'{SOURCE_COMMIT}:{config_path}'], cwd=ROOT))
    same(cfg, historical_config)
    hashes = {str(CONFIG.relative_to(ROOT)).replace('\\', '/'): blob_sha(str(CONFIG.relative_to(ROOT)).replace('\\', '/'))}
    config_hash = next(iter(hashes.values()))
    data = {}
    for seed in (42, 17):
        for arm in ARMS:
            d = read(BASE / f'server_{arm}_seed{seed}_summary.json')
            assert (d['arm'], d['seed'], d['smoke'], d['val2_loaded'], d['test6_loaded']) == (arm, seed, False, True, False)
            assert d['config_sha256'] == config_hash == d['signature']['training']['config_sha256']
            assert set(d['conditions']) == set(cfg['evaluation_conditions'])
            for group in (d['signature']['training']['sources'], d['signature']['evaluation_sources']):
                for path, sha in group.items():
                    if path not in hashes:
                        hashes[path] = blob_sha(path)
                    assert sha == hashes[path], path
            for entry in d['conditions'].values():
                assert set(entry['tiles']) == {'3_11', '5_10'}
                counts = entry['joint_noboundary']
                assert counts['valid'] == sum(v for k, v in counts.items() if k != 'valid')
                for scope in ('full', 'noboundary'):
                    pooled = entry['pooled'][scope]
                    for field, metric in (('cm', 'metrics'), ('availability_fallback_cm', 'availability_fallback_metrics')):
                        cm, iou = metrics(pooled[field])
                        tile_sum = sum(np.asarray(t['metrics'][scope][field], dtype=np.int64) for t in entry['tiles'].values())
                        assert np.array_equal(cm, tile_sum)
                        for obj in [pooled] + [t['metrics'][scope] for t in entry['tiles'].values()]:
                            local_cm, local_iou = metrics(obj[field])
                            assert int(local_cm.sum()) == obj[metric]['valid_pixels']
                            assert abs(float(np.nanmean(local_iou[:5])) - obj[metric]['mIoU_fg5']) < 1e-12
                            assert np.allclose(local_iou, obj[metric]['per_class_iou'], atol=1e-12, rtol=0, equal_nan=True)
                    if scope == 'noboundary':
                        assert counts['valid'] == pooled['metrics']['valid_pixels']
                        assert counts['both_correct'] + counts['only_candidate_correct'] == int(np.trace(pooled['cm']))
            data[arm, seed] = d
        refs = {(data[a, seed]['signature']['reference_sha256'], data[a, seed]['signature']['reference_config_sha256']) for a in ARMS}
        assert len(refs) == 1
        for group in (('A0', 'A1', 'A2', 'A3', 'B1', 'B2'), ('A4', 'A5')):
            assert len({data[a, seed]['signature']['training']['anchor_sha256'] for a in group}) == 1
        assert len({data[a, seed]['signature']['training']['split_sha256'] for a in ARMS}) == 1

    # Run the frozen decision logic with archived-file IO; no torch/data imports.
    captured = []
    adapter = SimpleNamespace(ROOT=ROOT, CONFIG=CONFIG, read=read,
        sha=lambda path: config_hash,
        write=lambda path, result: captured.append(result))
    class ArchiveDirectory:
        def __init__(self, arm, seed):
            self.arm, self.seed = arm, seed
        def __truediv__(self, name):
            assert name == 'summary.json'
            return BASE / f'server_{self.arm}_seed{self.seed}_summary.json'
    adapter.evaluation_output = ArchiveDirectory
    sys.modules['d16_d17_portfolio'] = adapter
    screen_path = ROOT / 'scripts/summarize_rebuild_v1_d16_d17.py'
    assert hashlib.sha256(screen_path.read_text(encoding='utf-8').encode()).hexdigest() == blob_sha('scripts/summarize_rebuild_v1_d16_d17.py')
    spec = importlib.util.spec_from_file_location('frozen_screen', screen_path)
    screen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(screen)
    screen.main()
    assert len(captured) == 1
    same(captured[0], read(BASE / 'decision.json'))
    rows = []
    for seed in (42, 17):
        for arm in ARMS:
            values, families, macro = screen.scores(data[arm, seed], cfg)
            rows.append(dict(arm=arm, seed=seed, macro_percent=macro, **families))
    result = dict(status='PASS', summaries=16, source_commit=SOURCE_COMMIT,
        candidates=captured[0]['candidates'], score_rows=rows,
        checks=['historical Git-blob source/config hashes', 'matched anchor/split/reference bindings',
                'pooled and tile integer confusion matrices', 'per-class IoU and fg5 recomputation',
                'paired correctness counts', 'all decision fields recomputed'],
        limitation='Server checkpoint bytes, split-file bytes and imagery were not independently accessed or rehashed; no reinference. Repeated Val2 remains exploratory.')
    (BASE / 'offline_audit.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    for row in rows:
        print(row['seed'], row['arm'], 'macro', round(row['macro_percent'], 4), 'clean', round(row['clean'], 4))
    print('ARCHIVE AUDIT PASS: 16 summaries; decisions reproduced')


if __name__ == '__main__':
    main()
