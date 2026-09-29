"""Bounded D21 throughput probe on one visible GPU; never saves checkpoints."""
import argparse
import gc
import json
import os
from pathlib import Path
import random
import resource
import subprocess
import time

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
os.environ.setdefault('XFORMERS_DISABLED', '1')

import torch
import numpy as np
import d21_common as p
import d18_d19_night as d18
import d16_d17_portfolio as old
import train_rebuild_v1_r02_budget_pilot as r02
from train_rebuild_v1_d16_d17 import sample
from run_rebuild_v1_d21_job import build, load, transform


def training_batch(cache, ids, base, parent, job, step):
    """Build identical 16-item samples for every microbatch candidate."""
    names = list(parent['treatment_probabilities'])
    weights = list(parent['treatment_probabilities'].values())
    sampler = dict(base, patch=p.config()['patch'], micro_batch=1)
    clean_op, clean_aux, damaged_op, damaged_aux, labels = [], [], [], [], []
    for index in range(16):
        key = job['seed'] * 1000000 + step * 100 + index
        op, ds, gt, _ = sample(cache, ids, sampler, key)
        condition = random.Random(key + 1).choices(names, weights=weights, k=1)
        op2, ds2, _ = transform(op, ds, job['arm'], condition, key + 2)
        clean_op.append(op)
        clean_aux.append(op.mean(1) if job['arm'] == 'M1' else ds)
        damaged_op.append(op2)
        damaged_aux.append(ds2)
        labels.append(gt)
    return tuple(torch.cat(parts) for parts in
                 (clean_op, clean_aux, damaged_op, damaged_aux, labels))


