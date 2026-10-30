"""Finite two-GPU seed17 D18 queue with smoke gates and resumable outputs."""
import concurrent.futures
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'records/rebuild_v1_d18_replication_queue_20260928'
ARMS = ('P0','P1','P2')
CONDITIONS = ('clean','rgb_down2','rgb_down4','rgb_blur5','rgb_local_down4_q1',
              'aux_down4','aux_noise_std010','aux_zero','aux_local_zero_q1',
              'rgb_contrast060','aux_shift8')
SOURCES = (
    'scripts/d18_replication.py','scripts/train_rebuild_v1_d18_replication.py',
    'scripts/eval_rebuild_v1_d18_replication.py','scripts/analyze_rebuild_v1_d18_replication.py',
    'scripts/archive_rebuild_v1_d18_replication.py','scripts/run_rebuild_v1_d18_replication_queue.py',
    'scripts/run_rebuild_v1_d18_replication_queue.sh',
    'configs/rebuild_v1/d18_replication_seed17_20260928.json',
    'configs/rebuild_v1/d18_d19_night_20260927.json',
    'configs/rebuild_v1/potsdam_split_seed20260915.json',
    'configs/rebuild_v1/r05_quality_plus_dropout_16k.json',
    'configs/rebuild_v1/r01_optical_only_16k.json',
    'scripts/summarize_rebuild_v1_d18_d19.py',
    'scripts/train_rebuild_v1_r01_optical_only.py',
    'scripts/d15_capability.py','model/rebuild_v1_optical_only.py',
    'scripts/d18_d19_night.py','model/rebuild_v1_night_screen.py',
    'scripts/train_rebuild_v1_d18_d19.py','scripts/eval_rebuild_v1_d18_d19.py',
    'scripts/d16_d17_portfolio.py','scripts/train_rebuild_v1_d16_d17.py',
    'scripts/train_rebuild_v1_r02_budget_pilot.py',
    'model/vitcross_seg_modeling_freq_ablation.py',
    'model/vitcross_seg_modeling_freqfusion.py',
    'model/vit_seg_modeling_resnet_skip.py','model/dynamic_conv.py',
    'model/vit_seg_configs.py',
    'scripts/night_boundary_metrics.py',
    'tests/test_d18_d19_night.py','tests/test_d18_replication.py',
)


def digest(path):
    hash_ = hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda:file.read(8*1024*1024),b''):
            hash_.update(block)
    return hash_.hexdigest()


def d18_python():
    old=ROOT/'records/rebuild_v1_d18_d19_queue_20260927/d18_python.txt'
    if old.is_file():
        python=Path(old.read_text(encoding='utf-8').strip())
        if python.is_file():
            return str(python)
    conda = os.environ.get('CONDA_EXE') or shutil.which('conda')
    if not conda:
        raise RuntimeError('conda executable unavailable')
    base = Path(subprocess.check_output([conda,'info','--base'],text=True).strip())
    python = base/'envs/d18_dino/bin/python'
    if not python.is_file():
        raise RuntimeError(f'D18 Python unavailable: {python}')
    return str(python)


