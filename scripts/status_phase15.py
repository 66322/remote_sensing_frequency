"""Read-only last observation plus owned-process checks; no enqueue or retry."""
import argparse
from pathlib import Path
from collections import Counter
from phase15_common import *


def main(base):
    from d30_common import live_owned
    s=read(base/'queue_status.json')
    pid=s.get('controller_pid',read(base/'launch.json').get('controller_pid',-1) if (base/'launch.json').exists() else -1)
    print('QUERY_OBSERVED='+now(),'LAST_OBSERVED='+s['observed_at'],'QUEUE='+s['status'],'CONTROLLER_LIVE='+str(live_owned(pid,base)))
    print('COUNTS',dict(Counter(x['status'] for x in s['jobs'].values())))
    for n,r in s['jobs'].items():
        if r['status']=='RUNNING':
            f=base/'jobs'/n/'progress.json'
            print(n,'GPU='+str(r['gpu']),'LIVE='+str(live_owned(r['pid'],base)),read(f) if f.exists() else {})
    for g in (0,1):
        f=base/'smoke'/('gpu'+str(g))/'progress.json'
        if f.exists() and not (f.parent/'complete.json').exists():print('SMOKE',g,read(f))
    if s.get('error'):print('ERROR',s['error'])
    print('Zero training; no failed-recipe retry, extra seed, new method dispatch, or 24h deadline.')


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',type=Path,required=True)
    main(a.parse_args().directory.resolve())