def step_once(model, optimizer, batch, micro):
    optimizer.zero_grad(set_to_none=True)
    op, aux, op2, aux2, gt = batch
    accum = 16 // micro
    for offset in range(0, 16, micro):
        end = offset + micro
        for rgb, height in ((op[offset:end], aux[offset:end]),
                            (op2[offset:end], aux2[offset:end])):
            logits = model(rgb, height)
            loss = .5 * old.deterministic_ce(logits, gt[offset:end]) / accum
            if not bool(torch.isfinite(loss)):
                raise RuntimeError('nonfinite loss')
            loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), float('inf'), error_if_nonfinite=True)
    optimizer.step()
    torch.cuda.synchronize()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', choices=('potsdam', 'vaihingen'), default='vaihingen')
    ap.add_argument('--arm', choices=('R0', 'M0', 'F2'), default='F2')
    ap.add_argument('--warmup', type=int, default=2)
    ap.add_argument('--measured', type=int, default=6)
    ap.add_argument('--max-minutes', type=float, default=20)
    ap.add_argument('--output', type=Path, default=p.ROOT/'records/rebuild_v1_d21_throughput_probe_20260929/result.json')
    args = ap.parse_args()
    if args.warmup < 1 or args.measured < 2 or not 1 <= args.max_minutes <= 30:
        raise ValueError('bounded probe requires warmup >=1, measured >=2 and max-minutes 1..30')
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError('exactly one visible CUDA GPU required')
    if not os.environ.get('CUDA_VISIBLE_DEVICES'):
        raise RuntimeError('set CUDA_VISIBLE_DEVICES to one explicitly selected physical GPU')
    started = time.monotonic()
    deadline = started + args.max_minutes * 60
    job = dict(dataset=args.dataset, arm=args.arm, seed=42)
    cfg = p.config()
    base, parent = p.read(d18.base_config()), p.read(d18.CONFIG)
    repo, weights = d18.artifacts()
    if not repo.is_dir() or not weights.is_file():
        raise RuntimeError('DINO source/weights missing; this probe never downloads or installs')
    dino_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    if dino_commit != parent['dino']['repository_commit']:
        raise RuntimeError('DINO source commit differs from frozen D21 input')
    weights_sha256 = p.sha(weights)
    manifest = p.read(weights.with_suffix('.manifest.json'))
    if manifest['sha256'] != weights_sha256 or manifest['repository_commit'] != dino_commit:
        raise RuntimeError('DINO weight manifest mismatch')
    ids = p.datasets()[args.dataset]['train']
    cache = {}
    for tile in ids:
        item = load(args.dataset, tile)
        cache[str(tile)] = (item['optical'], item['dsm'], item['full_gt'])
    ids = list(cache)
    result = dict(kind='bounded_throughput_not_accuracy_evidence', job=job,
                  git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=p.ROOT, text=True).strip(),
                  config_sha256=p.sha(p.CONFIG), dino_commit=dino_commit,
                  dino_weights_sha256=weights_sha256,
                  device=torch.cuda.get_device_name(), visible_gpu=os.environ['CUDA_VISIBLE_DEVICES'],
                  torch_version=torch.__version__, effective_batch=16, warmup=args.warmup,
                  measured=args.measured, max_minutes=args.max_minutes,
                  note='Canonical per-sample data stream is shared across candidates; it differs from original D21 per-micro sampling. Throughput only.',
                  candidates=[])
    for micro in (2, 4, 8, 16):
        if time.monotonic() >= deadline:
            result['stop_reason'] = 'time_limit_before_candidate'
            break
        r02.set_seed(42)
        model = build(job)
        optimizer = r02.build_optimizer(model, dict(base, optimizer=parent['pretrained_optimizer'], schedule=parent['schedule']))
        model.train()
        torch.cuda.reset_peak_memory_stats()
        prepare, compute = [], []
        try:
            for index in range(args.warmup + args.measured):
                if time.monotonic() >= deadline:
                    raise TimeoutError('probe time limit reached between steps')
                t0 = time.monotonic()
                batch = training_batch(cache, ids, base, parent, job, index + 1)
                torch.cuda.synchronize()
                t1 = time.monotonic()
                step_once(model, optimizer, batch, micro)
                t2 = time.monotonic()
                if index >= args.warmup:
                    prepare.append(t1-t0)
                    compute.append(t2-t1)
            result['candidates'].append(dict(micro_batch=micro, accum_steps=16//micro,
                preparation_seconds=sum(prepare)/len(prepare), compute_seconds=sum(compute)/len(compute),
                total_seconds=(sum(prepare)+sum(compute))/len(compute),
                effective_samples_per_second=16*len(compute)/(sum(prepare)+sum(compute)),
                cuda_allocated_peak_mib=torch.cuda.max_memory_allocated()/1048576,
                cuda_reserved_peak_mib=torch.cuda.max_memory_reserved()/1048576,
                host_ru_maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
        except (torch.cuda.OutOfMemoryError, TimeoutError) as exc:
            result['candidates'].append(dict(micro_batch=micro, accum_steps=16//micro,
                                              status=type(exc).__name__, message=str(exc)))
            if isinstance(exc, TimeoutError):
                result['stop_reason'] = 'time_limit'
                break
        finally:
            if result['candidates']:
                p.write(args.output, result)
                print('CANDIDATE', json.dumps(result['candidates'][-1], ensure_ascii=False), flush=True)
            del model, optimizer
            gc.collect()
            torch.cuda.empty_cache()
    if time.monotonic() < deadline:
        r02.set_seed(42)
        model = build(job).eval()
        tile = ids[0]
        op, ds, _ = cache[tile]
        torch.cuda.reset_peak_memory_stats()
        t0 = time.monotonic()
        try:
            prediction = r02.infer_tile(model, op, ds, cfg['patch'],
                                        cfg['evaluation_stride'][args.dataset], cfg['evaluation_batch'])
            torch.cuda.synchronize()
            elapsed = time.monotonic()-t0
            result['evaluation'] = dict(split='train', tile=tile, batch=cfg['evaluation_batch'],
                seconds=elapsed, pixels=int(np.prod(prediction.shape)),
                pixels_per_second=int(np.prod(prediction.shape))/elapsed,
                cuda_allocated_peak_mib=torch.cuda.max_memory_allocated()/1048576,
                cuda_reserved_peak_mib=torch.cuda.max_memory_reserved()/1048576)
            del prediction
        except torch.cuda.OutOfMemoryError as exc:
            result['evaluation'] = dict(status='OutOfMemoryError', message=str(exc))
        del model
    else:
        result['evaluation'] = dict(status='skipped_time_limit')
    result['elapsed_seconds'] = time.monotonic()-started
    result['test6_loaded'] = False
    result['development_labels_loaded'] = False
    p.write(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
