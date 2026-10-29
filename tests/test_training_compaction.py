"""Exercise all 108 trace receipts before allowing their retirement."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np

spec = importlib.util.spec_from_file_location('compact_training',Path(__file__).resolve().parents[1]/'scripts/compact_phase3_m2.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class TrainingChecks(unittest.TestCase):
    def test_all_training_and_batch_receipts_without_new_hashing(self):
        with tempfile.TemporaryDirectory(prefix='m2_owned_trace_fixture_') as tmp:
            p = Path(tmp)
            cm = (np.eye(6,dtype=np.int64)*10).tolist()
            batches = ''.join(json.dumps(dict(step=i,hash='a'*64))+'\n' for i in range(1,32001))
            for fold in ('F0','F1','F2'):
                for seed in m.SEEDS:
                    for arm in ('R','T0','T1','T2','T3')+m.ARMS:
                        job = fold+'_s'+str(seed)+'_'+arm
                        folder = p/'jobs'/job
                        folder.mkdir(parents=True)
                        (folder/'complete.json').write_text(json.dumps(dict(batch_stream_sha256='existing_receipt_only')))
                        (folder/'batch_hashes.jsonl').write_text(batches)
                        rows = [dict(step=s,loss=.5,gradient_norm=2.,elapsed_seconds=60.,stable_sec_per_update=.1) for s in (1,32000)]
                        (folder/'trajectory.jsonl').write_text('\n'.join(json.dumps(z) for z in rows)+'\n')
                        tc = p/'trajectory_counts'/job
                        tc.mkdir(parents=True)
                        for age in (8000,16000,24000,32000):
                            for tile in range(4):
                                (tc/(str(age)+'_'+str(tile)+'.json')).write_text(json.dumps(dict(metadata=dict(job=job,step=age,tile=tile),counts=dict(nb=cm,full=cm))))
            summary = m.trajectories(p,p)
            self.assertEqual(summary['batch_stream_receipts'],108)
            self.assertEqual(summary['training_trace_rows'],108)
            self.assertEqual(summary['dsm_age_deltas'][3]['DSM_DF_minus_D0_miou_pp'],[0.,0.,0.])
            self.assertIn('existing_receipt_only',(p/'batch_stream_receipts.csv').read_text())
            # Input traces remain until the separate destructive phase.
            self.assertEqual(len(list((p/'jobs').glob('*/batch_hashes.jsonl'))),108)


if __name__ == '__main__':
    unittest.main()
