"""Source-only fitting. Target data is not accepted by this interface."""
import numpy as np
from scipy.optimize import minimize, minimize_scalar
from scipy.special import logsumexp, expit
from phase24_common import cid, metric, FEATURES

ALPHAS=[0,.25,.5,.75,.9,.95,1]
THRESHOLDS=[.5,.7,.9,.95,.99]
LAMBDAS=[.1,1,10]

def weighted_cm(y,p,w):
 return np.bincount(y.astype(np.int64)*6+p.astype(np.int64),weights=w,minlength=36).reshape(6,6)
def sample_scores(records,preds,panel='P-U',direction=None,region='all'):
 values=[]
 for (c,z),pred in zip(records,preds):
  if c['panel']!=panel or (direction and c['direction']!=direction):continue
  keep=z['group']==1
  if region=='healthy':keep &= (z['region']&2)>0
  if region=='missing':keep &= (z['region']&1)>0
  if not keep.any():continue
  v=metric(weighted_cm(z['gt'][keep],pred[keep],z['weight'][keep]))
  if v is not None:values.append(v)
 return float(np.mean(values)) if values else None
def protections(records,preds,rgb_preds):
 for pan,dr,reg in [('clean',None,'all'),('P-U','dsm','all'),('P-U',None,'healthy')]:
  a=sample_scores(records,preds,pan,dr,reg);b=sample_scores(records,rgb_preds,pan,dr,reg)
  if a is None or b is None or a-b<-.2:return False
 return True

def fit_temperature(records,expert):
 zs=[];ys=[];ws=[]
 for c,z in records:
  if c['panel']!='clean':continue
  keep=z['group']==0;zs.append(z[expert][keep].astype(np.float64));ys.append(z['gt'][keep]);ws.append(z['weight'][keep])
 x=np.concatenate(zs);y=np.concatenate(ys).astype(int);w=np.concatenate(ws)
 if len(y)<1000:raise RuntimeError('source clean temperature support insufficient')
 def objective(logt):
  logits=x/np.exp(logt);loss=logsumexp(logits,axis=1)-logits[np.arange(len(y)),y]
  return float(w@loss/w.sum())
 opt=minimize_scalar(objective,bounds=(np.log(.25),np.log(4)),method='bounded',options={'xatol':1e-6})
 if not opt.success or not np.isfinite(opt.fun):raise RuntimeError('temperature fitting did not converge')
 return float(np.exp(opt.x)),dict(source_clean_training_pixels=len(y),nll_before=objective(0),nll_after=float(opt.fun))

def mix_predictions(records,alpha,temperatures):
 out=[]
 for c,z in records:
  if alpha==1:p=z['expert'][:,0].copy()
  elif alpha==0:p=z['expert'][:,1].copy()
  else:p=(alpha*z['r'].astype(float)/temperatures[0]+(1-alpha)*z['d'].astype(float)/temperatures[1]).argmax(1).astype(np.uint8)
  out.append(p)
 return out
def select_alpha(records,temperatures):
 rgb=mix_predictions(records,1,(1,1));best=None;curve=[]
 for alpha in ALPHAS:
  p=mix_predictions(records,alpha,temperatures);score=sample_scores(records,p)
  protected=protections(records,p,rgb);curve.append(dict(alpha=alpha,P_U=score,protected=protected))
  if protected and score is not None and (best is None or (score,alpha)>(best[0],best[1])):best=(score,alpha)
 if best is None:raise RuntimeError('even RGB source fallback could not be selected')
 return best[1],curve

def fit_logistic(x,y,w,lam):
 w=w/w.sum()
 def obj(beta):
  a=x@beta[:-1]+beta[-1];p=expit(a)
  loss=float(w@(np.logaddexp(0,a)-y*a)+lam*.5*(beta[:-1]@beta[:-1]))
  diff=w*(p-y);grad=np.r_[x.T@diff+lam*beta[:-1],diff.sum()]
  return loss,grad
 opt=minimize(obj,np.zeros(x.shape[1]+1),jac=True,method='L-BFGS-B',options={'maxiter':200,'ftol':1e-10})
 if not opt.success:raise RuntimeError('logistic fit did not converge: '+str(opt.message))
 return opt.x
def logistic_predictions(records,model,threshold):
 out=[]
 for c,z in records:
  x=(z['features'].astype(float)-model['mean'])/model['scale']
  p=expit(x@model['coefficient']+model['intercept'])
  r,d=z['expert'].T
  use=(p>=threshold)&(r!=d) if threshold is not None else np.zeros(len(r),bool)
  out.append(np.where(use,d,r).astype(np.uint8))
 return out

