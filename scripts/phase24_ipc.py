"""Anonymous RAM packets. Linux memfd lifetime follows the last registered consumer."""
import os, mmap
from multiprocessing.reduction import DupFd
import numpy as np

class Packet:
 def __init__(self,fd,meta,readonly=False):
  self.fd=fd;self.meta=meta;self.map=mmap.mmap(fd,meta['bytes'],access=mmap.ACCESS_READ if readonly else mmap.ACCESS_WRITE)
  self.arrays={n:np.ndarray(tuple(r['shape']),dtype=r['dtype'],buffer=self.map,offset=r['offset'])
    for n,r in meta['arrays'].items()}
 def close(self):
  self.arrays.clear()
  if self.map is not None:self.map.close();self.map=None
  if self.fd is not None:os.close(self.fd);self.fd=None
 def descriptor(self):return dict(fd=DupFd(self.fd),meta=self.meta)
 @classmethod
 def receive(cls,row):return cls(row['fd'].detach(),row['meta'],readonly=True)
 @classmethod
 def create(cls,arrays):
  if not hasattr(os,'memfd_create'):raise RuntimeError('Linux anonymous memfd required; no disk-array fallback')
  offset=0;rows={}
  for n,a in arrays.items():
   a=np.asarray(a);offset=(offset+63)//64*64
   rows[n]=dict(offset=offset,shape=list(a.shape),dtype=str(a.dtype));offset+=a.nbytes
  fd=os.memfd_create('phase24_anonymous_packet',flags=getattr(os,'MFD_CLOEXEC',0));os.ftruncate(fd,offset)
  packet=cls(fd,dict(bytes=offset,arrays=rows))
  for n,a in arrays.items():packet.arrays[n][...]=a
  return packet
