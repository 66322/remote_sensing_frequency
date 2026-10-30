"""Register exactly once, copy immutable source snapshot, CPU-check and detach."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys

SOURCE = 'research_post_t_mechanism_20261011T094823_3625851'
PREFIX = 'research_post_t_paired_v2_'
FILES = [
    'model/post_t_paired_v2.py',
    'scripts/post_t_paired_v2_common.py', 'scripts/post_t_paired_v2_data.py',
    'scripts/post_t_paired_v2_evaluation.py', 'scripts/post_t_paired_v2_runtime.py',
    'scripts/run_post_t_paired_v2.py', 'scripts/run_post_t_content_v2.py',
    'scripts/prepare_post_t_paired_v2.py', 'scripts/control_post_t_paired_v2.py',
    'scripts/manage_post_t_paired_v2.py', 'scripts/summarize_post_t_paired_v2.py',
    'scripts/enqueue_post_t_paired_v2.py', 'scripts/upload_post_t_paired_v2.py',
    'tests/test_post_t_paired_v2.py',
    'configs/post_t_paired_v2/source_mechanism_plan.json', 'configs/post_t_paired_v2/source_receipt.json',
    *['configs/post_t_paired_v2/' + n + '.json' for n in ('F8', 'H8', 'R8', 'F16', 'H16', 'R16')],
    'docs/protocols/POST_T_PAIRED_V2_EXECUTION_20261011.md',
    'docs/protocols/POST_T_PAIRED_ADAPTATION_BUDGET_20261011.md',
    'docs/protocols/POST_T_RESEARCH_SEQUENCE_20261011.md',
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--commit', required=True)
    a = ap.parse_args()
    root = a.root.resolve()
    root.relative_to(Path('/home/jovyan/zzx').resolve())
    records = root / 'records'
    source = records / SOURCE
    sys.path.insert(0, str(source / 'code/scripts'))
    from post_n2_diag_common import read, write, sha
    import fcntl
    with (records / 'post_t_paired_v2_registration.lock').open('a') as registration:
        fcntl.flock(registration, fcntl.LOCK_EX | fcntl.LOCK_NB)
        existing = sorted(records.glob(PREFIX + '*'))
        if existing:
            for folder in existing:
                status = read(folder / 'queue_status.json')['status'] if (folder / 'queue_status.json').exists() else 'HOLD_INCOMPLETE_REGISTRATION'
                print('PAIRED_ALREADY_REGISTERED', folder, status, flush=True)
            return 0
        commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', a.commit + '^{commit}'], text=True).strip()
        base = records / (PREFIX + datetime.now().strftime('%Y%m%dT%H%M%S') + '_' + str(os.getpid()))
        base.mkdir()
        code = base / 'code'
        manifest = read(source / 'code_manifest.json')
        try:
            for name, digest in manifest['files'].items():
                old = (source / 'code' / name).resolve()
                old.relative_to(source / 'code')
                if sha(old) != digest:
                    raise RuntimeError('inherited source changed: ' + name)
                target = code / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(old.read_bytes())
            for name in FILES:
                target = code / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(subprocess.check_output(['git', '-C', str(root), 'show', commit + ':' + name]))
            sys.path.insert(0, str(code / 'scripts'))
            import post_t_paired_v2_common as c
            if sha(source / 'plan.json') != c.SOURCE_PLAN_SHA or sha(source / 'code_manifest.json') != c.SOURCE_CODE_SHA:
                raise RuntimeError('predecessor receipt binding differs')
            p = c.make_plan(root, base, commit, read(source / 'plan.json'))
            c.validate(p)
            observation = c.inspect_predecessor(root, p)
            if observation['verdict'] != 'READY':
                raise RuntimeError('prior queue is not complete/released: ' + str(observation))
            write(base / 'plan.json', p)
            write(base / 'registration_observation.json', observation)
            (base / 'execution_commit.txt').write_text(commit + '\n')
            write(base / 'code_manifest.json', dict(commit=commit, inherited_source_commit=manifest['commit'],
                  files={f.relative_to(code).as_posix(): sha(f) for f in code.rglob('*') if f.is_file()}))
            for name in ('temporary', 'cache/torch', 'logs', 'control'):
                (base / name).mkdir(parents=True, exist_ok=True)
            env = dict(os.environ, CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                       PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(base / 'temporary'), TEMP=str(base / 'temporary'), TMP=str(base / 'temporary'),
                       XDG_CACHE_HOME=str(base / 'cache'), TORCH_HOME=str(base / 'cache/torch'),
                       PYTHONPATH=os.pathsep.join([str(code), str(code / 'scripts')]))
            state = c.initial_state(p)
            state['status'] = 'CPU_VERIFYING'
            write(base / 'queue_status.json', state)
            with (base / 'cpu_checks.log').open('x') as log:
                subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(code / 'tests'), '-p', 'test_post_t_paired_v2.py', '-v'],
                               cwd=code, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=900)
            state['status'] = 'REGISTERED'
            write(base / 'queue_status.json', state)
            logfile = base / ('nohup_' + datetime.now().strftime('%Y%m%dT%H%M%S%f') + '.log')
            cmd = [sys.executable, '-u', '-B', str(code / 'scripts/control_post_t_paired_v2.py'), '--root', str(root), '--directory', str(base)]
            with logfile.open('x') as log:
                proc = subprocess.Popen(['nohup', *cmd], cwd=code, env=env, stdin=subprocess.DEVNULL,
                                        stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            write(base / 'launch.json', dict(controller_pid=proc.pid, command=cmd, log=str(logfile), physical_gpus=[0, 1]))
            (base / 'controller.pid').write_text(str(proc.pid) + '\n')
            print('PAIRED_QUEUE_REGISTERED', base, 'PID=' + str(proc.pid), 'GPU=0,1 TRAININGS=6 NEW_STEPS=72000 CONTENT_CASES=48', flush=True)
            print('PAIRED_LOG', logfile, flush=True)
            print('PAIRED_RELEASE: python', code / 'scripts/manage_post_t_paired_v2.py', '--directory', base, '--action release --gpu 0', flush=True)
        except BaseException as exc:
            write(base / 'registration_failure.json', dict(error=str(exc), preserve_directory=True, no_retry=True))
            if (base / 'queue_status.json').exists():
                state = read(base / 'queue_status.json')
                state['status'] = 'HOLD_REGISTRATION'
                state['error'] = str(exc)
                write(base / 'queue_status.json', state)
            raise
    return 0


if __name__ == '__main__':
    sys.exit(main())
