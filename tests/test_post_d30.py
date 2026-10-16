import copy,json,sys,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'scripts')]
import numpy as np
import torch
from torch import nn
from model.rebuild_v1_post_d30 import PortfolioSegmenter,correspondence,alignment,distillation,BandBlock
from model.rebuild_v1_d26 import D26Segmenter
from post_d30_common import predecessor_verdict,next_job,PHASES
from post_d30_data import objective,materialize_shift,geometry
torch.set_num_threads(1)

class Expert(nn.Module):
    def __init__(self,kind):
        super().__init__();self.kind=kind;self.channels=8;self.features=nn.Conv2d(3,8,1);self.logits=nn.Conv2d(8,6,1)
    def configure(self,joint):self.requires_grad_(False);self.eval()
    def forward(self,rgb,dsm):
        x=rgb if self.kind=='rgb' else dsm[:,None].expand(-1,3,-1,-1)
        feature=self.features(x);return self.logits(feature),feature
def make(job):
    torch.manual_seed(10);r,d=Expert('rgb'),Expert('dsm')
    teacher=D26Segmenter(r,d,'B0') if job['id'].startswith('C') else None
    torch.manual_seed(42);return PortfolioSegmenter(r,d,job,teacher)
def batch():
    torch.manual_seed(11);r=torch.rand(2,3,16,16);d=torch.rand(2,16,16);g=torch.randint(0,6,(2,16,16));m=torch.ones_like(g,dtype=torch.bool)
    return dict(rgb=r,aux=d,gt=g,rgb2=r*.7,aux2=d*.8,rm2=m,dm2=m)

