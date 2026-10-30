"""Audited local DINO import mirror for Python 3.9; no download or install."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
MIRROR = ROOT/'records/post_d21_day_queue_20260929/dinov2_py39_compat'
MANIFEST = '.codex_py39_compat_manifest.json'


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(8*1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def compatible_repo(original, force_py39=False):
    original = Path(original).resolve()
    if sys.version_info >= (3, 10) and not force_py39:
        return original, None
    manifest_path = MIRROR/MANIFEST
    if not MIRROR.exists():
        MIRROR.parent.mkdir(parents=True, exist_ok=True)
        stage = MIRROR.with_name(MIRROR.name+'.tmp.'+uuid.uuid4().hex)
        shutil.copytree(original, stage, ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc'))
        files = {}
        for path in sorted(stage.rglob('*.py')):
            source = path.read_text(encoding='utf-8')
            tree = ast.parse(source, filename=str(path))
            future = [node for node in tree.body if isinstance(node,ast.ImportFrom)
                and node.module == '__future__']
            if not any(alias.name == 'annotations' for node in future for alias in node.names):
                if future:
                    insert_at = max(node.end_lineno for node in future)
                elif tree.body and isinstance(tree.body[0],ast.Expr) and isinstance(tree.body[0].value,ast.Constant) and isinstance(tree.body[0].value.value,str):
                    insert_at = tree.body[0].end_lineno
                else:
                    insert_at = 0
                lines = source.splitlines(keepends=True)
                lines.insert(insert_at,'from __future__ import annotations\n')
                path.write_text(''.join(lines), encoding='utf-8')
            files[str(path.relative_to(stage)).replace('\\','/')] = digest(path)
        if not files or 'hubconf.py' not in files:
            raise RuntimeError('DINO compatibility mirror has no hubconf.py')
        manifest = dict(original_repository=str(original), python_compatibility='3.9',
            change='prepend postponed annotations to Python sources only', files=files)
        (stage/MANIFEST).write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        os.replace(stage,MIRROR)
    if not manifest_path.is_file():
        raise RuntimeError('DINO compatibility mirror has no manifest')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['original_repository'] != str(original) or manifest['python_compatibility'] != '3.9':
        raise RuntimeError('DINO compatibility mirror origin mismatch')
    for name,expected in manifest['files'].items():
        path = MIRROR/name
        if not path.is_file() or digest(path) != expected:
            raise RuntimeError('DINO compatibility mirror changed: '+name)
    return MIRROR, digest(manifest_path)
