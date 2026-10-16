"""Persisted progress; estimate only from actual normal completed jobs."""
import argparse,json
from pathlib import Path
from datetime import datetime,timedelta

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);args=ap.parse_args()
    base=args.directory.resolve();base.relative_to(Path('/home/jovyan/zzx').resolve())
    state=json.loads((base/'queue_status.json').read_text());plan=json.loads((base/'plan.json').read_text())
    rows=state['jobs'];done=sum(r['status']=='COMPLETE' for r in rows.values())
    print('LAST_OBSERVED='+state['observed_at'],'QUEUE='+state['status'],'COMPLETE=%d/9'%done)
    for spec in plan['jobs']:
        row=rows[spec['id']];path=base/'jobs'/spec['id']/'progress.json'
        p=json.loads(path.read_text()) if path.exists() else row.get('progress',{})
        print(spec['id'],'GPU'+str(row.get('gpu','-')),row['status'],p.get('phase',''),'step=%s/8000'%p.get('step',0),'windows=%s/%s'%(p.get('windows_done','-'),p.get('windows_total','-')),'progress_at='+str(p.get('observed_at','-')))
    if state['status'].startswith('COMPLETE'):
        print('QUEUE_COMPLETED_AT='+str(state.get('completed_at')))
    else:
        normal=[r['elapsed_seconds'] for k,r in rows.items() if k!='J0' and r['status']=='COMPLETE' and r.get('elapsed_seconds')]
        if not normal:print('ETA_PENDING_FIRST_NORMAL_COMPLETED_JOB; no extra probe')
        else:
            mean=sum(normal)/len(normal);loads=[0.,0.]
            for row in rows.values():
                if row['status']=='RUNNING':loads[row['gpu']]=max(0,mean-row.get('elapsed_seconds',0))
            for row in rows.values():
                if row['status']=='PENDING':i=min(range(2),key=lambda j:loads[j]);loads[i]+=mean
            end=datetime.now().astimezone()+timedelta(seconds=max(loads))
            print('ROUGH_REMAINING_HOURS=%.2f ROUGH_QUEUE_END=%s'%(max(loads)/3600,end),'J0 may take longer than frozen-expert jobs')
    print('Persisted observations, not proof that a PID is live. Worker/controller logs remain authoritative for errors.')
if __name__=='__main__':main()
