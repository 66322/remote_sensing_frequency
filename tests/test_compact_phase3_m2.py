"""Affected-scope numeric and retention-policy checks; no server deletion test."""
import copy
import gzip
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compact', HERE/'scripts/compact_phase3_m2.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def counts():
    # All classes present. RGB makes one GT0->1 error; DSM fixes it but
    # introduces GT2->3. Primary fusion fixes it without introducing the latter.
    j = np.zeros((6, 6, 6), dtype=np.int64)
    f = j.copy()
    for g in range(6):
        j[g, g, g] = f[g, g, g] = 10
    j[0, 1, 0] = f[0, 1, 0] = 4
    j[2, 2, 3] = 3
    f[2, 2, 2] += 3
    cms = [j.sum(2).tolist(), f.sum(1).tolist(), f.sum(1).tolist(),
           f.sum(1).tolist(), f.sum(1).tolist(), f.sum(1).tolist(), j.sum(1).tolist()]
    row = dict(joint=j.tolist(), fusion_joint=f.tolist(), cms=cms, logit_cm=cms[0])
    cal = dict(count=[10]*15, correct=[8]*15, confidence=[9.]*15, nll_sum=30.)
    return dict(nb={r:copy.deepcopy(row) for r in m.REGIONS},
                full={r:copy.deepcopy(row) for r in m.REGIONS},
                aux={r:[cms[i] for i in (0, 6, 2)] for r in ('fulltile_nb', 'fulltile_full', 'boundary', 'interior')},
                margin_counts=[[0]*5, [1]*5, [2]*5, [2]*5, [2]*5, [2]*5, [2]*5],
                calibration={k:copy.deepcopy(cal) for k in ('rgb', 'dsm', 'fusion')})


