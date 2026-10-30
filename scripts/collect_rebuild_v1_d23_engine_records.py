"""Read existing D23 engine records only; never import torch or launch a job."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import statistics
import tarfile

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True)
    args=ap.parse_args();base=args.directory.resolve()
    base.relative_to(Path('/home/jovyan/zzx').resolve())
    result={'kind':'EXISTING_ENGINE_RECORD_REVIEW','collected_at':datetime.now().astimezone().isoformat(),
            'server_directory':str(base),'new_inference':False,'new_training':False,'gpus':{}}
    files=[base/'cpu_checks.log'];log=files[0].read_text()
    result['cpu_checks']={'sha256':sha(files[0]),'reported_tests':22,
                         'pass':bool(re.search(r'Ran\s+22\s+tests',log) and re.search(r'^OK\s*$',log,re.M))}
    for gpu,mode in ((0,'smoke'),(1,'profile')):
        summary_path=base/('gpu%d'%gpu)/'summary.json';preflight_path=summary_path.with_name('preflight.json')
        row=json.loads(summary_path.read_text());pre=json.loads(preflight_path.read_text())
        if row['signature']!=pre or pre['gpu']!=gpu or row['mode']!=mode:
            raise RuntimeError('summary/preflight identity mismatch')
        if row['status']!='ENGINE_ADMISSION_COMPLETE' or row['formal_training_started'] is not False:
            raise RuntimeError('not completed engineering admission')
        train={}
        for arm,value in row['train'].items():
            times=value['step_seconds']
            train[arm]={k:v for k,v in value.items() if k!='step_seconds'}
            train[arm]['measured_step_median_seconds']=statistics.median(times[2:] if len(times)>2 else times)
            if value['train_steps']!=(2 if gpu==0 else 12) or value['checkpoint_reload_equal'] is not True:
                raise RuntimeError('training/reload admission incomplete')
        if set(train)!=({'T0','TS','TF','TSF','TCAP','TSF_CE','TSF_shuffleS','TSF_shuffleF'} if gpu==0 else {'TSF'}):
            raise RuntimeError('arm coverage incomplete')
        conditions={}
        expected={'clean','rgb_down2','rgb_down4','rgb_blur5','rgb_local_down4_q1','aux_down4',
                  'aux_noise_std010','aux_zero','aux_local_zero_q1','rgb_contrast060','aux_shift8',
                  'aux_local_zero_stripe_eighth','aux_noise_std020','aux_shift16'} if gpu==0 else {'clean','aux_zero','aux_local_zero_stripe_eighth'}
        if set(row['evaluation'])!=expected:raise RuntimeError('condition coverage incomplete')
        for condition,value in row['evaluation'].items():
            conditions[condition]={'seconds':value['seconds'],'shape':value['shape'],
                'models':{name:{'valid':v['full']['all']['valid'],'missing':v['full']['missing'],
                               'prediction_sha256':v['prediction_sha256'],'missing_logits_equal':v['missing_logits_equal']}
                          for name,v in value['results'].items()}}
            if not all(v['missing_logits_equal'] for v in value['results'].values()):
                raise RuntimeError('fallback failed')
        result['gpus'][str(gpu)]={'status':row['status'],'mode':mode,'observed_at':row['observed_at'],
                'summary_sha256':sha(summary_path),'preflight_sha256':sha(preflight_path),'signature':pre,
                'train':train,'conditions':conditions,
                **{k:row[k] for k in ('elapsed_seconds','rss_peak_bytes','gpu_peak_allocated_bytes',
                                     'gpu_peak_reserved_bytes','formal_training_started','formal_fit_statistics')}}
        files.extend((summary_path,preflight_path,base/('gpu%d.log'%gpu)))
    suffix=datetime.now().strftime('%Y%m%dT%H%M%S%f')
    archive=base/('light_engine_evidence_'+suffix+'.tar.gz')
    with tarfile.open(archive,'x:gz') as target:
        for path in files:target.add(path,arcname=str(path.relative_to(base)),recursive=False)
    result['archive']={'path':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),
                       'members':[str(p.relative_to(base)) for p in files],'received_off_server':False}
    output=base/('compact_review_'+suffix+'.json')
    with output.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(result,indent=2,allow_nan=False))
    print('D23_COMPACT_REVIEW='+str(output))

if __name__=='__main__':main()
