"""Persistent GPU lane: one expert forward for all heads, no disk logit cache."""
import os, sys, time, traceback
from pathlib import Path
import numpy as np
from phase24_common import *

def setup_cuda(base,gpu):
 os.environ.update(env(base,gpu))
 import torch
 if torch.__version__!='2.2.2+cu121' or not torch.cuda.is_available():raise RuntimeError('frozen Torch 2.2.2+cu121 CUDA runtime required')
 if os.environ['CUDA_VISIBLE_DEVICES']!=str(gpu):raise RuntimeError('physical GPU mapping differs')
 torch.manual_seed(42);torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
 torch.backends.cudnn.benchmark=False;torch.backends.cuda.matmul.allow_tf32=True;torch.backends.cudnn.allow_tf32=True
 return torch

class Frozen:
 def __init__(self,base,gpu):
  self.base=Path(base);self.gpu=gpu;self.plan=verify(base);self.old=Path(self.plan['previous'])
  self.torch=setup_cuda(base,gpu)
  from phase2_train import trained,load_head
  self.r=trained(self.old,'A_RGB',16000);self.d=trained(self.old,'A_DSM',16000)
  self.heads={'B0':load_head(self.old,'B0'),'B2':load_head(self.old,'B2')}
  self.clean_low={}  # At most 4 fixed tile/modality tensors, < 1 GiB per GPU.
  from collections import OrderedDict
  self.mask_cache=OrderedDict();self.mask_manifest=read(self.old/'mask_manifest.json')
  self.code_smoke()
 def code_smoke(self):
  import torch
  from phase24_model import ProtectedHead,features_torch
  from phase24_numeric import native_features,feature_core
  from phase2_train import smoke_ce,segmentation_ce,model_digest
  torch.manual_seed(42)
  r=torch.randn(1,6,32,32,device='cuda');d=torch.randn_like(r)
  rgb=torch.randn(1,3,32,32,device='cuda');ds=torch.rand(1,32,32,device='cuda')
  rm=torch.ones_like(ds,dtype=torch.bool);dm=rm.clone()
  rm[:,:4,:4]=False;dm[:,8:12,8:12]=False
  f=features_torch(r,d,rgb,ds,rm,dm)
  packet={'ds':ds[0].cpu().numpy(),'dm':dm[0].cpu().numpy(),'zero':(rgb[0]==0).all(0).cpu().numpy()}
  mean,std,grad,zero=native_features(packet,0,32)
  expected=feature_core(r[0].cpu().numpy(),d[0].cpu().numpy(),mean,std,grad,zero,rm[0].cpu().numpy(),dm[0].cpu().numpy())
  np.testing.assert_allclose(f[0].cpu().numpy(),expected,atol=1e-5,rtol=1e-5)
  proofs={}
  target=(torch.arange(32*32,device='cuda').reshape(1,32,32)%6).long()
  from model.phase2_matched import FusionHead,observables
  static=FusionHead('B0').cuda();initial=model_digest(static)
  if initial!='4a3c4bafb567b46b71c30c4577b4b6b96906250d74ea14d2cf477048456d0a69':raise RuntimeError('static initial state differs')
  obs=observables(r,d,rgb,ds,rm,dm);segmentation_ce(static(r,d,obs,rm,dm),target).backward()
  if not any(p.grad is not None and torch.isfinite(p.grad).all() and bool(p.grad.abs().sum()>0) for p in static.parameters()):raise RuntimeError('static head gradient is disconnected')
  if model_digest(static)!=initial:raise RuntimeError('static smoke updated parameters')
  proofs['T0']=dict(gradient_nonzero=True,optimizer_updates=0,initial_state_sha256=initial)
  for arm in ('T1','T2','T3'):
   torch.manual_seed(42);model=ProtectedHead(arm).cuda();before=model_digest(model)
   z,g=model(r,d,f,rm,dm);reference=torch.where((rm&dm)[:,None],r,torch.where(rm[:,None],r,d))
   if not torch.equal(z,reference):raise RuntimeError('new residual zero initialization not exact RGB/fallback')
   loss=segmentation_ce(z,target);loss.backward()
   if not any(p.grad is not None and torch.isfinite(p.grad).all() and bool(p.grad.abs().sum()>0) for p in model.parameters()):
    raise RuntimeError('new protected head has a dead zero initialization')
   if model_digest(model)!=before:raise RuntimeError('backward-only smoke unexpectedly updated parameters')
   proofs[arm]=dict(exact_RGB_initialization=True,gradient_nonzero=True,optimizer_updates=0,initial_state_sha256=before)
  write(self.base/'smoke'/('gpu%d_gradient.json'%self.gpu),dict(binding=binding(self.base),physical_gpu=self.gpu,CE=smoke_ce('cuda'),
    protected_heads=proofs,Torch_NumPy_feature_close=True,optimizer_updates=0,observed_at=now()))
  torch.cuda.empty_cache()
 def refresh(self,names):
  import torch
  from model.phase2_matched import FusionHead
  for name in names:
   if not name.startswith('T0') or name in self.heads:continue
   folder=self.base/'jobs/T0';done=read(folder/'complete.json')
   path=folder/('trajectory_04000.pth' if name.endswith('_4000') else 'endpoint.pth')
   expected=done['trajectory_sha256'] if name.endswith('_4000') else done['checkpoint_sha256']
   if done['binding']!=binding(self.base) or sha(path)!=expected:raise RuntimeError('T0 checkpoint differs')
   st=torch.load(path,map_location='cpu',weights_only=False)
   model=FusionHead('B0').cuda();model.load_state_dict(st['model']);self.heads[name]=model.eval().requires_grad_(False)
 def view(self,c,item):
  from phase2_infer import view
  if c['panel'] in ('clean','ordinary'):return view(self.old,item,c)
  from phase15_numeric import decode_mask
  from structured_v0_masks import canonical
  token=(c['tile'],c['family'],c['realization'],c['ratio'])
  if token not in self.mask_cache:
   row=self.mask_manifest['tiles'][c['tile']][str(c['realization'])][c['family']][str(c['ratio'])]
   mask=decode_mask(row['path'])
   if canonical(mask)!=row['canonical_sha256']:raise RuntimeError('canonical mask changed')
   mask.flags.writeable=False;self.mask_cache[token]=mask
   if len(self.mask_cache)>8:self.mask_cache.popitem(last=False)
  mask=self.mask_cache[token];self.mask_cache.move_to_end(token)
  rgb=np.array(item['optical']);ds=np.array(item['dsm']);rm=np.ones(ds.shape,bool);dm=rm.copy()
  if c['direction']=='rgb':
   rgb[mask]=0 if c['damage']=='zero' else item['rgb_down4'][mask]
   if c['panel']!='P-U':rm[mask]=False
  else:
   ds[mask]=0 if c['damage']=='zero' else item['dsm_down4'][mask]
   if c['panel']!='P-U':dm[mask]=False
  return rgb,ds,rm,dm,mask
 def infer(self,c,systems,smoke=False):
  import torch
  from torch.nn import functional as F
  from phase2_infer import view,coords
  from model.phase2_matched import observables
  self.refresh(systems);item=DATA[c['tile']]
  rgb,ds,rm,dm,mask=self.view(c,item);shape=ds.shape;cs=coords(shape)
  sr=torch.zeros((6,*shape),device='cuda',dtype=torch.float32);sd=torch.zeros_like(sr)
  scores={n:torch.zeros_like(sr) for n in systems if n in ('average','B0','B2') or n.startswith('T0')}
  coverage=np.zeros(shape,np.uint16);refs={n:np.zeros((6,*shape),np.float32) for n in ['rgb','dsm']+list(scores)} if smoke else None
  identity=True;started=time.monotonic();tick=started
  with torch.inference_mode():
   for start in range(0,len(cs),8):
    use=cs[start:start+8];num=len(use)
    ar=np.stack([rgb[y:y+512,x:x+512].transpose(2,0,1) for y,x in use])
    ad=np.stack([np.repeat(ds[y:y+512,x:x+512][None],3,0) for y,x in use])
    xr=torch.from_numpy(ar).cuda();xd=torch.from_numpy(ad).cuda()
    if num<8:
     xr=torch.cat((xr,xr[-1:].expand(8-num,-1,-1,-1)));xd=torch.cat((xd,xd[-1:].expand(8-num,-1,-1,-1)))
    def low(mod,model,image):
     clean=c['panel']=='clean' or (c['panel']!='ordinary' and c['direction']!=mod)
     if not clean:return model.low(image).float()[:num]
     cachekey=(c['tile'],mod)
     if cachekey not in self.clean_low:
      self.clean_low[cachekey]=dict(values=torch.empty((len(cs),6,128,128),device='cuda'),filled=np.zeros(len(cs),bool))
     cache=self.clean_low[cachekey]
     if not cache['filled'][start:start+num].all():
      cache['values'][start:start+num]=model.low(image).float()[:num];cache['filled'][start:start+num]=True
     return cache['values'][start:start+num]
    lowr=low('rgb',self.r,xr);lowd=low('dsm',self.d,xd)
    if lowr.shape!=(num,6,128,128) or lowd.shape!=lowr.shape:raise RuntimeError('frozen low-logit grid differs')
    r=F.interpolate(lowr,size=(512,512),mode='nearest');d=F.interpolate(lowd,size=(512,512),mode='nearest')
    mr=torch.from_numpy(np.stack([rm[y:y+512,x:x+512] for y,x in use])).cuda()
    md=torch.from_numpy(np.stack([dm[y:y+512,x:x+512] for y,x in use])).cuda()
    obs=observables(lowr,lowd,xr[:num],xd[:num,0],mr,md)
    zz={}
    for n in scores:
     if n=='average':z=torch.where((mr&md)[:,None],(r+d)/2,torch.where(mr[:,None],r,d))
     else:z=self.heads[n](lowr,lowd,obs,mr,md)
     identity &= torch.equal(z.masked_select((~mr&md)[:,None]),d.masked_select((~mr&md)[:,None]))
     identity &= torch.equal(z.masked_select((mr&~md)[:,None]),r.masked_select((mr&~md)[:,None]))
     zz[n]=z
    for i,(y,x) in enumerate(use):
     sr[:,y:y+512,x:x+512].add_(r[i]);sd[:,y:y+512,x:x+512].add_(d[i])
     coverage[y:y+512,x:x+512]+=1
     for n in scores:scores[n][:,y:y+512,x:x+512].add_(zz[n][i])
     if refs is not None:
      refs['rgb'][:,y:y+512,x:x+512]+=r[i].cpu().numpy();refs['dsm'][:,y:y+512,x:x+512]+=d[i].cpu().numpy()
      for n in scores:refs[n][:,y:y+512,x:x+512]+=zz[n][i].cpu().numpy()
    if time.monotonic()-tick>=15 or start+num==len(cs):
     write(self.base/('progress_gpu%d.json'%self.gpu),dict(case=c,phase='shared_expert_forward',windows_done=start+num,
       windows_total=len(cs),physical_gpu=self.gpu,elapsed_seconds=time.monotonic()-started,observed_at=now(),
       gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated()))
     tick=time.monotonic()
  if not identity or not coverage.all():raise RuntimeError('fallback/coverage failed')
  arrays=dict(r=sr.cpu().numpy(),d=sd.cpu().numpy(),coverage=coverage,rm=rm,dm=dm,mask=mask,ds=ds,
   zero=np.all(rgb==0,-1),full_gt=item['full_gt'],noboundary_gt=item['noboundary_gt'])
  from scipy.ndimage import maximum_filter
  arrays['healthy']=~maximum_filter(mask,size=17,mode='constant',cval=0).astype(bool)
  for n in scores:
   pred=scores[n].argmax(0).cpu().numpy().astype(np.uint8);pred[~(rm|dm)]=255;arrays[n]=pred
  checks={}
  if refs is not None:
   for n,z in [('rgb',sr),('dsm',sd)]+list(scores.items()):
    current=z.cpu().numpy();equal=np.array_equal(current,refs[n])
    if not equal:raise RuntimeError('GPU/CPU sequential stitch not bitwise exact: '+n)
    checks[n]=dict(logits_exact=True,prediction_exact=True)
   del refs
  from phase24_ipc import Packet
  packet=Packet.create(arrays)
  write(self.base/('runtime_gpu%d.json'%self.gpu),dict(physical_gpu=self.gpu,forward_seconds=time.monotonic()-started,
   packet_bytes=packet.meta['bytes'],stitch_reference=checks,observed_at=now(),
   gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated()))
  del arrays,sr,sd,scores,rgb,ds
  return packet,checks

