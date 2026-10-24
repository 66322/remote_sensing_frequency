"""Read-only single-GPU status; never dispatches any job."""
import argparse
from pathlib import Path
from post_s1_support_common import read,now
from d30_common import live_owned
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();base=a.directory.resolve()
    s=read(base/'queue_status.json')
    print('QUERY_OBSERVED='+now(),'LAST_OBSERVED='+s['observed_at'],'QUEUE='+s['status'],
        'PID='+str(s.get('controller_pid',-1)),'LIVE='+str(live_owned(s.get('controller_pid',-1),base)))
    print('GPU=0 ONLY CPU='+s['CPU'],'Q='+s['Q'])
    if (base/'preparation_progress.json').exists():print('CPU_PROGRESS',read(base/'preparation_progress.json'))
    for name,row in s['jobs'].items():
        p=base/'jobs'/name/'progress.json';progress=read(p) if p.exists() else {}
        print(name,'GPU0',row['status'],'PID='+str(row.get('pid',-1)),'LIVE='+str(live_owned(row.get('pid',-1),base)),progress)
    if (base/'support_screen.json').exists():
        r=read(base/'support_screen.json');print('P7_GATE',r['P7_passed'],'E_GATE',r['E_passed'],'Q',r['Q_status'])
    print('Read-only. No automatic retries, seeds, Q protocol or GPU1 work.')
if __name__=='__main__':main()

