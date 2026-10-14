import sys
from pathlib import Path
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'storage-cleanup-20261013/scripts'))
import cleanup_phase2_completed as m

class Checks(unittest.TestCase):
    def test_scope(self):
        for p in ('val_cache/3_11_16000_rgb_clean.npy','head_cache/00001.npz','evaluation/B0_16000/case/pred.npy'):
            self.assertTrue(m.safe_candidate(p))
        for p in ('../val_cache/a.npy','val_cache/a.json','head_cache/00001.json','inputs/3_11/rgb.npy',
                  'jobs/A_RGB/last_train_state.pth','evaluation/B0_16000/case/counts.json',
                  'evaluation/OTHER/case/pred.npy','evaluation/B0_16000/case/label.npy'):
            self.assertFalse(m.safe_candidate(p))
    def test_changed_file_blocks_delete(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d).resolve();p=base/'val_cache/a.npy';p.parent.mkdir();p.write_bytes(b'cache')
            row=m.row_for(p,base);p.write_bytes(b'changed')
            with self.assertRaises(RuntimeError):m.unlink(row,base)
            self.assertTrue(p.exists())
    def test_keeps_counts_weights_and_external_hardlink(self):
        import os
        with tempfile.TemporaryDirectory() as d:
            base=Path(d).resolve();p=base/'evaluation/B0_16000/case/pred.npy';p.parent.mkdir(parents=True);p.write_bytes(b'cache')
            keep=p.with_name('counts.json');keep.write_text('{}')
            weight=base/'model.pth';weight.write_bytes(b'weights')
            outside=base/'shared.npy';os.link(p,outside)
            row=m.row_for(p,base);self.assertEqual(row['links'],2);m.unlink(row,base)
            self.assertTrue(outside.exists());self.assertTrue(keep.exists());self.assertTrue(weight.exists())
    def test_outside_candidate_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d).resolve();p=base/'inputs/a.npy';p.parent.mkdir();p.write_bytes(b'data')
            with self.assertRaises(RuntimeError):m.row_for(p,base)
            with self.assertRaises(ValueError):m.row_for(base.parent/'outside.npy',base)

if __name__=='__main__':unittest.main()
