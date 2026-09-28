"""Recompute matched-seed gates and paired pixel errors from saved Val2 predictions."""
import json
from pathlib import Path

import numpy as np

import d18_replication as p
import train_rebuild_v1_r02_budget_pilot as r02
from summarize_rebuild_v1_d18_d19 import assess, scores

OUT = p.ROOT / 'records/rebuild_v1_d18_replication_20260928'
NAMES = r02.CLASS_NAMES


def source(seed, arm):
    if seed == 42:
        return p.ROOT / 'records/rebuild_v1_d18_d19_20260927' / f'{arm}_seed42'
    return p.evaluation_output(arm, 17)


def prediction(seed, arm, condition, tile, expected_shape):
    path = source(seed, arm) / f'{condition}_{tile}_prediction.npz'
    with np.load(path, allow_pickle=False) as file:
        value = file['prediction']
    if value.shape != expected_shape or not np.issubdtype(value.dtype, np.integer):
        raise RuntimeError(f'prediction shape/type mismatch: {path}')
    if np.any((value < 0) | (value >= 6)):
        raise RuntimeError(f'prediction class out of range: {path}')
    return value


def add(a, b):
    return {key:a[key]+b[key] for key in a}


def score_cm(cm):
    return r02.metrics_from_cm(cm)['mIoU_fg5'] * 100


def main():
    _, cfg = p.validate()
    split = p.read(p.ROOT / cfg['split_file'])
    tiles = split['val2']
    if len(tiles) != 2 or set(tiles) & set(split['train16'] + split['historical_exposed_test6']):
        raise RuntimeError('split boundary mismatch')
    conditions = cfg['evaluation_conditions'] + cfg['diagnostics']
    summaries = {}
    for seed in (42, 17):
        summaries[seed] = {}
        for arm in p.ARMS:
            path = source(seed, arm) / 'summary.json'
            summary = p.read(path)
            if summary['seed'] != seed or summary['arm'] != arm or summary['smoke'] or summary['test6_loaded']:
                raise RuntimeError(f'invalid summary: {path}')
            if summary['config_sha256'] != p.sha(p.CONFIG):
                raise RuntimeError(f'original protocol config mismatch: {path}')
            if seed == 17 and (summary['replication_config_sha256'] != p.sha(p.REPLICATION)
                or summary['evaluation_corruption_seed'] != 42
                or summary['historical_r01_reference_seed'] != 42
                or summary['signature']['training']['seed'] != 17):
                raise RuntimeError(f'replication provenance mismatch: {path}')
            if set(summary['conditions']) != set(conditions):
                raise RuntimeError(f'missing evaluation conditions: {path}')
            summaries[seed][arm] = summary
    outcome = {}
    for seed, data in summaries.items():
        decision = assess('P2', ['P0', 'P1'], 'P0', data, cfg)
        outcome[str(seed)] = dict(decision=decision,
            score_rows={arm:dict(macro_percent=scores(s,cfg)[2],families=scores(s,cfg)[1])
                        for arm,s in data.items()})
    paired = {}
    base = p.read(p.base_config())
    labels = {tile:r02.load_tile(Path(base['data_root']),tile,need_nb=True)['noboundary_gt']
              for tile in tiles}
    for seed in (42, 17):
        paired[str(seed)] = {}
        for condition in conditions:
            per_tile = {}
            aggregate = {}
            fallback_cm = np.zeros((6,6), dtype=np.int64)
            raw_cm = np.zeros_like(fallback_cm)
            for tile in tiles:
                gt = labels[tile]
                pred = {arm:prediction(seed, arm, condition, tile, gt.shape) for arm in p.ARMS}
                valid = gt != 255
                available = p.availability(condition, gt.shape)
                region = ~available if condition in ('aux_zero','aux_local_zero_q1') else np.ones_like(valid)
                details = {}
                for arm in ('P1','P2'):
                    all_count = p.paired_counts(gt,pred['P0'],pred[arm],np.ones_like(valid))
                    masked = p.paired_counts(gt,pred['P0'],pred[arm],region)
                    classes = {NAMES[i]:p.paired_counts(gt,pred['P0'],pred[arm],gt==i) for i in range(6)}
                    details[arm] = dict(all=all_count,damaged_region=masked,by_class=classes)
                    if arm not in aggregate:
                        aggregate[arm] = details[arm]
                    else:
                        aggregate[arm] = dict(all=add(aggregate[arm]['all'],all_count),
                            damaged_region=add(aggregate[arm]['damaged_region'],masked),
                            by_class={name:add(aggregate[arm]['by_class'][name],classes[name]) for name in NAMES})
                fallback = np.where(available,pred['P2'],pred['P0'])
                if condition == 'aux_zero' and not np.array_equal(fallback,pred['P0']):
                    raise RuntimeError('full-absence P0 fallback failed')
                cm0, cm1 = np.zeros((6,6),dtype=np.int64), np.zeros((6,6),dtype=np.int64)
                r02.update_cm(cm0, gt, pred['P2'])
                r02.update_cm(cm1, gt, fallback)
                raw_cm += cm0
                fallback_cm += cm1
                # The saved summary must describe exactly these prediction arrays.
                for arm, arr in pred.items():
                    checked = np.zeros((6,6),dtype=np.int64)
                    r02.update_cm(checked, gt, arr)
                    saved = summaries[seed][arm]['conditions'][condition]['tiles'][tile]['metrics']['noboundary']['cm']
                    if checked.tolist() != saved:
                        raise RuntimeError(f'{arm} prediction/summary mismatch: seed{seed} {condition} {tile}')
                per_tile[tile] = dict(paired=details,raw_p2_mIoU_fg5_percent=score_cm(cm0),
                    matched_p0_fallback_mIoU_fg5_percent=score_cm(cm1),
                    raw_p2_cm=cm0.tolist(),matched_p0_fallback_cm=cm1.tolist(),
                    absent_valid_pixels=int((valid & ~available).sum()))
            paired[str(seed)][condition] = dict(tiles=per_tile,pooled_paired=aggregate,
                pooled_raw_p2_mIoU_fg5_percent=score_cm(raw_cm),
                pooled_matched_p0_fallback_mIoU_fg5_percent=score_cm(fallback_cm),
                pooled_raw_p2_cm=raw_cm.tolist(),pooled_matched_p0_fallback_cm=fallback_cm.tolist())
    decision = dict(status='COMPLETE',seeds=[42,17],arms=list(p.ARMS),test6_loaded=False,
                    val2_exploratory=True,original_config_sha256=p.sha(p.CONFIG),
                    replication_config_sha256=p.sha(p.REPLICATION),outcomes=outcome,
                    both_seeds_pass=all(outcome[str(seed)]['decision']['passed'] for seed in (42,17)),
                    paired=paired,interpretation='paired P0 fallback is an explicit availability-mask policy; historical R01 fallback remains in arm summaries')
    OUT.mkdir(parents=True, exist_ok=True)
    p.write(OUT/'decision.json',decision)
    print('REPLICATION ANALYSIS COMPLETE', OUT/'decision.json', flush=True)


if __name__ == '__main__':
    main()
