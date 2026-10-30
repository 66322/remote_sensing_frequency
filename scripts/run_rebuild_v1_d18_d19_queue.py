"""Finite shared-GPU portfolio with branch-local smoke gates and preparation isolation."""
import os
os.environ.setdefault('CUDA_DEVICE_ORDER','PCI_BUS_ID')
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
os.environ.setdefault('XFORMERS_DISABLED','1')
for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):
    os.environ[key]='2'
import concurrent.futures as futures
from collections import deque
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'records/rebuild_v1_d18_d19_queue_20260927'
CFG=ROOT/'configs/rebuild_v1/d18_d19_night_20260927.json'
C_SMOKES=('C0','C1','C2','C3','CP','C4','C5')
P_SMOKES=('P0','P1','P2')
C_FORMAL=('C0','C2','CP','C1','C3')


def main():
    import fcntl
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'lock').open('w') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print('Queue already running',flush=True)
            return 3
        status_lock=threading.Lock()
        def record(job,state,detail=''):
            line=f'{datetime.now().astimezone().isoformat(timespec="seconds")}\t{job}\t{state}\t{detail}'
            with status_lock:
                with (OUT/'status.tsv').open('a',encoding='utf-8') as file:
                    file.write(line+'\n')
            print(line,flush=True)
        def stage(gpu,name,python,script,args):
            record(name,'START',f'gpu={gpu}')
            env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu),PYTHONDONTWRITEBYTECODE='1')
            with (OUT/f'{name}.log').open('a',encoding='utf-8') as log:
                code=subprocess.run([python,'-B','-u',script,*args],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
            record(name,'COMPLETE' if code==0 else 'FAILED',str(code))
            return code==0
        try:
            ROOT.resolve().relative_to(Path('/home/jovyan/zzx').resolve())
            commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
            record('QUEUE','START',commit)
            cfg=json.loads(CFG.read_text())
            sources=['scripts/d18_d19_night.py','scripts/train_rebuild_v1_d18_d19.py',
                'scripts/eval_rebuild_v1_d18_d19.py','scripts/summarize_rebuild_v1_d18_d19.py',
                'scripts/night_boundary_metrics.py','model/rebuild_v1_night_screen.py',
                'scripts/run_rebuild_v1_d18_d19_queue.py','scripts/run_rebuild_v1_d18_d19_queue.sh',
                'scripts/setup_rebuild_v1_d18_environment.sh','scripts/prepare_rebuild_v1_d18.py',
                'scripts/eval_rebuild_v1_d18_legacy_boundaries.py','tests/test_d18_d19_night.py',
                str(CFG.relative_to(ROOT)), 'scripts/d16_d17_portfolio.py',
                'scripts/train_rebuild_v1_d16_d17.py','scripts/train_rebuild_v1_r02_budget_pilot.py',
                'scripts/train_rebuild_v1_r01_optical_only.py','scripts/d15_capability.py',
                'model/vitcross_seg_modeling_freq_ablation.py','model/vitcross_seg_modeling_freqfusion.py',
                'model/vit_seg_modeling_resnet_skip.py','model/dynamic_conv.py','model/vit_seg_configs.py',
                'model/rebuild_v1_optical_only.py','configs/rebuild_v1/r05_quality_plus_dropout_16k.json',
                'configs/rebuild_v1/r01_optical_only_16k.json',cfg['split_file']]
            subprocess.run(['git','diff','--exit-code','HEAD','--',*sources],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
            frozen={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}
            (OUT/'planned_jobs.json').write_text(json.dumps(dict(git_commit=commit,source_sha256=frozen,
                base_arms=cfg['base_arms'],conditional_arms=cfg['conditional_arms'],seeds=[42],
                physical_gpus=[0,1],test6_loaded=False),indent=2)+'\n')
            with (OUT/'preflight.log').open('a',encoding='utf-8') as log:
                subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_d18_d19_night.py','-v'],cwd=ROOT,env=dict(os.environ,CUDA_VISIBLE_DEVICES='0'),stdout=log,stderr=subprocess.STDOUT,check=True)
            indices=subprocess.check_output(['nvidia-smi','--query-gpu=index','--format=csv,noheader'],text=True).split()
            if not {'0','1'}.issubset(indices):
                raise RuntimeError('physical GPU0/GPU1 missing')
            if shutil.disk_usage(ROOT).free<55*1024**3:
                raise RuntimeError('55 GiB free required for checkpoint/atomic save/new environment; no evidence deleted')
            split=json.loads((ROOT/cfg['split_file']).read_text())
            if len(split['train16'])!=16 or len(split['val2'])!=2 or set(split['train16']+split['val2']) & set(split['historical_exposed_test6']):
                raise RuntimeError('split safety failure')
            base=json.loads((ROOT/'configs/rebuild_v1/r05_quality_plus_dropout_16k.json').read_text())
            for tile in split['train16']+split['val2']:
                a,b=tile.split('_')
                paths=[Path(base['data_root'])/'2_Ortho_RGB'/f'top_potsdam_{tile}_RGB.tif',
                    Path(base['data_root'])/'1_DSM/1_DSM'/f'dsm_potsdam_{int(a):02d}_{int(b):02d}.tif',
                    Path(base['data_root'])/'5_Labels_for_participants'/f'top_potsdam_{tile}_label.tif']
                if tile in split['val2']:
                    paths.append(Path(base['data_root'])/'5_Labels_for_participants_no_Boundary'/f'top_potsdam_{tile}_label_noBoundary.tif')
                if not all(p.is_file() for p in paths):
                    raise RuntimeError(f'dataset files missing: {tile}')
            for prefix in ('R05_dual_f0_quality_plus_dropout','R01_optical_only'):
                anchor=ROOT/'runs/rebuild_v1'/f'{prefix}_seed42_sched16000_stop16000'
                if not (anchor/'best_model.pth').is_file() or not (anchor/'summary.json').is_file():
                    raise RuntimeError(f'anchor missing: {prefix}')
            record('PREFLIGHT','COMPLETE','inputs/CPU tests/GPU0+1/disk/source bindings')
            def prepare():
                record('D18_PREPARATION','START','isolated conda environment and official pinned weights')
                with (OUT/'D18_PREPARATION.log').open('a',encoding='utf-8') as log:
                    process=subprocess.Popen(['bash','scripts/setup_rebuild_v1_d18_environment.sh'],cwd=ROOT,env=dict(os.environ,CUDA_VISIBLE_DEVICES='0'),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                    try:
                        code=process.wait(timeout=7200)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid,signal.SIGTERM)
                        try:
                            process.wait(timeout=30)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid,signal.SIGKILL)
                            process.wait()
                        raise RuntimeError('D18 setup exceeded 2 hours; own process group stopped; D19 continues')
                record('D18_PREPARATION','COMPLETE' if code==0 else 'FAILED',str(code))
                return (OUT/'d18_python.txt').read_text().strip() if code==0 else None
            def execute(gpu,job,python):
                kind,arm=job
                if any(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=v for p,v in frozen.items()):
                    record(str(job),'BLOCKED','source/config changed after launch')
                    return False
                if kind=='legacy':
                    return stage(gpu,f'LEGACY_BOUNDARY_{arm}',python,'scripts/eval_rebuild_v1_d18_legacy_boundaries.py',['--arm',arm])
                args=['--arm',arm,'--seed','42']+(['--smoke'] if kind=='smoke' else [])
                name=f'{kind.upper()}_{arm}_42'
                if not stage(gpu,f'TRAIN_{name}',python,'scripts/train_rebuild_v1_d18_d19.py',args):
                    record(f'EVAL_{name}','BLOCKED','training incomplete')
                    return False
                return stage(gpu,f'EVAL_{name}',python,'scripts/eval_rebuild_v1_d18_d19.py',args)

            ready=deque(('smoke',a) for a in C_SMOKES)
            # Existing checkpoint diagnostics can fill preparation/gate gaps without retraining.
            for a in ('A0','A2','B1','B2'):
                ck=ROOT/'runs/rebuild_v1'/f'D16_D17_{a}_seed42_4000_20260926/last_train_state.pth'
                if ck.is_file():
                    ready.append(('legacy',a))
                else:
                    record(f'LEGACY_{a}','BLOCKED','completed old checkpoint absent')
            running={}
            done={}
            p_python=None
            p_prepared=c_released=p_released=conditional=False
            started=time.monotonic()
            progress=False
            with futures.ThreadPoolExecutor(max_workers=1) as prep_pool, futures.ThreadPoolExecutor(max_workers=2) as gpu_pool:
                prep=prep_pool.submit(prepare)
                while ready or running or not p_prepared:
                    if not p_prepared and prep.done():
                        p_prepared=True
                        try:
                            p_python=prep.result()
                        except Exception as error:
                            record('D18_PREPARATION','FAILED',str(error))
                        if p_python:
                            ready.extendleft(('smoke',a) for a in reversed(P_SMOKES))
                        else:
                            for a in P_SMOKES:
                                record(f'PILOT_{a}','BLOCKED','D18 preparation failed; independent D19 continues')
                    for gpu in (0,1):
                        if gpu not in running and ready:
                            job=ready.popleft()
                            python=p_python if job[1].startswith('P') else sys.executable
                            running[gpu]=(gpu_pool.submit(execute,gpu,job,python),job)
                    completed=[gpu for gpu,(task,job) in running.items() if task.done()]
                    for gpu in completed:
                        task,job=running.pop(gpu)
                        try:
                            done[job]=bool(task.result())
                        except Exception as error:
                            done[job]=False
                            record(str(job),'FAILED',str(error))
                    if not c_released and all(('smoke',a) in done for a in C_SMOKES):
                        c_released=True
                        if all(done['smoke',a] for a in C_SMOKES):
                            record('D19_SMOKE_GATE','COMPLETE','all 7 training/loss/reload/evaluation branches')
                            ready.appendleft(('pilot','C0'))
                            ready.extend(('pilot',a) for a in C_FORMAL[1:])
                        else:
                            for a in C_FORMAL+('C4','C5'):
                                record(f'PILOT_{a}','BLOCKED','D19 smoke gate failed')
                    if p_python and not p_released and all(('smoke',a) in done for a in P_SMOKES):
                        p_released=True
                        if all(done['smoke',a] for a in P_SMOKES):
                            record('D18_SMOKE_GATE','COMPLETE','3 frozen encoder/head/aux/reload/evaluation branches')
                            ready.appendleft(('pilot','P0'))
                            ready.extend(('pilot',a) for a in ('P1','P2'))
                        else:
                            for a in P_SMOKES:
                                record(f'PILOT_{a}','BLOCKED','D18 smoke gate failed')
                    if not conditional and all(('pilot',a) in done for a in C_FORMAL):
                        conditional=True
                        gate_ok=stage(0,'CONDITIONAL_SCREEN',sys.executable,'scripts/summarize_rebuild_v1_d18_d19.py',['--gate'])
                        gate_path=ROOT/'records/rebuild_v1_d18_d19_20260927/conditional_gate.json'
                        trigger=gate_ok and all(done['pilot',a] for a in C_FORMAL) and json.loads(gate_path.read_text())['conditional_trigger']
                        if trigger:
                            ready.extend(('pilot',a) for a in ('C4','C5'))
                        else:
                            for a in ('C4','C5'):
                                record(f'PILOT_{a}','SKIPPED','structure screen not passed or prerequisite failed')
                    if not progress and time.monotonic()-started>=24*3600:
                        record('24H_PROGRESS','CONTINUING',f'completed_jobs={len(done)}; finite queue continues')
                        progress=True
                    if running and not completed:
                        futures.wait([x[0] for x in running.values()],timeout=1,return_when=futures.FIRST_COMPLETED)
                    elif not ready and not running and not p_prepared:
                        time.sleep(1)
            summary_ok=stage(0,'SUMMARY',sys.executable,'scripts/summarize_rebuild_v1_d18_d19.py',[])
            decision=json.loads((ROOT/'records/rebuild_v1_d18_d19_20260927/decision.json').read_text()) if summary_ok else {}
            failures=sum(not ok for ok in done.values())
            incomplete=decision.get('status')!='COMPLETE'
            formal=sum(kind=='pilot' for kind,arm in done)
            formal_ok=sum(kind=='pilot' and ok for (kind,arm),ok in done.items())
            record('QUEUE','FINISHED',f'jobs_all={len(done)} formal_attempted={formal} formal_complete={formal_ok} failures={failures} missing_base={decision.get("missing_base")} missing_conditional={decision.get("missing_conditional")} summary_ok={summary_ok}')
            return 1 if failures or incomplete or not summary_ok else 0
        except Exception as error:
            record('QUEUE','STOPPED',str(error))
            return 1


if __name__=='__main__':
    raise SystemExit(main())
