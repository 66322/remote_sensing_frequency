"""Matched full-network continuation pilots; no Val2/Test6 read during training."""
import argparse
import os
import random
import subprocess
import time
from pathlib import Path

os.environ.setdefault('CUDA_VISIBLE_DEVICES', '0')
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import train_rebuild_v1_r02_budget_pilot as r02
import d16_d17_portfolio as p


def save(path, net, head, optimizer, step, signature, counts):
    state = dict(model=net.state_dict(), auxiliary=None if head is None else head.state_dict(),
                 optimizer=optimizer.state_dict(), global_step=step, signature=signature,
                 scheduler_state={'kind':'warmup_poly_from_frozen_config','last_step':step},
                 treatment_counts=counts, **p.rng_state())
    temporary = path.with_name(path.name + '.tmp')
    torch.save(state, temporary)
    os.replace(temporary, path)


def sample(cache, ids, cfg, seed):
    # Crop RNG independent of model/head/dropout RNG. This key also resumes exactly.
    py, npstate = random.getstate(), np.random.get_state()
    random.seed(seed)
    np.random.seed(seed % (2**32))
    try:
        return r02.sample_batch(cache, ids, cfg)
    finally:
        random.setstate(py)
        np.random.set_state(npstate)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', choices=p.ARMS, required=True)
    ap.add_argument('--seed', type=int, choices=(42,17), required=True)
    ap.add_argument('--smoke', action='store_true')
    args = ap.parse_args()
    cfg = p.read(p.CONFIG)
    p.validate_config(cfg)
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError('exactly one visible CUDA GPU required')
    split = p.read(p.ROOT / cfg['split_file'])
    ids = split['train16']
    if len(ids) != 16 or set(ids) & (set(split['val2']) | set(split['historical_exposed_test6'])):
        raise RuntimeError('split boundary failure')
    model = p.model_name(args.arm)
    anchor_dir, base_config = p.anchor_paths(model, args.seed)
    base = p.read(base_config)
    anchor = anchor_dir / 'best_model.pth'
    original = p.read(anchor_dir / 'summary.json')
    if original.get('global_step') != 16000 or original.get('test6_loaded') is not False:
        raise RuntimeError('anchor is incomplete or unsafe')
    signature = p.binding(args.arm, args.seed, anchor, args.smoke)
    out = p.output(args.arm, args.seed, args.smoke)
    summary_path = out / 'summary.json'
    target = 1 if args.smoke else cfg['steps']
    if summary_path.is_file():
        result = p.read(summary_path)
        if result['signature'] != signature or result['global_step'] != target or not (out / 'last_train_state.pth').is_file():
            raise RuntimeError('completed run binding mismatch')
        print('TRAIN REUSED', out, flush=True)
        return
    out.mkdir(parents=True, exist_ok=True)
    r02.set_seed(args.seed)
    state = torch.load(out / 'last_train_state.pth', map_location='cpu', weights_only=False) if (out / 'last_train_state.pth').is_file() else None
    if state is not None and state['signature'] != signature:
        raise RuntimeError('resume source/config/anchor mismatch; keep original source')
    initial = state or torch.load(anchor, map_location='cpu', weights_only=False)
    net, _ = r02.build_model(base, Path(base['pretrain']), resume_state=initial)
    head = None
    captured = []
    handle = None
    if args.arm in ('B1', 'B2'):
        # root is executed before rootd and se_layer0 (first cross-modal operation).
        root = net.transformer.embeddings.hybrid_model.root
        with torch.random.fork_rng(devices=[0]):
            torch.manual_seed(args.seed + 17000)
            head = nn.Sequential(nn.Conv2d(64,32,3,padding=1), nn.ReLU(), nn.Conv2d(32,2,1)).to(r02.DEVICE)
        if state is not None:
            head.load_state_dict(state['auxiliary'], strict=True)
        handle = root.register_forward_hook(lambda _m, _i, x: captured.append(x))
    optcfg = dict(base, optimizer=cfg['optimizer'], schedule=cfg['schedule'])
    optimizer = r02.build_optimizer(net, optcfg)
    if head is not None:
        optimizer.add_param_group(dict(params=head.parameters(), lr=cfg['optimizer']['backbone_lr']*10,
                                      lr_mult=10., group_name='geometry_head'))
    if state is not None:
        optimizer.load_state_dict(state['optimizer'])
        p.restore_rng(state)
    else:
        r02.set_seed(args.seed)
    start = int(state['global_step']) if state else 0
    counts = state['treatment_counts'] if state else {k:0 for k in cfg['treatment_probabilities']}
    train_ids = ids[:1] if args.smoke else ids
    cache, _ = r02.preload(Path(base['data_root']), train_ids, [])
    sampler = dict(base, micro_batch=1 if args.smoke else cfg['micro_batch'])
    accum = 1 if args.smoke else cfg['accum_steps']
    names = list(cfg['treatment_probabilities'])
    weights = list(cfg['treatment_probabilities'].values())
    started = time.time()
    metadata = dict(signature=signature, model=model, train_tiles=train_ids,
                    val2_loaded=False, test6_loaded=False, physical_gpu=os.environ['CUDA_VISIBLE_DEVICES'],
                    git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=p.ROOT,text=True).strip())
    p.write(out / 'run_metadata.json', metadata)
    net.train()
    try:
        for step in range(start+1, target+1):
            optimizer.zero_grad(set_to_none=True)
            r02.set_lr(optimizer, optcfg, step, cfg['steps'])
            total_loss, pixels = 0., 0
            for micro in range(accum):
                key = args.seed*1000000 + step*100 + micro
                op, ds, gt, _ = sample(cache, train_ids, sampler, key)
                kinds = random.Random(key+1).choices(names, weights=weights, k=len(op))
                for kind in kinds:
                    counts[kind] += 1
                noise = torch.Generator().manual_seed(key+2)
                op2, aux2, available = p.transform(op, ds, args.arm, kinds, noise)
                aux = op.mean(1) if model == 'C-OO-QD' else ds
                captured.clear()
                clean = net(op, aux)
                detached = clean.detach()
                loss = 0.5 * F.cross_entropy(clean, gt, ignore_index=255)
                if head is not None:
                    if len(captured) != 1:
                        raise RuntimeError('RGB pre-fusion root hook count mismatch')
                    pred = head(captured.pop())
                    geometry = p.geometry_target(ds, pred.shape[-2:], cfg['geometry_scale'])
                    if args.arm == 'B2':
                        geometry = p.shuffled_geometry(geometry, torch.Generator().manual_seed(key+3))
                    loss = loss + cfg['geometry_weight'] * F.smooth_l1_loss(pred, geometry)
                    del pred, geometry
                if not torch.isfinite(loss):
                    raise RuntimeError('nonfinite clean/geometry loss')
                total_loss += float(loss.detach()) / accum
                (loss / accum).backward()
                del loss, clean
                captured.clear()
                perturbed = net(op2, aux2)
                captured.clear()
                loss = 0.5 * F.cross_entropy(perturbed, gt, ignore_index=255)
                if args.arm in ('A1','A2','A3','A5'):
                    kl, n = p.consistency(detached, perturbed, gt, available, args.arm,
                                         torch.Generator().manual_seed(key+4))
                    loss = loss + cfg['consistency_weight'] * kl
                    pixels += n
                if not torch.isfinite(loss):
                    raise RuntimeError('nonfinite perturbed loss')
                total_loss += float(loss.detach()) / accum
                (loss / accum).backward()
                del loss, perturbed, detached, op, ds, gt, op2, aux2, aux, available
            torch.nn.utils.clip_grad_norm_(list(net.parameters()) + ([] if head is None else list(head.parameters())),
                                           float('inf'), error_if_nonfinite=True)
            optimizer.step()
            if step == 1 or step % 20 == 0 or step == target:
                print(f'{args.arm} seed{args.seed} step={step}/{target} loss={total_loss:.6f} selected={pixels} elapsed={time.time()-started:.1f}s', flush=True)
            if step % cfg['checkpoint_every'] == 0 or step == target:
                save(out / 'last_train_state.pth', net, head, optimizer, step, signature, counts)
        p.write(summary_path, dict(**metadata, global_step=target, checkpoint_sha256=p.sha(out / 'last_train_state.pth'),
                                 treatment_counts=counts, seconds_this_session=time.time()-started,
                                 checkpoint_selection='fixed_final_step', smoke=args.smoke))
        print('TRAIN COMPLETE', out, flush=True)
    finally:
        if handle is not None:
            handle.remove()


if __name__ == '__main__':
    main()
