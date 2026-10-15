import base64
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import upload_phase3_m1_api as u

class FakeApi:
    def __init__(self):
        self.current='a'*40; self.parents={self.current:{'tree':{'sha':'b'*40}}}
        self.blobs={}; self.trees={}; self.commit_trees={}; self.calls=[]; self.race=False
    def head(self): return self.current
    def manifest(self,commit,prefix):
        tree=self.commit_trees.get(commit,{})
        obj=tree.get(prefix+'/manifest.json')
        return None if obj is None else json.loads(self.blobs[obj])
    def get(self,commit,path): return self.blobs[self.commit_trees[commit][path]]
    def call(self,method,path,value=None):
        self.calls.append((method,path,value))
        if path.endswith('/git/blobs'):
            data=base64.b64decode(value['content']); h=u.gitsha(data); self.blobs[h]=data; return {'sha':h}
        if method=='GET' and '/git/commits/' in path: return self.parents[path.rsplit('/',1)[1]]
        if path.endswith('/git/trees'):
            assert value['base_tree']=='b'*40
            assert all(x['path'].startswith('records/'+u.RUN+'/compact_evidence/') for x in value['tree'])
            h=hashlib.sha1(json.dumps(value).encode()).hexdigest(); self.trees[h]={x['path']:x['sha'] for x in value['tree']}; return {'sha':h}
        if path.endswith('/git/commits'):
            h=hashlib.sha1(json.dumps(value).encode()).hexdigest(); self.commit_trees[h]=self.trees[value['tree']]
            self.parents[h]={'tree':{'sha':'b'*40}}; return {'sha':h}
        if method=='PATCH':
            assert value['force'] is False
            if self.race:
                self.race=False; self.current='c'*40; self.parents[self.current]={'tree':{'sha':'b'*40}}
                raise u.ApiError(422,'non-fast-forward race')
            self.current=value['sha']; return {'object':{'sha':self.current}}
        raise AssertionError((method,path))

class Upload(unittest.TestCase):
    def setup_run(self,td):
        base=Path(td)/u.RUN; (base/'upload_tmp').mkdir(parents=True)
        data=bytes(range(200)); archive=base/'upload_tmp/core.jsonl.gz'; archive.write_bytes(data)
        for name in ('plan.json','summary.json','result_verification.json','queue_status.json'):
            u.write(base/name,{'execution_commit':'d'*40,'value':name})
        prepared={'archive_sha256':u.sha(data),'files':[{'bytes':200}]}
        retired=[]
        def retire(b,p,reason):
            assert p==base/'upload_tmp'
            assert u.read(base/'github_upload_receipt.json')['all_parts_readback'] is True
            retired.append(p)
        common=SimpleNamespace(binding=lambda b:u.BINDING,read=u.read,now=lambda:'test-time',retire=retire)
        return base,archive,prepared,common,retired

    def test_upload_roundtrip_retains_payload_and_only_retires_after_readback(self):
        with tempfile.TemporaryDirectory() as td:
            base,archive,prep,c,retired=self.setup_run(td); api=FakeApi()
            with patch.object(u,'PART_BYTES',64),patch.object(u,'raw',side_effect=api.get),contextlib.redirect_stdout(io.StringIO()):
                u.upload(base,'e'*40,api,c,prep,archive)
            receipt=u.read(base/'github_upload_receipt.json')
            self.assertTrue(receipt['all_parts_readback']); self.assertEqual(receipt['parts'],4); self.assertEqual(len(retired),1)
            prefix='records/'+u.RUN+'/compact_evidence'; m=api.manifest(api.head(),prefix)
            self.assertEqual(m['part_encoding'],'binary'); self.assertEqual(m['archive_sha256'],prep['archive_sha256'])
            actual=b''.join(api.get(api.head(),prefix+'/'+r['file']) for r in m['parts'])
            self.assertEqual(actual,archive.read_bytes())
            self.assertFalse(any('fetch' in p or 'clone' in p for _,p,_ in api.calls))

    def test_corrupt_remote_part_never_writes_receipt_or_cleans_archive(self):
        with tempfile.TemporaryDirectory() as td:
            base,archive,prep,c,retired=self.setup_run(td); api=FakeApi()
            def bad(commit,path): return b'corrupt' if path.endswith('.part') else api.get(commit,path)
            with patch.object(u,'raw',side_effect=bad),contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError,'part SHA differs'): u.upload(base,'e'*40,api,c,prep,archive)
            self.assertFalse((base/'github_upload_receipt.json').exists()); self.assertEqual(retired,[]); self.assertTrue(archive.exists())

    def test_blob_checkpoint_reuses_exact_content_without_uploading_twice(self):
        with tempfile.TemporaryDirectory() as td:
            api=FakeApi(); checkpoint={'blobs':{}}; p=Path(td)/'checkpoint.json'
            first=u.put_blob(api,'records/x','part',b'evidence',checkpoint,p)
            self.assertEqual(first,u.put_blob(api,'records/x','part',b'evidence',checkpoint,p))
            self.assertEqual(len(api.calls),1)
            self.assertNotIn('token',p.read_text())

    def test_branch_race_rebuilds_metadata_on_latest_parent_without_force(self):
        api=FakeApi(); api.race=True; prefix='records/'+u.RUN+'/compact_evidence'
        with contextlib.redirect_stdout(io.StringIO()):
            commit,_=u.publish(api,[{'path':prefix+'/test','mode':'100644','type':'blob','sha':'f'*40}],prefix,'archive',u.BINDING)
        commits=[v for m,p,v in api.calls if m=='POST' and p.endswith('/git/commits')]
        self.assertEqual(commits[-1]['parents'],['c'*40]); self.assertEqual(commit,api.current)
        self.assertTrue(all(v['force'] is False for m,p,v in api.calls if m=='PATCH'))

    def test_readback_accepts_preexisting_original_base64_archive(self):
        prefix='records/x'; data=b'original prepared archive'; encoded=base64.b64encode(data)
        m={'parts':[{'file':'core_000.gz.b64','sha256':u.sha(encoded),'decoded_bytes':len(data)}]}
        rows={prefix+'/manifest.json':u.encode(m),prefix+'/core_000.gz.b64':encoded,prefix+'/summary.json':b'original summary'}
        with contextlib.redirect_stdout(io.StringIO()):
            u.readback('a'*40,prefix,m,u.sha(data),{'summary.json':b'original summary'},get=lambda c,p:rows[p])

    def test_different_existing_remote_archive_is_never_overwritten(self):
        api=FakeApi(); api.manifest=lambda *args:{'archive_sha256':'different','binding':u.BINDING}
        with self.assertRaisesRegex(RuntimeError,'refuse overwrite'):
            u.publish(api,[],'records/'+u.RUN+'/compact_evidence','expected',u.BINDING)
        self.assertEqual(api.calls,[])

if __name__=='__main__': unittest.main()
