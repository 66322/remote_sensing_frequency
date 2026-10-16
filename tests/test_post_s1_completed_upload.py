"""Live-queue snapshot regression tests. No Torch, GPU or real Git push."""
import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from upload_post_s1_completed_records import collect,json_bytes,digest
SCRATCH=ROOT/'test_scratch';SCRATCH.mkdir(exist_ok=True)
def put(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(json_bytes(obj))
def fixture(root):
    base=root/'records/research_post_s1_support_fixture';base.mkdir(parents=True)
    plan=dict(execution_commit='science',jobs=[dict(id='P6'),dict(id='P7'),dict(id='P3')])
    put(base/'plan.json',plan)
    queue=dict(CPU='COMPLETE',observed_at='2026-10-09T21:31:07+08:00',jobs={
        'D1':dict(status='COMPLETE'),'P6':dict(status='COMPLETE'),'P7':dict(status='COMPLETE'),
        'P3':dict(status='RUNNING'),'E':dict(status='PENDING')})
    put(base/'queue_status.json',queue)
    for n in ('preparation_complete.json','d0_index.json','source_acceptance.json'):put(base/n,{})
    (base/'execution_commit.txt').write_text('science\n');(base/'cpu_checks.log').write_text('OK\n')
    code=base/'code/tool.py';code.parent.mkdir();code.write_bytes(b'# immutable science\n')
    put(base/'code_manifest.json',dict(files={'tool.py':digest(code.read_bytes())}))
    put(base/'mask_manifest.json',dict(tiles={}))
    for stage in ('D0','R0_U','R0_ordinary'):put(base/stage/'summary.json',{})
    for j in ('D1','P6','P7'):
        put(base/'jobs'/j/'complete.json',dict(artifacts={'summary.json':'fixture'}))
        put(base/'jobs'/j/'summary.json',dict(value=j))
    # An intentionally incomplete/invalid active record must NEVER be read.
    f=base/'jobs/P3/evaluation/incomplete.json';f.parent.mkdir(parents=True);f.write_text('{unfinished')
    ref=root/'records/research_post_n3_s1_20261007T083203_694293/jobs/S1-0'
    put(ref/'complete.json',{})
    for tag in ('evaluation','fixed8000','support_evaluation','support_fixed8000'):put(ref/tag/'summary.json',{})
    return base,queue
def accept(base,j,plan):return json.loads((base/'jobs'/j/'complete.json').read_bytes())
def binding(*a,**k):return dict(model='S1-0'),{},{}
class SnapshotTests(unittest.TestCase):
    def test_running_incomplete_excluded_and_raw_sources_unchanged(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp);base,queue=fixture(root)
            before={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
            data,s=collect(root,base,accept,binding)
            self.assertEqual(s['included_jobs'],['D1','P6','P7']);self.assertEqual(s['core_training_complete'],2)
            self.assertFalse(s['scientific_final_gate_available']);self.assertFalse(s['unfinished_job_records_read'])
            self.assertFalse(any(k.startswith('jobs/P3/') for k in data))
            self.assertIn('references/S1-0/support_evaluation/summary.json',data)
            after={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(before,after)
    def test_queue_membership_stays_frozen_during_completion_race(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp);base,q=fixture(root)
            def racing_accept(base,j,p):
                q['jobs']['P3']['status']='COMPLETE';put(base/'queue_status.json',q)
                return accept(base,j,p)
            data,s=collect(root,base,racing_accept,binding)
            self.assertEqual(s['excluded_jobs']['P3'],'RUNNING')
            self.assertEqual(json.loads(data['queue_status.json'])['jobs']['P3']['status'],'RUNNING')
            self.assertFalse(any(k.startswith('jobs/P3/') for k in data))
    def test_bad_completed_binding_fails_snapshot(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp);base,q=fixture(root)
            def reject(*args):raise RuntimeError('completion checksum changed')
            with self.assertRaises(RuntimeError):collect(root,base,reject,binding)
    def test_D0_or_D1_incomplete_rejected(self):
        for stage in ('CPU','D1'):
            with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
                root=Path(tmp);base,q=fixture(root)
                if stage=='CPU':q['CPU']='RUNNING'
                else:q['jobs']['D1']['status']='RUNNING'
                put(base/'queue_status.json',q)
                with self.assertRaises(RuntimeError):collect(root,base,accept,binding)
    def test_prediction_index_complete_files_and_missing_rejected(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp);base,q=fixture(root);record=base/'jobs/P7/evaluation/rgb_U/3_11.json'
            put(record,dict(tile='3_11',predictions={'candidate':'bound_sha'}))
            with self.assertRaises(RuntimeError):collect(root,base,accept,binding)
            path=record.parent/'candidate/3_11.npy';path.parent.mkdir();path.write_bytes(b'server array fixture')
            data,s=collect(root,base,accept,binding);index=json.loads(data['server_artifact_index.json'])
            self.assertEqual(index['artifacts'][0]['sha256'],'bound_sha')
            self.assertFalse(index['prediction_bodies_rehashed_by_this_snapshot'])
    def test_changed_science_snapshot_rejected(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp);base,q=fixture(root);(base/'code/tool.py').write_bytes(b'changed')
            with self.assertRaises(RuntimeError):collect(root,base,accept,binding)
if __name__=='__main__':unittest.main()

