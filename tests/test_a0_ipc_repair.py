import ast
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

BASE=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
a0=module('a0_fixed',BASE/'scripts/post_m2_a0_ipcfix_20261030.py')
repair=module('a0_repair',BASE/'scripts/repair_post_m2_a0_ipc_20261030.py')

class RepairTests(unittest.TestCase):
    def test_scientific_routines_unchanged(self):
        def functions(path):return {x.name:ast.dump(x,include_attributes=False) for x in ast.parse(path.read_text()).body if isinstance(x,ast.FunctionDef)}
        old=functions(BASE/'scripts/post_m2_a0.py');new=functions(BASE/'scripts/post_m2_a0_ipcfix_20261030.py')
        for name in ('resource_snapshot','contract','arrays','crop_key','extract','one_update','predict_tile','cm_tile','metrics','run_train','run_evaluate','screen'):
            self.assertEqual(old[name],new[name],name)

    def test_loader_timeout_only_for_workers(self):
        fake=types.SimpleNamespace(utils=types.SimpleNamespace(data=types.SimpleNamespace(DataLoader=lambda **kw:kw)))
        with patch.dict(sys.modules,torch=fake):
            kw=a0.loader({},[],4,32);self.assertEqual(kw['timeout'],30)
            self.assertEqual(kw['batch_size'],16);self.assertTrue(kw['persistent_workers'])
            self.assertNotIn('timeout',a0.loader({},[],0,32))

    def test_patch_metadata_without_changing_scientific_commit(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,POST_M2_EXECUTION_PATCH_COMMIT='a'*40):
            p=Path(d)/'receipt.json';a0.write_once(p,{'status':'TRAINED_HEAD_ONLY','code_commit':repair.SCIENCE})
            value=json.loads(p.read_text());self.assertEqual(value['code_commit'],repair.SCIENCE)
            self.assertEqual(value['execution_patch']['execution_patch_commit'],'a'*40)

    def test_ownership_requires_exact_script_kind_and_stdout(self):
        info=dict(argv=['python',str(repair.ORIGINAL),'train','--kind','dino2'],stdout=str(repair.OLD/'pair_train_dino2.log'))
        self.assertTrue(repair.child_matches(info,'dino2'))
        self.assertFalse(repair.child_matches(info,'dino3'))
        self.assertFalse(repair.child_matches(dict(info,stdout='/other/job.log'),'dino2'))

    def test_partial_progress_blocks_replay_even_without_endpoint(self):
        with tempfile.TemporaryDirectory() as d,patch.object(repair,'OLD',Path(d)):
            for kind in ('dino2','dino3'):(Path(d)/('pair_train_'+kind+'.log')).write_text('OSError: AF_UNIX path too long\n')
            evidence,partial=repair.observed_updates();self.assertFalse(partial)
            self.assertIsNone(evidence['dino2']['last_logged_step'])
            (Path(d)/'dino2').mkdir();(Path(d)/'dino2/progress.json').write_text('{"step":1,"loss":2.0}')
            evidence,partial=repair.observed_updates();self.assertTrue(partial)
            self.assertEqual(evidence['dino2']['last_logged_step'],1)

    def test_pid_reuse_and_zombie_are_not_signalled(self):
        old=dict(pid=123,start_ticks='first')
        with patch.object(repair,'process',return_value=dict(state='S',start_ticks='second')):
            self.assertFalse(repair.active_same(old))
        with patch.object(repair,'process',return_value=dict(state='Z',start_ticks='first')):
            self.assertFalse(repair.active_same(old))
        with patch.object(repair,'active_same',return_value=False),patch.object(repair.os,'kill') as kill:
            result=repair.stop_owned({123:old},{123});kill.assert_not_called()
            self.assertEqual(result['remaining_owned_pids'],[])

    def test_short_temp_environment_is_independent_of_long_run_name(self):
        env=repair.environment('b'*40)
        self.assertLess(len((env['TMPDIR']+'/pymp-abcdefgh/listener-abcdefgh').encode()),108)
        self.assertEqual(env['TMPDIR'],env['TEMP']);self.assertEqual(env['TMPDIR'],env['TMP'])
        self.assertEqual(env['POST_M2_CODE_COMMIT'],repair.SCIENCE)

    def test_full_worker_env_uses_short_temp_path(self):
        sys.path.insert(0,str(BASE/'scripts'))
        from post_m2_v2 import common as c
        env=c.env(1,BASE/('very_long_run_name_'*10))
        self.assertLess(len((env['TMPDIR']+'/pymp-abcdefgh/listener-abcdefgh').encode()),108)
        self.assertEqual(env['TMPDIR'],env['TEMP']);self.assertEqual(env['TMPDIR'],env['TMP'])
        self.assertEqual(env['CUDA_VISIBLE_DEVICES'],'1')

    def test_spatial_branch_binds_separate_repaired_a0_records(self):
        sys.path.insert(0,str(BASE/'scripts'))
        from post_m2_v2 import common as c,spatial
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);old=root/'records/old';new=root/'records/repaired';new.mkdir(parents=True)
            (new/'repair_ready.json').write_text(json.dumps({'scientific_source_commit':repair.SCIENCE}))
            fake=types.SimpleNamespace(contract=lambda *args,**kw:{'out':old})
            with patch.object(c,'ROOT',root),patch.dict(os.environ,POST_M2_A0_RECORDS=str(new)):
                self.assertEqual(spatial.a0_contract(fake,c)['out'],new.resolve())
            (new/'repair_ready.json').write_text('{"scientific_source_commit":"wrong"}')
            with patch.object(c,'ROOT',root),patch.dict(os.environ,POST_M2_A0_RECORDS=str(new)):
                with self.assertRaises(RuntimeError):spatial.a0_contract(fake,c)

if __name__=='__main__':unittest.main(verbosity=2)
