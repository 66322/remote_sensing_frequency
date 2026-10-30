#!/usr/bin/env python3
"""One-shot A-spatial successor of the existing, unmodified Full pipeline."""
import argparse
from contextlib import contextmanager, redirect_stdout, redirect_stderr
import datetime as dt
import gzip
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import traceback

ROOT = Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro')
FULL = ROOT / 'records/post_m2_multiroute_v2_20261030_r1'
CODE = ROOT / 'execution/post_m2_multiroute_v2_20261030_r1'
A0 = ROOT / 'records/post_m2_a0_ipcfix_20261030'
BASE = ROOT / 'records/post_m2_a_spatial_followup_20261030_r1'
SCIENCE = 'c22a046407daf42064cbb161429f2648c9b86d66'
PAYLOAD = 'd15f34e8d53f935aa17542123c2227fab14cb810'
KINDS = ('dino2', 'dino3')
STAGES = ('profile', 'train', 'calibration', 'outer')
POLL = 2
WAIT_SECONDS = 24 * 3600
STALL_SECONDS = 300


def now():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value, once=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n'
    if once:
        with path.open('x', encoding='utf-8') as f:
            f.write(body)
    else:
        temporary = path.with_name(path.name + '.tmp.' + str(os.getpid()))
        temporary.write_text(body, encoding='utf-8')
        os.replace(temporary, path)


def proc(pid):
    """Read identity, not just PID liveness; never signal predecessor processes."""
    try:
        folder = Path('/proc') / str(int(pid))
        stat = (folder / 'stat').read_text().rsplit(')', 1)[1].split()
        if stat[0] == 'Z':
            return None
        argv = [x.decode() for x in (folder / 'cmdline').read_bytes().split(b'\0') if x]
        return dict(pid=int(pid), start_ticks=stat[19], argv=argv)
    except (FileNotFoundError, ProcessLookupError):
        return None


def full_identity():
    pid = read(FULL / 'pipeline_started.json')['pid']
    item = proc(pid)
    if item and not (str(CODE / 'scripts/post_m2_multiroute.py') in item['argv'] and 'pipeline' in item['argv']):
        return None
    return item


def predecessor_failure():
    for pattern in ('*_first_failure*.json',):
        matches = sorted(FULL.glob(pattern))
        if matches:
            raise RuntimeError('Full engineering failure; no successor dispatch: ' + str(matches[0]))


def completion():
    predecessor_failure()
    path = FULL / 'train_complete.json'
    if not path.exists():
        return None
    value = read(path)
    if value.get('status') not in ('COMPLETE', 'COMPLETE_WITH_INVALID_ROUTES'):
        raise RuntimeError('unexpected Full completion status')
    if value.get('source') != read(CODE / 'SOURCE.json'):
        raise RuntimeError('Full completion/source mismatch')
    return value


def validate():
    expected_env = Path('/home/jovyan/miniconda3/envs/remote_sensing')
    if Path(sys.prefix).resolve() != expected_env.resolve() or sys.version_info[:3] != (3, 11, 13):
        raise RuntimeError('use existing remote_sensing/bin/python (Python3.11.13); no environment changes')
    if read(CODE / 'SOURCE.json')['commit'] != PAYLOAD:
        raise RuntimeError('expected the already installed d15 payload; do not install or replace it')
    if read(FULL / 'contract.json')['source'] != read(CODE / 'SOURCE.json'):
        raise RuntimeError('Full contract/source mismatch')
    ready = read(A0 / 'repair_ready.json')
    if ready['scientific_source_commit'] != SCIENCE:
        raise RuntimeError('A0 scientific source differs')
    read(A0 / 'repair_run_complete.json')
    for kind in KINDS:
        if read(A0 / kind / 'train_complete.json')['status'] != 'TRAINED_HEAD_ONLY':
            raise RuntimeError('original A0 pair is not complete')
        if read(A0 / ('profile_' + kind + '.json'))['code_commit'] != SCIENCE:
            raise RuntimeError('existing A0 model profile differs')
    d3 = read(A0 / 'dino3/train_started.json')['source']
    for field, name in (('repo', 'hubconf.py'), ('weight', None)):
        path = Path(d3[field]).resolve()
        path.relative_to(ROOT.resolve())
        if not (path / name if name else path).is_file():
            raise RuntimeError('accepted DINOv3 input missing: ' + str(path))
    if completion() is None and full_identity() is None:
        raise RuntimeError('Full has neither a live matching pipeline nor a normal completion receipt')
    reject_existing_spatial()
    return d3


