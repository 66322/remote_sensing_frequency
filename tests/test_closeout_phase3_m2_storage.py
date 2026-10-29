import importlib.util
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('storage', BASE / 'scripts' / 'closeout_phase3_m2_storage.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


def fixture_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class StorageSafetyTests(unittest.TestCase):
    def setUp(self):
        parent = BASE / 'tests' / 'owned_test_workspaces'
        parent.mkdir(exist_ok=True)
        self.parent = parent.resolve()
        self.tmp = Path(tempfile.mkdtemp(prefix='fixture_', dir=str(self.parent))).resolve()
        self.records = self.tmp / 'records'
        self.records.mkdir()
        self.m2 = self.records / 'research_phase3_m2_revision_fixture'
        self.q = self.records / 'research_phase3_combined_revision_fixture'
        self.m2.mkdir(); self.q.mkdir()
        self.runs = dict(m2_directory=self.m2, combined_directory=self.q)
        for name in ('plan.json', 'code_manifest.json', 'folds.json'):
            s.write(self.m2 / name, dict(fixture=name))
        self.binding = {name: fixture_sha(self.m2 / name) for name in ('plan.json', 'code_manifest.json', 'folds.json')}
        s.write(self.m2 / 'registration.json', dict(binding=self.binding))
        s.write(self.m2 / 'queue_status.json', dict(status='COMPLETE_SERVER_CHECKED'))
        s.write(self.q / 'queue_status.json', dict(status='STOPPED_NO_AUTOMATIC_RETRY'))
        for fold in ['F0', 'F1', 'F2']:
            for seed in [42, 17, 2026]:
                for tail in ['R', 'T0', 'T1', 'T2', 'T3', 'D0', 'DSelf', 'DClean', 'DF', 'DShuffle', 'DEntropy', 'DMix']:
                    full = self._testMethodName in ('test_inventory_and_90_retired_18_retained', 'test_only_named_temporary_caches_added',
                                                     'test_endpoint_receipt_mismatch_refused', 'test_missing_endpoint_refused')
                    if not full and (fold, seed, tail) not in [('F0', 42, 'R'), ('F0', 42, 'DF')]:
                        continue
                    jobid = '%s_s%s_%s' % (fold, seed, tail)
                    folder = self.m2 / 'jobs' / jobid
                    folder.mkdir(parents=True)
                    role = 'rgb_reference' if tail == 'R' else 'rgb_oof_teacher' if tail.startswith('T') else 'dsm_student'
                    arm = tail if role == 'dsm_student' else 'D0'
                    s.write(folder / 'parameters.json', dict(binding=self.binding, job=dict(id=jobid, role=role, arm=arm)))
                    (folder / 'endpoint.pth').write_bytes(('fixture endpoint ' + jobid).encode())
                    s.write(folder / 'complete.json', dict(job=jobid, binding=self.binding, optimizer_updates=32000,
                                                          checkpoint_sha256=fixture_sha(folder / 'endpoint.pth')))
        pub = self.m2 / 'publication'; pub.mkdir()
        gates = dict(G0=True, G1=False, H2_degradation_specificity=True, G2=False, G3=True, G4=False)
        s.write(pub / 'summary.json', dict(status='COMPLETE_SERVER_CHECKED', jobs_complete=108, evaluated_cases=77868,
                                         errors=[], failures=[], binding=self.binding, gates=gates))
        s.write(pub / 'gates.json', dict(status=gates))
        originals = []
        for name in ['case_counts.jsonl.gz', 'all_aggregates.jsonl.gz']:
            p = self.m2 / name; p.write_bytes(b'fixture sufficient counts')
            originals.append(dict(path=name, size=p.stat().st_size, sha256=fixture_sha(p)))
        for name in s.PUB:
            if not (pub / name).exists() and name not in ('manifest.json', 'server_evidence_index.json'):
                (pub / name).write_bytes(b'fixture publication')
        s.write(pub / 'server_evidence_index.json', dict(binding=self.binding, files=originals))
        self.rebuild_manifest()
        s.write(self.records / s.LATCH, {key: str(value) for key, value in self.runs.items()})

    def rebuild_manifest(self):
        pub = self.m2 / 'publication'
        s.write(pub / 'manifest.json', dict(files=[dict(file=p.name, size=p.stat().st_size, sha256=fixture_sha(p))
                                                for p in sorted(pub.iterdir()) if p.name != 'manifest.json']))

    def tearDown(self):
        # Only recursively remove this test's newly created, resolved owned directory.
        target = self.tmp.resolve()
        self.assertEqual(target.parent, self.parent)
        self.assertTrue(target.name.startswith('fixture_'))
        shutil.rmtree(str(target))

    def test_inventory_and_90_retired_18_retained(self):
        _, runs = s.bound_runs(self.records)
        before = s.inventory(runs)
        summary, _ = s.verify_evidence(self.m2)
        candidates, retained = s.choose_candidates(runs, before, summary['binding'])
        self.assertEqual(len(candidates), 90)
        self.assertEqual(len(retained), 18)
        self.assertEqual(sum(r['reason'] == 'retired_oof_teacher' for r in candidates), 36)
        self.assertEqual(sum(r['reason'] == 'closed_dsm_recipe' for r in candidates), 54)
        self.assertTrue(all(Path(p).name == 'endpoint.pth' for p in retained))

    def test_only_named_temporary_caches_added(self):
        paths = ['cache/cuda/generated.bin', 'cache/torch/pretrained.pth', 'unclassified_large.bin',
                 'temporary/scratch.dat', 'jobs/F0_s42_DF/last_resume.pth']
        for name in paths:
            p = self.m2 / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b'keep or retire by role')
        candidates, _ = s.choose_candidates(self.runs, s.inventory(self.runs), self.binding)
        names = {r['relative'] for r in candidates}
        self.assertTrue(str(Path(paths[0])) in names)
        self.assertTrue(str(Path(paths[3])) in names)
        self.assertTrue(str(Path(paths[4])) in names)
        self.assertFalse(str(Path(paths[1])) in names)
        self.assertFalse(str(Path(paths[2])) in names)

    def test_endpoint_receipt_mismatch_refused(self):
        p = self.m2 / 'jobs/F0_s42_DF/complete.json'
        value = s.read(p); value['optimizer_updates'] = 31000; s.write(p, value)
        with self.assertRaisesRegex(RuntimeError, 'receipt mismatch'):
            s.choose_candidates(self.runs, s.inventory(self.runs), self.binding)

    def test_missing_endpoint_refused(self):
        (self.m2 / 'jobs/F0_s42_DF/endpoint.pth').unlink()
        with self.assertRaisesRegex(RuntimeError, 'missing endpoint'):
            s.choose_candidates(self.runs, s.inventory(self.runs), self.binding)

    def test_changed_publication_refused(self):
        (self.m2 / 'publication/metrics.csv').write_text('modified')
        with self.assertRaisesRegex(RuntimeError, 'manifest mismatch'):
            s.verify_evidence(self.m2)

    def test_changed_original_counts_refused(self):
        (self.m2 / 'case_counts.jsonl.gz').write_bytes(b'modified raw counts')
        with self.assertRaisesRegex(RuntimeError, 'sufficient counts missing/changed'):
            s.verify_evidence(self.m2)

    def test_mismatched_binding_refused(self):
        s.write(self.m2 / 'registration.json', dict(binding=dict(modified=True)))
        with self.assertRaisesRegex(RuntimeError, 'binding mismatch'):
            s.verify_evidence(self.m2)

    def test_archive_preserves_evidence_without_weights(self):
        _, checked = s.verify_evidence(self.m2)
        out = self.records / 'export'; out.mkdir()
        result = s.export_evidence(self.records, self.runs, out, checked)
        with tarfile.open(result['path']) as tar:
            names = tar.getnames()
        self.assertIn('M2/publication/F0_counts.jsonl.gz', names)
        self.assertIn('m2_directory/jobs/F0_s42_DF/complete.json', names)
        self.assertFalse(any(name.endswith('.pth') for name in names))
        self.assertEqual(len(names), result['listed_members'])

    def test_process_reference_blocks_cleanup(self):
        proc = self.tmp / 'proc'; p = proc / '12345'; p.mkdir(parents=True)
        (p / 'cmdline').write_bytes(('python\0' + str(self.m2) + '/code/train.py\0').encode())
        with self.assertRaisesRegex(RuntimeError, 'live processes'):
            s.assert_stopped(self.runs, proc)
        (p / 'cmdline').write_bytes(b'')
        s.assert_stopped(self.runs, proc)

    def test_running_queue_blocks_cleanup(self):
        s.write(self.q / 'queue_status.json', dict(status='RUNNING_J'))
        with self.assertRaisesRegex(RuntimeError, 'not stopped'):
            s.assert_stopped(self.runs, self.tmp)

    def test_outside_root_refused(self):
        with self.assertRaises(ValueError):
            s.safe(self.q / 'file', self.m2)
        with self.assertRaisesRegex(RuntimeError, 'root itself'):
            s.safe(self.m2, self.m2)

    def test_changed_stat_refused_before_unlink(self):
        p = self.m2 / 'sentinel'; p.write_bytes(b'keep')
        st = p.stat()
        row = dict(path=str(p), dev=st.st_dev, ino=st.st_ino, bytes=st.st_size + 1,
                   mtime_ns=st.st_mtime_ns)
        with self.assertRaisesRegex(RuntimeError, 'Candidate changed'):
            s.delete_checked(row, self.m2)
        self.assertEqual(p.read_bytes(), b'keep')

    @unittest.skipUnless(os.name == 'posix', 'Actual dir_fd unlink is verified by the server-owned sentinel selfcheck')
    def test_linux_file_only_delete_and_symlink_refusal(self):
        out = self.tmp / 'selfcheck'; out.mkdir()
        self.assertEqual(s.linux_delete_selfcheck(out)['status'], 'PASSED')


if __name__ == '__main__':
    unittest.main()
