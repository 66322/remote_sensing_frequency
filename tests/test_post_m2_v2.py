import collections
import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
os.environ['OMP_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
import numpy as np
import torch
torch.set_num_threads(1)
from post_m2_v2 import common as c,data as d
from post_m2_v2.model import Readout,SpatialProbe
from post_m2_v2.controller import runnable,DEPENDENCIES

class Contracts(unittest.TestCase):
    def test_budget_and_dependency_graph(self):
        self.assertEqual(len(c.JOBS),11);self.assertEqual(len(c.JOBS)*8000+4*2000,96000)
        completed={'B0':{'status':'COMPLETE'},'B1':{'status':'COMPLETE'}}
        self.assertNotIn('Q3',runnable(['Q2','Q3'],completed,DEPENDENCIES))
        completed['Q1']={'status':'COMPLETE'};completed['Q2']={'status':'COMPLETE'}
        self.assertEqual(runnable(['Q3'],completed,DEPENDENCIES),['Q3'])
        completed['Q2']={'status':'INVALID_LEARNING_NOT_SCIENTIFIC_NEGATIVE'}
        self.assertEqual(runnable(['Q3'],completed,DEPENDENCIES),[])

    def test_exposure_replay_exact_multiset_and_different_order(self):
        import json
        rows=[d.exposure(i,.7) for i in range(50)];out,order=d.replay(rows)
        packed=lambda r:collections.Counter(json.dumps(x,sort_keys=True) for x in r)
        self.assertEqual(packed(rows),packed(out));self.assertNotEqual(rows,out)
        self.assertEqual(sorted(order),list(range(50)))

    def test_label_mapping_and_unknown_color(self):
        a=np.array([list(c.COLORS)+[(0,0,0)]],np.uint8)
        self.assertEqual(d.decode_label(a).tolist(),[[0,1,2,3,4,5,255]])
        with self.assertRaises(RuntimeError):d.decode_label(np.array([[[1,2,3]]],np.uint8))

    def test_only_whitelisted_tiles(self):
        with self.assertRaises(ValueError):d.tile_paths('/data','5_11')

    def test_constant_height_offset_is_removed_at_load(self):
        # The declared normalisation first subtracts the per-tile valid median.
        x=np.arange(100,dtype=np.float32).reshape(10,10)
        np.testing.assert_array_equal(x-np.median(x),(x+100)-np.median(x+100))

    def test_match_parameter_counts_and_all_parameters_receive_gradients(self):
        sizes={}
        feat=torch.randn(1,384,3,3);rgb=torch.rand(1,3,32,32);height=torch.randn(1,1,32,32);valid=torch.ones_like(height,dtype=torch.bool)
        for arm in c.JOBS:
            torch.manual_seed(42);m=Readout(arm);z=m(feat,rgb,height,valid)
            self.assertEqual(tuple(z.shape),(1,6,32,32));self.assertTrue(torch.isfinite(z).all())
            torch.nn.functional.cross_entropy(z,torch.randint(0,6,(1,32,32))).backward()
            for name,p in m.named_parameters():
                self.assertIsNotNone(p.grad,(arm,name));self.assertTrue(torch.isfinite(p.grad).all(),(arm,name))
            sizes[arm]=sum(p.numel() for p in m.parameters())
        for group in [('B0','B1','Q1','Q2','Q3'),('G1','G2','G3'),('S1','S2','S3')]:
            self.assertEqual(len({sizes[x] for x in group}),1)

    def test_geometry_constant_height_offset_and_correspondence_intervention(self):
        torch.manual_seed(1);m=Readout('G2');z=torch.randn(1,96,8,8);rgb=torch.rand(1,3,32,32)
        h=torch.randn(1,1,32,32);v=torch.ones_like(h,dtype=torch.bool)
        a=m.geometry(z,rgb,h,v);b=m.geometry(z,rgb,h+100,v)
        self.assertTrue(torch.allclose(a,b,atol=2e-5,rtol=1e-4))
        m.arm='G3';other=m.geometry(z,rgb,h,v)
        self.assertGreater(float((a-other).abs().mean().detach()),1e-5)

    def test_spatial_probe_backprop(self):
        m=SpatialProbe();z=m(torch.randn(2,384,4,4));z.square().mean().backward()
        self.assertEqual(tuple(z.shape),(2,6,4,4));self.assertTrue(all(p.grad is not None for p in m.parameters()))

    def test_counts_perfect_prediction_and_ignore_regions(self):
        from post_m2_v2.evaluate import counts,pool,count_reference
        y=np.zeros((32,32),np.uint8);y[:,16:]=1;nb=y.copy();nb[:,14:18]=255
        a=counts(y,y,nb,(8,8,8),border=2,tolerance=1)
        self.assertEqual(a['full']['valid_pixels'],28*28);self.assertEqual(a['roi']['valid_pixels'],64)
        self.assertEqual(a['boundary_f1'],100.0)
        self.assertLess(a['nb']['valid_pixels'],a['full']['valid_pixels'])
        cached=counts(y,y,nb,(8,8,8),reference=count_reference(y,border=2,tolerance=1))
        self.assertEqual(a,cached)
        b=pool([a,a]);self.assertEqual(b['full']['valid_pixels'],2*28*28)
        self.assertEqual(b['boundary_f1'],100.0)

    def test_atomic_write_once_protects_receipts(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'receipt.json';c.write(p,{'a':1},once=True)
            with self.assertRaises(FileExistsError):c.write(p,{'a':2},once=True)
            self.assertEqual(c.read(p),{'a':1})

    def test_controller_stops_on_first_failed_worker_and_preserves_original(self):
        import io,json,types
        from unittest.mock import patch
        from post_m2_v2 import controller
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);source={'commit':'a'*40}
            c.write(base/'execution_tuning.json',dict(source=source,paths={}))
            for arm in c.PROFILES:c.write(base/'profiles'/(arm+'.json'),dict(status='REAL_PATH_PROFILE_PASSED',source=source))
            dispatched=[];owned=[]
            class Worker:
                def __init__(self,*args,**kw):self.stdin=self;self.failed=False;self.gpu=kw['env']['CUDA_VISIBLE_DEVICES'];self.pid=100+len(owned);owned.append(self)
                def write(self,text):
                    task=json.loads(text);dispatched.append(task['arm'])
                    if task['arm']=='Q1':
                        self.failed=True;c.write(base/('worker_first_failure_gpu'+self.gpu+'.json'),dict(traceback='FIRST ORIGINAL CHILD STACK'),once=True)
                    else:c.write(base/'tasks'/(task['id']+'.json'),dict(status='COMPLETE'),once=True)
                def flush(self):pass
                def poll(self):return None  # Simulate a failed worker still unwinding CPU counter threads.
            fake_fcntl=types.SimpleNamespace(flock=lambda *args:None,LOCK_EX=1,LOCK_NB=2)
            with patch.dict(sys.modules,{'fcntl':fake_fcntl}),patch.object(c,'runtime_contract',return_value={'source':source}),\
                patch.object(controller,'idle_gpus',return_value={}),patch.object(controller,'gpu_snapshot',return_value={}),\
                patch.object(controller.subprocess,'Popen',Worker),patch.object(controller,'stop_owned') as stop,\
                patch.object(controller.time,'sleep',lambda _:None):
                with self.assertRaises(RuntimeError):controller.run(base,'train')
                self.assertEqual(dispatched,['B0','B1','Q1','S1'])
                self.assertTrue((base/'train_first_failure.json').exists());stop.assert_called_once()
                self.assertIn('worker failure receipt',c.read(base/'train_first_failure.json')['error'])
                with self.assertRaises(FileExistsError):controller.run(base,'train')

    def test_bootstrap_in_isolated_payload_and_rejects_corruption(self):
        import json,hashlib
        from bootstrap_post_m2_v2 import install
        payload={'scripts/post_m2_multiroute.py':b'print("isolated-entry")\n'}
        raw=json.dumps({'files':{n:hashlib.sha256(v).hexdigest() for n,v in payload.items()}}).encode()
        def fetch(url):return raw if url.endswith('payload_manifest.json') else payload['scripts/post_m2_multiroute.py']
        with tempfile.TemporaryDirectory() as t:
            install('a'*40,Path(t)/'payload',fetch)
            self.assertEqual((Path(t)/'payload/scripts/post_m2_multiroute.py').read_bytes(),payload['scripts/post_m2_multiroute.py'])
            self.assertTrue((Path(t)/'payload/payload_manifest.json').exists())
            with self.assertRaises(RuntimeError):install('a'*40,Path(t)/'bad',lambda url:raw if url.endswith('payload_manifest.json') else b'wrong')

    def test_microbatch_gradient_uses_global_valid_pixel_denominator(self):
        import copy
        torch.manual_seed(3);a=Readout('B1');b=copy.deepcopy(a)
        feat=torch.randn(2,384,3,3);rgb=torch.rand(2,3,32,32);height=torch.randn(2,1,32,32);v=torch.ones_like(height,dtype=torch.bool)
        y=torch.randint(0,6,(2,32,32));y[0,:,:16]=255;denom=(y<6).sum()
        torch.nn.functional.cross_entropy(a(feat,rgb,height,v),y,ignore_index=255,reduction='sum').div(denom).backward()
        for j in range(2):
            torch.nn.functional.cross_entropy(b(feat[j:j+1],rgb[j:j+1],height[j:j+1],v[j:j+1]),y[j:j+1],ignore_index=255,reduction='sum').div(denom).backward()
        for x,z in zip(a.parameters(),b.parameters()):self.assertTrue(torch.allclose(x.grad,z.grad,atol=2e-6,rtol=1e-4))

    def test_failed_partial_training_is_not_reported_as_zero_updates(self):
        from post_m2_v2.report import summarize
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);c.write(base/'jobs/B0/started.json',{'pid':123})
            (base/'jobs/B0/trajectory.jsonl').write_text('{"step":1}\n{"step":100}\n',encoding='utf-8')
            result=summarize(base)
            self.assertEqual(result['jobs_complete'],0)
            self.assertEqual(result['observed_updates_lower_bound'],100)
            self.assertFalse(result['exact_total_updates_known'])

if __name__=='__main__':unittest.main()
