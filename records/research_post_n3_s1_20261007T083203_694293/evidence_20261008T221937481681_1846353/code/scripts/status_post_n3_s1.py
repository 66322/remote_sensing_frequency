"""Read-only N3/S1 queue status with worker progress and source timestamps."""
import argparse
from pathlib import Path
from post_n3_s1_common import read,now
from d30_common import live_owned
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args();base=a.directory.resolve();s=read(base/'queue_status.json')
    print('QUERY_OBSERVED='+now(),'LAST_OBSERVED='+s['observed_at'],'QUEUE='+s['status'],'PID='+str(s.get('controller_pid',-1)),'LIVE='+str(live_owned(s.get('controller_pid',-1),base)))
    for j,r in s['jobs'].items():
        f=base/'jobs'/j/'progress.json';v=read(f) if f.exists() else {}
        print(j,'GPU'+str(r['gpu']),r['status'],'PID='+str(r.get('pid',-1)),'LIVE='+str(live_owned(r.get('pid',-1),base)),v)
    print('Nine registered cells only; no automatic retries, new seeds or further families.')
if __name__=='__main__':main()
