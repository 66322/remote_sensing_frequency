import copy
import hashlib
import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import d23_engine as e
import d23_lifecycle as life
import summarize_rebuild_v1_d23 as s


def fixture(no_reference_rescue=False):
    gt=np.tile(np.arange(6,dtype=np.uint8),100).reshape(20,30)
    ref=gt.copy();ref.flat[:60]=(ref.flat[:60]+1)%6
    m0=ref.copy() if no_reference_rescue else gt.copy()
    if not no_reference_rescue:m0.flat[60:120]=(m0.flat[60:120]+1)%6
    sig={field:0 for field in ('experts','sources','base_sha256','split_sha256','input_manifest_sha256','torch_version',
                             'matmul_allow_tf32','cudnn_allow_tf32','expert_micro_batch','gate_batch','backward_calls_per_step')}
    summaries={}
    for arm in s.ARMS:
        summary=dict(test6_loaded=False,independent_final_loaded=False,signature={'training':sig},tiles={},pooled={})
        candidate=gt.copy()
        if arm in ('T0','TCAP'):candidate=ref.copy()
        elif arm!='TSF':candidate.flat[:6]=(candidate.flat[:6]+1)%6
        for cond in e.CONDITIONS:
            mask=np.ones_like(gt,dtype=bool)
            if cond=='aux_zero':mask[:]=False
            elif cond in ('aux_local_zero_q1','aux_local_zero_stripe_eighth'):mask[2:4]=False
            preds={name:(m0.copy() if name=='M0_safe' else ref.copy()) for name in e.FIXED};preds[arm]=candidate.copy()
            for pred in preds.values():pred[~mask]=ref[~mask]
            tiles={}
            for tile in ('3_11','5_10'):
                tiles[tile]={name:dict(scopes={scope:e.count_result(gt,pred,ref,mask) for scope in ('full','noboundary')},
                      prediction_sha256=hashlib.sha256(pred.tobytes()).hexdigest(),missing_logits_equal=True) for name,pred in preds.items()}
            summary['tiles'][cond]=tiles
            summary['pooled'][cond]={name:{scope:life.pool([tiles[t][name]['scopes'][scope] for t in tiles]) for scope in ('full','noboundary')} for name in preds}
        summaries[arm]=summary
    return summaries


class ScreenTests(unittest.TestCase):
    def test_positive_fixture_and_mechanism_failure(self):
        data=fixture();result=s.screen(data)
        self.assertTrue(result['eligible_to_plan_confirmation'])
        # Candidate/TS comparison, not just beating a weak fixed baseline, is required.
        data['TS']['pooled']['clean']['TS']['noboundary']['mIoU_fg5']=1.
        with self.assertRaisesRegex(RuntimeError,'recomputation'):s.screen(data)

    def test_missing_arm_baseline_mismatch_and_na(self):
        data=fixture();bad=copy.deepcopy(data);del bad['TF']
        with self.assertRaises(RuntimeError):s.screen(bad)
        data['TF']['tiles']['clean']['3_11']['R0']['prediction_sha256']='different'
        with self.assertRaisesRegex(RuntimeError,'baseline differs'):s.screen(data)
        result=s.screen(fixture(True))
        self.assertIsNone(result['rescue_retention_ratio'])
        self.assertIsNone(result['checks']['rescue_retention'])
        self.assertFalse(result['eligible_to_plan_confirmation'])

if __name__=='__main__':unittest.main()
