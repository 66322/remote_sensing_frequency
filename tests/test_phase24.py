"""Scientific invariants on synthetic data; real CUDA bridge remains server-only."""
import copy,json,sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase24_common import panel,smoke_cases,cid
from phase24_numeric import stripe,combine,exact_margin_tables,null_cm,native_features,feature_core,head_numpy
from phase24_analysis import gate
from phase24_fit import fit_fold
from verify_phase24_results import validate_row
CONDITIONS=['clean']+['ordinary'+str(i) for i in range(21)]
def packet(h=35,w=31):
 rng=np.random.default_rng(19);gt=rng.integers(0,6,(h,w),dtype=np.uint8);gt[0,:3]=255
 r=rng.normal(size=(6,h,w)).astype(np.float32);d=rng.normal(size=r.shape).astype(np.float32)
 rm=np.ones((h,w),bool);dm=rm.copy();rm[:3,:3]=False;dm[5:8,5:8]=False
 mask=np.zeros((h,w),bool);mask[:,8:12]=True;healthy=~mask
 old={n:np.where(rm&dm,((r+d)/2).argmax(0),np.where(rm,r.argmax(0),d.argmax(0))).astype(np.uint8) for n in ('average','B0','B2')}
 return dict(r=r,d=d,coverage=np.ones((h,w),np.uint16),rm=rm,dm=dm,mask=mask,healthy=healthy,
  ds=rng.normal(size=(h,w)).astype(np.float32),zero=rng.random((h,w))<.15,full_gt=gt,noboundary_gt=gt,**old)
