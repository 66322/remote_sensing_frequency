"""Read-only diagnostic controller, CPU and GPU worker status."""
import argparse
from pathlib import Path
from post_n2_diag_common import read
from d30_common import live_owned
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();base=a.directory.resolve();base.relative_to(Path('/home/jovyan/zzx'))
    state=read(base/'queue_status.json');pid=state.get('controller_pid')
    if pid is None:pid=read(base/'launch.json')['controller_pid'] if (base/'launch.json').exists() else -1
    print('LAST_OBSERVED='+str(state.get('observed_at')),'QUEUE='+state['status'],'PID='+str(pid),'LIVE='+str(live_owned(pid,base)))
    print('E0='+state['E0'],'MASKS='+state['mask_preparation'],'NEW_OPTIMIZER_UPDATES=0')
    if (base/'cpu_progress.json').exists():print('CPU_PROGRESS',read(base/'cpu_progress.json'))
    for name,row in state['jobs'].items():
        print(name,'GPU'+str(row['gpu']),row['status'],'PID='+str(row.get('pid',-1)),'LIVE='+str(live_owned(row.get('pid',-1),base)))
        if (base/'jobs'/name/'progress.json').exists():print('PROGRESS',name,read(base/'jobs'/name/'progress.json'))
    print('Read-only. No training and no reserved T-rule evaluation.')
if __name__=='__main__':main()
