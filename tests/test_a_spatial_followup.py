import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch, Mock

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/queue_post_m2_a_spatial_20261030.py'
spec = importlib.util.spec_from_file_location('spatial_successor', SCRIPT)
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)


class SuccessorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.full, self.base, self.code = root/'full', root/'new', root/'code'
        for p in (self.full,self.base,self.code):p.mkdir()
        for name, value in [('FULL',self.full),('BASE',self.base),('CODE',self.code)]:
            item = patch.object(q,name,value);item.start();self.addCleanup(item.stop)
        q.write(self.code/'SOURCE.json',dict(commit=q.PAYLOAD))

    def complete(self, status='COMPLETE'):
        q.write(self.full/'train_complete.json',dict(status=status,source=dict(commit=q.PAYLOAD),blocked=[]))

    def test_failure_overrides_complete_and_preserves_original(self):
        self.complete()
        q.write(self.full/'worker_first_failure_gpu1.json',dict(traceback='ORIGINAL THREAD FAILURE'))
        with self.assertRaisesRegex(RuntimeError,'Full engineering failure'):q.completion()
        self.assertIn('ORIGINAL THREAD FAILURE',(self.full/'worker_first_failure_gpu1.json').read_text())

    def test_invalid_full_route_is_not_a_dependency_for_spatial(self):
        self.complete('COMPLETE_WITH_INVALID_ROUTES')
        self.assertEqual(q.completion()['status'],'COMPLETE_WITH_INVALID_ROUTES')

    def test_unfinished_or_wrong_source_never_counts_as_completion(self):
        self.assertIsNone(q.completion())
        self.complete('FAILED')
        with self.assertRaisesRegex(RuntimeError,'completion status'):q.completion()
        self.complete()
        q.write(self.code/'SOURCE.json',dict(commit='b'*40))
        with self.assertRaisesRegex(RuntimeError,'source mismatch'):q.completion()

    def test_handoff_uses_completion_and_lock_without_waiting_for_upload(self):
        self.complete('COMPLETE_WITH_INVALID_ROUTES')
        q.write(self.base/'registered.json',dict(predecessor_identity=None))
        (self.full/'controller.lock').touch()
        controller=types.ModuleType('post_m2_v2.controller')
        controller.idle_gpus=Mock(return_value=dict(gpus={'0':'free','1':'free'}))
        fcntl=types.SimpleNamespace(LOCK_EX=1,LOCK_NB=2,flock=Mock())
        with patch.dict(sys.modules,{'fcntl':fcntl,'post_m2_v2':types.ModuleType('post_m2_v2'),
                                    'post_m2_v2.controller':controller}),patch.object(q,'load_payload',return_value=Mock()):
            with q.wait_for_full():pass
        controller.idle_gpus.assert_called_once()
        self.assertTrue(q.read(self.base/'handoff.json')['full_upload_not_a_dependency'])
        self.assertFalse((self.full/'github_upload_receipt.json').exists())

    def test_reused_predecessor_pid_without_completion_is_not_live_work(self):
        q.write(self.base/'registered.json',dict(predecessor_identity=dict(start_ticks='original')))
        fake=types.SimpleNamespace(LOCK_EX=1,LOCK_NB=2,flock=Mock())
        with patch.dict(sys.modules,{'fcntl':fake}),patch.object(q,'full_identity',return_value=dict(start_ticks='reused')):
            with self.assertRaisesRegex(RuntimeError,'exited/replaced'):q.wait_for_full()

    def test_busy_unrelated_gpu_at_handoff_is_not_killed_or_waited_for(self):
        self.complete();q.write(self.base/'registered.json',dict(predecessor_identity=None))
        (self.full/'controller.lock').touch()
        controller=types.ModuleType('post_m2_v2.controller')
        controller.idle_gpus=Mock(side_effect=RuntimeError('GPU0/1 unavailable or busy'))
        fcntl=types.SimpleNamespace(LOCK_EX=1,LOCK_NB=2,flock=Mock())
        with patch.dict(sys.modules,{'fcntl':fcntl,'post_m2_v2':types.ModuleType('post_m2_v2'),
                                    'post_m2_v2.controller':controller}),patch.object(q,'load_payload',return_value=Mock()),patch.object(q.time,'sleep') as sleep:
            with self.assertRaisesRegex(RuntimeError,'busy'):q.wait_for_full()
        sleep.assert_not_called()

    def test_old_standalone_work_is_never_replayed(self):
        q.write(self.full/'a_spatial_train_started.json',{})
        with self.assertRaisesRegex(RuntimeError,'do not duplicate'):q.reject_existing_spatial()

    def test_existing_registration_never_launches_again(self):
        q.write(self.base/'registered.json',dict(status='already submitted'))
        with patch.object(q,'status') as status,patch.object(q.subprocess,'Popen') as popen:
            q.start('a'*40)
        status.assert_called_once();popen.assert_not_called()

    def test_loader_timeout_keeps_sampling_configuration(self):
        one = types.SimpleNamespace(num_workers=4,timeout=0,batch_size=16,shuffle=False)
        original = Mock(return_value=one)
        self.assertIs(q.bounded_loader(original)('fit',[1],4,32000),one)
        self.assertEqual(one.timeout,30);self.assertEqual(one.batch_size,16)
        original.assert_called_once_with('fit',[1],4,32000)
        zero = types.SimpleNamespace(num_workers=0,timeout=0)
        q.bounded_loader(lambda:zero)();self.assertEqual(zero.timeout,0)

    def test_timeout_is_accepted_by_real_dataloader_before_iteration(self):
        import torch
        loader=q.bounded_loader(lambda:torch.utils.data.DataLoader(
            torch.utils.data.TensorDataset(torch.arange(2)),num_workers=1))()
        self.assertEqual(loader.timeout,30)
        self.assertEqual(loader.num_workers,1)

    def test_failed_first_phase_dispatches_no_later_phase(self):
        with patch.object(q,'stage',side_effect=RuntimeError('real loader error')) as stage:
            with self.assertRaisesRegex(RuntimeError,'real loader error'):q.execute_stages()
        stage.assert_called_once_with('profile',None)

    def test_unlearned_head_closes_only_spatial_after_exact_training(self):
        profiles = [dict(status='REAL_SPATIAL_PROFILE_PASSED',selected=dict(median_seconds=.1),evaluation=dict(seconds=1))]*2
        train = [dict(status='TRAINED_SPATIAL_HEAD'),dict(status='INVALID_PROBE')]
        with patch.object(q,'stage',side_effect=[profiles,train]) as stage:
            self.assertEqual(q.execute_stages(),'INVALID_PROBE_NO_AUTOMATIC_EXPANSION')
        self.assertEqual([x.args[0] for x in stage.call_args_list],['profile','train'])

    def test_all_phases_use_original_gate_without_requiring_dino3_win(self):
        screen = self.base/'a_spatial/screen.json'
        def gate(base,phase):
            self.assertEqual((base,phase),(self.base,'screen'))
            q.write(screen,dict(status='READY_SPATIAL_OUTER',dino3_minus_dino2_pp=-2))
        fake = types.ModuleType('post_m2_v2.spatial');fake.run=gate
        with patch.dict(sys.modules,{'post_m2_v2':types.ModuleType('post_m2_v2'),'post_m2_v2.spatial':fake}),patch.object(q,'stage',side_effect=[
                [dict(status='REAL_SPATIAL_PROFILE_PASSED',selected=dict(median_seconds=.1),evaluation=dict(seconds=1))]*2,
                [dict(status='TRAINED_SPATIAL_HEAD')]*2,[],[]]) as stage:
            self.assertEqual(q.execute_stages(),'SPATIAL_PAIR_ALL_PHASES_COMPLETE')
        self.assertEqual([x.args[0] for x in stage.call_args_list],list(q.STAGES))

    def test_pair_first_failure_stops_only_its_own_children(self):
        controller = types.ModuleType('post_m2_v2.controller')
        controller.idle_gpus=Mock();controller.stop_owned=Mock()
        child=Mock();child.poll.return_value=1;child.pid=123;child.returncode=1
        with patch.dict(sys.modules,{'post_m2_v2':types.ModuleType('post_m2_v2'),'post_m2_v2.controller':controller}),\
             patch.object(q.subprocess,'Popen',return_value=child),patch.object(q,'environment',return_value={}):
            with self.assertRaisesRegex(RuntimeError,'spatial worker failure'):
                with q.resident_pair() as pair:q.stage('profile',pair)
        controller.stop_owned.assert_called_once_with({0:child,1:child})
        self.assertFalse((self.base/'a_spatial_profile_complete.json').exists())

    def test_resident_reuses_model_and_fit_then_releases_fit_for_evaluation(self):
        import io
        legacy=dict(folds=dict(train=['fit']))
        array_calls=[]
        def arrays(contract,tiles,need_labels=True):
            array_calls.append(list(tiles))
            return {tiles[0]:dict(rgb=types.SimpleNamespace(nbytes=4))}
        model_loader=Mock(return_value=('frozen encoder',16))
        a0=types.ModuleType('post_m2_a0')
        a0.load_encoder=model_loader;a0.arrays=arrays;a0.loader=Mock()
        spatial=types.ModuleType('post_m2_v2.spatial')
        def execute(base,kind,phase):
            a0.load_encoder(legacy,kind)
            a0.arrays(legacy,['fit'] if phase in ('profile','train') else ['eval'])
        spatial.execute=execute
        common=types.SimpleNamespace(ipc_tmpdir=lambda _:str(self.base/'tmp'),CONFIG=dict(max_resident_tile_bytes=100))
        phases=io.StringIO(''.join(json.dumps(dict(phase=p))+'\n' for p in q.STAGES))
        with patch.object(q,'load_payload',return_value=common),patch.object(q.sys,'stdin',phases),\
             patch.dict(sys.modules,{'post_m2_a0':a0,'post_m2_v2':types.ModuleType('post_m2_v2'),'post_m2_v2.spatial':spatial,
                                    'torch':types.SimpleNamespace(__version__='2.7.1+cu126')}),\
             patch.dict(q.os.environ),patch.object(q.tempfile,'tempdir',q.tempfile.tempdir):
            q.worker('dino3')
        model_loader.assert_called_once_with(legacy,'dino3')
        self.assertEqual(array_calls,[['fit'],['eval'],['eval']])
        result=q.read(self.base/'resident_dino3.json')
        self.assertEqual(result['model_loads'],1);self.assertEqual(result['fit_loads'],1)
        self.assertFalse(result['fit_cache_retained'])

    def test_failure_export_keeps_partial_update_uncertainty_and_no_models(self):
        q.write(self.base/'registered.json',dict(followup_commit='a'*40))
        q.write(self.base/'a_spatial/dino2/train_started.json',{})
        q.write(self.base/'a_spatial/dino2/progress.json',dict(step=100))
        head=self.base/'a_spatial/dino2/head_2000.pt';head.write_bytes(b'endpoint')
        q.export()
        result=q.read(self.base/'publication/summary.json')
        self.assertFalse(result['exact_total_updates_known'])
        self.assertEqual(result['partial_jobs']['dino2']['last_logged_successful_step'],100)
        self.assertEqual(head.read_bytes(),b'endpoint')
        self.assertFalse(result['endpoints'][0]['uploaded'])
        import gzip
        with gzip.open(self.base/'publication/evidence.jsonl.gz','rt',encoding='utf-8') as f:
            names=[json.loads(line)['path'] for line in f]
        self.assertIn('a_spatial/dino2/progress.json',names)
        self.assertNotIn('a_spatial/dino2/head_2000.pt',names)

    def test_frozen_package_and_full_entry_are_not_written(self):
        import ast
        tree=ast.parse(SCRIPT.read_text(encoding='utf-8'))
        self.assertNotIn('prepare',[n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)])
        self.assertNotIn("'pipeline'",ast.get_source_segment(SCRIPT.read_text(encoding='utf-8'),next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='start')))


if __name__=='__main__':unittest.main()
