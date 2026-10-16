"""Seed17 D18 paths and provenance; the original seed42 code stays frozen."""
from pathlib import Path

import numpy as np
import d18_d19_night as original

ROOT = original.ROOT
CONFIG = original.CONFIG
REPLICATION = ROOT / 'configs/rebuild_v1/d18_replication_seed17_20260928.json'
ARMS = ('P0', 'P1', 'P2')
read, write, sha = original.read, original.write, original.sha
base_config, build = original.base_config, original.build
training_transform, transform = original.training_transform, original.transform
steps = original.steps


def validate():
    rep, cfg = read(REPLICATION), read(CONFIG)
    if rep['arms'] != list(ARMS) or rep['training_seed'] != 17 or rep['evaluation_corruption_seed'] != 42:
        raise RuntimeError('replication arm/seed policy mismatch')
    if rep['original_config'] != str(CONFIG.relative_to(ROOT)).replace('\\', '/'):
        raise RuntimeError('original configuration path mismatch')
    if cfg['seeds'] != [42] or rep['steps'] != cfg['pretrained_steps'] or rep['test6_loaded'] is not False:
        raise RuntimeError('original training budget/Test6 policy mismatch')
    if cfg['micro_batch'] * cfg['accum_steps'] != cfg['effective_batch'] or cfg['effective_batch'] != 16:
        raise RuntimeError('effective batch mismatch')
    if abs(sum(cfg['treatment_probabilities'].values()) - 1) > 1e-8:
        raise RuntimeError('treatment probabilities do not sum to one')
    return rep, cfg


def output(arm, seed=17, smoke=False):
    if arm not in ARMS or seed != 17:
        raise ValueError((arm, seed))
    suffix = '_smoke' if smoke else ''
    return ROOT / 'runs/rebuild_v1' / f'D18_REPL_{arm}_seed17_8000_20260928{suffix}'


def evaluation_output(arm, seed=17, smoke=False):
    if arm not in ARMS or seed != 17:
        raise ValueError((arm, seed))
    suffix = '_smoke' if smoke else ''
    return ROOT / 'records/rebuild_v1_d18_replication_20260928' / f'{arm}_seed17{suffix}'


def binding(arm, smoke):
    rep, cfg = validate()
    if arm not in ARMS:
        raise ValueError(arm)
    original_binding = original.binding(arm, smoke)
    return dict(arm=arm, seed=17, smoke=smoke,
                config_sha256=sha(CONFIG), replication_config_sha256=sha(REPLICATION),
                split_sha256=original_binding['split_sha256'],
                base_config_sha256=original_binding['base_config_sha256'],
                anchor_sha256=original_binding['anchor_sha256'],
                dino_commit=original_binding['dino_commit'],
                torch_version=original_binding['torch_version'],
                original_sources=original_binding['sources'],
                replication_sources={name: sha(ROOT / name) for name in (
                    'scripts/d18_replication.py', 'scripts/train_rebuild_v1_d18_replication.py',
                    'scripts/eval_rebuild_v1_d18_replication.py')})


def paired_counts(gt, reference, candidate, region):
    valid = (gt != 255) & region
    right0, right1 = reference == gt, candidate == gt
    return dict(valid=int(valid.sum()), both_correct=int((valid & right0 & right1).sum()),
                only_p0_correct=int((valid & right0 & ~right1).sum()),
                only_candidate_correct=int((valid & ~right0 & right1).sum()),
                both_wrong=int((valid & ~right0 & ~right1).sum()))


def availability(condition, shape):
    available = np.ones(shape, dtype=bool)
    if condition == 'aux_zero':
        available[:] = False
    elif condition == 'aux_local_zero_q1':
        h, w = shape
        available[h//4:h//4+h//2, w//4:w//4+w//2] = False
    return available
