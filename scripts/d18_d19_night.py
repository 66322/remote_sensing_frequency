"""Frozen configurations, matched treatments, models and provenance bindings."""
import os
from pathlib import Path
import subprocess

import torch
from torch.nn import functional as F
import d16_d17_portfolio as old

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/'configs/rebuild_v1/d18_d19_night_20260927.json'
ARMS = ('P0', 'P1', 'P2', 'C0', 'C1', 'C2', 'C3', 'CP', 'C4', 'C5')
read, write, sha = old.read, old.write, old.sha
SOURCES = ('scripts/d18_d19_night.py', 'model/rebuild_v1_night_screen.py',
 'scripts/train_rebuild_v1_d18_d19.py', 'scripts/eval_rebuild_v1_d18_d19.py',
 'scripts/d16_d17_portfolio.py', 'scripts/train_rebuild_v1_d16_d17.py',
 'scripts/train_rebuild_v1_r02_budget_pilot.py', 'model/vitcross_seg_modeling_freq_ablation.py',
 'model/vitcross_seg_modeling_freqfusion.py', 'model/vit_seg_modeling_resnet_skip.py',
 'model/dynamic_conv.py', 'model/vit_seg_configs.py', 'scripts/d15_capability.py',
 'scripts/train_rebuild_v1_r01_optical_only.py', 'model/rebuild_v1_optical_only.py',
 'scripts/night_boundary_metrics.py')


def steps(arm):
    return read(CONFIG)['pretrained_steps' if arm.startswith('P') else 'fusion_steps']


def output(arm, seed=42, smoke=False):
    return ROOT/'runs/rebuild_v1'/f'D18_D19_{arm}_seed{seed}_{steps(arm)}_20260927{"_smoke" if smoke else ""}'


def evaluation_output(arm, seed=42, smoke=False):
    return ROOT/'records/rebuild_v1_d18_d19_20260927'/f'{arm}_seed{seed}{"_smoke" if smoke else ""}'


def base_config():
    return old.anchor_paths('R05', 42)[1]


def artifacts():
    cfg = read(CONFIG)['dino']
    return ROOT/cfg['repository_dir'], ROOT/cfg['weights_path']


def binding(arm, smoke):
    cfg = read(CONFIG)
    split = ROOT/cfg['split_file']
    result = dict(arm=arm, seed=42, smoke=smoke, config_sha256=sha(CONFIG),
        split_sha256=sha(split), base_config_sha256=sha(base_config()),
        sources={name:sha(ROOT/name) for name in SOURCES}, torch_version=torch.__version__)
    if arm.startswith('P'):
        repo, weights = artifacts()
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
        if commit != cfg['dino']['repository_commit']:
            raise RuntimeError('DINO repository commit mismatch')
        subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--', 'dinov2', 'hubconf.py'], cwd=repo, check=True, stdout=subprocess.DEVNULL)
        manifest = read(weights.with_suffix('.manifest.json'))
        if manifest['sha256'] != sha(weights) or manifest['repository_commit'] != commit:
            raise RuntimeError('DINO weight manifest mismatch')
        result.update(anchor_sha256=manifest['sha256'], dino_commit=commit)
    else:
        anchor = old.anchor_paths('R05', 42)[0]
        anchor_summary = read(anchor/'summary.json')
        if anchor_summary['global_step'] != 16000 or anchor_summary.get('test6_loaded') is not False:
            raise RuntimeError('R05 anchor incomplete')
        result['anchor_sha256'] = sha(anchor/'best_model.pth')
    return result


def build(arm, base, device, state=None):
    from model.rebuild_v1_night_screen import FrozenDinoSegmenter, LocalInteraction, load_dino
    if arm.startswith('P'):
        repo, weights = artifacts()
        net = FrozenDinoSegmenter(load_dino(repo, weights), auxiliary=arm != 'P0').to(device)
    else:
        import train_rebuild_v1_r02_budget_pilot as r02
        anchor = old.anchor_paths('R05', 42)[0]/'best_model.pth'
        net, _ = r02.build_model(base, Path(base['pretrain']), resume_state=torch.load(anchor, map_location='cpu', weights_only=False))
        if arm in ('C2', 'C3', 'C4', 'C5', 'CP'):
            hybrid = net.transformer.embeddings.hybrid_model
            with torch.random.fork_rng(devices=[0] if device.type == 'cuda' else []):
                torch.manual_seed(17042)
                hybrid.se_layer0 = LocalInteraction(hybrid.se_layer0, capacity=arm=='CP').to(device)
    if state is not None:
        net.load_state_dict(state['model'], strict=True)
    return net


def transform(op, ds, arm, kinds, generator):
    gray = arm == 'P1'
    proxy = 'A4' if gray else 'A0'
    if any(k in ('rgb_contrast060', 'aux_shift8') for k in kinds):
        if len(set(kinds)) != 1:
            raise ValueError('diagnostic transforms are inference-only homogeneous batches')
        kind = kinds[0]
        op = ((op-.5)*.6+.5).clamp(0, 1) if kind == 'rgb_contrast060' else op.clone()
        aux = op.mean(1) if gray else ds.clone()
        if kind == 'aux_shift8':
            aux = F.pad(aux[:, None], (8, 0, 0, 0), mode='replicate')[:, 0, :, :ds.shape[-1]]
        return op, aux, torch.ones_like(aux, dtype=torch.bool)
    return old.transform(op, ds, proxy, kinds, generator)


def training_transform(op, ds, arm, kinds, key, mask_config=None):
    op, aux, available = transform(op, ds, arm, kinds, torch.Generator().manual_seed(key+2))
    if not arm.startswith('P'):
        # One quarter-area block, randomly RGB-only, aux-only, or complementary.
        h, w = op.shape[-2:]
        cfg = read(CONFIG)['structured_mask'] if mask_config is None else mask_config
        if cfg['area_fraction'] != .25 or cfg['modes'] != ['rgb','aux','complementary']:
            raise RuntimeError('structured-mask implementation/config mismatch')
        rng = __import__('random').Random(key+10)
        for i in range(len(op)):
            if rng.random() >= cfg['probability']:
                continue
            y, x = rng.randrange(max(1, h//2)), rng.randrange(max(1, w//2))
            mode = rng.randrange(3)
            if mode in (0, 2):
                op[i, :, y:y+h//2, x:x+w//2] = 0
            if mode == 1:
                aux[i, y:y+h//2, x:x+w//2] = 0
                available[i, y:y+h//2, x:x+w//2] = False
            elif mode == 2:
                mask = torch.ones_like(available[i])
                mask[y:y+h//2, x:x+w//2] = False
                aux[i][mask] = 0
                available[i][mask] = False
    return op, aux, available


def consistency_arm(arm):
    return {'C1':'A1', 'C3':'A1', 'C4':'A2', 'C5':'A3'}.get(arm)
