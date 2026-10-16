"""D21 matched training and resumable full-tile development evaluation."""
import argparse
import gc
import os
from pathlib import Path
import random
import sys
import time

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
os.environ.setdefault('XFORMERS_DISABLED', '1')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
import d21_common as p
import d18_d19_night as d18
import d16_d17_portfolio as old
import train_rebuild_v1_r02_budget_pilot as r02
from train_rebuild_v1_d16_d17 import sample, save
from d20_vaihingen_smoke_arm import load_tile as load_vai
from model.rebuild_v1_night_screen import load_dino
from model.rebuild_v1_d21_detail import DetailDinoSegmenter
from night_boundary_metrics import boundary_counts


def load(dataset, tile, development=False):
    root = Path(p.datasets()[dataset]['root'])
    if dataset == 'potsdam':
        return r02.load_tile(root, tile, need_nb=development)
    rgb, dsm, gt = load_vai(root, tile, 'gts_complete_full' if development else 'gts_for_participants')
    return dict(optical=rgb, dsm=dsm, full_gt=gt, noboundary_gt=None)


def binding(job, smoke):
    plan = p.read(p.OUT/'plan.json')
    if any(p.sha(p.ROOT/name) != value for name, value in plan['source_sha256'].items()):
        raise RuntimeError('source/config changed during frozen queue')
    manifest = p.read(p.OUT/'input_manifest.json')
    p.verify_inputs(manifest)
    parent = d18.binding('P0', smoke)
    return dict(job=job, smoke=smoke, source_sha256=plan['source_sha256'],
                input_manifest_sha256=p.sha(p.OUT/'input_manifest.json'),
                dino_commit=parent['dino_commit'], dino_sha256=parent['anchor_sha256'],
                torch_version=torch.__version__, test6_loaded=False,
                independent_final_loaded=False, checkpoint_selection='fixed_final_step')


def build(job, state=None):
    repo, weights = d18.artifacts()
    model = DetailDinoSegmenter(load_dino(repo, weights), job['arm']).to(r02.DEVICE)
    if state is not None:
        model.load_state_dict(state['model'], strict=True)
    def finite_output(module, inputs, logits):
        if not bool(torch.isfinite(logits).all()):
            raise RuntimeError('nonfinite logits')
    model.register_forward_hook(finite_output)
    return model


def transform(op, ds, arm, conditions, seed):
    return d18.transform(op, ds, 'P1' if arm == 'M1' else 'P2', conditions,
                         torch.Generator().manual_seed(seed))