def reject_existing_spatial():
    if list(FULL.glob('a_spatial_*_started.json')) or list(FULL.glob('a_spatial/*/*_started.json')):
        raise RuntimeError('spatial work already started through the old standalone entry; do not duplicate it')


def load_payload():
    sys.path.insert(0, str(CODE / 'scripts'))
    from post_m2_v2 import common as c
    root, source = c.source()  # Existing small-code manifest check; no data/weight hashing.
    if root.resolve() != CODE.resolve() or source['commit'] != PAYLOAD:
        raise RuntimeError('payload origin differs')
    return c


def environment(gpu=None):
    registered = read(BASE / 'registered.json')
    d3 = registered['dino3']
    env = dict(os.environ)
    if gpu is not None:
        if gpu not in (0, 1):
            raise ValueError('physical GPUs0/1 only')
        c = load_payload()
        env.update(c.env(gpu, BASE))
        Path(env['TMPDIR']).mkdir(parents=True, exist_ok=True)
        for rel in ('cache/torch', 'cache/cuda'):
            (BASE / rel).mkdir(parents=True, exist_ok=True)
    env.update(POST_M2_A0_RECORDS=str(A0),
               POST_M2_DINO3_REPO=d3['repo'], POST_M2_DINO3_WEIGHTS=d3['weight'],
               POST_M2_CODE_COMMIT=SCIENCE, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
               OPENBLAS_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', XFORMERS_DISABLED='1',
               PYTHONDONTWRITEBYTECODE='1', CONDA_DEFAULT_ENV='remote_sensing')
    return env


def status():
    out = dict(observed_at=now(),base=str(BASE),not_automatic_retry=True)
    for name in ('registered', 'dispatch', 'state', 'run_complete', 'first_failure', 'start_first_failure', 'github_upload_receipt', 'upload_pending'):
        path = BASE / (name + '.json')
        if path.exists():
            out[name] = read(path)
    dispatch = out.get('dispatch', {})
    item = proc(dispatch['pid']) if dispatch.get('pid') else None
    out['queue_process_identity_matches'] = bool(item and item['start_ticks'] == dispatch.get('start_ticks')
                                               and str(Path(__file__).resolve()) in item['argv'] and 'run' in item['argv'])
    for kind in KINDS:
        for name in ('progress', 'train_result'):
            path = BASE / 'a_spatial' / kind / (name + '.json')
            if path.exists():
                out[kind + '_' + name] = read(path)
    print(json.dumps(out, ensure_ascii=False, indent=2), flush=True)


def start(commit):
    BASE.mkdir(parents=True, exist_ok=True)
    if (BASE / 'registered.json').exists():
        status()
        return
    d3 = validate()
    # Exclusive registration is the duplicate guard, including failed/abandoned dispatches.
    try:
        write(BASE / 'registered.json', dict(status='REGISTERED_NOT_TRAINING_PROOF', observed_at=now(),
              followup_commit=commit, payload_commit=PAYLOAD, original_a0_source=SCIENCE,
              original_a0_run=str(A0), predecessor=str(FULL), predecessor_identity=full_identity(),
              dino3=d3, seed=42, formal_jobs=2, formal_updates_per_model=2000,
              maximum_disposable_profile_updates=8, loader_timeout_seconds=30,
              existing_checks_reused=True, automatic_retry=False), once=True)
    except FileExistsError:
        status()
        return
    try:
        with (BASE / 'followup.log').open('x', encoding='utf-8') as log:
            child = subprocess.Popen([sys.executable, '-u', '-B', str(Path(__file__).resolve()),
                                      'run', '--commit', commit], stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT,
                                     env=environment(), start_new_session=True)
    except BaseException:
        write(BASE / 'start_first_failure.json', dict(observed_at=now(),traceback=traceback.format_exc(),
              automatic_retry=False), once=True)
        raise
    item = proc(child.pid)
    receipt = dict(status='FOLLOWUP_DISPATCHED_NOT_TRAINING_PROOF', observed_at=now(), pid=child.pid,
                   start_ticks=item['start_ticks'] if item else None, log=str(BASE / 'followup.log'))
    write(BASE / 'dispatch.json', receipt, once=True)
    print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)


