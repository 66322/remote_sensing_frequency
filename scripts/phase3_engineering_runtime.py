"""Explicit runtime revision: owned DINO mirror, memfd, first-failure stop."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import runpy
import sys
import time
import traceback

from phase3_memfd_compat import probe

ROOT = Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro')
_original_worker = None
_original_make_model = None
_runtime = None


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def file_at(root, name):
    path = Path(root) / name
    result = path.resolve()
    result.relative_to(Path(root).resolve())
    for node in (path, *path.parents):
        if node.is_symlink():
            raise RuntimeError('runtime symlink refused')
        if node == Path(root):
            break
    return result


def verify_runtime(directory):
    directory = Path(directory)
    revision = read(directory / 'runtime_revision.json')
    runtime = Path(revision['runtime_directory'])
    m2, combined = Path(revision['m2_directory']), Path(revision['combined_directory'])
    if directory not in (m2, combined) or runtime != m2 / 'repairs/engineering_runtime':
        raise RuntimeError('revision directory binding differs')
    if m2.parent != ROOT / 'records' or combined.parent != ROOT / 'records':
        raise RuntimeError('revision outside project records')
    if sha(directory / 'runtime_revision.json') != read(directory / 'registration.json')['runtime_revision_sha256']:
        raise RuntimeError('revision receipt changed')
    if read(m2 / 'runtime_revision.json') != revision or read(combined / 'runtime_revision.json') != revision:
        raise RuntimeError('paired runtime revision differs')
    binding = {name: sha(m2 / name) for name in ('plan.json', 'code_manifest.json', 'folds.json')}
    if binding != revision['m2_binding'] or read(m2 / 'registration.json')['binding'] != binding:
        raise RuntimeError('revised M2 binding changed')
    for name, expected in read(m2 / 'code_manifest.json')['files'].items():
        if sha(file_at(m2 / 'code', name)) != expected:
            raise RuntimeError('frozen M2 source changed: ' + name)
    if sha(m2 / 'pretrained.json') != revision['pretrained_sha256']:
        raise RuntimeError('revised pretrained source binding changed')
    if read(m2 / 'pretrained.json')['repository'] != str(runtime / 'dinov2_py39'):
        raise RuntimeError('actual model path is not the owned compatibility mirror')
    for name, expected in revision['runtime_files'].items():
        if sha(file_at(runtime, name)) != expected:
            raise RuntimeError('runtime file changed: ' + name)
    admission = read(runtime / 'admission.json')
    for name, row in admission['dino_files'].items():
        if sha(file_at(runtime / 'dinov2_py39', name)) != row['mirror_sha256']:
            raise RuntimeError('DINO compatibility mirror changed: ' + name)
    registration = read(combined / 'registration.json')
    if registration['explicit_m2_directory'] != str(m2):
        raise RuntimeError('combined explicit source changed')
    manifest = combined / 'code/configs/phase3_combined_execution_manifest.json'
    if sha(manifest) != registration['manifest_sha256']:
        raise RuntimeError('combined manifest changed')
    if read(manifest)['files'] != registration['package_files']:
        raise RuntimeError('combined manifest binding changed')
    for name, expected in registration['package_files'].items():
        if sha(file_at(combined / 'code', name)) != expected:
            raise RuntimeError('combined frozen source changed: ' + name)
    return revision


class StopOnFailureEvents:
    """Escalate the first failed job through the original owned-worker cleanup."""
    def __init__(self, events):
        self.events = events

    def put(self, event):
        if event.get('kind') == 'FAILED':
            event = dict(event, kind='WORKER_FAILED', error='STOP_ON_FIRST_JOB_FAILURE: ' + event['error'])
        self.events.put(event)


def failfast_worker(base, gpu, uuid, tasks, events, acks):
    return _original_worker(base, gpu, uuid, tasks, StopOnFailureEvents(events), acks)


def guarded_make_model(base, job, load=False):
    verify_runtime(Path(base))
    return _original_make_model(base, job, load)


def explicit_source(records, revision):
    source = Path(revision['m2_directory'])
    if source.parent != Path(records) or not (source / 'registration.json').is_file():
        raise RuntimeError('explicit revised M2 source missing; never register another M2')
    return source


def normalized_catalog(status):
    # The frozen helper uses a top-level absent result; the supervisor expects both datasets.
    if status == {'ready': False, 'reason': 'catalog absent'}:
        return {name: dict(ready=False, reason='catalog absent') for name in ('3DCD', 'P3')}
    return status


def wait_for_release(base, revision):
    runtime = Path(revision['runtime_directory'])
    ready = dict(pid=os.getpid(), revision_commit=revision['revision_commit'], observed='verified_before_launch')
    target = base / 'runtime_entry_ready.json'
    with target.open('x', encoding='utf-8') as output:
        json.dump(ready, output)
    print('RUNTIME_READY_WAITING_FOR_PAIRED_LAUNCH', base, flush=True)
    deadline = time.monotonic() + 120
    while not (runtime / 'launch_release.json').exists():
        if time.monotonic() > deadline:
            raise RuntimeError('paired launch release absent; no training started')
        time.sleep(.2)
    release = read(runtime / 'launch_release.json')
    key = 'm2_controller_pid' if base == Path(revision['m2_directory']) else 'combined_controller_pid'
    if (release['revision_commit'] != revision['revision_commit'] or release[key] != os.getpid()
            or release['runtime_revision_sha256'] != sha(base / 'runtime_revision.json')):
        raise RuntimeError('paired launch release binding differs')


def main():
    global _original_worker, _original_make_model, _runtime
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--mode', choices=('checks', 'm2', 'combined'), required=True)
    args = parser.parse_args()
    base = args.directory.resolve()
    revision = verify_runtime(base)
    m2, combined = Path(revision['m2_directory']), Path(revision['combined_directory'])
    print('ENGINEERING_RUNTIME_MEMFD', json.dumps(probe()), flush=True)
    _runtime = Path(revision['runtime_directory'])
    sys.path[:0] = [str(m2 / 'code'), str(m2 / 'code/scripts')]
    import phase3_m2_common as c
    c.verify(m2)
    if args.mode == 'checks':
        sys.argv = ['unittest', 'discover', '-s', str(m2 / 'code/tests'), '-p', 'test_phase3_m2.py', '-v']
        runpy.run_module('unittest', run_name='__main__')
        return
    try:
        wait_for_release(base, revision)
        runtime = importlib.import_module('phase3_m2_runtime')
        _original_worker, _original_make_model = runtime.worker, runtime.make_model
        runtime.worker, runtime.make_model = failfast_worker, guarded_make_model
        if args.mode == 'm2':
            if base != m2:
                raise RuntimeError('M2 entry directory differs')
            controller = importlib.import_module('control_phase3_m2')
            controller.run(m2)
            status = read(m2 / 'queue_status.json')['status']
            if status != 'COMPLETE_SERVER_CHECKED':
                raise RuntimeError('M2 stopped without server-checked completion: ' + status)
        else:
            if base != combined:
                raise RuntimeError('combined entry directory differs')
            sys.path[:0] = [str(combined / 'code/scripts'), str(combined / 'code')]
            controller = importlib.import_module('control_phase3_combined')
            controller._m2_directory = lambda records: explicit_source(records, revision)
            original_catalog = controller.public_catalog_status
            controller.public_catalog_status = lambda *a, **kw: normalized_catalog(original_catalog(*a, **kw))
            controller.run(combined)
    except BaseException as error:
        c.write(base / 'runtime_revision_failure.json', dict(error=str(error), traceback=traceback.format_exc(),
                automatic_retry=False, observed_at=c.now()))
        # Do not turn an existing diagnostic status into a successful completion.
        current = read(base / 'queue_status.json') if (base / 'queue_status.json').exists() else {}
        if current.get('status') not in ('FAILED_NO_RETRY', 'INCOMPLETE_NO_RETRY', 'STOPPED_NO_AUTOMATIC_RETRY'):
            c.write(base / 'queue_status.json', dict(status='FAILED_NO_RETRY' if args.mode == 'm2'
                    else 'STOPPED_NO_AUTOMATIC_RETRY', error=str(error), automatic_retry=False, observed_at=c.now()))
        raise


def entry():
    # Cover corruption/import/probe failures before the original controller try block.
    argv = list(sys.argv)
    try:
        main()
    except BaseException as error:
        if '--directory' in argv and '--mode' in argv and argv[argv.index('--mode') + 1] != 'checks':
            base = Path(argv[argv.index('--directory') + 1]).resolve()
            if base.parent == ROOT / 'records' and base.is_dir():
                from datetime import datetime, timezone, timedelta
                observed = datetime.now(timezone(timedelta(hours=8))).isoformat()
                value = dict(error=str(error), traceback=traceback.format_exc(), automatic_retry=False, observed_at=observed)
                for name, payload in [('runtime_revision_entry_failure.json', value)]:
                    target = base / name
                    temporary = target.with_name(name + '.tmp.' + str(os.getpid()))
                    temporary.write_text(json.dumps(payload, ensure_ascii=False) + '\n', encoding='utf-8')
                    os.replace(temporary, target)
                status = read(base / 'queue_status.json') if (base / 'queue_status.json').exists() else {}
                if status.get('status') not in ('FAILED_NO_RETRY', 'INCOMPLETE_NO_RETRY', 'STOPPED_NO_AUTOMATIC_RETRY'):
                    target = base / 'queue_status.json'
                    temporary = target.with_name(target.name + '.tmp.' + str(os.getpid()))
                    temporary.write_text(json.dumps(dict(value, status='FAILED_NO_RETRY'
                        if argv[argv.index('--mode') + 1] == 'm2' else 'STOPPED_NO_AUTOMATIC_RETRY')), encoding='utf-8')
                    os.replace(temporary, target)
        raise


if __name__ == '__main__':
    entry()
