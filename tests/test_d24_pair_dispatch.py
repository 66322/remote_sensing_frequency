import importlib.util
import json
from pathlib import Path
import unittest
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pair_objectives', ROOT/'scripts/d24_objectives.py')
obj = importlib.util.module_from_spec(spec)
spec.loader.exec_module(obj)

class Student(nn.Module):
    def __init__(self):
        super().__init__()
        self.logits = nn.Parameter(torch.tensor([0., 2., 0., 0., 0., 0.]).view(1,6,1,1))
    def forward(self, rgb, aux, available, return_parts=False):
        logits = self.logits.expand(len(rgb),6,*rgb.shape[-2:])
        return logits,logits,logits,logits

class Teacher(nn.Module):
    def forward(self, rgb, aux):
        x=torch.zeros(len(rgb),6,*rgb.shape[-2:]);x[:,0]=8
        return x

class PairDispatchTests(unittest.TestCase):
    def setUp(self):
        self.plan=json.loads((ROOT/'records/research_d24_overnight_plan_20261001/plan.json').read_text(encoding='utf-8'))
        self.jobs={j['id']:j for j in self.plan['jobs']}
        rgb=torch.zeros(2,3,2,2);aux=torch.zeros(2,2,2)
        self.batch=dict(rgb=rgb,rgb2=rgb,aux=aux,aux2=aux,mask2=torch.ones_like(aux,dtype=torch.bool),gt=torch.zeros(2,2,2,dtype=torch.long))
    def test_actual_plan_pair_names_change_loss_and_gradient(self):
        for pair,control in [('A1','A0'),('A3','A2')]:
            with self.subTest(pair=pair):
                a,b=Student(),Student()
                la,_,_,ca=obj.step_objective(a,{'R0':Teacher()},self.jobs[pair],self.batch,self.plan,mixed=False)
                lb,_,_,cb=obj.step_objective(b,{'R0':Teacher()},self.jobs[control],self.batch,self.plan,mixed=False)
                expected=self.plan['pair']['weight']*ca['Pair:penalty_sum']
                self.assertGreater(expected,0)
                self.assertAlmostEqual(float((la-lb).detach()),expected,places=6)
                la.backward();lb.backward()
                self.assertFalse(torch.allclose(a.logits.grad,b.logits.grad))
                self.assertEqual(ca['Pair:enabled_steps'],1)
                self.assertEqual(cb['Pair:enabled_steps'],0)
    def test_unknown_route_a_objective_rejected(self):
        job=dict(self.jobs['A3'],objective='typo')
        with self.assertRaises(ValueError):
            obj.step_objective(Student(),{'R0':Teacher()},job,self.batch,self.plan,mixed=False)

if __name__=='__main__':unittest.main()
