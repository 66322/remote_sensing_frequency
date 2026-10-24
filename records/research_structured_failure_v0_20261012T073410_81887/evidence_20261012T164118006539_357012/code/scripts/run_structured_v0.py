"""Four fixed output systems, native inference only, cooperative GPU release."""
import argparse
import os
from pathlib import Path
import sys
import time
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
os.environ.setdefault('XFORMERS_DISABLED', '1')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from structured_v0_common import *
from structured_v0_masks import supports, canonical, availability_diagnostics
from structured_v0_metrics import evidence


def save_array(path, array):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    with tmp.open('wb') as f:
        np.savez_compressed(f, prediction=array)
    os.replace(tmp, path)
    return sha(path)


def prediction(record):
    row = read(record)
    f = record.parent / row['prediction_file']
    if sha(f) != row['prediction_sha256']:
        raise RuntimeError('cached prediction changed')
    with np.load(f, allow_pickle=False) as z:
        return z['prediction']


def load_mask(base, tile, i, family):
    r = read(base/'mask_manifest.json')['tiles'][tile][str(i)][family]
    path = Path(r['path'])
    path.resolve().relative_to(base.resolve())
    if sha(path) != r['file_sha256']:
        raise RuntimeError('mask file changed')
    with np.load(path, allow_pickle=False) as z:
        shape = tuple(z['shape'])
        m = np.unpackbits(z['bits'], bitorder='little', count=int(np.prod(shape))).reshape(shape).astype(bool)
    if canonical(m) != r['canonical_sha256'] or int(m.sum()) != 9000000:
        raise RuntimeError('decoded mask differs')
    return m, r


def make_models(root, source):
    from run_post_s1_transfer import load_anchors, seed_all
    from model.rebuild_v1_d26 import build_experts
    from model.rebuild_v1_post_ab_n1 import N1Segmenter
    from model.post_s1_transfer_model import checkpoint
    from model.post_n5_cross_paths import CrossPaths
    from post_d30_evaluation import FixedPair
    seed_all()
    states, provenance = load_anchors(root, source)
    anchor = FixedPair(*build_experts(root, states)).eval().requires_grad_(False).cuda()
    base = N1Segmenter(*build_experts(root, states), dict(id='N1-2', information_entry='late', adaptation='last4_and_heads'))
    base.load_state_dict(checkpoint(source['donors']['S1-0']['path'], source['donors']['S1-0']['sha256']), strict=True)
    wrapper = CrossPaths(base, 'A1B1C0').eval().requires_grad_(False).cuda()
    return anchor, base, wrapper, provenance