CASE=dict(tile='3_11',panel='P-U',direction='rgb',family='pixel',realization=1,ratio=25,damage='zero')
class Contracts(unittest.TestCase):
 def test_panel_and_smoke_counts(self):
  rows=panel(CONDITIONS);sm=smoke_cases(rows)
  self.assertEqual((len(rows),sum(c['panel'] in ('clean','P-U') for c in rows),len(sm)),(1164,642,12))
  self.assertEqual(len(set(map(cid,rows))),1164)
  self.assertEqual([sum(i%2==g for i in range(len(sm))) for g in (0,1)],[6,6])
 def test_fixed_margins(self):
  rng=np.random.default_rng(1)
  for rows,cols in [(np.array([5,8,0,4,3,7]),np.array([2,4,5,6,7,3])),(np.zeros(6,int),np.zeros(6,int))]:
   t=exact_margin_tables(rows,cols,1000,rng)
   np.testing.assert_array_equal(t.sum(1),np.tile(cols,(1000,1)))
   np.testing.assert_array_equal(t.sum(2),np.tile(rows,(1000,1)))
  with self.assertRaises(ValueError):exact_margin_tables(np.ones(6,int),np.zeros(6,int),3,rng)
 def test_null_conserves_groundtruth(self):
  r=np.arange(36).reshape(6,6);d=r[:,::-1]
  out=null_cm(r,d,4,300);np.testing.assert_array_equal(out.sum(2),np.tile(r.sum(1),(300,1)))
 def test_stripe_integer_partition(self):
  p=packet();full,_=combine([stripe(p,0,35,CASE)])
  split,_=combine([stripe(p,0,13,CASE),stripe(p,13,29,CASE),stripe(p,29,35,CASE)])
  for n in ('matrices','joint','flows','blocks'):self.assertEqual(full[n],split[n])
  self.assertEqual(full['fallback_errors'],0)
  for system in full['matrices']['full']:
   pred=p[system] if system in p else p['r' if system=='rgb' else 'd'].argmax(0)
   use=(p['rm']|p['dm'])&(p['full_gt']<6)
   expected=np.bincount(p['full_gt'][use].astype(int)*6+pred[use],minlength=36).reshape(6,6)
   np.testing.assert_array_equal(full['matrices']['full'][system]['all'],expected)
 def test_T0_trajectory_is_counted(self):
  p=packet();p['T0']=p['average'].copy();p['T0_4000']=p['average'].copy()
  z,_=combine([stripe(p,0,35,CASE)])
  for n in ('T0','T0_4000'):self.assertEqual(z['matrices']['full'][n],z['matrices']['full']['average'])
 def test_native_feature_halos(self):
  p=packet();full=native_features(p,0,35)
  for a,b in [(0,4),(4,20),(20,35)]:
   part=native_features(p,a,b)
   for f,v in zip(full,part):np.testing.assert_allclose(f[a:b],v,atol=1e-7,rtol=1e-6)
 def test_validate_rejects_noninteger_and_partition_change(self):
  z,_=combine([stripe(packet(),0,35,CASE)])
  z.update(case=CASE,binding={'a':'b'})
  self.assertTrue(validate_row(z,{'a':'b'}))
  for mutate in ('float','partition','binding'):
   q=copy.deepcopy(z)
   if mutate=='float':q['matrices']['full']['rgb']['all'][0][0]=1.0
   elif mutate=='partition':q['matrices']['full']['rgb']['all'][0][0]+=1
   else:q['binding']={}
   with self.assertRaises(RuntimeError):validate_row(q,{'a':'b'})
 def test_gate_requires_both_tile_protection(self):
  rows=[]
  for c in panel(CONDITIONS):
   if c['panel'] not in ('clean','P-U'):continue
   ref=np.diag([100]*6);pred=ref.copy()
   if c['panel']=='P-U' and c['direction']=='rgb':
    ref[0,0]-=10;ref[0,1]+=10
   regs=lambda x:{k:x.tolist() for k in ('all','missing','healthy','observed')}
   rows.append(dict(case=c,matrices={'noboundary':{'reference':regs(ref),'rgb':regs(ref),'x':regs(pred)}},fallback_errors=0))
  self.assertTrue(gate(rows,'x')['accepted'])
  bad=copy.deepcopy(rows)
  for r in bad:
   if r['case']['panel']=='clean' and r['case']['tile']=='5_10':
    cm=np.array(r['matrices']['noboundary']['x']['all']);cm[0,0]-=20;cm[0,1]+=20
    r['matrices']['noboundary']['x']['all']=cm.tolist()
  self.assertFalse(gate(bad,'x')['accepted'])
 def test_source_fit_rejects_target_and_handles_no_preference(self):
  n=3000;gt=(np.arange(n)%6).astype(np.uint8);logits=np.eye(6,dtype=np.float32)[gt]*3
  z=dict(r=logits,d=logits,features=np.zeros((n,15),np.float32),gt=gt,
   group=(np.arange(n)%2).astype(np.uint8),region=np.full(n,6,np.uint8),
   old=np.tile(gt[:,None],(1,3)),expert=np.tile(gt[:,None],(1,2)),weight=np.ones(n))
  cases=[dict(CASE,panel='clean',direction='none'),CASE,dict(CASE,direction='dsm')]
  out=fit_fold('3_11',[(c,z) for c in cases])
  self.assertFalse(out['target_used_for_fitting']);self.assertIsNone(out['logistic']['threshold'])
  self.assertEqual(out['source'],'3_11');self.assertEqual(out['target'],'5_10')
  with self.assertRaises(ValueError):fit_fold('3_11',[(dict(CASE,tile='5_10'),z)])
 def test_constant_features_keep_constant_stump(self):
  n=3600;gt=(np.arange(n)%6).astype(np.uint8);r=np.eye(6,dtype=np.float32)[gt]*3;d=r.copy()
  unique=(np.arange(n)//2)%4==0;wrong=(gt[unique]+1)%6;r[unique]=np.eye(6,dtype=np.float32)[wrong]*3
  expert=np.stack((r.argmax(1),d.argmax(1)),1).astype(np.uint8)
  z=dict(r=r,d=d,features=np.zeros((n,15),np.float32),gt=gt,group=(np.arange(n)%2).astype(np.uint8),
   region=np.full(n,6,np.uint8),old=np.tile(expert[:,0,None],(1,3)),expert=expert,weight=np.ones(n))
  # Include both DSM-unique positives and disagreement negatives without varying features.
  negative=(np.arange(n)//2)%4==1;d[negative]=np.eye(6,dtype=np.float32)[(gt[negative]+1)%6]*3
  z['expert'][:,1]=d.argmax(1)
  cases=[dict(CASE,panel='clean',direction='none'),CASE,dict(CASE,direction='dsm')]
  out=fit_fold('3_11',[(c,z) for c in cases])
  self.assertEqual(out['stump']['left'],out['stump']['right']);self.assertFalse(out['target_used_for_fitting'])
 def test_rebuild_rejects_consistent_hash_but_wrong_summary(self):
  import tempfile
  from unittest.mock import patch
  import verify_phase24_results as verifier
  from phase24_common import write,read,sha,binding,FIT,VAL
  from phase24_analysis import trajectory_summary,paired_summary
  parent=Path(__file__).resolve().parent/'temporary';parent.mkdir(exist_ok=True)
  with tempfile.TemporaryDirectory(dir=parent,prefix='unit_only_') as folder:
   base=Path(folder);write(base/'plan.json',dict(fit12=FIT,val2=VAL,gpus=[0,1],seed=42,max_head_updates=32000,automatic_retry=False,new_seeds=False,fixed_conditions=[]))
   write(base/'code_manifest.json',dict(files={}));b=binding(base);write(base/'registration.json',dict(binding=b))
   cases=[dict(CASE,panel='clean',direction='none'),dict(CASE,panel='clean',direction='none',tile='5_10'),dict(CASE,panel='ordinary',direction='none')]
   locks={}
   for target,source in [('3_11','5_10'),('5_10','3_11')]:
    path='fits/source_'+source+'.json';write(base/path,dict(binding=b,source=source,target=target,target_used_for_fitting=False))
    locks[target]=dict(path=path,sha256=sha(base/path),source=source,target=target)
   refs=[];end=[];diagnostic=[]
   systems=['rgb','dsm','reference','calibrated','probe','T0','T0_4000']
   cm=np.diag([100]*6).tolist();zero=np.zeros((6,6),int).tolist()
   for stage,cs in [('E',cases),('D2',cases[:2]),('D3',cases[2:])]:
    for c in cs:
     row=dict(case=c,stage=stage,binding=b,fallback_errors=0,lock=locks[c['tile']],
      matrices={scope:{n:dict(all=cm,missing=zero,observed=cm,healthy=cm) for n in systems} for scope in ('full','noboundary')})
     path='results/'+stage+'/'+cid(c)+'.json';write(base/path,row)
     refs.append(dict(path=path,sha256=sha(base/path)))
     (end if stage=='E' else diagnostic).append(row)
   summary=dict(binding=b,results=trajectory_summary(end),
    deployment_gate={n:gate(diagnostic,n) for n in ('calibrated','probe')},
    trained_heads=['T0'],total_optimizer_updates=8000,old_expert_optimizer_updates=0,
    paired_mask_intervals={'T0':paired_summary(end,'T0','reference')},signal_gate=None)
   write(base/'summary.json',summary)
   write(base/'evidence_index.json',dict(binding=b,records=refs,summary_sha256=sha(base/'summary.json')))
   with patch.object(verifier,'panel',return_value=cases):
    verifier.verify_results(base)
    summary['results']['T0']['clean']['all']-=1;write(base/'summary.json',summary)
    index=read(base/'evidence_index.json');index['summary_sha256']=sha(base/'summary.json');write(base/'evidence_index.json',index)
    with self.assertRaisesRegex(RuntimeError,'summary does not reproduce'):verifier.verify_results(base)
 def test_temperature_does_not_change_expert_argmax(self):
  p=packet()
  for t in (.25,1,4):np.testing.assert_array_equal(p['r'].argmax(0),(p['r']/t).argmax(0))

class Differentiable(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  import torch
  torch.set_num_threads(1);cls.torch=torch
 def test_matched_static_initial_state_and_pairing(self):
  import hashlib
  from model.phase2_matched import FusionHead
  from phase24_model import ProtectedHead
  def digest(m):
   h=hashlib.sha256()
   for n,v in m.state_dict().items():h.update(n.encode());h.update(v.detach().contiguous().numpy().tobytes())
   return h.hexdigest()
  self.assertEqual(digest(FusionHead('B0')),'4a3c4bafb567b46b71c30c4577b4b6b96906250d74ea14d2cf477048456d0a69')
  hashes=[]
  for arm in ('T1','T2','T3'):
   self.torch.manual_seed(42);hashes.append(digest(ProtectedHead(arm)))
  self.assertEqual(len(set(hashes)),1)
  from model.phase2_matched import observables
  t=self.torch;r=t.randn(1,6,32,32);d=t.randn_like(r);rgb=t.randn(1,3,32,32);ds=t.randn(1,32,32);mask=t.ones_like(ds,dtype=t.bool)
  m=FusionHead('B0');z=m(r,d,observables(r,d,rgb,ds,mask,mask),mask,mask)
  t.nn.functional.cross_entropy(z,t.arange(1024).reshape(1,32,32)%6).backward()
  self.assertTrue(all(p.grad is not None and t.isfinite(p.grad).all() for p in m.parameters()))
  self.assertTrue(any(float(p.grad.abs().sum())>0 for p in m.parameters()))
 def test_features_torch_numpy_agree(self):
  from phase24_model import features_torch
  torch=self.torch;p=packet(32,32)
  rgb=np.stack([p['zero'].astype(np.float32)]*3);rgb=1-rgb
  args=[torch.tensor(p['r'][None]),torch.tensor(p['d'][None]),torch.tensor(rgb[None]),torch.tensor(p['ds'][None]),torch.tensor(p['rm'][None]),torch.tensor(p['dm'][None])]
  f=features_torch(*args)[0].numpy();a,b,c,z=native_features(p,0,32)
  ref=feature_core(p['r'],p['d'],a,b,c,z,p['rm'],p['dm'])
  np.testing.assert_allclose(f,ref,rtol=1e-5,atol=1e-5)
 def test_exact_initialization_and_live_gradient(self):
  from phase24_model import ProtectedHead
  torch=self.torch;torch.manual_seed(42)
  r=torch.randn(1,6,32,32);d=torch.randn_like(r);f=torch.randn(1,15,32,32)
  rm=torch.ones((1,32,32),dtype=torch.bool);dm=rm.clone();rm[:,:4]=False;dm[:,8:12]=False
  for arm in ('T1','T2','T3'):
   torch.manual_seed(42);m=ProtectedHead(arm);before=copy.deepcopy(m.state_dict())
   z,g=m(r,d,f,rm,dm);ref=torch.where((rm&dm)[:,None],r,torch.where(rm[:,None],r,d))
   self.assertTrue(torch.equal(z,ref));self.assertEqual(float(g.abs().sum()),0)
   target=torch.arange(1024).reshape(1,32,32)%6
   torch.nn.functional.cross_entropy(z,target).backward()
   self.assertGreater(float(m.net[-1].weight.grad.abs().sum()),0)
   for k,v in m.state_dict().items():self.assertTrue(torch.equal(v,before[k]))
 def test_export_matches_nonzero_torch_gate(self):
  from phase24_model import ProtectedHead
  torch=self.torch;torch.manual_seed(5);m=ProtectedHead('T1')
  with torch.no_grad():m.net[-1].weight.fill_(.02);m.net[-1].bias.fill_(.01)
  f=torch.randn(1,15,32,32);expected=torch.tanh(m.net(f))[0,0].detach().numpy()
  actual=head_numpy(f[0].numpy(),m.weights());np.testing.assert_allclose(actual,expected,atol=1e-6,rtol=1e-5)
 def test_capacity_control_removes_only_signal_features(self):
  from phase24_model import ProtectedHead
  torch=self.torch;m=ProtectedHead('T2')
  with torch.no_grad():m.net[-1].weight.fill_(.02)
  r=torch.zeros(1,6,8,8);d=torch.randn_like(r);a=torch.randn(1,15,8,8);b=a.clone();b[:,:13]*=100
  rm=torch.ones((1,8,8),dtype=torch.bool)
  self.assertTrue(torch.equal(m(r,d,a,rm,rm)[0],m(r,d,b,rm,rm)[0]))
 def test_statistics_control_only_rolls_three_slots(self):
  from phase24_model import ProtectedHead
  torch=self.torch;m=ProtectedHead('T3');m.arm='T1'
  with torch.no_grad():m.net[-1].weight.fill_(.02)
  f=torch.randn(1,15,259,9);r=torch.randn(1,6,259,9);d=torch.randn_like(r);rm=torch.ones((1,259,9),dtype=torch.bool)
  expected=f.clone();expected[:,9:12]=torch.roll(expected[:,9:12],(256,256),(-2,-1))
  z=m(r,d,expected,rm,rm)[0];m.arm='T3'
  self.assertTrue(torch.equal(z,m(r,d,f,rm,rm)[0]))

def receive_child(q,out):
 from phase24_ipc import Packet
 p=Packet.receive(q.get())
 try:
  out.put((float(p.arrays['x'].sum()),p.arrays['x'].flags.writeable))
 finally:p.close()

@unittest.skipUnless(hasattr(__import__('os'),'memfd_create'),'Linux memfd server transport required')
class Transport(unittest.TestCase):
 def test_cross_process_readonly(self):
  import multiprocessing as mp
  from phase24_ipc import Packet
  ctx=mp.get_context('spawn');q=ctx.Queue();out=ctx.Queue();p=Packet.create({'x':np.arange(100,dtype=np.float32)})
  child=ctx.Process(target=receive_child,args=(q,out));child.start()
  try:
   q.put(p.descriptor());result=out.get(timeout=30);child.join(timeout=10)
   self.assertEqual(result,(4950.0,False));self.assertEqual(child.exitcode,0)
  finally:
   if child.is_alive():child.terminate();child.join(timeout=5)
   p.close();q.close();out.close()
 def test_roundtrip_and_last_close(self):
  from phase24_ipc import Packet
  a=np.arange(30,dtype=np.float32).reshape(5,6);p=Packet.create({'x':a})
  other=Packet.receive(p.descriptor());np.testing.assert_array_equal(other.arrays['x'],a)
  other.close();p.close()
if __name__=='__main__':unittest.main()
