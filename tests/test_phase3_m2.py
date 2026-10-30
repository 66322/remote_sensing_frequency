"""Checks for the changed scientific and execution contracts; no training runs."""
import copy
import json
import multiprocessing as mp
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'scripts')]
import numpy as np
import torch
import phase3_m2_common as c
from phase3_m2_data import freeze_folds,Crops,boundary_bins
from phase3_m2_loss import objective,stratified,crop_mask,teacher_view
from phase3_m2_counts import analyze_arrays,validate_counts,count_task,lists,reconstruct_masks
from phase3_m2_analysis import gates,arrays,Sink,finalize

torch.set_num_threads(1)

def folds():
    order=sorted(c.FIT,key=lambda t:tuple(map(int,t.split('_'))))
    out={}
    for i in range(3):
        test=order[i*4:i*4+4];train=[t for t in order if t not in test]
        out['F'+str(i)]=dict(evaluation=test,train=train,inner_pairs=[train[j:j+2] for j in range(0,8,2)])
    return dict(folds=out)

def toy(size=1030):
    yy,xx=np.indices((size,size));gt=((yy+xx)%6).astype(np.uint8)
    r=np.stack([np.where(gt==k,2.,-1.) for k in range(6)]).astype(np.float32)
    d=np.roll(r,1,axis=0);mask=(xx%4==0)
    return r,d,dict(full=gt,nb=gt.copy(),bin=np.where(xx<10,0,2).astype(np.uint8)),mask,~mask