def train(base,frozen,arm):
 import torch
 from torch.nn import functional as F
 from concurrent.futures import ThreadPoolExecutor
 from collections import deque
 from phase2_data import Crops,batch_hash,training_view
 from phase2_train import segmentation_ce,model_digest,smoke_ce
 from model.phase2_matched import FusionHead,optimizer,factor,observables
 from phase24_model import ProtectedHead,features_torch
 base=Path(base);out=base/'jobs'/arm;out.mkdir(parents=True,exist_ok=False);torch.manual_seed(42)
 model=(FusionHead('B0') if arm=='T0' else ProtectedHead(arm)).cuda()
 init=model_digest(model);oldparams=read(frozen.old/'jobs/B0/parameters.json')
 if arm=='T0' and init!=oldparams['initial_state_sha256']:raise RuntimeError('T0 clean/mixed initial state mismatch')
 smoke_ce('cuda');opt=optimizer(model,8000)
 ds=object.__new__(Crops);ds.tiles=DATA;ds.phase='phase23';ds.start=0;ds.stop=8000
 expected=[readline['batch_hash'] for readline in (json.loads(x) for x in (frozen.old/'jobs/B0/batch_hashes.jsonl').read_text().splitlines())]
 if len(expected)!=8000:raise RuntimeError('old common head stream incomplete')
 def batch(step):
  xs=[ds[(step-1)*16+i] for i in range(16)]
  return {n:torch.stack([x[n] for x in xs]).pin_memory() for n in ('rgb','dsm','gt')}|{'token':[x['token'] for x in xs]}
 def save(step,resume=False):
  name='last_resume.pth' if resume else ('trajectory_04000.pth' if step==4000 else 'endpoint.pth')
  path=out/name;tmp=path.with_suffix('.tmp')
  state=dict(model=model.state_dict(),arm=arm,step=step,binding=binding(base),initial_state_sha256=init)
  if resume:state.update(optimizer=opt.state_dict(),rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all())
  torch.save(state,tmp);os.replace(tmp,path)
  write(path.with_suffix('.json'),dict(sha256=sha(path),step=step,binding=binding(base)))
  export=model.weights() if arm!='T0' else dict(state_dict={n:v.detach().cpu().tolist() for n,v in model.state_dict().items()},deployment='window_head_FP32')
  write(out/(name.replace('.pth','_weights.json')),export)
 write(out/'parameters.json',dict(arm=arm,initial_state_sha256=init,trainable=sum(p.numel() for p in model.parameters()),
  expert_ages=16000,experts_frozen=True,seed=42,feature_names=FEATURES,regularization=0 if arm=='T0' else .01,
  train_batch=16,endpoint=8000,deployment='window_head' if arm=='T0' else 'FP64_post_stitch',registered_crop_shift=256 if arm=='T3' else None))
 start=time.monotonic();last=start
 with ThreadPoolExecutor(max_workers=4) as pool,(out/'trajectory.jsonl').open('x') as log,(out/'batch_hashes.jsonl').open('x') as hashes:
  ready=deque(pool.submit(batch,i) for i in range(1,5));next_step=5
  for step in range(1,8001):
   x=ready.popleft().result();wait=time.monotonic()-last
   if next_step<=8000:ready.append(pool.submit(batch,next_step));next_step+=1
   token=batch_hash(x['token'])
   if token!=expected[step-1]:raise RuntimeError('common stream mismatch at '+str(step))
   x={n:v.cuda(non_blocking=True) if torch.is_tensor(v) else v for n,v in x.items()}
   rgb,ds1=x['rgb'],x['dsm'];rm=torch.ones_like(ds1,dtype=torch.bool);dm=rm.clone()
   if arm!='T0':rgb,ds1,rm,dm,kinds=training_view(x,step)
   with torch.inference_mode():
    lowr=frozen.r.low(rgb).float();lowd=frozen.d.low(ds1[:,None].repeat(1,3,1,1)).float()
   # Clone inference tensors before autograd consumes them.
   lowr=lowr.clone();lowd=lowd.clone();opt.zero_grad(set_to_none=True)
   for g in opt.param_groups:g['lr']=g['initial_lr']*factor(step,8000)
   if arm=='T0':
    with torch.no_grad():obs=observables(lowr,lowd,rgb,ds1,rm,dm)
    z=model(lowr,lowd,obs,rm,dm);penalty=z.new_zeros(())
   else:
    r=F.interpolate(lowr,size=(512,512),mode='nearest');d=F.interpolate(lowd,size=(512,512),mode='nearest')
    with torch.no_grad():feat=features_torch(r,d,rgb,ds1,rm,dm)
    z,gate=model(r,d,feat,rm,dm);penalty=.01*gate.abs().mean()
   loss=segmentation_ce(z,x['gt'])+penalty;loss.backward()
   torch.nn.utils.clip_grad_norm_(model.parameters(),float('inf'),error_if_nonfinite=True)
   if step==1 and not any(p.grad is not None and bool(p.grad.abs().sum()>0) for p in model.parameters()):
    raise RuntimeError('head first update has no connected nonzero gradient')
   opt.step();hashes.write(json.dumps(dict(step=step,batch_hash=token))+'\n')
   if step==1 or step%20==0:
    row=dict(arm=arm,step=step,target=8000,loss=float(loss),regularizer=float(penalty),data_wait_seconds=wait,
      elapsed_seconds=time.monotonic()-start,physical_gpu=frozen.gpu,optimizer_updates=step,observed_at=now(),
      remaining_train_hours=(8000-step)*(time.monotonic()-start)/step/3600,
      gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated())
    log.write(json.dumps(row)+'\n');log.flush();hashes.flush();write(out/'progress.json',row)
   if step%200==0:save(step,True)
   if step in (4000,8000):save(step)
   last=time.monotonic();del x,lowr,lowd,z,loss
 write(out/'complete.json',dict(arm=arm,optimizer_updates=8000,binding=binding(base),checkpoint_sha256=sha(out/'endpoint.pth'),
  initial_state_sha256=init,stream_verified=True,stream_sha256=sha(out/'batch_hashes.jsonl'),
  trajectory_sha256=sha(out/'trajectory_04000.pth'),
  weights_sha256=sha(out/'endpoint_weights.json'),
  trajectory_weights_sha256=sha(out/'trajectory_04000_weights.json'),completed_at=now()))
 if arm=='T0':frozen.heads['T0']=model.eval().requires_grad_(False)
 del model,opt;torch.cuda.empty_cache()

