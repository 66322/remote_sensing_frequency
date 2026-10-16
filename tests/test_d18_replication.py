"""Small protocol checks that do not require server imagery or CUDA."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import d18_replication as p


class ReplicationTests(unittest.TestCase):
    def test_seed17_paths_and_frozen_evaluation_seed(self):
        rep,cfg=p.validate()
        self.assertEqual(rep['training_seed'],17)
        self.assertEqual(rep['evaluation_corruption_seed'],42)
        self.assertEqual(rep['historical_r01_reference_seed'],42)
        self.assertEqual(cfg['pretrained_steps'],8000)
        for arm in p.ARMS:
            self.assertIn('seed17',str(p.output(arm)))
            self.assertIn('seed17',str(p.evaluation_output(arm)))
            self.assertNotEqual(p.output(arm),p.original.output(arm,42))
        with self.assertRaises(ValueError):
            p.output('P2',42)

    def test_binding_identifies_new_training_seed_and_original_anchor(self):
        historical=dict(split_sha256='split',base_config_sha256='base',
                        anchor_sha256='weights',dino_commit='commit',
                        torch_version='torch',sources={'old':'sha'})
        with patch.object(p.original,'binding',return_value=historical):
            signature=p.binding('P2',False)
        self.assertEqual(signature['seed'],17)
        self.assertEqual(signature['anchor_sha256'],'weights')
        self.assertEqual(signature['original_sources'],{'old':'sha'})
        self.assertIn('scripts/eval_rebuild_v1_d18_replication.py',signature['replication_sources'])

    def test_paired_errors_and_explicit_missing_fallback(self):
        gt=np.array([[0,1,4,255],[0,1,4,5],[0,1,4,5],[0,1,4,5]],dtype=np.uint8)
        p0=np.array([[0,0,4,3],[0,1,0,5],[1,1,4,5],[0,1,4,5]],dtype=np.uint8)
        p2=np.array([[1,1,4,3],[0,1,4,5],[0,0,4,5],[0,1,4,5]],dtype=np.uint8)
        got=p.paired_counts(gt,p0,p2,np.ones_like(gt,dtype=bool))
        self.assertEqual(got['valid'],15)
        self.assertEqual(got['only_p0_correct'],2)
        self.assertEqual(got['only_candidate_correct'],3)
        self.assertEqual(sum(got[k] for k in ('both_correct','only_p0_correct','only_candidate_correct','both_wrong')),15)
        absent=p.availability('aux_zero',gt.shape)
        self.assertTrue(np.array_equal(np.where(absent,p2,p0),p0))
        local=p.availability('aux_local_zero_q1',gt.shape)
        self.assertEqual(int((~local).sum()),4)
        self.assertEqual(p.paired_counts(gt,p0,p2,~local)['valid'],4)


if __name__=='__main__':
    unittest.main()
