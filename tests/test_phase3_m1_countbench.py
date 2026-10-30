import sys
import unittest
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'scripts'))
sys.path.insert(0,str(root.parent/'phase3_m1_recovery/code/scripts'))
import benchmark_phase3_m1_counts as b
import phase3_m1_common as c
from phase3_m1_numeric import analyze

class Equality(unittest.TestCase):
    def tearDown(self): c.DATA.clear()
    def test_every_integer_and_rate_matches_across_rois_fallbacks_and_ties(self):
        rng=np.random.default_rng(42)
        for height,width in ((37,51),(261,49)):
            r=rng.integers(-3,4,size=(6,height,width)).astype(np.float32)
            d=rng.integers(-3,4,size=r.shape).astype(np.float32)
            gt=rng.integers(0,6,size=(height,width),dtype=np.uint8); gt[::3,::5]=255
            nb=gt.copy(); nb[::2,::7]=255
            c.DATA['t']=dict(full_gt=gt,noboundary_gt=nb)
            mask=rng.random(gt.shape)<.25
            for availability in ('both','rgb_missing','dsm_missing'):
                for border in (0,8):
                    for mode in ('none','ordinary','overlap'):
                        selected=None if mode=='none' else mask
                        healthy=(rng.random(gt.shape)<.5) if mode=='overlap' else None
                        with self.subTest(shape=gt.shape,availability=availability,border=border,mode=mode):
                            a=analyze(r,d,'t',selected,border,availability,healthy)
                            z=b.fast_analyze(c,r,d,'t',selected,border,availability,healthy)
                            self.assertEqual(a,z)
    def test_nonfinite_logits_are_rejected(self):
        r=np.zeros((6,10,10),np.float32); d=r.copy(); d[0,0,0]=np.nan
        c.DATA['t']=dict(full_gt=np.zeros((10,10),np.uint8),noboundary_gt=np.zeros((10,10),np.uint8))
        with self.assertRaises(RuntimeError): b.fast_analyze(c,r,d,'t')

    def test_process_worker_uses_only_inherited_arrays_and_returns_same_small_digest(self):
        import hashlib,json
        r=np.arange(6*13*17,dtype=np.float32).reshape(6,13,17); d=-r
        gt=(np.arange(13*17).reshape(13,17)%6).astype(np.uint8)
        c.DATA['t']=dict(full_gt=gt,noboundary_gt=gt)
        mask=gt%3==0; healthy=~mask
        import phase3_m1_numeric as original
        b._FORK_ENV=(c,original,[r],[d],'t',[mask],[healthy])
        expected=hashlib.sha256(json.dumps(analyze(r,d,'t',mask,healthy_override=healthy),sort_keys=True,separators=(',',':')).encode()).hexdigest()
        try:
            for fast in (False,True):
                b._FORK_FAST=fast; result=b.process_invoke((0,0))
                self.assertEqual(result,expected); self.assertEqual(len(result),64)
            if sys.platform=='linux':
                import multiprocessing as mp
                pool=mp.get_context('fork').Pool(2)
                try: self.assertEqual(pool.map(b.process_invoke,[(0,0),(0,0)]),[expected,expected])
                finally: pool.close(); pool.join()
        finally: b._FORK_ENV=None

if __name__=='__main__': unittest.main()
