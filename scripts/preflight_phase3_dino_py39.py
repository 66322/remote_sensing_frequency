"""CPU-only import repair preflight; no queue/controller/training entry point."""
import argparse
import ast
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

ROOT = Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro')
DINO_COMMIT = '7764ea0f912e53c92e82eb78a2a1631e92725fc8'
M2_COMMIT = 'ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd'
ERROR = "unsupported operand type(s) for |: 'type' and 'NoneType'"


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
    # Preflight records are new and never replace an existing receipt.
    with Path(path).open('x', encoding='utf-8') as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write('\n')


def checked_path(path, root):
    path, root = Path(path), Path(root).resolve()
    resolved = path.resolve()
    resolved.relative_to(root)
    for node in (path, *path.parents):
        if node == root:
            break
        if node.is_symlink():
            raise RuntimeError('symlink refused: ' + str(node))
    if resolved == root:
        raise RuntimeError('root itself refused')
    return resolved


def postpone(source):
    """Only add a future statement; require identical executable AST."""
    tree = ast.parse(source)
    if any(isinstance(node, ast.ImportFrom) and node.module == '__future__'
           and any(a.name == 'annotations' for a in node.names) for node in tree.body):
        return source
    at = tree.body[0].lineno - 1 if tree.body else len(source.splitlines())
    for i, node in enumerate(tree.body):
        doc = (i == 0 and isinstance(node, ast.Expr)
               and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str))
        if doc or (isinstance(node, ast.ImportFrom) and node.module == '__future__'):
            at = node.end_lineno
        else:
            break
    lines = source.splitlines(keepends=True)
    if at and not lines[at - 1].endswith(('\n', '\r')):
        lines[at - 1] += '\n'
    lines.insert(at, 'from __future__ import annotations\n')
    result = ''.join(lines)
    transformed = ast.parse(result)
    transformed.body = [n for n in transformed.body if not (
        isinstance(n, ast.ImportFrom) and n.module == '__future__'
        and [a.name for a in n.names] == ['annotations'])]
    if ast.dump(tree, include_attributes=False) != ast.dump(transformed, include_attributes=False):
        raise RuntimeError('annotation transform changed executable AST')
    compile(result, '<postponed-dino-source>', 'exec', dont_inherit=True)
    return result


def verify_m2(base):
    names = ('plan.json', 'code_manifest.json', 'folds.json')
    binding = {name: sha(base / name) for name in names}
    if read(base / 'registration.json')['binding'] != binding:
        raise RuntimeError('original M2 binding differs')
    plan = read(base / 'plan.json')
    if (plan['execution_commit'] != M2_COMMIT or plan['core_jobs'] != 108
            or plan['updates'] != 32000 or plan['batch'] != 16 or plan['auto_retry']):
        raise RuntimeError('original M2 contract differs')
    for name, digest in read(base / 'code_manifest.json')['files'].items():
        if sha(checked_path(base / 'code' / name, base / 'code')) != digest:
            raise RuntimeError('original M2 code changed: ' + name)
    return binding


