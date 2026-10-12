"""Idempotent snapshot registration. User runs this on server; never trains."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

NEW_FILES = ['scripts/'+n+'.py' for n in ('phase15_common','phase15_numeric','prepare_phase15','phase15_inference',
    'run_phase15','smoke_phase15','analyze_phase15','summarize_phase15','control_phase15','status_phase15',
    'enqueue_phase15','upload_phase15')]
NEW_FILES += ['tests/test_phase15.py','docs/protocols/PHASE_1_5_EXECUTION_20261012.md',
              'docs/protocols/PHASE_1_5_RECOVERABILITY_20261012.md','docs/protocols/PHASE_1_5_TWO_GPU_PLAN_20261012.md']


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()


def check_path_bug_replacement(base, live_owned, lock_free):
    """One explicit technical replacement; preserve the original immutable attempt."""
    if base.name != 'research_phase15_recoverability_20261012T232212_836118':
        raise RuntimeError('replacement only applies to the reported path bug attempt')
    state = read(base/'queue_status.json')
    plan = read(base/'plan.json')
    if (state['status'] != 'SMOKE_FAILED_HOLD' or
        state.get('error') != 'smoke_phase15.py exit=1' or
        plan['execution_commit'] != '7b12fec6d7fb451e09316ba59f7d62ca8e0c316b' or
        plan['optimizer_updates'] != 0 or len(state['jobs']) != 100 or
        any(j['status'] != 'PENDING' for j in state['jobs'].values()) or
        (base/'smoke_pass.json').exists() or (base/'smoke/gpu1').exists()):
        raise RuntimeError('replacement precondition changed; preserve and diagnose')
    for pid in [state.get(n,-1) for n in ('controller_pid','current_stage_pid','E_pid')]+[j.get('pid',-1) for j in state['jobs'].values()]:
        if live_owned(pid,base):raise RuntimeError('failed attempt still owns a live process')
    if not lock_free(base):raise RuntimeError('failed attempt controller lock held')
    log=(base/'logs/smoke_gpu0.log').read_text(encoding='utf-8')
    expected="TypeError: unsupported operand type(s) for +: 'PosixPath' and 'str'"
    if expected not in log or "write(self.base/'input_binding_last_'+str(self.gpu)+'.json'" not in log:
        raise RuntimeError('failure is not the diagnosed input-binding path bug')
    manifest=read(base/'code_manifest.json')
    for name,digest in manifest['files'].items():
        f=(base/'code'/name).resolve();f.relative_to((base/'code').resolve())
        if sha(f)!=digest:raise RuntimeError('failed snapshot changed: '+name)
    return dict(directory=str(base),status=state['status'],execution_commit=plan['execution_commit'],
        reason='explicit replacement of known input-binding PosixPath+str bug; no scientific retry',
        automatic_retry=False,original_preserved=True,old_case_cache_reused=False,
        receipts={name:sha(base/name) for name in ('plan.json','code_manifest.json','queue_status.json',
            'technical_failure.json','logs/smoke_gpu0.log')})


def main():
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);a.add_argument('--commit',required=True)
    a.add_argument('--replace-path-bug-directory',type=Path)
    x=a.parse_args();root=x.root.resolve();root.relative_to(Path('/home/jovyan/zzx').resolve())
    records=root/'records'
    import fcntl
    with (records/'phase15_registration.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        existing=sorted(records.glob('research_phase15_recoverability_*'))
        replacement=None
        if existing and x.replace_path_bug_directory is None:
            for f in existing:
                print('PHASE15_ALREADY_REGISTERED',f,read(f/'queue_status.json')['status'] if (f/'queue_status.json').exists() else 'HOLD_PARTIAL_REGISTRATION')
            return
        structured=records/'research_structured_failure_v0_20261012T073410_81887'
        paired=records/'research_post_t_paired_v2_20261011T182543_3880702'
        sys.path.insert(0,str(structured/'code/scripts'))
        from d30_common import live_owned,lock_free
        if x.replace_path_bug_directory is not None:
            previous=x.replace_path_bug_directory.resolve();previous.relative_to(records.resolve())
            if existing != [previous]:
                print('PHASE15_REPLACEMENT_NOT_CREATED existing attempts:',*[str(f) for f in existing])
                return
            replacement=check_path_bug_replacement(previous,live_owned,lock_free)
        source_states={}
        for d,expected in ((structured,'STRUCTURED_COMPLETE_AWAITING_REVIEW'),(paired,'PAIRED_COMPLETE_AWAITING_REVIEW')):
            s=read(d/'queue_status.json')
            if s['status']!=expected or any(j['status']!='COMPLETE' for j in s['jobs'].values()):
                raise RuntimeError('original queue not complete: '+str(d))
            if live_owned(s.get('controller_pid',-1),d) or any(live_owned(j.get('pid',-1),d) for j in s['jobs'].values()) or not lock_free(d):
                raise RuntimeError('original queue still owns active workers/lock')
            source_states[d.name]=s
        commit=subprocess.check_output(['git','-C',str(root),'rev-parse',x.commit+'^{commit}'],text=True).strip()
        base=records/('research_phase15_recoverability_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()))
        base.mkdir()
        code=base/'code'
        try:
            inherited=read(structured/'code_manifest.json')
            for name,digest in inherited['files'].items():
                f=(structured/'code'/name).resolve();f.relative_to((structured/'code').resolve())
                if sha(f)!=digest:raise RuntimeError('old source changed: '+name)
                t=code/name;t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(f.read_bytes())
            for name in NEW_FILES:
                t=code/name;t.parent.mkdir(parents=True,exist_ok=True)
                t.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+name]))
            sys.path.insert(0,str(code/'scripts'))
            import phase15_common as c
            source_files={}
            if replacement is not None:
                c.write(base/'technical_replacement.json',replacement)
                source_files['technical_replacement.json']=sha(base/'technical_replacement.json')
            for name,source in (('source_plan.json',structured/'source_plan.json'),('old_mask_manifest.json',structured/'mask_manifest.json'),
                               ('paired_plan.json',paired/'plan.json'),('R16_complete.json',paired/'jobs/R16/complete.json')):
                (base/name).write_bytes(source.read_bytes());source_files[name]=sha(base/name)
            plan=dict(protocol=c.PROTOCOL,root=str(root),structured=str(structured),paired=str(paired),
                execution_commit=commit,source_files=source_files,source_receipts={d.name:{'plan_sha256':sha(d/'plan.json'),
                'code_sha256':sha(d/'code_manifest.json'),'queue_snapshot':source_states[d.name]} for d in (structured,paired)},
                tiles=list(c.TILES),jobs=c.jobs(),physical_gpus=[0,1],optimizer_updates=0,new_seeds=False,
                automatic_retry=False,wall_deadline_hours=None,registered_at=c.now(),
                full_dispatch_requires_real_smoke=True,scientific_review_required_before_new_training=True,
                forbidden_data=['Test6','held4','independent_final'],DSM_zero='existing dsm_present_zero; dm=True',
                entropy='softmax(mean stitched FP32 logits); fixed H/log6 bins',registered_cases=1540,
                expected_inference_upper_count=1538,previous_cache_required=True)
            c.write(base/'plan.json',plan)
            c.write(base/'registration.json',dict(plan_sha256=sha(base/'plan.json'),server_runtime_verified=False))
            c.write(base/'code_manifest.json',dict(commit=commit,inherited_structured_execution=read(structured/'plan.json')['execution_commit'],
                files={f.relative_to(code).as_posix():sha(f) for f in code.rglob('*') if f.is_file()}))
            for folder in ('logs','temporary','cache/torch','cases','smoke','analysis'):(base/folder).mkdir(parents=True,exist_ok=True)
            for folder in ('cuda','triton','torch_kernels'):(base/'cache'/folder).mkdir(parents=True,exist_ok=True)
            env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
                TMPDIR=str(base/'temporary'),TMP=str(base/'temporary'),TEMP=str(base/'temporary'),
                XDG_CACHE_HOME=str(base/'cache'),TORCH_HOME=str(base/'cache/torch'),MPLCONFIGDIR=str(base/'cache/matplotlib'),
                PHASE15_TEST_DIRECTORY=str(base/'test_scratch'),
                CUDA_CACHE_PATH=str(base/'cache/cuda'),TRITON_CACHE_DIR=str(base/'cache/triton'),PYTORCH_KERNEL_CACHE_PATH=str(base/'cache/torch_kernels'),HF_HOME=str(base/'cache/huggingface'),
                PYTHONPATH=os.pathsep.join([str(code),str(code/'scripts')]))
            state=dict(status='CPU_TESTING',observed_at=c.now(),jobs={j['id']:dict(status='PENDING',gpu=None) for j in c.jobs()})
            c.write(base/'queue_status.json',state)
            with (base/'cpu_checks.log').open('x') as log:
                subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(code/'tests'),'-p','test_phase15.py','-v'],
                    cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=900)
            state.update(status='REGISTERED_PENDING_PREPARATION',observed_at=c.now());c.write(base/'queue_status.json',state)
            logpath=base/('nohup_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log')
            cmd=[sys.executable,'-u','-B',str(code/'scripts/control_phase15.py'),'--directory',str(base)]
            with logpath.open('x') as log:
                proc=subprocess.Popen(['nohup',*cmd],cwd=code,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            c.write(base/'launch.json',dict(controller_pid=proc.pid,log=str(logpath),command=cmd))
            if replacement is not None:print('PHASE15_TECHNICAL_REPLACEMENT_OF',replacement['directory'],flush=True)
            print('PHASE15_REGISTERED',base,'PID='+str(proc.pid),'GPU=0,1 TRAININGS=0 JOBS=100 SMOKE_BEFORE_FULL=True NO24H_DEADLINE',flush=True)
            print('PHASE15_LOG',logpath,flush=True)
        except BaseException as exc:
            failure=dict(error=str(exc),automatic_retry=False)
            (base/'registration_failure.json').write_text(json.dumps(failure,indent=2)+'\n',encoding='utf-8')
            if (base/'queue_status.json').exists():
                s=read(base/'queue_status.json');s.update(status='HOLD_REGISTRATION',error=str(exc));
                (base/'queue_status.json').write_text(json.dumps(s,indent=2)+'\n',encoding='utf-8')
            raise


if __name__=='__main__':main()