def train(job, smoke):
    cfg = p.config()
    target = cfg['smoke_steps'] if smoke else cfg['steps']
    signature = binding(job, smoke)
    out = p.run_dir(job, smoke)
    out.mkdir(parents=True, exist_ok=True)
    ck, summary = out/'last_train_state.pth', out/'summary.json'
    if summary.is_file():
        previous = p.read(summary)
        if previous['signature'] != signature or previous['global_step'] != target or p.sha(ck) != previous['checkpoint_sha256']:
            raise RuntimeError('completed training binding mismatch')
        print('TRAIN REUSED', p.key(job, smoke), flush=True)
        return
    r02.set_seed(job['seed'])
    state = torch.load(ck, map_location='cpu', weights_only=False) if ck.is_file() else None
    if state is not None and state['signature'] != signature:
        raise RuntimeError('resume signature mismatch')
    model = build(job, state)
    base, parent = p.read(d18.base_config()), p.read(d18.CONFIG)
    optcfg = dict(base, optimizer=parent['pretrained_optimizer'], schedule=parent['schedule'])
    optimizer = r02.build_optimizer(model, optcfg)
    if state is not None:
        optimizer.load_state_dict(state['optimizer'])
        old.restore_rng(state)
    else:
        r02.set_seed(job['seed'])
    start = int(state['global_step']) if state else 0
    counts = state['treatment_counts'] if state else {k: 0 for k in parent['treatment_probabilities']}
    del state
    ids = p.datasets()[job['dataset']]['train']
    if smoke:
        ids = ids[:1]
    cache = {}
    for tile in ids:
        item = load(job['dataset'], tile)
        cache[str(tile)] = (item['optical'], item['dsm'], item['full_gt'])
    sampler = dict(base, patch=cfg['patch'], micro_batch=cfg['micro_batch'])
    accum = cfg['accum_steps']
    names, weights = list(parent['treatment_probabilities']), list(parent['treatment_probabilities'].values())
    started = time.monotonic()
    model.train()
    for step in range(start+1, target+1):
        optimizer.zero_grad(set_to_none=True)
        r02.set_lr(optimizer, optcfg, step, cfg['steps'])
        loss_value = 0.
        for micro in range(accum):
            key = job['seed']*1000000 + step*100 + micro
            op, ds, gt, _ = sample(cache, list(cache), sampler, key)
            conditions = random.Random(key+1).choices(names, weights=weights, k=len(op))
            for condition in conditions:
                counts[condition] += 1
            op2, ds2, _ = transform(op, ds, job['arm'], conditions, key+2)
            clean_aux = op.mean(1) if job['arm'] == 'M1' else ds
            for optical, aux in ((op, clean_aux), (op2, ds2)):
                logits = model(optical, aux)
                loss = .5 * old.deterministic_ce(logits, gt)
                if not bool(torch.isfinite(loss)):
                    raise RuntimeError(f'nonfinite loss step {step}')
                loss_value += float(loss.detach()) / accum
                (loss/accum).backward()
                del loss, logits
        torch.nn.utils.clip_grad_norm_(model.parameters(), float('inf'), error_if_nonfinite=True)
        optimizer.step()
        if step == 1 or step % 100 == 0 or step == target:
            torch.cuda.synchronize()
            elapsed = time.monotonic()-started
            progress = dict(job=job, step=step, target=target, elapsed_seconds=elapsed,
                seconds_per_step=elapsed/max(1, step-start),
                remaining_hours=(target-step)*elapsed/max(1, step-start)/3600,
                gpu_peak_memory_mib=torch.cuda.max_memory_allocated()/1024**2)
            p.write(out/'progress.json', progress)
            print('TRAIN', p.key(job, smoke), progress, 'loss', loss_value, flush=True)
        if step % cfg['checkpoint_every'] == 0 or step == target:
            save(ck, model, None, optimizer, step, signature, counts)
    op, ds, _, _ = sample(cache, list(cache), dict(sampler, micro_batch=1), job['seed']*1000000+999999)
    aux = op.mean(1) if job['arm'] == 'M1' else ds
    model.eval()
    with torch.no_grad():
        pred = model(op, aux).argmax(1).cpu()
    probe = out/'clean_probe.pth'
    tmp = probe.with_suffix('.tmp')
    torch.save(dict(rgb=op.cpu(), aux=aux.cpu(), pred=pred), tmp)
    os.replace(tmp, probe)
    p.write(summary, dict(job=job, signature=signature, global_step=target,
        checkpoint_sha256=p.sha(ck), clean_probe_sha256=p.sha(probe),
        treatment_counts=counts, seconds_this_session=time.monotonic()-started,
        train_tiles=ids, development_labels_loaded=False, test6_loaded=False,
        trainable_parameters=sum(x.numel() for x in model.parameters() if x.requires_grad),
        total_parameters=sum(x.numel() for x in model.parameters())))


def metrics(cm):
    result = r02.metrics_from_cm(cm)
    result = {k: None if isinstance(v, float) and not np.isfinite(v) else v for k,v in result.items()}
    result['class_true_count'] = cm.sum(1).tolist()
    result['class_predicted_count'] = cm.sum(0).tolist()
    result['class_correct_count'] = np.diag(cm).tolist()
    return result


