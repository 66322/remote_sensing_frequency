import importlib.util,json,tempfile,unittest
from pathlib import Path
B=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('upload',B/'scripts/upload_post_s1_transfer_completed_records.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def write(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(m.json_bytes(value))
class CompletedUploadTests(unittest.TestCase):
    def setup(self,base):
        jobs=[{'id':'T'+str(i)} for i in range(10)]
        write(base/'plan.json',dict(jobs=jobs,execution_commit='science'))
        s=dict(CPU='COMPLETE',status='RUNNING_T1',observed_at='2026-10-10T09:00:00+08:00',jobs={j['id']:dict(status='PENDING') for j in jobs})
        s['jobs']['T0']['status']='COMPLETE';s['jobs']['T1']['status']='RUNNING';write(base/'queue_status.json',s)
        for name in ('code_manifest.json','mask_manifest.json','reference_index.json','predecessor_acceptance.json'):write(base/name,{'files':{}} if name=='code_manifest.json' else {'tiles':{}} if name=='mask_manifest.json' else {})
        write(base/'preparation_complete.json',dict(reference_index_sha256=m.digest((base/'reference_index.json').read_bytes())))
        (base/'execution_commit.txt').write_text('science\n');(base/'cpu_checks.log').write_text('tests OK\n')
        write(base/'jobs/T0/complete.json',dict(artifacts={}))
        # A forbidden unfinished file must never be parsed.
        f=base/'jobs/T1/invalid.json';f.parent.mkdir(parents=True);f.write_text('not JSON')
        return s
    def test_only_completed_and_freeze_membership(self):
        with tempfile.TemporaryDirectory(dir=B) as tmp:
            b=Path(tmp);s=self.setup(b);calls=[]
            def accept(base,j,p):
                calls.append(j);s['jobs']['T1']['status']='COMPLETE';write(b/'queue_status.json',s)
                return {'artifacts':{}}
            data,state=m.collect(b,b,accept)
            self.assertEqual(calls,['T0']);self.assertEqual(state['included_jobs'],['T0']);self.assertEqual(state['excluded_jobs']['T1'],'RUNNING')
            self.assertFalse(any('jobs/T1/' in k for k in data));self.assertFalse(state['scientific_final_gate_available'])
    def test_no_complete_rejected(self):
        with tempfile.TemporaryDirectory(dir=B) as tmp:
            b=Path(tmp);s=self.setup(b);s['jobs']['T0']['status']='RUNNING';write(b/'queue_status.json',s)
            with self.assertRaisesRegex(RuntimeError,'no fully completed'):m.collect(b,b,lambda *a:None)
    def test_preparation_and_reference_tamper_rejected(self):
        with tempfile.TemporaryDirectory(dir=B) as tmp:
            b=Path(tmp);s=self.setup(b);(b/'reference_index.json').write_text('{"changed":1}')
            with self.assertRaisesRegex(RuntimeError,'reference index changed'):m.collect(b,b,lambda *a:{'artifacts':{}})
    def test_acceptance_error_propagates(self):
        with tempfile.TemporaryDirectory(dir=B) as tmp:
            b=Path(tmp);self.setup(b)
            def bad(*a):raise RuntimeError('bad checkpoint SHA')
            with self.assertRaisesRegex(RuntimeError,'checkpoint SHA'):m.collect(b,b,bad)
    def test_final_screen_included_only_when_fully_complete(self):
        with tempfile.TemporaryDirectory(dir=B) as tmp:
            b=Path(tmp);s=self.setup(b);(b/'jobs/T1/invalid.json').unlink()
            for j in s['jobs']:s['jobs'][j]['status']='COMPLETE';write(b/'jobs'/j/'complete.json',dict(artifacts={}))
            write(b/'transfer_screen.json',dict(T7_passed=False));s.update(status='TRANSFER_COMPLETE_AWAITING_REVIEW',screen_sha256=m.digest((b/'transfer_screen.json').read_bytes()));write(b/'queue_status.json',s)
            data,state=m.collect(b,b,lambda *a:{'artifacts':{}})
            self.assertEqual(len(state['included_jobs']),10);self.assertTrue(state['scientific_final_gate_available']);self.assertIn('transfer_screen.json',data)
if __name__=='__main__':unittest.main()
