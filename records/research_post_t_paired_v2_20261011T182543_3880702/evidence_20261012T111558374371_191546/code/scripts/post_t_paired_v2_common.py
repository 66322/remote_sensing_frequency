"""Frozen six-arm design, source receipts, two GPU slots and no failed-recipe retries."""
import copy
from pathlib import Path
from post_s1_support_common import read, write, sha, now, within, verify_snapshot, hours, SHAS, E_KEYS

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'research_post_t_paired_v2_'
PREDECESSOR = 'research_post_t_mechanism_20261011T094823_3625851'
PREDECESSOR_COMMIT = 'cd958925cb5d4292dd15802830e97493c9c67033'
SOURCE_PLAN_SHA = '0b22ceb9836e14a13c1407bbe280b4a2a3745ec13e5a79c1273f5875e5d73d1c'
SOURCE_CODE_SHA = 'e5e0a5c66d0604b5d6dceb9bb974ba2e3daa00b2e1fd5d016178e08a8419087b'
TRAIN_ORDER = ['H8', 'F8', 'R8', 'R16', 'H16', 'F16']
ORDER = ['CONTENT_PRE'] + TRAIN_ORDER + ['CONTENT_POST']
CONTENT_KEYS = ['rgb_lines64w8__clean', 'rgb_blocks64q25__clean']
INHERITED = ('data', 'experts', 'input_manifest_sha256', 'expected_configs', 'augmentation',
             'evaluation', 'fixed_conditions', 'initial_checkpoint', 'reference_shas',
             'source_directory', 'source_execution_commit', 'donors')


def source_plan():
    path = ROOT / 'configs/post_t_paired_v2/source_mechanism_plan.json'
    if sha(path) != SOURCE_PLAN_SHA:
        raise RuntimeError('frozen scientific source changed')
    return read(path)


def card(name):
    if name in TRAIN_ORDER:
        budget = 16000 if name.endswith('16') else 8000
        return dict(id=name, kind='train', mechanism=name[0], gpu='available_0_or_1', steps=budget,
                    seed=42, donor='S1-0', frozen_base=True, support_preserved=True,
                    local_only=True, geometry_aug=False, control='none',
                    timeout_hours=24. if budget == 16000 else 12.)
    if name in ('CONTENT_PRE', 'CONTENT_POST'):
        return dict(id=name, kind='content', gpu='available_0_or_1', steps=0, seed=42,
                    models=['M000_context', 'M300_context'] if name == 'CONTENT_PRE' else ['F16', 'R16'],
                    interventions=['C', 'Z', 'S'], keys=CONTENT_KEYS, cases=24, timeout_hours=4.)
    raise ValueError('reserved or unknown job')


def make_plan(root, base, commit, parent):
    if parent != source_plan():
        raise ValueError('source mechanism plan differs from audited bytes')
    p = {k: copy.deepcopy(parent[k]) for k in INHERITED}
    training = copy.deepcopy(parent['training'])
    training.update(steps=None, steps_by_job={n: card(n)['steps'] for n in TRAIN_ORDER},
                    validation_steps=[4000, 8000, 12000, 16000], primary_checkpoint_step='job.steps',
                    selection='secondary protected Val2 rgb_U maximum; tie earlier; fixed endpoint primary')
    p.update(id='POST_T_PAIRED_V2', execution_commit=commit, created_at=now(),
             jobs=[card(n) for n in ORDER], training=training, primary_candidate='R16',
             physical_gpus=[0, 1], max_gpu_workers=2, automatic_retry=False, new_seeds=False,
             test_release=False, total_optimizer_steps=72000, extra_content_cases=48,
             predecessor_directory=str(root / 'records' / PREDECESSOR),
             predecessor_execution_commit=PREDECESSOR_COMMIT,
             predecessor_plan_sha256=SOURCE_PLAN_SHA, predecessor_code_manifest_sha256=SOURCE_CODE_SHA,
             design=dict(E_keys=E_KEYS, matched_pp=.3, route_floor_pp=-.2, protect_floor_pp=-.1,
                         worst_tile_floor_pp=-.2, content_signal_pp=.3, reserved_not_automatic=['X8', 'X16'],
                         estimand='adaptation location and capacity jointly; budget and schedule jointly',
                         output_support='known local RGB missing and observed DSM and observable window'),
             runtime=dict(cpu_stage_timeout_hours=4., wait_poll_seconds=10,
                          wall_deadline_hours=None, cooperative_gpu_release=True,
                          resume_paused_only=True, cross_device_resume=True,
                          resource_authorization='user 2026-10-11: GPU0+GPU1, no one-day cutoff, release either card on request'))
    return p


def validate(p):
    expected = make_plan(Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro'),
                         Path('unused'), p['execution_commit'], source_plan())
    for key in expected:
        if key in ('created_at', 'predecessor_directory'):
            continue
        if p.get(key) != expected[key]:
            raise ValueError('frozen plan changed: ' + key)
    if set(p) != set(expected) or Path(p['predecessor_directory']).name != PREDECESSOR:
        raise ValueError('plan schema/predecessor changed')
    return p


