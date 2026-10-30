"""Regression tests for the inherited condition interface and evaluation-only repair."""
import json,os,sys,tempfile,unittest
from pathlib import Path
import torch

HERE=Path(__file__).resolve().parent
if os.environ.get('POST_D30_BASE'):
    BASE=Path(os.environ['POST_D30_BASE']);sys.path[:0]=[str(HERE),str(BASE/'code/scripts'),str(BASE/'code')]
else:
    BASE=HERE.parent;sys.path[:0]=[str(BASE/'scripts'),str(BASE)]
from post_d30_eval_compat import compatible,check_conditions,repairable_row,transform_controller,reuse_equal_age,sha
from post_d30_data import treatment
from d27_data import treatment as previous_treatment
torch.set_num_threads(1)

def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v),encoding='utf-8')

class RepairTests(unittest.TestCase):
    def test_present_bad_dsm_matches_previous_protocol_without_missing_mask(self):
        op=torch.rand(1,3,33,35);ds=torch.rand(1,33,35)
        for kind in ('dsm_present_zero','dsm_present_shift_half'):
            expected=previous_treatment(op,ds,kind,42)
            for actual in (compatible(treatment)(op,ds,kind,42),):
                for a,b in zip(actual,expected):self.assertTrue(torch.equal(a,b))
                self.assertTrue(actual[2].all() and actual[3].all())
        self.assertTrue(torch.equal(op,expected[0]))

    def test_all_effective_runtime_conditions(self):
        if os.environ.get('POST_D30_BASE'):
            plan=json.loads((BASE/'plan.json').read_text(encoding='utf-8'))
        else:
            # Include inherited D27 diagnostics, not just the D26 source plan.
            from post_d30_common import runtime_plan
            parent=json.loads((BASE.parent/'d30-execution-20261003/records/research_d27_plan_20261002/plan.json').read_text(encoding='utf-8'))
            design=json.loads((BASE/'records/research_post_d30_design_20261003/plan.json').read_text(encoding='utf-8'))
            plan=runtime_plan(parent,design,'test',BASE)
        tested=check_conditions(plan,treatment)
        self.assertIn('dsm_present_zero',tested);self.assertIn('dsm_present_shift_half',tested)
        self.assertEqual(len(tested),32)

    def test_controller_repair_changes_only_diagnosed_retry_and_worker_dispatch(self):
        source=(BASE/('code/scripts' if os.environ.get('POST_D30_BASE') else 'scripts')/'launch_post_d30.py').read_text(encoding='utf-8')
        patched=transform_controller(source,HERE/'run_post_d30_repaired.py')
        compile(patched,'repair-controller','exec')
        self.assertIn('if repairable_row(j,row,base)',patched)
        self.assertIn("'--resume'",patched)
        self.assertIn('for phase,ids in PHASES.items()',patched)

    def test_known_error_only_and_checkpoint_required(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            base=Path(temp);log=base/'A0.log';log.write_text('ValueError: dsm_present_zero',encoding='utf-8')
            ck=base/'jobs/A0/last_train_state.pth';ck.parent.mkdir(parents=True);ck.write_bytes(b'fixture')
            row=dict(status='TECHNICAL_FAILURE',log_path=str(log),progress=dict(step=8000))
            self.assertTrue(repairable_row('A0',row,base))
            with self.assertRaises(RuntimeError):repairable_row('B1',row,base)
            row['progress']['step']=4000
            with self.assertRaises(RuntimeError):repairable_row('A0',row,base)
            row['progress']['step']=8000;log.write_text('different error',encoding='utf-8')
            with self.assertRaises(RuntimeError):repairable_row('A0',row,base)

    def test_reuse_requires_same_checkpoint_and_preserves_existing_rows(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            base=Path(temp);folder=base/'jobs/A0';(folder/'checkpoints').mkdir(parents=True)
            for name in ('checkpoints/step_8000.pth','selected.pth'):(folder/name).write_bytes(b'identical checkpoint')
            digest=sha(folder/'selected.pth');signature={'original':'unchanged'}
            state=dict(best=dict(step=8000,checkpoint_sha256=digest),signature=signature)
            write(base/'plan.json',dict(design=dict(geometry_conditions=['geom_dx8'],missing_conditions=[]),evaluation=dict(primary=[]),data=dict(validation=['3_11'])))
            source=folder/'fixed8000/geom_dx8/3_11.json';pred=source.parent/'candidate/3_11.npy';pred.parent.mkdir(parents=True);pred.write_bytes(b'prediction')
            write(source,dict(binding=dict(training=signature,checkpoint_sha256=digest),predictions=dict(candidate=sha(pred))))
            self.assertEqual(len(reuse_equal_age(base,folder,state,write)),1)
            target=folder/'evaluation/geom_dx8/3_11.json';before=target.read_bytes()
            self.assertEqual(reuse_equal_age(base,folder,state,write),[]);self.assertEqual(target.read_bytes(),before)
            state['best']['step']=4000;self.assertEqual(reuse_equal_age(base,folder,state,write),[])
            state['best']['step']=8000;(folder/'selected.pth').write_bytes(b'different')
            with self.assertRaises(RuntimeError):reuse_equal_age(base,folder,state,write)

if __name__=='__main__':unittest.main()
