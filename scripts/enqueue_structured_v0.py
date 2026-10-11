"""One registration, immutable inherited source, CPU tests, then wait-only controller."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys

FILES = ['scripts/'+n+'.py' for n in ('structured_v0_common','structured_v0_masks','structured_v0_metrics',
         'prepare_structured_v0','run_structured_v0','control_structured_v0','manage_structured_v0',
         'enqueue_structured_v0','summarize_structured_v0','upload_structured_v0')]
FILES += ['tests/test_structured_v0.py','docs/protocols/STRUCTURED_FAILURE_V0_EXECUTION_20261011.md']


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--root',type=Path,required=True)
    a.add_argument('--commit',required=True)
    args = a.parse_args()
    root = args.root.resolve()
    root.relative_to(Path('/home/jovyan/zzx').resolve())
    records = root/'records'
    source = records/'research_post_t_paired_v2_20261011T182543_3880702'
    sys.path.insert(0,str(source/'code/scripts'))
    from post_t_paired_v2_common import read,write,sha,validate
    import fcntl
    with (records/'structured_v0_registration.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        existing = sorted(records.glob('research_structured_failure_v0_*'))
        if existing:
            for f in existing:
                print('STRUCTURED_ALREADY_REGISTERED', f, read(f/'queue_status.json')['status'] if (f/'queue_status.json').exists() else 'HOLD_INCOMPLETE_REGISTRATION')
            return
        old = validate(read(source/'plan.json'))
        if old['execution_commit'] != '44e4df5afbaeb603e6441e7ef14ff09f228bc027':
            raise RuntimeError('unexpected original execution')
        commit = subprocess.check_output(['git','-C',str(root),'rev-parse',args.commit+'^{commit}'],text=True).strip()
        base = records/('research_structured_failure_v0_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()))
        base.mkdir()
        try:
            code = base/'code'
            manifest = read(source/'code_manifest.json')
            for name,digest in manifest['files'].items():
                oldfile=(source/'code'/name).resolve()
                oldfile.relative_to((source/'code').resolve())
                if sha(oldfile)!=digest:
                    raise RuntimeError('inherited source changed: '+name)
                target=code/name
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(oldfile.read_bytes())
            for name in FILES:
                target=code/name
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+name]))
            sys.path.insert(0,str(code/'scripts'))
            import structured_v0_common as c
            source_bytes=(source/'plan.json').read_bytes()
            (base/'source_plan.json').write_bytes(source_bytes)
            plan=dict(protocol='STRUCTURED_V0_1', root=str(root), execution_commit=commit, predecessor=str(source),
                predecessor_plan_sha256=sha(source/'plan.json'), predecessor_code_sha256=sha(source/'code_manifest.json'),
                source_plan_sha256=sha(base/'source_plan.json'), tiles=list(c.TILES), models=list(c.MODELS), families=list(c.FAMILIES),
                jobs=c.JOBS, optimizer_updates=0, missing_cases=640, clean_cases=8, old_endpoint_checks=6,
                allowed_physical_gpus=[0,1], new_seeds=False, automatic_retry=False, test6_loaded=False,
                generator=dict(tile_shape=[6000,6000], missing_pixels=9000000, main_block=128, main_count=549,
                    remainder_block=72, remainder_count=1, grid_spacing=136, grid_phase_range=[0,7],
                    gradient='Sobel3 reflect magnitude; per-tile percentile90 strict greater',
                    sampling='weighted without replacement exp(2*clip(z,-3,3))',
                    matching='NB proportions max1pp, Car0.2pp, coverage1pp; max50000 improving random swaps',
                    matched_gradient_contrast='positive for every fixed pair, otherwise HOLD', mask_realizations=20),
                real_mask_feasibility_required=True, registration_at=c.now())
            c.write(base/'plan.json',plan)
            c.write(base/'registration.json',dict(plan_sha256=sha(base/'plan.json'),source_plan_sha256=sha(base/'source_plan.json'),
                    predecessor_last_observation=read(source/'queue_status.json'), server_gpu_runtime_verified=False))
            c.write(base/'code_manifest.json',dict(commit=commit, inherited_execution=old['execution_commit'],
                    files={f.relative_to(code).as_posix():sha(f) for f in code.rglob('*') if f.is_file()}))
            for folder in ('logs','control','temporary','cache/torch'):
                (base/folder).mkdir(parents=True,exist_ok=True)
            env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
                TMPDIR=str(base/'temporary'),TEMP=str(base/'temporary'),TMP=str(base/'temporary'),XDG_CACHE_HOME=str(base/'cache'),TORCH_HOME=str(base/'cache/torch'),
                PYTHONPATH=os.pathsep.join([str(code),str(code/'scripts')]))
            state=dict(status='CPU_TESTING', observed_at=c.now(), jobs={n:dict(status='PENDING',gpu=None) for n in c.JOBS})
            c.write(base/'queue_status.json',state)
            with (base/'cpu_checks.log').open('x') as log:
                subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(code/'tests'),'-p','test_structured_v0.py','-v'],
                    cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=900)
            state.update(status='REGISTERED_WAITING_PREDECESSOR',observed_at=c.now())
            c.write(base/'queue_status.json',state)
            logpath=base/('nohup_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log')
            cmd=[sys.executable,'-u','-B',str(code/'scripts/control_structured_v0.py'),'--directory',str(base)]
            with logpath.open('x') as log:
                proc=subprocess.Popen(['nohup',*cmd],cwd=code,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            c.write(base/'launch.json',dict(controller_pid=proc.pid,log=str(logpath),command=cmd))
            print('STRUCTURED_QUEUE_REGISTERED',base,'PID='+str(proc.pid),'WAIT_FOR_PAIRED=True GPU=0,1 TRAININGS=0 MISSING_CASES=640 CLEAN=8 ENDPOINT_CHECKS=6',flush=True)
            print('STRUCTURED_LOG',logpath,flush=True)
        except BaseException as exc:
            write(base/'registration_failure.json',dict(error=str(exc),no_retry=True))
            if (base/'queue_status.json').exists():
                state=read(base/'queue_status.json');state.update(status='HOLD_REGISTRATION',error=str(exc));write(base/'queue_status.json',state)
            raise


if __name__=='__main__':
    main()
