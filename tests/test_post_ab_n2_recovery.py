"""CPU regression checks for null timeout and nonduplicating controller recovery."""
import ast,json,sys,tempfile,unittest,types
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import post_ab_n2_recovery as m
class RecoveryTests(unittest.TestCase):
    def test_timeout_none_and_valid(self):
        self.assertEqual(m.timeout_hours(None),8);self.assertEqual(3600*m.timeout_hours(None),28800)
        self.assertEqual(m.timeout_hours(4),4)
    def test_timeout_invalid(self):
        for x in (False,True,0,-1,'8',float('nan'),float('inf')):
            with self.assertRaises(ValueError):m.timeout_hours(x)
    def test_adopt_without_requeue(self):
        with tempfile.TemporaryDirectory() as d:
            state={'jobs':{'N2-0':{'status':'RUNNING','gpu':0,'pid':3,'started_at':'time'},'N2-1':{'status':'PENDING','gpu':1}}}
            active,done=m.reconcile(Path(d),{},state,lambda *a:'123')
            self.assertEqual(active[0].pid,3);self.assertEqual(done,[]);self.assertEqual(state['jobs']['N2-0']['status'],'RUNNING')
    def test_dead_incomplete_holds(self):
        with tempfile.TemporaryDirectory() as d:
            state={'jobs':{'N2-0':{'status':'RUNNING','gpu':0,'pid':3}}}
            with self.assertRaisesRegex(RuntimeError,'no automatic retry'):m.reconcile(Path(d),{},state,lambda *a:None)
    def test_dead_completed_accepts(self):
        with tempfile.TemporaryDirectory() as d:
            b=Path(d);(b/'jobs/N2-0').mkdir(parents=True);(b/'jobs/N2-0/complete.json').write_text('{}')
            with patch.object(m,'verify_complete') as check:
                active,done=m.reconcile(b,{}, {'jobs':{'N2-0':{'status':'RUNNING','gpu':0,'pid':3}}},lambda *a:None)
                self.assertEqual(done,['N2-0']);self.assertFalse(active);check.assert_called_once()
    def test_adopted_poll_and_pid_reuse(self):
        w=m.AdoptedWorker(3,Path('x'),'N2-0',0,{},'123')
        with patch.object(m,'process_identity',return_value='123'):self.assertIsNone(w.poll())
        with patch.object(m,'process_identity',return_value='999'):
            with self.assertRaisesRegex(RuntimeError,'PID reused'):w.poll()
        with patch.object(m,'process_identity',return_value=None):self.assertEqual(w.poll(),2)
    def test_pending_artifacts_hold(self):
        with tempfile.TemporaryDirectory() as d:
            b=Path(d);(b/'jobs/N2-1').mkdir(parents=True);(b/'jobs/N2-1/progress.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError,'execution evidence'):m.reconcile(b,{}, {'jobs':{'N2-1':{'status':'PENDING','gpu':1}}})
    def test_failed_state_is_not_requeued(self):
        with self.assertRaisesRegex(RuntimeError,'diagnosis required'):m.reconcile(Path('x'),{}, {'jobs':{'N2-0':{'status':'TECHNICAL_FAILURE','gpu':0}}})
    def test_corrupt_completion_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            b=Path(d);(b/'jobs/N2-0').mkdir(parents=True);(b/'jobs/N2-0/complete.json').write_text(json.dumps({'global_step':4}))
            with self.assertRaisesRegex(RuntimeError,'binding differs'):m.verify_complete(b,'N2-0',{})
    def monitor_fixture(self,returncode,gpu):
        # Execute the actual controller monitor AST, including timeout and
        # active-first dispatch order, without GPU/model imports or training.
        source=ast.parse((Path(__file__).resolve().parents[1]/'scripts/control_post_ab_n2.py').read_text())
        main=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        timeout=next(n for n in ast.walk(main) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='timeout' for t in n.targets))
        loop=next(n for n in ast.walk(main) if isinstance(n,ast.While) and any(isinstance(x,ast.For) and isinstance(x.target,ast.Name) and x.target.id=='gpu' for x in n.body))
        unit=ast.fix_missing_locations(ast.Module(body=[timeout,loop],type_ignores=[]))
        # Controller loop contains return for HOLD; compile in a function scope.
        fn=ast.FunctionDef(name='monitor',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=unit.body,decorator_list=[])
        wrapper=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]))
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);job='N2-'+str(gpu);folder=base/'jobs'/job;folder.mkdir(parents=True)
            if returncode==0:(folder/'complete.json').write_text('{}')
            state={'jobs':{'N2-0':{'status':'COMPLETE' if gpu==1 and returncode==0 else 'PENDING','gpu':0},'N2-1':{'status':'COMPLETE','gpu':1}}}
            state['jobs'][job]={'status':'RUNNING','gpu':gpu,'started_at':datetime.now().astimezone().isoformat()}
            proc=types.SimpleNamespace(poll=unittest.mock.Mock(side_effect=[None,returncode]),terminate=unittest.mock.Mock())
            popen=unittest.mock.Mock(side_effect=AssertionError('duplicate or post-failure launch'))
            verified=unittest.mock.Mock()
            env={'base':base,'plan':{'runtime':{'per_job_timeout_hours':None}},'timeout_hours':m.timeout_hours,'state':state,'active':{gpu:(job,proc,None)},'N2':['N2-0','N2-1'],'datetime':datetime,'now':lambda:'now','write':lambda *a:None,'verify_complete':verified,'close_handle':lambda *a:None,'subprocess':types.SimpleNamespace(Popen=popen),'next_job':lambda s,g:next((j for j,r in s['jobs'].items() if r['gpu']==g and r['status']=='PENDING'),None)}
            exec(compile(wrapper,'controller_monitor','exec'),env);result=env['monitor']()
            popen.assert_not_called();proc.terminate.assert_not_called()
            return result,state,verified.call_count
    def test_actual_monitor_none_timeout_adopted_finishes(self):
        result,state,calls=self.monitor_fixture(0,0)
        self.assertEqual(state['jobs']['N2-0']['status'],'COMPLETE');self.assertEqual(calls,1)
    def test_actual_monitor_failure_stops_other_lane_dispatch(self):
        result,state,calls=self.monitor_fixture(2,1)
        self.assertEqual(result,2);self.assertEqual(state['status'],'HOLD_N2_TECHNICAL_FAILURE');self.assertEqual(calls,0)
if __name__=='__main__':unittest.main()
