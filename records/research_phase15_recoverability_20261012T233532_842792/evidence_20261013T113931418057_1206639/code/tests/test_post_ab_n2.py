"""N2 CPU contracts: equal capacity, relation identity, masks, gradients and base loading."""
import copy,hashlib,importlib.util,json,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import torch
from torch import nn
from torch.nn import functional as F
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from model.post_ab_n2_relation import RelationPropagation,affinities,MODES

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class RelationTests(unittest.TestCase):
    def setUp(self):torch.set_num_threads(1);torch.manual_seed(42)
    def test_capacity_and_gradients_all_six(self):
        counts=[]
        for mode in MODES:
            torch.manual_seed(42);m=RelationPropagation(mode)
            r=torch.randn(2,128,16,16,requires_grad=True);d=torch.randn_like(r,requires_grad=True)
            out=m(r,d,torch.rand(2,64,64),torch.ones(2,16,16,dtype=torch.bool))
            sum(x.square().mean() for x in out).backward()
            self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() and p.grad.abs().sum()>0 for p in m.parameters()))
            self.assertTrue(torch.isfinite(r.grad).all() and torch.isfinite(d.grad).all())
            counts.append(sum(p.numel() for p in m.parameters()))
        self.assertEqual(len(set(counts)),1)
    def test_constant_relations_reduce_to_distance(self):
        r=torch.ones(2,128,5,5);h=torch.ones(2,1,5,5);v=torch.ones(2,5,5,dtype=torch.bool)
        base=affinities(r,h,v,'spatial')
        for mode in MODES:
            wr,wd=affinities(r,h,v,mode)
            torch.testing.assert_close(wr,base[0]);torch.testing.assert_close(wd,base[1])
    def test_height_changes_only_rgb_relation(self):
        r=torch.randn(1,128,5,5);h=torch.arange(25.).reshape(1,1,5,5)/25;v=torch.ones(1,5,5,dtype=torch.bool)
        a=affinities(r,h,v,'height');b=affinities(r,torch.zeros_like(h),v,'height')
        self.assertFalse(torch.equal(a[0],b[0]));torch.testing.assert_close(a[1],b[1])
        a=affinities(r,h,v,'semantic');b=affinities(r,torch.zeros_like(h),v,'semantic')
        torch.testing.assert_close(a[0],b[0]);torch.testing.assert_close(a[1],b[1])
    def test_masked_donors_and_empty_rows(self):
        r=torch.randn(1,128,5,5);h=torch.rand(1,1,5,5);v=torch.ones(1,5,5,dtype=torch.bool);v[:,2,2]=False
        for mode in MODES:
            for w in affinities(r,h,v,mode):
                self.assertEqual(float(w[:,:,2,2].abs().sum()),0.)
                self.assertEqual(float(w[:,4,2,2].abs().sum()),0.)
                self.assertTrue(torch.isfinite(w).all())
            z=affinities(r,h,torch.zeros_like(v),mode)
            self.assertTrue(all(torch.equal(x,torch.zeros_like(x)) for x in z))
    def test_missing_all_blocks_propagation(self):
        r=torch.randn(1,128,16,16);d=torch.randn_like(r)
        for mode in MODES:
            m=RelationPropagation(mode);a,b=m(r,d,torch.rand(1,64,64),torch.zeros(1,16,16,dtype=torch.bool))
            torch.testing.assert_close(a,r,rtol=0,atol=0);torch.testing.assert_close(b,d,rtol=0,atol=0)
    def test_contract_rejects_changed_base_mode_seed(self):
        shim=types.ModuleType('post_ab_queue_common')
        for n in ('read','write','sha','within','now','predecessor_verdict'):setattr(shim,n,lambda *a:None)
        with patch.dict(sys.modules,{'post_ab_queue_common':shim}):m=load(ROOT/'scripts/post_ab_n2_common.py','test_n2_common')
        p=m.runtime_plan({'training':dict(steps=8000,seed=42,physical_batch=16,gradient_accumulation=False,validation_steps=[4000,8000],selection_states=['clean','dsm_missing','rgb_missing']),
            'runtime':{},'data':dict(validation=['3_11','5_10'],test6_loaded=False,independent_final_loaded=False),'physical_gpus':[0,1]},'abc',Path('/home/jovyan/zzx/root/records/research_post_ab_followup_n2_demo'))
        self.assertEqual(len(m.validate_plan(p)),6)
        for key,value in [('relation_mode','semantic'),('seed',17),('initial_checkpoint_sha256','bad')]:
            q=copy.deepcopy(p);q['jobs'][0][key]=value
            with self.assertRaises(ValueError):m.validate_plan(q)
        q=copy.deepcopy(p);q['jobs']=q['jobs'][:4]
        with self.assertRaises(ValueError):m.validate_plan(q)
    def test_model_base_load_and_exact_missing_fallback(self):
        # Real N1/N2 forward wiring with tiny synthetic expert interfaces, no server weights.
        util=types.ModuleType('model.rebuild_v1_d26')
        util.align_feature=lambda x,size:F.interpolate(x,size,mode='nearest')
        util.valid_at=lambda mask,size:(F.adaptive_avg_pool2d(mask[:,None].float(),size)>=1).float()
        class Expert(nn.Module):
            def __init__(self,channels):
                super().__init__();self.channels=channels;self.net=nn.Module()
                self.net.encoder=nn.Module();self.net.encoder.blocks=nn.ModuleList([nn.Identity() for _ in range(12)])
                self.net.transformer=nn.Module();self.net.transformer.encoder=nn.Module();self.net.transformer.encoder.layer=nn.ModuleList([nn.Identity() for _ in range(12)])
                self.feature=nn.Conv2d(channels,128,1);self.head=nn.Conv2d(128,6,1)
            def configure(self,adapt):
                for p in self.parameters():p.requires_grad_(adapt)
            def forward(self,rgb,dsm):
                x=rgb if self.channels==3 else dsm[:,None]
                f=self.feature(F.avg_pool2d(x,4,4));return F.interpolate(self.head(f),rgb.shape[-2:],mode='nearest'),f
        with patch.dict(sys.modules,{'model.rebuild_v1_d26':util}):
            n1=load(ROOT/'model/rebuild_v1_post_ab_n1.py','test_real_n1')
            with patch.dict(sys.modules,{'model.rebuild_v1_post_ab_n1':n1}):n2=load(ROOT/'model/rebuild_v1_post_ab_n2.py','test_real_n2')
        folder=ROOT.parent/'temporary_cpu_test';folder.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=folder) as tmp:
            path=Path(tmp)/'base.pth';base=n1.N1Segmenter(Expert(3),Expert(1),dict(id='N1-2',adaptation='last4_and_heads',information_entry='late'))
            torch.save(dict(global_step=8000,model=base.state_dict()),path)
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            rgb=torch.randn(1,3,64,64);dsm=torch.randn(1,64,64);yes=torch.ones_like(dsm,dtype=torch.bool);no=torch.zeros_like(yes)
            for i,mode in enumerate(MODES):
                m=n2.N2Segmenter(Expert(3),Expert(1),dict(id=f'N2-{i}',relation_mode=mode,initial_checkpoint_path=str(path),initial_checkpoint_sha256=digest))
                for rm,dm in [(yes,no),(no,yes),(no,no),(yes,yes)]:
                    parts=m(rgb,dsm,rm,dm,return_parts=True)
                    if not dm.any():torch.testing.assert_close(parts['logits'],parts['rgb'] if rm.any() else torch.zeros_like(parts['logits']),rtol=0,atol=0)
                    elif not rm.any():torch.testing.assert_close(parts['logits'],parts['dsm'],rtol=0,atol=0)
                    self.assertTrue(torch.isfinite(parts['logits']).all())
            bad=dict(id='N2-0',relation_mode='spatial',initial_checkpoint_path=str(path),initial_checkpoint_sha256='bad')
            with self.assertRaises(RuntimeError):n2.N2Segmenter(Expert(3),Expert(1),bad)
    def test_gate_rejects_unmatched_and_shuffled_advantage(self):
        common=types.ModuleType('post_ab_n2_common')
        for n in ('read','write','now','validate_plan'):setattr(common,n,lambda *a:None)
        common.N2=[f'N2-{i}' for i in range(6)]
        n1=types.ModuleType('summarize_post_ab_n1');n1.cell=lambda *a:None
        old=types.ModuleType('summarize_post_d30')
        def mean(s,cs):return sum(100*s['pooled'][c]['noboundary']['metrics']['candidate']['valid']['mIoU_fg5'] for c in cs)/len(cs)
        def score(s,p):
            v={k:mean(s,cs) for k,cs in p['evaluation']['families'].items()};v['S_available']=sum(v.values())/4;return v
        old.score=score;old.difference=lambda a,b,cs:mean(a,cs)-mean(b,cs)
        old.worst=lambda a,b,cs:min(100*(a['tiles'][c][t]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']-b['tiles'][c][t]['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']) for c in cs for t in ['3_11','5_10'])
        old.retention=lambda *a:{}
        with patch.dict(sys.modules,{'post_ab_n2_common':common,'summarize_post_ab_n1':n1,'summarize_post_d30':old}):m=load(ROOT/'scripts/summarize_post_ab_n2.py','test_n2_screen')
        cs=['clean','qr','qd','qj','dsm_missing','rgb_missing']
        def summary(v):
            metric=lambda:{'candidate':{'valid':{'mIoU_fg5':v}}}
            return dict(pooled={c:{'noboundary':{'metrics':metric()}} for c in cs},tiles={c:{t:{'scopes':{'noboundary':{'metrics':metric()}}} for t in ['3_11','5_10']} for c in cs})
        plan=dict(data={'validation':['3_11','5_10']},evaluation={'primary':cs[:4],'families':dict(C=['clean'],QR=['qr'],QD=['qd'],QJ=['qj'])})
        data={j:dict(evaluation=summary(.86),fixed8000=summary(.86)) for j in common.N2}
        data['N2-3']=dict(evaluation=summary(.87),fixed8000=summary(.87))
        self.assertTrue(m.screen(data,plan)['passed'])
        data['N2-4']=dict(evaluation=summary(.88),fixed8000=summary(.88))
        out=m.screen(data,plan)
        self.assertFalse(out['passed']);self.assertFalse(out['checks']['height_correspondence'])
        data['N2-4']=dict(evaluation=summary(.86),fixed8000=summary(.86))
        data['N2-3']['evaluation']['pooled']['dsm_missing']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']=.85
        self.assertFalse(m.screen(data,plan)['checks']['dsm_missing_floor'])
if __name__=='__main__':unittest.main()
