"""Read-only observation; no dispatch or retry."""
import argparse
from pathlib import Path
from post_n5_cross_common import read,now
from d30_common import live_owned
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();base=a.directory.resolve()
    s=read(base/'queue_status.json')
    print('QUERY_OBSERVED='+now(),'LAST_OBSERVED='+s['observed_at'],'QUEUE='+s['status'],'PID='+str(s.get('controller_pid',-1)),'LIVE='+str(live_owned(s.get('controller_pid',-1),base)))
    print('CPU='+s['CPU'],'NEW_OPTIMIZER_UPDATES=0')
    if (base/'cpu_progress.json').exists():print('CPU_PROGRESS',read(base/'cpu_progress.json'))
    for j,row in s['jobs'].items():
        progress=base/'jobs'/j/'progress.json';v=read(progress) if progress.exists() else {}
        print(j,'GPU'+str(row['gpu']),row['status'],'PID='+str(row.get('pid',-1)),'LIVE='+str(live_owned(row.get('pid',-1),base)),v)
    if (base/'cross_screen.json').exists():
        screen=read(base/'cross_screen.json');print('PROBLEM_SCREENS',screen['E4']);print('NEXT_FAMILIES',screen['recommended_next_families'],'TRAINING_PROTOCOL_NOT_YET_IMPLEMENTED')
    print('Read-only. Existing N5/N2/diagnostics are never restarted.')
if __name__=='__main__':main()
