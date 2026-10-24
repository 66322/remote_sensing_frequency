"""Read state, or explicitly release/rejoin a physical GPU across queue stages."""
import argparse
from pathlib import Path
from structured_v0_common import *


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--directory', type=Path, required=True)
    a.add_argument('--action', choices=('status','release','rejoin'), default='status')
    a.add_argument('--gpu', type=int, choices=(0,1))
    args = a.parse_args()
    base = args.directory.resolve()
    base.relative_to(Path('/home/jovyan/zzx'))
    if not base.name.startswith(PREFIX):
        raise ValueError('unexpected directory')
    p = validate(base)
    if args.action != 'status':
        if args.gpu is None:
            raise ValueError('gpu required')
        request = dict(blocked=args.action=='release', requested_action=args.action, requested_at=now())
        # Explicit user controls apply to the active original queue as well.
        pred = Path(p['predecessor'])
        old = read(pred/'queue_status.json')
        if old['status'] != 'PAIRED_COMPLETE_AWAITING_REVIEW':
            write(pred/'control'/('gpu_%d.json'%args.gpu), request)
        write(base/'control'/('gpu_%d.json'%args.gpu), request)
        print('GPU_REQUEST', args.gpu, args.action, 'wait for worker exit and nvidia-smi before using card')
    from d30_common import live_owned
    s = read(base/'queue_status.json')
    print('QUERY_OBSERVED='+now(), 'LAST_OBSERVED='+s['observed_at'], 'QUEUE='+s['status'],
          'CONTROLLER_LIVE='+str(live_owned(s.get('controller_pid',-1),base)))
    print('GPU_BLOCKED', {g:blocked(base,g) for g in (0,1)})
    print('PREDECESSOR', s.get('predecessor',{}))
    counts = {k:sum(r['status']==k for r in s['jobs'].values()) for k in ('COMPLETE','RUNNING','PENDING','PAUSED_USER','TECHNICAL_FAILURE')}
    print('COUNTS', counts)
    for n,r in s['jobs'].items():
        if r['status'] not in ('COMPLETE','PENDING'):
            print(n,r['status'],'GPU',r.get('gpu'),'LIVE',live_owned(r.get('pid',-1),base),r.get('progress',{}))
    if 'error' in s:
        print('ERROR',s['error'])
    print('No training, no automatic retry, no extra seeds or Phase1B/Phase2 dispatch.')


if __name__ == '__main__':
    main()
