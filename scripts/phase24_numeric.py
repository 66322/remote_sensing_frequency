"""One-pass stripe counts, deployable features and fixed-margin alignment reference."""
import math
import numpy as np
from scipy.ndimage import uniform_filter
from scipy.special import logsumexp, erf
from phase24_common import key, metric, FEATURES

def probabilities(z):
 z=np.asarray(z,np.float64);lp=z-logsumexp(z,axis=0,keepdims=True)
 return np.exp(lp),lp

def feature_core(r,d,ds_mean,ds_std,ds_grad,zero,rm,dm):
 pr,_=probabilities(r);pd,_=probabilities(d)
 ent=lambda p:-(p*np.log(np.maximum(p,1e-300))).sum(0)/math.log(6)
 margin=lambda p:np.sort(p,axis=0)[-1]-np.sort(p,axis=0)[-2]
 norm=lambda z:np.clip(np.log1p(np.sqrt(((z-z.mean(0,keepdims=True))**2).sum(0)))/8,0,1)
 values=[ent(pr),ent(pd),pr.max(0),pd.max(0),margin(pr),margin(pd),norm(r),norm(d),
  (r.argmax(0)!=d.argmax(0)).astype(float),np.clip(ds_mean/4,-1,1),
  np.clip(ds_std/4,0,1),np.clip(ds_grad/4,0,1),zero,rm,dm]
 return np.stack(values).astype(np.float32)

def native_features(packet,start,stop):
 ds=packet['ds'];dm=packet['dm'];rgbzero=packet['zero'];h,w=ds.shape
 lo=max(0,start-3);hi=min(h,stop+3);a=np.asarray(ds[lo:hi],np.float64);av=dm[lo:hi].astype(float)
 box=lambda x:uniform_filter(x,size=5,mode='nearest')
 weight=box(av);mean=box(a*av)/np.maximum(weight,1e-12)
 std=np.sqrt(np.maximum(0,box(a*a*av)/np.maximum(weight,1e-12)-mean*mean))
 gx=np.diff(a,axis=1);gx=np.pad(gx,((0,0),(0,1)),mode='edge')
 gy=np.diff(a,axis=0);gy=np.pad(gy,((0,1),(0,0)),mode='edge')
 mx=np.pad((av[:,1:]>0)&(av[:,:-1]>0),((0,0),(0,1)),mode='edge')
 my=np.pad((av[1:]>0)&(av[:-1]>0),((0,1),(0,0)),mode='edge')
 grad=np.sqrt((gx*mx)**2+(gy*my)**2)
 zf=box(np.asarray(rgbzero[lo:hi],float))
 cut=slice(start-lo,stop-lo)
 return mean[cut],std[cut],grad[cut],zf[cut]

def head_numpy(features,weights):
 # Explicit FP64 post-stitch inference; training is FP32. Both are tested.
 x=np.moveaxis(features,0,-1).astype(np.float64)
 w=weights;v=x@np.asarray(w['w0']).T+np.asarray(w['b0'])
 v=.5*v*(1+erf(v/math.sqrt(2)))
 return np.tanh(v@np.asarray(w['w1']).reshape(-1)+float(w['b1']))

def post_predictions(r,d,f,rm,dm,lock=None,heads=None,old=None,shifted=None):
 pr=r.argmax(0).astype(np.uint8);pd=d.argmax(0).astype(np.uint8)
 fallback=lambda pred:np.where(rm&dm,pred,np.where(rm,pr,pd)).astype(np.uint8)
 out={}
 if lock:
  tr,td=lock['temperature'];alpha=lock['alpha'];au=lock['alpha_uncalibrated']
  def mix(a,t):
   if a==1:return pr.copy()
   if a==0:return pd.copy()
   return (a*r/t[0]+(1-a)*d/t[1]).argmax(0).astype(np.uint8)
  out['calibrated']=fallback(mix(alpha,(tr,td)))
  out['uncalibrated']=fallback(mix(au,(1,1)))
  prob_r,_=probabilities(r/tr);prob_d,_=probabilities(d/td)
  out['probability_mix']=fallback((alpha*prob_r+(1-alpha)*prob_d).argmax(0).astype(np.uint8))
  z=lock['logistic'];x=np.moveaxis(f,0,-1)
  logit=((x-np.asarray(z['mean']))/np.asarray(z['scale']))@np.asarray(z['coefficient'])+z['intercept']
  p=1/(1+np.exp(-np.clip(logit,-700,700)))
  threshold=z['threshold']
  use=(p>=threshold)&(pr!=pd) if threshold is not None else np.zeros(pr.shape,bool)
  out['probe']=fallback(np.where(use,pd,pr))
  st=lock['stump'];p=np.where(f[st['feature']]>=st['cut'],st['right'],st['left'])
  out['stump']=fallback(np.where((p>=st['threshold'])&(pr!=pd),pd,pr)) if st['threshold'] is not None else fallback(pr)
  name=lock['reference']
  out['reference']={'rgb':fallback(pr),'calibrated':out['calibrated'],'uncalibrated':out['uncalibrated'],
   'average':old['average'],'B0':old['B0'],'B2':old['B2']}[name]
 for name,w in (heads or {}).items():
  x=f.copy()
  if name.split('_')[0]=='T2':x[:13]=0
  if name.split('_')[0]=='T3':
   if shifted is None:raise ValueError('missing fixed 256-pixel DSM-statistics shift')
   x[9:12]=shifted
  gate=head_numpy(x,w)
  z=r+gate[None]*(d-r);out[name]=fallback(z.argmax(0).astype(np.uint8))
 for name in out:out[name][~(rm|dm)]=255
 return out

