"""Once-only source verification and read-only fork-shared inputs. No copied disk arrays."""
from pathlib import Path
import hashlib, io, os, shutil, subprocess, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import phase24_common as common
from phase24_common import *

def source_guard(old):
 old=Path(old)
 for n,h in OLD_BINDING.items():
  if sha(old/n)!=h:raise RuntimeError('original Phase2 binding differs: '+n)
 for n,h in read(old/'prepared.json')['receipts'].items():
  if sha(old/n)!=h:raise RuntimeError('original prepared receipt changed: '+n)
 state=read(old/'queue_status.json')
 if state['status']!='PHASE2_COMPLETE_AWAITING_REVIEW' or any(x['status']!='COMPLETE' for x in state['workers'].values()):
  raise RuntimeError('original Phase2 not completed; do not enqueue')
 p=read(old/'plan.json')
 if p['execution_commit']!='e5641e073bf4421e346f589199c291a6e94db8b2' or p['fit12']!=FIT or p['val2']!=VAL:raise RuntimeError('original source/split differs')
 return state

def prepare(base):
 base=Path(base);p=verify(base);old=Path(p['previous']);source_guard(old)
 root=Path(p['root']);root.relative_to(Path('/home/jovyan/zzx').resolve())
 profile1=profile()
 if shutil.disk_usage(base).free<4*1024**3:raise RuntimeError('4 GiB free disk reserve required; no full cache is allocated')
 original=read(old/'input_manifest.json')
 if set(original['arrays'])!=set(FIT+VAL):raise RuntimeError('forbidden/extra input tile')
 bytes_needed=int(original['total_array_bytes'])
 candidates=profile1['analysis_worker_candidates']
 envelope=bytes_needed+(12+10+1+1+8)*1024**3+max(candidates)*int(1.5*1024**3)
 if profile1['ram_cap_bytes']<envelope:raise RuntimeError('effective RAM cap below declared shared-input/stripe envelope')
 profile1.update(input_bytes=bytes_needed,estimated_ram_envelope_bytes=envelope,disk_free_bytes=shutil.disk_usage(base).free,
  required_disk_reserve_bytes=4*1024**3,shared_inputs='read-only fork COW',packet_transport='anonymous Linux memfd',
  clean_low_gpu_cache_cap_bytes=1024**3)
 arrays={t:{} for t in FIT+VAL};audit={};work=[]
 for tile,fields in original['arrays'].items():
  for name,row in fields.items():
   f=scoped(row['path'],old/'inputs');work.append((tile,name,row,f))
 def load(item):
  tile,name,row,f=item;before=identity(f);raw=f.read_bytes()
  if hashlib.sha256(raw).hexdigest()!=row['sha256'] or identity(f)!=before:raise RuntimeError('input changed: '+str(f))
  a=np.load(io.BytesIO(raw),allow_pickle=False)
  if list(a.shape)!=row['shape'] or str(a.dtype)!=row['dtype']:raise RuntimeError('input header changed')
  a.flags.writeable=False;return tile,name,a,dict(row,current_identity=before,current_sha256=row['sha256'])
 with ThreadPoolExecutor(max_workers=min(8,profile1['effective_cores'])) as pool:
  for i,(tile,name,a,receipt) in enumerate(pool.map(load,work),1):
   arrays[tile][name]=a;audit[tile+'/'+name]=receipt
   write(base/'preparation_progress.json',dict(verified_arrays=i,total_arrays=len(work),tile=tile,name=name,observed_at=now()))
 # Bound masks and only the required endpoints, never read retired array/cache manifests.
 mask=read(old/'mask_manifest.json');mask_checks={}
 for tile in VAL:
  for families in mask['tiles'][tile].values():
   for ratios in families.values():
    for row in ratios.values():
     f=scoped(row['path'],root)
     if sha(f)!=row['sha256']:raise RuntimeError('mask bytes changed')
     mask_checks[str(f)]=row['sha256']
 weights={}
 for job,name in [('A_RGB','step_16000'),('A_DSM','step_16000'),('B0','step_08000'),('B2','step_08000')]:
  f=old/'jobs'/job/(name+'.pth');receipt=read(f.with_suffix('.json'));done=read(f.parent/'complete.json')
  h=sha(f)
  if h!=receipt['sha256'] or done['files'].get(f.name)!=h or done['binding']!=OLD_BINDING:raise RuntimeError('expert/head endpoint changed')
  weights[job]=dict(path=str(f),sha256=h,bytes=f.stat().st_size)
 gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,name,memory.free','--format=csv,noheader,nounits'],text=True)
 info={}
 for line in gpu.splitlines():
  fields=[x.strip() for x in line.split(',')]
  if int(fields[0]) in (0,1):info[int(fields[0])]=fields
 if set(info)!={0,1} or any(float(row[-1])<24000 for row in info.values()):raise RuntimeError('GPU0/1 each needs at least 24 GiB currently free')
 apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader,nounits'],text=True)
 uuids={x[1] for x in info.values()}
 if any(any(u in line for u in uuids) for line in apps.splitlines()):raise RuntimeError('GPU0/1 already has an external compute process; preserve original queue')
 write(base/'gpu_inventory.json',dict(output=gpu,compute_apps=apps,observed_at=now()))
 write(base/'source_bindings.json',dict(old_directory=str(old),old_binding=OLD_BINDING,
  arrays=audit,masks=mask_checks,weights=weights,raw_source_images='not reread: normalized immutable input arrays are the actual execution inputs'))
 write(base/'resource_profile.json',profile1)
 write(base/'prepared.json',dict(binding=binding(base),source_bindings_sha256=sha(base/'source_bindings.json'),
  resources_sha256=sha(base/'resource_profile.json'),prepared_at=now()))
 common.DATA.clear();common.DATA.update(arrays)
 return profile1
