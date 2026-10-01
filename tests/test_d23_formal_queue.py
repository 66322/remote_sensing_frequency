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
    def simulate(self,failure=False,completion_step=4000):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'records').mkdir();base=root/'records/research_d23_b_formal_fixture';launched=[]
            lock=dict(job_wall_seconds=10800)
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
            with patch.object(sys,'argv',['queue','--root',str(root),'--commit','fixed','--directory',str(base)]),                  patch.object(Path,'relative_to',lambda self,*args:Path()),                  patch.object(q,'validate_bindings'),                  patch.object(q.subprocess,'check_output',side_effect=output),                  patch.object(q.subprocess,'Popen',Process),                  patch.object(q.subprocess,'run',return_value=types.SimpleNamespace(returncode=0)),                  patch.object(q.time,'sleep'):
                if failure:
                    with self.assertRaises(RuntimeError):q.main()
                else:q.main()
            return launched,json.loads((base/'queue_status.json').read_text())
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
