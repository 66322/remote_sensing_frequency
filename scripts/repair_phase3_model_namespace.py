"""Resume the registered, never-released revision after its model-package check failure."""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request

from datetime import datetime, timezone, timedelta

ROOT = Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro')
REVISION = '752d3835a18a15a04d83b1dcc1841bff98bf0b07'
M2_NAME = 'research_phase3_m2_revision_20261024T092814_2738345'
QUEUE_NAME = 'research_phase3_combined_revision_20261024T092814_2738345'
LATCH = 'phase3_engineering_restart_20261024_once.json'
MANIFEST = 'configs/phase3_model_namespace_manifest.json'


def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp.' + str(os.getpid()))
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def fetch(commit, name):
    with urllib.request.urlopen('https://raw.githubusercontent.com/66322/remote_sensing_frequency/' + commit + '/' + name, timeout=90) as response:
        return response.read()


def admissible(records, verify):
    records = Path(records)
    latch = read(records / LATCH)
    m2, queue = records / M2_NAME, records / QUEUE_NAME
    if (latch['status'] != 'FAILED_NO_AUTOMATIC_RETRY' or latch['revision_commit'] != REVISION
            or latch['m2_directory'] != str(m2) or latch['combined_directory'] != str(queue)
            or 'test_phase3_j_heads.py.log' not in latch['error']):
        raise RuntimeError('not the diagnosed never-launched revision')
    revision = verify(m2)
    verify(queue)
    runtime = Path(revision['runtime_directory'])
    if (runtime / 'launch_release.json').exists():
        raise RuntimeError('launch already released; no training retry')
    for directory in (m2, queue):
        for name in ('launch.json', 'runtime_entry_ready.json', 'namespace_entry_ready.json'):
            if (directory / name).exists():
                raise RuntimeError('controller launch evidence exists: ' + name)
        for name in ('jobs', 'failures'):
            if any((directory / name).iterdir()):
                raise RuntimeError('job/failure evidence exists; no training retry')
        if not read(directory / 'queue_status.json').get('no_launch_release'):
            raise RuntimeError('not a no-release stop')
    log = (queue / 'test_phase3_j_heads.py.log').read_text(encoding='utf-8')
    if not all(s in log for s in ("No module named 'model.phase3_j_heads'", 'Ran 1 test', 'FAILED (errors=1)')):
        raise RuntimeError('not the diagnosed single model-package import error')
    if not read(m2 / 'target_checks.json')['passed']:
        raise RuntimeError('original M2 target checks did not pass')
    return latch, revision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if sys.platform != 'linux' or not re.fullmatch('[a-f0-9]{40}', args.commit):
        raise RuntimeError('Linux and full immutable commit required')
    import fcntl
    records = ROOT / 'records'; m2, queue = records / M2_NAME, records / QUEUE_NAME
    with (records / 'phase3_model_namespace_registration.lock').open('a') as lock, ExitStack() as stack:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (m2 / 'model_namespace_repair.json').exists():
            print('EXISTING_NAMESPACE_REPAIR_NO_DUPLICATE', (m2 / 'model_namespace_repair.json').read_text(), flush=True)
            return
        raw = fetch(args.commit, MANIFEST); manifest = json.loads(raw)
        if manifest['revision_commit'] != REVISION or manifest['schema_version'] != 1:
            raise RuntimeError('namespace manifest revision differs')
        if sha(__file__) != manifest['files']['scripts/repair_phase3_model_namespace.py']:
            raise RuntimeError('repair launcher source differs')
        package = records / ('phase3_model_namespace_package_' + args.commit)
        package.mkdir(exist_ok=True)
        for name, expected in manifest['files'].items():
            target = (package / name).resolve(); target.relative_to(package.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if sha(target) != expected:
                    raise RuntimeError('existing namespace package changed: ' + name)
                continue
            data = fetch(args.commit, name)
            if hashlib.sha256(data).hexdigest() != expected:
                raise RuntimeError('namespace source SHA differs')
            target.write_bytes(data)
        sys.path.insert(0, str(package / 'scripts'))
        from phase3_engineering_runtime import verify_runtime
        from bootstrap_phase3_engineering_restart import checked_run, copy_sources
        from phase3_memfd_repair_common import validate_target_checks
        previous, revision = admissible(records, verify_runtime)
        controller_locks = []
        for directory in (m2, queue):
            stream = stack.enter_context((directory / 'controller.lock').open('a'))
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            controller_locks.append(stream)
        sys.path[:0] = [str(m2 / 'code'), str(m2 / 'code/scripts')]
        import phase3_m2_common as c
        inventory = c.gpu_inventory()
        if not inventory['ready']:
            print('GPU0_OR_1_BUSY_NO_NAMESPACE_LAUNCH', json.dumps(inventory), flush=True)
            return
        env = c.environment(m2)
        env['PYTHONPATH'] = str(package / 'scripts')
        checked_run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(package / 'tests'),
                    '-p', 'test_phase3_model_namespace.py', '-v'], package, env,
                    package / ('checks_' + str(os.getpid()) + '.log'))
        if not args.apply:
            print('NAMESPACE_CHECKS_ONLY_NO_CONTROLLER', flush=True)
            return
        packet = m2 / 'repairs' / ('model_namespace_' + args.commit)
        copy_sources(package, packet, manifest['files'])
        (packet / 'execution_manifest.json').write_bytes(raw)
        receipt = dict(patch_commit=args.commit, previous_revision_commit=REVISION, m2_directory=str(m2),
              combined_directory=str(queue), packet_directory=str(packet), files=dict(manifest['files'],
              **{'execution_manifest.json': sha(packet / 'execution_manifest.json')}),
              previous_runtime_revision_sha256=sha(m2 / 'runtime_revision.json'), automatic_retry=False, observed_at=now())
        write(packet / 'repair_receipt.json', receipt)
        for directory in (m2, queue):
            write(directory / 'model_namespace_repair.json', receipt)
        write(packet / 'previous_bootstrap_failure.json', previous)
        for label, directory in (('m2', m2), ('combined', queue)):
            write(packet / (label + '_status_before.json'), read(directory / 'queue_status.json'))
        entry = packet / 'scripts/phase3_model_namespace.py'
        process = supervisor = None; released = False
        try:
            checked_run([sys.executable, '-u', '-B', str(entry), '--directory', str(m2), '--mode', 'checks-m2'],
                        m2 / 'code', dict(env, M2_TARGET_RUNTIME='1'), packet / 'm2_target_checks.log')
            validate_target_checks((packet / 'm2_target_checks.log').read_text())
            for suite in ('test_phase3_combined_plan.py', 'test_phase3_j_heads.py', 'test_phase3_public_queue.py'):
                checked_run([sys.executable, '-u', '-B', str(entry), '--directory', str(queue), '--mode', 'checks-combined', '--suite', suite],
                            queue / 'code', env, packet / (suite + '.log'))
            write(packet / 'target_checks_passed.json', dict(passed=True, original_m2_checks=16, combined_checks=11, observed_at=now()))
            admissible(records, verify_runtime)
            fresh = c.gpu_inventory()
            if not fresh['ready'] or any(fresh['selected'][g][1] != inventory['selected'][g][1] for g in (0, 1)):
                raise RuntimeError('GPU occupied or changed before namespace launch')
            intent = dict(previous, status='LAUNCHING_NAMESPACE_FIX', namespace_patch_commit=args.commit, observed_at=now())
            write(packet / 'launch_intent.json', intent)
            write(records / LATCH, intent)
            c.write(m2 / 'queue_status.json', dict(status='LAUNCHED_PREPARING', observed_at=now()))
            c.write(queue / 'queue_status.json', dict(status='WAIT_M2', source=str(m2), observed_at=now()))
            for directory, mode in ((m2, 'm2'), (queue, 'combined')):
                with (directory / 'nohup.log').open('x', encoding='utf-8') as output:
                    owned = subprocess.Popen([sys.executable, '-u', '-B', str(entry), '--directory', str(directory), '--mode', mode],
                        cwd=directory / 'code', env=env, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
                if mode == 'm2': process = owned
                else: supervisor = owned
                key = 'm2_controller_pid' if mode == 'm2' else 'combined_controller_pid'
                intent[key] = owned.pid
                write(records / LATCH, intent)
                write(directory / 'launch.json', dict(controller_pid=owned.pid, namespace_patch_commit=args.commit, observed_at=now()))
            deadline = time.monotonic() + 90
            while not all((d / 'runtime_entry_ready.json').exists() and (d / 'namespace_entry_ready.json').exists() for d in (m2, queue)):
                if process.poll() is not None or supervisor.poll() is not None:
                    raise RuntimeError('namespace entry failed before release; see new nohup logs')
                if time.monotonic() > deadline:
                    raise RuntimeError('namespace entry readiness timeout')
                time.sleep(.2)
            for directory, owned in ((m2, process), (queue, supervisor)):
                ready, patched = read(directory / 'runtime_entry_ready.json'), read(directory / 'namespace_entry_ready.json')
                if (ready['pid'] != owned.pid or ready['revision_commit'] != REVISION
                        or patched['pid'] != owned.pid or patched['patch_commit'] != args.commit):
                    raise RuntimeError('namespace entry PID/revision binding differs')
            fresh = c.gpu_inventory()
            if not fresh['ready'] or any(fresh['selected'][g][1] != inventory['selected'][g][1] for g in (0, 1)):
                raise RuntimeError('GPU busy before namespace release')
            runtime = Path(revision['runtime_directory'])
            # The entries acquire these exact locks after release; keep only the repair-owner lock.
            for stream in controller_locks:
                fcntl.flock(stream, fcntl.LOCK_UN)
            write(runtime / 'launch_release.json', dict(revision_commit=REVISION, namespace_patch_commit=args.commit,
                  m2_controller_pid=process.pid, combined_controller_pid=supervisor.pid,
                  runtime_revision_sha256=sha(m2 / 'runtime_revision.json'), observed_at=now()))
            released = True
            intent.update(status='CONTROLLERS_LAUNCHED', observed_at=now())
            write(records / LATCH, intent)
            write(packet / 'launched.json', intent)
            print('REGISTERED_REVISION_NAMESPACE_FIXED_LAUNCHED', json.dumps(intent, ensure_ascii=False), flush=True)
        except BaseException as error:
            released = released or (Path(revision['runtime_directory']) / 'launch_release.json').exists()
            if not released:
                for owned in (process, supervisor):
                    if owned is not None and owned.poll() is None:
                        owned.terminate(); owned.wait(timeout=30)
                for directory in (m2, queue):
                    write(directory / 'queue_status.json', dict(status='FAILED_NO_RETRY' if directory == m2 else 'STOPPED_NO_AUTOMATIC_RETRY',
                          error=str(error), no_launch_release=True, observed_at=now()))
            write(packet / 'repair_failure.json', dict(error=str(error), automatic_retry=False, observed_at=now()))
            stopped = read(records / LATCH)
            stopped.update(status='FAILED_NO_AUTOMATIC_RETRY', namespace_patch_commit=args.commit,
                           error=str(error), observed_at=now())
            write(records / LATCH, stopped)
            raise


if __name__ == '__main__':
    main()