def evaluate(job, smoke):
    cfg = p.config()
    signature = binding(job, smoke)
    run, out = p.run_dir(job, smoke), p.eval_dir(job, smoke)
    train_result = p.read(run/'summary.json')
    ck = run/'last_train_state.pth'
    if train_result['signature'] != signature or p.sha(ck) != train_result['checkpoint_sha256']:
        raise RuntimeError('training/checkpoint binding mismatch')
    signature = dict(training=signature, checkpoint_sha256=p.sha(ck))
    out.mkdir(parents=True, exist_ok=True)
    r02.set_seed(job['seed'])
    state = torch.load(ck, map_location='cpu', weights_only=False)
    if state['signature'] != signature['training']:
        raise RuntimeError('checkpoint signature mismatch')
    model = build(job, state).eval()
    del state
    probe_path = run/'clean_probe.pth'
    if p.sha(probe_path) != train_result['clean_probe_sha256']:
        raise RuntimeError('clean probe changed')
    probe = torch.load(probe_path, map_location='cpu', weights_only=False)
    with torch.no_grad():
        reproduced = model(probe['rgb'].to(r02.DEVICE), probe['aux'].to(r02.DEVICE)).argmax(1).cpu()
    if not torch.equal(reproduced, probe['pred']):
        raise RuntimeError('saved checkpoint did not reproduce clean training probe')
    del probe, reproduced
    # Smoke uses a training crop only; it never screens candidates on validation.
    spec = p.datasets()[job['dataset']]
    ids = spec['train'][:1] if smoke else spec['dev']
    conditions = ['clean', 'aux_zero', 'aux_shift8'] if smoke else cfg['evaluation_conditions']
    scopes = ['full'] if smoke or job['dataset'] == 'vaihingen' else ['full', 'noboundary']
    started = time.monotonic()
    for tile in ids:
        item = None
        for condition in conditions:
            predpath, detail = out/condition/f'{tile}.npy', out/condition/f'{tile}.json'
            if detail.is_file() and predpath.is_file():
                row = p.read(detail)
                if row['signature'] != signature or row['prediction_sha256'] != p.sha(predpath):
                    raise RuntimeError('existing prediction binding mismatch')
                continue
            if item is None:
                item = load(job['dataset'], tile, development=not smoke)
                if smoke:
                    item = {k: v[:512, :512] if v is not None else None for k,v in item.items()}
            op = torch.from_numpy(np.ascontiguousarray(item['optical'].transpose(2,0,1)))[None]
            ds = torch.from_numpy(np.ascontiguousarray(item['dsm']))[None]
            # Corruption seed is identical across all arms and training seeds.
            treated, aux, _ = transform(op, ds, job['arm'], [condition], 42+sum(map(ord,str(tile))))
            optical = np.ascontiguousarray(treated[0].permute(1,2,0).numpy())
            secondary = np.ascontiguousarray(aux[0].numpy())
            pred = r02.infer_tile(model, optical, secondary, cfg['patch'],
                        cfg['evaluation_stride'][job['dataset']], cfg['evaluation_batch'])
            if smoke:
                again = r02.infer_tile(model, optical, secondary, cfg['patch'], cfg['patch'], cfg['evaluation_batch'])
                if not np.array_equal(pred, again):
                    raise RuntimeError('repeated smoke inference changed')
            values = {}
            for scope in scopes:
                label = item[scope+'_gt']
                cm = np.zeros((6,6), dtype=np.int64)
                r02.update_cm(cm, label, pred)
                expected = int(((label >= 0) & (label < 6)).sum())
                if int(cm.sum()) != expected:
                    raise RuntimeError('confusion matrix pixel count mismatch')
                values[scope] = dict(cm=cm.tolist(), metrics=metrics(cm))
            boundaries = boundary_counts(item['full_gt'], pred, cfg['boundary_tolerance_pixels']) if condition in ('clean','rgb_down4','aux_shift8') else None
            predpath.parent.mkdir(parents=True, exist_ok=True)
            tmp = predpath.with_suffix('.tmp.npy')
            np.save(tmp, pred)
            os.replace(tmp, predpath)
            p.write(detail, dict(signature=signature, tile=str(tile), condition=condition,
                scopes=values, prediction_sha256=p.sha(predpath), boundary_counts=boundaries))
            print('EVAL', p.key(job, smoke), tile, condition, flush=True)
    results = {}
    for condition in conditions:
        rows = {str(tile): p.read(out/condition/f'{tile}.json') for tile in ids}
        pooled = {}
        for scope in scopes:
            cm = sum((np.asarray(row['scopes'][scope]['cm'], dtype=np.int64) for row in rows.values()), np.zeros((6,6),dtype=np.int64))
            pooled[scope] = dict(cm=cm.tolist(), metrics=metrics(cm))
        # Keep the signature once in summary, retain all original counts and hashes.
        tiles = {tile: {k:v for k,v in row.items() if k != 'signature'} for tile,row in rows.items()}
        results[condition] = dict(pooled=pooled, tiles=tiles)
    if job['arm'] == 'R0':
        for condition in conditions:
            if condition.startswith('aux_'):
                for scope in scopes:
                    if results[condition]['pooled'][scope]['cm'] != results['clean']['pooled'][scope]['cm']:
                        raise RuntimeError('optical-only auxiliary invariance failed')
    p.write(out/'summary.json', dict(job=job, signature=signature, smoke=smoke,
        conditions=results, evaluation_ids=ids, trainable_parameters=train_result['trainable_parameters'],
        checkpoint_reload_pass=True, test6_loaded=False, independent_final_loaded=False,
        primary_scope=cfg['primary_scope'][job['dataset']],
        evaluation_seconds=time.monotonic()-started))
    print('JOB COMPLETE', p.key(job, smoke), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', choices=p.config()['datasets'], required=True)
    ap.add_argument('--arm', choices=p.config()['arms'], required=True)
    ap.add_argument('--seed', type=int, choices=p.config()['seeds'], required=True)
    ap.add_argument('--smoke', action='store_true')
    args = ap.parse_args()
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError('exactly one visible CUDA GPU required')
    job = dict(dataset=args.dataset, arm=args.arm, seed=args.seed)
    train(job, args.smoke)
    gc.collect()
    torch.cuda.empty_cache()
    evaluate(job, args.smoke)


if __name__ == '__main__':
    main()
