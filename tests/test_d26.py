"""Behavioral CPU tests of actual model, treatment, metric and queue code."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from model.rebuild_v1_d26 import ARMS,D26Segmenter,Expert,Interaction,pack,unpack
from d26_common import validate_plan
from d26_data import treatment,views,objective
from d26_evaluation import counts,joint_counts,joint_report,infer,encode_joint,decode_joint,evaluate
from run_rebuild_v1_d26 import verify_gradients,optimizer_for
from summarize_rebuild_v1_d26 import pair_gate,protections,screen
from launch_rebuild_v1_d26 import next_job
torch.set_num_threads(1)

class Toy(nn.Module):
    def __init__(self,kind):
        super().__init__();self.kind=kind
        self.encoder=nn.Module();self.encoder.blocks=nn.ModuleList([nn.Conv2d(3,3,1) for _ in range(6)])
        self.transformer=nn.Module();self.transformer.encoder=nn.Module();self.transformer.encoder.layer=nn.ModuleList([nn.Conv2d(3,3,1) for _ in range(6)])
        self.rgb=nn.Conv2d(3,8,1)
        self.decoder=nn.Sequential(nn.Conv2d(8,8,3,padding=1),nn.BatchNorm2d(8),nn.GELU(),nn.Conv2d(8,6,1))
        self.segmentation_head=nn.Sequential(nn.Conv2d(6,6,1))
    def forward(self,rgb,ds=None):
        x=rgb
        blocks=self.encoder.blocks if self.kind=='rgb' else self.transformer.encoder.layer
        for block in blocks:x=block(x)
        x=self.rgb(x);x=self.decoder(x)
        return x if self.kind=='rgb' else self.segmentation_head(x)

def make(arm):
    torch.manual_seed(41);r=Toy('rgb');d=Toy('dsm')
    experts=(Expert(r,r.decoder[-1],'rgb'),Expert(d,d.segmentation_head[0],'dsm'))
    torch.manual_seed(42);return D26Segmenter(*experts,arm)

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.plan=json.loads((ROOT/'records/research_d26_plan_20261002/plan.json').read_text(encoding='utf-8'))
    def test_locked_plan_budget_split_selection(self):
        self.assertEqual(len(validate_plan(self.plan)),9)
        for mutator in (lambda p:p['training'].update(physical_batch=8),lambda p:p['data'].update(test6_loaded=True),lambda p:p['jobs'].pop(),lambda p:p['training'].update(validation_steps=[2000,8000])):
            p=copy.deepcopy(self.plan);mutator(p)
            with self.assertRaises(ValueError):validate_plan(p)
    def test_basis_inverse_energy_constant_and_gradients(self):
        x=torch.randn(2,5,15,17,requires_grad=True)
        for frequency in (False,True):
            y=pack(x,frequency);restored=unpack(y,x.shape[-2:],frequency)
            torch.testing.assert_close(restored,x,rtol=1e-5,atol=1e-6)
            torch.testing.assert_close(y.square().sum(),x.square().sum(),rtol=1e-5,atol=1e-5)
            restored.sum().backward(retain_graph=True)
        high=pack(torch.ones(1,4,8,8),True).reshape(1,4,4,4,4)[:,:,1:]
        self.assertEqual(float(high.abs().sum()),0.)
        self.assertTrue(torch.isfinite(x.grad).all())
    def test_all_arm_capacity_and_exact_common_initialization(self):
        models={arm:make(arm) for arm in ARMS}
        capacities={arm:sum(p.numel() for p in m.parameters() if p.requires_grad) for arm,m in models.items()}
        self.assertEqual(len({capacities[a] for a in ARMS[2:]}),1)
        self.assertGreater(capacities['J0'],capacities['B0'])
        for name,v in models['B0'].state_dict().items():
            if name.startswith(('project_rgb.','project_dsm.','fusion.')):
                for m in models.values():torch.testing.assert_close(m.state_dict()[name],v,rtol=0,atol=0)
    def test_bilateral_exact_fallback_masks_and_hidden_input_independence(self):
        op=torch.rand(2,3,32,36);ds=torch.rand(2,32,36)
        rm=torch.ones_like(ds,dtype=torch.bool);dm=rm.clone()
        rm[0,:,18:]=False;dm[0,:,:18]=False;rm[1,8:16,:]=False;dm[1,8:16,:]=False
        for arm in ARMS:
            m=make(arm).eval();out=m(op,ds,rm,dm,True)
            for mask,name in ((rm&~dm,'rgb'),(dm&~rm,'dsm')):
                torch.testing.assert_close(out['logits'].masked_select(mask[:,None]),out[name].masked_select(mask[:,None]),rtol=0,atol=0)
            self.assertEqual(float(out['logits'].masked_select((~rm&~dm)[:,None]).abs().sum()),0.)
            op2=op.masked_fill(~rm[:,None],77);ds2=ds.masked_fill(~dm,99)
            torch.testing.assert_close(m(op2,ds2,rm,dm),out['logits'],rtol=0,atol=0)
            with self.assertRaises(ValueError):m(op,ds,rm.float(),dm)
    def test_complete_forward_hook_matches_unmodified_expert_logits(self):
        m=make('B0').eval();op=torch.rand(1,3,32,32);ds=torch.rand(1,32,32)
        r=m.rgb_expert.net(op,ds);d=m.dsm_expert.net(ds[:,None].repeat(1,3,1,1))
        rm=torch.ones_like(ds,dtype=torch.bool)
        out=m(op,ds,rm,rm,True)
        torch.testing.assert_close(out['rgb'],r,rtol=0,atol=0);torch.testing.assert_close(out['dsm'],d,rtol=0,atol=0)
    def test_trainable_paths_and_frozen_expert_gradients_bn_statistics(self):
        batch=dict(rgb=torch.rand(2,3,32,32),aux=torch.rand(2,32,32),rgb2=torch.rand(2,3,32,32),aux2=torch.rand(2,32,32),gt=torch.randint(6,(2,32,32)),rm2=torch.ones(2,32,32,dtype=torch.bool),dm2=torch.ones(2,32,32,dtype=torch.bool))
        batch['rm2'][0,8:16]=False;batch['dm2'][1,8:16]=False
        for arm in ARMS:
            m=make(arm).train();before={n:v.clone() for n,v in m.named_buffers() if 'running' in n}
            loss,den=objective(m,batch);loss.backward();report=verify_gradients(m)
            self.assertTrue(report['frozen_gradients_absent']);self.assertTrue(report['groups_nonzero']['fusion.'])
            for n,v in before.items():torch.testing.assert_close(dict(m.named_buffers())[n],v,rtol=0,atol=0)
            optim=optimizer_for(m,self.plan['training']);self.assertEqual(len(optim.param_groups),2 if arm=='J0' else 1)
            if arm=='J0':self.assertLess(den['aug_rgb_pixels'],den['clean_rgb_pixels'])
    def test_cap_has_no_cross_donor_but_cross_arm_does(self):
        op=torch.rand(1,3,32,32);ds=torch.rand(1,32,32);mask=torch.ones_like(ds,dtype=torch.bool)
        cap=make('CAP').eval();x=make('X').eval()
        for model,should_equal in ((cap,True),(x,False)):
            a=model(op,ds,mask,mask,True)['dr'];b=model(op,ds+.5,mask,mask,True)['dr']
            self.assertEqual(torch.equal(a,b),should_equal)
    def test_frequency_and_semantic_shuffle_are_effective(self):
        op=torch.rand(1,3,48,48);ds=torch.rand(1,48,48);mask=torch.ones_like(ds,dtype=torch.bool)
        base=make('XSF').eval();z=base(op,ds,mask,mask)
        for arm in ('XS','XF','XSF-shS','XSF-shF'):
            m=make(arm).eval();m.load_state_dict(base.state_dict());self.assertFalse(torch.equal(z,m(op,ds,mask,mask)))
    def test_invalid_interaction_neighborhood_zero(self):
        block=Interaction();r=torch.rand(1,128,8,8);d=torch.rand(r.shape)
        valid=torch.zeros(1,1,8,8,dtype=torch.bool)
        self.assertEqual(float(block(r,d,torch.rand(1,18,8,8),valid,True,True).abs().sum()),0.)
    def test_treatments_both_modalities_correct_shapes_and_no_gt_input(self):
        op=torch.rand(1,3,32,32);ds=torch.rand(1,32,32)
        conditions=self.plan['evaluation']['primary']+self.plan['evaluation']['missing']+sum(self.plan['evaluation']['local'].values(),[])+self.plan['evaluation']['diagnostic']
        for c in conditions:
            r,d,rm,dm=treatment(op,ds,c,123)
            self.assertEqual(r.shape,op.shape);self.assertEqual(d.shape,ds.shape)
            self.assertEqual(float(r.masked_select((~rm)[:,None]).abs().sum()),0.);self.assertEqual(float(d.masked_select(~dm).abs().sum()),0.)
            if c in self.plan['evaluation']['primary']:self.assertTrue(bool(rm.all()&dm.all()))
        _,_,rm,dm=treatment(op,ds,'complementary_halves',1);self.assertTrue(bool((rm|dm).all()));self.assertFalse(bool((rm&dm).any()))
    def test_keyed_independent_quality_draws_and_availability(self):
        op=torch.rand(3,16,16);ds=torch.rand(16,16);seen=set()
        for i in range(160):
            a=views(op,ds,self.plan,10,i);b=views(op,ds,self.plan,10,i)
            for x,y in zip(a[:4],b[:4]):torch.testing.assert_close(x,y,rtol=0,atol=0)
            seen.add(tuple(a[-1].split('+')[:2]));self.assertTrue(bool((a[2]|a[3]).all()))
        self.assertIn(('clean','clean'),seen);self.assertTrue(any(r!='clean' and d!='clean' for r,d in seen));self.assertTrue(any(r=='clean' and d!='clean' for r,d in seen))
    def test_joint_raw_counts_support_class_and_recovery(self):
        g=np.array([[0,1],[2,255]],np.uint8);r=np.array([[0,0],[1,0]],np.uint8);d=np.array([[1,1],[1,0]],np.uint8);f=np.array([[0,1],[2,0]],np.uint8);region=np.ones((2,2),bool)
        joint=joint_counts(g,r,d,f,region);self.assertEqual(joint.dtype,np.int64);self.assertEqual(int(joint.sum()),3)
        np.testing.assert_array_equal(decode_joint(encode_joint(joint)),joint)
        report=joint_report(joint);self.assertEqual(report['only_rgb_correct']['fused_correct'],1);self.assertEqual(report['only_dsm_correct']['fused_correct'],1);self.assertEqual(report['both_wrong']['fused_correct'],1)
        row=counts(g,f,region);self.assertEqual(row['valid'],3);self.assertEqual(row['mIoU_fg5'],1.)
    def test_dynamic_queue_never_duplicates_assigned_job(self):
        jobs=self.plan['jobs'];state={'jobs':{j['id']:{'status':'PENDING'} for j in jobs}}
        first=next_job(jobs,state,0);state['jobs'][first['id']]['status']='RUNNING';second=next_job(jobs,state,1)
        self.assertNotEqual(first['id'],second['id']);self.assertEqual(first['id'],'J0');self.assertEqual(second['id'],'B0')
    def test_stitch_and_evaluation_resume_preserve_evidence(self):
        class PixelModel(nn.Module):
            def __init__(self):super().__init__();self.anchor=nn.Parameter(torch.zeros(()));self.arm='B0'
            def forward(self,op,ds,rm,dm,return_parts=True):
                r=torch.cat((op,1-op),1);d=torch.stack((ds,1-ds,ds*0,ds*0,ds*0,ds*0),1)
                z=torch.where((rm&dm)[:,None],r+d,torch.where(rm[:,None],r,d));z=z.masked_fill((~rm&~dm)[:,None],0)
                return dict(rgb=r,dsm=d,logits=z)
        class Refs:
            def get(self,tile,condition,item,rm,dm,provided=None,progress=None):return {n:p for n,p in provided.items() if n!='candidate'},dict(source='synthetic')
        model=PixelModel().eval();rng=np.random.default_rng(42)
        item=dict(optical=rng.random((512,512,3),dtype=np.float32),dsm=rng.random((512,512),dtype=np.float32),full_gt=np.zeros((512,512),np.uint8),noboundary_gt=np.zeros((512,512),np.uint8))
        rm=np.ones((512,512),bool);dm=rm.copy();rm[:128]=False;dm[128:256]=False;rm[256:384]=False;dm[256:384]=False
        preds,ident=infer(model,item,rm,dm,batch=2)
        self.assertTrue(all(ident.values()));self.assertTrue(np.all(preds['candidate'][~rm&~dm]==255))
        self.assertTrue(np.array_equal(preds['candidate'][rm&~dm],preds['rgb'][rm&~dm]))
        plan=copy.deepcopy(self.plan);plan['data']['validation']=['3_11','5_10']
        temp_root=ROOT/'verification_tmp';temp_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as folder:
            out=Path(folder);binding={'synthetic':True}
            first=evaluate(model,lambda tile,validation:item,Refs(),plan,out,binding,lambda **kw:None,conditions=['clean'])
            second=evaluate(model,lambda tile,validation:item,Refs(),plan,out,binding,lambda **kw:None,conditions=['clean'])
            self.assertEqual(first['pooled'],second['pooled']);self.assertEqual(first['pooled']['clean']['noboundary']['metrics']['candidate']['valid']['valid'],2*512*512)
            path=out/'evaluation/clean/candidate/3_11.npy';path.write_bytes(b'broken')
            with self.assertRaises(RuntimeError):evaluate(model,lambda tile,validation:item,Refs(),plan,out,binding,lambda **kw:None,conditions=['clean'])
    def synthetic_summary(self,v):
        pooled={};tiles={}
        conditions=self.plan['evaluation']['primary']+self.plan['evaluation']['missing']+sum(self.plan['evaluation']['local'].values(),[])
        for c in conditions:
            metric={'mIoU_fg5':v/100};jr={n:dict(valid=100,fused_correct=80) for n in ('only_rgb_correct','only_dsm_correct')}
            pooled[c]={'noboundary':{'metrics':{n:{'valid':metric} for n in ('candidate','fixed_rgb','fixed_dsm')},'joint_reports':{'both':jr}}}
            tiles[c]={t:{'scopes':{'noboundary':{'metrics':{'candidate':{'valid':metric}}}},'fallback_logits_equal_own':{'rgb_only':True,'dsm_only':True}} for t in self.plan['data']['validation']}
        return dict(pooled=pooled,tiles=tiles)
    def test_gate_thresholds_and_protection_failures(self):
        a=self.synthetic_summary(80.2);b=self.synthetic_summary(80.)
        self.assertTrue(pair_gate(a,b,self.plan)['passed']);self.assertFalse(pair_gate(self.synthetic_summary(80.19),b,self.plan)['passed'])
        self.assertTrue(protections(a,b,self.plan)['passed'])
        a['pooled']['rgb_missing']['noboundary']['metrics']['fixed_dsm']={'valid':{'mIoU_fg5':.805}}
        self.assertFalse(protections(a,b,self.plan)['passed'])
        ss={n:self.synthetic_summary(80.) for n in ARMS};result=screen(ss,self.plan);self.assertFalse(result['primary_full_mechanism_eligible']);self.assertFalse(result['frequency']['passed'])

if __name__=='__main__':unittest.main()