def audit_failure(base):
    summary = read(base / 'publication/summary.json')
    if (summary['status'] != 'INCOMPLETE_NO_RETRY' or summary['jobs_complete'] != 0
            or summary['evaluated_cases'] != 0 or summary['optimizer_updates'] != 0):
        raise RuntimeError('not the diagnosed incomplete M2 attempt')
    if read(base / 'queue_status.json')['status'] != 'INCOMPLETE_NO_RETRY':
        raise RuntimeError('original M2 status changed')
    rows = [read(p) for p in sorted((base / 'failures').glob('*.json'))]
    if len(rows) != 63 or len(summary['failures']) != 63:
        raise RuntimeError('expected exactly the original 63 failed jobs')
    if {r['task_id'] for r in rows} != {r['task'] for r in summary['failures']}:
        raise RuntimeError('failure task bindings differ')
    for row in rows:
        trace = row['traceback']
        if (row['error'] != ERROR or row['automatic_retry']
                or not all(s in trace for s in ('in make_model', 'torch.hub.load',
                                               'attention.py', 'float | None', 'TypeError: ' + ERROR))):
            raise RuntimeError('failure differs from the diagnosed pre-model import')
    if any(row['error'] != ERROR for row in summary['failures']):
        raise RuntimeError('summary failure class differs')
    # parameters.json is written only AFTER make_model and optimizer construction.
    for folder in (base / 'jobs').iterdir():
        for path in folder.iterdir():
            if path.name in ('parameters.json', 'progress.json', 'complete.json') or path.suffix in ('.pth', '.tmp'):
                raise RuntimeError('later model/training artifact present: ' + str(path))
            if path.name in ('trajectory.jsonl', 'batch_hashes.jsonl') and path.stat().st_size:
                raise RuntimeError('nonempty update artifact present: ' + str(path))
    return dict(failed_before_model=63, jobs_complete=0, evaluated_cases=0,
                no_update_artifacts=True, summary_sha256=sha(base / 'publication/summary.json'))