class ContractTests(unittest.TestCase):
    def test_model_import_path(self):
        from model.phase2_matched import MatchedExpert,optimizer
        from d24_data import PrefetchedBatches
        self.assertTrue(callable(MatchedExpert));self.assertTrue(callable(optimizer));self.assertTrue(callable(PrefetchedBatches))

    def test_dag_and_no_leakage(self):
        f=folds();jobs=c.jobs(f);ids={j['id']:j for j in jobs}
        self.assertEqual(len(ids),108)
        for j in jobs:
            outer=set(f['folds'][j['fold']]['evaluation'])
            self.assertFalse(outer&set(j['train']))
            for dep in j['depends_on']:
                teacher=ids[dep]
                self.assertFalse(set(teacher['excluded'])&set(teacher['train']))
                self.assertFalse(outer&set(teacher['train']))
                self.assertEqual(len(teacher['train']),6)

    def test_fold_geo_and_overlap(self):
        values={t:dict(shape=[6000,6000],bounds=[i*10,0,i*10+10,10],crs=[1,2,3]) for i,t in enumerate(c.FIT)}
        with patch('phase3_m2_data.paths',side_effect=lambda root,t:dict(rgb=t)),patch('phase3_m2_data.header',side_effect=lambda t:values[t]):
            out=freeze_folds('unused');self.assertIn('geospatial',out['method'])
            values[c.FIT[1]]['bounds']=[5,0,15,10]
            with self.assertRaisesRegex(RuntimeError,'overlapping'):freeze_folds('unused')

    def test_fold_fallback(self):
        with patch('phase3_m2_data.paths',side_effect=lambda root,t:dict(rgb=t)),patch('phase3_m2_data.header',return_value=dict(shape=[6000,6000],bounds=None,crs=None)):
            out=freeze_folds('unused');self.assertIn('not_geographic',out['method']);self.assertFalse(out['labels_used'])

    def test_paired_crop_and_teacher_exclusion(self):
        old=c.DATA.copy();f=folds();job=next(j for j in c.jobs(f) if j['arm']=='DF')
        try:
            for t in c.FIT:
                c.DATA[t]=dict(rgb=np.zeros((520,520,3),np.float32),dsm=np.zeros((520,520),np.float32),full=np.zeros((520,520),np.uint8),bin=np.zeros((520,520),np.uint8))
            a=Crops(job,f,1)[0];other=dict(job,arm='DShuffle');b=Crops(other,f,1)[0]
            self.assertEqual(a['token'],b['token']);self.assertTrue(torch.equal(a['teacher_rgb'],b['teacher_rgb']))
            self.assertIn(a['tile'],f['folds'][job['fold']]['inner_pairs'][a['inner']])
            clean=Crops(dict(job,arm='D0'),f,1)[0];self.assertEqual(a['token'],clean['token'])
        finally:c.DATA.clear();c.DATA.update(old)

    def test_ce_and_dmix_exact_gradient(self):
        torch.manual_seed(9);target=torch.randint(0,6,(2,5,7));target[:,0,0]=255
        x=torch.randn(2,6,5,7,requires_grad=True);teacher=torch.randn_like(x,requires_grad=True)
        ce,_=objective(x,target,'D0');ref=torch.nn.functional.cross_entropy(x,target,ignore_index=255)
        torch.testing.assert_close(ce,ref)
        ce.backward();g0=x.grad.clone();x.grad=None
        # Matching teacher and student probabilities gives a normalized CE
        # gradient exactly, instead of the unnormalized .55 scaling.
        loss,diag=objective(x,target,'DMix',x.detach().clone());loss.backward()
        torch.testing.assert_close(x.grad,g0,rtol=1e-5,atol=1e-7)
        self.assertAlmostEqual(diag['raw_gradient_coefficient_mean'],.55,places=6)
        x.grad=None;loss,_=objective(x,target,'DF',teacher);loss.backward();self.assertIsNone(teacher.grad)

    def test_shuffle_entropy_multisets(self):
        torch.manual_seed(5);q=torch.rand(2,20,22);entropy=torch.rand_like(q)
        target=torch.randint(0,6,(2,20,22));bins=torch.randint(0,3,target.shape)
        for mode in ['shuffle','entropy']:
            out,_=stratified(q,entropy,target,bins,['11','12'],mode)
            out2,_=stratified(q,entropy,target,bins,['11','12'],mode)
            self.assertTrue(torch.equal(out,out2))
            for i in range(2):
                for k in range(6):
                    for b in range(3):
                        use=(target[i]==k)&(bins[i]==b)
                        self.assertTrue(torch.equal(torch.sort(q[i][use]).values,torch.sort(out[i][use]).values))

    def test_crop_masks(self):
        rng=np.random.default_rng(2);dsm=rng.random((512,512)).astype(np.float32);gt=rng.integers(0,6,(512,512),dtype=np.uint8)
        for family in c.FAMILIES:
            mask=crop_mask(None,dsm,gt,family,19);self.assertEqual(int(mask.sum()),512*512//4)
            self.assertTrue(np.array_equal(mask,crop_mask(None,dsm,gt,family,19)))
        g=crop_mask(None,dsm,gt,'gradient',19);m=crop_mask(None,dsm,gt,'matched',19)
        self.assertTrue(np.array_equal(np.bincount(gt[g],minlength=6),np.bincount(gt[m],minlength=6)))

    def test_frozen_mask_design_reconstruction(self):
        from structured_v0_masks import rng_for,canonical,raster
        tile,realization='2_12',1;shape=(16,16);meta={}
        for family in c.FAMILIES:
            if family=='pixel':
                a=np.zeros(shape,bool);a.flat[rng_for(tile,realization,'pixel').choice(a.size,64,replace=False)]=True
                meta[family]=dict(canonical_sha256=canonical(a))
            else:
                a=raster(shape,[[0,0,8]]);meta[family]=dict(primitives=[[0,0,8]],canonical_sha256=canonical(a))
        out=reconstruct_masks(tile,realization,dict(full=np.zeros(shape,np.uint8)),meta)
        self.assertTrue(all(int(a.sum())==64 for a in out.values()))
        meta['random']['canonical_sha256']='changed'
        with self.assertRaisesRegex(RuntimeError,'reconstruction'):reconstruct_masks(tile,realization,dict(full=np.zeros(shape,np.uint8)),meta)

    def test_publication_cannot_replace_another_run_handoff(self):
        from upload_phase3_m2 import may_refresh_shared,READY_STATUS_BLOB
        run='research_phase3_m2_example'
        self.assertTrue(may_refresh_shared(READY_STATUS_BLOB,'ready',run))
        self.assertTrue(may_refresh_shared('other','# M2\n\n运行：`'+run+'`；状态：RUNNING',run))
        self.assertFalse(may_refresh_shared('other','# Next experiment\nPrevious run: '+run,run))
        self.assertFalse(may_refresh_shared('other','# M2\n运行：`research_phase3_m2_other`；状态：RUNNING\nPrevious '+run,run))

    def test_counter_marginals_and_fallbacks(self):
        r,d,item,mask,healthy=toy();z=analyze_arrays(r,d,item,mask,healthy);self.assertTrue(validate_counts(z))
        bad=copy.deepcopy(z);bad['nb']['all']['cms'][2,0,0]+=1
        with self.assertRaisesRegex(ValueError,'marginal'):validate_counts(bad)
        self.assertEqual(int(z['nb']['all']['joint'].sum()),6*6)

    def test_missing_data_cannot_pass_gates(self):
        z=gates({},False);self.assertFalse(z['advance_reverse']);self.assertFalse(z['status']['G0'])

    def test_gate_dc_clean_and_tile_protection(self):
        with patch('phase3_m2_analysis.gain',return_value=1.):self.assertTrue(gates({},True)['advance_reverse'])
        def values(groups,other,*args,**kw):
            return -.1 if other=='DClean' and kw.get('measure','miou')=='miou' else 1.
        with patch('phase3_m2_analysis.gain',side_effect=values):
            g=gates({},True);self.assertTrue(g['status']['G1']);self.assertFalse(g['status']['G2']);self.assertFalse(g['advance_reverse'])
        def damaged_tile(groups,other,*args,**kw):return -.51 if kw.get('tile')==c.FIT[0] else 1.
        with patch('phase3_m2_analysis.gain',side_effect=damaged_tile):self.assertFalse(gates({},True)['status']['G3'])

    def test_evaluation_state_machine_complete_coverage(self):
        from control_phase3_m2 import Evaluation
        class FakePacket:
            def __init__(self,arrays):self.arrays=arrays;self.fd=1
            @classmethod
            def create(cls,arrays):return cls(arrays)
            @classmethod
            def receive(cls,descriptor):return cls(descriptor['arrays'])
            def descriptor(self):return dict(arrays=self.arrays)
            def close(self):self.fd=None
        old=c.DATA.copy();f=folds();jobs=c.jobs(f);work=[];identities=set()
        try:
            for t in c.FIT:c.DATA[t]=dict(full=np.zeros((16,16),np.uint8))
            with tempfile.TemporaryDirectory() as tmp,patch('phase24_ipc.Packet',FakePacket):
                c.write(Path(tmp)/'folds.json',f)
                def submit(fn,task,context=None):work.append((fn,task,context))
                ev=Evaluation(tmp,'F0',jobs,submit);iterations=0
                while not ev.done:
                    iterations+=1;self.assertLess(iterations,40000)
                    if work:
                        fn,task,context=work.pop(0)
                        if fn.__name__=='mask_task':
                            ev.receive_masks(dict(tile=task['tile'],realization=task['realization'],metadata={},
                                packets={fam:dict(arrays=dict(mask=np.zeros((16,16),bool),healthy=np.ones((16,16),bool))) for fam in c.FAMILIES}))
                        else:
                            meta=task['metadata'];identity=tuple(meta[k] for k in ['tile','rseed','dseed','arm','condition','family','realization'])
                            self.assertNotIn(identity,identities);identities.add(identity);ev.count_finished(context['lease'])
                    task=ev.next_task(len(work))
                    if task:
                        meta={k:v for k,v in task.items() if k not in ['job','mask_packet']};meta['job']=task['job']['id']
                        ev.receive_prediction(meta,FakePacket(dict(score=np.zeros((6,16,16),np.float32))))
                    elif not work and not ev.done:self.fail('evaluation queue stalled')
                self.assertEqual(len(identities),4*3*3*7*103);ev.close()
        finally:c.DATA.clear();c.DATA.update(old)

    def test_server_publication_preserves_incomplete_state(self):
        r,d,item,mask,healthy=toy();counts=analyze_arrays(r,d,item,mask,healthy)
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            for name,value in [('plan.json',{}),('code_manifest.json',{}),('folds.json',folds()),('input_index.json',{})]:c.write(base/name,value)
            sink=Sink(base)
            try:sink.accept(dict(kind='count',metadata=dict(tile='2_12',fold='F0',rseed=42,dseed=42,arm='D0',condition='down4',family='pixel',realization=1),counts=lists(counts)))
            finally:sink.close()
            summary=finalize(base,sink,[])
            self.assertEqual(summary['status'],'INCOMPLETE_NO_RETRY');self.assertFalse(summary['advance_reverse'])
            for name in ['REPORT.md','metrics.csv','summary.json','gates.json','manifest.json','F0_counts.jsonl.gz','F1_counts.jsonl.gz','F2_counts.jsonl.gz']:
                self.assertTrue((base/'publication'/name).is_file())
            manifest=c.read(base/'publication/manifest.json')
            for row in manifest['files']:self.assertEqual(row['sha256'],c.sha(base/'publication'/row['file']))

    @unittest.skipUnless(sys.platform=='linux','actual Linux memfd/FD transport checked on server')
    def test_linux_process_memfd(self):
        from phase24_ipc import Packet
        r,d,item,mask,healthy=toy();old=c.DATA.copy();c.DATA['2_12']=item
        packets=[Packet.create(dict(score=r)),Packet.create(dict(score=d)),Packet.create(dict(mask=mask,healthy=healthy))]
        try:
            pool=mp.get_context('fork').Pool(2)
            try:
                task=dict(r=packets[0].descriptor(),d=packets[1].descriptor(),mask=packets[2].descriptor(),tile='2_12',metadata={})
                actual=pool.apply_async(count_task,(task,)).get(60)
                self.assertTrue(validate_counts(actual['counts']))
                self.assertEqual(actual['counts']['nb']['all']['joint'],analyze_arrays(r,d,item,mask,healthy)['nb']['all']['joint'].tolist())
            finally:pool.close();pool.join()
        finally:
            for p in packets:p.close()
            c.DATA.clear();c.DATA.update(old)

if __name__=='__main__':unittest.main()
