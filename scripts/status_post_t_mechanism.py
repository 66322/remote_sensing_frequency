"""Read-only single-GPU status; never dispatches any job."""
import argparse
from pathlib import Path
from post_t_mechanism_common import read,now
from d30_common import live_owned
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();base=a.directory.resolve()
    s=read(base/'queue_status.json')
    print('QUERY_OBSERVED='+now(),'LAST_OBSERVED='+s['observed_at'],'QUEUE='+s['status'],
        'PID='+str(s.get('controller_pid',-1)),'LIVE='+str(live_owned(s.get('controller_pid',-1),base)))
    print('GPU=0 ONLY CPU='+s['CPU']);print('PREDECESSOR',s.get('predecessor',{}))
    if (base/'preparation_progress.json').exists():print('CPU_PROGRESS',read(base/'preparation_progress.json'))
    for name,row in s['jobs'].items():
        p=base/'jobs'/name/'progress.json';progress=read(p) if p.exists() else {}
        print(name,'GPU0',row['status'],'PID='+str(row.get('pid',-1)),'LIVE='+str(live_owned(row.get('pid',-1),base)),progress)
    if (base/'mechanism_screen.json').exists():
        r=read(base/'mechanism_screen.json');print('DIAGNOSTIC_SCREEN',r['recommendations']);print('NEW_OPTIMIZER_UPDATES=0')
    print('Read-only. No automatic retries, seeds, Q protocol or GPU1 work.')
if __name__=='__main__':main()

