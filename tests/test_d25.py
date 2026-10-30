"""Behavioral checks of D25 treatments, gradients, bindings and queue contracts."""
import copy
import json
from pathlib import Path
import sys
import unittest
import torch
from torch import nn
from torch.nn import functional as F

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from model.rebuild_v1_d25 import D25Segmenter
from model.rebuild_v1_d24 import D24Segmenter
from model.rebuild_v1_d21_detail import DetailDinoSegmenter
from d25_common import validate_plan
from d25_objectives import partition_ce,objective,backward,transform_shared
from d24_objectives import ce,verify_gradients
from d25_treatments import treatment,EXTRA
from d24_data import views
from launch_rebuild_v1_d25 import FILES,next_job
from summarize_rebuild_v1_d25 import build_screen
from d25_evaluation import FixedView

torch.set_num_threads(1)

class FakeEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.embed=nn.Conv2d(3,384,14,14)
        self.blocks=nn.ModuleList([nn.Linear(384,384) for _ in range(8)])
        self.norm=nn.LayerNorm(384)
    def forward_features(self,x):
        z=self.embed(x).flatten(2).transpose(1,2)
        for block in self.blocks:z=z+torch.tanh(block(z))
        return {'x_norm_patchtokens':self.norm(z)}

class D25Tests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(42)
        self.plan=json.loads((ROOT/'records/research_d25_plan_20261002/plan.json').read_text(encoding='utf-8'))
        self.state=DetailDinoSegmenter(FakeEncoder(),'M0').state_dict()
    def inputs(self):
        rgb=torch.rand(2,3,31,29);aux=torch.rand(2,31,29)
        gt=torch.randint(0,6,(2,31,29));gt[:,0,:]=255
        mask=torch.ones_like(aux,dtype=torch.bool);mask[0,6:26,5:25]=False;mask[1]=False
        return dict(rgb=rgb,aux=aux,gt=gt,rgb2=rgb*.8,aux2=aux.masked_fill(~mask,0),mask2=mask)
    def model(self,mode='shared',optical=False):
        m=D25Segmenter(FakeEncoder(),mode,optical);m.initialize(self.state)
        return m.train()

    def test_plan_freezes_eight_jobs_snapshots_and_device_queue(self):
        jobs=validate_plan(self.plan)
        self.assertTrue(all((ROOT/p).is_file() for p in FILES))
        state={'jobs':{j['id']:{'status':'PENDING'} for j in jobs}}
        self.assertEqual(next_job(jobs,state,0)['id'],'P0')
        self.assertEqual(next_job(jobs,state,1)['id'],'P1')
        wrong=copy.deepcopy(self.plan);wrong['jobs'][1]['pair']=False
        with self.assertRaises(ValueError):validate_plan(wrong)
        wrong=copy.deepcopy(self.plan);wrong['data']['test6_loaded']=True
        with self.assertRaises(ValueError):validate_plan(wrong)

    def test_all_initial_full_and_optical_predictions_match_same_M0(self):
        batch=self.inputs();mask=torch.ones_like(batch['aux'],dtype=torch.bool)
        old=D24Segmenter(FakeEncoder(),last4=True);old.load_state_dict(self.state)
        expected=old(batch['rgb'],batch['aux'],mask,return_parts=True)
        for mode in ('shared','separate','average'):
            m=self.model(mode)
            parts=m(batch['rgb'],batch['aux'],mask,return_parts=True)
            self.assertTrue(torch.equal(parts[0],expected[0]))
            self.assertTrue(torch.equal(parts[1],expected[1]))
        optical=self.model(optical=True)
        self.assertTrue(torch.equal(optical(batch['rgb'],batch['aux']),expected[1]))

    def test_pixel_mask_fallback_and_optical_invariance(self):
        b=self.inputs()
        for mode in ('shared','separate','average'):
            m=self.model(mode)
            parts=m(b['rgb2'],b['aux2'],b['mask2'],return_parts=True)
            self.assertTrue(torch.equal(parts[0].permute(0,2,3,1)[~b['mask2']],
                                        parts[1].permute(0,2,3,1)[~b['mask2']]))
            with self.assertRaises(ValueError):m(b['rgb'],b['aux'])
        m=self.model(optical=True)
        self.assertTrue(torch.equal(m(b['rgb'],b['aux']),m(b['rgb'],b['aux']*0)))

    def test_partition_keeps_full_valid_denominator_and_empty_missing(self):
        a=torch.randn(2,6,3,4,requires_grad=True)
        b=torch.randn_like(a,requires_grad=True)
        gt=torch.randint(0,6,(2,3,4));gt[0,0,0]=255
        for mask in (torch.ones_like(gt,dtype=torch.bool),torch.zeros_like(gt,dtype=torch.bool),gt%2==0):
            p,m,c=partition_ce(a,b,gt,mask)
            self.assertTrue(torch.allclose(p+m,.5*(ce(a,gt)+ce(b,gt)),atol=1e-7))
            ga=torch.autograd.grad(p+m,(a,b),retain_graph=True)
            gb=torch.autograd.grad(.5*(ce(a,gt)+ce(b,gt)),(a,b),retain_graph=True)
            self.assertTrue(all(torch.allclose(x,y,atol=1e-8) for x,y in zip(ga,gb)))
        gt.fill_(255);p,m,c=partition_ce(a,b,gt,gt==0)
        self.assertEqual(float(p+m),0.)

    def test_projection_and_norm_sham_direction_nonconflict_and_zero(self):
        gp=[torch.tensor([1.,0.])];gm=[torch.tensor([-1.,2.])]
        projected,stats=transform_shared(gp,gm,'project')
        sham,_=transform_shared(gp,gm,'norm_sham')
        self.assertTrue(torch.allclose(projected[0],torch.tensor([0.,2.])))
        self.assertAlmostEqual(float(sham[0].norm()),float(projected[0].norm()),places=6)
        self.assertLess(float((gp[0]*sham[0]).sum()),0)
        self.assertEqual(stats['conflict'],1)
        for g in ([torch.zeros(2)],[torch.tensor([1.,2.])]):
            changed,_=transform_shared(gp,g,'project')
            self.assertTrue(torch.equal(changed[0],g[0]))
        for mode in ('project','norm_sham'):
            changed,stats=transform_shared([torch.zeros(2)],[torch.zeros(2)],mode)
            self.assertTrue(torch.equal(changed[0],torch.zeros(2)))
        with self.assertRaises(ValueError):transform_shared(gp,gm,'unknown')

    def test_plain_gradient_equals_original_ce_and_all_eight_paths_update(self):
        b=self.inputs()
        teacher=DetailDinoSegmenter(FakeEncoder(),'R0').eval().requires_grad_(False)
        for job in self.plan['jobs']:
            with self.subTest(job=job['id']):
                m=self.model(job['decoder_mode'],job['optical_only'])
                p,q,c=objective(m,{'R0':teacher},job,b,self.plan,mixed=False)
                stats=backward(m,p,q,job['gradient_mode'],True)
                verify_gradients(m,[teacher])
                if job['decoder_mode'] in ('separate','average'):
                    self.assertTrue(stats['decoder_optical.gradient_nonzero'])
                    self.assertTrue(stats['decoder.gradient_nonzero'])
                if job['decoder_mode']=='separate':
                    self.assertFalse(any(n.startswith('decoder') for n in stats['shared_parameters']))
                if job['id']=='P6':self.assertEqual(c['missing_pixels'],0)
                self.assertEqual(c['Pair:enabled_steps'],int(job['pair']))
        m=self.model();clone=copy.deepcopy(m)
        j=self.plan['jobs'][0]
        p,q,c=objective(m,{},j,b,self.plan,mixed=False);backward(m,p,q,'none',True)
        p,q,c=objective(clone,{},j,b,self.plan,mixed=False);(p+q).backward()
        for (n,a),(n2,bp) in zip(m.named_parameters(),clone.named_parameters()):
            if a.grad is not None:self.assertTrue(torch.allclose(a.grad,bp.grad,atol=1e-7,rtol=1e-5),n)

    def test_exclusive_decoders_and_detail_have_no_missing_gradient(self):
        b=self.inputs();m=self.model('separate')
        j=next(x for x in self.plan['jobs'] if x['id']=='P2')
        p,q,_=objective(m,{},j,b,self.plan,mixed=False)
        named=[(n,x) for n,x in m.named_parameters() if x.requires_grad]
        grads=torch.autograd.grad(q,[x for _,x in named],allow_unused=True)
        for (n,x),g in zip(named,grads):
            if n.startswith(('decoder.','detail.')):
                self.assertTrue(g is None or float(g.abs().sum())==0,n)
        self.assertTrue(any(g is not None and float(g.abs().sum())>0
                            for (n,x),g in zip(named,grads) if n.startswith('decoder_optical.')))

    def test_pair_actual_P1_changes_loss_and_gradients(self):
        class Toy(nn.Module):
            def __init__(self):super().__init__();self.logits=nn.Parameter(torch.zeros(1,6,2,3))
            def forward(self,rgb,aux,available=None,return_parts=False):
                z=self.logits.expand(len(rgb),-1,-1,-1)
                return (z,z,None,None) if return_parts else z
        class Teacher(nn.Module):
            def forward(self,rgb,aux):
                z=torch.zeros(len(rgb),6,2,3);z[:,0]=5
                return z
        b=dict(rgb=torch.zeros(1,3,2,3),rgb2=torch.zeros(1,3,2,3),aux=torch.zeros(1,2,3),
               aux2=torch.zeros(1,2,3),mask2=torch.ones(1,2,3,dtype=torch.bool),gt=torch.zeros(1,2,3,dtype=torch.long))
        base,pair=Toy(),Toy()
        p,m,_=objective(base,{},self.plan['jobs'][0],b,self.plan,mixed=False)
        loss=p+m;loss.backward()
        p,m,c=objective(pair,{'R0':Teacher()},self.plan['jobs'][1],b,self.plan,mixed=False)
        added=p+m;added.backward()
        self.assertGreater(float(added-loss),0.)
        self.assertAlmostEqual(float(added-loss),c['Pair:weighted_loss_sum'],places=6)
        self.assertFalse(torch.equal(base.logits.grad,pair.logits.grad))

    def test_pressure_treatments_and_same_Q_rgb_for_optical_control(self):
        op=torch.rand(1,3,31,29);ds=torch.arange(899).reshape(1,31,29).float()/899
        for condition in EXTRA:
            x,y,mask=treatment(op,ds,condition,123)
            self.assertEqual(x.shape,op.shape);self.assertEqual(y.shape,ds.shape)
            self.assertEqual(mask.dtype,torch.bool)
            if condition=='rgb_down4+aux_zero':self.assertFalse(bool(mask.any()));self.assertEqual(float(y.sum()),0)
            if condition=='aux_local_zero_center_quarter':
                self.assertFalse(bool(mask[:,3*31//8:5*31//8].any()))
                self.assertTrue(bool(mask[:,:3*31//8].all()))
            if condition=='aux_shift24':
                self.assertTrue(torch.equal(y[:,:,24:],ds[:,:,:5]))
                self.assertTrue(torch.equal(y[:,:,:24],ds[:,:,:1].expand(-1,-1,24)))
        a=views(op[0],ds[0],'QD',7,4);b=views(op[0],ds[0],'Q',7,4)
        self.assertTrue(torch.equal(a[0],b[0]))

    def test_resume_state_preserves_both_decoders_optimizer_and_rng(self):
        m=self.model('separate');optimizer=torch.optim.AdamW([p for p in m.parameters() if p.requires_grad],lr=.001)
        b=self.inputs();j=next(x for x in self.plan['jobs'] if x['id']=='P3')
        p,q,_=objective(m,{},j,b,self.plan,mixed=False);backward(m,p,q,'project',True);optimizer.step()
        state=copy.deepcopy(m.state_dict());opt=copy.deepcopy(optimizer.state_dict())
        clone=self.model('separate');clone.load_state_dict(state,strict=True)
        other=torch.optim.AdamW([p for p in clone.parameters() if p.requires_grad],lr=.001);other.load_state_dict(opt)
        for model,optim in ((m,optimizer),(clone,other)):
            optim.zero_grad();p,q,_=objective(model,{},j,b,self.plan,mixed=False)
            backward(model,p,q,'project',True);optim.step()
        self.assertTrue(all(torch.equal(v,clone.state_dict()[k]) for k,v in m.state_dict().items()))

    def test_screen_uses_missing_floors_and_ignores_pressure_for_selection(self):
        def summary(value):
            conditions=self.plan['evaluation']['conditions']
            row={'mIoU_fg5':value,'available':{'harm':4,'rescue':8,'valid':100}}
            pooled={c:{'candidate':{'noboundary':copy.deepcopy(row)}} for c in conditions}
            tiles={c:{t:{'results':{'candidate':{'noboundary':copy.deepcopy(row)}}}
                      for t in self.plan['data']['validation']} for c in conditions}
            return {'pooled':pooled,'tiles':tiles}
        values={'P0':.88,'P1':.883,'P2':.883,'P3':.886,'P4':.883,'P5':.88,'P6':.88,'P7':.883}
        summaries={j:summary(v) for j,v in values.items()}
        completes={j:{'selected':{'step':2000},'treatment_counts':{'Pair:enabled_steps':4000 if j=='P1' else 0}}
                   for j in values}
        result=build_screen(self.plan,{},summaries,completes)
        self.assertTrue(result['mechanism_screen']['H1_separate_decoders'])
        self.assertTrue(result['mechanism_screen']['H2_projection_separate'])
        self.assertTrue(result['mechanism_screen']['Pair_corrected'])
        for c in self.plan['evaluation']['pressure_diagnostics']:
            summaries['P2']['pooled'][c]['candidate']['noboundary']['mIoU_fg5']=0.
        result=build_screen(self.plan,{},summaries,completes)
        self.assertTrue(result['mechanism_screen']['H1_separate_decoders'])
        summaries['P2']['pooled']['aux_zero']['candidate']['noboundary']['mIoU_fg5']=.87
        result=build_screen(self.plan,{},summaries,completes)
        self.assertFalse(result['mechanism_screen']['H1_separate_decoders'])
        del summaries['P7']
        result=build_screen(self.plan,{},summaries,completes)
        self.assertIsNone(result['mechanism_screen']['H2_projection_separate'])

    def test_new_pressure_fixed_reference_uses_R0_fallback(self):
        b=self.inputs()
        r0=DetailDinoSegmenter(FakeEncoder(),'R0').eval()
        m0=DetailDinoSegmenter(FakeEncoder(),'M0').eval()
        wrapper=FixedView({'R0':r0,'M0':m0})
        with torch.no_grad():
            safe,own,_,_=wrapper(b['rgb2'],b['aux2'],b['mask2'],return_parts=True)
            expected=torch.where(b['mask2'][:,None],m0(b['rgb2'],b['aux2']),r0(b['rgb2'],b['aux2']))
        self.assertTrue(torch.equal(safe,expected))
        self.assertTrue(torch.equal(own,r0(b['rgb2'],b['aux2'])))

if __name__=='__main__':unittest.main()
