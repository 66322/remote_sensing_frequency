import sys
from pathlib import Path
import unittest
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import d23_engine as e
import d23_lifecycle as life
from model import rebuild_v1_d23_gate as g


class Pair(nn.Module):
    def __init__(self):super().__init__();self.batches=[]
    def forward(self,op,ds):
        self.batches.append(len(op))
        z0=torch.stack((op[:,0],-op[:,0],ds,-ds,ds*0,ds*0),1)
        z1=z0.flip(1)
        low0,low1=F.avg_pool2d(z0,4),F.avg_pool2d(z1,4)
        return dict(z0=z0,z1=z1,E=g.output_evidence(low0,low1),
                    S=torch.zeros(len(op),256,*low0.shape[-2:]),F=g.frequency_evidence(op,ds))


class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):torch.set_num_threads(1)
    def test_single_backward_with_frozen_experts_micro8_gate16(self):
        torch.manual_seed(42);pair=Pair();gate=g.DenseBenefitGate('TSF')
        calls=[];handle=gate.layers[0].register_forward_pre_hook(lambda m,x:calls.append(len(x[0])))
        op=torch.rand(16,3,8,8);ds=torch.rand(16,8,8);mask=torch.ones_like(ds,dtype=torch.bool)
        gt=torch.randint(0,6,(16,8,8));treated=(op,ds*0,mask&False)
        logical=((op,ds,mask),treated,gt)
        optimizer=torch.optim.SGD(gate.parameters(),lr=0.)
        value,counts=e.fit_update(pair,gate,optimizer,logical,g.loss_sums,device='cpu',combine=g.combine_loss_sums)
        handle.remove();grad=[p.grad.clone() for p in gate.parameters()]
        self.assertEqual(pair.batches,[8,8,8,8]);self.assertEqual(calls,[16,16])
        optimizer.zero_grad();parts=[]
        for view in logical[:2]:
            inp=pair(view[0],view[1]);out=gate(inp['E'],inp['S'],inp['F'],inp['z0'],inp['z1'],view[2])
            parts.append(g.loss_sums(out['logits'],out['gate_logits'],inp['z0'],inp['z1'],gt,view[2]))
        loss=g.combine_loss_sums(parts);loss.backward()
        self.assertAlmostEqual(value,float(loss),places=6)
        for a,p in zip(grad,gate.parameters()):torch.testing.assert_close(a,p.grad)
        self.assertEqual(counts['valid'],2048)

    def test_stitch_tail_padding_and_exact_missing_fallback(self):
        pair=Pair();op=np.random.default_rng(42).random((12,12,3),dtype=np.float32)
        ds=np.ones((12,12),np.float32);mask=np.ones((12,12),bool);mask[2:5]=False
        scores=e.infer(pair,{'M0_safe':None,'probability_average':None},op,ds,mask,g.fixed_blend,
                       patch=8,stride=4,batch=8,device='cpu')
        self.assertEqual(pair.batches,[8])
        for name,z in scores.items():np.testing.assert_array_equal(z[:,~mask],scores['R0'][:,~mask])
        # Center appears in all four windows; original semantics sum their logits.
        self.assertAlmostEqual(float(scores['R0'][0,6,6]),4*float(op[6,6,0]),places=6)

    def test_statistics_matches_direct_and_ignores_partition(self):
        x=torch.rand(8,16,4,4);m=e.Moments();m.add(x[:3]);m.add(x[3:])
        direct=x.double().permute(1,0,2,3).reshape(16,-1)
        torch.testing.assert_close(torch.tensor(m.result()['mean'],dtype=torch.float64),direct.mean(1))
        torch.testing.assert_close(torch.tensor(m.result()['std'],dtype=torch.float64),direct.std(1,unbiased=False))

    def test_masks_stress_geometry_and_rng(self):
        op=torch.ones(1,3,16,16);ds=torch.arange(256).reshape(1,16,16).float()/256
        _,shift,mask=e.treatment(op,ds,'aux_shift16',42)
        self.assertTrue(mask.all());torch.testing.assert_close(shift,ds[:,:,:1].expand_as(ds))
        _,_,mask=e.treatment(op,ds,'aux_local_zero_stripe_eighth',42)
        self.assertEqual(int((~mask).sum()),32)
        for kind in ('aux_noise_std010','aux_noise_std020'):
            a=e.treatment(op,ds,kind,42,numpy_noise=kind.endswith('020'))
            b=e.treatment(op,ds,kind,42,numpy_noise=kind.endswith('020'))
            torch.testing.assert_close(a[1],b[1],rtol=0,atol=0)

    def test_counting_ignore_and_harm_rescue_by_region(self):
        gt=np.array([[0,1,255],[2,3,4]],np.uint8);ref=np.array([[0,0,5],[2,0,4]],np.uint8)
        pred=np.array([[1,1,5],[2,3,4]],np.uint8);mask=np.array([[True,True,False],[False,True,True]])
        r=e.count_result(gt,pred,ref,mask)
        self.assertEqual(np.array(r['cm']).sum(),5);self.assertEqual(r['all'],dict(valid=5,harm=1,rescue=2))
        self.assertEqual(r['missing']['valid'],1)
        pooled=life.pool([r,r])
        self.assertEqual(np.asarray(pooled['cm']).sum(),10)
        self.assertEqual(pooled['all'],dict(valid=10,harm=2,rescue=4))
        self.assertEqual(pooled['support'],[2,2,2,2,2,0])

    def test_split_fit_heldout_and_test_are_disjoint(self):
        train=['6_10','7_10','4_11','7_11']+['tile'+str(i) for i in range(12)]
        fit,held=e.partition(dict(train16=train,val2=['3_11','5_10'],historical_exposed_test6=['4_10']))
        self.assertEqual(len(fit),12);self.assertFalse(set(fit)&set(held))
        with self.assertRaises(RuntimeError):e.partition(dict(train16=train,val2=['3_11','5_10'],historical_exposed_test6=['6_10']))

    def test_keyed_sample_plan_cache_does_not_load_forbidden_tiles(self):
        aug=dict(random_scale_min=.5,random_scale_max=2.,vertical_flip_p=.5,horizontal_flip_p=.5)
        a=[e.sample_spec(['2_12','2_10'],i,aug) for i in range(16)]
        b=sum(([e.sample_spec(['2_12','2_10'],i,aug) for i in range(j,j+8)] for j in (0,8)),[])
        self.assertEqual(a,b)
        cache=e.TileCache(lambda t:None,['2_12'])
        with self.assertRaises(RuntimeError):cache.get('3_11')

if __name__=='__main__':unittest.main()
