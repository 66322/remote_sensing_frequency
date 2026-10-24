"""Rebuild summaries from immutable full-tile integer counts before retirement/upload."""
from pathlib import Path
import copy,json
import numpy as np
from phase24_common import *
from phase24_analysis import gate,trajectory_summary,paired_summary
def validate_row(row,expected_binding):
 if row['binding']!=expected_binding:raise RuntimeError('result binding changed')
 c=row['case']
 if c['tile'] not in VAL:raise RuntimeError('forbidden result tile')
 for scope,systems in row['matrices'].items():
  if scope not in ('full','noboundary'):raise RuntimeError('unexpected scope')
  for n,regions in systems.items():
   for region,cm in regions.items():
    if len(cm)!=6 or any(len(x)!=6 for x in cm) or any(type(v) is not int or v<0 or v>np.iinfo(np.int64).max for x in cm for v in x):
     raise RuntimeError('invalid int64 confusion matrix')
    if sum(v for x in cm for v in x)>36000000:raise RuntimeError('counts exceed one full tile')
   a=np.asarray(regions['all'],np.int64);m=np.asarray(regions['missing'],np.int64);o=np.asarray(regions['observed'],np.int64)
   h=np.asarray(regions['healthy'],np.int64)
   if not np.array_equal(a,m+o) or (h>o).any():raise RuntimeError('ROI partition differs')
  counts=[np.asarray(v['all'],np.int64).sum(1).tolist() for v in systems.values()]
  if any(v!=counts[0] for v in counts):raise RuntimeError('system ground-truth totals differ')
 if row['fallback_errors']!=0:raise RuntimeError('fallback errors')
 return True
def verify_results(base,require_complete=False):
 base=Path(base);p=verify(base);b=binding(base)
 if require_complete and read(base/'queue_status.json')['status']!='PHASE24_COMPLETE_AWAITING_REVIEW':raise RuntimeError('queue not complete')
 index=read(base/'evidence_index.json');summary=read(base/'summary.json')
 if index['binding']!=b or summary['binding']!=b or index['summary_sha256']!=sha(base/'summary.json'):raise RuntimeError('summary/index binding changed')
 groups={}
 for row in index['records']:
  f=scoped(base/row['path'],base/'results')
  if sha(f)!=row['sha256']:raise RuntimeError('count evidence changed')
  z=read(f);validate_row(z,b)
  if z['stage'] in ('D2','D3','E','E_T3') and z.get('lock') is None:raise RuntimeError('missing source-only parameter lock')
  if z.get('lock') is not None:
   lock=z['lock'];fit=scoped(base/lock['path'],base/'fits')
   if sha(fit)!=lock['sha256'] or lock['target']!=z['case']['tile'] or lock['source']==lock['target']:raise RuntimeError('source/target lock differs')
   params=read(fit)
   if params['target_used_for_fitting'] or params['binding']!=b or params['source']!=lock['source']:raise RuntimeError('source fit differs')
  groups.setdefault(z['stage'],{})[cid(z['case'])]=z
 end=list(groups['E'].values());expected={cid(c) for c in panel(p['fixed_conditions'])}
 if {cid(r['case']) for r in end}!=expected:raise RuntimeError('endpoint panel incomplete')
 if 'T3' in summary['trained_heads']:
  t3=groups['E_T3']
  if set(t3)!=expected:raise RuntimeError('T3 panel incomplete')
  for r in end:
   other=t3[cid(r['case'])]
   for scope in ('full','noboundary'):
    for name in ('T3','T3_4000'):r['matrices'][scope][name]=other['matrices'][scope][name]
 rebuilt=trajectory_summary(end)
 if rebuilt!=summary['results']:raise RuntimeError('summary does not reproduce from integer counts')
 dp=list(groups['D2'].values())+list(groups['D3'].values())
 if {cid(r['case']) for r in dp}!=expected:raise RuntimeError('diagnostic panel incomplete')
 for n in ('calibrated','probe'):
  if gate(dp,n)!=summary['deployment_gate'][n]:raise RuntimeError('deployment gate does not reproduce')
 arms=summary['trained_heads']
 if arms not in (['T0'],['T0','T1','T2'],['T0','T1','T2','T3']):raise RuntimeError('unregistered training dispatch')
 if summary['total_optimizer_updates']!=8000*len(arms) or summary['old_expert_optimizer_updates']!=0:raise RuntimeError('training budget differs')
 for n in arms:
  if paired_summary(end,n,'reference')!=summary['paired_mask_intervals'][n]:raise RuntimeError('paired interval differs')
 if 'T1' in arms and gate(end,'T1')!=summary['signal_gate']:raise RuntimeError('head gate differs')
 write(base/'result_verification.json',dict(binding=b,index_sha256=sha(base/'evidence_index.json'),
  summary_sha256=sha(base/'summary.json'),exact_integer_summary_rebuild=True,validated_records=sum(map(len,groups.values())),
  optimizer_updates=summary['total_optimizer_updates'],observed_at=now()))
 return summary
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True)
 verify_results(p.parse_args().directory,True);print('PHASE24_RESULT_VERIFIED')