def wait_for_full():
    import fcntl
    identity = read(BASE / 'registered.json')['predecessor_identity']
    deadline = time.monotonic() + WAIT_SECONDS
    previous = None
    while time.monotonic() < deadline:
        result = completion()
        label = 'WAITING_FULL_NORMAL_COMPLETION'
        if result is not None:
            lock = (FULL / 'controller.lock').open('r+')
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                lock.close()
                label = 'WAITING_FULL_WORKERS_TO_RELEASE'
            else:
                try:
                    completion()
                    reject_existing_spatial()
                    load_payload().runtime_contract(FULL)  # Existing file size/mtime bindings only.
                    from post_m2_v2.controller import idle_gpus
                    snapshot = idle_gpus()  # Busy unrelated processes cause a stop, never a kill.
                    write(BASE / 'handoff.json', dict(observed_at=now(),full_status=result['status'],
                          blocked_full_routes=result.get('blocked', []), gpu=snapshot,
                          full_upload_not_a_dependency=True), once=True)
                    return lock
                except BaseException:
                    lock.close()
                    raise
        else:
            live = full_identity()
            if not live or not identity or live['start_ticks'] != identity['start_ticks']:
                raise RuntimeError('Full exited/replaced without its normal completion; no auto retry')
        if label != previous:
            print(label, flush=True)
            previous = label
        write(BASE / 'state.json', dict(status=label, observed_at=now(), cuda_loaded=False))
        time.sleep(POLL)
    raise TimeoutError('bounded successor wait expired; no training started by waiter')


def bounded_loader(original):
    def loader(*args, **kwargs):
        value = original(*args, **kwargs)
        if value.num_workers:
            value.timeout = 30
        return value
    return loader


def worker(kind):
    c = load_payload()
    short = c.ipc_tmpdir(BASE)
    Path(short).mkdir(parents=True, exist_ok=True)
    os.environ.update(TMPDIR=short, TEMP=short, TMP=short)
    tempfile.tempdir = short
    import post_m2_a0 as a0
    import torch
    if torch.__version__ != '2.7.1+cu126':
        raise RuntimeError('expected existing Torch2.7.1+cu126; do not change packages inside the queue')
    # New processes only. No mutation of the frozen files or running Full processes.
    a0.loader = bounded_loader(a0.loader)
    from post_m2_v2.spatial import execute
    encoder_loader, array_loader = a0.load_encoder, a0.arrays
    encoders, fit_cache = {}, {}
    current = [None]
    counts = dict(model_loads=0,fit_loads=0,fit_cache_peak_bytes=0)

    def reuse_encoder(contract, selected):
        if selected != kind:
            raise RuntimeError('resident encoder kind mismatch')
        if selected not in encoders:
            encoders[selected] = encoder_loader(contract, selected)
            counts['model_loads'] += 1
        return encoders[selected]

    def reuse_fit(contract, tiles, need_labels=True):
        if current[0] not in ('profile', 'train'):
            return array_loader(contract, tiles, need_labels)
        if list(tiles) != list(contract['folds']['train']) or not need_labels:
            raise RuntimeError('unexpected spatial fit cache request')
        if not fit_cache:
            fit_cache.update(array_loader(contract, tiles, need_labels))
            counts['fit_loads'] += 1
            counts['fit_cache_peak_bytes'] = sum(a.nbytes for row in fit_cache.values() for a in row.values())
            if counts['fit_cache_peak_bytes'] > c.CONFIG['max_resident_tile_bytes']:
                raise RuntimeError('bounded resident fit cache exceeded')
        return fit_cache

    a0.load_encoder, a0.arrays = reuse_encoder, reuse_fit
    for index, line in enumerate(sys.stdin):
        phase = json.loads(line)['phase']
        if index >= len(STAGES) or phase != STAGES[index]:
            raise RuntimeError('unexpected/repeated spatial phase')
        current[0] = phase
        try:
            with (BASE / ('a_spatial_' + phase + '_' + kind + '.log')).open('x',encoding='utf-8') as log:
                with redirect_stdout(log), redirect_stderr(log):
                    execute(BASE, kind, phase)
            if phase == 'train':
                fit_cache.clear()  # No fit arrays retained for calibration/outer.
            import gc
            gc.collect()
            write(BASE / ('resident_' + kind + '.json'),dict(observed_at=now(),phase=phase,
                  fit_cache_retained=bool(fit_cache),**counts))
            write(BASE / ('worker_done_' + phase + '_' + kind + '.json'),dict(observed_at=now()),once=True)
        except BaseException:
            write(BASE / ('worker_first_failure_' + phase + '_' + kind + '.json'),
                  dict(observed_at=now(), traceback=traceback.format_exc(), kind=kind, phase=phase), once=True)
            raise


