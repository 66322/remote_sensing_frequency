"""Read persisted progress and PID liveness; never launch inference/probes."""
import argparse,json,time,sys
from pathlib import Path
from datetime import datetime,timedelta
overlay_base=Path(__file__).resolve().parent.parent
if (overlay_base/'code/scripts').is_dir():sys.path[:0]=[str(overlay_base/'code/scripts'),str(overlay_base/'code')]
from post_d30_common import PHASES,read
from d30_common import live_owned,lock_free
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();base=a.directory.resolve();base.relative_to(Path('/home/jovyan/zzx'))
    state=read(base/'queue_status.json');plan=read(base/'plan.json');controller=state.get('controller_pid',-1)
    print('LAST_OBSERVED='+state['observed_at'],'QUEUE='+state['status'],'PID='+str(controller),'LIVE='+str(live_owned(controller,base)))
    complete=sum(r['status']=='COMPLETE' for j,r in state['jobs'].items() if not j.startswith('F'));print('COMPLETE=%d/18 main; F conditional'%complete)
    if state['status'].startswith('WAITING'):
        parent=Path(plan['predecessor_directory']);s=read(parent/'queue_status.json')
        print('D30_LAST_OBSERVED='+s['observed_at'],'STATUS='+s['status'],'LOCK_FREE='+str(lock_free(parent)))
    normal=[]
    for j,row in state['jobs'].items():
        p=row.get('progress',{});file=base/'jobs'/j/'progress.json'
        if file.exists():p=read(file)
        print(j,'GPU'+str(row['gpu']),row['status'],p.get('phase',''),'step=%s/8000'%p.get('step',0),'windows=%s/%s'%(p.get('windows_done','-'),p.get('windows_total','-')),'progress_at='+p.get('observed_at','-'),'PID_LIVE='+str(live_owned(row.get('pid',-1),base)))
        repair_binding=base/'jobs'/j/'evaluation_repair_binding.json'
        evaluation_only=repair_binding.exists() and read(repair_binding).get('optimizer_updates')==0
        if row['status']=='COMPLETE' and 'started_at' in row and not evaluation_only:
            normal.append((datetime.fromisoformat(row['completed_at'])-datetime.fromisoformat(row['started_at'])).total_seconds())
    if state['status']=='COMPLETE':print('REMAINING=0; QUEUE_COMPLETED_AT='+state['completed_at']);return
    if 'FAILURE' in state['status'] or state['status']=='CONTROLLER_INTERRUPTED':print('ETA_HALTED; inspect error, queue is not actively finishing');return
    if state['status'].startswith('WAITING'):print('ETA_WAITING_D30; will not estimate from stale predecessor logs');return
    if not normal:print('ETA_PENDING_FIRST_NORMAL_COMPLETED_JOB; no extra probe');return
    duration=sum(normal)/len(normal);hours=0.
    for phase,ids in PHASES.items():
        if phase=='F':continue
        lanes=[]
        for gpu in (0,1):
            pending=[state['jobs'][j] for j in ids if state['jobs'][j]['gpu']==gpu and state['jobs'][j]['status'] in ('PENDING','RUNNING')]
            lanes.append(sum(max(0,duration-r.get('elapsed_seconds',0)) if r['status']=='RUNNING' else duration for r in pending))
        hours+=max(lanes)/3600
    end=datetime.now().astimezone()+timedelta(hours=hours)
    print('ROUGH_MAIN_REMAINING_HOURS=%.2f ROUGH_MAIN_END=%s'%(hours,end.isoformat()))
    print('New correspondence/KD workloads may differ. F adds conditional work; no wall-clock promise.')
if __name__=='__main__':main()
