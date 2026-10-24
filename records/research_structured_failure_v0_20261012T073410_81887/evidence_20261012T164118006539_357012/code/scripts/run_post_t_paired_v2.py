"""Six fresh paired trainings; only explicit GPU releases permit automatic continuation."""
import argparse
from collections import Counter
import os
from pathlib import Path
import sys
import time
import random
import numpy as np
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
os.environ.setdefault('XFORMERS_DISABLED', '1')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import torch
from model.rebuild_v1_d26 import build_experts
from model.post_t_paired_v2 import PairedAdaptation, frozen_digest, optimizer_for, lr_factor
from post_t_paired_v2_common import *
from post_t_paired_v2_data import Crops, BatchLedger
from post_ab_n1_data import Loader, PrefetchedBatches
from post_s1_support_evaluation import support_objective
from post_t_paired_v2_evaluation import ReferenceStore, evaluate, ordinary_keys, checkpoint_selection
from run_post_s1_transfer import load_anchors, seed_all, copy, verify_gradients
from post_t_paired_v2_runtime import PausedForUser, poll_release, mark_pause, validate_device

PAUSE_SAVE = None
PAUSE_CONTEXT = None


def save(path, model, optimizer, step, signature, best, counts, gradient, observed=()):
    tmp = path.with_suffix('.tmp')
    torch.save(dict(model=model.state_dict(), optimizer=optimizer.state_dict(), global_step=step,
                    signature=signature, best=best, treatment_counts=dict(counts), gradient_check=gradient,
                    observed_nonzero=sorted(observed), random_state=random.getstate(),
                    numpy_state=np.random.get_state(), torch_rng=torch.get_rng_state(),
                    cuda_rng=torch.cuda.get_rng_state_all()), tmp)
    os.replace(tmp, path)


def setup(root, base, p, gpu):
    verify_snapshot(base)
    validate_device(gpu)
    if torch.__version__ != '2.2.2+cu121':
        raise RuntimeError('bound Torch2.2.2+cu121 required')
    from post_n2_diag_runtime import input_contract
    input_contract(root, p)
    prep = read(base / 'preparation_complete.json')
    for key, name in (('plan_sha256', 'plan.json'), ('mask_manifest_sha256', 'mask_manifest.json'), ('reference_index_sha256', 'reference_index.json')):
        if prep[key] != sha(base / name):
            raise RuntimeError('CPU preparation binding changed')
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True


def make_model(root, p, job):
    seed_all()
    states, provenance = load_anchors(root, p)
    experts = build_experts(root, states)
    seed_all()
    model = PairedAdaptation(*experts, job, p['initial_checkpoint']['path'], p['initial_checkpoint']['sha256']).cuda()
    return model, provenance