def worker(base,gpu,tasks,events,acks):
 # Forked from a parent that has never imported Torch/CUDA.
 try:
  os.setsid()
  frozen=Frozen(base,gpu);events.put(dict(kind='READY',gpu=gpu,pid=os.getpid()))
  packets={}
  def drain(block=False):
   if not packets:return
   rows=[acks.get()] if block else []
   from queue import Empty
   while True:
    try:rows.append(acks.get_nowait())
    except Empty:break
   for row in rows:
    packet=packets.pop(row['id']);packet.close()
    if row.get('error'):raise RuntimeError('CPU consumer failed: '+row['error'])
  while True:
   drain()
   from queue import Empty
   try:command=tasks.get(timeout=.2)
   except Empty:continue
   if command['kind']=='STOP':break
   if command['kind']=='TRAIN':
    while packets:drain(True)
    train(base,frozen,command['arm']);events.put(dict(kind='TRAIN_COMPLETE',gpu=gpu,arm=command['arm']))
   else:
    if len(packets)>=2:drain(True)
    packet,checks=frozen.infer(command['case'],command['systems'],command.get('smoke',False))
    ident=command['stage']+'/'+cid(command['case']);packets[ident]=packet
    events.put(dict(kind='PACKET',gpu=gpu,id=ident,case=command['case'],stage=command['stage'],
      packet=packet.descriptor(),checks=checks,quota=command.get('quota',0),lock=command.get('lock'),
      heads=command.get('heads'),observed_at=now()))
   events.put(dict(kind='READY',gpu=gpu,pid=os.getpid()))
  while packets:drain(True)
  events.put(dict(kind='EXIT',gpu=gpu))
 except BaseException as exc:
  events.put(dict(kind='ERROR',gpu=gpu,error=str(exc),traceback=traceback.format_exc()))
  raise
 finally:
  for p in list(locals().get('packets',{}).values()):
   try:p.close()
   except Exception:pass