class NumericChecks(unittest.TestCase):
    def test_actual_fusion_separate_from_dsm(self):
        z = m.capsule(counts())['nb']['all']
        self.assertEqual(z['dsm_flow'], [53, 4, 4, 3])
        self.assertEqual(z['fusion_flow'], [53, 4, 4, 0])
        self.assertEqual(m.rates(z['fusion_flow'])['net_correct_pixels'], 4)
        self.assertAlmostEqual(m.rates(z['dsm_flow'])['harm_pp'], 300/53)

    def test_class5_denominator_and_absent_class(self):
        cm = np.eye(6, dtype=np.int64)*10
        cm[5, 0] = 10
        self.assertEqual(m.metric(cm)[1][0], 50.)
        self.assertEqual(m.metric(cm)[0], 90.)
        cm[4] = 0
        self.assertIsNone(m.metric(cm)[0])

    def test_pool_preserves_integer_counts_and_float_calibration(self):
        z = m.capsule(counts())
        g = {}
        m.pool_into(g, 'k', z)
        m.pool_into(g, 'k', z)
        self.assertEqual(g['k']['nb']['all']['fusion_flow'].tolist(), [106, 8, 8, 0])
        self.assertAlmostEqual(g['k']['calibration']['rgb']['nll_sum'], 60.)
        self.assertEqual(z['nb']['all']['fusion_flow'], [53, 4, 4, 0])

    def test_gate_recomputation_and_changed_value_refusal(self):
        z = m.arrays(m.capsule(counts()))
        g = {(s,s,a,c):copy.deepcopy(z) for s in m.SEEDS for a in m.ARMS for c in m.CONDITIONS}
        gates = {'checks':{'G1_rescue_DF-D0':{'values_pp':[0.,0.,0.]},
                           'G2_fusion_DF-D0':{'values_pp':[0.,0.,0.]}}}
        summary = m.summarize(g, gates)
        self.assertEqual(summary['alpha_down4_diagnostic'][2]['alpha'], .1)
        gates['checks']['G2_fusion_DF-D0']['values_pp'][0] = .01
        with self.assertRaisesRegex(RuntimeError, 'disagrees'):
            m.summarize(g, gates)

    def test_exports_calibration_and_aux_scopes(self):
        with tempfile.TemporaryDirectory(prefix='m2_compact_numeric_') as tmp:
            p = Path(tmp)
            z = m.arrays(m.capsule(counts()))
            g = {(42,42,'DF','down4'):z}
            rows = m.export_tables(g, {('F0',42,42,'DF','down4'):z}, p)
            self.assertEqual(rows['alpha'], 42)
            self.assertEqual(rows['flow'], 12)
            self.assertEqual(rows['aux'], 12)
            import csv
            with (p/'calibration_margin.csv').open() as f:
                cal = list(csv.DictReader(f))
            self.assertAlmostEqual(float(cal[0]['value']), 10.)
            self.assertAlmostEqual(float(cal[1]['value']), .2)
            with gzip.open(p/'alpha_roi_class_metrics.csv.gz', 'rt') as f:
                self.assertEqual(len(list(csv.DictReader(f))),42)

    def test_incomplete_cases_stop_without_deleting_original(self):
        with tempfile.TemporaryDirectory(prefix='m2_compact_cases_') as tmp:
            p = Path(tmp)
            source = p/'case_counts.jsonl.gz'
            meta = dict(tile='2_12',fold='F0',rseed=42,dseed=42,arm='DF',condition='down4',family='pixel',realization=0)
            with gzip.open(source, 'wt') as f:
                f.write(json.dumps(dict(metadata=meta, counts=counts()))+'\n')
            with self.assertRaisesRegex(RuntimeError, 'coverage'):
                m.analyze_cases(p,p)
            self.assertTrue(source.exists())

    def test_complete_aggregate_coverage_and_roundtrip_capsule(self):
        # Exercise the actual reader and 6048-group coverage contract; tiny
        # synthetic CMs only, no model/data access and no deletion.
        with tempfile.TemporaryDirectory(prefix='m2_compact_aggregates_') as tmp:
            p = Path(tmp)
            encoded = json.dumps(counts(), separators=(',',':'))
            with gzip.open(p/'all_aggregates.jsonl.gz', 'wt', compresslevel=1) as f:
                for ti in range(12):
                    for r in m.SEEDS:
                        for d in m.SEEDS:
                            for arm in m.ARMS:
                                for cond in m.CONDITIONS:
                                    meta = dict(tile='tile'+str(ti),fold='F'+str(ti//4),rseed=r,dseed=d,arm=arm,condition=cond)
                                    cases = 20 if cond in m.CONDITIONS[1:6] else 1
                                    f.write('{"metadata":'+json.dumps(meta)+',"cases":'+str(cases)+',"counts":'+encoded+'}\n')
            groups, folds, coverage = m.analyze_aggregates(p,p)
            self.assertEqual(coverage['cases'],77868)
            self.assertEqual(len(groups),504)
            self.assertEqual(len(folds),504)
            self.assertEqual(groups[(42,42,'DF','down4')]['nb']['all']['fusion_flow'].tolist(),[636,48,48,0])
            with gzip.open(p/'tile_sufficient_counts.jsonl.gz', 'rt') as f:
                row = json.loads(next(f))
            self.assertNotIn('joint',row['counts']['nb']['all'])
            self.assertEqual(row['counts']['nb']['all']['fusion_flow'],[53,4,4,0])


class RetentionChecks(unittest.TestCase):
    def reason(self, path, run='m2_directory'):
        return m.candidate_reason(dict(relative=path,run=run))

    def test_remaining_weights_and_partial_checkpoints_selected(self):
        for p in ('jobs/F0_s42_R/endpoint.pth','jobs/F0_s42_D0/endpoint.pth','jobs/J2/last_resume.pth','jobs/J2/last_resume.tmp'):
            self.assertIsNotNone(self.reason(p))

    def test_only_bound_raw_stats_and_known_prediction_paths(self):
        self.assertEqual(self.reason('publication/F0_counts.jsonl.gz'), 'replaced_by_compact_statistics')
        self.assertIsNone(self.reason('publication/metrics.csv'))
        self.assertIsNone(self.reason('all_aggregates.jsonl.gz','old_m2'))
        self.assertIsNone(self.reason('unclassified/large.npy'))
        self.assertIsNotNone(self.reason('predictions/tile.npy'))

    def test_shared_inputs_code_and_necessary_small_records_kept(self):
        for p in ('pretrained/public.pth','data/tile.tif','code/models.pt','jobs/F0_s42_R/parameters.json',
                  'publication/summary.json','mask_design/frozen.json','trajectory_counts/job/8000_tile.json'):
            self.assertIsNone(self.reason(p),p)

    def test_full_batch_traces_replaced_but_small_receipts_kept(self):
        self.assertEqual(self.reason('jobs/F0_s42_R/batch_hashes.jsonl'), 'batch_trace_replaced_by_108_checked_receipts')
        self.assertIsNone(self.reason('jobs/F0_s42_R/complete.json'))
        self.assertIsNone(self.reason('jobs/F0_s42_R/batch_hashes.jsonl','old_m2'))


if __name__ == '__main__':
    unittest.main()
