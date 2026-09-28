"""Offline integer-count audit, paired contrasts, and compact archival; no test data."""
import csv
import math
import shutil
import d21_common as p


def metric(cm):
    if len(cm) != 6 or any(len(row) != 6 for row in cm):
        raise ValueError('expected 6x6 confusion matrix')
    if any(type(v) is not int or v < 0 for row in cm for v in row):
        raise ValueError('counts must be nonnegative integers')
    scores = []
    for c in range(5):
        union = sum(cm[c]) + sum(row[c] for row in cm) - cm[c][c]
        if union:
            scores.append(cm[c][c]/union)
    return sum(scores)/len(scores) if scores else None


def audit(summary):
    if summary['smoke'] or summary['test6_loaded'] or summary['independent_final_loaded']:
        raise ValueError('unexpected evidence scope')
    cfg = p.config()
    if set(summary['conditions']) != set(cfg['evaluation_conditions']):
        raise ValueError('missing evaluation conditions')
    expected = {str(tile) for tile in p.datasets()[summary['job']['dataset']]['dev']}
    for condition in summary['conditions'].values():
        if set(condition['tiles']) != expected:
            raise ValueError('development tiles changed')
        for scope, pooled in condition['pooled'].items():
            matrices = [tile['scopes'][scope] for tile in condition['tiles'].values()]
            total = [[sum(row['cm'][i][j] for row in matrices) for j in range(6)] for i in range(6)]
            if total != pooled['cm']:
                raise ValueError('pooled matrix does not match per-tile counts')
            for row in matrices + [pooled]:
                score = metric(row['cm'])
                saved = row['metrics']['mIoU_fg5']
                if score is None or saved is None or not math.isclose(score,saved,rel_tol=0,abs_tol=1e-12):
                    raise ValueError('metric recomputation failed')
                if sum(map(sum,row['cm'])) != row['metrics']['valid_pixels']:
                    raise ValueError('valid pixel mismatch')
                if [sum(line) for line in row['cm']] != row['metrics']['class_true_count']:
                    raise ValueError('per-class count mismatch')


def scores(summary, scope, tile=None):
    cfg = p.config()
    def score(condition):
        row = summary['conditions'][condition]
        row = row['pooled'][scope] if tile is None else row['tiles'][str(tile)]['scopes'][scope]
        return 100*metric(row['cm'])
    result = {family:sum(score(c) for c in members)/len(members)
              for family,members in cfg['score_families'].items()}
    result['macro'] = sum(result.values())/len(result)
    result['aux_zero'] = score('aux_zero')
    return result


def decision(arms, dataset):
    cfg = p.config()
    scope = cfg['primary_scope'][dataset]
    all_scores = {arm:scores(summary,scope) for arm,summary in arms.items()}
    candidate = all_scores['F2']
    strongest = max(all_scores[a]['macro'] for a in cfg['candidate_controls'])
    protections = ['R0','R1','M0']
    gate = cfg['gate_pp']
    failures = []
    if candidate['macro']-strongest < gate['macro_gain_min']:
        failures.append('macro gain below +0.2 pp over strongest control')
    for arm in protections:
        for family in cfg['score_families']:
            limit = gate['clean_loss_max'] if family == 'clean' else gate['family_loss_max']
            if candidate[family]-all_scores[arm][family] < -limit:
                failures.append(f'pooled {family} below {arm} protection')
    tile_contrasts = {}
    for tile in p.datasets()[dataset]['dev']:
        current = scores(arms['F2'],scope,tile)
        tile_contrasts[str(tile)] = {}
        for arm in protections:
            reference = scores(arms[arm],scope,tile)
            delta = {k:current[k]-reference[k] for k in current}
            tile_contrasts[str(tile)][arm] = delta
            for family in cfg['score_families']:
                limit = gate['tile_clean_loss_max'] if family == 'clean' else gate['tile_family_loss_max']
                if delta[family] < -limit:
                    failures.append(f'tile {tile} {family} below {arm} protection')
    return dict(scope=scope, scores=all_scores, candidate_macro_gain_pp=candidate['macro']-strongest,
        candidate_minus_controls={a:{k:candidate[k]-all_scores[a][k] for k in candidate}
                                  for a in cfg['candidate_controls']},
        tile_contrasts=tile_contrasts, development_accuracy_gate_passed=not failures, failures=failures,
        missing_aux_safety_passed=candidate['aux_zero']-all_scores['R0']['aux_zero'] >= -cfg['aux_zero_loss_vs_R0_max_pp'],
        no_learned_robustness_claim=True)


def main():
    cfg = p.config()
    p.COMPACT.mkdir(parents=True,exist_ok=True)
    summaries, rows, missing = {}, [], []
    for job in p.jobs():
        name, path = p.key(job), p.eval_dir(job)/'summary.json'
        if not path.is_file():
            missing.append(name)
            continue
        summary = p.read(path)
        if summary['job'] != job:
            raise RuntimeError('job identity mismatch')
        train = p.read(p.run_dir(job)/'summary.json')
        if train['global_step'] != cfg['steps'] or train['signature'] != summary['signature']['training'] or train['checkpoint_sha256'] != summary['signature']['checkpoint_sha256']:
            raise RuntimeError('training/evaluation binding mismatch')
        audit(summary)
        summaries[name] = summary
        shutil.copy2(path,p.COMPACT/f'{name}_summary.json')
        p.write(p.COMPACT/f'{name}_training.json',train)
        for scope in summary['conditions']['clean']['pooled']:
            rows.append(dict(**job,scope=scope,**scores(summary,scope),
                             trainable_parameters=summary['trainable_parameters']))
    decisions = {}
    for dataset in cfg['datasets']:
        for seed in cfg['seeds']:
            arms = {a:summaries.get(p.key(dict(dataset=dataset,arm=a,seed=seed))) for a in cfg['arms']}
            if all(arms.values()):
                bindings = [row['signature']['training'] for row in arms.values()]
                for field in ('source_sha256','input_manifest_sha256','dino_sha256','torch_version'):
                    if any(row[field] != bindings[0][field] for row in bindings):
                        raise RuntimeError('unmatched experiment bindings: '+field)
                decisions[f'{dataset}_seed{seed}'] = decision(arms,dataset)
    p.write(p.COMPACT/'decision.json',dict(completed=len(summaries),planned=32,missing=missing,
        integer_count_audit='PASS', decisions=decisions,
        all_development_accuracy_gates_passed=(len(decisions)==4 and all(d['development_accuracy_gate_passed'] for d in decisions.values())),
        all_missing_aux_safety_gates_passed=(len(decisions)==4 and all(d['missing_aux_safety_passed'] for d in decisions.values())),
        evidence_level=cfg['evidence_level'], independent_confirmation=False, test6_loaded=False))
    with (p.COMPACT/'metrics.csv').open('w',encoding='utf-8',newline='') as file:
        fields=['dataset','arm','seed','scope','clean','optical_quality','auxiliary_quality','macro','aux_zero','trainable_parameters']
        writer=csv.DictWriter(file,fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    for name in ('plan.json','preflight.json','input_manifest.json'):
        if (p.OUT/name).is_file():
            shutil.copy2(p.OUT/name,p.COMPACT/name)
    print(f'D21 ARCHIVED {len(summaries)}/32; integer audit PASS; missing jobs retained',flush=True)


if __name__ == '__main__':
    main()
