"""Raw-count recomputation, paired sample audit and fixed v2 decisions."""
import argparse
import itertools
import json
from pathlib import Path
from post_t_paired_v2_common import *
from summarize_post_s1_support import verify_summary, compare, score
from post_t_paired_v2_evaluation import content_screen


def audit_streams(base, names):
    streams = {}
    for n in names:
        rows = [json.loads(line) for line in (base / 'jobs' / n / 'batch_hashes.jsonl').read_text().splitlines()]
        if len(rows) != card(n)['steps'] or [r['step'] for r in rows] != list(range(1, card(n)['steps'] + 1)):
            raise RuntimeError('training stream age differs')
        streams[n] = rows
    comparisons = {}
    for a, b in itertools.combinations(names, 2):
        k = min(len(streams[a]), len(streams[b]))
        if streams[a][:k] != streams[b][:k]:
            raise RuntimeError('actual paired input tensors differ: ' + a + '/' + b)
        comparisons[a + '/' + b] = dict(common_steps=k, exact=True)
    return comparisons


def scientific_screen(p, u, ordinary, stress, refs):
    candidate = u['R16']
    main = {n: compare(candidate, u[n], 'rgb_U', .3, True) for n in ('F16', 'H16')}
    main['R0'] = compare(candidate, refs['R0_U'], 'rgb_U', -.2)
    protection = {k: compare(ordinary['R16'], refs['base_ordinary'], k, -.1) for k in ('clean', 'rgb_missing', 'dsm_missing')}
    protection['dsm_U'] = compare(candidate, refs['base_U'], 'dsm_U', -.1)
    worst = min((dict(condition=k, tile=t, gain_pp=score(ordinary['R16'], k, t) - score(refs['base_ordinary'], k, t))
                 for k in p['evaluation']['primary'] for t in p['data']['validation']), key=lambda x: x['gain_pp'])
    ebase = {k: compare(stress['R16'], refs['E_S1-0'], k, -.1) for k in E_KEYS}
    eroute = {k: compare(stress['R16'], refs['E_R0'], k, -.2) for k in E_KEYS}
    eworst = min((dict(condition=k, tile=t, gain_pp=score(stress['R16'], k, t) - score(refs['E_S1-0'], k, t))
                  for k in E_KEYS for t in p['data']['validation']), key=lambda x: x['gain_pp'])
    budget = {m: compare(u[m + '16'], u[m + '8'], 'rgb_U', .3, True) for m in 'FHR'}
    contrasts = {str(b): {a + '-' + c: compare(u[a + str(b)], u[c + str(b)], 'rgb_U', .3, True)
                          for a, c in (('H', 'F'), ('R', 'H'), ('R', 'F'))} for b in (8, 16)}
    did = dict(pooled_gain_pp=budget['R']['pooled_gain_pp'] - budget['F']['pooled_gain_pp'],
               tile_gains_pp={t: budget['R']['tile_gains_pp'][t] - budget['F']['tile_gains_pp'][t] for t in p['data']['validation']})
    passed = all(x['passed'] for group in (main, protection, ebase, eroute) for x in group.values()) and worst['gain_pp'] >= -.2 and eworst['gain_pp'] >= -.2
    return dict(R16_passed=passed, main=main, protection=protection, worst_primary_tile=worst,
                E=dict(base=ebase, R0=eroute, worst_tile=eworst), same_budget=contrasts,
                budget=budget, budget_signal=budget['F']['passed'] and budget['R']['passed'],
                budget_method_difference_in_differences=did,
                interpretation='Val2 seed42 development only; unfreezing and capacity coupled; budget and schedule coupled')


def summarize(base):
    p = validate(read(base / 'plan.json'))
    verify_snapshot(base)
    for n in ORDER:
        accept_worker(base, n, p)
    paired = audit_streams(base, TRAIN_ORDER)
    summaries = {}
    trajectories = {}
    for n in TRAIN_ORDER:
        out = base / 'jobs' / n
        summaries[n] = {tag: verify_summary(out / ('endpoint_' + tag) / 'summary.json') for tag in ('ordinary', 'U', 'E')}
        initial = verify_summary(out / 'initial_U/summary.json')
        def point(summary):
            return {key: dict(pooled=score(summary, key), tiles={t: score(summary, key, t) for t in p['data']['validation']})
                    for key in ('rgb_U', 'dsm_U')}
        trajectories[n] = {'0': point(initial)}
        for step in range(4000, card(n)['steps'] + 1, 4000):
            summary = verify_summary(out / 'validation' / ('step_%05d' % step) / 'U/summary.json')
            trajectories[n][str(step)] = point(summary)
        for path in out.glob('secondary_*/summary.json'):
            verify_summary(path)
    refs = {}
    for name, ix in read(base / 'reference_index.json').items():
        if name in ('base_ordinary', 'base_U', 'R0_U', 'E_S1-0', 'E_R0'):
            if sha(ix['path']) != ix['sha256']:
                raise RuntimeError('reference changed')
            refs[name] = verify_summary(ix['path'])
    result = scientific_screen(p, {n: s['U'] for n, s in summaries.items()},
                               {n: s['ordinary'] for n, s in summaries.items()},
                               {n: s['E'] for n, s in summaries.items()}, refs)
    contents = {}
    for phase in ('CONTENT_PRE', 'CONTENT_POST'):
        out = base / 'jobs' / phase
        rows = {n: {mode: verify_summary(out / n / mode / 'summary.json') for mode in ('C', 'Z', 'S')} for n in card(phase)['models']}
        computed = content_screen(rows)
        if computed != read(out / 'content_screen.json'):
            raise RuntimeError('content contrast changed')
        contents[phase] = computed
    post = contents['CONTENT_POST']['contrasts']
    content_did = {a: {k: dict(pooled_gain_pp=post['R16'][a][k]['pooled_gain_pp'] - post['F16'][a][k]['pooled_gain_pp'],
                    tile_gains_pp={t: post['R16'][a][k]['tile_gains_pp'][t] - post['F16'][a][k]['tile_gains_pp'][t] for t in p['data']['validation']})
                   for k in CONTENT_KEYS} for a in ('Z', 'S')}
    result.update(optimizer_updates=72000, diagnostic_cases=48, input_pairs=paired, trajectories=trajectories,
                  contents=contents, content_difference_in_differences=content_did,
                  capacities={n: read(base / 'jobs' / n / 'model_capacity.json') for n in TRAIN_ORDER},
                  selections={n: read(base / 'jobs' / n / 'selection.json') for n in TRAIN_ORDER},
                  plan_sha256=sha(base / 'plan.json'), code_manifest_sha256=sha(base / 'code_manifest.json'),
                  observed_at=now(), no_automatic_followup=True, test6_loaded=False, independent_final_loaded=False)
    write(base / 'paired_screen.json', result)
    print('PAIRED_SCREEN', result['R16_passed'], 'NO_FURTHER_DISPATCH', flush=True)
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--directory', type=Path, required=True)
    summarize(ap.parse_args().directory.resolve())
