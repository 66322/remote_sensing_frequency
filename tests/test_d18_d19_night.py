import copy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import numpy as np
import torch
from torch import nn
import d18_d19_night as p
import d16_d17_portfolio as old
from model.rebuild_v1_night_screen import LocalInteraction,FrozenDinoSegmenter
from night_boundary_metrics import boundary_counts
from summarize_rebuild_v1_d18_d19 import assess


class Add(nn.Module):
    def forward(self,x,y):
        return x+y


class Encoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.projection=nn.Conv2d(3,384,14,stride=14)
    def forward_features(self,x):
        return {'x_norm_patchtokens':self.projection(x).flatten(2).transpose(1,2)}


class NightTests(unittest.TestCase):
    def test_insertion_in_actual_dual_encoder_forward_and_reload(self):
        from model.vit_seg_modeling_resnet_skip import FuseResNetV2
        torch.manual_seed(10)
        original=FuseResNetV2((1,1,1),1).eval()
        adapted=copy.deepcopy(original)
        adapted.se_layer0=LocalInteraction(adapted.se_layer0)
        x,y=torch.randn(1,3,32,32),torch.randn(1,1,32,32)
        expected=original(x,y)[0]
        actual=adapted(x,y)[0]
        self.assertTrue(torch.equal(expected,actual))
        adapted.se_layer0.alpha.data.fill_(.5)
        adapted(x,y)[0].square().mean().backward()
        self.assertIsNotNone(adapted.se_layer0.q.weight.grad)
        restored=copy.deepcopy(adapted)
        restored.load_state_dict(adapted.state_dict(),strict=True)
        self.assertTrue(torch.equal(adapted(x,y)[0],restored(x,y)[0]))

    def test_interaction_preserves_anchor_and_matches_capacity(self):
        torch.manual_seed(1)
        model=LocalInteraction(Add())
        capacity=LocalInteraction(Add(),capacity=True)
        n=sum(p.numel() for p in model.parameters())
        m=sum(p.numel() for p in capacity.parameters())
        self.assertLess(abs(n-m)/n,.05)
        x,y=torch.randn(1,64,19,23),torch.randn(1,64,19,23)
        self.assertTrue(torch.equal(model(x,y),x+y))
        model.alpha.data.fill_(.5)
        loss=model(x,y).square().mean()
        loss.backward()
        for name,param in model.named_parameters():
            self.assertIsNotNone(param.grad,name)
            self.assertTrue(torch.isfinite(param.grad).all(),name)

    def test_frozen_encoder_and_auxiliary_dependence(self):
        torch.manual_seed(4)
        p0=FrozenDinoSegmenter(Encoder(),False)
        p2=FrozenDinoSegmenter(copy.deepcopy(p0.encoder),True)
        rgb=torch.rand(1,3,56,56)
        a,b=torch.zeros(1,56,56),torch.ones(1,56,56)
        self.assertTrue(torch.equal(p0(rgb,a),p0(rgb,b)))
        self.assertFalse(torch.equal(p2(rgb,a),p2(rgb,b)))
        p2.train()
        self.assertFalse(p2.encoder.training)
        p2(rgb,a).square().mean().backward()
        self.assertTrue(all(x.grad is None and not x.requires_grad for x in p2.encoder.parameters()))
        self.assertTrue(all(x.grad is not None for x in p2.aux.parameters()))

    def test_matched_gray_and_dsm_initialization(self):
        nets=[]
        encoder=Encoder()
        for _ in range(2):
            torch.manual_seed(42)
            nets.append(FrozenDinoSegmenter(copy.deepcopy(encoder),True))
        for x,y in zip(nets[0].parameters(),nets[1].parameters()):
            self.assertTrue(torch.equal(x,y))

    def test_crop_independent_structured_treatments(self):
        rgb=torch.rand(2,3,32,32)
        ds=torch.rand(2,32,32)
        expected=p.training_transform(rgb,ds,'C0',['clean','aux_down4'],12)
        for arm in ('C2','CP','C4','C5'):
            actual=p.training_transform(rgb,ds,arm,['clean','aux_down4'],12)
            for x,y in zip(expected,actual):
                self.assertTrue(torch.equal(x,y))

    def test_diagnostics_are_correct_and_not_training_conditions(self):
        cfg=p.read(p.CONFIG)
        self.assertFalse(set(cfg['diagnostics']) & set(cfg['treatment_probabilities']))
        rgb=torch.ones(1,3,16,16)
        ds=torch.arange(16).expand(1,16,16).float()
        op,aux,_=p.transform(rgb,ds,'P2',['rgb_contrast060'],torch.Generator())
        torch.testing.assert_close(op,torch.full_like(op,.8))
        op,aux,_=p.transform(rgb,ds,'P2',['aux_shift8'],torch.Generator())
        self.assertTrue(torch.equal(aux[:,:,8:],ds[:,:,:8]))
        self.assertTrue(torch.equal(aux[:,:,:8],torch.zeros_like(aux[:,:,:8])))

    def test_boundary_counts_tolerance_and_ignore(self):
        gt=np.zeros((50,50),dtype=np.uint8)
        gt[15:35,15:35]=1
        same=boundary_counts(gt,gt)
        for row in same:
            self.assertEqual(row['predicted'],row['matched_predicted'])
            self.assertEqual(row['truth'],row['matched_truth'])
        pred=np.roll(gt,2,axis=1)
        shifted=boundary_counts(gt,pred)
        self.assertEqual(shifted[1]['predicted'],shifted[1]['matched_predicted'])
        gt[:]=255
        self.assertTrue(all(x['predicted']==x['truth']==0 for x in boundary_counts(gt,pred)))

    def test_screen_needs_capacity_control_and_tile_guards(self):
        cfg=p.read(p.CONFIG)
        def summary(value):
            return {'conditions':{c:{'pooled':{'noboundary':{'metrics':{'mIoU_fg5':value}}},
                'tiles':{t:{'metrics':{'noboundary':{'metrics':{'mIoU_fg5':value}}}} for t in ('3_11','5_10')},
                'joint_noboundary':{'valid':100,'only_r01_correct':3,'only_candidate_correct':5}}
                for c in cfg['evaluation_conditions']}}
        data={a:summary(v) for a,v in [('C0',.8),('CP',.81),('C2',.811)]}
        self.assertFalse(assess('C2',['C0','CP'],'C0',data,cfg)['passed'])
        data['C2']=summary(.815)
        self.assertTrue(assess('C2',['C0','CP'],'C0',data,cfg)['passed'])
        data['C2']['conditions']['clean']['tiles']['5_10']['metrics']['noboundary']['metrics']['mIoU_fg5']=.798
        self.assertFalse(assess('C2',['C0','CP'],'C0',data,cfg)['passed'])

    def test_optimizer_state_resume_same_next_update(self):
        torch.manual_seed(6)
        net=LocalInteraction(Add())
        opt=torch.optim.AdamW(net.parameters(),lr=.01)
        x,y=torch.randn(1,64,8,8),torch.randn(1,64,8,8)
        def update(n,o):
            o.zero_grad()
            n(x,y).square().mean().backward()
            o.step()
        update(net,opt)
        restored=copy.deepcopy(net)
        restored_opt=torch.optim.AdamW(restored.parameters(),lr=.01)
        restored_opt.load_state_dict(copy.deepcopy(opt.state_dict()))
        update(net,opt)
        update(restored,restored_opt)
        for x,y in zip(net.parameters(),restored.parameters()):
            self.assertTrue(torch.equal(x,y))

    @unittest.skipUnless(torch.cuda.is_available(),'server CUDA check')
    def test_cuda_new_losses_and_modules_strict(self):
        previous=torch.are_deterministic_algorithms_enabled()
        try:
            torch.use_deterministic_algorithms(True)
            for capacity in (False,True):
                net=LocalInteraction(Add(),capacity=capacity).cuda()
                net.alpha.data.fill_(.5)
                result=net(torch.randn(1,64,16,16,device='cuda'),torch.randn(1,64,16,16,device='cuda'))
                result.square().mean().backward()
                self.assertTrue(all(torch.isfinite(x.grad).all() for x in net.parameters()))
            result=torch.randn(1,6,16,16,device='cuda',requires_grad=True)
            labels=torch.zeros(1,16,16,dtype=torch.long,device='cuda')
            for arm in ('A1','A2','A3'):
                logits=result.clone()
                available=torch.ones_like(labels,dtype=torch.bool)
                loss,_=old.consistency(logits.detach(),logits,labels,available,arm,torch.Generator().manual_seed(1))
                (old.deterministic_ce(logits,labels)+loss).backward(retain_graph=True)
        finally:
            torch.use_deterministic_algorithms(previous)

    @unittest.skipUnless(torch.cuda.is_available() and int(torch.__version__.split('.')[0])>=2,'D18 modern CUDA environment check')
    def test_cuda_frozen_adapter_in_modern_environment(self):
        previous=torch.are_deterministic_algorithms_enabled()
        try:
            torch.use_deterministic_algorithms(True)
            net=FrozenDinoSegmenter(Encoder(),True).cuda()
            result=net(torch.rand(1,3,56,56,device='cuda'),torch.rand(1,56,56,device='cuda'))
            labels=torch.zeros(1,56,56,dtype=torch.long,device='cuda')
            old.deterministic_ce(result,labels).backward()
            self.assertTrue(all(x.grad is None for x in net.encoder.parameters()))
        finally:
            torch.use_deterministic_algorithms(previous)


if __name__=='__main__':
    unittest.main()
