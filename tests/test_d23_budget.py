import copy
import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'scripts/summarize_rebuild_v1_d23_budget.py'
spec=importlib.util.spec_from_file_location('budget',path)
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

def fixture():
    rows=[]
    for gpu in (0,1):
        sig=dict(gpu=gpu,uuid=str(gpu),test6_loaded=False,development_labels_loaded=False,sources={'x':'same'})
        rows.append(dict(status='ENGINE_BUDGET_COMPLETE',mode='budget',formal_training_started=False,
          formal_fit_statistics=False,signature=sig,train_fit_ids=list(map(str,range(12))),
          cache_measurement={str(i):{} for i in range(12)},budget_statistics_samples=256,
          cache_seconds=12,statistics_seconds=20,
          train={a:dict(train_steps=16,checkpoint_reload_equal=True,step_seconds=[100,100]+[.25]*14) for a in b.ARMS},
          evaluation={c:dict(seconds=10,shape=[6000,6000],
            results={n:dict(missing_logits_equal=True,prediction_sha256='same') for n in ('R0','M0_safe','confidence','entropy','logit_average','probability_average','TSF')}) for c in b.CONDITIONS}))
    return rows
class BudgetTests(unittest.TestCase):
    def test_full_cost_uses_cpu_step_worst_gpu_and_safety(self):
        rows=fixture();rows[1]['train']['TF']['step_seconds']=[100,100]+[.5]*14
        r=b.analyse(rows);self.assertEqual(r['train_4000_seconds'],2000)
        self.assertEqual(r['two_tile_14_condition_eval_allowance_seconds'],560)
        self.assertEqual(r['estimated_job_wall_seconds'],4188)
        self.assertFalse(r['formal_runtime_admitted'])
    def test_incomplete_arm_tile_condition_or_stats_rejected(self):
        for field in ('train','cache_measurement','evaluation'):
            rows=fixture();rows[0][field].pop(next(iter(rows[0][field])))
            with self.assertRaises(ValueError):b.analyse(rows)
        rows=fixture();rows[0]['budget_statistics_samples']=32
        with self.assertRaises(ValueError):b.analyse(rows)
    def test_phase_source_and_uuid_mismatch_rejected(self):
        rows=fixture();rows[1]['signature']['sources']['x']='changed'
        with self.assertRaises(ValueError):b.analyse(rows)
        rows=fixture();rows[1]['signature']['uuid']='0'
        with self.assertRaises(ValueError):b.analyse(rows)
        rows=fixture();rows[0]['signature']['development_labels_loaded']=True
        with self.assertRaises(ValueError):b.analyse(rows)
    def test_nonfinite_time_or_fallback_failure_rejected(self):
        rows=fixture();rows[0]['train']['T0']['step_seconds'][4]=float('nan')
        with self.assertRaises(ValueError):b.analyse(rows)
        rows=fixture();rows[1]['evaluation']['aux_zero']['results']['TSF']['missing_logits_equal']=False
        with self.assertRaises(ValueError):b.analyse(rows)
    def test_nearest_rank_timing_and_warmup_exclusion(self):
        self.assertEqual(b.percentile([1,2,3,4,5],.95),5)
        self.assertEqual(b.analyse(fixture())['worst_step_p95_seconds'],.25)
if __name__=='__main__':unittest.main()
