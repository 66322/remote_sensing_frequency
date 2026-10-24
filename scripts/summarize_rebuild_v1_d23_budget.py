"""Reduce bounded D23 budget records; never grants the formal runtime lock."""
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re

ARMS={'T0','TS','TF','TSF','TCAP','TSF_CE','TSF_shuffleS','TSF_shuffleF'}
CONDITIONS={'clean','rgb_down2','rgb_down4','rgb_blur5','rgb_local_down4_q1','aux_down4',
 'aux_noise_std010','aux_zero','aux_local_zero_q1','rgb_contrast060','aux_shift8',
 'aux_local_zero_stripe_eighth','aux_noise_std020','aux_shift16'}
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def percentile(values, quantile):
    values=sorted(values)
    if not values or any(not math.isfinite(v) or v<=0 for v in values):
        raise ValueError('invalid timing')
    return values[max(0,math.ceil(len(values)*quantile)-1)]
def analyse(rows):
    if len(rows)!=2:raise ValueError('two GPU records required')
    common=[]
    for gpu,row in enumerate(rows):
        if row['status']!='ENGINE_BUDGET_COMPLETE' or row['mode']!='budget':
            raise ValueError('not completed budget measurement')
        if row['formal_training_started'] or row['formal_fit_statistics']:
            raise ValueError('unexpected formal run')
        sig=row['signature']
        if sig['gpu']!=gpu or sig['test6_loaded'] or sig['development_labels_loaded']:
            raise ValueError('phase/device mismatch')
        common.append({k:v for k,v in sig.items() if k not in ('gpu','uuid')})
        if set(row['train'])!=ARMS or set(row['evaluation'])!=CONDITIONS:
            raise ValueError('coverage mismatch')
        if len(set(row['train_fit_ids']))!=12 or set(row['cache_measurement'])!=set(row['train_fit_ids']):
            raise ValueError('12-tile cache incomplete')
        if row['budget_statistics_samples']!=256:
            raise ValueError('TCAP sample coverage incomplete')
        for arm,value in row['train'].items():
            if value['train_steps']!=16 or not value['checkpoint_reload_equal']:
                raise ValueError('short training incomplete')
            percentile(value['step_seconds'][2:],.95)
        percentile([row['cache_seconds'],row['statistics_seconds']],1)
        for condition,value in row['evaluation'].items():
            percentile([value['seconds']],1)
            if value['shape']!=[6000,6000] or set(value['results'])!={'R0','M0_safe','confidence','entropy','logit_average','probability_average','TSF'}:
                raise ValueError('full image/comparator coverage mismatch')
            if not all(v['missing_logits_equal'] for v in value['results'].values()):
                raise ValueError('missing fallback failed')
    if common[0]!=common[1]:raise ValueError('cross-device source/backend mismatch')
    if rows[0]['signature']['uuid']==rows[1]['signature']['uuid']:
        raise ValueError('GPU UUID duplicated')
    for condition in CONDITIONS:
        for name in ('R0','M0_safe','confidence','entropy','logit_average','probability_average'):
            if rows[0]['evaluation'][condition]['results'][name]['prediction_sha256']!=rows[1]['evaluation'][condition]['results'][name]['prediction_sha256']:
                raise ValueError('cross-device fixed baseline predictions differ')
    # Worst device and arm, CPU/data loading included; NB counting cost is unmeasured.
    step=max(percentile(v['step_seconds'][2:],.95) for r in rows for v in r['train'].values())
    evaluation=max(sum(v['seconds'] for v in r['evaluation'].values()) for r in rows)
    setup=max(r['cache_seconds']+r['statistics_seconds'] for r in rows)
    wall=math.ceil(300+1.5*(setup+4000*step+2*2*evaluation))
    return dict(status='BUDGET_MEASURED_REVIEW_REQUIRED',worst_step_p95_seconds=step,
      train_4000_seconds=4000*step,two_tile_14_condition_eval_allowance_seconds=4*evaluation,
      estimated_job_wall_seconds=wall,estimated_four_jobs_per_gpu_seconds=4*wall,
      safety_multiplier=1.5,nb_and_validation_io_measured=False,
      evaluation_basis='14 conditions on 6000x6000 train tile, 7 models; two tiles and 2x evaluation allowance',
      formal_runtime_admitted=False,test6_loaded=False,formal_training_started=False)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True)
    base=ap.parse_args().directory.resolve();base.relative_to(Path('/home/jovyan/zzx').resolve())
    rows=[json.loads((base/f'gpu{i}/summary.json').read_text()) for i in (0,1)]
    result=analyse(rows)
    log=(base/'cpu_checks.log').read_text()
    tests=re.search(r'Ran\s+(\d+)\s+tests',log)
    if not tests or int(tests.group(1))<22 or not re.search(r'^OK\s*$',log,re.M):
        raise ValueError('server CPU checks incomplete')
    result.update(collected_at=datetime.now().astimezone().isoformat(),server_directory=str(base),
      cpu_checks=dict(sha256=sha(base/'cpu_checks.log'),pass_=True,reported_tests=int(tests.group(1))),gpus={})
    result['cpu_checks']['pass']=result['cpu_checks'].pop('pass_')
    for gpu,row in enumerate(rows):
        result['gpus'][str(gpu)]=dict(signature=row['signature'],
          summary_sha256=sha(base/f'gpu{gpu}/summary.json'),
          preflight_sha256=sha(base/f'gpu{gpu}/preflight.json'),
          observed_at=row['observed_at'],cache_seconds=row['cache_seconds'],
          statistics_seconds=row['statistics_seconds'],elapsed_seconds=row['elapsed_seconds'],
          rss_peak_bytes=row['rss_peak_bytes'],
          gpu_peak_allocated_bytes=max(v['gpu_peak_allocated_bytes'] for v in row['train'].values()),
          gpu_peak_reserved_bytes=max(v['gpu_peak_reserved_bytes'] for v in row['train'].values()))
    result['archive']=dict(path=None,uploaded=False,meaning='explicit JSON/log evidence only; no tar generated')
    path=base/('compact_review_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.json')
    with path.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    print('D23_BUDGET_ESTIMATED_JOB_SECONDS='+str(result['estimated_job_wall_seconds']))
    print('D23_COMPACT_REVIEW='+str(path))
if __name__=='__main__':main()
