"""One native Val2 path for checkpoints, content interventions and protection."""
from pathlib import Path
import time
import numpy as np
import torch
import d23_engine as engine
from post_t_paired_v2_common import read, write, sha, within, E_KEYS
from post_s1_support_evaluation import view_for, write_case, finish_summary, simple_route, transition
from post_d30_data import treatment
from post_d30_evaluation import infer
from summarize_post_t_mechanism import scores, compare, signal


def ordinary_keys(p):
    e = p['evaluation']
    return e['primary'] + e['missing'] + sum(e['local'].values(), []) + e['diagnostic']


class ReferenceStore:
    def __init__(self, base, p):
        self.base, self.p = Path(base), p
        self.index = read(self.base / 'reference_index.json')
        self.cache = {}

    def name(self, key, which):
        if key in E_KEYS:
            return 'E_S1-0' if which == 'base' else 'E_R0'
        return ('base_' if which == 'base' else 'R0_') + ('U' if key in ('rgb_U', 'dsm_U') else 'ordinary')

    def summary(self, name):
        if name not in self.cache:
            row = self.index[name]
            if sha(row['path']) != row['sha256']:
                raise RuntimeError('reference summary changed')
            self.cache[name] = read(row['path'])
        return self.cache[name]

    def get(self, key, tile, which):
        name = self.name(key, which)
        ix = self.index[name]
        row = self.summary(name)['tiles'][key][tile]
        folder = within(Path(ix['source_path']).parent, '/home/jovyan/zzx')
        preds = {}
        for n in ('candidate', 'fixed_rgb', 'fixed_dsm'):
            path = folder / key / n / (tile + '.npy')
            if sha(path) != row['predictions'][n]:
                raise RuntimeError('reference prediction changed: ' + str(path))
            preds[n] = np.load(path, allow_pickle=False)
        return preds, dict(summary_path=ix['path'], summary_sha256=ix['sha256'],
                           source_path=ix['source_path'], predictions=row['predictions'])


def view(base, item, tile, key):
    if key in E_KEYS or key in ('rgb_U', 'dsm_U'):
        return view_for(base, item, tile, key)
    op = torch.from_numpy(item['optical'].transpose(2, 0, 1).copy())[None]
    ds = torch.from_numpy(item['dsm'])[None]
    op, ds, rm, dm = treatment(op, ds, key, engine.key(42, 'D26_eval', tile))
    return dict(optical=op[0].permute(1, 2, 0).numpy(), dsm=ds[0].numpy()), rm[0].numpy(), dm[0].numpy(), None


