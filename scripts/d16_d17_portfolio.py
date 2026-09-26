"""Losses, deterministic treatments and atomic manifests for the portfolio."""
import hashlib
import json
import os
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'configs/rebuild_v1/d16_d17_portfolio_20260926.json'
ARMS = ('A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'B1', 'B2')
SOURCES = ('scripts/d16_d17_portfolio.py', 'scripts/train_rebuild_v1_d16_d17.py',
           'scripts/train_rebuild_v1_r02_budget_pilot.py',
           'model/vitcross_seg_modeling_freq_ablation.py', 'model/vitcross_seg_modeling_freqfusion.py',
           'model/vit_seg_modeling_resnet_skip.py', 'model/dynamic_conv.py', 'model/vit_seg_configs.py')

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(tmp, path)

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def model_name(arm):
    if arm not in ARMS:
        raise ValueError(arm)
    return 'C-OO-QD' if arm in ('A4', 'A5') else 'R05'

def output(arm, seed, smoke=False):
    return ROOT / 'runs/rebuild_v1' / f'D16_D17_{arm}_seed{seed}_4000_20260926{"_smoke" if smoke else ""}'

def evaluation_output(arm, seed, smoke=False):
    return ROOT / 'records/rebuild_v1_d16_d17_20260926' / f'{arm}_seed{seed}{"_smoke" if smoke else ""}'

def binding(arm, seed, anchor, smoke):
    cfg = read(CONFIG)
    _, base = anchor_paths(model_name(arm), seed)
    return dict(arm=arm, seed=seed, smoke=smoke, config_sha256=sha(CONFIG),
                anchor_sha256=sha(anchor), split_sha256=sha(ROOT / cfg['split_file']),
                base_config_sha256=sha(base), sources={p: sha(ROOT / p) for p in SOURCES})

def anchor_paths(model, seed):
    names = {
        'R01': ('R01_optical_only', 'r01_optical_only_16k.json'),
        'R05': ('R05_dual_f0_quality_plus_dropout', 'r05_quality_plus_dropout_16k.json'),
        'C-OO-QD': ('C_OO_QD_dual_optical_gray_quality_plus_dropout', 'c_oo_qd_optical_gray_16k.json')}
    prefix, config = names[model]
    return ROOT / 'runs/rebuild_v1' / f'{prefix}_seed{seed}_sched16000_stop16000', ROOT / 'configs/rebuild_v1' / config

def validate_config(cfg):
    assert cfg['arms'] == list(ARMS) and cfg['seeds'] == [42, 17]
    assert cfg['micro_batch'] * cfg['accum_steps'] == cfg['effective_batch'] == 16
    assert abs(sum(cfg['treatment_probabilities'].values()) - 1) < 1e-8
    assert set(cfg['evaluation_conditions']) == set(cfg['treatment_probabilities'])
    assert cfg['test6_loaded'] is False and cfg['steps'] == 4000
    assert 0 < cfg['schedule']['warmup_steps'] < cfg['steps']

def resize_restore(x, factor):
    h, w = x.shape[-2:]
    small = F.interpolate(x, size=(max(1, h//factor), max(1, w//factor)),
                          mode='bilinear', align_corners=False, antialias=True)
    return F.interpolate(small, size=(h, w), mode='bilinear', align_corners=False)

def transform(op, ds, arm, kinds, generator):
    """RGB damage precedes grayscale derivation; aux damage applies to second stream."""
    op = op.clone()
    for i, kind in enumerate(kinds):
        if kind.startswith('rgb_'):
            x = op[i:i+1]
            if kind == 'rgb_blur5':
                op[i:i+1] = F.avg_pool2d(F.pad(x, (2,2,2,2), mode='reflect'), 5, 1)
            else:
                degraded = resize_restore(x, 2 if kind == 'rgb_down2' else 4)
                if kind == 'rgb_local_down4_q1':
                    h, w = op.shape[-2:]
                    op[i:i+1, :, h//4:h//4+h//2, w//4:w//4+w//2] = degraded[:, :, h//4:h//4+h//2, w//4:w//4+w//2]
                else:
                    op[i:i+1] = degraded
    aux = op.mean(1) if model_name(arm) == 'C-OO-QD' else ds.clone()
    available = torch.ones_like(aux, dtype=torch.bool)
    for i, kind in enumerate(kinds):
        if kind == 'aux_down4':
            aux[i:i+1] = resize_restore(aux[i:i+1, None], 4)[:, 0]
        elif kind == 'aux_noise_std010':
            noise = torch.randn(aux[i].shape, generator=generator, device='cpu').to(aux.device)
            aux[i] = (aux[i] + 0.1 * noise).clamp(0, 1)
        elif kind == 'aux_zero':
            aux[i].zero_()
            available[i].zero_()
        elif kind == 'aux_local_zero_q1':
            h, w = aux.shape[-2:]
            aux[i, h//4:h//4+h//2, w//4:w//4+w//2] = 0
            available[i, h//4:h//4+h//2, w//4:w//4+w//2] = False
        elif kind not in ('clean', 'rgb_down2', 'rgb_down4', 'rgb_blur5', 'rgb_local_down4_q1'):
            raise ValueError(kind)
    return op, aux, available

def selected_mask(clean, perturbed, gt, available):
    return (gt != 255) & available & (clean.detach().argmax(1) == gt) & (perturbed.detach().argmax(1) != gt)

def shuffled_mask(mask, gt, generator):
    """Per-sample/class count preserved within valid, available eligibility."""
    result = torch.zeros_like(mask)
    for i in range(mask.shape[0]):
        for c in range(6):
            candidates = torch.nonzero((gt[i] == c).flatten(), as_tuple=False).flatten()
            n = int((mask[i] & (gt[i] == c)).sum())
            if n:
                order = torch.randperm(len(candidates), generator=generator).to(candidates.device)
                result[i].flatten()[candidates[order[:n]]] = True
    return result

def consistency(clean, perturbed, gt, available, arm, generator):
    valid = (gt != 255) & available
    if arm == 'A1':
        mask = valid
    else:
        mask = selected_mask(clean, perturbed, gt, available)
        if arm == 'A3':
            # Preserve class counts among available pixels, not missing regions.
            eligible_gt = gt.masked_fill(~valid, 255)
            mask = shuffled_mask(mask, eligible_gt, generator)
    values = F.kl_div(F.log_softmax(perturbed, 1), F.softmax(clean.detach(), 1), reduction='none').sum(1)
    loss = (values * mask).sum() / mask.sum().clamp_min(1)
    return loss, int(mask.sum())

def geometry_target(ds, size, scale):
    # Gradients at the feature resolution, using aligned original (uncorrupted) DSM.
    low = F.interpolate(ds[:, None], size=size, mode='bilinear', align_corners=False)
    dx = F.pad(low[:, :, :, 1:] - low[:, :, :, :-1], (0,1,0,0))
    dy = F.pad(low[:, :, 1:, :] - low[:, :, :-1, :], (0,0,0,1))
    return (torch.cat((dx, dy), 1) / scale).clamp(-1, 1)

def shuffled_geometry(target, generator):
    flat = target.flatten(2)
    result = torch.empty_like(flat)
    for i in range(len(target)):
        order = torch.randperm(flat.shape[-1], generator=generator).to(target.device)
        result[i] = flat[i, :, order]
    return result.view_as(target)

def rng_state():
    return dict(python_rng=random.getstate(), numpy_rng=np.random.get_state(),
                torch_rng=torch.get_rng_state(), cuda_rng=torch.cuda.get_rng_state_all())

def restore_rng(state):
    random.setstate(state['python_rng'])
    np.random.set_state(state['numpy_rng'])
    torch.set_rng_state(state['torch_rng'])
    torch.cuda.set_rng_state_all(state['cuda_rng'])
