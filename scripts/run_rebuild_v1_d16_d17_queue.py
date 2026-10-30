"""Two shared workers: each pilot immediately evaluates; failures isolate jobs."""
import os
os.environ.setdefault('CUDA_DEVICE_ORDER','PCI_BUS_ID')
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
for name in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):
    os.environ[name] = '2'
import collections
import concurrent.futures
import json
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'records/rebuild_v1_d16_d17_queue_20260926'
CONFIG = ROOT/'configs/rebuild_v1/d16_d17_portfolio_20260926.json'
ARMS = ('A0','A1','A2','A3','A4','A5','B1','B2')
SOURCES = ('scripts/d16_d17_portfolio.py','scripts/train_rebuild_v1_d16_d17.py',
           'scripts/eval_rebuild_v1_d16_d17.py','scripts/summarize_rebuild_v1_d16_d17.py',
           'scripts/run_rebuild_v1_d16_d17_queue.py','scripts/run_rebuild_v1_d16_d17_queue.sh',
           'tests/test_d16_d17_portfolio.py', 'configs/rebuild_v1/d16_d17_portfolio_20260926.json',
           'scripts/train_rebuild_v1_r01_optical_only.py','scripts/train_rebuild_v1_r02_budget_pilot.py',
           'scripts/eval_rebuild_v1_d15_capability.py','scripts/train_rebuild_v1_d15_dsm_only.py',
           'model/vitcross_seg_modeling_freq_ablation.py','model/vitcross_seg_modeling_freqfusion.py',
           'model/vit_seg_modeling_resnet_skip.py','model/dynamic_conv.py','model/vit_seg_configs.py',
           'model/rebuild_v1_optical_only.py','scripts/d15_capability.py',
           'configs/rebuild_v1/r01_optical_only_16k.json','configs/rebuild_v1/r05_quality_plus_dropout_16k.json',
           'configs/rebuild_v1/c_oo_qd_optical_gray_16k.json','configs/rebuild_v1/potsdam_split_seed20260915.json')


def run_shared(jobs, execute, gpus=(0,1)):
    """Claim under lock; callbacks train and evaluate each job on the same GPU."""
    ready = collections.deque(jobs)
    lock = threading.Lock()
    results = []
    def worker(gpu):
        while True:
            with lock:
                if not ready:
                    return
                job = ready.popleft()
            try:
                success = bool(execute(gpu,job))
            except Exception:
                success = False
            with lock:
                results.append((job,success))
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(gpus)) as pool:
        list(pool.map(worker,gpus))
    return results


