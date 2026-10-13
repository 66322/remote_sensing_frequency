import sys
from pathlib import Path
import tempfile
import unittest
import os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import delete_remaining_val2_predictions as m
from test_prediction_cleanup import npy

class RemainingChecks(unittest.TestCase):
    def test_scope_and_kept_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d).resolve()
            p=r/m.core.NAMES[0]/'jobs/B0/fixed8000/clean/rgb/3_11.npy'
            npy(p)
            keep=r/m.core.NAMES[0]/'jobs/B0/inputs/rgb/3_11.npy'
            npy(keep)
            rows,s,skipped,_=m.inventory(r,[str(p),str(keep)])
            self.assertEqual(s['paths'],1);self.assertEqual(skipped,[str(keep)])
            m.core.unlink_one(rows[0],r)
            self.assertTrue(keep.exists());self.assertFalse(p.exists())
    def test_hardlinks_and_external_reference(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d).resolve();p=r/m.core.NAMES[0]/'jobs/B0/fixed8000/clean/rgb/3_11.npy';npy(p)
            q=p.with_name('5_10.npy');os.link(p,q)
            outside=r/'keep.npy';os.link(p,outside)
            rows,s,_,_=m.inventory(r,[str(p),str(q)])
            self.assertEqual(s['unique_inodes'],1);self.assertEqual(s['estimated_fully_unlinked_bytes'],0)
            for row in rows:m.core.unlink_one(row,r)
            self.assertTrue(outside.exists())
    def test_wrong_file_or_experiment_rejected(self):
        r=Path.cwd()
        for text in ['current_phase2/jobs/B0/fixed8000/clean/rgb/3_11.npy',m.core.NAMES[0]+'/jobs/B0/fixed8000/clean/rgb/selected.pth']:
            with self.assertRaises(ValueError):m.select(r,str(r/text))
    def test_duplicate_manifest_rejected(self):
        with self.assertRaises(RuntimeError):m.inventory(Path.cwd(),['a','a'])
    def test_bad_array_and_changed_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d).resolve();p=r/m.core.NAMES[0]/'jobs/B0/fixed8000/clean/rgb/3_11.npy';npy(p,'<f4')
            with self.assertRaises(RuntimeError):m.inventory(r,[str(p)])
            npy(p);rows,_,_,_=m.inventory(r,[str(p)])
            with p.open('ab') as f:f.write(b'x')
            with self.assertRaises(RuntimeError):m.core.unlink_one(rows[0],r)
    def test_all_audited_phases_and_missing(self):
        r=Path.cwd()
        for phase in m.PHASES:
            p=r/m.core.NAMES[0]/('jobs/B0/'+phase+'/clean/rgb/3_11.npy')
            self.assertTrue(m.select(r,str(p))[1])
            rows,s,_,missing=m.inventory(r,[str(p)])
            self.assertEqual(rows,[]);self.assertEqual(s['missing_path_count'],1)

if __name__=='__main__':unittest.main()