def mirror(original, destination):
    commit = subprocess.check_output(['git', '-C', str(original), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != DINO_COMMIT:
        raise RuntimeError('DINO pinned commit differs')
    raw = subprocess.check_output(['git', '-C', str(original), 'ls-tree', '-rz', '--full-tree', 'HEAD'])
    files = {}
    destination.mkdir()
    for entry in raw.split(b'\0'):
        if not entry:
            continue
        info, encoded = entry.split(b'\t', 1)
        mode, kind, oid = info.decode('ascii').split()
        name = encoded.decode('utf-8')
        if name != 'hubconf.py' and not (name.startswith('dinov2/') and name.endswith('.py')):
            continue
        if mode not in ('100644', '100755') or kind != 'blob':
            raise RuntimeError('non-regular DINO Python source: ' + name)
        source = checked_path(original / name, original)
        data = source.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != oid:
            raise RuntimeError('DINO source is dirty: ' + name)
        output = postpone(data.decode('utf-8')).encode('utf-8')
        target = checked_path(destination / name, destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(output)
        files[name] = dict(git_blob=oid, original_sha256=hashlib.sha256(data).hexdigest(),
                           mirror_sha256=hashlib.sha256(output).hexdigest())
    if 'hubconf.py' not in files or 'dinov2/layers/attention.py' not in files:
        raise RuntimeError('DINO mirror lacks required entry points')
    return files


def cpu_model(base, record):
    """Separate process: import + public weights only, zero forward/backward/update."""
    receipt = read(record / 'admission.json')
    source = read(base / 'pretrained.json')
    if sha(source['path']) != source['sha256']:
        raise RuntimeError('public weights changed')
    for name, row in receipt['dino_files'].items():
        if sha(record / 'dinov2_py39' / name) != row['mirror_sha256']:
            raise RuntimeError('preflight mirror changed: ' + name)
    import torch
    if torch.__version__ != '2.2.2+cu121':
        raise RuntimeError('use existing Torch2.2.2+cu121 environment')
    if torch.cuda.is_initialized():
        raise RuntimeError('CPU preflight must not initialize CUDA')
    torch.set_num_threads(1)
    sys.path[:0] = [str(record / 'dinov2_py39'), str(base / 'code'), str(base / 'code/scripts')]
    torch.manual_seed(42)
    encoder = torch.hub.load(str(record / 'dinov2_py39'), 'dinov2_vits14', source='local', pretrained=False)
    import dinov2
    Path(dinov2.__file__).resolve().relative_to((record / 'dinov2_py39').resolve())
    if len(encoder.blocks) != 12:
        raise RuntimeError('expected original twelve-block DINOv2 ViT-S/14')
    encoder.load_state_dict(torch.load(source['path'], map_location='cpu', weights_only=False), strict=True)
    from model.phase2_matched import MatchedExpert
    model = MatchedExpert(encoder)
    from phase2_train import model_digest
    if any(p.device.type != 'cpu' for p in model.parameters()) or torch.cuda.is_initialized():
        raise RuntimeError('CPU-only requirement violated')
    result = dict(status='CPU_MODEL_IMPORT_AND_PUBLIC_WEIGHTS_PASSED', observed_at=now(),
                  python=sys.version, torch=torch.__version__, encoder_blocks=len(encoder.blocks),
                  initial_state_sha256=model_digest(model), weights_sha256=source['sha256'],
                  cuda_initialized=False, forward_calls=0, optimizer_updates=0,
                  controllers_launched=0, datasets_read=False, training_retry=False)
    write(record / 'cpu_model_passed.json', result)
    print(json.dumps(result, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--cpu-worker', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.platform != 'linux':
        raise RuntimeError('server Linux preflight only')
    base = checked_path(args.directory, ROOT / 'records')
    if base.parent != ROOT / 'records' or not base.name.startswith('research_phase3_m2_'):
        raise RuntimeError('exact existing M2 record directory required')
    os.environ.update(CUDA_VISIBLE_DEVICES='', XFORMERS_DISABLED='1', PYTHONDONTWRITEBYTECODE='1',
                      OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
    sys.dont_write_bytecode = True
    if args.cpu_worker:
        record = checked_path(args.cpu_worker, base / 'repairs')
        cpu_model(base, record)
        return
    import fcntl
    with (base / 'controller.lock').open('r+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        binding = verify_m2(base)
        audit = audit_failure(base)
        source = read(base / 'pretrained.json')
        original = checked_path(source['repository'], ROOT / 'external')
        if source['repository_commit'] != DINO_COMMIT:
            raise RuntimeError('pretrained DINO binding differs')
        checked_path(source['path'], ROOT / 'pretrained_external')
        parent = checked_path(base / 'repairs', base)
        parent.mkdir(exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        record = parent / ('dino_py39_preflight_' + stamp + '_' + str(os.getpid()))
        record.mkdir()
        print('CPU_PREFLIGHT_RECORD', record, flush=True)
        try:
            (record / 'preflight_source.py').write_bytes(Path(__file__).read_bytes())
            files = mirror(original, record / 'dinov2_py39')
            write(record / 'admission.json', dict(observed_at=now(), original_binding=binding,
                audit=audit, dino_repository=str(original), dino_commit=DINO_COMMIT,
                dino_files=files, preflight_source_sha256=sha(__file__), training_retry=False))
            env = dict(os.environ)
            env['PYTHONPATH'] = ''
            with (record / 'cpu_model.log').open('x', encoding='utf-8') as log:
                result = subprocess.run([sys.executable, '-u', '-B', str(record / 'preflight_source.py'),
                    '--directory', str(base), '--cpu-worker', str(record)], cwd=record, env=env,
                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, timeout=180)
            if result.returncode:
                raise RuntimeError('CPU model preflight failed; see ' + str(record / 'cpu_model.log'))
            passed = read(record / 'cpu_model_passed.json')
            if verify_m2(base) != binding or audit_failure(base) != audit:
                raise RuntimeError('original evidence changed during preflight')
            # Re-read tracked source bytes; no changes to the original repository are allowed.
            for name, row in files.items():
                if sha(original / name) != row['original_sha256']:
                    raise RuntimeError('DINO original changed during preflight')
            print('CPU_PREFLIGHT_PASSED_NO_TRAINING_OR_RETRY', record, passed['status'], flush=True)
        except BaseException as error:
            write(record / 'preflight_failure.json', dict(error=str(error), traceback=traceback.format_exc(),
                  observed_at=now(), automatic_retry=False, controllers_launched=0))
            raise


if __name__ == '__main__':
    main()
