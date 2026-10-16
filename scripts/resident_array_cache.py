"""Reusable SHA-verified, read-only host array cache; never reads unlisted files."""
from collections import OrderedDict
import hashlib
from pathlib import Path
from threading import RLock
import numpy as np


class ResidentArrayCache:
    def __init__(self,budget_bytes):
        if budget_bytes<=0:raise ValueError('positive measured memory budget required')
        self.budget=int(budget_bytes);self.bytes=0;self.entries=OrderedDict();self.lock=RLock()
        self.loads=0;self.hits=0

    def load(self,path,expected_sha256,key=None):
        path=Path(path).resolve();identity=(str(path),expected_sha256,key)
        with self.lock:
            stamp=path.stat();stamp=(stamp.st_size,stamp.st_mtime_ns)
            if identity in self.entries:
                array,original_stamp=self.entries.pop(identity)
                self.entries[identity]=(array,original_stamp)
                if stamp!=original_stamp:raise RuntimeError('immutable cached source metadata changed')
                self.hits+=1;return array
            digest=hashlib.sha256()
            with path.open('rb') as source:
                for chunk in iter(lambda:source.read(8*1024**2),b''):digest.update(chunk)
            if digest.hexdigest()!=expected_sha256:raise RuntimeError('array source SHA mismatch')
            if key is None:array=np.load(path,allow_pickle=False)
            else:
                with np.load(path,allow_pickle=False) as source:array=source[key]
            if not isinstance(array,np.ndarray):raise ValueError('explicit array key required for archive')
            after=path.stat()
            if stamp!=(after.st_size,after.st_mtime_ns):raise RuntimeError('source changed while loading')
            if array.nbytes>self.budget:raise MemoryError('single array exceeds cache budget')
            while self.bytes+array.nbytes>self.budget:
                _,(old,_)=self.entries.popitem(last=False);self.bytes-=old.nbytes
            array.setflags(write=False)
            self.entries[identity]=(array,stamp);self.bytes+=array.nbytes;self.loads+=1
            return array

    def preload(self,receipts):
        # Caller must supply only the frozen allowed working set, never discover Test6.
        identities=set()
        for r in receipts:
            self.load(r['path'],r['sha256'],r.get('key'))
            identities.add((str(Path(r['path']).resolve()),r['sha256'],r.get('key')))
        return dict(all_resident=identities.issubset(self.entries),resident_bytes=self.bytes,
            requested_arrays=len(identities),resident_arrays=len(self.entries))


def recommended_profile(available_memory_bytes,effective_cpus,working_set_bytes):
    if min(available_memory_bytes,effective_cpus)<=0:raise ValueError('actual resource limits required')
    cache_budget=int(available_memory_bytes*.50)
    reserve=max(8*1024**3,int(available_memory_bytes*.10))
    workers=min(8,int(effective_cpus),max(0,(available_memory_bytes-cache_budget-reserve)//(12*1024**3)))
    if workers<1:raise MemoryError('insufficient CPU/memory resources for resident parallel profile')
    return dict(cpu_case_workers=int(workers),resident_cache_budget_bytes=cache_budget,
        preload_whole_working_set=working_set_bytes<=cache_budget,
        library_threads_per_process=1,cache_immutable_arrays_only=True,
        training_sample_order_must_remain_fixed=True)
