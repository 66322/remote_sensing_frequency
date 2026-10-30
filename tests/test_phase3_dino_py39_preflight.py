import ast
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import preflight_phase3_dino_py39 as p


class PreflightTests(unittest.TestCase):
    def test_postpones_evaluation_without_changing_function(self):
        source = 'def f(x: Undefined | None = None):\n    return x\n'
        with self.assertRaises(NameError):
            exec(source, {})
        namespace = {}
        exec(p.postpone(source), namespace)
        self.assertEqual(namespace['f'](7), 7)
        self.assertEqual(namespace['f'].__annotations__['x'], 'Undefined | None')
        ast.parse(p.postpone(source), feature_version=(3, 9))

    def test_headers_docstring_and_future_are_preserved(self):
        for source in (
            '#!/usr/bin/python\n# coding: utf-8\n"""Module."""\nfrom __future__ import division\ndef f(x: float | None):\n    return x\n',
            '# comment without final newline',
            '"""doc without final newline"""',
            '',
        ):
            transformed = p.postpone(source)
            self.assertIn('from __future__ import annotations', transformed)
            ast.parse(transformed, feature_version=(3, 9))
            self.assertEqual(p.postpone(transformed), transformed)

    def test_existing_future_bytes_stay_unchanged(self):
        source = 'from __future__ import annotations, division\ndef f(x: float | None):\n    return x\n'
        self.assertEqual(p.postpone(source), source)

    def test_mirror_proves_git_bytes_and_original_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); original = root / 'original'; original.mkdir()
            files = {'hubconf.py': b'def dinov2_vits14():\n    return None\n',
                     'dinov2/layers/attention.py': b'class Attention:\n    def f(self, x: float | None):\n        return x\n'}
            tree = b''
            for name, data in files.items():
                target = original / name; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                oid = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
                tree += b'100644 blob ' + oid.encode() + b'\t' + name.encode() + b'\0'
            with patch.object(p.subprocess, 'check_output', side_effect=[p.DINO_COMMIT, tree]):
                result = p.mirror(original, root / 'mirror')
            for name, data in files.items():
                self.assertEqual((original / name).read_bytes(), data)
                self.assertEqual(p.sha(root / 'mirror' / name), result[name]['mirror_sha256'])
            (original / 'hubconf.py').write_text('changed')
            with patch.object(p.subprocess, 'check_output', side_effect=[p.DINO_COMMIT, tree]):
                with self.assertRaisesRegex(RuntimeError, 'dirty'):
                    p.mirror(original, root / 'dirty_mirror')

    def fixture(self, base):
        for name in ('publication', 'failures', 'jobs'):
            (base / name).mkdir()
        failures = []
        for i in range(63):
            task = 'T_job' + str(i)
            row = dict(task_id=task, error=p.ERROR, automatic_retry=False,
                       traceback='in make_model torch.hub.load attention.py float | None TypeError: ' + p.ERROR)
            (base / 'failures' / (task + '.json')).write_text(json.dumps(row))
            failures.append(dict(task=task, error=p.ERROR))
            (base / 'jobs' / ('job' + str(i))).mkdir()
        summary = dict(status='INCOMPLETE_NO_RETRY', jobs_complete=0, evaluated_cases=0,
                       optimizer_updates=0, failures=failures)
        (base / 'publication/summary.json').write_text(json.dumps(summary))
        (base / 'queue_status.json').write_text(json.dumps(dict(status='INCOMPLETE_NO_RETRY')))

    def test_import_failure_audit_and_update_evidence_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); self.fixture(base)
            self.assertEqual(p.audit_failure(base)['failed_before_model'], 63)
            for name, content in (('parameters.json', '{}'), ('progress.json', '{}'),
                                  ('trajectory.jsonl', '{"step":1}'), ('endpoint.pth', 'weights')):
                target = base / 'jobs/job0' / name
                target.write_text(content)
                with self.assertRaises(RuntimeError):
                    p.audit_failure(base)
                target.unlink()

    def test_foreign_failure_and_task_mismatch_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); self.fixture(base)
            target = base / 'failures/T_job0.json'; row = p.read(target)
            row['error'] = 'CUDA OOM'; target.write_text(json.dumps(row))
            with self.assertRaisesRegex(RuntimeError, 'differs'):
                p.audit_failure(base)
            row['error'] = p.ERROR; row['task_id'] = 'other'; target.write_text(json.dumps(row))
            with self.assertRaisesRegex(RuntimeError, 'bindings'):
                p.audit_failure(base)

    def test_paths_and_receipts_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises((RuntimeError, ValueError)):
                p.checked_path(root / '../outside', root)
            with self.assertRaises(RuntimeError):
                p.checked_path(root, root)
            p.write(root / 'receipt.json', {'passed': True})
            with self.assertRaises(FileExistsError):
                p.write(root / 'receipt.json', {'passed': False})


if __name__ == '__main__':
    unittest.main()
