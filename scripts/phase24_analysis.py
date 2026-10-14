"""Development-only gates and original-count diagnostics; no site-level significance claims."""
from pathlib import Path
from collections import defaultdict
import numpy as np
from phase24_common import *

def gate(rows,name,reference='reference'):
 checks={};delta=lambda pan,dr,t,region,ref: _delta(scores(rows,name,pan,dr,t,region),scores(rows,ref,pan,dr,t,region))
 checks['P_U_gain']=delta('P-U',None,None,'all',reference)
 checks['rgb_fault_gain']=delta('P-U','rgb',None,'all',reference)
 checks['positive_RGB_fault_tiles']={t:delta('P-U','rgb',t,'all',reference) for t in VAL}
 protect={}
 for pan,dr,reg in [('clean',None,'all'),('P-U','dsm','all'),('P-U',None,'healthy')]:
  for t in VAL:
   for ref in (reference,'rgb'):
    protect['/'.join((pan,dr or 'both',reg,t,ref))]=delta(pan,dr,t,reg,ref)
 checks['protections']=protect
 worst=[]
 for dr in ('rgb','dsm'):
  for fam in FAMILIES:
   for damage in ('zero','down4'):
    subset=[r for r in rows if r['case']['direction']==dr and r['case']['family']==fam and r['case']['damage']==damage]
    for ref in (reference,'rgb'):
     v=_delta(scores(subset,name),scores(subset,ref))
     if v is not None:worst.append(v)
 checks['worst_family_damage']=min(worst) if worst else None
 checks['fallback_exact']=all(r['fallback_errors']==0 for r in rows)
 accepted=(checks['P_U_gain'] is not None and checks['P_U_gain']>=.3 and
  checks['rgb_fault_gain'] is not None and checks['rgb_fault_gain']>=.5 and
  all(x is not None and x>0 for x in checks['positive_RGB_fault_tiles'].values()) and
  all(x is not None and x>=-.2 for x in protect.values()) and
  checks['worst_family_damage'] is not None and checks['worst_family_damage']>=-.5 and checks['fallback_exact'])
 return dict(accepted=accepted,candidate=name,reference=reference,checks=checks,
  interpretation='development gate on two reused Val2 tiles, seed42; no independent test claim')
def _delta(a,b):return None if a is None or b is None else a-b

def paired_summary(rows,name,reference):
 values=[]
 for i in range(1,21):
  subset=[r for r in rows if r['case']['realization']==i]
  d=_delta(scores(subset,name),scores(subset,reference))
  if d is not None:values.append(d)
 if len(values)!=20:return dict(mask_pairs=len(values),mean=None,interval95=None)
 x=np.array(values);rng=np.random.default_rng(20261014)
 sim=x[rng.integers(0,20,(5000,20))].mean(1)
 return dict(mask_pairs=20,mean=float(x.mean()),interval95=np.quantile(sim,[.025,.975]).tolist(),
  interpretation='paired mask perturbations conditional on two reused sites; pixels/masks are not independent sites')

def trajectory_summary(rows):
 names=sorted(rows[0]['matrices']['noboundary'])
 return {name:{p:{r:scores(rows,name,p,region=r) for r in ('all','missing','healthy','observed')}
  for p in ('clean','P-U','P-M','dose','ordinary')} for name in names}

