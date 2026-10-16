"""Display persisted phases, steps and measured completion estimates; no GPU audit."""
import argparse
from pathlib import Path
import json
from datetime import datetime,timedelta

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);args=ap.parse_args()
    base=args.directory.resolve();base.relative_to(Path('/home/jovyan/zzx').resolve())
    state=json.loads((base/'queue_status.json').read_text())
    jobs=state['jobs'];done=sum(r['status']=='COMPLETE' for r in jobs.values())
    print('LAST_OBSERVED='+state['observed_at'],'QUEUE='+state['status'],'COMPLETE=%d/8'%done)
    plan=json.loads((base/'plan.json').read_text())
    for j in sorted(plan['jobs'],key=lambda j:j['priority']):
        row=jobs[j['id']];p=row.get('progress',{})
        path=base/'jobs'/j['id']/'progress.json'
        if path.exists():p=json.loads(path.read_text())
        print(j['id'],'GPU'+str(j['gpu']),row['status'],p.get('phase',''),
              'step=%s/4000'%p.get('step',0),
              'windows=%s/%s'%(p.get('windows_done','-'),p.get('windows_total','-')),
              'progress_at='+str(p.get('observed_at','-')))
    specs={j['id']:j for j in plan['jobs']}
    estimates=[]
    for gpu in (0,1):
        unfinished=[(j,r) for j,r in jobs.items() if r['gpu']==gpu and r['status'] in ('PENDING','RUNNING')]
        remaining,unknown,proxy=0.,0,0
        for j,row in unfinished:
            spec=specs[j]
            exact=[r['elapsed_seconds'] for k,r in jobs.items() if r['status']=='COMPLETE' and r.get('elapsed_seconds')
                   and specs[k]['route']==spec['route'] and specs[k]['last4']==spec['last4']]
            nearby=[r['elapsed_seconds'] for k,r in jobs.items() if r['status']=='COMPLETE' and r.get('elapsed_seconds')
                    and specs[k]['last4']==spec['last4']]
            observed=exact or nearby
            if not observed:unknown+=1;continue
            if not exact:proxy+=1
            estimate=sum(observed)/len(observed)
            remaining+=max(0,estimate-row.get('elapsed_seconds',0)) if row['status']=='RUNNING' else estimate
        if unknown:
            print('GPU%d ETA: %d jobs have no completed matching update range; known work roughly %.2fh'%(gpu,unknown,remaining/3600))
            continue
        estimates.append(remaining)
        print('GPU%d rough remaining hours=%.2f; %d jobs estimated via another route, using normal completed jobs'%(gpu,remaining/3600,proxy))
    if state['status'] in ('COMPLETE','COMPLETE_WITH_TECHNICAL_FAILURES'):
        print('QUEUE_COMPLETED_AT='+str(state.get('completed_at',state['observed_at'])))
    elif len(estimates)==2:
        print('ROUGH_QUEUE_END='+str(datetime.now().astimezone()+timedelta(seconds=max(estimates))))
    print('Persisted observations, not proof that a PID is live. ETA is approximate and includes train/eval only after a job completes.')
if __name__=='__main__':main()