def main():
    global PAUSE_SAVE, PAUSE_CONTEXT
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--directory', type=Path, required=True)
    ap.add_argument('--job', choices=TRAIN_ORDER, required=True)
    ap.add_argument('--gpu', type=int, choices=(0, 1), required=True)
    ap.add_argument('--resume', action='store_true')
    a = ap.parse_args()
    root, base = dirs(a.root, a.directory)
    p = validate(read(base / 'plan.json'))
    job = card(a.job)
    cfg = resolved_job(p, job)['training']
    setup(root, base, p, a.gpu)
    out = base / 'jobs' / a.job
    if a.resume:
        if not (out / 'paused.json').exists() or (out / 'complete.json').exists():
            raise RuntimeError('only cooperatively paused jobs may resume')
    out.mkdir(parents=True, exist_ok=a.resume)
    import fcntl
    lock = (out / 'worker.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    sig = signature(base, p, job)
    if (out / 'preflight.json').exists() and read(out / 'preflight.json') != sig:
        raise RuntimeError('resume signature changed')
    write(out / 'preflight.json', sig)
    began = time.monotonic()
    state_progress = dict(job=a.job, target=job['steps'], step=0, physical_gpu=a.gpu)
    PAUSE_CONTEXT = (base, a.job, a.gpu, state_progress)
    def progress(**kw):
        poll_release(base, a.gpu)
        if kw.get('phase', state_progress.get('phase')) != state_progress.get('phase'):
            for n in ('windows_done', 'windows_total', 'tile', 'condition'):
                state_progress.pop(n, None)
        state_progress.update(kw)
        state_progress.update(observed_at=now(), elapsed_seconds=time.monotonic() - began)
        write(out / 'progress.json', state_progress)
    progress(phase='loading_bound_weights')
    model, provenance = make_model(root, p, job)
    initial_frozen = frozen_digest(model)
    params = dict(model.named_parameters())
    trainable = [n for n, v in params.items() if v.requires_grad]
    optimizer = optimizer_for(model, cfg)
    write(out / 'model_capacity.json', dict(total_parameters=sum(v.numel() for v in params.values()),
          trainable_parameters=sum(params[n].numel() for n in trainable), trainable_names=trainable,
          frozen_names=[n for n in params if n not in trainable],
          optimizer_groups=[dict(names=g['names'], initial_lr=g['initial_lr']) for g in optimizer.param_groups],
          initial_frozen_digest=initial_frozen, mechanism=job['mechanism'],
          expert_forward_calls_per_window=dict(base_rgb=1, base_dsm=1, private_rgb=1),
          compute_claim='measured native inference seconds; no shared-prefix or FLOPs saving claim'))
    write(out / 'environment.json', dict(torch_version=torch.__version__, experts=provenance,
          allowed_physical_gpus=[0, 1], seed=42, batch=16, precision='trainBF16_evalFP32_TF32',
          test6_loaded=False, independent_final_loaded=False))
    loader = Loader(root, p)
    refs = ReferenceStore(base, p)
    counts = Counter()
    gradient = None
    observed_nonzero = set()
    best = None
    selections = []
    checkpoints = out / 'checkpoints'
    checkpoints.mkdir(exist_ok=a.resume)
    last = out / 'last_train_state.pth'
    current_step = 0
    if a.resume and last.exists():
        st = torch.load(last, map_location='cpu', weights_only=False)
        if st['signature'] != sig:
            raise RuntimeError('paused checkpoint signature differs')
        model.load_state_dict(st['model'], strict=True)
        optimizer.load_state_dict(st['optimizer'])
        current_step = st['global_step']
        counts = Counter(st['treatment_counts'])
        gradient = st['gradient_check']
        observed_nonzero = set(st['observed_nonzero'])
        best = st['best']
        random.setstate(st['random_state'])
        np.random.set_state(st['numpy_state'])
        torch.set_rng_state(st['torch_rng'])
        torch.cuda.set_rng_state_all(st['cuda_rng'])
        del st
        if (out / 'selection.json').exists():
            saved_selection = read(out / 'selection.json')
            selections = saved_selection['candidates']
            best = saved_selection['selected']
        if frozen_digest(model) != initial_frozen:
            raise RuntimeError('paused frozen state changed')
    PAUSE_SAVE = lambda: save(last, model, optimizer, current_step, sig, best, counts, gradient, observed_nonzero)
    state_progress['step'] = current_step
    with (out / 'device_sessions.jsonl').open('a', encoding='utf-8') as history:
        import subprocess, json
        uuid = subprocess.check_output(['nvidia-smi', '-i', str(a.gpu), '--query-gpu=uuid', '--format=csv,noheader'], text=True).strip()
        history.write(json.dumps(dict(physical_gpu=a.gpu, uuid=uuid, resume=a.resume, start_step=current_step, at=now())) + '\n')
    model.eval()
    if current_step == 0:
        initial = evaluate(model, loader, refs, p, out, dict(training=sig, step=0), progress, base,
                           ['rgb_U', 'dsm_U'], 'initial_U')
    else:
        initial = read(out / 'initial_U/summary.json')
    # All three new mechanisms have the same initial forward before any update.
    old_m = read(Path(p['predecessor_directory']) / 'jobs/M000_context/summary.json')
    for key in ('rgb_U', 'dsm_U'):
        for tile in p['data']['validation']:
            if initial['tiles'][key][tile]['predictions']['candidate'] != old_m['tiles'][key][tile]['predictions']['candidate']:
                raise RuntimeError('initial paired forward does not reproduce M000_context')

    def validate_at(step):
        nonlocal best
        save(last, model, optimizer, step, sig, best, counts, gradient, observed_nonzero)
        point = checkpoints / ('step_%05d.pth' % step)
        if not point.exists():
            copy(last, point)
        else:
            old = torch.load(point, map_location='cpu', weights_only=False)
            if old['signature'] != sig or old['global_step'] != step or any(not torch.equal(old['model'][n].to(v.device), v) for n, v in model.state_dict().items()):
                raise RuntimeError('preserve conflicting validation checkpoint')
            del old
        binding = dict(training=sig, step=step, checkpoint_sha256=sha(point))
        model.eval()
        us = evaluate(model, loader, refs, p, out, binding, progress, base,
                      ['rgb_U', 'dsm_U'], 'validation/step_%05d/U' % step)
        ps = evaluate(model, loader, refs, p, out, binding, progress, base,
                      ['clean', 'rgb_missing', 'dsm_missing'], 'validation/step_%05d/protection' % step)
        row = checkpoint_selection(us, ps, refs, step)
        row.update(binding=binding, checkpoint_path=str(point))
        selections[:] = [r for r in selections if r['step'] != step] + [row]
        if row['eligible'] and (best is None or row['score'] > best['score']):
            best = row
            copy(point, out / 'selected.pth')
        write(out / 'selection.json', dict(primary='fixed endpoint', selected=best, candidates=selections))
        if frozen_digest(model) != initial_frozen:
            raise RuntimeError('frozen parameters/statistics changed')
        model.train()
        save(last, model, optimizer, step, sig, best, counts, gradient, observed_nonzero)

    if current_step in cfg['validation_steps']:
        validate_at(current_step)

    tiles = {}
    for i, tile in enumerate(p['data']['fit12'] if current_step < job['steps'] else []):
        tiles[tile] = loader(tile)
        progress(phase='loading_fit_tiles', tiles_loaded=i + 1, tiles_total=12)
    input_path = out / 'input_binding.json'
    previous_inputs = read(input_path)['files'] if input_path.exists() else {}
    previous_inputs.update(loader.verified)
    write(input_path, dict(files=previous_inputs, input_manifest_sha256=p['input_manifest_sha256']))
    dataset = Crops(tiles, p['data']['fit12'], loader.base['augmentation'], p, job, current_step) if current_step < job['steps'] else None
    batches = PrefetchedBatches(dataset, 16, 8, 4, True) if dataset is not None else []
    # Only previously completed training arms are comparisons; never read an active peer.
    peers = []
    for name in TRAIN_ORDER:
        if name != a.job and (base / 'jobs' / name / 'complete.json').exists():
            accept_worker(base, name, p)
            peers.append(base / 'jobs' / name / 'batch_hashes.jsonl')
    ledger = BatchLedger(out, peers, current_step)
    model.train()
    tick = time.monotonic()
    train_seconds = 0.
    start_step = current_step
    step = current_step
    for step, batch in enumerate(batches, current_step + 1):
        poll_release(base, a.gpu)
        ledger.record(step, batch)
        optimizer.zero_grad(set_to_none=True)
        for group in optimizer.param_groups:
            group['lr'] = group['initial_lr'] * lr_factor(step, job['steps'])
        tensors = {k: v.cuda(non_blocking=True) for k, v in batch.items() if torch.is_tensor(v)}
        loss, denominators = support_objective(model, tensors)
        if not torch.isfinite(loss):
            raise RuntimeError('nonfinite loss')
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), float('inf'), error_if_nonfinite=True)
        # Record all parameter gradient connectivity once and first supported update,
        # then every500; zero-support batches are legitimate zero gradients.
        supported = model.exposure['residual_support_pixels'] > 0
        if gradient is None or (supported and not observed_nonzero) or step % 500 == 0:
            gradient = verify_gradients(model)
            observed_nonzero.update(n for n, flag in gradient['groups_nonzero'].items() if flag)
            write(out / 'gradient_diagnostics' / ('step_%05d.json' % step),
                  dict(step=step, signature=sig, denominators=denominators, **gradient))
        optimizer.step()
        current_step = step
        state_progress['step'] = step
        counts.update(denominators)
        counts.update(batch['treatment'])
        counts.update(branch_exposed_updates=int(supported),
                      branch_nonzero_updates=int(any(v.grad is not None and bool(v.grad.abs().sum() > 0) for v in model.branch.parameters())))
        train_seconds += time.monotonic() - tick
        if step == 1 or step % 20 == 0 or step == job['steps']:
            progress(phase='training', step=step, loss=float(loss.detach()),
                     seconds_per_train_step=train_seconds / (step - start_step),
                     remaining_train_hours=(job['steps'] - step) * train_seconds / (step - start_step) / 3600,
                     gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated())
            print('PAIRED_TRAIN', a.job, step, job['steps'], float(loss.detach()), flush=True)
        del tensors, loss
        if step % 500 == 0:
            save(last, model, optimizer, step, sig, best, counts, gradient, observed_nonzero)
        if step in cfg['validation_steps']:
            validate_at(step)
        tick = time.monotonic()
    if step != job['steps']:
        raise RuntimeError('sample stream ended at wrong budget')
    write(out / 'data_stream.json', ledger.close())
    # Evaluation may temporarily load the secondary selected age. Preserve the
    # final optimizer checkpoint for all evaluation-only pauses.
    PAUSE_SAVE = lambda: None
    del batches, dataset, tiles, optimizer
    endpoint = checkpoints / ('step_%05d.pth' % job['steps'])
    copy(endpoint, out / 'endpoint.pth')
    # A failure of scientific eligibility is reported, never fixed by retraining.
    if best is None:
        copy(endpoint, out / 'selected.pth')
        write(out / 'selection.json', dict(primary='fixed endpoint', selected=None, candidates=selections,
              storage_fallback='selected.pth stores endpoint, not an eligible selected candidate'))
    model.eval()
    binding = dict(training=sig, step=job['steps'], checkpoint_sha256=sha(endpoint), primary=True)
    evaluate(model, loader, refs, p, out, binding, progress, base, ordinary_keys(p), 'endpoint_ordinary')
    evaluate(model, loader, refs, p, out, binding, progress, base, ['rgb_U', 'dsm_U'], 'endpoint_U')
    evaluate(model, loader, refs, p, out, binding, progress, base, E_KEYS, 'endpoint_E')
    secondary = dict(selected=best, primary=False)
    if best is not None and best['step'] != job['steps']:
        selected = torch.load(out / 'selected.pth', map_location='cpu', weights_only=False)
        if selected['signature'] != sig or selected['global_step'] != best['step']:
            raise RuntimeError('secondary selected binding changed')
        model.load_state_dict(selected['model'], strict=True)
        del selected
        model.eval()
        sb = dict(training=sig, selected=best, primary=False)
        for keys, tag in ((ordinary_keys(p), 'ordinary'), (['rgb_U', 'dsm_U'], 'U'), (E_KEYS, 'E')):
            evaluate(model, loader, refs, p, out, sb, progress, base, keys, 'secondary_' + tag)
        secondary['tags'] = ['secondary_ordinary', 'secondary_U', 'secondary_E']
    else:
        secondary['reuse_endpoint'] = True
    write(out / 'secondary_results.json', secondary)
    final_frozen = frozen_digest(model)
    if initial_frozen != final_frozen:
        raise RuntimeError('frozen state changed')
    # Every allowed private parameter must have actually received a nonzero gradient.
    missing = sorted(set(trainable) - observed_nonzero)
    if missing:
        raise RuntimeError('declared trainable but never observed nonzero gradient: ' + str(missing))
    write(out / 'gradient_contract.json', dict(passed=True, trainable_names=trainable,
          observed_nonzero_names=sorted(observed_nonzero), diagnostic_period=500,
          frozen_gradients_absent=True, classifier_frozen=True))
    write(out / 'protection.json', dict(frozen_state_equal=True, initial_digest=initial_frozen,
          final_digest=final_frozen, native_outside_support_equal=True,
          scope='all evaluated checkpoint/endpoint/secondary cases'))
    previous_inputs.update(loader.verified)
    write(out / 'input_binding.json', dict(files=previous_inputs, input_manifest_sha256=p['input_manifest_sha256']))
    names = [f.relative_to(out).as_posix() for f in out.rglob('*.json') if f.name not in ('complete.json', 'progress.json', 'paused.json')]
    names += ['selected.pth', 'endpoint.pth', 'last_train_state.pth', 'batch_hashes.jsonl', 'device_sessions.jsonl']
    names += [f.relative_to(out).as_posix() for f in checkpoints.glob('*.pth')]
    write(out / 'complete.json', dict(signature=sig, optimizer_updates=job['steps'], global_step=job['steps'],
          frozen_state_equal=True, gradient_contract_passed=True, treatment_counts=dict(counts),
          selected=best, artifacts={n: sha(out / n) for n in names}, completed_at=now(),
          test6_loaded=False, independent_final_loaded=False))
    progress(phase='complete', step=job['steps'])
    print('PAIRED_TRAIN_COMPLETE', a.job, flush=True)
    lock.close()


if __name__ == '__main__':
    try:
        main()
    except PausedForUser as exc:
        if PAUSE_SAVE is not None:
            PAUSE_SAVE()
        if PAUSE_CONTEXT is not None:
            b, j, g, progress_state = PAUSE_CONTEXT
            mark_pause(b, j, g, progress_state['step'], exc)
        print('PAIRED_PAUSED_GPU_RELEASED_ON_EXIT', str(exc), flush=True)
        sys.exit(75)