def d0(old,base):
 old=Path(old);base=Path(base);oldrows=[];hist={}
 for f in sorted((old/'evaluation/average_16000').glob('*/counts.json')):
  c=read(f)['case'];r=original_counts(old,c);oldrows.append(r)
  if c['panel'] not in ('clean','P-U'):continue
  for scope in ('full','noboundary'):
   for region in ('all','missing','healthy','observed'):
    m=r['matrices'][scope];a=np.asarray(m['rgb'][region],np.int64);b=np.asarray(m['dsm'][region],np.int64)
    o=np.asarray(m['oracle'][region],np.int64);n=a.sum(1);ra=a.diagonal();da=b.diagonal();oa=o.diagonal()
    joint=np.stack((ra+da-oa,oa-da,oa-ra,n-oa),1)
    if (joint<0).any() or not np.array_equal(joint.sum(1),n):raise RuntimeError('old correctness inclusion-exclusion failed')
    k='/'.join((c['tile'],c['panel'],c['direction'],c['family'],scope,region))
    hist[k]=hist.get(k,np.zeros((6,4),np.int64))+joint
 out={}
 for k,a in hist.items():
  phi=[]
  for values in a:
   both,r,d,neither=map(int,values)
   den=(both+r)*(d+neither)*(both+d)*(r+neither)
   phi.append(None if den==0 else float((float(both)*neither-float(r)*d)/np.sqrt(float(den))))
  out[k]=dict(columns=['both_correct','RGB_unique','DSM_unique','both_wrong'],raw=a.tolist(),phi_by_class=phi)
 # Match original direction-level best fixed expert and static B2.
 b2=[original_counts(old,r['case'],'B2') for r in oldrows]
 decomposition={}
 for dr in ('rgb','dsm'):
  best=max(scores(oldrows,'rgb',direction=dr),scores(oldrows,'dsm',direction=dr))
  oracle=scores(oldrows,'oracle',direction=dr);static=scores(b2,'candidate',direction=dr)
  decomposition[dr]=dict(oracle_minus_best_fixed=oracle-best,oracle_minus_B2=oracle-static,
   B2_minus_best_fixed=static-best)
 write(base/'analysis/D0.json',dict(binding=binding(base),old_binding=OLD_BINDING,decomposition=decomposition,
  correctness=out,source_cases=len(oldrows),optimizer_updates=0,
  caveat='Empirical aligned-error dependence across repeated masks. Full R/D/F flow requires new inference.',
  observed_at=now()))
 return [r for r in oldrows if r['case']['panel']=='P-U']

def null_case(row):
 from phase24_numeric import null_cm
 c=row['case'];m=row['matrices']['noboundary']
 return c,null_cm(m['rgb']['all'],m['dsm']['all'],key(20261014,'alignment',cid(c)))

def summarize_null(results,base):
 pooled={}
 for c,cm in results:
  k=groupkey(c);pooled[k]=pooled.get(k,np.zeros_like(cm))+cm
 vectors={'rgb':[],'dsm':[]}
 for k,cm in pooled.items():
  den=cm.sum(1)+cm.sum(2)-np.diagonal(cm,axis1=1,axis2=2)
  tp=np.diagonal(cm,axis1=1,axis2=2)
  score=np.divide(tp[:,:5],den[:,:5],out=np.zeros((len(cm),5),float),where=den[:,:5]>0)
  valid=(den[:,:5]>0).sum(1);v=score.sum(1)/valid*100;vectors[k[1]].append(v)
 out={}
 original=read(Path(base)/'analysis/D0.json')['decomposition']
 for dr,values in vectors.items():
  v=np.mean(values,axis=0)
  # bestFixed = original oracle - H; obtain its exact source score separately.
  fixed=read(Path(base)/'analysis/null_reference.json')[dr]
  out[dr]=dict(null_oracle_minus_best_fixed_mean=float(np.mean(v-fixed)),
   interval95=np.quantile(v-fixed,[.025,.975]).tolist(),observed_gap=original[dr]['oracle_minus_best_fixed'])
 write(Path(base)/'analysis/alignment_null.json',dict(binding=binding(base),replicates=1000,result=out,
  strata='tile x condition x ground-truth class; full predicted-class margins',
  spatial_dependence_preserved=False,p_values_reported=False,route_gate=False,
  interpretation='descriptive cross-pixel alignment reference; not a correction for unrecoverable stochastic oracle inflation'))

def bridge(old,row):
 for name,original in [('average','average'),('B0','B0'),('B2','B2')]:
  ref=original_counts(old,row['case'],original)
  for scope in ('full','noboundary'):
   for region in ('all','missing','healthy','observed'):
    for current,source in [(name,'candidate'),('rgb','rgb'),('dsm','dsm')]:
     if row['matrices'][scope][current][region]!=ref['matrices'][scope][source][region]:
      raise RuntimeError('original CM mismatch: '+cid(row['case'])+'/'+name+'/'+scope+'/'+region+'/'+current)
 return True
