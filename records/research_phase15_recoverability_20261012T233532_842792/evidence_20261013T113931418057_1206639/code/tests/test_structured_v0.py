"""CPU known-answer and scheduling tests; no real images, weights or CUDA."""
import json
import sys
import tempfile
import contextlib
import io
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from structured_v0_common import JOBS, ready_jobs, blocked, write, read, Released, poll
from structured_v0_masks import canonical, raster, rectangle_sums, supports, rng_for, match_indices, semantic_error, availability_diagnostics
from structured_v0_metrics import cm, metric, difference, transitions, evidence
from control_structured_v0 import predecessor_verdict, dispatch
from summarize_structured_v0 import classify, interval


class Scheduling(unittest.TestCase):
    def exercise(self, release=False, fail=False):
        with tempfile.TemporaryDirectory() as temp:
            b=Path(temp)/'new';old=Path(temp)/'old'
            write(b/'plan.json',dict(predecessor=str(old)))
            (b/'logs').mkdir();(b/'code').mkdir()
            state=dict(jobs={n:dict(status='PENDING') for n in JOBS})
            started=[];resumed=False
            class Process:
                pid=12345
                def __init__(self,cmd,**kw):
                    nonlocal resumed
                    self.job=cmd[cmd.index('--job')+1]
                    self.gpu=int(cmd[cmd.index('--gpu')+1])
                    self.resume='--resume' in cmd
                    started.append((self.job,self.gpu,self.resume))
                    folder=b/'jobs'/self.job;folder.mkdir(parents=True,exist_ok=self.resume)
                    self.rc=0
                    if fail and self.job=='clean_3_11':self.rc=2
                    elif release and self.job=='clean_3_11' and not self.resume:
                        self.rc=75
                        write(folder/'paused.json',dict(user=True))
                        write(b/'control/gpu_0.json',dict(blocked=True,requested_at='2026-10-11T23:00:00+08:00'))
                    else:write(folder/'complete.json',{})
                    if self.resume:resumed=True
                def poll(self):return self.rc
                def wait(self,timeout=None):return self.rc
            with patch('control_structured_v0.accept',return_value={}), contextlib.redirect_stdout(io.StringIO()):
                if fail:
                    with self.assertRaises(RuntimeError):dispatch(b,state,{},popen=Process,sleep=lambda _:None,available=lambda g,u:'uuid'+str(g))
                else:dispatch(b,state,{},popen=Process,sleep=lambda _:None,available=lambda g,u:'uuid'+str(g))
            if fail:
                self.assertEqual(len(started),2)
                self.assertTrue((b/'control/stop_all.json').exists())
            else:
                self.assertTrue(all(r['status']=='COMPLETE' for r in state['jobs'].values()))
                self.assertEqual(len(started),43 if release else 42)
                if release:
                    self.assertTrue(resumed)
                    self.assertIn(('clean_3_11',1,True),started)
                    self.assertEqual(sum(g==0 for _,g,_ in started),1)
                else:self.assertEqual(set(g for _,g,_ in started),{0,1})

    def test_two_cards(self):self.exercise()
    def test_release_resume_other_card(self):self.exercise(release=True)
    def test_failed_job_no_retry(self):self.exercise(fail=True)


