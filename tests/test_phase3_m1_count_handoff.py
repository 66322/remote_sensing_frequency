import json
import queue
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
sys.path.insert(0,str(root/'scripts'))
if not (root/'scripts/phase3_m1_common.py').exists():
    sys.path.insert(0,str(root.parent/'phase3_m1_recovery/code/scripts'))
import numpy as np
import phase3_m1_common as c
from phase3_m1_numeric import analyze
import handoff_phase3_m1_counts as h

class Handoff(unittest.TestCase):
    def tearDown(self): c.DATA.clear(); c.STATS.clear()
    def test_case_enumeration_and_paths_are_exactly_the_existing_320_cases(self):
        tasks=h.cases(c.VAL)
        self.assertEqual(len(tasks),320); self.assertEqual(len({h.case_id(t) for t in tasks}),320)
        self.assertEqual(h.case_id(tasks[0]),'RGB_FAULT_3_11_pixel_1_zero')
        self.assertEqual(h.case_id(tasks[-1]),'RGB_FAULT_5_10_matched_20_down4')

    def test_pid_reuse_and_wrong_task_never_receive_signals(self):
        base=Path('/known/run'); cmd=[b'python',str(base/'code/scripts/control_phase3_m1.py').encode(),b'--directory',str(base).encode(),b'']
        expected=dict(cmd=cmd,start=100,ppid=1); changed=dict(expected,start=101)
        with patch.object(h,'process_identity',return_value=changed),patch.object(h.os,'pidfd_open',create=True) as opened,patch.object(h.signal,'pidfd_send_signal',create=True) as sent:
            with self.assertRaisesRegex(RuntimeError,'identity changed'): h.signal_identified_controller(base,123,expected)
            opened.assert_not_called(); sent.assert_not_called()
        with patch.object(h,'process_identity',side_effect=[expected,changed]),patch.object(h.os,'pidfd_open',return_value=99,create=True),patch.object(h.os,'close'),patch.object(h.signal,'pidfd_send_signal',create=True) as sent:
            with self.assertRaisesRegex(RuntimeError,'PID changed'): h.signal_identified_controller(base,123,expected)
            sent.assert_not_called()
        unrelated=dict(expected,cmd=[b'python',b'other_experiment.py'])
        self.assertFalse(h.validate_old_identity(base,unrelated))

    def test_verified_pidfd_signal_targets_only_the_checked_handle(self):
        base=Path('/known/run'); cmd=[b'python',str(base/'code/scripts/control_phase3_m1.py').encode(),b'--directory',str(base).encode()]
        expected=dict(cmd=cmd,start=100,ppid=1)
        with patch.object(h,'process_identity',return_value=expected),patch.object(h.os,'pidfd_open',return_value=99,create=True) as opened,patch.object(h.os,'close') as closed,patch.object(h.signal,'pidfd_send_signal',create=True) as sent:
            h.signal_identified_controller(base,123,expected)
            opened.assert_called_once_with(123); sent.assert_called_once_with(99,h.signal.SIGTERM); closed.assert_called_once_with(99)

    def test_partial_case_scan_preserves_existing_files_and_rejects_wrong_binding(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); c.write(base/'plan.json',{}); c.write(base/'code_manifest.json',{})
            task=h.cases(['3_11'])[0]
            counts={scope:{roi:{s:{} for s in ('dsm','logit_mix','probability_mix')} for roi in ('all','healthy','damaged')} for scope in ('full','noboundary')}
            p=h.result_path(base,'M01_17',task); h.write(p,dict(job='M01_17',case=task,counts=counts,binding=c.binding(base)))
            inv=h.scan_cases(base,c,['M01_17','M20_17'],[task])
            self.assertEqual(inv['todo'][0]['models'],['M20_17']); self.assertEqual(sum(inv['complete'].values()),0)
            h.preserve_check(base,inv['retained_files'])
            z=h.read(p); z['binding']={'changed':True}; h.write(p,z)
            with self.assertRaises(RuntimeError): h.scan_cases(base,c,['M01_17','M20_17'],[task])
            with self.assertRaises(RuntimeError): h.preserve_check(base,inv['retained_files'])

    def test_two_gpu_three_cpu_queue_preserves_completed_counts_and_only_fills_missing(self):
        import phase24_ipc as ipc
        import phase3_m1_runtime as runtime
        class Q(queue.Queue):
            def cancel_join_thread(self): pass
            def close(self): pass
        class P:
            seq=100
            def __init__(self,target,args):
                type(self).seq+=1; self.pid=type(self).seq; self.args=args
                self.t=threading.Thread(target=target,args=args,daemon=True)
            def start(self): self.t.start()
            def is_alive(self): return self.t.is_alive()
            def join(self,timeout=None): self.t.join(timeout)
            def terminate(self): self.args[2].put(dict(kind='STOP'))
            def kill(self): self.terminate()
        class Context:
            def Queue(self): return Q()
            def Process(self,target,args): return P(target,args)
        class Packet:
            opened=0
            def __init__(self,arrays):
                self.arrays=dict(arrays); self.meta={'bytes':sum(a.nbytes for a in arrays.values())}; self.closed=False; type(self).opened+=1
            def close(self):
                if not self.closed: type(self).opened-=1; self.closed=True; self.arrays.clear()
            def descriptor(self): return {'payload':self}
            @classmethod
            def receive(cls,d): return cls(d['payload'].arrays)
        tile='3_11'; gt=(np.arange(19*23).reshape(19,23)%6).astype('uint8'); nb=gt.copy(); nb[0]=255
        c.DATA[tile]=dict(full_gt=gt,noboundary_gt=nb)
        rng=np.random.default_rng(42); models=['M01_17','M20_17']; tasks=h.cases([tile])[:4]
        ds={j:rng.normal(size=(6,*gt.shape)).astype('float32') for j in models}
        rs={h.case_id(t):rng.normal(size=(6,*gt.shape)).astype('float32') for t in tasks}
        mask=gt%3==0; healthy=~mask
        def worker(base,gpu,commands,events,acks):
            events.put(dict(kind='READY',gpu=gpu))
            while True:
                task=commands.get()
                if task['kind']=='STOP': return
                if task['kind']=='INFER_CLEAN': arrays={'score':ds[task['job']]}
                else: arrays=dict(score=rs[h.case_id(task)],mask=mask,healthy=healthy)
                packet=Packet(arrays); events.put(dict(kind='PACKET',gpu=gpu,task=task,packet=packet.descriptor()))
                acks.get(); packet.close(); events.put(dict(kind='DONE',gpu=gpu,task=task)); events.put(dict(kind='READY',gpu=gpu))
        with tempfile.TemporaryDirectory() as td:
            base=Path(td); c.write(base/'plan.json',{}); c.write(base/'code_manifest.json',{})
            expected={}
            for task in tasks:
                for job in models:
                    expected[h.case_id(task),job]=analyze(rs[h.case_id(task)],ds[job],tile,mask,healthy_override=healthy)
            # First case complete; second case has one model persisted.
            for task,job in [(tasks[0],models[0]),(tasks[0],models[1]),(tasks[1],models[0])]:
                h.write(h.result_path(base,job,task),dict(case=task,job=job,counts=expected[h.case_id(task),job],binding=c.binding(base)))
            inv=h.scan_cases(base,c,models,tasks)
            with patch.object(h.mp,'get_context',return_value=Context()),patch.object(h,'reset_child_signals'),patch.object(h.os,'setsid',create=True),patch.object(runtime,'worker',side_effect=worker),patch.object(ipc,'Packet',Packet):
                engine=h.Engine(base,c,models,inv,{},workers=3,capacity=2)
                try:
                    engine.start(); self.assertTrue(engine.run()); self.assertEqual(engine.done[tile],4)
                    self.assertEqual(engine.new_files,5); self.assertTrue(engine.calibrated)
                    self.assertFalse(engine.clean); self.assertFalse(engine.live)
                    h.preserve_check(base,inv['retained_files'])
                    for task in tasks:
                        for job in models: self.assertEqual(h.read(h.result_path(base,job,task))['counts'],expected[h.case_id(task),job])
                finally: engine.close()
            self.assertEqual(Packet.opened,0)
            self.assertTrue(h.read(base/'count_engine_ram_retirement.json')['all_owned_processes_exited'])

    @unittest.skipUnless(sys.platform=='linux','actual memfd/two-process smoke runs on target before handoff')
    def test_target_fd_smoke(self): h.transport_smoke()

if __name__=='__main__': unittest.main()