def evaluate(model, loader, refs, p, out, binding, progress, base, keys, tag,
             expected=None, check_raw_outside=True, endpoint_checks=None):
    """Always write raw counts and transitions; known-mask route never reads labels."""
    folder = Path(out) / tag
    tiles = {}
    for tile in p['data']['validation']:
        item = loader(tile, True)
        for key in keys:
            record = folder / key / (tile + '.json')
            if record.exists():
                row = read(record)
                if row['binding'] != binding:
                    raise RuntimeError('partial evaluation binding differs')
                for n, digest in row['predictions'].items():
                    if sha(folder / key / n / (tile + '.npy')) != digest:
                        raise RuntimeError('partial prediction changed')
                if expected is not None:
                    original = expected['tiles'][key][tile]
                    if row['predictions']['candidate'] != original['predictions']['candidate']:
                        raise RuntimeError('reused endpoint differs')
                    for scope in ('full', 'noboundary'):
                        for region in ('valid', 'mask_location', 'other_locations'):
                            if row['scopes'][scope]['metrics']['candidate'][region]['cm'] != original['scopes'][scope]['metrics']['candidate'][region]['cm']:
                                raise RuntimeError('reused endpoint raw counts differ')
                    if endpoint_checks is not None:
                        endpoint_checks.append(dict(tile=tile, condition=key, exact=True,
                                                    prediction_sha256=row['predictions']['candidate']))
                tiles.setdefault(key, {})[tile] = row
                progress(phase=tag, tile=tile, condition=key, reused_complete_case=True)
                continue
            v, rm, dm, mb = view(base, item, tile, key)
            report = lambda **kw: progress(phase=tag, tile=tile, condition=key, **kw)
            report()
            tick = time.monotonic()
            predictions, _ = infer(model, v, rm, dm, report)
            elapsed = time.monotonic() - tick
            control, rb = refs.get(key, tile, 'base')
            route, rr = refs.get(key, tile, 'R0')
            candidate, use = simple_route(control['candidate'], predictions['candidate'], rm, dm)
            if check_raw_outside and not np.array_equal(predictions['candidate'][~use], control['candidate'][~use]):
                raise RuntimeError('native raw prediction changed outside allowed support')
            values = dict(control, candidate=candidate)
            row = write_case(folder, key, tile, item, rm, dm, values, binding, mb, rb)
            row['route_protection'] = dict(outside_equal=True, support_pixels=int(use.sum()),
                                           raw_outside_checked=check_raw_outside)
            row['cost'] = dict(native_inference_seconds=elapsed, peak_allocated_bytes=torch.cuda.max_memory_allocated() if torch.cuda.is_available() else None,
                               baseline_predictions_reused=True, inference_batch=8)
            row['transition_vs_base'] = {scope: transition(item[scope + '_gt'], control['candidate'], candidate, use) for scope in ('full', 'noboundary')}
            row['transition_vs_R0'] = {scope: transition(item[scope + '_gt'], route['candidate'], candidate, use) for scope in ('full', 'noboundary')}
            row['R0_reference'] = rr
            if expected is not None:
                original = expected['tiles'][key][tile]
                if row['predictions']['candidate'] != original['predictions']['candidate']:
                    raise RuntimeError('unperturbed endpoint prediction SHA differs')
                for scope in ('full', 'noboundary'):
                    for region in ('valid', 'mask_location', 'other_locations'):
                        if row['scopes'][scope]['metrics']['candidate'][region]['cm'] != original['scopes'][scope]['metrics']['candidate'][region]['cm']:
                            raise RuntimeError('unperturbed endpoint raw counts differ')
                if endpoint_checks is not None:
                    endpoint_checks.append(dict(tile=tile, condition=key, exact=True,
                                                prediction_sha256=row['predictions']['candidate']))
            write(folder / key / (tile + '.json'), row)
            tiles.setdefault(key, {})[tile] = row
            print('PAIRED_EVAL', tag, tile, key, flush=True)
        del item
    return finish_summary(folder, tiles, binding)


def checkpoint_selection(u, protection, refs, step):
    us, ps = scores(u), scores(protection)
    base_u = scores(refs.summary('base_U'))
    base_p = scores(refs.summary('base_ordinary'))
    checks = {key: compare(ps, base_p)[key]['pooled_gain_pp'] >= -.1 for key in ('clean', 'rgb_missing', 'dsm_missing')}
    checks['dsm_U'] = compare(us, base_u)['dsm_U']['pooled_gain_pp'] >= -.1
    checks['worst_protected_tile'] = all(v >= -.2 for key in ('clean', 'rgb_missing', 'dsm_missing') for v in compare(ps, base_p)[key]['tile_gains_pp'].values())
    return dict(step=step, score=us['rgb_U']['pooled'], eligible=all(checks.values()), protection_checks=checks,
                metric='Val2 NoBoundary pooled rgb_U mIoU_fg5 percent', secondary_only=True)


def content_screen(summaries):
    values = {m: {a: scores(s) for a, s in ss.items()} for m, ss in summaries.items()}
    contrasts = {m: {a: compare(ss['C'], ss[a]) for a in ('Z', 'S')} for m, ss in values.items()}
    signals = {m: all(signal(row) for intervention in rs.values() for row in intervention.values()) for m, rs in contrasts.items()}
    return dict(scores=values, contrasts=contrasts, planning_signals=signals,
                interpretation='fixed-model content sensitivity; not a matched RGB-only training result',
                optimizer_updates=0)