def fit_fold(source,records):
 if not records or any(c['tile']!=source or c['panel'] not in ('clean','P-U') for c,_ in records):raise ValueError('source-only clean/P-U records required')
 records=sorted(records,key=lambda x:cid(x[0]))
 tr,rfit=fit_temperature(records,'r');td,dfit=fit_temperature(records,'d')
 alpha,curve=select_alpha(records,(tr,td));au,ucurve=select_alpha(records,(1,1))
 rgb=mix_predictions(records,1,(1,1));cal=mix_predictions(records,alpha,(tr,td));unc=mix_predictions(records,au,(1,1))
 candidates={'rgb':rgb,'calibrated':cal,'uncalibrated':unc}
 for j,n in enumerate(('average','B0','B2')):candidates[n]=[z['old'][:,j] for _,z in records]
 allowed={n:p for n,p in candidates.items() if protections(records,p,rgb)}
 reference=max(allowed,key=lambda n:(sample_scores(records,allowed[n]),n=='rgb',n))
 xs=[];ys=[];ws=[]
 for c,z in records:
  r,d=z['expert'].T;keep=(z['group']==0)&(r!=d)
  xs.append(z['features'][keep]);ys.append(((d[keep]==z['gt'][keep])&(r[keep]!=z['gt'][keep])).astype(float));ws.append(z['weight'][keep])
 x=np.concatenate(xs).astype(float);y=np.concatenate(ys);w=np.concatenate(ws)
 if len(y)<128 or np.count_nonzero(y)<64 or np.count_nonzero(1-y)<64:
  return dict(source=source,target='5_10' if source=='3_11' else '3_11',temperature=[tr,td],alpha=alpha,
   alpha_uncalibrated=au,reference=reference,
   logistic=dict(mean=[0]*15,scale=[1]*15,coefficient=[0]*15,intercept=-50,threshold=None,l2=1),
   stump=dict(feature=0,cut=0,left=0,right=0,threshold=None),feature_names=FEATURES,
   temperature_fit={'rgb':rfit,'dsm':dfit},alpha_curve=curve,uncalibrated_curve=ucurve,
   source_record_ids=[cid(c) for c,_ in records],target_used_for_fitting=False,
   preference_support=False,reason='insufficient source-only preference support; protected RGB fallback',
   segmentation_optimizer_updates=0)
 mean=(x*w[:,None]).sum(0)/w.sum();scale=np.sqrt(((x-mean)**2*w[:,None]).sum(0)/w.sum());scale[scale<1e-6]=1
 x=(x-mean)/scale
 if np.count_nonzero(y)<64 or np.count_nonzero(1-y)<64:raise RuntimeError('unexpected source support changed')
 chosen=None;grid=[]
 for lam in LAMBDAS:
  beta=fit_logistic(x,y,w,lam);m=dict(mean=mean,scale=scale,coefficient=beta[:-1],intercept=float(beta[-1]))
  for threshold in THRESHOLDS:
   p=logistic_predictions(records,m,threshold);score=sample_scores(records,p);protected=protections(records,p,rgb)
   grid.append(dict(l2=lam,threshold=threshold,P_U=score,protected=protected))
   if protected and score is not None and (chosen is None or (score,threshold,lam)>(chosen[0],chosen[1],chosen[2])):
    chosen=(score,threshold,lam,m)
 if chosen is None:
  beta=fit_logistic(x,y,w,1);model=dict(mean=mean,scale=scale,coefficient=beta[:-1],intercept=float(beta[-1]),threshold=None,l2=1)
 else:model=dict(chosen[3],threshold=chosen[1],l2=chosen[2])
 # Fixed depth-one sensitivity model, fitted without target/source-calibration labels.
 raw=x*scale+mean;best_stump=None
 for j in range(len(FEATURES)):
  for q in (.1,.25,.5,.75,.9):
   cut=float(np.quantile(raw[:,j],q));right=raw[:,j]>=cut
   wl=w[~right].sum();wr=w[right].sum()
   if wl==0 or wr==0:continue
   left=float(w[~right]@y[~right]/wl);rp=float(w[right]@y[right]/wr)
   loss=float(w@((np.where(right,rp,left)-y)**2)/w.sum())
   if best_stump is None or loss<best_stump[0]:best_stump=(loss,dict(feature=j,cut=cut,left=left,right=rp))
 stump=best_stump[1] if best_stump is not None else dict(feature=0,cut=0,left=float(w@y/w.sum()),right=float(w@y/w.sum()))
 best=None
 for t in THRESHOLDS:
  preds=[]
  for c,z in records:
   p=np.where(z['features'][:,stump['feature']]>=stump['cut'],stump['right'],stump['left'])
   r,d=z['expert'].T;preds.append(np.where((p>=t)&(r!=d),d,r).astype(np.uint8))
  sc=sample_scores(records,preds)
  if protections(records,preds,rgb) and sc is not None and (best is None or (sc,t)>best):best=(sc,t)
 stump['threshold']=None if best is None else best[1]
 def lists(v):
  if isinstance(v,np.ndarray):return v.tolist()
  if isinstance(v,dict):return {k:lists(x) for k,x in v.items()}
  return v
 return lists(dict(source=source,target='5_10' if source=='3_11' else '3_11',temperature=[tr,td],
  alpha=alpha,alpha_uncalibrated=au,reference=reference,logistic=model,stump=stump,
  temperature_fit={'rgb':rfit,'dsm':dfit},alpha_curve=curve,uncalibrated_curve=ucurve,logistic_grid=grid,
  feature_names=FEATURES,source_record_ids=[cid(c) for c,_ in records],
  fit_sample_pixels=len(y),positive_labels=int(y.sum()),source_split='2048 blocks, hash(42,inner,by,bx)%2; 512 guard',
  sample_population='eligible guarded interiors, inverse inclusion weighting within each stripe; not a full-tile score',
  target_used_for_fitting=False,segmentation_optimizer_updates=0))
