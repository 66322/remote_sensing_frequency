import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import types

path=Path(__file__).resolve().parents[1]/'scripts/launch_rebuild_v1_d23_formal.py'
spec=importlib.util.spec_from_file_location('queue',path)
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
class QueueTests(unittest.TestCase):
    def test_handover_waits_for_utilization_decay_and_process_exit(self):
        inventories=iter(['0, GPU-0, 0, 30\n1, GPU-1, 5000, 90\n',
                          '0, GPU-0, 0, 0\n', '0, GPU-0, 0, 0\n', '0, GPU-0, 0, 0\n'])
        apps=iter(['GPU-0, 123\n', 'GPU-0, 123\n', '', ''])
        def output(cmd,**kwargs):
            return next(apps) if '--query-compute-apps=gpu_uuid,pid' in cmd else next(inventories)
        with patch.object(q.subprocess,'check_output',side_effect=output), patch.object(q.time,'sleep') as sleep:
            q.wait_for_gpu(0,'GPU-0')
        self.assertEqual(sleep.call_count,3)
    def test_handover_does_not_kill_or_ignore_persistent_compute(self):
        def output(cmd,**kwargs):
            return 'GPU-0, 555\n' if '--query-compute-apps=gpu_uuid,pid' in cmd else '0, GPU-0, 5000, 80\n'
        with patch.object(q.subprocess,'check_output',side_effect=output), \
             patch.object(q.time,'monotonic',side_effect=[0,0,91]), \
             patch.object(q.time,'sleep'), patch.object(q.os,'killpg',create=True) as kill:
            with self.assertRaisesRegex(RuntimeError,'bounded handover wait'):
                q.wait_for_gpu(0,'GPU-0')
            kill.assert_not_called()
    def test_handover_rejects_changed_uuid(self):
        with patch.object(q.subprocess,'check_output',return_value='0, GPU-other, 0, 0\n'):
            with self.assertRaisesRegex(RuntimeError,'identity changed'):
                q.wait_for_gpu(0,'GPU-0')
    def test_resume_retains_old_outputs_and_copies_matching_checkpoint(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);old=base/'jobs/TS';(old/'training').mkdir(parents=True)
            (old/'training/last_train_state.pth').write_bytes(b'checkpoint')
            (old/'failure.json').write_text('failed preflight')
            target,resume=q.prepare_resume_job(base,'TS',old,'new')
            self.assertTrue(resume)
            self.assertEqual((target/'training/last_train_state.pth').read_bytes(),b'checkpoint')
            self.assertEqual((old/'failure.json').read_text(),'failed preflight')
            self.assertFalse((target/'evaluation').exists())
    def test_inputs_and_source_drift_stop_before_launch(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);code=root/'code';paths=['configs/rebuild_v1/r05_quality_plus_dropout_16k.json',
              'configs/rebuild_v1/potsdam_split_seed20260915.json','records/rebuild_v1_d21_queue_20260928/input_manifest.json']
            for p in paths+['code/scripts/run.py','code/model/rebuild_v1_d23_gate.py']:
                f=root/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b'bound')
            h=hashlib.sha256(b'bound').hexdigest()
            lock=dict(status='FULL_ENGINE_RUNTIME_ADMITTED',source_sha256={'run.py':h},
              gate_source_sha256=h,base_sha256=h,split_sha256=h,input_manifest_sha256=h)
            q.validate_bindings(root,code,lock)
            (root/paths[-1]).write_bytes(b'changed')
            with self.assertRaises(ValueError):q.validate_bindings(root,code,lock)
    def simulate(self,failure=False,completion_step=4000,resume=False):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'records').mkdir();base=root/'records/research_d23_b_formal_fixture';launched=[]
            lock=dict(job_wall_seconds=10800,gpus=[dict(gpu=0,uuid='GPU-0'),dict(gpu=1,uuid='GPU-1')])
            if resume:
                base.mkdir();(base/'plan.json').write_text('{}')
                (base/'runtime_lock.json').write_text(json.dumps(lock));jobs={}
                for gpu,arm in ((0,'TSF'),(1,'T0')):
                    out=base/'jobs'/arm;out.mkdir(parents=True)
                    (out/'formal_complete.json').write_text('{"global_step":4000}')
                    jobs[arm]=dict(gpu=gpu,status='COMPLETE',job_directory=str(out),log_path=str(base/(arm+'.log')))
                (base/'queue_status.json').write_text(json.dumps(dict(jobs=jobs)))
            def output(cmd,**kw):
                if 'rev-parse' in cmd:return 'f'*40+'\n'
                p=cmd[-1].split(':',1)[1]
                return json.dumps(lock).encode() if p.endswith('.json') else b'# mock source\n'
            class Process:
                def __init__(self,cmd,**kw):
                    arm=cmd[cmd.index('--arm')+1];launched.append(arm);self.pid=100+len(launched)
                    self.returncode=1 if failure and arm=='TSF' else 0
                    out=Path(cmd[cmd.index('--output')+1]);out.mkdir(parents=True)
                    if self.returncode==0:(out/'formal_complete.json').write_text(json.dumps({'global_step':completion_step}))
                def poll(self):return self.returncode
            with patch.object(sys,'argv',['queue','--root',str(root),'--commit','fixed','--directory',str(base)]+(['--resume-queue'] if resume else [])),                  patch.object(Path,'relative_to',lambda self,*args:Path()),                  patch.object(q,'validate_bindings'), patch.object(q,'wait_for_gpu'),                  patch.object(q.subprocess,'check_output',side_effect=output),                  patch.object(q.subprocess,'Popen',Process),                  patch.object(q.subprocess,'run',return_value=types.SimpleNamespace(returncode=0)),                  patch.object(q.time,'sleep'):
                if failure:
                    with self.assertRaises(RuntimeError):q.main()
                else:q.main()
            return launched,json.loads((base/'queue_status.json').read_text())
    def test_resume_runs_only_six_remaining_jobs_and_keeps_completed_metadata(self):
        jobs,state=self.simulate(resume=True)
        self.assertEqual(len(jobs),6)
        self.assertNotIn('TSF',jobs);self.assertNotIn('T0',jobs)
        self.assertEqual(state['status'],'COMPLETE')
        self.assertTrue(state['jobs']['T0']['log_path'].endswith('T0.log'))
    def test_all_eight_jobs_run_once_and_reach_screen(self):
        jobs,state=self.simulate()
        self.assertEqual(len(jobs),8)
        self.assertEqual(set(jobs),{a for arms in q.SCHEDULE.values() for a in arms})
        self.assertEqual(state['status'],'COMPLETE')
    def test_failure_stops_new_jobs_but_preserves_other_completed_job(self):
        jobs,state=self.simulate(True)
        self.assertEqual(jobs,['TSF','T0'])
        self.assertEqual(state['status'],'TECHNICAL_FAILURE')
        self.assertEqual(state['jobs']['T0']['status'],'COMPLETE')
    def test_checkpoint_completion_cannot_be_three_thousand_steps(self):
        jobs,state=self.simulate(True,completion_step=3000)
        self.assertEqual(state['jobs']['T0']['status'],'TECHNICAL_FAILURE')
    def test_atomic_status_keeps_latest_observation(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'queue_status.json';q.write(p,{'status':'READY'});q.write(p,{'status':'RUNNING'})
            self.assertEqual(json.loads(p.read_text())['status'],'RUNNING')
            self.assertFalse(p.with_suffix('.tmp').exists())
if __name__=='__main__':unittest.main()
