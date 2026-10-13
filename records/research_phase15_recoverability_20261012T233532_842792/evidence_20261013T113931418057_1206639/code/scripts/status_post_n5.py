"""Read-only queue and worker observations."""
import argparse
from pathlib import Path
from post_n5_common import read
from d30_common import live_owned
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();b=a.directory
    s=read(b/'queue_status.json')
    print('LAST_OBSERVED='+s['observed_at'],'QUEUE='+s['status'],'PID='+str(s.get('controller_pid')),'LIVE='+str(live_owned(s.get('controller_pid',-1),b)))
    for j,r in s['jobs'].items():
        p=b/'jobs'/j/'progress.json';v=read(p) if p.exists() else {}
        print(j,'GPU'+str(r['gpu']),r['status'],v.get('phase',''),'step='+str(v.get('step',0))+'/8000','PID='+str(r.get('pid',-1)),'LIVE='+str(live_owned(r.get('pid',-1),b)),'progress_at='+str(v.get('observed_at','-')))
    if 'error' in s:print('ERROR',s['error'])
    print('N5 only; no automatic retry or reserved-family dispatch.')
if __name__=='__main__':main()