class KnownAnswers(unittest.TestCase):
    def test_shared_weight_forward_and_zero_fill(self):
        import torch
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
        from test_post_s1_support import Expert, inputs
        from model.rebuild_v1_post_ab_n1 import N1Segmenter
        from model.post_n5_cross_paths import CrossPaths
        torch.manual_seed(42)
        native=N1Segmenter(Expert(True),Expert(False),dict(id='N1-2',information_entry='late',adaptation='last4_and_heads')).eval()
        wrapper=CrossPaths(native,'A1B1C0').eval()
        rgb,ds,rm,dm=inputs();full=torch.ones_like(rm)
        with torch.inference_mode():
            clean=native(rgb,ds,full,full)
            for path in ('A1B1C0','A1B0C0'):
                wrapper.set_path(path)
                self.assertTrue(torch.equal(clean,wrapper(rgb,ds,full,full)))
            wrapper.set_path('A1B0C0')
            damaged=rgb.masked_fill(~rm[:,None],0)
            a=wrapper(rgb,ds,rm,dm)
            b=wrapper(damaged,ds,rm,dm)
            self.assertTrue(torch.equal(a,b))
            self.assertIs(wrapper.base,native)

    def test_prediction_archive_and_binding(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
        from run_structured_v0 import save_array,prediction
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);a=np.arange(6,dtype=np.uint8).reshape(2,3)
            digest=save_array(p/'x.npz',a)
            write(p/'x.json',dict(prediction_file='x.npz',prediction_sha256=digest))
            np.testing.assert_array_equal(a,prediction(p/'x.json'))
            (p/'x.npz').write_bytes(b'changed')
            with self.assertRaises(RuntimeError):prediction(p/'x.json')

    def test_rng_canonical(self):
        np.testing.assert_array_equal(rng_for('3_11',1,'pixel').integers(100,size=30),rng_for('3_11',1,'pixel').integers(100,size=30))
        a=np.zeros((4,5),bool);a[0,0]=1
        self.assertEqual(canonical(a),canonical(a.astype(np.uint8)))
        self.assertNotEqual(canonical(a),canonical(a.T))

    def test_rectangles(self):
        rects=[(1,2,2),(5,5,3)]
        mask=raster((10,10),rects)
        self.assertEqual(mask.sum(),13)
        self.assertEqual(rectangle_sums(np.ones((10,10)),rects).tolist(),[4,9])
        with self.assertRaises(ValueError):raster((10,10),[(0,0,4),(1,1,2)])
        with self.assertRaises(ValueError):raster((10,10),[(9,9,2)])
        self.assertEqual(549*128**2+72**2,6000**2//4)

    def test_semantic_match(self):
        hist=np.eye(6,dtype=np.int64)*100
        target=hist[[0,1,2]].sum(0)
        ix, report=match_indices(hist,np.array([0,1,3]),target,np.zeros(6),300,np.random.default_rng(2),10000)
        self.assertLessEqual(semantic_error(hist[ix].sum(0),target,300),1)
        with self.assertRaises(RuntimeError):match_indices(hist,np.array([0,1,3]),target,np.zeros(6),300,np.random.default_rng(2),0)

    def test_empty_healthy(self):
        m=np.zeros((20,20),bool);m[::2,::2]=1
        s=supports(m)
        self.assertEqual(s['healthy'].sum(),0)
        gt=np.zeros(m.shape,np.uint8)
        r=transitions(gt,gt,gt,s['healthy'])
        self.assertIsNone(r['flip_rate']);self.assertIsNone(r['harm_rate'])

    def test_integer_counts(self):
        gt=np.array([[0,0,1],[1,4,5]],np.uint8)
        pred=np.array([[0,1,1],[0,4,5]],np.uint8)
        m=np.ones_like(gt,bool)
        c=cm(gt,pred,m)
        self.assertEqual(c.dtype,np.int64)
        self.assertEqual(c[0,1],1);self.assertEqual(c[1,0],1);self.assertEqual(c.sum(),6)
        r=transitions(gt,gt,pred,m)
        self.assertEqual(r['harmed'],2);self.assertEqual(r['rescued'],0)
        reverse=transitions(gt,pred,gt,m)
        self.assertEqual(reverse['rescued'],2)

    def test_fixed_classes_and_same_support(self):
        a=np.eye(6,dtype=np.int64)*10;b=a.copy();b[4,4]=0;b[4,0]=10
        self.assertGreater(difference(a,b),0)
        self.assertGreater(difference(a,b,classes=(0,1,2,3)),0) # Car FP affects class 0 too.
        self.assertIsNone(metric(np.zeros((6,6),np.int64)))
        gt=np.arange(6,dtype=np.uint8).reshape(2,3)
        region=gt<3;pred=gt.copy();pred[gt>=3]=0
        np.testing.assert_array_equal(cm(gt,gt,region),cm(gt,pred,region))

    def test_pool_before_nonlinear_metric(self):
        a=np.eye(6,dtype=np.int64)*100;b=np.eye(6,dtype=np.int64)
        b[0,0]=0;b[0,1]=1
        self.assertNotAlmostEqual(metric(a+b),(metric(a)+metric(b))/2)

    def test_mask_support_scales_and_windows(self):
        a=np.zeros((32,32),bool);a[::2,::2]=True
        row=availability_diagnostics(a,window=16,stride=8)
        self.assertEqual(row['windows'],9)
        self.assertEqual(row['masked_path_full_valid_pooling']['4']['valid'],0)
        self.assertEqual(sum(row['missing_pixel_distance_histogram']),int(a.sum()))

    def test_predecessor_holds(self):
        s=dict(status='RUNNING',jobs={str(i):dict(status='PENDING') for i in range(8)})
        self.assertEqual(predecessor_verdict(s,True,True,False),'WAITING_PREDECESSOR')
        self.assertEqual(predecessor_verdict(s,False,False,True),'HOLD_PREDECESSOR')
        s['status']='PAIRED_COMPLETE_AWAITING_REVIEW'
        for r in s['jobs'].values():r['status']='COMPLETE'
        self.assertEqual(predecessor_verdict(s,False,False,False),'WAITING_PREDECESSOR_RELEASE')
        self.assertEqual(predecessor_verdict(s,False,False,True),'READY')

    def test_clean_stage_barrier(self):
        s=dict(jobs={n:dict(status='PENDING') for n in JOBS})
        self.assertEqual(ready_jobs(s),['clean_3_11','clean_5_10'])
        for n in list(s['jobs'])[:2]:s['jobs'][n]['status']='COMPLETE'
        self.assertEqual(len(ready_jobs(s)),40)
        s['jobs']['pair_02_3_11']['status']='PAUSED_USER'
        self.assertEqual(ready_jobs(s)[0],'pair_02_3_11')

    def test_release_inheritance(self):
        with tempfile.TemporaryDirectory() as temp:
            b=Path(temp)/'new';old=Path(temp)/'old'
            write(b/'plan.json',dict(predecessor=str(old)))
            write(old/'control/gpu_0.json',dict(blocked=True,requested_at='2026-10-11T23:00:00+08:00'))
            self.assertTrue(blocked(b,0));self.assertFalse(blocked(b,1))
            with self.assertRaises(Released):poll(b,0)
            write(b/'control/gpu_0.json',dict(blocked=False,requested_at='2026-10-11T23:01:00+08:00'))
            self.assertFalse(blocked(b,0))
            write(old/'control/gpu_0.json',dict(blocked=True,requested_at='2026-10-11T23:02:00+08:00'))
            self.assertTrue(blocked(b,0))

    def test_gate_and_ci(self):
        self.assertEqual(classify(.31,[.2,.4],.16,[.1]*5),'STRUCTURED_SIGNAL')
        self.assertEqual(classify(.31,[-.1,.5],.16,[.1]*5),'INCONCLUSIVE_OR_MIXED')
        self.assertEqual(classify(.1,[.1,.1],.1,[.1]*5),'NO_SUPPORT_THIS_PROTOCOL')
        self.assertEqual(classify(None,[.1,.1],.1,[.1]*5),'INCONCLUSIVE')
        self.assertEqual(interval([.5]*20)['ci95'],[.5,.5])


if __name__=='__main__':unittest.main()
