"""Read-only successor status; never starts or resumes work."""
import argparse,json
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args();base=a.directory.resolve();base.relative_to(Path('/home/jovyan/zzx'))
    state=json.loads((base/'queue_status.json').read_text());launch=base/'launch.json'
    pid=state.get('controller_pid',json.loads(launch.read_text()).get('controller_pid',-1) if launch.exists() else -1)
    try:live=str(base).encode() in (Path('/proc')/str(pid)/'cmdline').read_bytes()
    except FileNotFoundError:live=False
    print('LAST_OBSERVED='+str(state.get('observed_at')),'QUEUE='+state['status'],'PID='+str(pid),'LIVE='+str(live))
    for j,row in state['jobs'].items():
        progress=row.get('progress',{})
        print(j,'GPU'+str(row['gpu']),row['status'],progress.get('phase',''),'step='+str(progress.get('step',0))+'/8000')
    for j,row in state['jobs'].items():
        worker=row.get('pid',-1)
        try:worker_live=str(base).encode() in (Path('/proc')/str(worker)/'cmdline').read_bytes()
        except FileNotFoundError:worker_live=False
        print('WORKER',j,'PID='+str(worker),'LIVE='+str(worker_live))
        progress=base/'jobs'/j/'progress.json'
        if progress.exists():print('WORKER_PROGRESS',j,progress.read_text().strip())
    print('Read-only status. Pending protocol reservations are never dispatched here.')
if __name__=='__main__':main()