class Tests(unittest.TestCase):
    def test_capacity_initialization_matched_and_predictors_active(self):
        plain=make(dict(id='A0',align='none'));other=make(dict(id='A2',align='shared',align_weight=.1))
        self.assertEqual(list(plain.state_dict()),list(other.state_dict()))
        for n,p in plain.state_dict().items():self.assertTrue(torch.equal(p,other.state_dict()[n]),n)
        local=make(dict(id='B3',radius=2,geometry_aug=True))
        for n,p in plain.state_dict().items():self.assertTrue(torch.equal(p,local.state_dict()[n]),n)
        frequency=make(dict(id='F0',radius=2))
        for name in ('F1','F2','F3'):
            other=make(dict(id=name,radius=2))
            for n,p in frequency.state_dict().items():self.assertTrue(torch.equal(p,other.state_dict()[n]),n)
        loss,_=objective(plain,batch());loss.backward()
        self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in plain.parameters() if p.requires_grad))
        self.assertGreater(float(plain.predict_rgb[0].weight.grad.abs().sum()),0)
        self.assertTrue(all(p.grad is None for p in plain.rgb_expert.parameters()))
    def test_all_shared_alignment_stop_gradient_and_shuffle(self):
        b=batch();model=make(dict(id='A0'));m=b['rm2'];parts=model(b['rgb'],b['aux'],m,m,True)
        terms=[]
        for mode in ('all','shared','shuffled'):terms.append(float(alignment(parts,dict(align=mode)).detach()))
        self.assertGreater(max(terms)-min(terms),1e-4)
        for n in ('rgb','dsm'):parts['features_'+n]=parts['features_'+n].detach().requires_grad_()
        alignment(parts,dict(align='shared')).backward()
        self.assertIsNone(parts['features_rgb'].grad);self.assertIsNone(parts['features_dsm'].grad)
    def test_correspondence_zero_padding_mask_and_nontrivial_gradients(self):
        q=torch.randn(1,4,5,7,requires_grad=True);d=torch.randn_like(q,requires_grad=True);m=torch.ones(1,1,5,7,dtype=torch.bool)
        out,w=correspondence(q,d,m,m,2);sh,_=correspondence(q,d,m,m,2,True)
        self.assertEqual(out.shape,q.shape);self.assertTrue(torch.allclose(w.sum(1),torch.ones(1,5,7)))
        self.assertEqual(float(w[0,0,0,0]),0);self.assertFalse(torch.allclose(out,sh))
        out.square().sum().backward();self.assertGreater(float(q.grad.abs().sum()),0);self.assertGreater(float(d.grad.abs().sum()),0)
        empty=torch.zeros_like(m);z,w=correspondence(q,d,m,empty,2);self.assertTrue(torch.equal(z,torch.zeros_like(z)));self.assertFalse(w.any())
    def test_every_arm_exact_missing_fallback_and_gradient(self):
        design=json.loads((Path(__file__).resolve().parents[1]/'records/research_post_d30_design_20261003/plan.json').read_text())
        b=batch()
        for job in design['jobs']:
            if job['phase']=='C':continue
            model=make(job);m=b['rm2'];missing=torch.zeros_like(m)
            parts=model(b['rgb'],b['aux'],m,missing,True);self.assertTrue(torch.equal(parts['logits'],parts['rgb']),job['id'])
            parts=model(b['rgb'],b['aux'],missing,m,True);self.assertTrue(torch.equal(parts['logits'],parts['dsm']),job['id'])
            loss,_=objective(model,b);loss.backward()
            self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters() if p.requires_grad),job['id'])
    def test_C_full_teacher_identity_bilateral_heads_and_own_inputs(self):
        b=batch();m=b['rm2'];model=make(dict(id='C2',distill='correct'));model.eval()
        with torch.no_grad():
            original=model.teacher(b['rgb'],b['aux'],m,m);parts=model(b['rgb'],b['aux'],m,m,True)
            self.assertTrue(torch.equal(original,parts['logits']))
            missing=torch.zeros_like(m);a=model(b['rgb'],b['aux'],m,missing);c=model(b['rgb'],b['aux']+100,m,missing)
            self.assertTrue(torch.equal(a,c))
            self.assertTrue(torch.equal(a,model.single(b['rgb'],b['aux'],m,'rgb')))
            a=model(b['rgb'],b['aux'],missing,m);c=model(b['rgb']+100,b['aux'],missing,m);self.assertTrue(torch.equal(a,c))
            self.assertTrue(torch.equal(a,model.single(b['rgb'],b['aux'],m,'dsm')))
        loss,counts=objective(model,b);loss.backward()
        self.assertTrue(all(p.grad is None for p in model.teacher.parameters()))
        for head in (model.single_rgb,model.single_dsm):self.assertGreater(float(head[0].weight.grad.abs().sum()),0)
        self.assertEqual(counts['clean_rgb_pixels'],512)
    def test_correct_mask_global_denominator_and_teacher_detach(self):
        s=torch.randn(1,6,2,2,requires_grad=True);t=torch.full_like(s,-10,requires_grad=True);gt=torch.ones(1,2,2,dtype=torch.long);valid=torch.ones_like(gt,dtype=torch.bool)
        with torch.no_grad():t[:,0]=10;t[:,1,0,0]=30
        masked=distillation(s,t,gt,valid,'correct');manual=distillation(s,t,gt,valid&torch.tensor([[[1,0],[0,0]]],dtype=torch.bool),'all')/4
        self.assertTrue(torch.allclose(masked,manual));masked.backward();self.assertIsNone(t.grad)
    def test_native_halo_keeps_labels_and_no_wrap(self):
        grid=np.arange(40*40,dtype=np.float32).reshape(40,40)
        tile=dict(dsm=grid,optical=np.repeat(grid[...,None],3,2),full_gt=np.zeros((40,40),np.uint8))
        spec=dict(tile='t',patch=8,scale=1.,fy=.5,fx=.5,vflip=False,hflip=False,treatment='clean',treatment_seed=1)
        op,ds,gt=materialize_shift({'t':tile},spec);op2,ds2,gt2=materialize_shift({'t':tile},spec,4,0)
        self.assertTrue(torch.equal(op,op2));self.assertTrue(torch.equal(gt,gt2));self.assertTrue(torch.equal(ds2,ds-4))
        image=torch.arange(20*20).reshape(1,20,20);shifted=geometry(image,'geom_dx8')
        self.assertEqual(int(shifted[0,0,0]),0);self.assertEqual(int(shifted[0,0,10]),2)
    def test_frequency_suppression_removes_bypass_high_signal(self):
        block=BandBlock()
        for p in block.parameters():nn.init.zeros_(p)
        x=(torch.arange(8)[:,None]+torch.arange(8)[None,:])%2*2-1
        x=x.float()[None,None].expand(1,128,8,8)
        self.assertTrue(torch.equal(block(x,True,True),torch.zeros_like(x)))
        self.assertTrue(torch.equal(block(x,True,False),x))
    def test_frozen_gate_requires_increment_over_plain_and_augmentation(self):
        from summarize_post_d30 import screen
        def fake(score):
            metric=dict(mIoU_fg5=score/100,cm=np.eye(6,dtype=np.int64).tolist())
            report={n:dict(valid=1,fused_correct=1,fused_wrong=0,retention=1) for n in ('both_correct','only_rgb_correct','only_dsm_correct','both_wrong')}
            joint=np.zeros((6,)*4,np.int64);joint[0,0,1,0]=1;joint[1,0,1,1]=1
            from post_d30_evaluation import encode_joint
            row=dict(scopes={'noboundary':dict(metrics={'candidate':{'valid':metric}},joint={'both':encode_joint(joint)},joint_reports={'both':report})})
            return dict(pooled={c:row['scopes'] for c in ('clean','geo')},tiles={c:{'t':row} for c in ('clean','geo')})
        plan=dict(evaluation=dict(primary=['clean'],families={n:['clean'] for n in ('C','QR','QD','QJ')}),design=dict(geometry_conditions=['geo']),data=dict(validation=['t']))
        names=PHASES['A']+PHASES['B'];data={age:{n:fake(80) for n in names} for age in ('selected','fixed8000')}
        result=screen(data,plan);self.assertFalse(result['A2']['passed']);self.assertFalse(result['B3']['passed'])
        self.assertFalse(result['B3']['checks']['vs_augmentation'])
    def test_phase_barrier_and_no_premature_handover(self):
        jobs={n:dict(status='COMPLETE') for n in ('replay_G0','replay_G1','P','R','PR_area','PR_pixel')};s=dict(status='COMPLETE',jobs=jobs)
        self.assertEqual(predecessor_verdict(s,False,False,True),'WAITING_D30_RELEASE')
        self.assertEqual(predecessor_verdict(s,True,True,False),'WAITING_D30_RELEASE')
        self.assertEqual(predecessor_verdict(s,True,False,False),'READY')
        s['jobs']['R']['status']='PENDING';self.assertTrue(predecessor_verdict(s,True,False,False).startswith('HOLD'))
        queue=dict(jobs={n:dict(status='PENDING',gpu=0) for names in PHASES.values() for n in names})
        self.assertEqual(next_job(queue,0,'A'),'A0');self.assertNotEqual(next_job(queue,0,'B'),'A0')
if __name__=='__main__':unittest.main()
