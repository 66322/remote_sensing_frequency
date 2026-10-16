"""Cooperative GPU release: save and exit, never SIGSTOP holding VRAM."""
import os
from pathlib import Path
from post_t_paired_v2_common import read, write, now


class PausedForUser(Exception):
    pass


def blocked(base, gpu):
    path = Path(base) / 'control' / ('gpu_%d.json' % gpu)
    return path.exists() and read(path).get('blocked', False)


def poll_release(base, gpu):
    stop = Path(base) / 'control' / 'stop_all.json'
    if stop.exists() and read(stop).get('stop', False):
        raise PausedForUser('controller technical HOLD; preserve checkpoint')
    if blocked(base, gpu):
        raise PausedForUser('GPU%d requested by user' % gpu)


def mark_pause(base, job, gpu, step, reason):
    write(Path(base) / 'jobs' / job / 'paused.json',
          dict(status='PAUSED_USER', reason=str(reason), physical_gpu=gpu, step=step,
               process_id=os.getpid(), saved_at=now(), resume_is_continuation=True))


def validate_device(gpu):
    if gpu not in (0, 1) or os.environ.get('CUDA_VISIBLE_DEVICES') != str(gpu):
        raise RuntimeError('physical GPU binding differs')


def dependencies_ready(task, state):
    jobs = state['jobs']
    if task == 'CONTENT_PRE':
        return True
    if jobs['CONTENT_PRE']['status'] != 'COMPLETE':
        return False
    if task in ('H8', 'F8', 'R8'):
        return True
    if not all(jobs[n]['status'] == 'COMPLETE' for n in ('H8', 'F8', 'R8')):
        return False
    if task in ('R16', 'H16', 'F16'):
        return True
    return all(jobs[n]['status'] == 'COMPLETE' for n in ('R16', 'H16', 'F16'))