@contextmanager
def resident_pair():
    from post_m2_v2.controller import idle_gpus, stop_owned
    idle_gpus()
    children, files = {}, []
    try:
        for gpu, kind in enumerate(KINDS):
            handle = (BASE / ('worker_gpu' + str(gpu) + '.log')).open('x', encoding='utf-8')
            files.append(handle)
            children[gpu] = subprocess.Popen([sys.executable, '-u', '-B', str(Path(__file__).resolve()),
                    'worker', '--kind', kind], stdin=subprocess.PIPE, text=True,
                    stdout=handle, stderr=subprocess.STDOUT, env=environment(gpu), start_new_session=True)
        yield children
    finally:
        stop_owned(children)
        write(BASE / 'workers_released.json',dict(observed_at=now(),
              workers={str(g):dict(pid=p.pid,returncode=p.returncode) for g,p in children.items()}))
        for handle in files:
            handle.close()


def stage(phase, children):
    write(BASE / ('a_spatial_' + phase + '_started.json'), dict(observed_at=now()), once=True)
    write(BASE / 'state.json',dict(status='RUNNING_A_SPATIAL',phase=phase,observed_at=now(),
          workers={str(g):p.pid for g,p in children.items()}))
    print('A_SPATIAL_STAGE_DISPATCHED',phase,{g:p.pid for g,p in children.items()},flush=True)
    for child in children.values():
        child.stdin.write(json.dumps(dict(phase=phase)) + '\n')
        child.stdin.flush()
    started = time.monotonic()
    last_activity = time.time()
    while True:
        if list(BASE.glob('worker_first_failure_*.json')) or any(p.poll() is not None for p in children.values()):
            raise RuntimeError('spatial worker failure; inspect original phase/kind log; no next phase')
        if all((BASE / ('worker_done_' + phase + '_' + k + '.json')).exists() for k in KINDS):
            break
        paths = list(BASE.glob('a_spatial/*/*.json')) + list(BASE.glob('a_spatial_' + phase + '_*.log'))
        last_activity = max([last_activity] + [p.stat().st_mtime for p in paths])
        if time.time() - last_activity > STALL_SECONDS:
            raise TimeoutError('spatial pair made no recorded progress for 300 seconds')
        if time.monotonic() - started > (720 if phase == 'profile' else 24 * 3600):
            raise TimeoutError('spatial phase hard timeout')
        time.sleep(.5)
    rows = [read(BASE / 'a_spatial' / k / (phase + '_result.json')) for k in KINDS]
    write(BASE / ('a_spatial_' + phase + '_complete.json'), dict(observed_at=now()), once=True)
    return rows


def execute_stages(children=None):
    profiles = stage('profile', children)
    if any(x['status'] != 'REAL_SPATIAL_PROFILE_PASSED' for x in profiles):
        raise RuntimeError('spatial profile not passed')
    write(BASE / 'measured_budget.json',dict(observed_at=now(),indicative_only=True,
          training_seconds_by_model={k:2000*p['selected']['median_seconds'] for k,p in zip(KINDS,profiles)},
          evaluation_seconds_per_profile_tile={k:p['evaluation']['seconds'] for k,p in zip(KINDS,profiles)},
          warning='four-update sanity check, not a precise completion-time forecast'))
    train = stage('train', children)
    if any(x['status'] not in ('TRAINED_SPATIAL_HEAD', 'INVALID_PROBE') for x in train):
        raise RuntimeError('unexpected spatial training status')
    if any(x['status'] != 'TRAINED_SPATIAL_HEAD' for x in train):
        return 'INVALID_PROBE_NO_AUTOMATIC_EXPANSION'
    stage('calibration', children)
    from post_m2_v2.spatial import run
    run(BASE, 'screen')  # Reuse the frozen inner-only gate, independent of linear/Full wins.
    if read(BASE / 'a_spatial/screen.json')['status'] != 'READY_SPATIAL_OUTER':
        return 'INVALID_PROBE_NO_AUTOMATIC_EXPANSION'
    stage('outer', children)
    return 'SPATIAL_PAIR_ALL_PHASES_COMPLETE'