def joint_to_cm(j):
 j=np.asarray(j,np.int64).reshape(6,6,6,6)
 return {'rgb':j.sum((2,3)),'dsm':j.sum((1,3)),'candidate':j.sum((1,2))}
def sparse(x):
 x=np.asarray(x,np.int64).ravel();at=np.flatnonzero(x)
 return [[int(i),int(x[i])] for i in at]
def stripe(packet,start,stop,case,quota=0,lock=None,heads=None):
 r=packet['r'][:,start:stop].astype(np.float64)/packet['coverage'][None,start:stop]
 d=packet['d'][:,start:stop].astype(np.float64)/packet['coverage'][None,start:stop]
 rm=packet['rm'][start:stop];dm=packet['dm'][start:stop]
 pr=packet['r'][:,start:stop].argmax(0).astype(np.uint8)
 pd=packet['d'][:,start:stop].argmax(0).astype(np.uint8)
 if not np.array_equal(r.argmax(0),pr) or not np.array_equal(d.argmax(0),pd):raise RuntimeError('coverage normalization changed argmax')
 a,b,c,z=native_features(packet,start,stop);f=feature_core(r,d,a,b,c,z,rm,dm)
 if not np.isfinite(f).all():raise RuntimeError('nonfinite deployable feature')
 pred={n:packet[n][start:stop] for n in packet if n in ('average','B0','B2') or n.startswith('T0')}
 shifted=None
 if heads and any(n.split('_')[0]=='T3' for n in heads):
  ids=(np.arange(start,stop)-256)%packet['ds'].shape[0];cuts=np.r_[0,np.flatnonzero(np.diff(ids)!=1)+1,len(ids)]
  fields=[]
  for i,j in zip(cuts[:-1],cuts[1:]):
   sm,ss,sg,_=native_features(packet,int(ids[i]),int(ids[j-1])+1)
   fields.append(np.stack([np.clip(sm/4,-1,1),np.clip(ss/4,0,1),np.clip(sg/4,0,1)]))
  shifted=np.roll(np.concatenate(fields,axis=1),256,axis=2).astype(np.float32)
 pred.update(post_predictions(r,d,f,rm,dm,lock,heads,pred,shifted))
 mask=packet['mask'][start:stop];valid=rm|dm;healthy=packet['healthy'][start:stop]
 regions={'all':valid,'missing':mask&valid,'healthy':healthy&valid,'observed':~mask&valid}
 result={'matrices':{},'joint':{},'flows':{},'blocks':{},'calibration':{},'fallback_errors':0}
 full_gt=packet['full_gt'][start:stop];nb_gt=packet['noboundary_gt'][start:stop]
 for name,p in pred.items():
  result['fallback_errors']+=int(((~rm&dm)&(p!=pd)).sum()+((rm&~dm)&(p!=pr)).sum())
 region_code=np.where(mask,0,np.where(healthy,1,2)).astype(np.int64)
 grid=np.indices((6,6,6,6)).reshape(4,-1)
 flow_dest=grid[0]*8+(grid[1]==grid[0])+2*(grid[2]==grid[0])+4*(grid[3]==grid[0])
 for scope,gt in [('full',full_gt),('noboundary',nb_gt)]:
  result['matrices'][scope]={};result['joint'][scope]={};result['flows'][scope]={}
  use=valid&(gt<6)
  base=gt[use].astype(np.int64)*216+pr[use].astype(np.int64)*36+pd[use].astype(np.int64)*6
  partition=region_code[use]*1296
  for n,prediction in pred.items():
   j=np.bincount(partition+base+prediction[use],minlength=3*1296).reshape(3,6,6,6,6)
   joints={'all':j.sum(0),'missing':j[0],'healthy':j[1],'observed':j[1]+j[2]}
   result['matrices'][scope][n]={};result['joint'][scope][n]={};result['flows'][scope][n]={}
   for region,joint in joints.items():
    result['joint'][scope][n][region]=joint
    result['matrices'][scope][n][region]=joint.sum((1,2))
    flow=np.zeros(48,np.int64);np.add.at(flow,flow_dest,joint.ravel())
    result['flows'][scope][n][region]=flow.reshape(6,8)
   if 'rgb' not in result['matrices'][scope]:
    result['matrices'][scope]['rgb']={q:a.sum((2,3)) for q,a in joints.items()}
    result['matrices'][scope]['dsm']={q:a.sum((1,3)) for q,a in joints.items()}
 use=valid&(nb_gt<6)
 calibrands=[('rgb',r,pr),('dsm',d,pd)]
 if lock:calibrands += [('rgb_calibrated',r/lock['temperature'][0],pr),('dsm_calibrated',d/lock['temperature'][1],pd)]
 for name,logits,p in calibrands:
  prob,lp=probabilities(logits);yy=nb_gt[use].astype(int);conf=prob.max(0)[use];correct=(p[use]==yy)
  bins=np.minimum(14,(conf*15).astype(int));code=yy*15+bins
  hist=np.zeros((6,15,3),float)
  hist[:,:,0]=np.bincount(code,minlength=90).reshape(6,15)
  hist[:,:,1]=np.bincount(code,weights=correct.astype(float),minlength=90).reshape(6,15)
  hist[:,:,2]=np.bincount(code,weights=conf,minlength=90).reshape(6,15)
  pv=prob[:,use];lv=lp[:,use];idx=np.arange(len(yy));pg=pv[yy,idx]
  brier=(pv*pv).sum(0)-2*pg+1
  result['calibration'][name]={'histogram':hist,'count':np.bincount(yy,minlength=6),
   'nll_sum':np.bincount(yy,weights=-lv[yy,idx],minlength=6),
   'brier_sum':np.bincount(yy,weights=brier,minlength=6),
   'confident_wrong':np.bincount(yy,weights=(~correct)&(conf>=.9),minlength=6)}
  margin=np.sort(pv,axis=0)[-1]-np.sort(pv,axis=0)[-2]
  entropy=-(pv*np.log(np.maximum(pv,1e-300))).sum(0)/math.log(6)
  norm=np.clip(np.log1p(np.sqrt(((logits-logits.mean(0,keepdims=True))**2).sum(0)))/8,0,1)[use]
  for field,value in [('margin',margin),('entropy',entropy),('center_norm',norm)]:
   bins=np.minimum(19,(value*20).astype(int))
   code=(yy*2+correct.astype(int))*20+bins
   result['calibration'][name][field+'_histogram']=np.bincount(code,minlength=240).reshape(6,2,20)
 preference=(pr[use]==nb_gt[use]).astype(int)+2*(pd[use]==nb_gt[use])
 for label,diff in [('margin_gap',f[4][use]-f[5][use]),('entropy_gap',f[0][use]-f[1][use])]:
  bins=np.clip(((diff+1)*10.5).astype(int),0,20)
  result['calibration'][label]=np.bincount((nb_gt[use].astype(int)*4+preference)*21+bins,minlength=504).reshape(6,4,21)
 yy,xx=np.indices(nb_gt.shape);yy+=start;blocks=(yy//256)*math.ceil(nb_gt.shape[1]/256)+xx//256
 for n,p in pred.items():
  v=valid&(nb_gt<5);bits=(pr[v]==nb_gt[v]).astype(int)+2*(pd[v]==nb_gt[v])+4*(p[v]==nb_gt[v])
  result['blocks'][n]=np.bincount(blocks[v]*8+bits,minlength=math.ceil(packet['rm'].shape[0]/256)*math.ceil(nb_gt.shape[1]/256)*8).reshape(-1,8)
 result['sample']=None
 if quota:
  eligible=use&(xx%2048>=512)&(xx%2048<1536)&(yy%2048>=512)&(yy%2048<1536)
  ids=np.flatnonzero(eligible);n=min(int(quota),len(ids))
  if n:
   rng=np.random.default_rng(key(42,'phase24_sample',case['tile'],case['panel'],case['direction'],case['family'],
    case['realization'],case['damage'],start))
   idx=rng.choice(ids,n,replace=False);y=yy.ravel()[idx];x=xx.ravel()[idx]
   lut=np.array([key(42,'inner',by,bx)%2 for by in range((packet['rm'].shape[0]+2047)//2048) for bx in range((packet['rm'].shape[1]+2047)//2048)],np.uint8)
   group=lut[(y//2048)*((packet['rm'].shape[1]+2047)//2048)+x//2048]
   region=(mask.ravel()[idx].astype(np.uint8)+2*healthy.ravel()[idx]+4*(~mask.ravel()[idx]))
   result['sample']={'r':np.moveaxis(r,0,-1).reshape(-1,6)[idx].astype(np.float32),
    'd':np.moveaxis(d,0,-1).reshape(-1,6)[idx].astype(np.float32),
    'features':np.moveaxis(f,0,-1).reshape(-1,15)[idx],
    'gt':nb_gt.ravel()[idx],'group':group,'region':region,
    'old':np.stack([pred[n].ravel()[idx] for n in ('average','B0','B2')],1),
    'expert':np.stack([pr.ravel()[idx],pd.ravel()[idx]],1),
    'coordinate':np.stack([y,x],1).astype(np.uint16),'weight':np.full(n,len(ids)/n,np.float64)}
 return result

def add_nested(a,b):
 if isinstance(b,dict):
  if a is None:a={}
  for k,v in b.items():a[k]=add_nested(a.get(k),v)
  return a
 if isinstance(b,np.ndarray):return b.copy() if a is None else a+b
 if b is None:return a
 return b if a is None else a+b

def combine(parts):
 out=None;samples=[]
 for part in parts:
  sample=part.pop('sample')
  if sample is not None:samples.append(sample)
  out=add_nested(out,part)
 out['joint']={scope:{n:{region:sparse(x) for region,x in regs.items()} for n,regs in systems.items()}
  for scope,systems in out['joint'].items()}
 out['blocks']={n:sparse(x) for n,x in out['blocks'].items()}
 def native(x):
  if isinstance(x,np.ndarray):return x.tolist()
  if isinstance(x,dict):return {k:native(v) for k,v in x.items()}
  return x
 sample={k:np.concatenate([x[k] for x in samples]) for k in samples[0]} if samples else None
 return native(out),sample

def exact_margin_tables(rows,cols,replicates,rng):
 rows=np.asarray(rows,np.int64);cols=np.asarray(cols,np.int64)
 if rows.sum()!=cols.sum():raise ValueError('marginals differ')
 output=np.zeros((replicates,6,6),np.int64);remaining=np.tile(cols,(replicates,1))
 for i in range(5):
  left=np.full(replicates,rows[i],np.int64)
  population=remaining.sum(1)
  for j in range(5):
   good=remaining[:,j];bad=population-good
   draw=np.zeros(replicates,np.int64);take=(left>0)&(population>0)
   draw[take]=rng.hypergeometric(good[take],bad[take],left[take])
   output[:,i,j]=draw;left-=draw;population-=good;remaining[:,j]-=draw
  output[:,i,5]=left;remaining[:,5]-=left
 output[:,5,:]=remaining
 if not np.array_equal(output.sum(2),np.tile(rows,(replicates,1))) or not np.array_equal(output.sum(1),np.tile(cols,(replicates,1))):
  raise RuntimeError('fixed-margin simulation violated marginals')
 return output

def null_cm(rgb,dsm,seed,replicates=1000):
 rgb=np.asarray(rgb,np.int64);dsm=np.asarray(dsm,np.int64);rng=np.random.default_rng(seed)
 out=np.zeros((replicates,6,6),np.int64)
 for gt in range(6):
  table=exact_margin_tables(rgb[gt],dsm[gt],replicates,rng)
  # RGB-priority oracle: choose correct R, otherwise correct D, otherwise R.
  for r in range(6):
   for d in range(6):
    pred=gt if (r==gt or d==gt) else r
    out[:,gt,pred]+=table[:,r,d]
 return out
