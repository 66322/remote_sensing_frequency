from contextlib import contextmanager
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import phase3_model_namespace as namespace
import repair_phase3_model_namespace as repair


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


@contextmanager
def isolated_model():
    saved = {k: v for k, v in sys.modules.items() if k == 'model' or k.startswith('model.')}
    path = list(sys.path)
    for k in saved: del sys.modules[k]
    try:
        yield
    finally:
        for k in list(sys.modules):
            if k == 'model' or k.startswith('model.'): del sys.modules[k]
        sys.modules.update(saved)
        sys.path[:] = path
        importlib.invalidate_caches()


class NamespaceTests(unittest.TestCase):
    def model_fixture(self, root):
        m2, queue = root / 'm2', root / 'queue'
        (m2 / 'model').mkdir(parents=True); (queue / 'model').mkdir(parents=True)
        (m2 / 'model/__init__.py').write_text('')
        (m2 / 'model/core.py').write_text('value = "frozen M2"\n')
        (queue / 'model/phase3_j_heads.py').write_text('value = "combined J"\n')
        return m2, queue

    def test_reproduces_regular_package_shadow_and_repairs_same_process(self):
        with tempfile.TemporaryDirectory() as tmp, isolated_model():
            m2, queue = self.model_fixture(Path(tmp))
            sys.path[:0] = [str(queue), str(m2)]
            with self.assertRaises(ModuleNotFoundError):
                importlib.import_module('model.phase3_j_heads')
            namespace.install_model_paths(m2, queue)
            j = importlib.import_module('model.phase3_j_heads')
            core = importlib.import_module('model.core')
            self.assertEqual(j.value, 'combined J')
            self.assertEqual(core.value, 'frozen M2')
            self.assertEqual(Path(j.__file__).parent, queue / 'model')
            self.assertEqual(Path(core.__file__).parent, m2 / 'model')
            self.assertFalse((queue / 'model/__init__.py').exists())

    def test_conflicting_names_are_not_silently_selected(self):
        with tempfile.TemporaryDirectory() as tmp, isolated_model():
            m2, queue = self.model_fixture(Path(tmp))
            (queue / 'model/core.py').write_text('value = "different"\n')
            with self.assertRaisesRegex(RuntimeError, 'conflicting'):
                namespace.install_model_paths(m2, queue)

    def test_foreign_preloaded_package_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, isolated_model():
            root = Path(tmp); m2, queue = self.model_fixture(root)
            (root / 'foreign/model').mkdir(parents=True)
            (root / 'foreign/model/__init__.py').write_text('')
            sys.path.insert(0, str(root / 'foreign')); importlib.import_module('model')
            with self.assertRaisesRegex(RuntimeError, 'outside'):
                namespace.install_model_paths(m2, queue)

    def test_path_installation_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp, isolated_model():
            m2, queue = self.model_fixture(Path(tmp))
            self.assertEqual(namespace.install_model_paths(m2, queue), namespace.install_model_paths(m2, queue))

    def admission_fixture(self, root):
        m2, queue = root / repair.M2_NAME, root / repair.QUEUE_NAME
        runtime = m2 / 'repairs/engineering_runtime'; runtime.mkdir(parents=True)
        for base in (m2, queue):
            for name in ('jobs', 'failures'): (base / name).mkdir(parents=True)
            put(base / 'queue_status.json', dict(no_launch_release=True))
        put(root / repair.LATCH, dict(status='FAILED_NO_AUTOMATIC_RETRY', revision_commit=repair.REVISION,
            m2_directory=str(m2), combined_directory=str(queue), error='target check failed; see test_phase3_j_heads.py.log'))
        put(m2 / 'target_checks.json', dict(passed=True))
        (queue / 'test_phase3_j_heads.py.log').write_text("No module named 'model.phase3_j_heads'\nRan 1 test\nFAILED (errors=1)\n")
        verify = lambda base: dict(runtime_directory=str(runtime))
        return m2, queue, runtime, verify

    def test_only_never_released_existing_pair_is_admitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); m2, queue, runtime, verify = self.admission_fixture(root)
            repair.admissible(root, verify)
            (runtime / 'launch_release.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'released'):
                repair.admissible(root, verify)

    def test_any_job_or_launch_refuses_training_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); m2, queue, runtime, verify = self.admission_fixture(root)
            (m2 / 'jobs/started').mkdir()
            with self.assertRaisesRegex(RuntimeError, 'job/failure'):
                repair.admissible(root, verify)
            (m2 / 'jobs/started').rmdir()
            (queue / 'launch.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'launch evidence'):
                repair.admissible(root, verify)

    def test_other_import_failure_or_changed_latch_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); m2, queue, runtime, verify = self.admission_fixture(root)
            (queue / 'test_phase3_j_heads.py.log').write_text('CUDA OOM')
            with self.assertRaisesRegex(RuntimeError, 'single model-package'):
                repair.admissible(root, verify)

    def test_existing_repair_cannot_relaunch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); records = root / 'records'; m2 = records / repair.M2_NAME; m2.mkdir(parents=True)
            put(m2 / 'model_namespace_repair.json', {'patch_commit': 'already'})
            from types import SimpleNamespace
            fake = SimpleNamespace(flock=lambda *a: None, LOCK_EX=1, LOCK_NB=2)
            with patch.object(repair, 'ROOT', root), patch.object(sys, 'platform', 'linux'), \
                 patch.dict(sys.modules, {'fcntl': fake}), patch.object(sys, 'argv', ['repair', '--commit', 'a' * 40, '--apply']), \
                 patch.object(repair, 'fetch') as fetch, patch.object(repair.subprocess, 'Popen') as popen:
                repair.main()
            fetch.assert_not_called(); popen.assert_not_called()


if __name__ == '__main__':
    unittest.main()
