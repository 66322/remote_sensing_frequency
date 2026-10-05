import json,gzip,base64,hashlib,math,gc
from pathlib import Path
import argparse
parser=argparse.ArgumentParser(description='Offline review of downloaded C/N light payload directories; no training/inference')
parser.add_argument('--directory',type=Path,required=True)
P=parser.parse_args().directory.resolve()
report={'schema_version':'1.0','payload_sha_checks':0,'source_sha_checks':0,'complete_bindings':0,'summaries':0,'cm_pairs':0,'joint_pairs':0,'candidate_joint_marginals':0,'metric_records':0,'max_metric_error':0.0,'records':{},'scope':'C0-C5 and N1-0..3 selected/fixed summaries; no checkpoint or prediction bytes loaded'}
manifests={g:json.loads((P/g/'upload_manifest.json').read_text(encoding='utf-8')) for g in ('C','N')}
def digest(raw):return hashlib.sha256(raw).hexdigest()
def rd(g,name):
 raw=(P/g/name).read_bytes()
 m=next((x for x in manifests[g]['files'] if x['path']==name),None)
 if m:
  if digest(raw)!=m['sha256'] and raw.endswith(b'\n') and digest(raw[:-1])==m['sha256']:raw=raw[:-1]
  assert len(raw)==m['bytes'] and digest(raw)==m['sha256'],('upload SHA',g,name,len(raw),m['bytes'])
  report['payload_sha_checks']+=1
 v=json.loads(raw)
 if isinstance(v,dict) and 'payload_base64' in v and v.get('record_encoding')=='gzip-base64-exact-v1':
  decoded=gzip.decompress(base64.b64decode(v['payload_base64'],validate=True))
  assert len(decoded)==v['original_bytes'] and digest(decoded)==v['original_sha256']
  raw=decoded;v=json.loads(raw)
 src=next((x for x in manifests[g].get('source_files',[]) if x['path']==name),None)
 if src:
  assert len(raw)==src['original_bytes'] and digest(raw)==src['original_sha256'],('source SHA',g,name)
  report['source_sha_checks']+=1
 return v,raw
def approx(a,b):
 if a is None or b is None: assert a==b;return
 e=abs(a-b);report['max_metric_error']=max(e,report['max_metric_error']);assert e<1e-12,(a,b,e)
def valid_cm(r):
 cm=r['cm'];assert len(cm)==6 and all(len(x)==6 for x in cm)
 assert all(type(v)==int and 0<=v<2**63 for row in cm for v in row)
 tp=[cm[i][i] for i in range(6)];support=[sum(row) for row in cm];pred=[sum(cm[i][j] for i in range(6)) for j in range(6)]
 fp=[pred[i]-tp[i] for i in range(6)];fn=[support[i]-tp[i] for i in range(6)]
 for k,a in [('support',support),('TP',tp),('FP',fp),('FN',fn)]:assert r[k]==a,(k,r[k],a)
 assert r['valid']==sum(support)
 iou=[tp[i]/(tp[i]+fp[i]+fn[i]) if tp[i]+fp[i]+fn[i] else None for i in range(6)]
 for a,b in zip(iou,r['IoU']):approx(a,b)
 for k,n in [('mIoU_fg5',5),('mIoU_6',6)]:
  vs=[x for x in iou[:n] if x is not None];approx(sum(vs)/len(vs) if vs else None,r[k])
 report['metric_records']+=1
 return cm
def jdecode(x):
 assert x['shape']==[6]*4 and x['dtype']=='int64' and x['format']=='sparse_flat_index_count'
 a=[0]*1296;seen=set()
 for idx,n in x['nonzero']:
  assert type(idx)==int and 0<=idx<1296 and idx not in seen and type(n)==int and 0<n<2**63
  a[idx]=n;seen.add(idx)
 return a
def metric(s,c,name='candidate'):return 100*s['pooled'][c]['noboundary']['metrics'][name]['valid']['mIoU_fg5']
def average(s,cs,name='candidate'):return sum(metric(s,c,name) for c in cs)/len(cs)
def scores(s,plan):
 row={n:average(s,cs) for n,cs in plan['evaluation']['families'].items()};row['S_available']=sum(row.values())/len(row);return row
def compact(s,plan,complete):
 return {'scores_pp':scores(s,plan),'selected_step':complete['selected']['step'],'clean':metric(s,'clean'),'dsm_missing':metric(s,'dsm_missing'),'rgb_missing':metric(s,'rgb_missing'),'tiles':{t:{c:100*r['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5'] for c,rs in s['tiles'].items() for tt,r in rs.items() if tt==t} for t in plan['data']['validation']},'conditions':{c:metric(s,c) for c in s['pooled']},'missing_mean_pp':{a:average(s,cs) for a,cs in plan['design']['C_conditions'].items()},'anchor_missing_mean_pp':{a:average(s,cs,'fixed_'+a) for a,cs in plan['design']['C_conditions'].items()}}