def export():
    publication = BASE / 'publication'
    publication.mkdir(parents=True, exist_ok=True)
    train, partial, panels, endpoints = {}, {}, {}, []
    for kind in KINDS:
        folder = BASE / 'a_spatial' / kind
        if (folder / 'train_result.json').exists():
            train[kind] = read(folder / 'train_result.json')
        elif (folder / 'train_started.json').exists():
            progress = read(folder / 'progress.json') if (folder / 'progress.json').exists() else {}
            partial[kind] = dict(last_logged_successful_step=progress.get('step'),
                                  exact_updates_known=False,unlogged_updates_possible=True)
        for phase in ('calibration', 'outer'):
            if (folder / (phase + '_result.json')).exists():
                panels.setdefault(phase, {})[kind] = read(folder / (phase + '_result.json'))['pooled']
        for p in folder.glob('head_*.pt'):
            endpoints.append(dict(path=str(p), bytes=p.stat().st_size, uploaded=False))
    summary = dict(observed_at=now(),scope='A spatial readout, original F0 NB128; not Full512',
                   status=read(BASE / 'run_complete.json')['status'] if (BASE / 'run_complete.json').exists() else 'ENGINEERING_STOP_NO_RETRY',
                   seed=42, original_a0_run=str(A0), matched_spatial_parameters_each=19254,
                   completed_receipt_updates=sum(x['updates'] for x in train.values()),partial_jobs=partial,
                   exact_total_updates_known=not partial and len(train)==2,
                   panels=panels, endpoints=endpoints,
                   registration=read(BASE / 'registered.json'))
    write(publication / 'summary.json', summary)
    screen = BASE / 'a_spatial/screen.json'
    write(publication / 'gates.json', read(screen) if screen.exists() else dict(status='SCREEN_NOT_REACHED'))
    paths = sorted(set(BASE.glob('*.json')) | set(BASE.glob('a_spatial/**/*.json')) | set(BASE.glob('*.log')))
    index = []
    with gzip.open(publication / 'evidence.jsonl.gz', 'wt', encoding='utf-8') as archive:
        for path in paths:
            if path.stat().st_size > 25 * 1024**2:
                raise RuntimeError('unexpected oversized evidence: ' + str(path))
            rel = path.relative_to(BASE).as_posix()
            archive.write(json.dumps(dict(path=rel,content=path.read_text(encoding='utf-8')),ensure_ascii=False)+'\n')
            index.append(dict(path=rel,bytes=path.stat().st_size))
    write(publication / 'manifest.json', dict(files=index, weights_uploaded=False, no_recomputation=True))
    print('SPATIAL_EVIDENCE_READY', publication, flush=True)


def run(commit):
    import fcntl
    if read(BASE / 'registered.json')['followup_commit'] != commit:
        raise RuntimeError('registered successor release differs')
    with (BASE / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        write(BASE / 'run_started.json', dict(observed_at=now(),pid=os.getpid()), once=True)
        try:
            load_payload()
            os.environ.update(environment())
            with wait_for_full():  # The predecessor lock stays held until OUR workers have exited.
                write(BASE / 'state.json', dict(status='RUNNING_A_SPATIAL',observed_at=now()))
                with resident_pair() as children:
                    result = execute_stages(children)
            write(BASE / 'run_complete.json', dict(status=result,observed_at=now()), once=True)
            write(BASE / 'state.json', dict(status=result,observed_at=now()))
        except BaseException:
            write(BASE / 'first_failure.json', dict(observed_at=now(),traceback=traceback.format_exc(),
                  automatic_retry=False,original_full_untouched=True), once=True)
            raise
        finally:
            # All own workers are stopped before exporting/auth/network; never hold a GPU for upload.
            try:
                export()
                from post_m2_v2.publish import publish
                publish(BASE)
            except Exception as exc:
                write(BASE / 'upload_pending.json', dict(status='UPLOAD_PENDING_NO_RECOMPUTE',
                      error=type(exc).__name__,observed_at=now()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('start', 'run', 'worker', 'status', 'publish'))
    parser.add_argument('--commit')
    parser.add_argument('--kind', choices=KINDS)
    args = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('use the existing remote_sensing Linux server')
    if args.action in ('start', 'run') and not re.fullmatch('[0-9a-f]{40}', args.commit or ''):
        parser.error('exact published successor commit required')
    if args.action == 'status':
        status()
    elif args.action == 'start':
        start(args.commit)
    elif args.action == 'run':
        def terminated(signum, frame):
            raise RuntimeError('successor terminated; no automatic restart')
        signal.signal(signal.SIGTERM, terminated)
        run(args.commit)
    elif args.action == 'worker':
        if not args.kind:
            parser.error('worker kind required')
        worker(args.kind)
    else:
        load_payload()
        from post_m2_v2.publish import publish
        publish(BASE)  # Existing compact output only; no training or inference.


if __name__ == '__main__':
    main()
