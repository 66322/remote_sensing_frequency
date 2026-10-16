import hashlib
from pathlib import Path
import tempfile
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from resident_array_cache import ResidentArrayCache,recommended_profile


class CacheChecks(unittest.TestCase):
    def scratch(self):
        p=Path(os.environ.get('PHASE15_TEST_DIRECTORY',str(Path(__file__).resolve().parents[1]/'test_scratch')))
        p.mkdir(parents=True,exist_ok=True)
        return tempfile.TemporaryDirectory(dir=p)
    def test_concurrent_single_load_readonly_and_exact(self):
        with self.scratch() as tmp:
            p=Path(tmp)/'value.npz';value=np.arange(1000,dtype=np.int64)
            np.savez_compressed(p,value=value);digest=hashlib.sha256(p.read_bytes()).hexdigest()
            cache=ResidentArrayCache(16000)
            with ThreadPoolExecutor(max_workers=8) as pool:
                rows=list(pool.map(lambda _:cache.load(p,digest,'value'),range(16)))
            self.assertEqual(cache.loads,1);self.assertEqual(cache.hits,15)
            self.assertTrue(all(r is rows[0] for r in rows));np.testing.assert_array_equal(rows[0],value)
            with self.assertRaises(ValueError):rows[0][0]=9
            with self.assertRaises(RuntimeError):cache.load(p,'0'*64,'value')
            p.write_bytes(b'changed')
            with self.assertRaises(RuntimeError):cache.load(p,digest,'value')
    def test_budget_evicts_and_profile_respects_limits(self):
        with self.scratch() as tmp:
            cache=ResidentArrayCache(8000)
            for i in range(2):
                p=Path(tmp)/f'{i}.npy';np.save(p,np.full(1000,i,dtype=np.int64))
                cache.load(p,hashlib.sha256(p.read_bytes()).hexdigest())
            self.assertEqual(len(cache.entries),1);self.assertEqual(cache.bytes,8000)
        gb=1024**3
        profile=recommended_profile(1800*gb,64,40*gb)
        self.assertEqual(profile['cpu_case_workers'],8);self.assertTrue(profile['preload_whole_working_set'])
        self.assertEqual(recommended_profile(1800*gb,2,40*gb)['cpu_case_workers'],2)
        self.assertFalse(recommended_profile(64*gb,8,40*gb)['preload_whole_working_set'])


if __name__=='__main__':unittest.main()