def run(base, job, gpu, resume):
    p = validate(base)
    verify_code(base)
    if job not in JOBS or gpu not in (0, 1) or os.environ.get('CUDA_VISIBLE_DEVICES') != str(gpu):
        raise RuntimeError('job/GPU binding differs')
    if torch.__version__ != '2.2.2+cu121':
        raise RuntimeError('bound Torch required')
    prep = read(base/'preparation_complete.json')
    if prep['plan_sha256'] != sha(base/'plan.json') or prep['mask_manifest_sha256'] != sha(base/'mask_manifest.json'):
        raise RuntimeError('preparation changed')
    out = base/'jobs'/job
    if resume and not (out/'paused.json').exists():
        raise RuntimeError('only explicit user pauses resume')
    out.mkdir(parents=True, exist_ok=resume)
    import fcntl
    lock = (out/'worker.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
    started = time.monotonic()
    def progress(**kw):
        poll(base, gpu)
        write(out/'progress.json', dict(job=job, physical_gpu=gpu, optimizer_updates=0,
              observed_at=now(), elapsed_seconds=time.monotonic()-started, **kw))
    try:
        progress(phase='loading')
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark = False
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        root = Path(p['root'])
        source = read(base/'source_plan.json')
        from post_n2_diag_runtime import input_contract
        from post_ab_n1_data import Loader
        from post_d30_evaluation import infer
        from post_s1_support_evaluation import simple_route, source_case, view_for
        input_contract(root, source)
        loader = Loader(root, source)
        tile = job.split('_', 1)[1] if job.startswith('clean_') else '_'.join(job.split('_')[2:])
        item = loader(tile, True)
        anchor, native, context, provenance = make_models(root, source)
        binding = dict(plan_sha256=sha(base/'plan.json'), code_sha256=sha(base/'code_manifest.json'),
                       mask_manifest_sha256=sha(base/'mask_manifest.json'), source_plan_sha256=sha(base/'source_plan.json'))
        records = {}
        def infer_one(system, view, rm, dm, family):
            report = lambda **kw: progress(phase='inference', system=system, family=family, tile=tile, **kw)
            report()
            if system == 'RGB':
                result, _ = infer(anchor, view, rm, dm, report, fixed_only=True)
                return result['rgb']
            if system == 'S1':
                model = native
            else:
                context.set_path('A1B1C0' if system == 'MASKED' else 'A1B0C0')
                model = context
            result, _ = infer(model, view, rm, dm, report)
            return result['candidate']
        if job.startswith('clean_'):
            full = np.ones(item['dsm'].shape, bool)
            expected, _, _ = source_case(root, 'S1-0', 'evaluation', 'clean', tile)
            predictions = {}
            for system in MODELS:
                f = out/(system+'.json')
                if f.exists():
                    if read(f)['binding'] != binding:
                        raise RuntimeError('clean binding differs')
                    pred = prediction(f)
                else:
                    pred = infer_one(system, item, full, full, 'clean')
                    ref = expected['fixed_rgb'] if system == 'RGB' else expected['candidate']
                    if not np.array_equal(pred, ref):
                        raise RuntimeError('clean old endpoint mismatch: '+system)
                    filename = system+'.npz'
                    digest = save_array(out/filename, pred)
                    write(f, dict(binding=binding, system=system, tile=tile, condition='clean',
                         prediction_file=filename, prediction_sha256=digest, old_endpoint_exact=True))
                predictions[system] = pred
                records[f.name] = sha(f)
            # Six total real endpoint checks across two clean jobs, not mask-bank results.
            checks = []
            if (out/'endpoint_checks.json').exists():
                check = read(out/'endpoint_checks.json')
                if check['binding'] != binding:
                    raise RuntimeError('endpoint binding differs')
                checks = check['checks']
            else:
                mechanism = Path(source['predecessor_directory'])
                view, rm, dm, _ = view_for(mechanism, item, tile, 'rgb_U')
                old_base, _, _ = source_case(root, 'S1-0', 'support_evaluation', 'rgb_U', tile)
                for system in ('S1', 'MASKED', 'CONTEXT'):
                    pred = infer_one(system, view, rm, dm, 'old_rgb_U_check')
                    if system == 'S1':
                        ref = old_base['candidate']
                    else:
                        pred, _ = simple_route(old_base['candidate'], pred, rm, dm)
                        name = 'M000_masked' if system == 'MASKED' else 'M000_context'
                        summary = read(mechanism/'jobs'/name/'summary.json')
                        f = mechanism/'jobs'/name/'rgb_U/candidate'/(tile+'.npy')
                        if sha(f) != summary['tiles']['rgb_U'][tile]['predictions']['candidate']:
                            raise RuntimeError('old endpoint evidence changed')
                        ref = np.load(f, allow_pickle=False)
                    if not np.array_equal(pred, ref):
                        raise RuntimeError('old U endpoint mismatch: '+system)
                    checks.append(dict(system=system, tile=tile, exact=True))
                write(out/'endpoint_checks.json', dict(binding=binding, checks=checks))
        else:
            realization = int(job.split('_')[1])
            cleans = {m: prediction(base/'jobs'/('clean_'+tile)/(m+'.json')) for m in MODELS}
            for family in FAMILIES:
                mask, mb = load_mask(base, tile, realization, family)
                rm, dm = ~mask, np.ones_like(mask)
                op = item['optical'].copy()
                op[mask] = 0
                view = dict(optical=op, dsm=item['dsm'])
                regions = supports(mask)
                support_stats = availability_diagnostics(mask)
                control = None
                for system in ('S1', 'RGB', 'MASKED', 'CONTEXT'):
                    poll(base, gpu)
                    f = out/(family+'_'+system+'.json')
                    if f.exists():
                        row = read(f)
                        if row['binding'] != binding or row['mask_sha256'] != mb['canonical_sha256']:
                            raise RuntimeError('completed case binding changed')
                        pred = prediction(f)
                    else:
                        tick = time.monotonic()
                        pred = infer_one(system, view, rm, dm, family)
                        seconds = time.monotonic()-tick
                        if system in ('MASKED', 'CONTEXT'):
                            pred, use = simple_route(control, pred, rm, dm)
                            if not np.array_equal(pred[~use], control[~use]):
                                raise RuntimeError('outside support changed')
                        reference = pred if system == 'S1' else control
                        counts = evidence(item, cleans[system], pred, reference, regions)
                        filename = family+'_'+system+'.npz'
                        digest = save_array(out/filename, pred)
                        row = dict(binding=binding, mask_sha256=mb['canonical_sha256'], tile=tile, realization=realization,
                            family=family, system=system, scopes=counts, prediction_file=filename, prediction_sha256=digest,
                            inference_seconds=seconds, gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                            support_pixels={n:int(v.sum()) for n,v in regions.items()}, physical_zero_before_expert_normalization=True,
                            availability_diagnostics=support_stats,
                            same_corrupted_input_base='S1', optimizer_updates=0, test6_loaded=False)
                        write(f, row)
                    if system == 'S1':
                        control = pred
                    records[f.name] = sha(f)
                del mask, rm, dm, op, view, regions, control, pred
        write(out/'input_binding.json', dict(files=loader.verified, experts=provenance, binding=binding))
        write(out/'complete.json', dict(job=job, **binding, records=records, optimizer_updates=0,
            endpoint_checks_sha256=sha(out/'endpoint_checks.json') if job.startswith('clean_') else None,
            input_binding_sha256=sha(out/'input_binding.json'), test6_loaded=False, independent_final_loaded=False, completed_at=now()))
        progress(phase='complete')
    except Released as exc:
        write(out/'paused.json', dict(reason=str(exc), job=job, physical_gpu=gpu, observed_at=now()))
        return 75
    finally:
        lock.close()
    return 0


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--directory', type=Path, required=True)
    a.add_argument('--job', required=True)
    a.add_argument('--gpu', type=int, choices=(0,1), required=True)
    a.add_argument('--resume', action='store_true')
    args = a.parse_args()
    sys.exit(run(args.directory.resolve(), args.job, args.gpu, args.resume))
