"""One explicitly authorized zero-update engineering restart; preserve failed runs."""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback
import urllib.request

ROOT = Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro')
OLD_M2 = 'research_phase3_m2_20261023T222114_2166330'
OLD_QUEUE = 'research_phase3_combined_20261023T222112_2164225'
CPU_RECORD = 'repairs/dino_py39_preflight_20261024T090448_2718326'
CPU_COMMIT = '86806140400620cc64af4728bc8c2af7cdcb69db'
MANIFEST = 'configs/phase3_engineering_restart_manifest.json'
LATCH = 'phase3_engineering_restart_20261024_once.json'


def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(8 * 1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp.' + str(os.getpid()))
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def download(commit, name):
    with urllib.request.urlopen('https://raw.githubusercontent.com/66322/remote_sensing_frequency/'
                                + commit + '/' + name, timeout=90) as response:
        return response.read()


def exact_records(records):
    for pattern, expected in (('research_phase3_m2_*', OLD_M2), ('research_phase3_combined_*', OLD_QUEUE)):
        if {p.name for p in records.glob(pattern)} != {expected}:
            raise RuntimeError('unexpected run directory; no implicit source selection: ' + pattern)


def package_at(records, commit):
    package = records / ('phase3_engineering_restart_package_' + commit)
    package.mkdir(exist_ok=True)
    raw = download(commit, MANIFEST)
    manifest = json.loads(raw)
    if manifest['schema_version'] != 1 or manifest['authorization'] != 'user_explicit_zero_update_restart_20261024':
        raise RuntimeError('unexpected engineering restart manifest')
    if sha(__file__) != manifest['files']['scripts/bootstrap_phase3_engineering_restart.py']:
        raise RuntimeError('bootstrap differs from the immutable revision')
    for name, expected in manifest['files'].items():
        target = package / name
        target.resolve().relative_to(package.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if sha(target) != expected:
                raise RuntimeError('existing revision package changed: ' + name)
            continue
        data = download(commit, name)
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError('revision source download mismatch: ' + name)
        with target.open('xb') as output:
            output.write(data)
    target = package / MANIFEST
    target.parent.mkdir(exist_ok=True)
    if target.exists() and target.read_bytes() != raw:
        raise RuntimeError('existing revision manifest differs')
    if not target.exists():
        target.write_bytes(raw)
    return package, manifest


def checked_run(command, cwd, env, log, timeout=300):
    print('CHECK_START', log, flush=True)
    with Path(log).open('x', encoding='utf-8') as output:
        result = subprocess.run(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
    if result.returncode:
        print(Path(log).read_text(encoding='utf-8')[-16000:], flush=True)
        raise RuntimeError('target check failed; see ' + str(log))
    print('CHECK_PASSED', log, flush=True)


def copy_sources(source, destination, files):
    destination.mkdir()
    for name, expected in files.items():
        original, target = source / name, destination / name
        original.resolve().relative_to(source.resolve())
        target.resolve().relative_to(destination.resolve())
        if original.is_symlink() or sha(original) != expected:
            raise RuntimeError('original source differs: ' + name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        if sha(target) != expected:
            raise RuntimeError('source copy mismatch: ' + name)


def validate_cpu_record(old, cpu, preflight, expected_script_sha):
    admission, passed = read(cpu / 'admission.json'), read(cpu / 'cpu_model_passed.json')
    if (admission['preflight_source_sha256'] != expected_script_sha
            or sha(cpu / 'preflight_source.py') != expected_script_sha):
        raise RuntimeError('CPU preflight executable binding differs')
    if admission['original_binding'] != preflight.verify_m2(old):
        raise RuntimeError('CPU preflight original binding differs')
    if admission['audit'] != preflight.audit_failure(old):
        raise RuntimeError('failed attempt changed since successful CPU preflight')
    if (passed['status'] != 'CPU_MODEL_IMPORT_AND_PUBLIC_WEIGHTS_PASSED' or passed['cuda_initialized']
            or passed['forward_calls'] != 0 or passed['optimizer_updates'] != 0
            or passed['controllers_launched'] != 0 or passed['datasets_read'] or passed['training_retry']):
        raise RuntimeError('not the CPU-only success receipt')
    if passed['python'] != sys.version or passed['torch'] != '2.2.2+cu121':
        raise RuntimeError('successful CPU preflight interpreter differs')
    for name, row in admission['dino_files'].items():
        if sha(cpu / 'dinov2_py39' / name) != row['mirror_sha256']:
            raise RuntimeError('successful CPU mirror changed')
    return admission, passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--apply', action='store_true', help='explicitly launch the one authorized revised attempt')
    args = parser.parse_args()
    if sys.platform != 'linux' or not re.fullmatch('[a-f0-9]{40}', args.commit):
        raise RuntimeError('Linux and full immutable commit required')
    import fcntl
    records = ROOT / 'records'
    with (records / 'phase3_engineering_restart_registration.lock').open('a') as lock, ExitStack() as stack:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        latch = records / LATCH
        if latch.exists():
            print('EXISTING_ENGINEERING_RESTART_NO_DUPLICATE', latch.read_text(), flush=True)
            return
        exact_records(records)
        package, manifest = package_at(records, args.commit)
        sys.path.insert(0, str(package / 'scripts'))
        import preflight_phase3_dino_py39 as preflight
        from phase3_memfd_repair_common import verify_sources
        old, old_queue = records / OLD_M2, records / OLD_QUEUE
        for directory in (old, old_queue):
            stream = stack.enter_context((directory / 'controller.lock').open('r+'))
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        original_binding = verify_sources(old, old_queue)
        cpu = old / CPU_RECORD
        admission, passed = validate_cpu_record(old, cpu, preflight, manifest['cpu_preflight_sha256'])
        state = read(old_queue / 'queue_status.json')
        if state['status'] != 'STOPPED_NO_AUTOMATIC_RETRY' or state['error'] != 'M2 did not finish as server-checked':
            raise RuntimeError('original combined stop differs')
        if any((old_queue / 'jobs').iterdir()):
            raise RuntimeError('original combined has later stage jobs')
        original_pretrained = read(old / 'pretrained.json')
        repository = preflight.checked_path(original_pretrained['repository'], ROOT / 'external')
        if sha(original_pretrained['path']) != original_pretrained['sha256'] or passed['weights_sha256'] != original_pretrained['sha256']:
            raise RuntimeError('public initialization binding changed')
        sys.path[:0] = [str(old / 'code'), str(old / 'code/scripts')]
        import phase3_m2_common as c
        env = c.environment(old)
        env['PYTHONPATH'] = str(package / 'scripts')
        checked_run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(package / 'tests'),
                     '-p', 'test_phase3_engineering_restart.py', '-v'], package, env,
                    package / ('admission_checks_' + str(os.getpid()) + '.log'))
        import torch
        if torch.__version__ != '2.2.2+cu121':
            raise RuntimeError('keep original Torch2.2.2+cu121 environment')
        inventory = c.gpu_inventory()
        if not inventory['ready']:
            print('GPU0_OR_1_BUSY_NOT_REGISTERED', json.dumps(inventory), flush=True)
            return
        if shutil.disk_usage(ROOT).free < 40 * 1024**3:
            raise RuntimeError('40GiB free reserve required')
        print('ZERO_UPDATE_FAILURE_AND_CPU_RECEIPT_VERIFIED', flush=True)
        if not args.apply:
            print('INSPECTED_NO_NEW_RUN_OR_TRAINING', flush=True)
            return
        stamp = datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%dT%H%M%S')
        m2 = records / ('research_phase3_m2_revision_' + stamp + '_' + str(os.getpid()))
        queue = records / ('research_phase3_combined_revision_' + stamp + '_' + str(os.getpid()))
        intent = dict(status='REGISTERING_ONCE', revision_commit=args.commit, old_m2=str(old), old_combined=str(old_queue),
                      m2_directory=str(m2), combined_directory=str(queue), automatic_retry=False,
                      authorization='user: 继续，把实验启动; 2026-10-24', observed_at=now())
        write(latch, intent)  # Remains a duplicate guard through every partial launch/failure.
        process = supervisor = None
        release_written = False
        try:
            for directory in (m2, queue):
                directory.mkdir()
                for name in ('jobs', 'logs', 'failures', 'skipped', 'trajectory_counts', 'mask_design', 'publication',
                             'temporary', 'cache/torch', 'cache/cuda', 'cache/triton', 'cache/kernels'):
                    (directory / name).mkdir(parents=True, exist_ok=True)
            copy_sources(old / 'code', m2 / 'code', read(old / 'code_manifest.json')['files'])
            combined_registration = read(old_queue / 'registration.json')
            copy_sources(old_queue / 'code', queue / 'code', combined_registration['package_files'])
            shutil.copyfile(old_queue / 'code/configs/phase3_combined_execution_manifest.json',
                            queue / 'code/configs/phase3_combined_execution_manifest.json')
            for name in ('folds.json', 'code_manifest.json'):
                shutil.copyfile(old / name, m2 / name)
            plan = read(old / 'plan.json')
            plan.update(registered_at=now(), previous_failed_attempt=str(old), engineering_revision_commit=args.commit)
            write(m2 / 'plan.json', plan)
            shutil.copyfile(old_queue / 'plan.json', queue / 'plan.json')
            runtime = m2 / 'repairs/engineering_runtime'
            runtime.parent.mkdir()
            copy_sources(package, runtime, manifest['files'])
            shutil.copyfile(package / MANIFEST, runtime / 'execution_manifest.json')
            dino_files = preflight.mirror(repository, runtime / 'dinov2_py39')
            if dino_files != admission['dino_files']:
                raise RuntimeError('owned mirror differs from server-checked CPU mirror')
            source = dict(original_pretrained, repository=str(runtime / 'dinov2_py39'),
                          original_repository=str(repository), compatibility='postponed_annotations_only')
            write(m2 / 'pretrained.json', source)
            binding = {name: sha(m2 / name) for name in ('plan.json', 'code_manifest.json', 'folds.json')}
            write(m2 / 'registration.json', dict(binding=binding, manifest=read(old / 'registration.json')['manifest'],
                  engineering_revision_commit=args.commit, observed_at=now()))
            write(queue / 'registration.json', dict(combined_registration, explicit_m2_directory=str(m2),
                  engineering_revision_commit=args.commit, registered_at=now()))
            write(runtime / 'admission.json', dict(original_binding=original_binding, dino_files=dino_files,
                  original_failed_directory=str(old), successful_cpu_record=str(cpu), successful_cpu_receipt_sha256=sha(cpu / 'cpu_model_passed.json'),
                  source_commit=args.commit, explicit_one_time_restart=True, automatic_retry=False, observed_at=now()))
            new_env = c.environment(m2)
            checked_run([sys.executable, '-u', '-B', str(runtime / 'scripts/preflight_phase3_dino_py39.py'),
                         '--directory', str(m2), '--cpu-worker', str(runtime)], m2 / 'code', new_env,
                        runtime / 'cpu_model.log', timeout=180)
            new_passed = read(runtime / 'cpu_model_passed.json')
            if new_passed['initial_state_sha256'] != passed['initial_state_sha256']:
                raise RuntimeError('revised actual model initialization differs from successful CPU check')
            runtime_files = dict(manifest['files'])
            for name in ('execution_manifest.json', 'admission.json', 'cpu_model_passed.json'):
                runtime_files[name] = sha(runtime / name)
            revision = dict(revision_commit=args.commit, m2_directory=str(m2), combined_directory=str(queue),
                  runtime_directory=str(runtime), m2_binding=binding, pretrained_sha256=sha(m2 / 'pretrained.json'),
                  runtime_files=runtime_files, old_m2_directory=str(old), old_combined_directory=str(old_queue),
                  scientific_m2_commit=preflight.M2_COMMIT, explicit_restart=True, automatic_retry=False, observed_at=now())
            for directory in (m2, queue):
                write(directory / 'runtime_revision.json', revision)
                registration = read(directory / 'registration.json')
                registration['runtime_revision_sha256'] = sha(directory / 'runtime_revision.json')
                write(directory / 'registration.json', registration)
            entry = runtime / 'scripts/phase3_engineering_runtime.py'
            check_env = dict(new_env, M2_TARGET_RUNTIME='1')
            checked_run([sys.executable, '-u', '-B', str(entry), '--mode', 'checks', '--directory', str(m2)],
                        m2 / 'code', check_env, m2 / 'target_checks.log')
            from phase3_memfd_repair_common import validate_target_checks
            validate_target_checks((m2 / 'target_checks.log').read_text())
            write(m2 / 'target_checks.json', dict(passed=True, original_tests=16, log_sha256=sha(m2 / 'target_checks.log'),
                  actual_cpu_model_passed=True, first_formal_update_is_cuda_admission=True, observed_at=now()))
            combined_env = dict(new_env)
            combined_env['PYTHONPATH'] = os.pathsep.join([str(queue / 'code'), str(queue / 'code/scripts'),
                                                          str(m2 / 'code'), str(m2 / 'code/scripts')])
            for suite in ('test_phase3_combined_plan.py', 'test_phase3_j_heads.py', 'test_phase3_public_queue.py'):
                checked_run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(queue / 'code/tests'),
                             '-p', suite, '-v'], queue / 'code', combined_env, queue / (suite + '.log'))
            write(queue / 'target_checks.json', dict(passed=True, suites=3, observed_at=now()))
            if verify_sources(old, old_queue) != original_binding or preflight.audit_failure(old) != admission['audit']:
                raise RuntimeError('old failed evidence changed during preparation')
            fresh = c.gpu_inventory()
            if not fresh['ready'] or any(fresh['selected'][g][1] != inventory['selected'][g][1] for g in (0, 1)):
                raise RuntimeError('GPU0/1 became busy or UUID changed; no controllers launched')
            intent.update(status='LAUNCHING_ONCE', observed_at=now())
            write(latch, intent)
            write(m2 / 'queue_status.json', dict(status='LAUNCHED_PREPARING', observed_at=now()))
            write(queue / 'queue_status.json', dict(status='WAIT_M2', source=str(m2), observed_at=now()))
            with (m2 / 'nohup.log').open('x', encoding='utf-8') as output:
                process = subprocess.Popen([sys.executable, '-u', '-B', str(entry), '--mode', 'm2', '--directory', str(m2)],
                    cwd=m2 / 'code', env=new_env, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            intent['m2_controller_pid'] = process.pid
            write(latch, intent)
            write(m2 / 'launch.json', dict(controller_pid=process.pid, runtime_wrapper=str(entry), observed_at=now()))
            with (queue / 'nohup.log').open('x', encoding='utf-8') as output:
                supervisor = subprocess.Popen([sys.executable, '-u', '-B', str(entry), '--mode', 'combined', '--directory', str(queue)],
                    cwd=queue / 'code', env=combined_env, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            write(queue / 'launch.json', dict(controller_pid=supervisor.pid, explicit_m2_directory=str(m2), observed_at=now()))
            deadline = time.monotonic() + 90
            while not all((directory / 'runtime_entry_ready.json').exists() for directory in (m2, queue)):
                if process.poll() is not None or supervisor.poll() is not None:
                    raise RuntimeError('runtime entry failed before paired launch; see new nohup logs')
                if time.monotonic() > deadline:
                    raise RuntimeError('paired runtime readiness timeout; no release written')
                time.sleep(.2)
            for directory, owned in ((m2, process), (queue, supervisor)):
                ready = read(directory / 'runtime_entry_ready.json')
                if ready['pid'] != owned.pid or ready['revision_commit'] != args.commit:
                    raise RuntimeError('paired runtime readiness binding differs')
            fresh = c.gpu_inventory()
            if not fresh['ready'] or any(fresh['selected'][g][1] != inventory['selected'][g][1] for g in (0, 1)):
                raise RuntimeError('GPU occupied before paired release; no training started')
            write(runtime / 'launch_release.json', dict(revision_commit=args.commit, m2_controller_pid=process.pid,
                combined_controller_pid=supervisor.pid, runtime_revision_sha256=sha(m2 / 'runtime_revision.json'), observed_at=now()))
            release_written = True
            intent.update(status='CONTROLLERS_LAUNCHED', combined_controller_pid=supervisor.pid, observed_at=now())
            write(latch, intent)
            print('ENGINEERING_RESTART_LAUNCHED', json.dumps(intent, ensure_ascii=False), flush=True)
            print('STATUS_RECEIPT', latch, flush=True)
        except BaseException as error:
            released = release_written or (m2 / 'repairs/engineering_runtime/launch_release.json').exists()
            if not released:
                for owned in (process, supervisor):
                    if owned is not None and owned.poll() is None:
                        owned.terminate()  # Only waiting entries owned by this bootstrap, before workers exist.
                        owned.wait(timeout=30)
                for directory in (m2, queue):
                    if directory.is_dir():
                        write(directory / 'queue_status.json', dict(status='FAILED_NO_RETRY' if directory == m2
                            else 'STOPPED_NO_AUTOMATIC_RETRY', error=str(error), no_launch_release=True, observed_at=now()))
            intent.update(status='FAILED_NO_AUTOMATIC_RETRY', error=str(error), traceback=traceback.format_exc(), observed_at=now())
            write(latch, intent)
            print('ENGINEERING_RESTART_STOPPED_NO_RETRY', latch, flush=True)
            raise


if __name__ == '__main__':
    main()
