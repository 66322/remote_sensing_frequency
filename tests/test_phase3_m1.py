"""Adversarial lifecycle, information boundaries and true frozen-block gradients."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import phase3_m1_common as c
from phase3_m1_data import normalize,Crops
from phase3_m1_numeric import analyze

class Numeric(unittest.TestCase):
    def setUp(self): c.STATS.clear(); c.DATA.clear()
    def test_metric_keeps_true_class_denominators(self):
        a=np.eye(6,dtype=np.int64)*100; a[0,5]=100
        self.assertAlmostEqual(c.metric(a),90.)
        with self.assertRaises(ValueError): c.metric(np.eye(6,dtype=float))
    def test_joint_cannot_confuse_rescue_and_damage(self):
        gt=np.array([[0,0,1,1,255]],np.uint8); r=np.array([[1,0,1,2,0]],np.uint8); p=np.array([[0,2,1,2,0]],np.uint8)
        j=c.joint(gt,r,p,np.ones(gt.shape,bool)); f=c.flow(j)
        self.assertEqual((f['rescued'],f['harmed'],f['rgb_correct'],f['rgb_wrong']),(1,1,2,2))
        np.testing.assert_array_equal(j.sum(1),c.cm(gt,p,np.ones(gt.shape,bool)))
    def test_actual_fallback_and_fusion_counts(self):
        rng=np.random.default_rng(42); r=rng.normal(size=(6,19,23)).astype('float32'); d=-r
        gt=(np.arange(19*23).reshape(19,23)%6).astype('uint8'); c.DATA['t']={'full_gt':gt,'noboundary_gt':gt}
        out=analyze(r,d,'t',availability='dsm_missing')
        for name in ('logit_mix','probability_mix'):
            x=out['noboundary']['all'][name]; self.assertEqual(x['cm'],x['rgb_cm']); self.assertEqual(x['flow']['harmed'],0)
        out=analyze(r,d,'t',availability='rgb_missing')
        self.assertEqual(out['full']['all']['logit_mix']['cm'],out['full']['all']['dsm']['cm'])
    def test_R1_R2_isolate_denominator_without_clipping(self):
        c.STATS.update(t=dict(min=0.,max=100.,median=10.,span=20.),_S=40.)
        h=np.array([-100,10,30,200],np.float32)
        np.testing.assert_allclose(normalize(h,'t','R2')-.5,(normalize(h,'t','R1')-.5)/2)
        self.assertGreater(float(normalize(h,'t','R2')[-1]),1.)
        # Extra validation stats cannot change the training-only S.
        c.STATS['3_11']=dict(median=99999,span=1.)
        self.assertEqual(c.STATS['_S'],40.)
    def test_counter_preserves_span_set_but_not_correspondence(self):
        c.STATS['_S']=10.
        for i,t in enumerate(c.FIT): c.STATS[t]=dict(min=0.,max=100.,median=0.,span=float(i+1))
        spans=[]
        for t in c.FIT:
            z=normalize(np.array([0,c.STATS[t]['span']],np.float32),t,'R2',42,True)
            spans.append(float((z[1]-z[0])*10))
        np.testing.assert_allclose(sorted(spans),list(range(1,13)),rtol=1e-5,atol=1e-5)
    def test_seed42_crop_gt_and_token_equal_legacy(self):
        from phase2_data import sample
        from phase2_common import digest
        import hashlib
        a=np.arange(514*515,dtype=np.float32).reshape(514,515); ds=a/a.max(); gt=(a%6).astype('uint8')
        item=dict(dsm=ds,height=a,optical=np.repeat(ds[...,None],3,-1),full_gt=gt)
        for t in c.FIT: c.DATA[t]=item
        for i in (0,7,15,16,33):
            batch=Crops('M00',42)[i]; values,spec=sample(c.DATA,i//16+1,i%16,'phase21')
            np.testing.assert_array_equal(batch['dsm'].numpy(),values[1]); np.testing.assert_array_equal(batch['gt'].numpy(),values[2])
            token=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()+digest(values[2]).encode()).hexdigest()
            self.assertEqual(batch['token'],token)
    def test_gate_requires_every_seed_and_tile(self):
        rows={}
        for s in (42,17):
            for arm in ('M11','M21'):
                a=np.eye(6,dtype=np.int64)*100
                if arm=='M11': a[0,1]=10
                rows[f'{arm}_{s}']=dict(tiles={t:dict(noboundary=a.tolist()) for t in c.VAL})
        self.assertTrue(c.gate(rows)['accepted'])
        rows['M21_17']=dict(failed=True); self.assertFalse(c.gate(rows)['accepted'])
        del rows['M21_17']; self.assertIsNone(c.gate(rows))

class Lifecycle(unittest.TestCase):
    def test_retirement_cannot_delete_final_or_outside(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)/'run'; base.mkdir(); f=base/'jobs/M21_42/endpoint.pth'; f.parent.mkdir(parents=True); f.write_bytes(b'keep')
            with self.assertRaises(RuntimeError): c.retire(base,f,'invalid')
            outside=Path(td)/'outside'; outside.write_bytes(b'keep')
            with self.assertRaises(ValueError): c.retire(base,outside,'invalid')
            self.assertTrue(f.exists()); self.assertTrue(outside.exists())
    def test_last_resume_retired_with_receipt_only(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); p=base/'jobs/M21_42'; p.mkdir(parents=True)
            (p/'last_resume.pth').write_bytes(b'opt'); (p/'endpoint.pth').write_bytes(b'keep')
            rows=c.retire(base,p/'last_resume.pth','verified endpoint and counts')
            self.assertFalse((p/'last_resume.pth').exists()); self.assertTrue((p/'endpoint.pth').exists())
            self.assertEqual(sum(x['unique_bytes'] for x in rows),3)
            self.assertEqual(c.read(next((base/'retirement').glob('*.json')))['status'],'RETIRED')
    def test_changed_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); p=base/'temporary/x'; p.parent.mkdir(); p.write_bytes(b'a')
            real=c.identity; calls=[0]
            def changed(path):
                value=real(path); calls[0]+=1
                if calls[0]>1: value[-1]+=1
                return value
            with patch.object(c,'identity',side_effect=changed):
                with self.assertRaises(RuntimeError): c.retire(base,p,'raced')
            self.assertTrue(p.exists())
    def test_RAM_leases_delay_retirement(self):
        from control_phase3_m1 import Controller
        class Fake:
            meta={'bytes':42}
            def __init__(self): self.closed=False
            def close(self): self.closed=True
        with tempfile.TemporaryDirectory() as td:
            ctl=object.__new__(Controller); ctl.base=Path(td); packet=Fake()
            ctl.cache={'M21_42/3_11':dict(packet=packet,users=1)}; ctl.rgb_cpu_done={'3_11':160}
            ctl.retire_ram(); self.assertFalse(packet.closed)
            ctl.release(['M21_42/3_11']); self.assertTrue(packet.closed); self.assertFalse(ctl.cache)
    def test_new_job_queue_has_no_historical_duplicate(self):
        jobs=c.job_list(); self.assertEqual(len(jobs),11); self.assertEqual(len({x['job'] for x in jobs}),11)
        self.assertNotIn('M00_42',[x['job'] for x in jobs]); self.assertNotIn('C21_42',[x['job'] for x in jobs])
    def test_FIT_release_keeps_validation_and_source_files(self):
        with tempfile.TemporaryDirectory() as td:
            c.DATA[c.FIT[0]]={'height':np.zeros((3,3),np.float32)}
            c.DATA['3_11']={'height':np.ones((3,3),np.float32)}
            c.release_fit(td,'test')
            self.assertNotIn(c.FIT[0],c.DATA); self.assertIn('3_11',c.DATA)
            self.assertFalse(c.read(Path(td)/'retirement/fit_ram_test.json')['source_disk_files_deleted'])
    def test_conditional_counter_is_enqueued_once_without_waiting_for_seed_affinity(self):
        from control_phase3_m1 import Controller
        from collections import deque
        with tempfile.TemporaryDirectory() as td:
            ctl=object.__new__(Controller); ctl.base=Path(td); ctl.rows={}; ctl.counter_decided=False; ctl.train=deque()
            with patch.object(c,'gate',return_value={'accepted':True}),patch.object(c,'binding',return_value={'fixed':True}):
                ctl.maybe_counter(); ctl.maybe_counter()
            self.assertEqual({x['job'] for x in ctl.train},{'C21_42','C21_17'}); self.assertEqual(len(ctl.train),2)
    @unittest.skipUnless(sys.platform=='linux','Linux-only anonymous descriptor transport')
    def test_memfd_last_consumer_handoff(self):
        from phase24_ipc import Packet
        p=Packet.create({'score':np.arange(42,dtype=np.float32)})
        q=Packet.receive(p.descriptor()); p.close()
        np.testing.assert_array_equal(q.arrays['score'],np.arange(42,dtype=np.float32)); q.close()

class Gradient(unittest.TestCase):
    def test_stem_grad_crosses_eight_frozen_blocks(self):
        import torch
        from torch import nn
        from model.phase2_matched import MatchedExpert
        torch.set_num_threads(1)
        class Encoder(nn.Module):
            def __init__(self):
                super().__init__(); self.patch_embed=nn.Module(); self.patch_embed.proj=nn.Conv2d(3,384,14,14)
                self.blocks=nn.ModuleList(nn.Linear(384,384) for _ in range(12))
            def forward_features(self,x):
                z=self.patch_embed.proj(x).flatten(2).transpose(1,2)
                for block in self.blocks: z=z+torch.tanh(block(z))*.1
                return {'x_norm_patchtokens':z}
        model=MatchedExpert(Encoder()); model.encoder.patch_embed.proj.requires_grad_(True)
        frozen={n:p.clone() for n,p in model.named_parameters() if not p.requires_grad}
        before=model.encoder.patch_embed.proj.weight.clone(); opt=torch.optim.SGD([p for p in model.parameters() if p.requires_grad],lr=.01)
        loss=model(torch.rand(2,3,28,28)).square().mean(); loss.backward()
        self.assertGreater(float(model.encoder.patch_embed.proj.weight.grad.abs().sum()),0)
        self.assertTrue(all(p.grad is None for b in model.encoder.blocks[:8] for p in b.parameters()))
        opt.step(); self.assertFalse(torch.equal(before,model.encoder.patch_embed.proj.weight))
        self.assertTrue(all(torch.equal(p,frozen[n]) for n,p in model.named_parameters() if n in frozen))

class QueueIntegration(unittest.TestCase):
    def test_two_lanes_complete_shared_cases_and_release_every_lease(self):
        import queue
        import threading
        import phase3_m1_runtime as runtime
        import phase24_ipc as ipc
        import control_phase3_m1 as control
        class Queue(queue.Queue):
            def cancel_join_thread(self): pass
            def close(self): pass
        class Process:
            pid=12345
            def __init__(self,target,args): self.t=threading.Thread(target=target,args=args,daemon=True)
            def start(self): self.t.start()
            def join(self,timeout=None): self.t.join(timeout)
            def is_alive(self): return self.t.is_alive()
        class Context:
            def Queue(self): return Queue()
            def Process(self,target,args): return Process(target,args)
        class Packet:
            def __init__(self,arrays): self.arrays=dict(arrays); self.meta={'bytes':sum(v.nbytes for v in arrays.values())}
            def close(self): self.arrays.clear()
            @classmethod
            def receive(cls,p): return cls(p.arrays)
        gt=(np.arange(20*24).reshape(20,24)%6).astype('uint8')
        score=np.zeros((6,20,24),np.float32)
        for k in range(6): score[k][gt==k]=2
        for tile in c.VAL: c.DATA[tile]={'full_gt':gt,'noboundary_gt':gt}
        tasks=[dict(kind='TRAIN',job=f'{a}_{s}',arm=a,seed=s) for a in ('M11','M21') for s in (42,17)]
        used=set(); done_jobs=[]
        def fake_worker(base,gpu,commands,events,acks):
            events.put(dict(kind='READY',gpu=gpu))
            while True:
                task=commands.get()
                if task['kind']=='STOP': return
                used.add(gpu)
                if task['kind']=='TRAIN':
                    job=task['job']; done_jobs.append(job); folder=Path(base)/'jobs'/job; folder.mkdir(parents=True)
                    (folder/'endpoint.pth').write_bytes(b'endpoint')
                    c.write(folder/'complete.json',dict(checkpoint_sha256=c.sha(folder/'endpoint.pth')))
                    packets=[dict(kind='DSM_CLEAN',job=job,tile=t) for t in c.VAL]
                elif task['kind'] in ('SCALE','RELEASE_FIT'): packets=[]
                else: packets=[task]
                for payload in packets:
                    p=Packet({'score':score.copy()})
                    events.put(dict(kind='PACKET',gpu=gpu,task=payload,packet=p)); acks.get(); p.close()
                events.put(dict(kind='DONE',gpu=gpu,task=task)); events.put(dict(kind='READY',gpu=gpu))
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); c.write(base/'plan.json',{})
            with patch.object(control.mp,'get_context',return_value=Context()),patch.object(runtime,'worker',side_effect=fake_worker),\
                 patch.object(ipc,'Packet',Packet),patch.object(c,'binding',return_value={'test':'fixed'}),patch.object(c,'job_list',return_value=tasks):
                ctl=control.Controller(base,{'analysis_threads':4})
                try:
                    self.assertTrue(ctl.run()); self.assertEqual(used,{0,1}); self.assertEqual(sorted(done_jobs),sorted(x['job'] for x in tasks))
                    self.assertEqual(ctl.rgb_cpu_done,{'3_11':160,'5_10':160}); self.assertFalse(ctl.cache); self.assertFalse(ctl.ephemeral)
                    self.assertEqual(len(list((base/'skipped').glob('C21_*.json'))),2)
                finally: ctl.close(False)

class StartupImports(unittest.TestCase):
    def test_real_model_import_without_cwd_or_test_path(self):
        import subprocess
        scripts=Path(__file__).resolve().parents[1]/'scripts'
        with tempfile.TemporaryDirectory() as other:
            env=dict(os.environ); env.pop('PYTHONPATH',None)
            for entry in ('runtime','controller'):
                code='import sys, runpy; sys.path.insert(0, '+repr(str(scripts))+'); '
                if entry=='runtime': code+='import phase3_m1_runtime; '
                else: code+='runpy.run_path('+repr(str(scripts/'control_phase3_m1.py'))+', run_name="import_check"); '
                code+='from model.phase2_matched import MatchedExpert, optimizer; from d24_data import PrefetchedBatches; from phase2_infer import coords; print("IMPORT_OK")'
                result=subprocess.run([sys.executable,'-B','-c',code],cwd=other,env=env,capture_output=True,text=True,timeout=120)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIn('IMPORT_OK',result.stdout)

    def test_only_known_empty_failed_launch_can_be_superseded(self):
        from bootstrap_phase3_m1 import validate_superseded
        with tempfile.TemporaryDirectory() as td:
            records=Path(td); old=records/'research_phase3_m1_20261015T142532_2652995'
            (old/'jobs').mkdir(parents=True); (old/'failures').mkdir()
            c.write(old/'queue_status.json',dict(status='FAILED_OR_INTERRUPTED_NO_RETRY'))
            c.write(old/'plan.json',dict(execution_commit='c46a9d8a129198d73e744b02ade62784283a50e1'))
            c.write(old/'failures/one.json',dict(error="No module named 'model'",task=dict(kind='RGB_CLEAN')))
            c.write(old/'ram_retirement.json',dict(all_owned_gpu_workers_exited=True,all_cpu_consumers_exited=True))
            c.write(old/'launch.json',dict(controller_pid=2147483647))
            before={str(p):p.read_bytes() for p in old.rglob('*') if p.is_file()}
            self.assertEqual(validate_superseded(records,old),old.resolve())
            self.assertEqual(before,{str(p):p.read_bytes() for p in old.rglob('*') if p.is_file()})
            (old/'jobs/M21_42').mkdir()
            with self.assertRaisesRegex(RuntimeError,'training artifacts'): validate_superseded(records,old)
            with self.assertRaisesRegex(RuntimeError,'only the identified'): validate_superseded(records,records/'other')

if __name__=='__main__': unittest.main()

