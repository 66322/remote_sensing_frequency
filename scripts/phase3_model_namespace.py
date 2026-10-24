"""Explicit model-package paths for the two verified, separated source snapshots."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import runpy
import sys
import traceback


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def install_model_paths(m2_code, combined_code):
    m2_code, combined_code = Path(m2_code).resolve(), Path(combined_code).resolve()
    paths = [m2_code / 'model', combined_code / 'model']
    if not all(p.is_dir() for p in paths):
        raise RuntimeError('both verified model directories are required')
    for source in paths[1].rglob('*.py'):
        other = paths[0] / source.relative_to(paths[1])
        if other.exists() and sha(source) != sha(other):
            raise RuntimeError('conflicting model source names: ' + source.name)
    # A regular M2 model package otherwise wins over the combined namespace directory.
    sys.path[:0] = [str(m2_code), str(combined_code), str(m2_code / 'scripts'), str(combined_code / 'scripts')]
    module = importlib.import_module('model')
    if getattr(module, '__file__', None) and Path(module.__file__).resolve().parent not in paths:
        raise RuntimeError('model package was imported from outside verified snapshots')
    for name, loaded in list(sys.modules.items()):
        if name.startswith('model.') and getattr(loaded, '__file__', None):
            file = Path(loaded.__file__).resolve()
            if not any(p == file.parent or p in file.parents for p in paths):
                raise RuntimeError('model submodule outside verified snapshots: ' + name)
    module.__path__ = [str(p) for p in paths]
    if module.__spec__ is not None:
        module.__spec__.submodule_search_locations = module.__path__
    importlib.invalidate_caches()
    return module.__path__


def verify_patch(base):
    base = Path(base).resolve()
    receipt = read(base / 'model_namespace_repair.json')
    m2, queue = Path(receipt['m2_directory']), Path(receipt['combined_directory'])
    if base not in (m2, queue) or read(m2 / 'model_namespace_repair.json') != read(queue / 'model_namespace_repair.json'):
        raise RuntimeError('namespace repair pair differs')
    packet = Path(receipt['packet_directory'])
    packet.relative_to(m2 / 'repairs')
    if sha(packet / 'repair_receipt.json') != sha(base / 'model_namespace_repair.json'):
        raise RuntimeError('namespace repair receipt changed')
    for name, expected in receipt['files'].items():
        path = (packet / name).resolve()
        path.relative_to(packet.resolve())
        if sha(path) != expected:
            raise RuntimeError('namespace repair source changed: ' + name)
    if sha(base / 'runtime_revision.json') != receipt['previous_runtime_revision_sha256']:
        raise RuntimeError('original runtime revision changed')
    runtime = Path(read(m2 / 'runtime_revision.json')['runtime_directory'])
    sys.path.insert(0, str(runtime / 'scripts'))
    core = importlib.import_module('phase3_engineering_runtime')
    if Path(core.__file__).resolve() != (runtime / 'scripts/phase3_engineering_runtime.py').resolve():
        raise RuntimeError('original runtime import came from a different snapshot')
    revision = core.verify_runtime(base)
    return receipt, revision, core


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--mode', choices=('m2', 'combined', 'checks-m2', 'checks-combined'), required=True)
    parser.add_argument('--suite', choices=('test_phase3_combined_plan.py', 'test_phase3_j_heads.py', 'test_phase3_public_queue.py'))
    args = parser.parse_args()
    base = args.directory.resolve()
    receipt, revision, core = verify_patch(base)
    m2, queue = Path(receipt['m2_directory']), Path(receipt['combined_directory'])
    paths = install_model_paths(m2 / 'code', queue / 'code')
    print('VERIFIED_MODEL_PACKAGE_PATHS', json.dumps(paths), flush=True)
    if args.mode == 'checks-combined':
        if not args.suite or base != queue:
            raise RuntimeError('combined check suite and directory required')
        sys.argv = ['unittest', 'discover', '-s', str(queue / 'code/tests'), '-p', args.suite, '-v']
        runpy.run_module('unittest', run_name='__main__')
        return
    mode = 'checks' if args.mode == 'checks-m2' else args.mode
    if args.mode in ('m2', 'combined'):
        expected = m2 if mode == 'm2' else queue
        if base != expected:
            raise RuntimeError('namespace controller directory differs')
        with (base / 'namespace_entry_ready.json').open('x', encoding='utf-8') as output:
            json.dump(dict(pid=os.getpid(), patch_commit=receipt['patch_commit'], model_paths=paths), output)
    sys.argv = [str(Path(core.__file__)), '--directory', str(base), '--mode', mode]
    core.entry()


if __name__ == '__main__':
    argv = list(sys.argv)
    try:
        main()
    except BaseException as error:
        if '--mode' in argv and argv[argv.index('--mode') + 1] in ('m2', 'combined'):
            base = Path(argv[argv.index('--directory') + 1]).resolve()
            if base.parent == Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records'):
                target = base / 'namespace_entry_failure.json'
                target.write_text(json.dumps(dict(error=str(error), traceback=traceback.format_exc(), automatic_retry=False)), encoding='utf-8')
        raise