for g in ('C','N'):
 plan,planbytes=rd(g,'plan.json');report[g]={'plan_sha256':digest(planbytes),'rows':{}}
 ids=[f'C{i}' for i in range(6)] if g=='C' else [f'N1-{i}' for i in range(4)]
 screen,_=rd(g,'portfolio_screen.json' if g=='C' else 'n1_screen.json')
 queue,_=rd(g,'queue_status.json');report[g]['queue_metadata']={k:v for k,v in queue.items() if k not in ['jobs','gpu_uuids']}
 for job in ids:
  complete,cr=rd(g,f'jobs/{job}/complete.json')
  assert complete['global_step']==8000 and complete['signature']['plan_sha256']==digest(planbytes) and complete['signature']['execution_commit']==plan['execution_commit']
  assert not complete['test6_loaded']
  report['complete_bindings']+=1;rows={}
  for tag in ('evaluation','fixed8000'):
   s,sraw=rd(g,f'jobs/{job}/{tag}/summary.json')
   assert digest(sraw)==complete[tag+'_summary_sha256']
   assert s['binding']['training']==complete['signature'] and not s['test6_loaded'] and not s['independent_final_loaded']
   assert s['confusion_matrix_dtype']=='int64'
   for c,tiles in s['tiles'].items():
    assert set(tiles)==set(plan['data']['validation'])
    for scope in ('full','noboundary'):
     pooled=s['pooled'][c][scope]
     for name,regions in pooled['metrics'].items():
      for region,rr in regions.items():
       p=valid_cm(rr);cs=[valid_cm(r['scopes'][scope]['metrics'][name][region]) for r in tiles.values()]
       assert p==[[sum(cm[i][j] for cm in cs) for j in range(6)] for i in range(6)]
       report['cm_pairs']+=1
     for region,pr in pooled['joint'].items():
      jp=jdecode(pr);js=[jdecode(r['scopes'][scope]['joint'][region]) for r in tiles.values()]
      assert jp==[sum(x[i] for x in js) for i in range(1296)]
      report['joint_pairs']+=1
      if region in pooled['metrics']['candidate']:
       cm=[[0]*6 for _ in range(6)]
       for idx,n in enumerate(jp):cm[idx//216][idx%6]+=n
       assert cm==pooled['metrics']['candidate'][region]['cm']
       report['candidate_joint_marginals']+=1
   rows[tag]=compact(s,plan,complete);report['summaries']+=1
   if g=='C':
    source=screen['jobs'][job]['selected' if tag=='evaluation' else 'fixed8000']
    for k,v in rows[tag]['scores_pp'].items():approx(v,source['scores_pp'][k])
    for k,v in rows[tag]['missing_mean_pp'].items():approx(v,source['missing_mean_pp'][k])
   del s,sraw;gc.collect()
  report[g]['rows'][job]=rows
  print('AUDITED',g,job,flush=True)
 if g=='C':
  checks={};deltas={}
  for a,cs in plan['design']['C_conditions'].items():
   ca=report[g]['rows']['C2']['evaluation'];fx=report[g]['rows']['C2']['fixed8000']
   deltas[a]={b:ca['missing_mean_pp'][a]-report[g]['rows'][b]['evaluation']['missing_mean_pp'][a] for b in ['C0','C1','C3']}
   for b,d in deltas[a].items():checks[a+'_vs_'+b]=d>=.3-1e-9
   checks[a+'_anchor_floor']=ca['missing_mean_pp'][a]-ca['anchor_missing_mean_pp'][a]>=-.1-1e-9
   checks[a+'_worst_tile']=min(ca['tiles'][t][c]-report[g]['rows']['C0']['evaluation']['tiles'][t][c] for t in plan['data']['validation'] for c in cs)>=-.2-1e-9
   checks[a+'_fixed_same_sign']=fx['missing_mean_pp'][a]>report[g]['rows']['C0']['fixed8000']['missing_mean_pp'][a]
  assert checks==screen['screens']['C2']['checks']
  for a in deltas:
   for b in deltas[a]:approx(deltas[a][b],screen['screens']['C2']['deltas_pp'][a][b])
  report[g]['screen']={'checks':checks,'passed':all(checks.values()),'deltas_pp':deltas}
 else:
  checks={};deltas={};ss={j:r['evaluation']['scores_pp']['S_available'] for j,r in report[g]['rows'].items()}
  ca=report[g]['rows']['N1-3']['evaluation'];fx=report[g]['rows']['N1-3']['fixed8000']
  for b in ['N1-1','N1-2']:
   ref=report[g]['rows'][b]['evaluation'];deltas[b]=ss['N1-3']-ss[b]
   checks['S_vs_'+b]=deltas[b]>=.3-1e-9
   checks['fixed_sign_vs_'+b]=fx['scores_pp']['S_available']>report[g]['rows'][b]['fixed8000']['scores_pp']['S_available']
   for c in ['clean','dsm_missing','rgb_missing']:checks[c+'_floor_vs_'+b]=ca[c]-ref[c]>=-.1-1e-9
   checks['worst_vs_'+b]=min(ca['tiles'][t][c]-ref['tiles'][t][c] for t in plan['data']['validation'] for c in plan['evaluation']['primary'])>=-.2-1e-9
   checks['both_tiles_positive_vs_'+b]=all(sum(sum(ca['tiles'][t][c]-ref['tiles'][t][c] for c in cs)/len(cs) for cs in plan['evaluation']['families'].values())/4>0 for t in plan['data']['validation'])
  assert checks==screen['checks'];assert all(checks.values())==screen['passed']
  for b,d in deltas.items():approx(d,screen['deltas_pp'][b])
  for j,d in ss.items():approx(d,screen['scores_pp'][j])
  report[g]['screen']={k:v for k,v in screen.items() if k!='harm_and_retention'}
  for j,rr in report[g]['rows'].items():
   r=rr['evaluation'];print('N1_RESULT',j,r['scores_pp'],{c:r[c] for c in ['clean','dsm_missing','rgb_missing']},flush=True)
report['passed']=True
(P/'audit_result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('AUDIT_PASS',json.dumps({k:v for k,v in report.items() if k not in ['C','N','records']}),flush=True)


