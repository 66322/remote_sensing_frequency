import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

source=Path(__file__).resolve().parents[1]/'scripts/recover_rebuild_v1_d23_gpu0.py'
spec=importlib.util.spec_from_file_location('recovery',source)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)


class RecoveryTests(unittest.TestCase):
    def simulate(self,tf_already_complete=False):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);base=root/'records/research_d23_b_formal_fixture';base.mkdir(parents=True)
            ts=base/'jobs/TS';ts.mkdir(parents=True)
            tf=base/'jobs/TF';tf.mkdir(parents=True)
            def completed(path):
                (path/'formal_complete.json').write_text('{"global_step":4000}')
                (path/'evaluation').mkdir(exist_ok=True)
                (path/'evaluation/summary.json').write_text('{}')
            if tf_already_complete:completed(tf)
            state=dict(status='FAILURE_DRAINING',jobs={
                'TS':dict(status='TECHNICAL_FAILURE',pid=9,job_directory=str(ts)),
                'TF':dict(status='COMPLETE' if tf_already_complete else 'PROCESS_STARTED',pid=11,job_directory=str(tf),log_path='tf-original.log')})
            (base/'queue_status.json').write_text(json.dumps(state))
            (base/'runtime_lock.json').write_text(json.dumps(dict(gpus=[dict(gpu=0,uuid='GPU-0')],job_wall_seconds=10800)))
            def write(path,value):path.write_text(json.dumps(value))
            q=types.SimpleNamespace(FILES=('scripts/run_rebuild_v1_d23.py',),validate_bindings=lambda *a:None,
                write=write,wait_for_gpu=lambda *a:None,stop=lambda *a:None,
                prepare_resume_job=lambda *a:(base/'jobs/TS-repaired',False))
            loader=types.SimpleNamespace(exec_module=lambda module:module.__dict__.update(q.__dict__))
            module=types.ModuleType('fixed_queue');finished=False;launched=[]
            def alive(pid,*args):return not tf_already_complete and not finished and pid in (11,88)
            class Worker:
                def __init__(self,cmd,**kwargs):
                    self.pid=77;self.returncode=0;launched.append(cmd[cmd.index('--arm')+1])
                    job=Path(cmd[cmd.index('--output')+1]);job.mkdir(parents=True)
                    completed(job)
                def poll(self):
                    nonlocal finished
                    finished=True;completed(tf);return 0
            def output(cmd,**kwargs):return 'f'*40+'\n' if 'rev-parse' in cmd else b'# fixture\n'
            mutex=types.SimpleNamespace(flock=lambda *a:None,LOCK_EX=1,LOCK_NB=2)
            with patch.object(sys,'argv',['recover','--root',str(root),'--directory',str(base),'--commit','fixed','--previous-controller','88']), \
                 patch.dict(sys.modules,fcntl=mutex),patch.object(Path,'relative_to',lambda *a:Path()), \
                 patch.object(r,'process_matches',side_effect=alive), \
                 patch.object(r.importlib.util,'spec_from_file_location',return_value=types.SimpleNamespace(loader=loader)), \
                 patch.object(r.importlib.util,'module_from_spec',return_value=module), \
                 patch.object(r.subprocess,'check_output',side_effect=output), \
                 patch.object(r.subprocess,'Popen',Worker), \
                 patch.object(r.subprocess,'run',return_value=types.SimpleNamespace(returncode=0)) as queue:
                r.main()
            return launched,json.loads((base/'queue_status.json').read_text()),queue.call_args[0][0]
    def test_existing_tf_is_retained_and_only_ts_is_started_before_merge(self):
        arms,state,cmd=self.simulate()
        self.assertEqual(arms,['TS'])
        self.assertEqual(state['jobs']['TS']['status'],'COMPLETE')
        self.assertEqual(state['jobs']['TF']['job_directory'].split('/')[-1].split('\\')[-1],'TF')
        self.assertEqual(state['jobs']['TF']['log_path'],'tf-original.log')
        self.assertIn('--resume-queue',cmd)
    def test_tf_already_complete_uses_normal_resume_without_extra_worker(self):
        arms,state,cmd=self.simulate(True)
        self.assertEqual(arms,[])
        self.assertIn('--resume-queue',cmd)
    def test_merge_refuses_changed_ts_state(self):
        with self.assertRaisesRegex(RuntimeError,'status changed'):
            r.merge_recovered(dict(jobs={'TS':dict(status='PROCESS_STARTED')}),Path('/job'),Path('/log'),77)
    def test_complete_requires_evaluation_summary(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'formal_complete.json').write_text('{"global_step":4000}')
            self.assertFalse(r.complete(p))
    def test_worker_identity_does_not_accept_another_command(self):
        with patch.object(Path,'exists',return_value=True),patch.object(Path,'read_bytes',return_value=b'python\0/base/log-reader.py\0'):
            self.assertFalse(r.process_matches(1,Path('/base'),True))


if __name__=='__main__':unittest.main()
