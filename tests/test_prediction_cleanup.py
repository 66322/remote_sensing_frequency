import importlib.util
from pathlib import Path
import tempfile
import struct
import unittest
import os

path=Path(__file__).resolve().parents[1]/'scripts/delete_historical_val2_predictions.py'
spec=importlib.util.spec_from_file_location('cleanup',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def npy(path,dtype='|u1'):
    text=repr(dict(descr=dtype,fortran_order=False,shape=(6000,6000))).encode()+b'\n'
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('wb') as f:
        f.write(b'\x93NUMPY\x01\x00'+struct.pack('<H',len(text))+text);f.truncate(f.tell()+36000000)

class Checks(unittest.TestCase):
    def tree(self,root):
        for n in m.NAMES:(root/n/'jobs').mkdir(parents=True)
    def test_scope_and_hardlink_count(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();self.tree(root)
            a=root/m.NAMES[0]/'jobs/B0/evaluation/clean/fixed_rgb/3_11.npy';npy(a)
            b=a.parent.parent/'candidate/3_11.npy';b.parent.mkdir();os.link(a,b)
            (a.parent/'selected.pth').write_bytes(b'keep')
            npy(a.parent/'2_10.npy')
            npy(root/m.NAMES[0]/'jobs/B0/inputs/3_11.npy')
            rows,s=m.inventory(root)
            self.assertEqual(len(rows),2);self.assertEqual(s['unique_inodes'],1);self.assertEqual(len(s['skipped_paths']),1)
            self.assertEqual(s['external_link_inodes'],0)
            for row in rows:m.unlink_one(row,root)
            self.assertTrue((a.parent/'selected.pth').exists());self.assertTrue((a.parent/'2_10.npy').exists())
    def test_modified_file_blocks_delete(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();self.tree(root)
            a=root/m.NAMES[0]/'jobs/B0/evaluation/clean/fixed_rgb/3_11.npy';npy(a)
            rows,_=m.inventory(root)
            with a.open('ab') as f:f.write(b'x')
            with self.assertRaises(RuntimeError):m.unlink_one(rows[0],root)
            self.assertTrue(a.exists())
    def test_external_link_is_not_reclaimable(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();self.tree(root)
            a=root/m.NAMES[0]/'jobs/B0/evaluation/clean/fixed_rgb/3_11.npy';npy(a)
            outside=root/'shared.npy';os.link(a,outside)
            rows,s=m.inventory(root);self.assertEqual(s['external_link_inodes'],1)
            self.assertEqual(s['estimated_fully_unlinked_bytes'],0)
            m.unlink_one(rows[0],root);self.assertTrue(outside.exists())
    def test_wrong_header_blocks_inventory(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();self.tree(root)
            a=root/m.NAMES[0]/'jobs/B0/evaluation/clean/fixed_rgb/3_11.npy';npy(a,'<f4')
            with self.assertRaises(RuntimeError):m.inventory(root)
            self.assertTrue(a.exists())
    def test_outside_scope_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();a=root/'one.npy';a.write_bytes(b'keep')
            with self.assertRaises(ValueError):m.safe_file(a,root/'jobs')
            self.assertTrue(a.exists())

if __name__=='__main__':unittest.main()
