"""Read-only persisted queue progress; no probing or inference."""
import argparse
from pathlib import Path
from d30_common import read,TRAIN_IDS
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();base=a.directory.resolve()
    state=read(base/'queue_status.json')
    print('LAST_OBSERVED='+str(state.get('observed_at'))+' QUEUE='+str(state.get('status'))+' PHASE='+str(state.get('phase','waiting')))
    print('PREDECESSOR='+str(state.get('predecessor_status'))+' OBSERVED='+str(state.get('predecessor_observed_at')))
    for j,row in state['jobs'].items():
        progress=row.get('progress',{})
        print(j,'GPU'+str(row['gpu']),row['status'],progress.get('phase',''),
              'step='+str(progress.get('step','-'))+'/8000' if j in TRAIN_IDS else str(progress.get('done',0))+'/24',
              'at='+str(progress.get('observed_at','-')))
    times=[r['elapsed_seconds'] for j,r in state['jobs'].items() if j in TRAIN_IDS and r['status']=='COMPLETE']
    if times:
        typical=sum(times)/len(times);lanes=[]
        for gpu in (0,1):
            remaining=0
            for j in TRAIN_IDS:
                row=state['jobs'][j]
                if row['gpu']!=gpu or row['status'] not in ('PENDING','RUNNING'):continue
                remaining+=max(0,typical-row.get('elapsed_seconds',0)) if row['status']=='RUNNING' else typical
            lanes.append(remaining)
        print('ROUGH_TRAIN_REMAINING_HOURS=%.2f'%(max(lanes)/3600))
    else:print('ETA: design estimate 3.5-4.5h after D28 release; no extra probe')
    print('Persisted observations; use handover checker and logs to verify liveness. ETA excludes predecessor waiting.')
if __name__=='__main__':main()

