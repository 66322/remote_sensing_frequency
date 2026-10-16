"""Anonymous RAM packets. Linux memfd lifetime follows the last registered consumer."""
import os, mmap, sys, secrets, threading
import numpy as np

def ensure_abstract_resource_sharer(sharer=None,listener_factory=None,platform=None):
 """CPython 3.10/3.13 lifecycle, explicit authenticated Linux abstract socket.

 No global arbitrary_address monkeypatch and no filesystem/TMPDIR fallback.
 The standard resource sharer still owns descriptor claims and after-fork cleanup.
 """
 if (sys.platform if platform is None else platform)!='linux':raise RuntimeError('Linux abstract AF_UNIX transport required')
 from multiprocessing import resource_sharer, current_process
 from multiprocessing.connection import Listener
 sharer=resource_sharer._resource_sharer if sharer is None else sharer
 factory=Listener if listener_factory is None else listener_factory
 required=('_lock','_listener','_address','_thread','_serve')
 if any(not hasattr(sharer,n) for n in required) or not callable(sharer._serve):raise RuntimeError('unsupported CPython resource-sharer lifecycle')
 with sharer._lock:
  if sharer._address is not None:
   if not isinstance(sharer._address,bytes) or not sharer._address.startswith(b'\x00'):
    raise RuntimeError('resource sharer already uses a filesystem socket; refuse silent fallback')
   return sharer._address
  address=b'\x00phase24-fd-'+str(os.getpid()).encode()+b'-'+secrets.token_hex(12).encode()
  if len(address)>=108:raise RuntimeError('abstract socket address exceeds Linux limit')
  listener=factory(address=address,family='AF_UNIX',authkey=current_process().authkey)
  sharer._listener=listener;sharer._address=listener.address
  thread=threading.Thread(target=sharer._serve,name='phase24_fd_sharer',daemon=True)
  try:thread.start()
  except BaseException:
   listener.close();sharer._listener=None;sharer._address=None;raise
  sharer._thread=thread
  return sharer._address

class Packet:
 def __init__(self,fd,meta,readonly=False):
  self.fd=fd;self.meta=meta;self.map=mmap.mmap(fd,meta['bytes'],access=mmap.ACCESS_READ if readonly else mmap.ACCESS_WRITE)
  self.arrays={n:np.ndarray(tuple(r['shape']),dtype=r['dtype'],buffer=self.map,offset=r['offset'])
    for n,r in meta['arrays'].items()}
 def close(self):
  self.arrays.clear()
  if self.map is not None:self.map.close();self.map=None
  if self.fd is not None:os.close(self.fd);self.fd=None
 def descriptor(self):
  ensure_abstract_resource_sharer()
  from multiprocessing.reduction import DupFd
  return dict(fd=DupFd(self.fd),meta=self.meta)
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
