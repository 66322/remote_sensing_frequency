"""Snapshot and run bounded dual-GPU budget measurement, then upload light records."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

FILES=['scripts/run_rebuild_v1_d23.py','scripts/d23_engine.py','scripts/d23_lifecycle.py',
 'scripts/probe_rebuild_v1_d23_gate.py','model/rebuild_v1_d23_gate.py',
 'scripts/summarize_rebuild_v1_d23_budget.py','scripts/upload_rebuild_v1_d23_budget_records.py',
 'tests/test_d23_engine.py','tests/test_d23_gate.py','tests/test_d23_probe_admission.py',
 'tests/test_d23_screen.py','scripts/summarize_rebuild_v1_d23.py','tests/test_d23_budget.py']
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--commit',required=True);ap.add_argument('--directory',type=Path,required=True);args=ap.parse_args()
    root=args.root.resolve();root.relative_to(Path('/home/jovyan/zzx').resolve())
    # Resolve locally fetched immutable commit, not the mutable checkout.
    commit=subprocess.check_output(['git','-C',str(root),'rev-parse',args.commit+'^{commit}'],text=True).strip()
    base=args.directory.resolve();base.relative_to(root/'records')
    if not base.name.startswith('research_d23_b_budget_'):raise ValueError('unexpected budget directory')
    if base.exists():
        if {p.name for p in base.iterdir()}!={'launch_budget.py'}:raise ValueError('refuse nonempty existing output')
    else:base.mkdir()
    code=base/'code'
    for name in FILES:
        data=subprocess.check_output(['git','-C',str(root),'show',commit+':'+name])
        path=code/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as f:f.write(data)
    (base/'execution_commit.txt').write_text(commit+'\n')
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
             PYTHONDONTWRITEBYTECODE='1')
    with (base/'cpu_checks.log').open('x') as log:
        subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(code/'tests'),
                        '-p','test_d23*.py','-v'],env=dict(env,CUDA_VISIBLE_DEVICES=''),
                       cwd=code,stdout=log,stderr=subprocess.STDOUT,timeout=120,check=True)
    print('D23_BUDGET_DIRECTORY='+str(base),flush=True)
    jobs=[]
    try:
        for gpu in (0,1):
            log=(base/f'gpu{gpu}.log').open('x')
            process=subprocess.Popen([sys.executable,'-B',str(code/'scripts/run_rebuild_v1_d23.py'),
               '--root',str(root),'--gpu',str(gpu),'--output',str(base/f'gpu{gpu}'),'--mode','budget'],
               env=env,cwd=root,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            jobs.append((process,log))
        started=time.monotonic()
        while any(p.poll() is None for p,_ in jobs):
            if any(p.poll() not in (None,0) for p,_ in jobs):
                raise RuntimeError('worker failed; retain logs for diagnosis')
            if time.monotonic()-started>1850:
                raise RuntimeError('30-minute measurement plus shutdown margin exceeded')
            time.sleep(2)
        if any(p.returncode for p,_ in jobs):raise RuntimeError('worker failed')
    finally:
        for process,log in jobs:
            if process.poll() is None:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL);process.wait()
            log.close()
    subprocess.run([sys.executable,'-B',str(code/'scripts/summarize_rebuild_v1_d23_budget.py'),
                    '--directory',str(base)],env=env,check=True)
    subprocess.run([sys.executable,'-B',str(code/'scripts/upload_rebuild_v1_d23_budget_records.py'),
                    '--root',str(root),'--directory',str(base)],env=env,check=True)
if __name__=='__main__':main()
