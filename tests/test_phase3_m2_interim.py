"""Scientific aggregation checks; no torch, datasets or filesystem fixtures."""
import sys
import json
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from report_phase3_m2_interim import checked_cm, pool_tiles, fg5, annotate_deltas, collect


def diagonal(n):
    return [[n if i == j else 0 for j in range(6)] for i in range(6)]


class InterimChecks(unittest.TestCase):
    def test_pool_before_metric(self):
        a, b = diagonal(100), diagonal(1)
        a[0][0], b[0][0], b[0][1] = 100, 0, 100
        values = {'a': {'nb': a, 'full': a}, 'b': {'nb': b, 'full': b},
                  'c': {'nb': diagonal(1), 'full': diagonal(1)},
                  'd': {'nb': diagonal(1), 'full': diagonal(1)}}
        pooled = pool_tiles(values, ['a', 'b', 'c', 'd'])
        expected = 100 * ((102 / 202) + (103 / 203) + 3) / 5
        self.assertAlmostEqual(fg5(pooled['nb']), expected)
        mean_tile_metric = sum(fg5(values[t]['nb']) for t in values) / 4
        self.assertNotAlmostEqual(fg5(pooled['nb']), mean_tile_metric)

    def test_incomplete_or_extra_tiles(self):
        value = {'nb': diagonal(1), 'full': diagonal(1)}
        self.assertIsNone(pool_tiles({'a': value}, ['a', 'b', 'c', 'd']))
        with self.assertRaises(ValueError):
            pool_tiles({'wrong': value}, ['a', 'b', 'c', 'd'])

    def test_missing_foreground_class_is_undefined(self):
        cm = diagonal(1)
        cm[4][4] = 0
        self.assertIsNone(fg5(cm))

    def test_integer_matrix_contract(self):
        for invalid in ([[0]], [[-1] * 6 for _ in range(6)],
                        [[1.2] * 6 for _ in range(6)], [[True] * 6 for _ in range(6)]):
            with self.assertRaises(ValueError):
                checked_cm(invalid)

    def test_comparisons_match_seed_age_role_and_complete_coverage(self):
        def row(arm, seed=42, step=32000, role='dsm_student', eligible=True):
            return dict(fold='F0', seed=seed, step=step, role=role, arm=arm,
                        eligible=eligible, tiles=['a', 'b', 'c', 'd'],
                        gt_support={'nb': [10] * 6, 'full': [10] * 6},
                        initial_state_sha256='same-init', sample_stream_sha256='same-stream',
                        nb_fg5=60 if arm == 'D0' else 61)
        rows = [row('D0'), row('DF'), row('DF', seed=17), row('DF', step=8000),
                row('DF', role='rgb_oof_teacher'), row('DF', eligible=False)]
        annotate_deltas(rows)
        self.assertEqual(rows[1]['delta_d0_nb_pp'], 1)
        self.assertTrue(all(r['delta_d0_nb_pp'] is None for r in rows[2:]))

    def test_gt_support_mismatch_rejected(self):
        base = dict(fold='F0', seed=42, step=32000, role='dsm_student', eligible=True,
                    tiles=['a', 'b', 'c', 'd'], nb_fg5=60)
        rows = [dict(base, arm='D0', gt_support={'nb': [10] * 6}),
                dict(base, arm='DF', gt_support={'nb': [11] * 6})]
        with self.assertRaises(ValueError):
            annotate_deltas(rows)

    def test_initialization_and_sample_stream_must_match(self):
        base = dict(fold='F0', seed=42, step=32000, role='dsm_student', eligible=True,
                    tiles=['a', 'b', 'c', 'd'], nb_fg5=60, gt_support={'nb': [10] * 6},
                    initial_state_sha256='init', sample_stream_sha256='stream')
        for field in ('initial_state_sha256', 'sample_stream_sha256'):
            rows = [dict(base, arm='D0'), dict(base, arm='DF', **{field: 'different'})]
            with self.assertRaises(ValueError):
                annotate_deltas(rows)

    def test_actual_record_layout_is_read_only_and_partial_rows_are_not_compared(self):
        workspace = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(prefix='interim_counts_fixture_', dir=str(workspace)) as name:
            base = Path(name).resolve()
            # Verify the owned fixture stays in tests before context cleanup.
            base.relative_to(workspace.resolve())
            def write(path, value):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding='utf-8')
            binding = {'plan.json': 'p', 'code_manifest.json': 'c', 'folds.json': 'f'}
            write(base / 'registration.json', {'binding': binding})
            write(base / 'folds.json', {'folds': {'F0': {'evaluation': ['a', 'b', 'c', 'd']}}})
            for arm in ('D0', 'DF'):
                identity = 'F0_s42_' + arm
                job = dict(id=identity, role='dsm_student', modality='dsm', fold='F0', seed=42, arm=arm)
                write(base / 'jobs' / identity / 'parameters.json', {'binding': binding, 'job': job})
                write(base / 'jobs' / identity / 'complete.json',
                      dict(binding=binding, job=identity, optimizer_updates=32000, checkpoint_sha256='0' * 64,
                           initial_state_sha256='same-init', batch_stream_sha256='same-stream'))
                cm = diagonal(1)
                if arm == 'DF':
                    cm[0][0], cm[0][1] = 0, 1
                for tile in ('a', 'b', 'c', 'd'):
                    write(base / 'trajectory_counts' / identity / ('32000_' + tile + '.json'),
                          {'metadata': dict(job=identity, step=32000, tile=tile),
                           'counts': {'nb': cm, 'full': cm}})
            before = {str(p.relative_to(base)): p.read_bytes() for p in base.rglob('*') if p.is_file()}
            result = collect(base, 32000)
            after = {str(p.relative_to(base)): p.read_bytes() for p in base.rglob('*') if p.is_file()}
            self.assertEqual(before, after)
            self.assertAlmostEqual(result['rows'][1]['delta_d0_nb_pp'], -30)
            (base / 'trajectory_counts/F0_s42_DF/32000_d.json').unlink()
            partial = collect(base, 32000)['rows'][1]
            self.assertFalse(partial['eligible'])
            self.assertIsNone(partial['nb_fg5'])
            self.assertIsNone(partial['delta_d0_nb_pp'])
            write(base / 'jobs/F0_s42_D0/complete.json', {})
            with self.assertRaises((KeyError, ValueError)):
                collect(base, 32000)


if __name__ == '__main__':
    unittest.main()
