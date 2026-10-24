"""Exact accelerated scientific result equality, including invalid/empty supports."""
import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase15_numeric as old
from phase15_fast_counts import fast_evidence,fast_oracle_evidence


class Equivalence(unittest.TestCase):
    def test_takeover_stage_and_resource_guards(self):
        from accelerate_phase15 import assert_stage,choose_workers
        state=dict(status='CPU_ORACLE_AND_CONDITIONAL_COUNTS',jobs={str(i):dict(status='COMPLETE') for i in range(100)})
        assert_stage(state)
        state['jobs']['0']['status']='RUNNING'
        with self.assertRaises(RuntimeError):assert_stage(state)
        state['jobs']['0']['status']='COMPLETE';state['status']='SMOKE_GPU0'
        with self.assertRaises(RuntimeError):assert_stage(state)
        gb=1024**3
        self.assertEqual(choose_workers(4,80*gb,2),2)
        self.assertEqual(choose_workers(4,32*gb,16),2)
        self.assertEqual(choose_workers(4,21*gb,16),1)
        with self.assertRaises(RuntimeError):choose_workers(2,19*gb,16)
    def test_all_oracle_fields_exact(self):
        rng=np.random.default_rng(6013)
        for shape in ((17,19),(129,133),(260,257)):
            gt=rng.integers(0,7,shape,dtype=np.uint8);gt[gt==6]=255
            clean=rng.integers(0,6,shape,dtype=np.uint8)
            preds=[rng.integers(0,6,shape,dtype=np.uint8) for _ in range(5)]
            entropy=rng.integers(0,4,shape,dtype=np.uint8)
            for mode in ('empty','full','pixel','rectangle'):
                mask=np.zeros(shape,bool)
                if mode=='full':mask[:]=True
                if mode=='pixel':mask[:]=rng.random(shape)<.25
                if mode=='rectangle':mask[2:-3,4:-4]=True
                bins={'dsm_mean':rng.integers(0,4,shape,dtype=np.uint8),'rgb_zero_fraction':entropy}
                expected=old.oracle_evidence(gt,clean,preds,mask,entropy,bins)
                actual=fast_oracle_evidence(gt,clean,preds,mask,entropy,bins)
                self.assertEqual(actual,expected,(shape,mode))
    def test_invalid_prediction_rejected(self):
        gt=np.zeros((4,4),np.uint8);bad=gt.copy();bad[0,0]=255
        with self.assertRaises(ValueError):fast_evidence(gt,gt,bad,{'all':np.ones_like(gt,bool)})
    def test_complete_agreement_and_absent_bins(self):
        gt=np.zeros((17,19),np.uint8);mask=np.ones_like(gt,bool)
        self.assertEqual(old.oracle_evidence(gt,gt,[gt]*5,mask,gt,{}),
            fast_oracle_evidence(gt,gt,[gt]*5,mask,gt,{}))


if __name__=='__main__':unittest.main()
