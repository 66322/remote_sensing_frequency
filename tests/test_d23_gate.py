import importlib.util
from pathlib import Path
import unittest
import torch
from torch import nn
from torch.nn import functional as F

spec=importlib.util.spec_from_file_location("gate",Path(__file__).resolve().parents[1]/"model/rebuild_v1_d23_gate.py")
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
torch.set_num_threads(1)


class ToyExpert(nn.Module):
    def __init__(self,auxiliary=False):
        super().__init__()
        self.auxiliary=auxiliary
        self.encoder=nn.Conv2d(3,128,1)
        self.decoder=nn.Sequential(nn.Conv2d(128,128,3,padding=1),nn.GroupNorm(8,128),nn.GELU(),nn.Conv2d(128,6,1))
    def forward(self,op,ds):
        h,w=op.shape[-2:]
        x=F.avg_pool2d(F.pad(op,(0,(-w)%4,0,(-h)%4)),4,4)
        x=self.encoder(x)
        if self.auxiliary: x=x+F.interpolate(ds[:,None],size=x.shape[-2:],mode="nearest")
        return F.interpolate(self.decoder(x),size=(h,w),mode="nearest")


class GateTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(42)
        self.E=torch.randn(2,16,4,5)
        self.S=torch.randn(2,256,4,5)
        self.freq=torch.randn(2,4,4,5)
        self.z0=torch.randn(2,6,16,20)
        self.z1=torch.randn_like(self.z0)
        self.mask=torch.ones(2,16,20,dtype=torch.bool)
        self.mask[:,3:8,2:9]=False

    def gate(self,arm):
        torch.manual_seed(42)
        g=d.DenseBenefitGate(arm)
        if arm=="TCAP": g.set_fit_statistics(torch.zeros(16),torch.ones(16))
        return g

    def test_matched_capacity_and_initialization(self):
        states=[]
        for arm in d.ARMS:
            g=self.gate(arm)
            self.assertEqual(sum(p.numel() for p in g.parameters()),18145)
            states.append({k:v for k,v in g.state_dict().items() if k.startswith("layers.")})
            out=g(self.E,self.S,self.freq,self.z0,self.z1,self.mask)
            self.assertTrue(torch.equal(out["g"],torch.full_like(out["g"],0.5)))
        for state in states[1:]:
            for k in states[0]: self.assertTrue(torch.equal(state[k],states[0][k]))

    def test_input_ablation_and_spatial_correspondence(self):
        g=self.gate("T0")
        self.assertTrue(torch.equal(g.inputs(self.E,self.S,self.freq),g.inputs(self.E,self.S+100,self.freq-100)))
        g=self.gate("TS")
        self.assertTrue(torch.equal(g.inputs(self.E,self.S,self.freq),g.inputs(self.E,self.S,self.freq+100)))
        self.assertTrue(torch.equal(self.gate("TF").inputs(self.E,self.S,self.freq)[:,16:272],d.repeat_channels(self.E,256)))
        x=self.gate("TSF_shuffleS").inputs(self.E,self.S,self.freq)
        self.assertTrue(torch.equal(x[:,16:272],torch.roll(self.S,(2,2),(-2,-1))))
        self.assertTrue(torch.equal(x[:,-4:],self.freq))

    def test_mask_exact_equality_all_gates_and_baselines(self):
        for arm in d.ARMS:
            g=self.gate(arm)
            with torch.no_grad(): g.layers[-1].bias.fill_(20)
            for mask in (self.mask,torch.zeros_like(self.mask)):
                out=g(self.E,self.S,self.freq,self.z0,self.z1,mask)["logits"]
                self.assertTrue(torch.equal(out.permute(0,2,3,1)[~mask],self.z0.permute(0,2,3,1)[~mask]))
        for kind in ("R0","M0_safe","confidence","entropy","logit_average","probability_average"):
            out=d.fixed_blend(self.z0,self.z1,self.mask,kind)
            self.assertTrue(torch.equal(out.permute(0,2,3,1)[~self.mask],self.z0.permute(0,2,3,1)[~self.mask]))

    def test_effective_batch_loss_and_gradient_are_partition_invariant(self):
        raw=torch.randn(2,1,16,20,requires_grad=True)
        z=self.z0+raw.sigmoid()*(self.z1-self.z0)
        label=torch.randint(0,6,(2,16,20));label[:,0,:]=255
        whole=d.combine_loss_sums([d.loss_sums(z,raw,self.z0,self.z1,label,self.mask)])
        parts=[d.loss_sums(z[i:i+1],raw[i:i+1],self.z0[i:i+1],self.z1[i:i+1],label[i:i+1],self.mask[i:i+1]) for i in range(2)]
        split=d.combine_loss_sums(parts)
        self.assertTrue(torch.allclose(whole,split,atol=1e-6))
        a=torch.autograd.grad(whole,raw,retain_graph=True)[0]
        b=torch.autograd.grad(split,raw)[0]
        self.assertTrue(torch.allclose(a,b,atol=1e-7))

    def test_utility_target_signs_and_empty_sets(self):
        label=torch.tensor([[[0,1,255]]])
        z0=torch.zeros(1,6,1,3);z1=z0.clone()
        z0[:,2,:,0]=10;z1[:,0,:,0]=10
        z0[:,1,:,1]=10;z1[:,2,:,1]=10
        raw=torch.zeros(1,1,1,3,requires_grad=True)
        mask=torch.ones_like(label,dtype=torch.bool)
        parts=d.loss_sums(z0,raw,z0,z1,label,mask)
        self.assertEqual((parts["positive"],parts["negative"]),(1,1))
        utility=0.5*(parts["positive_sum"]+parts["negative_sum"])
        grad=torch.autograd.grad(utility,raw)[0]
        self.assertLess(float(grad[0,0,0,0]),0)
        self.assertGreater(float(grad[0,0,0,1]),0)
        self.assertEqual(float(grad[0,0,0,2]),0)
        parts=d.loss_sums(z0,raw,z0,z1,label,torch.zeros_like(mask))
        self.assertEqual((parts["positive"],parts["negative"]),(0,0))
        self.assertTrue(torch.isfinite(d.combine_loss_sums([parts])))

    def test_frozen_expert_hook_and_gate_only_optimization(self):
        r0,m0=ToyExpert(),ToyExpert(True)
        pair=d.FrozenExpertPair(r0,m0)
        before={k:v.clone() for k,v in pair.state_dict().items()}
        pair.train(True)
        self.assertFalse(r0.training);self.assertFalse(m0.training)
        self.assertFalse(any(p.requires_grad for p in pair.parameters()))
        op=torch.randn(2,3,17,19,requires_grad=True)
        ds=torch.rand(2,17,19)
        inputs=pair(op,ds)
        self.assertEqual(inputs["S"].shape,(2,256,5,5))
        self.assertEqual(inputs["F"].shape,(2,4,5,5))
        self.assertFalse(any(x.requires_grad for x in inputs.values()))
        gate=self.gate("TSF");opt=torch.optim.AdamW(gate.parameters(),lr=1e-3)
        mask=torch.ones(2,17,19,dtype=torch.bool);y=torch.randint(0,6,(2,17,19))
        for _ in range(2):
            opt.zero_grad()
            out=gate(inputs["E"],inputs["S"],inputs["F"],inputs["z0"],inputs["z1"],mask)
            loss=d.combine_loss_sums([d.loss_sums(out["logits"],out["gate_logits"],inputs["z0"],inputs["z1"],y,mask)])
            loss.backward();opt.step()
        self.assertIsNone(op.grad)
        self.assertTrue(any(p.grad is not None and bool((p.grad!=0).any()) for p in gate.parameters()))
        for k,v in pair.state_dict().items():self.assertTrue(torch.equal(v,before[k]))
        self.assertTrue(all(p.grad is None for p in pair.parameters()))

    def test_fit_stats_required_and_input_validation(self):
        with self.assertRaisesRegex(RuntimeError,"gate-fit"):
            d.DenseBenefitGate("TCAP").inputs(self.E,self.S,self.freq)
        bad=self.S.clone();bad[0,0,0,0]=float("nan")
        with self.assertRaisesRegex(RuntimeError,"nonfinite"):
            self.gate("TSF").inputs(self.E,bad,self.freq)
        with self.assertRaisesRegex(RuntimeError,"boolean"):
            self.gate("TSF")(self.E,self.S,self.freq,self.z0,self.z1,self.mask.float())

    def test_frequency_constant_signal_and_odd_dimensions(self):
        f=d.frequency_evidence(torch.full((1,3,17,19),0.5),torch.full((1,17,19),0.25))
        self.assertEqual(f.shape,(1,4,5,5))
        self.assertTrue(torch.allclose(f[:,1],torch.zeros_like(f[:,1])))
        self.assertTrue(torch.allclose(f[:,3],torch.zeros_like(f[:,3])))
        self.assertTrue(torch.allclose(f[:,0],torch.full_like(f[:,0],0.5)))
        self.assertTrue(torch.allclose(f[:,2],torch.full_like(f[:,2],0.25)))


if __name__=="__main__": unittest.main()

