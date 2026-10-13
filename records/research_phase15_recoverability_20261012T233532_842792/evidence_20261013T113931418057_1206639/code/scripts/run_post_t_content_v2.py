"""Two batches of24 fixed-model DSM content cases; interruption reuses complete cases."""
import argparse
import os
from pathlib import Path
import sys
import time
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
os.environ.setdefault('XFORMERS_DISABLED', '1')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import torch
from post_t_paired_v2_common import *
from post_t_paired_v2_runtime import PausedForUser, poll_release, mark_pause
from post_t_paired_v2_evaluation import ReferenceStore, evaluate, content_screen
from post_ab_n1_data import Loader
from model.post_t_paired_v2 import intervene
from run_post_t_paired_v2 import setup, make_model
from run_post_t_mechanism import load_model as load_old_model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--directory', type=Path, required=True)
    ap.add_argument('--job', choices=('CONTENT_PRE', 'CONTENT_POST'), required=True)
    ap.add_argument('--gpu', type=int, choices=(0, 1), required=True)
    ap.add_argument('--resume', action='store_true')
    a = ap.parse_args()
    root, base = dirs(a.root, a.directory)
    p = validate(read(base / 'plan.json'))
    job = card(a.job)
    setup(root, base, p, a.gpu)
    out = base / 'jobs' / a.job
    if a.resume and not (out / 'paused.json').exists():
        raise RuntimeError('only user-paused diagnostic can resume')
    out.mkdir(parents=True, exist_ok=a.resume)
    import fcntl
    lock = (out / 'worker.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    sig = signature(base, p, job)
    began = time.monotonic()
    def progress(**kw):
        poll_release(base, a.gpu)
        write(out / 'progress.json', dict(job=a.job, physical_gpu=a.gpu, optimizer_updates=0,
              elapsed_seconds=time.monotonic() - began, observed_at=now(), **kw))
    try:
        loader = Loader(root, p)
        refs = ReferenceStore(base, p)
        summaries = {}
        checks = []
        for name in job['models']:
            progress(phase='loading_model', model=name)
            if a.job == 'CONTENT_PRE':
                parent = source_plan()
                oldcard = next(j for j in parent['jobs'] if j['id'] == name)
                model, mb = load_old_model(root, parent, oldcard)
                expected = read(Path(p['predecessor_directory']) / 'jobs' / name / 'summary.json')
                hook_target = model.base.dsm_expert
            else:
                accepted = accept_worker(base, name, p)
                model, provenance = make_model(root, p, card(name))
                point = base / 'jobs' / name / 'endpoint.pth'
                digest = sha(point)
                if digest != accepted['artifacts']['endpoint.pth']:
                    raise RuntimeError('fixed endpoint changed')
                state = torch.load(point, map_location='cpu', weights_only=False)
                if state['signature'] != signature(base, p, card(name)) or state['global_step'] != 16000:
                    raise RuntimeError('post content endpoint age differs')
                model.load_state_dict(state['model'], strict=True)
                del state
                mb = dict(checkpoint_path=str(point), checkpoint_sha256=digest, fixed_step=16000)
                expected = read(base / 'jobs' / name / 'endpoint_E/summary.json')
                hook_target = None
            model.eval().requires_grad_(False)
            summaries[name] = {}
            model_checks = []
            for mode in job['interventions']:
                handle = None
                if hook_target is not None:
                    handle = hook_target.register_forward_hook(lambda m, args, output, mode=mode: (output[0], intervene(output[1], mode)))
                else:
                    model.dsm_intervention = mode
                binding = dict(training=sig, source_model=name, checkpoint=mb, intervention=mode,
                               optimizer_updates=0)
                try:
                    summaries[name][mode] = evaluate(model, loader, refs, p, out, binding, progress, base,
                          CONTENT_KEYS, name + '/' + mode, expected=expected if mode == 'C' else None,
                          check_raw_outside=hook_target is None,
                          endpoint_checks=model_checks if mode == 'C' else None)
                finally:
                    if handle is not None:
                        handle.remove()
            for row in model_checks:
                row['model'] = name
            checks.extend(model_checks)
            del model
            torch.cuda.empty_cache()
        write(out / 'endpoint_checks.json', checks)
        write(out / 'content_screen.json', content_screen(summaries))
        write(out / 'input_binding.json', dict(files=loader.verified, input_manifest_sha256=p['input_manifest_sha256']))
        names = [f.relative_to(out).as_posix() for f in out.rglob('*.json') if f.name not in ('complete.json', 'progress.json', 'paused.json')]
        write(out / 'complete.json', dict(signature=sig, cases=24, optimizer_updates=0,
              artifacts={n: sha(out / n) for n in names}, completed_at=now(), test6_loaded=False, independent_final_loaded=False))
        progress(phase='complete')
        print('CONTENT_COMPLETE', a.job, 'CASES=24 NEW_UPDATES=0', flush=True)
    except PausedForUser as exc:
        mark_pause(base, a.job, a.gpu, 0, exc)
        print('CONTENT_PAUSED_GPU_RELEASED_ON_EXIT', str(exc), flush=True)
        return 75
    finally:
        lock.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