def resolved_job(p, job):
    cfg = {k: copy.deepcopy(p[k]) for k in INHERITED}
    cfg.update(job=job, training=copy.deepcopy(p['training']), design=copy.deepcopy(p['design']))
    cfg['training']['steps'] = job['steps']
    cfg['training']['validation_steps'] = list(range(4000, job['steps'] + 1, 4000))
    cfg['training']['primary_checkpoint_step'] = job['steps']
    return cfg


def dirs(root, base):
    root = within(root, '/home/jovyan/zzx')
    base = within(base, root / 'records')
    if not base.name.startswith(PREFIX):
        raise ValueError('unexpected output directory')
    return root, base


def predecessor_verdict(state, controller_live, workers_live, released):
    from post_t_mechanism_common import ORDER as previous_order
    if state.get('status') == 'MECHANISM_COMPLETE_AWAITING_REVIEW':
        if state.get('CPU') != 'COMPLETE' or set(state.get('jobs', {})) != set(previous_order) or any(x.get('status') != 'COMPLETE' for x in state['jobs'].values()):
            return 'HOLD_INVALID_COMPLETE'
        return 'READY' if not controller_live and not workers_live and released else 'WAITING_PREDECESSOR_RELEASE'
    return 'HOLD_PREDECESSOR_NOT_COMPLETE'


def inspect_predecessor(root, p, accept=False):
    from d30_common import live_owned, lock_free
    pred = within(p['predecessor_directory'], root / 'records')
    if sha(pred / 'plan.json') != SOURCE_PLAN_SHA or sha(pred / 'code_manifest.json') != SOURCE_CODE_SHA:
        raise RuntimeError('audited predecessor binding changed')
    s = read(pred / 'queue_status.json')
    a = live_owned(s.get('controller_pid', -1), pred)
    w = any(live_owned(r.get('pid', -1), pred) for r in s['jobs'].values())
    released = (pred / 'controller.lock').exists() and lock_free(pred)
    verdict = predecessor_verdict(s, a, w, released)
    result = dict(verdict=verdict, status=s['status'], last_observed=s['observed_at'],
                  controller_live=a, workers_live=w, checked_at=now())
    if accept:
        if verdict != 'READY':
            raise RuntimeError('predecessor not released: ' + verdict)
        # Reuse prior audit; check receipt bindings, not the whole historical analysis.
        receipt = read(ROOT / 'configs/post_t_paired_v2/source_receipt.json')
        for name, digest in receipt['files'].items():
            if sha(within(pred / name, pred)) != digest:
                raise RuntimeError('received source changed: ' + name)
        result.update(receipt_files=len(receipt['files']), scientific_gate_required=False)
    return result


def initial_state(p):
    return dict(status='REGISTERED', observed_at=now(), CPU='PENDING',
                jobs={n: dict(status='PENDING', gpu=None) for n in ORDER})


def signature(base, p, job):
    return dict(execution_commit=p['execution_commit'], plan_sha256=sha(base / 'plan.json'),
                code_manifest_sha256=sha(base / 'code_manifest.json'),
                mask_manifest_sha256=sha(base / 'mask_manifest.json'),
                initial_checkpoint_sha256=SHAS['S1-0'], job=job, allowed_physical_gpus=[0, 1],
                primary_checkpoint_step=job['steps'], test6_loaded=False, independent_final_loaded=False)


def accept_worker(base, name, p):
    out = base / 'jobs' / name
    c = read(out / 'complete.json')
    job = card(name)
    if c['signature'] != signature(base, p, job) or c['optimizer_updates'] != job['steps']:
        raise RuntimeError('worker binding/budget changed')
    if c['test6_loaded'] or c['independent_final_loaded']:
        raise RuntimeError('forbidden evaluation')
    if job['kind'] == 'train':
        required = {'selected.pth', 'endpoint.pth', 'last_train_state.pth', 'model_capacity.json',
                    'protection.json', 'input_binding.json', 'batch_hashes.jsonl', 'data_stream.json',
                    'endpoint_ordinary/summary.json', 'endpoint_U/summary.json', 'endpoint_E/summary.json',
                    'initial_U/summary.json', 'selection.json', 'gradient_contract.json'}
        if c['global_step'] != job['steps'] or not c['frozen_state_equal'] or not c['gradient_contract_passed']:
            raise RuntimeError('training contract not complete')
    else:
        required = {'content_screen.json', 'endpoint_checks.json', 'input_binding.json'}
        if c['cases'] != 24 or len(read(out / 'endpoint_checks.json')) != 8:
            raise RuntimeError('content cases/endpoint checks incomplete')
    if not required.issubset(c['artifacts']):
        raise RuntimeError('required evidence absent')
    for n, digest in c['artifacts'].items():
        if sha(within(out / n, out)) != digest:
            raise RuntimeError('artifact changed: ' + name + '/' + n)
    return c
