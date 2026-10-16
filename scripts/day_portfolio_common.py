"""Frozen manifest and paths for the post-D21 single-seed portfolio."""
import csv
import hashlib
import json
import os
from pathlib import Path

import d21_common as d21

ROOT = d21.ROOT
CONFIG = ROOT/'configs/rebuild_v1/post_d21_day_portfolio_20260929.json'
OUT = ROOT/'records/post_d21_day_queue_20260929'
COMPACT = ROOT/'records/post_d21_day_compact_20260929'
read, write, sha, datasets, input_paths, verify_inputs = (
    d21.read, d21.write, d21.sha, d21.datasets, d21.input_paths, d21.verify_inputs)


def config():
    cfg = read(CONFIG)
    if cfg['seed'] != 42 or cfg['effective_batch'] != 16 or cfg['test6_loaded'] is not False:
        raise RuntimeError('portfolio configuration boundary changed')
    return cfg


def jobs():
    with (ROOT/config()['job_manifest']).open(newline='', encoding='utf-8') as source:
        rows = list(csv.DictReader(source))
    if len(rows) != 50 or sum(row['budget_block'] == 'main' for row in rows) != 42:
        raise RuntimeError('expected 42 main plus 8 reserve jobs')
    for row in rows:
        row['scale'], row['seed'], row['steps'] = map(int, (row['scale'], row['seed'], row['steps']))
        if row['seed'] != 42 or row['state'] != 'planned_only':
            raise RuntimeError('manifest unexpectedly modified')
    return rows


def run_dir(job, smoke=False, profile=False, profile_micro_batch=None):
    suffix = '_smoke' if smoke else ('_profile_mb'+str(profile_micro_batch)) if profile else ''
    return ROOT/'runs/rebuild_v1'/('POST_D21_'+job['job_id']+suffix)


def eval_dir(job, smoke=False):
    return ROOT/'records/post_d21_day_evaluation_20260929'/(job['job_id']+('_smoke' if smoke else ''))


def source_snapshot():
    import subprocess
    names = subprocess.check_output(['git','ls-files','*.py','configs/rebuild_v1/*.json',
        'records/post_d21_day_plan_20260929/jobs.csv','scripts/run_rebuild_v1_day*.sh'],
        cwd=ROOT, text=True).splitlines()
    subprocess.run(['git','diff','--exit-code','HEAD','--',*names], cwd=ROOT,
                   check=True, stdout=subprocess.DEVNULL)
    needed = {'model/rebuild_v1_day_portfolio.py',
        'scripts/run_rebuild_v1_day_job.py', 'scripts/run_rebuild_v1_day_queue.py'}
    if not needed.issubset(names):
        raise RuntimeError('commit portfolio implementation before server preparation')
    return {name:sha(ROOT/name) for name in names}