def main():
    import fcntl
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'lock').open('w') as lockfile:
        try:
            fcntl.flock(lockfile,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print('Queue already running; second launcher stopped.',flush=True)
            return 3
        status_lock = threading.Lock()
        def record(job,state,detail=''):
            with status_lock:
                with (OUT/'status.tsv').open('a',encoding='utf-8') as f:
                    f.write(f'{datetime.now().astimezone().isoformat(timespec="seconds")}\t{job}\t{state}\t{detail}\n')
            print(job,state,detail,flush=True)
        def stage(gpu,name,script,arguments):
            record(name,'START',f'gpu={gpu}')
            env = dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu),PYTHONDONTWRITEBYTECODE='1')
            with (OUT/f'{name}.log').open('a',encoding='utf-8') as log:
                rc = subprocess.run([sys.executable,'-B','-u',script,*arguments],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
            record(name,'COMPLETE' if rc==0 else 'FAILED',str(rc))
            return rc==0
        try:
            ROOT.resolve().relative_to(Path('/home/jovyan/zzx').resolve())
            record('QUEUE','START',subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
            subprocess.run(['git','diff','--exit-code','HEAD','--',*SOURCES],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
            with (OUT/'preflight.log').open('a',encoding='utf-8') as log:
                subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_d16_d17_portfolio.py','-v'],cwd=ROOT,env=dict(os.environ,CUDA_VISIBLE_DEVICES='0'),stdout=log,stderr=subprocess.STDOUT,check=True)
            gpuids = subprocess.check_output(['nvidia-smi','--query-gpu=index','--format=csv,noheader'],text=True).split()
            if not {'0','1'}.issubset(set(gpuids)):
                raise RuntimeError('physical GPU0/GPU1 missing')
            cfg = json.loads(CONFIG.read_text())
            split = json.loads((ROOT/cfg['split_file']).read_text())
            planned = [(a,s,False) for a in ARMS for s in (42,17)] + [(a,42 if a in ('A0','A2','A4','B1') else 17,True) for a in ARMS]
            new_checkpoints = sum(not (ROOT/'runs/rebuild_v1'/f'D16_D17_{a}_seed{s}_4000_20260926{"_smoke" if smoke else ""}'/'last_train_state.pth').is_file() for a,s,smoke in planned)
            reserve_gib = 8+3*new_checkpoints
            if shutil.disk_usage(ROOT).free < reserve_gib*1024**3:
                raise RuntimeError(f'less than {reserve_gib} GiB free for pending checkpoints and atomic saves; provide capacity without deleting experiment evidence')
            for model,config,run in (
                ('R05','r05_quality_plus_dropout_16k.json','R05_dual_f0_quality_plus_dropout'),
                ('C-OO-QD','c_oo_qd_optical_gray_16k.json','C_OO_QD_dual_optical_gray_quality_plus_dropout'),
                ('R01','r01_optical_only_16k.json','R01_optical_only')):
                base = json.loads((ROOT/'configs/rebuild_v1'/config).read_text())
                for seed in (42,17):
                    directory = ROOT/'runs/rebuild_v1'/f'{run}_seed{seed}_sched16000_stop16000'
                    if not (directory/'best_model.pth').is_file() or not (directory/'summary.json').is_file():
                        raise RuntimeError(f'anchor missing: {directory}')
                data = Path(base['data_root'])
                for tile in split['train16']+split['val2']:
                    a,b = tile.split('_')
                    paths = [data/'2_Ortho_RGB'/f'top_potsdam_{tile}_RGB.tif',
                             data/'1_DSM/1_DSM'/f'dsm_potsdam_{int(a):02d}_{int(b):02d}.tif',
                             data/'5_Labels_for_participants'/f'top_potsdam_{tile}_label.tif']
                    if tile in split['val2']:
                        paths.append(data/'5_Labels_for_participants_no_Boundary'/f'top_potsdam_{tile}_label_noBoundary.tif')
                    for path in paths:
                        if not path.is_file():
                            raise FileNotFoundError(path)
            record('PREFLIGHT','COMPLETE','CPU tests, inputs, anchors, GPU indices')
            def execute(gpu,job):
                arm,seed,smoke = job
                args = ['--arm',arm,'--seed',str(seed)]+(['--smoke'] if smoke else [])
                label = f'{"SMOKE" if smoke else "PILOT"}_{arm}_{seed}'
                if not stage(gpu,f'TRAIN_{label}','scripts/train_rebuild_v1_d16_d17.py',args):
                    record(f'EVAL_{label}','BLOCKED','training incomplete; independent jobs continue')
                    return False
                return stage(gpu,f'EVAL_{label}','scripts/eval_rebuild_v1_d16_d17.py',args)
            # Every loss branch, both source architectures and both physical GPUs.
            smoke0 = [(a,42,True) for a in ('A0','A2','A4','B1')]
            smoke1 = [(a,17,True) for a in ('A1','A3','A5','B2')]
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                f0 = pool.submit(run_shared,smoke0,execute,(0,))
                f1 = pool.submit(run_shared,smoke1,execute,(1,))
                smoke = f0.result()+f1.result()
            if not all(ok for _,ok in smoke):
                raise RuntimeError('end-to-end smoke failed; formal queue stopped')
            record('SMOKE_GATE','COMPLETE','8 branches train/save/reload/deterministic clean eval')
            stop = threading.Event()
            def report_later():
                if not stop.wait(24*3600):
                    completed = len(list((ROOT/'records/rebuild_v1_d16_d17_20260926').glob('*seed*/summary.json')))
                    record('24H_PROGRESS','CONTINUING',f'summaries_including_smokes={completed}; finite queue continues')
            reporter = threading.Thread(target=report_later,daemon=True)
            reporter.start()
            # Opposite first seed by arm; workers share remaining ready jobs.
            jobs = [(a,s,False) for i,a in enumerate(ARMS) for s in ((42,17) if i%2==0 else (17,42))]
            results = run_shared(jobs,execute)
            stop.set()
            summary_ok = stage(0,'SUMMARY','scripts/summarize_rebuild_v1_d16_d17.py',[])
            failures = sum(not ok for _,ok in results)
            record('QUEUE','FINISHED',f'jobs={len(results)} failures={failures} summary_ok={summary_ok}')
            return 1 if failures or not summary_ok else 0
        except Exception as error:
            record('QUEUE','STOPPED',str(error))
            return 1


if __name__ == '__main__':
    raise SystemExit(main())
