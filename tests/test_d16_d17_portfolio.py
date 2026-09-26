import concurrent.futures
import importlib.util
from pathlib import Path
import sys
import threading
import time
import tempfile
import random
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import torch
import d16_d17_portfolio as p
from run_rebuild_v1_d16_d17_queue import run_shared


class PortfolioTests(unittest.TestCase):
    def test_deterministic_ce_matches_loss_and_gradients(self):
        torch.manual_seed(3)
        logits = torch.randn(2,6,7,9,dtype=torch.float64,requires_grad=True)
        labels = torch.randint(0,6,(2,7,9))
        labels[0,:2,:3] = 255
        reference = torch.nn.functional.cross_entropy(logits,labels,ignore_index=255)
        expected = torch.autograd.grad(reference,logits)[0]
        actual = p.deterministic_ce(logits,labels)
        gradient = torch.autograd.grad(actual,logits)[0]
        torch.testing.assert_close(actual,reference,rtol=1e-12,atol=1e-12)
        torch.testing.assert_close(gradient,expected,rtol=1e-12,atol=1e-12)
        empty = p.deterministic_ce(logits,torch.full_like(labels,255))
        self.assertEqual(float(empty.detach()),0)

    @unittest.skipUnless(torch.cuda.is_available(), 'requires server CUDA')
    def test_cuda_ce_strict_determinism_forward_backward(self):
        previous = torch.are_deterministic_algorithms_enabled()
        try:
            torch.use_deterministic_algorithms(True)
            torch.manual_seed(8)
            cpu = torch.randn(2,6,7,9,requires_grad=True)
            labels = torch.randint(0,6,(2,7,9))
            labels[0,0,0] = 255
            expected = torch.nn.functional.cross_entropy(cpu,labels,ignore_index=255)
            expected_grad = torch.autograd.grad(expected,cpu)[0]
            gradients = []
            for _ in range(2):
                logits = cpu.detach().cuda().requires_grad_()
                loss = p.deterministic_ce(logits,labels.cuda())
                gradient = torch.autograd.grad(loss,logits)[0]
                torch.testing.assert_close(loss.cpu(),expected.detach())
                torch.testing.assert_close(gradient.cpu(),expected_grad)
                gradients.append(gradient)
            self.assertTrue(torch.equal(*gradients))
        finally:
            torch.use_deterministic_algorithms(previous)

    def test_config_and_split_boundary(self):
        cfg = p.read(p.CONFIG)
        p.validate_config(cfg)
        split = p.read(ROOT/cfg['split_file'])
        self.assertEqual(len(split['train16']),16)
        self.assertFalse(set(split['train16']) & set(split['val2']+split['historical_exposed_test6']))

    def test_task_mask_missing_and_detached_teacher(self):
        clean = torch.tensor([[[[5.,5.,0.,5.]],[[0.,0.,5.,0.]]]],requires_grad=True)
        corrupt = torch.tensor([[[[0.,0.,5.,5.]],[[5.,5.,0.,0.]]]],requires_grad=True)
        gt = torch.tensor([[[0,0,0,255]]])
        available = torch.tensor([[[True,False,True,True]]])
        loss,n = p.consistency(clean,corrupt,gt,available,'A2',torch.Generator().manual_seed(1))
        self.assertEqual(n,1)
        loss.backward()
        self.assertIsNone(clean.grad)
        self.assertGreater(float(corrupt.grad.abs().sum()),0)
        self.assertEqual(float(corrupt.grad[:,:,:,1:].abs().sum()),0)

    def test_empty_mask_finite_zero(self):
        logits = torch.randn(1,6,4,4,requires_grad=True)
        loss,n = p.consistency(logits,logits,logits.argmax(1),torch.ones(1,4,4,dtype=torch.bool),'A2',torch.Generator())
        self.assertEqual(n,0)
        self.assertEqual(float(loss.detach()),0)
        loss.backward()
        self.assertTrue(torch.isfinite(logits.grad).all())

    def test_shuffle_preserves_class_counts_excludes_unavailable(self):
        gt = torch.tensor([[[0,0,0,255,1,1,1,255]]])
        mask = torch.tensor([[[True,False,False,False,True,True,False,False]]])
        new = p.shuffled_mask(mask,gt,torch.Generator().manual_seed(123))
        for c in (0,1):
            self.assertEqual(int((new & (gt==c)).sum()),int((mask & (gt==c)).sum()))
        self.assertFalse(bool((new & (gt==255)).any()))

    def test_aux_semantics_and_rgb_damage(self):
        op = torch.rand(2,3,16,16)
        ds = torch.rand(2,16,16)
        treated,aux,avail = p.transform(op,ds,'A4',['rgb_down4','aux_zero'],torch.Generator())
        self.assertTrue(torch.equal(aux[0],treated[0].mean(0)))
        self.assertEqual(float(aux[1].sum()),0)
        self.assertFalse(bool(avail[1].any()))
        _,dsm,_ = p.transform(op,ds,'A0',['clean','clean'],torch.Generator())
        self.assertTrue(torch.equal(dsm,ds))
        self.assertTrue(torch.equal(op,op.clone()))

    def test_noise_deterministic_and_geometry_shuffle(self):
        op = torch.rand(1,3,16,16)
        ds = torch.rand(1,16,16)
        a = p.transform(op,ds,'A0',['aux_noise_std010'],torch.Generator().manual_seed(9))[1]
        b = p.transform(op,ds,'A0',['aux_noise_std010'],torch.Generator().manual_seed(9))[1]
        self.assertTrue(torch.equal(a,b))
        target = p.geometry_target(ds,(8,8),0.1)
        shuffled = p.shuffled_geometry(target,torch.Generator().manual_seed(2))
        for channel in range(2):
            self.assertTrue(torch.equal(target[0,channel].flatten().sort().values,shuffled[0,channel].flatten().sort().values))

    def test_shared_queue_failure_does_not_drop_jobs(self):
        claimed = []
        lock = threading.Lock()
        def execute(gpu,job):
            with lock:
                claimed.append((gpu,job))
            time.sleep(0.005)
            if job == 2:
                raise RuntimeError('simulated evaluator failure')
            return True
        result = run_shared(list(range(12)),execute)
        self.assertEqual(sorted(j for _,j in claimed),list(range(12)))
        self.assertEqual(sum(not ok for _,ok in result),1)
        self.assertEqual(set(g for g,_ in claimed),{0,1})

    def test_geometry_hook_before_first_fusion(self):
        # Verify actual execution order rather than assuming deeper RGB is unmixed.
        source = (ROOT/'model/vit_seg_modeling_resnet_skip.py').read_text(encoding='utf-8')
        forward = source[source.index('    def forward(self, x, y):'):]
        self.assertLess(forward.index('x = self.root(x)'),forward.index('x = self.se_layer0(x, y)'))

    def test_checkpoint_resume_matches_next_optimizer_step(self):
        from train_rebuild_v1_d16_d17 import save
        torch.manual_seed(17)
        random.seed(17)
        net = torch.nn.Sequential(torch.nn.Linear(4,4),torch.nn.Dropout(0.3),torch.nn.Linear(4,2))
        optimizer = torch.optim.AdamW(net.parameters(),lr=0.01)
        def step(model,opt):
            opt.zero_grad()
            loss = model(torch.randn(3,4)).square().mean()
            loss.backward()
            opt.step()
        step(net,optimizer)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'state.pth'
            save(path,net,None,optimizer,1,{'test':True},{'clean':3})
            step(net,optimizer)
            expected = {k:v.clone() for k,v in net.state_dict().items()}
            state = torch.load(path,map_location='cpu',weights_only=False)
            net.load_state_dict(state['model'])
            optimizer.load_state_dict(state['optimizer'])
            p.restore_rng(state)
            step(net,optimizer)
            for key,value in net.state_dict().items():
                self.assertTrue(torch.equal(value,expected[key]))
            self.assertEqual(state['global_step'],1)
            self.assertEqual(state['treatment_counts'],{'clean':3})
            self.assertFalse(path.with_name('state.pth.tmp').exists())

    def test_actual_prefusion_feature_independent_of_dsm(self):
        from model.vit_seg_modeling_resnet_skip import FuseResNetV2
        torch.manual_seed(8)
        net = FuseResNetV2((1,1,1),1).eval()
        features = []
        hook = net.root.register_forward_hook(lambda _m,_i,x:features.append(x.clone()))
        op = torch.rand(1,3,64,64)
        with torch.no_grad():
            first = net(op,torch.zeros(1,1,64,64))[0]
            second = net(op,torch.ones(1,1,64,64))[0]
        hook.remove()
        self.assertTrue(torch.equal(features[0],features[1]))
        self.assertFalse(torch.equal(first,second))


if __name__ == '__main__':
    unittest.main()
