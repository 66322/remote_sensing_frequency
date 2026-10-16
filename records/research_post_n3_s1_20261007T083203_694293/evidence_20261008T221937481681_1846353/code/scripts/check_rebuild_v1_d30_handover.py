"""Read-only live controller / predecessor lock check; no GPU query."""
import argparse
from pathlib import Path
from d30_common import read,now,live_owned,lock_free
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args()
    base=a.directory.resolve();base.relative_to(Path('/home/jovyan/zzx'))
    if not (base/'queue_status.json').exists():
        print('D30_VERDICT=INITIALIZING_OR_BOOTSTRAP_FAILURE inspect nohup.log');return
    state=read(base/'queue_status.json');parent=Path(state['predecessor_directory']);previous=read(parent/'queue_status.json')
    alive=live_owned(state.get('controller_pid',-1),base)
    workers=[j for j,r in state['jobs'].items() if live_owned(r.get('pid',-1),base)]
    waiting=state.get('status') in ('WAITING_D28','WAITING_D28_RELEASE')
    verdict='ACTIVE_QUEUED_WAITING_PREDECESSOR' if alive and waiting and not workers else 'ACTIVE_RUNNING' if alive and state.get('status')=='RUNNING' else 'ACTIVE_INITIALIZING' if alive and state.get('status') in ('VERIFYING_CPU','READY') else 'COMPLETE' if state.get('status')=='COMPLETE' else 'NEEDS_ATTENTION'
    print('CHECKED_AT='+now(),'D30_STATUS='+state['status'],'PID='+str(state.get('controller_pid')),'LIVE='+str(alive))
    print('D30_LAST_OBSERVED='+str(state.get('observed_at')),'LIVE_WORKERS='+str(workers))
    print('D28_STATUS='+str(previous.get('status')),'D28_CONTROLLER_LOCK_FREE='+str(lock_free(parent)))
    print('D30_VERDICT='+verdict)
if __name__=='__main__':main()
