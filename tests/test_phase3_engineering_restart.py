import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import bootstrap_phase3_engineering_restart as boot
import phase3_engineering_runtime as runtime
import status_phase3_engineering_restart as status


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


class RevisionTests(unittest.TestCase):
    def fixture(self, root):
        m2, combined = root / 'records/m2', root / 'records/combined'
        m2.mkdir(parents=True); combined.mkdir()
        rt = m2 / 'repairs/engineering_runtime'; rt.mkdir(parents=True)
        for name in ('plan.json', 'folds.json'):
            put(m2 / name, {})
        source = m2 / 'code/source.py'; source.parent.mkdir(); source.write_text('frozen')
        put(m2 / 'code_manifest.json', {'files': {'source.py': runtime.sha(source)}})
        put(m2 / 'pretrained.json', {'repository': str(rt / 'dinov2_py39')})
        dino = rt / 'dinov2_py39/attention.py'; dino.parent.mkdir(); dino.write_text('compat')
        put(rt / 'admission.json', {'dino_files': {'attention.py': {'mirror_sha256': runtime.sha(dino)}}})
        payload = rt / 'entry.py'; payload.write_text('entry')
        manifest = combined / 'code/configs/phase3_combined_execution_manifest.json'
        put(manifest, {'files': {}})
        binding = {n: runtime.sha(m2 / n) for n in ('plan.json', 'code_manifest.json', 'folds.json')}
        revision = dict(runtime_directory=str(rt), m2_directory=str(m2), combined_directory=str(combined),
                        m2_binding=binding, pretrained_sha256=runtime.sha(m2 / 'pretrained.json'),
                        runtime_files={'entry.py': runtime.sha(payload), 'admission.json': runtime.sha(rt / 'admission.json')})
        for base in (m2, combined):
            put(base / 'runtime_revision.json', revision)
            reg = dict(runtime_revision_sha256=runtime.sha(base / 'runtime_revision.json'))
            reg.update(binding=binding) if base == m2 else reg.update(explicit_m2_directory=str(m2),
                manifest_sha256=runtime.sha(manifest), package_files={})
            put(base / 'registration.json', reg)
        return m2, combined, rt, revision

    def test_failed_event_escalates_without_mutating_original(self):
        class Events:
            def __init__(self): self.rows = []
            def put(self, event): self.rows.append(event)
        events = Events(); wrapper = runtime.StopOnFailureEvents(events)
        failed = dict(kind='FAILED', gpu=0, task_id='T_one', error='import error')
        wrapper.put(failed)
        self.assertEqual(events.rows[0]['kind'], 'WORKER_FAILED')
        self.assertEqual(failed['kind'], 'FAILED')
        packet = dict(kind='PACKET', packet={'fd': 7})
        wrapper.put(packet)
        self.assertIs(events.rows[1], packet)

    def test_explicit_source_ignores_other_old_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'old_failed').mkdir()
            source = root / 'new'; source.mkdir(); put(source / 'registration.json', {})
            self.assertEqual(runtime.explicit_source(root, {'m2_directory': str(source)}), source)
            with self.assertRaises(RuntimeError):
                runtime.explicit_source(root / 'foreign', {'m2_directory': str(source)})

    def test_runtime_pair_and_changed_model_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); m2, queue, rt, revision = self.fixture(root)
            with patch.object(runtime, 'ROOT', root):
                self.assertEqual(runtime.verify_runtime(m2), revision)
                self.assertEqual(runtime.verify_runtime(queue), revision)
                (m2 / 'pretrained.json').write_text('{}')
                with self.assertRaisesRegex(RuntimeError, 'pretrained'):
                    runtime.verify_runtime(m2)

    def test_frozen_source_and_mirror_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); m2, queue, rt, revision = self.fixture(root)
            with patch.object(runtime, 'ROOT', root):
                p = m2 / 'code/source.py'; original = p.read_text(); p.write_text('changed')
                with self.assertRaisesRegex(RuntimeError, 'frozen M2'):
                    runtime.verify_runtime(m2)
                p.write_text(original)
                (rt / 'dinov2_py39/attention.py').write_text('changed')
                with self.assertRaisesRegex(RuntimeError, 'mirror'):
                    runtime.verify_runtime(queue)

    def test_revision_receipt_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); m2, queue, rt, revision = self.fixture(root)
            put(queue / 'runtime_revision.json', dict(revision, m2_directory='other'))
            with patch.object(runtime, 'ROOT', root):
                with self.assertRaises(RuntimeError): runtime.verify_runtime(m2)

    def test_exact_failed_attempts_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / boot.OLD_M2).mkdir(); (root / boot.OLD_QUEUE).mkdir()
            boot.exact_records(root)
            (root / 'research_phase3_m2_unknown').mkdir()
            with self.assertRaises(RuntimeError): boot.exact_records(root)

    def test_copy_sources_checks_original_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'source'; source.mkdir()
            (source / 'one.py').write_text('original')
            files = {'one.py': boot.sha(source / 'one.py')}
            boot.copy_sources(source, root / 'copied', files)
            self.assertEqual((root / 'copied/one.py').read_text(), 'original')
            (source / 'one.py').write_text('changed')
            with self.assertRaises(RuntimeError): boot.copy_sources(source, root / 'refused', files)

    def test_early_entry_failure_sets_failed_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); m2 = root / 'records/m2'; m2.mkdir(parents=True)
            put(m2 / 'queue_status.json', {'status': 'LAUNCHED_PREPARING'})
            with patch.object(runtime, 'ROOT', root), patch.object(runtime, 'main', side_effect=RuntimeError('bad receipt')), \
                 patch.object(sys, 'argv', ['entry.py', '--directory', str(m2), '--mode', 'm2']):
                with self.assertRaises(RuntimeError): runtime.entry()
            self.assertEqual(runtime.read(m2 / 'queue_status.json')['status'], 'FAILED_NO_RETRY')
            self.assertTrue((m2 / 'runtime_revision_entry_failure.json').is_file())

    def test_absent_catalog_waits_but_invalid_contract_is_not_rewritten(self):
        ready = runtime.normalized_catalog({'ready': False, 'reason': 'catalog absent'})
        self.assertFalse(any(ready[k]['ready'] for k in ('3DCD', 'P3')))
        original = {'3DCD': {'ready': True}, 'P3': {'ready': False}}
        self.assertIs(runtime.normalized_catalog(original), original)

    def test_latch_prevents_download_or_second_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); records = root / 'records'; records.mkdir()
            put(records / boot.LATCH, {'status': 'LAUNCHING_ONCE'})
            fake = SimpleNamespace(flock=lambda *args: None, LOCK_EX=1, LOCK_NB=2)
            with patch.object(boot, 'ROOT', root), patch.object(sys, 'platform', 'linux'), \
                 patch.dict(sys.modules, {'fcntl': fake}), patch.object(sys, 'argv', ['boot', '--commit', 'a' * 40, '--apply']), \
                 patch.object(boot, 'package_at') as package, patch.object(boot.subprocess, 'Popen') as popen:
                boot.main()
            package.assert_not_called(); popen.assert_not_called()

    def test_launch_release_requires_the_owned_pid_and_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); m2, queue, rt, revision = self.fixture(root)
            revision['revision_commit'] = 'revision'
            put(rt / 'launch_release.json', dict(revision_commit='revision', m2_controller_pid=runtime.os.getpid(),
                combined_controller_pid=-1, runtime_revision_sha256=runtime.sha(m2 / 'runtime_revision.json')))
            runtime.wait_for_release(m2, revision)
            with self.assertRaises(RuntimeError): runtime.wait_for_release(queue, revision)

    def test_status_uses_explicit_source_and_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            records = Path(tmp); m2 = records / 'revised'; m2.mkdir()
            queue = records / 'queue'; queue.mkdir(); (records / 'old_failed').mkdir()
            put(records / status.LATCH, dict(m2_directory=str(m2), combined_directory=str(queue), status='CONTROLLERS_LAUNCHED'))
            put(m2 / 'jobs/job/progress.json', dict(step=20, loss=1.2))
            result = status.snapshot(records)
            self.assertEqual(result['m2_directory']['latest_training_progress'][0]['step'], 20)
            self.assertEqual(result['m2_directory']['directory'], str(m2.resolve()))

    def test_status_without_registration_does_not_create_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            records = Path(tmp)
            self.assertEqual(status.snapshot(records)['status'], 'NOT_REGISTERED_OR_BOOTSTRAP_STILL_CHECKING')
            self.assertEqual(list(records.iterdir()), [])

    def test_preparation_requires_original_input_identity_before_workers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); base = root / 'new'; base.mkdir(); rt = root / 'runtime'; rt.mkdir()
            put(base / 'input_index.json', {'files': ['original'], 'normalization': 1})
            put(rt / 'previous_input_index.json', {'files': ['original'], 'normalization': 1})
            with patch.object(runtime, '_runtime', rt), patch.object(runtime, '_original_prepare', return_value={'prepared': True}):
                self.assertEqual(runtime.guarded_prepare(base), {'prepared': True})
                put(base / 'input_index.json', {'files': ['different'], 'normalization': 1})
                with self.assertRaisesRegex(RuntimeError, 'Fit12 input'):
                    runtime.guarded_prepare(base)


if __name__ == '__main__':
    unittest.main()