def active_minutes(name):
    if name.startswith('EVAL_'):
        log=OUT/f'{name}.log'
        if not log.is_file():
            return 13.4
        tail=log.read_text(encoding='utf-8',errors='replace')[-16000:]
        completed=len(re.findall(r'^EVAL P[012] seed17 ',tail,re.MULTILINE))
        return max(1.,13.4*(22-min(22,completed))/22)
    log=OUT/f'{name}.log'
    if not log.is_file():
        return 47.
    tail=log.read_text(encoding='utf-8',errors='replace')[-16000:]
    matches=re.findall(r'step=(\d+)/(\d+) loss=[^\s]+ elapsed=([\d.]+)s',tail)
    if not matches:
        return 47.
    step,total,elapsed=matches[-1]
    step,total,elapsed=int(step),int(total),float(elapsed)
    return 13.4+max(0,total-step)*elapsed/max(1,step)/60


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'lock').open('w') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print('D18 replication queue already running',flush=True)
            return 3
        mutex = threading.Lock()
        active = {}
        def record(job, state, detail=''):
            line=f'{datetime.now().astimezone().isoformat(timespec="seconds")}\t{job}\t{state}\t{detail}'
            with mutex:
                with (OUT/'status.tsv').open('a',encoding='utf-8') as file:
                    file.write(line+'\n')
            print(line,flush=True)
        try:
            ROOT.resolve().relative_to(Path('/home/jovyan/zzx').resolve())
            commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
            record('QUEUE','START',commit)
            for name in SOURCES:
                subprocess.run(['git','ls-files','--error-unmatch','--',name],cwd=ROOT,
                               check=True,stdout=subprocess.DEVNULL)
            subprocess.run(['git','diff','--exit-code','HEAD','--',*SOURCES],cwd=ROOT,
                           check=True,stdout=subprocess.DEVNULL)
            frozen={name:digest(ROOT/name) for name in SOURCES}
            cfg=json.loads((ROOT/'configs/rebuild_v1/d18_d19_night_20260927.json').read_text())
            split=json.loads((ROOT/cfg['split_file']).read_text())
            if len(split['train16'])!=16 or len(split['val2'])!=2 or set(split['train16']+split['val2']) & set(split['historical_exposed_test6']):
                raise RuntimeError('Train16/Val2/Test6 split boundary failed')
            base=json.loads((ROOT/'configs/rebuild_v1/r05_quality_plus_dropout_16k.json').read_text())
            data=Path(base['data_root']).resolve()
            data.relative_to(Path('/home/jovyan/zzx').resolve())
            for tile in split['train16']+split['val2']:
                a,b=tile.split('_')
                paths=[data/'2_Ortho_RGB'/f'top_potsdam_{tile}_RGB.tif',
                       data/'1_DSM/1_DSM'/f'dsm_potsdam_{int(a):02d}_{int(b):02d}.tif',
                       data/'5_Labels_for_participants'/f'top_potsdam_{tile}_label.tif']
                if tile in split['val2']:
                    paths.append(data/'5_Labels_for_participants_no_Boundary'/f'top_potsdam_{tile}_label_noBoundary.tif')
                if not all(path.is_file() for path in paths):
                    raise RuntimeError(f'dataset files missing for {tile}')
            for arm in ARMS:
                old=ROOT/'records/rebuild_v1_d18_d19_20260927'/f'{arm}_seed42'
                if not (old/'summary.json').is_file() or not all((old/f'{c}_{t}_prediction.npz').is_file()
                    for c in CONDITIONS for t in split['val2']):
                    raise RuntimeError(f'original seed42 predictions/summary missing: {arm}')
            oldref=ROOT/'runs/rebuild_v1/R01_optical_only_seed42_sched16000_stop16000/best_model.pth'
            if not oldref.is_file():
                raise RuntimeError('historical R01 seed42 reference missing')
            indices=subprocess.check_output(['nvidia-smi','--query-gpu=index','--format=csv,noheader'],text=True).split()
            if not {'0','1'}.issubset(indices):
                raise RuntimeError('physical GPU0/GPU1 unavailable')
            if shutil.disk_usage(ROOT).free < 30*1024**3:
                raise RuntimeError('at least 30 GiB free disk required')
            python=d18_python()
            env=dict(os.environ,CUDA_VISIBLE_DEVICES='0',PYTHONDONTWRITEBYTECODE='1',
                     CUBLAS_WORKSPACE_CONFIG=':4096:8',XFORMERS_DISABLED='1',
                     OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2')
            with (OUT/'preflight.log').open('a',encoding='utf-8') as log:
                subprocess.run([python,'-B','-m','unittest','discover','-s','tests','-p','test_d18_d19_night.py','-v'],
                               cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
                subprocess.run([python,'-B','-m','unittest','discover','-s','tests','-p','test_d18_replication.py','-v'],
                               cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
                subprocess.run([python,'-B','-c','import sys; sys.path.insert(0,"scripts"); import d18_replication as p; p.validate(); print("REPLICATION CONFIG PASS")'],
                               cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
            plan=dict(git_commit=commit,source_sha256=frozen,arms=list(ARMS),
                      training_seed=17,evaluation_corruption_seed=42,physical_gpus=[0,1],
                      d18_python=python,data_root=str(data),test6_loaded=False)
            (OUT/'planned_jobs.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
            record('PREFLIGHT','COMPLETE','source/data/old predictions/GPU0+1/disk/CPU tests')
            def unchanged():
                return all(digest(ROOT/name)==value for name,value in frozen.items())
            def stage(gpu, phase, arm):
                if not unchanged():
                    record(f'{phase}_{arm}_17','BLOCKED','source/config changed after launch')
                    return False
                name=f'{phase}_{arm}_17'
                args=['--arm',arm,'--seed','17']+(['--smoke'] if phase=='SMOKE' else [])
                child_env=dict(env,CUDA_VISIBLE_DEVICES=str(gpu))
                with mutex:
                    active[gpu]=name
                record(name,'START',f'gpu={gpu}')
                with (OUT/f'{name}.log').open('a',encoding='utf-8') as log:
                    train=subprocess.run([python,'-B','-u','scripts/train_rebuild_v1_d18_replication.py',*args],
                                         cwd=ROOT,env=child_env,stdout=log,stderr=subprocess.STDOUT)
                record(name,'COMPLETE' if train.returncode==0 else 'FAILED',f'train={train.returncode}')
                if train.returncode:
                    record(f'EVAL_{name}','BLOCKED','training incomplete')
                    with mutex: active.pop(gpu,None)
                    return False
                record(f'EVAL_{name}','START',f'gpu={gpu}')
                with mutex:
                    active[gpu]=f'EVAL_{name}'
                with (OUT/f'EVAL_{name}.log').open('a',encoding='utf-8') as log:
                    evaluation=subprocess.run([python,'-B','-u','scripts/eval_rebuild_v1_d18_replication.py',*args],
                                              cwd=ROOT,env=child_env,stdout=log,stderr=subprocess.STDOUT)
                record(f'EVAL_{name}','COMPLETE' if evaluation.returncode==0 else 'FAILED',str(evaluation.returncode))
                with mutex: active.pop(gpu,None)
                return evaluation.returncode==0
            def wave(phase):
                jobs=iter(ARMS)
                results={}
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    running={}
                    for gpu in (0,1):
                        arm=next(jobs,None)
                        if arm: running[pool.submit(stage,gpu,phase,arm)]=(gpu,arm)
                    last_eta=0
                    while running:
                        completed,_=concurrent.futures.wait(running,timeout=5,
                            return_when=concurrent.futures.FIRST_COMPLETED)
                        for future in completed:
                            gpu,arm=running.pop(future)
                            try: results[arm]=bool(future.result())
                            except Exception as error:
                                results[arm]=False
                                record(f'{phase}_{arm}_17','FAILED',str(error))
                            next_arm=next(jobs,None)
                            if next_arm: running[pool.submit(stage,gpu,phase,next_arm)]=(gpu,next_arm)
                        if phase=='FORMAL' and time.monotonic()-last_eta>=120:
                            with mutex:
                                snapshot=dict(active)
                            loads=[active_minutes(snapshot[gpu]) if gpu in snapshot else 0. for gpu in (0,1)]
                            pending=len(ARMS)-len(results)-len(running)
                            for _ in range(pending):
                                gpu=min(range(2),key=lambda i:loads[i])
                                loads[gpu]+=47.
                            estimate=max(loads)
                            record('ETA','UPDATE',f'formal_complete={len(results)}/3 active={snapshot} pending={pending} approx_remaining={estimate:.0f}min (seed42 pace)')
                            last_eta=time.monotonic()
                return results
            smoke=wave('SMOKE')
            if not all(smoke.values()):
                record('SMOKE_GATE','FAILED',str(smoke))
                formal={}
            else:
                record('SMOKE_GATE','COMPLETE','all 3 train/reload/eval branches')
                formal=wave('FORMAL')
            analysis_ok=False
            if formal and all(formal.values()):
                record('ANALYSIS','START','paired pixels and both-seed decision')
                with (OUT/'ANALYSIS.log').open('a',encoding='utf-8') as log:
                    analysis=subprocess.run([python,'-B','-u','scripts/analyze_rebuild_v1_d18_replication.py'],
                        cwd=ROOT,env=dict(env,CUDA_VISIBLE_DEVICES=''),stdout=log,stderr=subprocess.STDOUT)
                analysis_ok=analysis.returncode==0
                record('ANALYSIS','COMPLETE' if analysis_ok else 'FAILED',str(analysis.returncode))
            else:
                record('ANALYSIS','BLOCKED','one or more formal evaluations incomplete')
            record('QUEUE','FINISHED',f'smoke={smoke} formal={formal} analysis_ok={analysis_ok}')
            record('ARCHIVE','START','compact GitHub evidence package')
            with (OUT/'ARCHIVE.log').open('a',encoding='utf-8') as log:
                archive=subprocess.run([sys.executable,'-B','-u','scripts/archive_rebuild_v1_d18_replication.py'],
                    cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            record('ARCHIVE','COMPLETE' if archive.returncode==0 else 'FAILED',str(archive.returncode))
            return 0 if analysis_ok and archive.returncode==0 else 1
        except Exception as error:
            record('QUEUE','STOPPED',str(error))
            return 1


if __name__=='__main__':
    raise SystemExit(main())
