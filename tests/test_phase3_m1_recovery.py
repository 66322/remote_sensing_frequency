"""Reboot recovery must preserve optimizer, RNG, sample indices and immutable lineage."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import phase3_m1_common as c
from recover_phase3_m1 import save_stream_prefix,save_trajectory_prefix

class Recovery(unittest.TestCase):
    def test_registration_copies_completed_and_committed_prefix_without_mutating_source(self):
        import torch
        from recover_phase3_m1 import copy_jobs,SOURCE_BINDING
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); source=d/'source'; base=d/'new'; (source/'jobs').mkdir(parents=True); (base/'jobs').mkdir(parents=True)
            for name in SOURCE_BINDING: c.write(source/name,{'source':name})
            oldbinding={name:c.sha(source/name) for name in SOURCE_BINDING}
            complete=source/'jobs/M11_42'; complete.mkdir(); (complete/'endpoint.pth').write_bytes(b'finished')
            c.write(complete/'complete.json',dict(job='M11_42',binding=oldbinding,optimizer_updates=16000,checkpoint_sha256=c.sha(complete/'endpoint.pth')))
            partial=source/'jobs/M20_17'; partial.mkdir()
            torch.save(dict(job='M20_17',binding=oldbinding,step=1000,model={},optimizer={},rng=torch.get_rng_state(),cuda_rng=[torch.get_rng_state()]),partial/'last_resume.pth')
            c.write(partial/'parameters.json',dict(initial_state_sha256='initial'))
            c.write(partial/'progress.json',dict(step=1520))
            (partial/'batch_hashes.jsonl').write_text(''.join(json.dumps(dict(step=i,batch_hash='h'+str(i)))+'\n' for i in range(1,1521)))
            (partial/'trajectory.jsonl').write_text(''.join(json.dumps(dict(step=i,elapsed_seconds=i/10))+'\n' for i in (1,1000,1500)))
            before={p.relative_to(source).as_posix():c.sha(p) for p in source.rglob('*') if p.is_file()}
            done,resumed=copy_jobs(source,base)
            self.assertEqual(set(done),{'M11_42'}); self.assertEqual(set(resumed),{'M20_17'})
            self.assertEqual(resumed['M20_17']['step'],1000); self.assertEqual(resumed['M20_17']['replayed_since_checkpoint'],520)
            self.assertEqual(len((base/'jobs/M20_17/batch_hashes.jsonl').read_text().splitlines()),1000)
            self.assertEqual(before,{p.relative_to(source).as_posix():c.sha(p) for p in source.rglob('*') if p.is_file()})
            self.assertEqual((base/'jobs/M11_42/complete.json').read_bytes(),(complete/'complete.json').read_bytes())

    def test_recovery_queue_skips_all_seven_completed_trainings(self):
        import queue
        import control_phase3_m1 as control
        class Q(queue.Queue):
            def cancel_join_thread(self): pass
            def close(self): pass
        class P:
            pid=101
            def start(self): pass
            def is_alive(self): return False
            def join(self,timeout=None): pass
        class Context:
            def Queue(self): return Q()
            def Process(self,**kwargs): return P()
        completed={j:{} for j in ('M10_17','M10_42','M11_17','M11_42','M20_42','M21_17','M21_42')}
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); c.write(base/'plan.json',{})
            with patch.object(control.mp,'get_context',return_value=Context()),patch.object(c,'recovery',return_value=dict(completed=completed,resumed={})):
                ctl=control.Controller(base,dict(analysis_threads=2))
                try:
                    self.assertEqual({t['job'] for t in ctl.train},{'M20_17','M01_42','M01_17','M00_17'})
                    self.assertEqual(ctl.train_done,set(completed)); self.assertEqual(ctl.state['actual_new_updates'],112000)
                    self.assertEqual({t['job'] for t in ctl.other if t['kind']=='INFER_CLEAN'},set(completed)|{'M00_42'})
                finally: ctl.close()

    def test_stream_rolls_back_only_uncommitted_tail(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); rows=[dict(step=i,batch_hash='hash'+str(i)) for i in range(1,11)]
            (d/'old').write_text(''.join(json.dumps(x)+'\n' for x in rows)+'BROKEN REBOOT TAIL')
            h=save_stream_prefix(d/'old',d/'new',6)
            self.assertEqual([json.loads(x) for x in (d/'new').read_text().splitlines()],rows[:6])
            self.assertEqual(h,c.sha(d/'new')); self.assertIn('BROKEN',(d/'old').read_text())
            rows[3]['step']=99
            (d/'bad').write_text(''.join(json.dumps(x)+'\n' for x in rows))
            with self.assertRaises(RuntimeError): save_stream_prefix(d/'bad',d/'no',6)

    def test_trajectory_rolls_back_and_does_not_parse_crashed_tail(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); (d/'old').write_text(''.join(json.dumps(dict(step=i,elapsed_seconds=i/10))+'\n' for i in (1,20,40,60))+'BROKEN')
            self.assertEqual(save_trajectory_prefix(d/'old',d/'new',40),4.)
            self.assertEqual([json.loads(x)['step'] for x in (d/'new').read_text().splitlines()],[1,20,40])
            with self.assertRaises(RuntimeError): save_trajectory_prefix(d/'old',d/'bad',30)

    def test_crop_offset_reproduces_original_sample_stream(self):
        from phase3_m1_data import Crops
        c.DATA.clear(); c.STATS.clear()
        for tile in c.FIT:
            height=np.arange(514*515,dtype=np.float32).reshape(514,515)
            c.DATA[tile]=dict(height=height,dsm=height/height.max(),full_gt=(height.astype('int64')%6).astype('uint8'))
            c.STATS[tile]=dict(min=0.,max=float(height.max()),median=100.,span=120.)
        c.STATS['_S']=200.
        for arm,seed,start in (('M20',17,12000),('M01',42,2000)):
            full=Crops(arm,seed); resumed=Crops(arm,seed,start)
            self.assertEqual(len(resumed),(16000-start)*16)
            for i in (0,15,16,43):
                a,b=full[start*16+i],resumed[i]
                self.assertEqual(a['token'],b['token'])
                np.testing.assert_array_equal(a['dsm'],b['dsm']); np.testing.assert_array_equal(a['gt'],b['gt'])
        c.DATA.clear(); c.STATS.clear()

    def test_optimizer_rng_and_schedule_continue_identically(self):
        import torch
        from phase3_m1_runtime import restore_checkpoint
        from model.phase2_matched import factor
        torch.set_num_threads(1)
        def make():
            torch.manual_seed(17)
            m=torch.nn.Sequential(torch.nn.Linear(4,8),torch.nn.Dropout(.3),torch.nn.Linear(8,2))
            o=torch.optim.AdamW(m.parameters(),lr=.001)
            return m,o
        def update(m,o,step):
            for g in o.param_groups: g['lr']=.001*factor(step,16000)
            o.zero_grad(); loss=m(torch.randn(3,4)).square().mean(); loss.backward(); o.step()
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); job='M20_17'; folder=d/'jobs'/job; folder.mkdir(parents=True)
            c.write(folder/'parameters.json',dict(initial_state_sha256='init'))
            (folder/'batch_hashes.jsonl').write_text('prefix\n')
            m,o=make()
            for step in range(1,7): update(m,o,step)
            source=d/'source.pth'; oldbinding={'old':'fixed'}
            torch.save(dict(model=m.state_dict(),optimizer=o.state_dict(),step=6,job=job,binding=oldbinding,rng=torch.get_rng_state(),cuda_rng=[]),source)
            for step in range(7,15): update(m,o,step)
            expected_model=copy.deepcopy(m.state_dict()); expected_opt=copy.deepcopy(o.state_dict()); expected_rng=torch.get_rng_state().clone()
            r=dict(previous_binding=oldbinding,completed={},resumed={job:dict(path=str(source),sha256=c.sha(source),step=6,elapsed_seconds=1.,prefix_sha256=c.sha(folder/'batch_hashes.jsonl'))})
            c.write(d/'recovery_manifest.json',r); c.write(d/'plan.json',dict(recovery_manifest_sha256=c.sha(d/'recovery_manifest.json')))
            m2,o2=make()
            with patch.object(torch.cuda,'set_rng_state_all') as cuda:
                self.assertEqual(restore_checkpoint(d,job,m2,o2,'init'),(6,1.)); cuda.assert_called_once_with([])
            for step in range(7,15): update(m2,o2,step)
            for k,v in m2.state_dict().items(): self.assertTrue(torch.equal(v,expected_model[k]),k)
            for k,st in o2.state_dict()['state'].items():
                for name,v in st.items(): self.assertTrue(torch.equal(v,expected_opt['state'][k][name]))
            self.assertTrue(torch.equal(torch.get_rng_state(),expected_rng))
            self.assertEqual(o2.param_groups[0]['lr'],expected_opt['param_groups'][0]['lr'])
            (folder/'batch_hashes.jsonl').write_text('changed')
            with self.assertRaisesRegex(RuntimeError,'prefix changed'): restore_checkpoint(d,job,m2,o2,'init')

    def test_old_binding_is_accepted_only_for_hashed_inherited_endpoint(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td); folder=d/'jobs/M11_42'; folder.mkdir(parents=True)
            c.write(d/'code_manifest.json',dict(files={}))
            (folder/'endpoint.pth').write_bytes(b'weights')
            done=dict(binding={'old':'binding'},checkpoint_sha256=c.sha(folder/'endpoint.pth'))
            c.write(folder/'complete.json',done)
            r=dict(previous_binding=done['binding'],completed={'M11_42':dict(files={'complete.json':c.sha(folder/'complete.json'),'endpoint.pth':c.sha(folder/'endpoint.pth')})},resumed={})
            c.write(d/'recovery_manifest.json',r); c.write(d/'plan.json',dict(recovery_manifest_sha256=c.sha(d/'recovery_manifest.json')))
            self.assertTrue(c.job_binding_ok(d,'M11_42',done))
            self.assertFalse(c.job_binding_ok(d,'M11_17',done))
            c.write(folder/'complete.json',dict(done,changed=True))
            self.assertFalse(c.job_binding_ok(d,'M11_42',done))

if __name__=='__main__': unittest.main()
