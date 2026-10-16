"""CPU behavior checks for new mechanisms, not a repeated resource admission."""
import copy
import json
from pathlib import Path
import sys
import unittest
import torch
from torch import nn
from torch.nn import functional as F

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from model.rebuild_v1_d21_detail import DetailDinoSegmenter
from model.rebuild_v1_d24 import D24Segmenter
from d24_objectives import ce,anchored_pair,rescue_mask,shuffled_mask,kd,verify_gradients,step_objective
from d24_common import validate_plan
from d24_data import views,PrefetchedBatches
from launch_rebuild_v1_d24 import next_job,FILES
from summarize_rebuild_v1_d24 import matched,audit_counts

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

class D24Tests(unittest.TestCase):
    def setUp(self):torch.manual_seed(42)
    def inputs(self):
        return torch.rand(2,3,31,29),torch.rand(2,31,29),torch.randint(0,6,(2,31,29))
    def test_frozen_initialization_matches_M0_and_presence_is_explicit(self):
        old=DetailDinoSegmenter(FakeEncoder(),'M0')
        new=D24Segmenter(FakeEncoder())
        new.load_state_dict(old.state_dict(),strict=True)
        old.eval();new.eval()
        rgb,aux,_=self.inputs();mask=torch.ones_like(aux,dtype=torch.bool)
        self.assertTrue(torch.equal(old(rgb,aux),new(rgb,aux,mask)))
        with self.assertRaises(ValueError):new(rgb,aux)
    def test_last4_gradient_range_and_teacher_freeze(self):
        for last4 in (False,True):
            model=D24Segmenter(FakeEncoder(),last4=last4)
            teacher=DetailDinoSegmenter(FakeEncoder(),'R0').requires_grad_(False)
            rgb,aux,gt=self.inputs();mask=torch.ones_like(aux,dtype=torch.bool)
            ce(model(rgb,aux,mask),gt).backward()
            result=verify_gradients(model,[teacher])
            self.assertEqual(result['encoder_gradient_nonzero'],last4)
            for name,p in model.encoder.named_parameters():
                if not (last4 and name.startswith(('blocks.4.','blocks.5.','blocks.6.','blocks.7.'))):
                    self.assertIsNone(p.grad)
    def test_full_and_local_missing_equal_own_optical_logits(self):
        for proto in (False,True):
            model=D24Segmenter(FakeEncoder(),last4=True,prototype=proto).train()
            rgb,aux,_=self.inputs()
            for full in (False,True):
                mask=torch.ones_like(aux,dtype=torch.bool)
                if full:mask.zero_()
                else:mask[:,9:24,8:23]=False
                fused,own,_,_=model(rgb,aux,mask,return_parts=True)
                self.assertTrue(torch.equal(fused.permute(0,2,3,1)[~mask],own.permute(0,2,3,1)[~mask]))
                if full:self.assertTrue(torch.equal(fused,own))
    def test_same_capacity_initial_state_and_training_only_bank_updates(self):
        models=[]
        for _ in range(4):
            torch.manual_seed(42);models.append(D24Segmenter(FakeEncoder(),last4=True,prototype=True))
        for other in models[1:]:
            self.assertEqual(sum(p.numel() for p in models[0].parameters()),sum(p.numel() for p in other.parameters()))
            self.assertTrue(all(torch.equal(v,other.state_dict()[k]) for k,v in models[0].state_dict().items()))
        rgb,aux,gt=self.inputs();mask=torch.ones_like(aux,dtype=torch.bool)
        model=models[0].train();parts=model(rgb,aux,mask,return_parts=True)
        ce(parts[0],gt).backward()
        before=model.prototype.bank.clone()
        model.prototype.update(parts[2],parts[3],gt,True,torch.tensor([1,2]))
        self.assertFalse(torch.equal(before,model.prototype.bank))
        self.assertFalse(model.prototype.bank.requires_grad)
        saved={k:v.clone() for k,v in model.prototype.state_dict().items()}
        model.eval();model(rgb,aux,mask)
        self.assertTrue(all(torch.equal(v,model.prototype.state_dict()[k]) for k,v in saved.items()))
    def test_pair_hinge_sign_and_detached_reference(self):
        gt=torch.zeros(2,3,4,dtype=torch.long)
        worse=torch.zeros(2,6,3,4,requires_grad=True)
        ref=torch.zeros_like(worse,requires_grad=True)
        with torch.no_grad():ref[:,0]=3
        loss=anchored_pair(worse,ref,gt)
        self.assertGreater(float(loss),0);loss.backward()
        self.assertIsNone(ref.grad);self.assertLess(float(worse.grad[:,0].mean()),0)
        self.assertEqual(float(anchored_pair(ref,worse,gt)),0)
    def test_balanced_ce_is_mean_of_present_classes(self):
        logits=torch.randn(1,6,2,3,requires_grad=True)
        gt=torch.tensor([[[0,0,0],[0,1,255]]])
        raw=-F.log_softmax(logits,1).gather(1,gt.clamp(0,5)[:,None])[:,0]
        expected=(raw[gt==0].mean()+raw[gt==1].mean())/2
        self.assertTrue(torch.allclose(ce(logits,gt,True),expected))
        self.assertEqual(float(ce(logits,torch.full_like(gt,255))),0)
    def test_spatial_KD_counts_teacher_stopgrad_and_empty_region(self):
        student=torch.randn(2,6,5,7,requires_grad=True)
        teacher=torch.randn_like(student,requires_grad=True)
        valid=torch.ones(2,5,7,dtype=torch.bool);valid[:,2,3]=False
        selected=valid & (torch.arange(7)[None,None,:]%3==0)
        shuffled=shuffled_mask(selected,valid)
        self.assertTrue(torch.equal(shuffled.sum((1,2)),selected.sum((1,2))))
        self.assertFalse(torch.equal(shuffled,selected));self.assertFalse(bool((shuffled & ~valid).any()))
        kd(student,teacher,selected).backward();self.assertIsNone(teacher.grad)
        self.assertTrue(torch.equal(student.grad.permute(0,2,3,1)[~selected],torch.zeros_like(student.grad.permute(0,2,3,1)[~selected])))
        self.assertEqual(float(kd(student,teacher,torch.zeros_like(valid))),0)
    def test_region_is_teacher_correct_reference_wrong(self):
        gt=torch.tensor([[[0,1,2]]]);teacher=F.one_hot(torch.tensor([[[0,0,2]]]),6).permute(0,3,1,2).float()
        ref=F.one_hot(torch.tensor([[[1,1,2]]]),6).permute(0,3,1,2).float()
        self.assertEqual(rescue_mask(teacher,ref,gt).tolist(),[[[True,False,False]]])
        model=D24Segmenter(FakeEncoder(),optical_only=True,last4=True).eval()
        rgb,aux,_=self.inputs()
        self.assertTrue(torch.equal(model(rgb,aux,torch.ones_like(aux,dtype=torch.bool)),
                                    model(rgb,torch.zeros_like(aux),torch.zeros_like(aux,dtype=torch.bool))))
    def test_keyed_quality_dropout_factor_streams(self):
        rgb=torch.rand(3,24,24);aux=torch.rand(24,24)
        q=views(rgb,aux,'Q',13,7);qd=views(rgb,aux,'QD',13,7);d=views(rgb,aux,'D',13,7)
        self.assertEqual(q[3],qd[3]);self.assertEqual(d[4],qd[4])
        again=views(rgb,aux,'QD',13,7)
        self.assertTrue(all(torch.equal(qd[i],again[i]) for i in range(3)))
        none=views(rgb,aux,'none',13,7)
        self.assertTrue(torch.equal(none[0],rgb));self.assertTrue(torch.equal(none[1],aux))
    def test_15_jobs_alias_and_queue_skip_completed_or_failed(self):
        plan=json.loads((ROOT/'records/research_d24_overnight_plan_20261001/plan.json').read_text(encoding='utf-8'))
        jobs=validate_plan(plan);self.assertEqual(len(jobs),15)
        state={'jobs':{j['id']:{'status':'PENDING'} for j in jobs}}
        self.assertEqual(next_job(jobs,state,0)['id'],'A0')
        state['jobs']['A0']['status']='COMPLETE';state['jobs']['A3']['status']='TECHNICAL_FAILURE'
        self.assertEqual(next_job(jobs,state,0)['id'],'C0')
    def test_optimizer_and_bank_resume_reproduces_next_step(self):
        model=D24Segmenter(FakeEncoder(),last4=True,prototype=True)
        opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=2e-4)
        def update(net,optimizer):
            rgb,aux,gt=self.inputs();mask=torch.ones_like(aux,dtype=torch.bool)
            optimizer.zero_grad();parts=net(rgb,aux,mask,return_parts=True)
            loss=ce(parts[0],gt);loss.backward();optimizer.step()
            net.prototype.update(parts[2],parts[3],gt,True,torch.tensor([1,2]))
            return float(loss.detach())
        update(model,opt)
        state=copy.deepcopy(model.state_dict());optim=copy.deepcopy(opt.state_dict());rng=torch.get_rng_state()
        loss=update(model,opt);expected=copy.deepcopy(model.state_dict())
        clone=D24Segmenter(FakeEncoder(),last4=True,prototype=True);clone.load_state_dict(state)
        optimizer=torch.optim.AdamW([p for p in clone.parameters() if p.requires_grad],lr=2e-4)
        optimizer.load_state_dict(optim);torch.set_rng_state(rng)
        self.assertEqual(update(clone,optimizer),loss)
        self.assertTrue(all(torch.equal(v,clone.state_dict()[k]) for k,v in expected.items()))
    def test_real_training_objective_all_15_groups_has_valid_gradients(self):
        plan=json.loads((ROOT/'records/research_d24_overnight_plan_20261001/plan.json').read_text(encoding='utf-8'))
        for job in plan['jobs']:
            torch.manual_seed(42)
            model=D24Segmenter(FakeEncoder(),job['route']=='C',job['last4'],job['route']=='B').train()
            teachers={arm:DetailDinoSegmenter(FakeEncoder(),arm).requires_grad_(False).eval()
                      for arm in (('R0','M0') if job['route']=='C' else ('R0',) if job['route']=='A' else ())}
            rgb,aux,gt=self.inputs();mask=torch.ones_like(aux,dtype=torch.bool)
            tensors=dict(rgb=rgb,aux=aux,gt=gt,rgb2=rgb*.9,aux2=aux,mask2=mask)
            loss,rf,af,counts=step_objective(model,teachers,job,tensors,plan,mixed=False)
            self.assertTrue(bool(torch.isfinite(loss)),job['id']);loss.backward()
            verify_gradients(model,list(teachers.values()))
            if job['route']=='B':model.prototype.update(rf,af,gt,job['prototype'].startswith('class_'),torch.tensor([1,2]))
            if job['route']=='C':self.assertIn('KD:clean:empty_views',counts)
    def test_standalone_snapshot_dependencies_exist_and_python310_syntax(self):
        import ast
        for name in FILES:
            self.assertTrue((ROOT/name).is_file(),name)
            if name.endswith('.py'):
                ast.parse((ROOT/name).read_text(encoding='utf-8'),filename=name,feature_version=(3,10))
    def test_original_int64_counts_pooling_and_harm_rescue_identity(self):
        import numpy as np
        import d23_engine as e
        from d23_lifecycle import pool
        gt=np.arange(6,dtype=np.uint8)[:,None].repeat(4,1)
        own=gt.copy();ref=gt.copy();ref[0,3]=1
        candidate=gt.copy();candidate[1,1]=2
        available=np.ones(gt.shape,bool);available[:,0]=False
        results={name:{scope:e.count_result(gt,pred,ref,available) for scope in ('full','noboundary')}
                 for name,pred in [('candidate',candidate),('own_optical',own),('R0',ref),('M0_safe',gt)]}
        row=dict(results=results,own_optical_reference={scope:e.count_result(gt,candidate,own,available)
                                                      for scope in ('full','noboundary')})
        tiles={c:{tile:copy.deepcopy(row) for tile in ('3_11','5_10')} for c in e.CONDITIONS}
        pooled={c:{name:{scope:pool([r['results'][name][scope] for r in rows.values()])
                        for scope in ('full','noboundary')}
                   for name in results} for c,rows in tiles.items()}
        summary=dict(tiles=tiles,pooled=pooled)
        self.assertEqual(audit_counts(summary),224)
        self.assertFalse(matched(summary,summary)['fusion_screen_pass'])
        bad=copy.deepcopy(summary);bad['tiles']['clean']['3_11']['results']['candidate']['full']['cm'][0][0]+=.1
        with self.assertRaises(RuntimeError):audit_counts(bad)
    def test_thread_prefetch_keeps_exact_sample_order_and_no_partial_batch(self):
        class Samples:
            def __len__(self):return 32
            def __getitem__(self,i):return dict(x=torch.tensor(i),tag=str(i))
        batches=list(PrefetchedBatches(Samples(),workers=8,pin_memory=False))
        self.assertEqual(torch.cat([b['x'] for b in batches]).tolist(),list(range(32)))
        self.assertEqual([v for b in batches for v in b['tag']],[str(i) for i in range(32)])
        class Partial(Samples):
            def __len__(self):return 31
        with self.assertRaises(ValueError):PrefetchedBatches(Partial(),pin_memory=False)

if __name__=='__main__':unittest.main()
