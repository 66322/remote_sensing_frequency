"""Release/rejoin a physical GPU without terminating the controller or the other card."""
import argparse
from pathlib import Path
from post_t_paired_v2_common import read, write, now, within, PREFIX
from d30_common import live_owned


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--directory', type=Path, required=True)
    ap.add_argument('--action', choices=('status', 'release', 'rejoin'), default='status')
    ap.add_argument('--gpu', type=int, choices=(0, 1))
    a = ap.parse_args()
    base = within(a.directory, '/home/jovyan/zzx')
    if not base.name.startswith(PREFIX):
        raise ValueError('wrong experiment directory')
    state = read(base / 'queue_status.json')
    if a.action != 'status':
        if a.gpu is None:
            raise ValueError('--gpu required')
        write(base / 'control' / ('gpu_%d.json' % a.gpu),
              dict(blocked=a.action == 'release', requested_at=now(), requested_action=a.action))
        print('GPU_CONTROL', a.gpu, a.action,
              'save-and-exit then automatically queue continuation on the other enabled GPU' if a.action == 'release' else 'available for future dispatch', flush=True)
    print('QUERY_OBSERVED=' + now(), 'LAST_OBSERVED=' + state['observed_at'],
          'QUEUE=' + state['status'], 'CONTROLLER_LIVE=' + str(live_owned(state.get('controller_pid', -1), base)))
    for name, row in state['jobs'].items():
        alive = live_owned(row.get('pid', -1), base)
        print(name, row['status'], 'GPU=' + str(row.get('gpu')), 'LIVE=' + str(alive), row.get('progress', {}))
    if a.action == 'release':
        print('RELEASE_REQUESTED_NOT_YET_CONFIRMED: wait for that worker LIVE=False and verify nvidia-smi before using the card.')
    print('No recipe retry, no new seed, no new queue, no24h deadline.')


if __name__ == '__main__':
    main()
