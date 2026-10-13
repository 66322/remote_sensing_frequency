import sys
from pathlib import Path
import unittest
import tempfile
import json
from test_prediction_cleanup import npy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import delete_audited_old_predictions as m

class Scope(unittest.TestCase):
    def test_allowed(self):
        self.assertTrue(m.allowed('jobs/N2/evaluation/clean/rgb/3_11.npy'))
        self.assertTrue(m.allowed('jobs/replay/modes/expert2/evaluation/clean/rgb/5_10.npy'))
        self.assertTrue(m.allowed('jobs/N5/content_fixed8000/dsm_U/candidate/3_11.npy'))
    def test_preserve(self):
        for p in ('jobs/TCAP/normalized_fit_cache/4_12/dsm.npy','jobs/X/selected.pth','shared_reference/clean/3_11/rgb.npy','jobs/X/evaluation/clean/rgb/2_10.npy'):
            self.assertFalse(m.allowed(p))
        with self.assertRaises(ValueError): m.allowed('../jobs/X/evaluation/clean/rgb/3_11.npy')
    def test_counts(self):
        self.assertTrue(m.has_counts({'scopes':{'full':{'cm':[[1]*6 for _ in range(6)]}}}))
        self.assertFalse(m.has_counts({'mIoU':0.8}))
        self.assertFalse(m.has_counts({'cm':[[1.0]*6 for _ in range(6)]}))
    def test_inventory_requires_retained_counts_and_unchanged_file(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d).resolve();source=r/'audit';source.mkdir()
            for name in m.audit.NAMES:
                (source/(name+'.json')).write_text('{"errors":[]}')
                (source/(name+'.jsonl')).write_text('')
            name=m.audit.NAMES[0];rel='jobs/X/evaluation/clean/rgb/3_11.npy';p=r/name/rel;npy(p)
            st=p.stat();row=dict(path=rel,device=st.st_dev,inode=st.st_ino,size_bytes=st.st_size,mtime_ns=st.st_mtime_ns)
            (source/(name+'.jsonl')).write_text(json.dumps(row)+'\n')
            self.assertEqual(m.inventory(r,source)[1]['paths'],0)
            e=p.parent.parent/'3_11.json';e.write_text(json.dumps({'cm':[[1]*6 for _ in range(6)]}))
            rows,summary,_,_=m.inventory(r,source);self.assertEqual(summary['paths'],1)
            with p.open('ab') as f:f.write(b'x')
            with self.assertRaises(RuntimeError):m.inventory(r,source)

if __name__=='__main__':unittest.main()
