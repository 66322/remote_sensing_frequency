"""Read-only queue and resource progress; never resumes or registers work."""
import argparse
from pathlib import Path
from phase2_common import *
def main(base):
    base=Path(base);s=read(base/'queue_status.json');launch=read(base/'launch.json')
    print('QUERY_OBSERVED='+now(),'LAST_OBSERVED='+s['observed_at'],'QUEUE='+s['status'],
          'CONTROLLER_LIVE='+str(live(launch['controller_pid'],base)))
    for n,v in s.get('workers',{}).items():
        print(n,v,'LIVE='+str(live(v['pid'],base)))
    for p in [base/'preparation_progress.json',*base.glob('head_cache_gpu*.json'),*base.glob('jobs/*/progress.json')]:
        print(p.relative_to(base),read(p))
    for n in ('gates_C_L.json','static_gate.json'):
        if (base/'analysis'/n).exists():print(n,read(base/'analysis'/n))
    print('No automatic recipe retry, new seed, Test6/held4/final or 24h deadline.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);main(p.parse_args().directory.resolve())
