import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args();base=a.directory.resolve();base.relative_to(Path('/home/jovyan/zzx'));s=json.loads((base/'queue_status.json').read_text())
print('LAST_OBSERVED='+s['observed_at'],'QUEUE='+s['status'],'COMPLETE='+str(sum(r['status']=='COMPLETE' for r in s['jobs'].values()))+'/7')
print('PREDECESSOR='+str(s.get('predecessor_status')),'OBSERVED='+str(s.get('predecessor_observed_at')))
for n,r in s['jobs'].items():print(n,'GPU'+str(r.get('gpu','-')),r['status'],r.get('progress',{}))
if s.get('missing_checkpoints'):print('MISSING_CHECKPOINTS',s['missing_checkpoints'])
print('Persisted observations; inspect worker/controller logs for errors. D29 is not queued.')
