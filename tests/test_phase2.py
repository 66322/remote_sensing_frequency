import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import tempfile
import unittest
import numpy as np
import torch
from torch import nn
from phase2_common import compact_save,compact_load,key
from phase2_data import panel,case_id,training_view,batch_hash
from model.phase2_matched import MatchedExpert,FusionHead,observables,factor

class Encoder(nn.Module):
    def __init__(self):
        super().__init__();self.blocks=nn.ModuleList([nn.Linear(384,384) for _ in range(12)]);self.norm=nn.LayerNorm(384)
    def forward_features(self,x):
        t=torch.nn.functional.avg_pool2d(x.mean(1,keepdim=True),14).flatten(2).transpose(1,2).expand(-1,-1,384)
        for b in self.blocks:t=torch.tanh(b(t))
        return {'x_norm_patchtokens':self.norm(t)}

class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):torch.set_num_threads(1)
    def test_scope_and_matching(self):
        torch.manual_seed(42);a=MatchedExpert(Encoder());torch.manual_seed(42);b=MatchedExpert(Encoder())
        self.assertTrue(all(torch.equal(a.state_dict()[n],v) for n,v in b.state_dict().items()))
        names={n for n,p in a.named_parameters() if p.requires_grad}
        self.assertTrue(all(n.startswith(('encoder.blocks.8.','encoder.blocks.9.','encoder.blocks.10.','encoder.blocks.11.','rgb.','decoder.')) for n in names))
        self.assertFalse(a.encoder.norm.weight.requires_grad)
        x=torch.rand(2,3,56,56);a.train();low=a.low(x);z=a(x)
        self.assertTrue(torch.equal(z,torch.nn.functional.interpolate(low,(56,56),mode='nearest')))
        z.square().mean().backward()
        self.assertTrue(all(p.grad is not None for n,p in a.named_parameters() if p.requires_grad))
        self.assertTrue(all(p.grad is None for n,p in a.named_parameters() if not p.requires_grad))
    def test_head_fallback_and_controls(self):
        r=torch.randn(2,6,8,8);d=torch.randn_like(r);obs=torch.rand(2,12,8,8)
        rm=torch.ones(2,32,32,dtype=torch.bool);dm=rm.clone();rm[:,:16]=False;dm[:,16:24]=False
        for arm in ('B0','B1','B2','B3'):
            torch.manual_seed(42);h=FusionHead(arm);z=h(r,d,obs,rm,dm)
            ar=torch.nn.functional.interpolate(r,(32,32),mode='nearest');ad=torch.nn.functional.interpolate(d,(32,32),mode='nearest')
            self.assertTrue(torch.equal(z[(~rm&dm)[:,None].expand_as(z)],ad[(~rm&dm)[:,None].expand_as(z)]))
            self.assertTrue(torch.equal(z[(rm&~dm)[:,None].expand_as(z)],ar[(rm&~dm)[:,None].expand_as(z)]))
        h=FusionHead('B2');self.assertTrue(torch.equal(h.low(r,d,obs),h.low(r,d,torch.cat((torch.randn_like(obs[:,:10]),obs[:,10:]),1))))
    def test_observable_no_hidden_metadata(self):
        r=torch.rand(2,6,8,8);d=torch.rand_like(r);rgb=torch.rand(2,3,32,32);ds=torch.rand(2,32,32);m=torch.ones_like(ds,dtype=torch.bool)
        o=observables(r,d,rgb,ds,m,m);self.assertEqual(o.shape,(2,12,8,8));self.assertTrue(torch.isfinite(o).all())
        self.assertTrue((o[:,:2]>=0).all());self.assertTrue((o[:,:2]<=1).all())
    def test_budget_panel_no_new_mask_ids(self):
        self.assertEqual(len(panel(8000)),322);self.assertEqual(len(panel(16000)),1122)
        self.assertEqual(len({case_id(c) for c in panel(16000)}),1122)
        self.assertEqual(factor(16000,16000),0);self.assertEqual(factor(8000,8000),0)
        with self.assertRaises(ValueError):factor(16001,16000)
    def test_lossless_compact_support(self):
        with tempfile.TemporaryDirectory() as d:
            a=np.arange(63,dtype=np.uint8).reshape(7,9)%6;a[0,0]=255
            row=compact_save(Path(d)/'labels.npy',a,'labels3');self.assertTrue(np.array_equal(a,compact_load(row)))
            b=a%2==0;row=compact_save(Path(d)/'mask.npy',b,'bool');self.assertTrue(np.array_equal(b,compact_load(row)))
    def test_stream_hash_invariance(self):
        self.assertEqual(batch_hash(['a','b']),batch_hash(['a','b']))
        self.assertNotEqual(batch_hash(['a','b']),batch_hash(['b','a']))
        self.assertNotEqual(key(42,'phase21',1,0),key(42,'phase23',1,0))
    def test_pool_before_metric(self):
        from phase2_analysis import scores
        from structured_v0_metrics import metric
        a=np.diag([1000,10,10,10,10,10]);a[0,1]=100
        b=np.diag([10,1000,10,10,10,10]);b[1,0]=500
        def row(tile,m):
            return dict(case=dict(tile=tile,panel='P-U',direction='rgb',family='pixel',realization=1,ratio=25,damage='zero'),
                        matrices={'noboundary':{'candidate':{'all':m.tolist()}}})
        self.assertAlmostEqual(scores([row('3_11',a),row('5_10',b)],'candidate'),100*metric(a+b))
        self.assertNotAlmostEqual(scores([row('3_11',a),row('5_10',b)],'candidate'),50*(metric(a)+metric(b)))
    def test_cpu_evidence_and_illegal_oracle(self):
        from phase2_common import write,binding
        from phase2_analysis import analyze_case
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            for n in ('plan.json','prepared.json','code_manifest.json'):write(base/n,{})
            gt=(np.arange(400).reshape(20,20)%6).astype(np.uint8);rm=np.zeros_like(gt,bool);dm=~rm
            rgb=gt.copy();dsm=(gt+1)%6;pred=dsm.copy();mask=np.ones_like(rm)
            inputs={s+'_gt':{'path':str(base/(s+'.npy'))} for s in ('full','noboundary')}
            for s in ('full','noboundary'):np.save(base/(s+'.npy'),gt)
            write(base/'input_manifest.json',{'arrays':{'3_11':inputs}})
            out=base/'one';out.mkdir()
            arrays={n:compact_save(out/(n+'.npy'),v,'bool' if v.dtype==bool else 'labels3') for n,v in
                    dict(rgb=rgb,dsm=dsm,pred=pred,rm=rm,dm=dm,mask=mask,entropy_bin=np.ones_like(gt)).items()}
            write(out/'arrays.json',dict(case=dict(tile='3_11',panel='P-M'),system='average',age=16000,arrays=arrays,fallback_exact=True,binding=binding(base)))
            path=Path(analyze_case(base,out));data=__import__('json').loads(path.read_text())
            unrestricted=np.array(data['matrices']['noboundary']['oracle']['all'])
            legal=np.array(data['matrices']['noboundary']['availability_oracle']['all'])
            self.assertEqual(int(unrestricted.trace()),400);self.assertEqual(int(legal.trace()),0)
    def test_training_view_fixed_quota(self):
        batch={'rgb':torch.rand(16,3,512,512),'dsm':torch.rand(16,512,512)}
        a=training_view(batch,1);b=training_view(batch,1)
        self.assertTrue(all(torch.equal(x,y) for x,y in zip(a[:4],b[:4])))
        from collections import Counter
        self.assertEqual(Counter(a[4])['clean'],2);self.assertEqual(Counter(a[4])['full_rgb'],1)
        for i,k in enumerate(a[4]):
            if k.startswith(('reported','full')):
                m=a[2][i] if k.endswith('rgb') else a[3][i]
                self.assertEqual(int((~m).sum()),512*512 if k.startswith('full') else 512*512//4)
    def test_learnability_and_static_residual_stop(self):
        import copy
        from unittest.mock import patch
        from phase2_common import array_save
        from phase2_analysis import gates,static_gate
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);values=[]
            weak=np.zeros((6,6),np.int64);strong=weak.copy()
            for c in range(5):
                weak[c,c]=3200;weak[c,(c+1)%5]=4800
                strong[c,c]=6400;strong[c,(c+1)%5]=1600
            packed={}
            for tail,sl in (('rgb',slice(0,20000)),('dsm',slice(20000,40000))):
                keep=np.zeros(40000,bool);keep[sl]=True
                packed[tail]=array_save(base/(tail+'.npy'),np.packbits(keep,bitorder='little'))
            for tile in ('3_11','5_10'):
                for dr in ('rgb','dsm'):
                    for i in range(1,21):
                        prefs={tail:dict(valid=20000,rgb_correct=16000 if tail=='rgb' else 0,
                            dsm_correct=16000 if tail=='dsm' else 0,both_wrong=4000,coordinates=packed[tail]) for tail in packed}
                        values.append(dict(case=dict(tile=tile,panel='P-U',direction=dr,family='pixel',realization=i,ratio=25,damage='zero'),
                            preference=prefs,fallback_exact=True,matrices={'noboundary':{n:{'all':m.tolist()} for n,m in
                            [('rgb',weak),('dsm',weak),('candidate',weak),('oracle',strong)]}}))
                values.append(dict(case=dict(tile=tile,panel='clean',direction='none',family='clean',realization=0,ratio=0,damage='clean'),
                    preference={},fallback_exact=True,matrices={'noboundary':{'candidate':{'all':weak.tolist()}}}))
            with patch('phase2_analysis.rows',return_value=values):
                result=gates(base)
                self.assertTrue(result['C']);self.assertTrue(result['L'])
            static=copy.deepcopy(values)
            for row in static:row['matrices']['noboundary']['candidate']['all']=strong.tolist()
            with patch('phase2_analysis.rows',side_effect=lambda base,system='average':values if system=='average' else static):
                result=static_gate(base)
                self.assertFalse(result['allow_dynamic'])
                self.assertTrue(all(abs(x)<1e-8 for x in result['residual_diagnostic_gap'].values()))
            bad=copy.deepcopy(values)
            for row in bad:
                if row['case']['panel']=='P-U':row['preference']['rgb'].update(rgb_correct=10000,both_wrong=10000)
            with patch('phase2_analysis.rows',return_value=bad):
                result=gates(base)
                self.assertTrue(result['C']);self.assertFalse(result['L'])

if __name__=='__main__':unittest.main()
