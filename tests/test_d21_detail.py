"""CPU contract tests with a tiny encoder substitute, no pretrained/data downloads."""
import copy
from pathlib import Path
import sys
import unittest
import torch
from torch import nn
from torch.nn import functional as F
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'scripts'))
from model.rebuild_v1_night_screen import FrozenDinoSegmenter
from model.rebuild_v1_d21_detail import DetailDinoSegmenter, detail_channels, ARMS
import d21_common as p
from analyze_rebuild_v1_d21 import metric, decision

torch.set_num_threads(2)


class TinyEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.projection=nn.Conv2d(3,384,1)

    def forward_features(self,x):
        x=self.projection(F.avg_pool2d(x,14,14))
        return dict(x_norm_patchtokens=x.flatten(2).transpose(1,2))


class Contracts(unittest.TestCase):
    def test_matched_reference_and_initialization(self):
        encoder=TinyEncoder()
        rgb,aux=torch.rand(1,3,32,44),torch.rand(1,32,44)
        for arm,enabled in [('R0',False),('R1',True)]:
            torch.manual_seed(42)
            old=FrozenDinoSegmenter(copy.deepcopy(encoder),enabled).eval()
            torch.manual_seed(42)
            new=DetailDinoSegmenter(copy.deepcopy(encoder),arm).eval()
            self.assertTrue(torch.equal(old(rgb,aux),new(rgb,aux)))
        torch.manual_seed(42)
        base=DetailDinoSegmenter(copy.deepcopy(encoder),'R0')
        counts=[]
        for arm in ARMS[2:]:
            torch.manual_seed(42)
            net=DetailDinoSegmenter(copy.deepcopy(encoder),arm)
            for name,weight in base.state_dict().items():
                self.assertTrue(torch.equal(weight,net.state_dict()[name]),name)
            counts.append(sum(x.numel() for x in net.parameters() if x.requires_grad))
        self.assertEqual(len(set(counts)),1)

    def test_frequency_reconstruction_and_alignment_control(self):
        aux=torch.rand(2,35,43)
        raw=detail_channels(aux,'M0')[:,0]
        frequency=detail_channels(aux,'F2')
        self.assertTrue(torch.allclose(frequency.sum(1),raw,atol=1e-7))
        shuffled=detail_channels(aux,'F3')
        self.assertTrue(torch.equal(shuffled[:,0],frequency[:,0]))
        self.assertTrue(torch.equal(shuffled[:,1].flatten(1).sort().values,frequency[:,1].flatten(1).sort().values))
        self.assertFalse(torch.equal(shuffled[:,1],frequency[:,1]))
        constant=detail_channels(torch.ones_like(aux)*.25,'F2')
        self.assertTrue(torch.equal(constant[:,1],torch.zeros_like(constant[:,1])))

    def test_all_arms_backward_and_reload(self):
        rgb,aux=torch.rand(2,3,32,44),torch.rand(2,32,44)
        for arm in ARMS:
            net=DetailDinoSegmenter(TinyEncoder(),arm).train()
            self.assertFalse(net.encoder.training)
            loss=net(rgb,aux).square().mean()
            loss.backward()
            self.assertTrue(all(x.grad is None for x in net.encoder.parameters()))
            self.assertTrue(any(x.grad is not None and torch.isfinite(x.grad).all() and x.grad.abs().sum()>0 for x in net.decoder.parameters()))
            if net.detail is not None:
                self.assertTrue(any(x.grad is not None and x.grad.abs().sum()>0 for x in net.detail.parameters()))
            net.eval()
            other=DetailDinoSegmenter(TinyEncoder(),arm).eval()
            other.load_state_dict(net.state_dict(),strict=True)
            with torch.no_grad():
                pred=net(rgb,aux)
                self.assertEqual(pred.shape,(2,6,32,44))
                self.assertTrue(torch.equal(pred,other(rgb,aux)))
                if arm == 'R0':
                    self.assertTrue(torch.equal(pred,net(rgb,aux*0)))

    def test_plan_and_count_audit(self):
        jobs=p.jobs()
        self.assertEqual(len(jobs),32)
        self.assertEqual(len({p.key(job) for job in jobs}),32)
        self.assertEqual([job['seed'] for job in jobs[:16]],[42]*16)
        p.datasets()
        cm=[[0]*6 for _ in range(6)]
        for c in range(6):
            cm[c][c]=10
        cm[0][1]=10
        self.assertAlmostEqual(metric(cm),.8)
        cm[0][0]=-1
        with self.assertRaises(ValueError):
            metric(cm)

    def test_pooled_gain_cannot_hide_tile_or_missing_aux_failure(self):
        def row(correct):
            cm=[[0]*6 for _ in range(6)]
            for c in range(6):
                cm[c][c]=correct
                cm[c][(c+1)%6]=100-correct
            return dict(cm=cm)
        def summary(correct):
            return dict(conditions={c:dict(pooled={'noboundary':row(correct)},
                tiles={str(t):dict(scopes={'noboundary':row(correct)})
                       for t in p.datasets()['potsdam']['dev']})
                for c in p.config()['evaluation_conditions']})
        arms={arm:summary(70) for arm in ARMS}
        arms['F2']=summary(90)
        self.assertTrue(decision(arms,'potsdam')['development_accuracy_gate_passed'])
        self.assertTrue(decision(arms,'potsdam')['missing_aux_safety_passed'])
        bad_tile=str(p.datasets()['potsdam']['dev'][0])
        arms['F2']['conditions']['clean']['tiles'][bad_tile]['scopes']['noboundary']=row(60)
        arms['F2']['conditions']['aux_zero']['pooled']['noboundary']=row(20)
        result=decision(arms,'potsdam')
        self.assertGreater(result['candidate_macro_gain_pp'],.2)
        self.assertFalse(result['development_accuracy_gate_passed'])
        self.assertFalse(result['missing_aux_safety_passed'])


if __name__ == '__main__':
    unittest.main()
