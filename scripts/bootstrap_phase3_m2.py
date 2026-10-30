"""Fixed-source M2 registration. Standard library bootstrap; no Git checkout."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime,timezone,timedelta
from pathlib import Path

ROOT=Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro')
SOURCE_RUN='research_phase3_m1_recovery_20261015T164357_19327'

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(data):return hashlib.sha256(data).hexdigest()
def download(commit,path):
    with urllib.request.urlopen('https://raw.githubusercontent.com/66322/remote_sensing_frequency/'+commit+'/'+path,timeout=90) as r:return r.read()

def main():
    import fcntl
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--commit',required=True)
    p.add_argument('--inspect',action='store_true',help='headers and GPU only; no run/training registration')
    args=p.parse_args();root=args.root.resolve()
    if root!=ROOT or not re.fullmatch('[a-f0-9]{40}',args.commit):raise RuntimeError('exact project root/full immutable commit required')
    records=root/'records';source=records/SOURCE_RUN
    manifest=json.loads(download(args.commit,'configs/phase3_m2_execution_manifest.json'))
    if manifest['core_jobs']!=108 or manifest['updates']!=32000:raise RuntimeError('execution manifest budget')
    # An immutable small source package can be prepared even while GPUs are busy.
    package=records/('phase3_m2_package_'+args.commit);package.mkdir(exist_ok=True)
    with (records/'phase3_m2_registration.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        inherited=read(source/'code_manifest.json')
        for name,h in inherited['files'].items():
            f=(source/'code'/name).resolve();f.relative_to((source/'code').resolve());data=f.read_bytes()
            if digest(data)!=h:raise RuntimeError('inherited source changed: '+name)
            target=(package/name).resolve();target.relative_to(package.resolve());target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():
                # New files may intentionally replace inherited source below.
                if name not in manifest['files'] and digest(target.read_bytes())!=h:raise RuntimeError('package source changed')
            else:target.write_bytes(data)
        for name,h in manifest['files'].items():
            target=(package/name).resolve();target.relative_to(package.resolve())
            if target.exists() and digest(target.read_bytes())==h:continue
            data=download(args.commit,name)
            if digest(data)!=h:raise RuntimeError('source download mismatch: '+name)
            if target.exists() and name not in inherited['files']:raise RuntimeError('existing package differs; preserve for inspection')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        sys.path[:0]=[str(package),str(package/'scripts')]
        import phase3_m2_common as c
        from phase3_m2_data import freeze_folds
        folds=freeze_folds(root);inventory=c.gpu_inventory()
        print('M2_GPU_SNAPSHOT',json.dumps(inventory,ensure_ascii=False),flush=True)
        print('M2_LABEL_BLIND_FOLDS',json.dumps(folds,ensure_ascii=False),flush=True)
        if args.inspect:print('INSPECTION_ONLY_NO_RUN_REGISTERED');return
        existing=sorted(records.glob('research_phase3_m2_*'))
        if existing:
            for d in existing:
                print('EXISTING_M2_NO_DUPLICATE',d)
                if (d/'queue_status.json').exists():print((d/'queue_status.json').read_text())
            return
        if not inventory['ready']:print('GPU0_OR_1_BUSY_NO_NEW_RUN_REGISTERED');return
        import shutil
        if shutil.disk_usage(root).free<40*1024**3:raise RuntimeError('40 GiB free reserve required for endpoints and evidence')
        stamp=datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%dT%H%M%S')
        base=records/f'research_phase3_m2_{stamp}_{os.getpid()}';base.mkdir();code=base/'code'
        shutil.copytree(package,code)
        for name in ['jobs','logs','failures','skipped','trajectory_counts','mask_design','publication','temporary','cache/torch','cache/cuda','cache/triton','cache/kernels']:
            (base/name).mkdir(parents=True,exist_ok=True)
        try:
            c.write(base/'folds.json',folds)
            c.write(base/'plan.json',dict(root=str(root),execution_commit=args.commit,source_commit=manifest['source_commit'],allowed_pool=c.FIT,
                seeds=c.SEEDS,physical_gpus=[0,1],updates=32000,batch=16,core_jobs=108,core_updates=3456000,auto_retry=False,
                dmix='stopped mean-gradient coefficient normalization',primary_fusion='probability 0.9 RGB + 0.1 DSM',
                forbidden=['Val2','Test6','held4','final','point_cloud'],walltime_limit=None,extension_B='conditional, reverse contract not yet executable',
                extension_C='budget reservation only',registered_at=c.now()))
            files={f.relative_to(code).as_posix():digest(f.read_bytes()) for f in code.rglob('*') if f.is_file()}
            c.write(base/'code_manifest.json',dict(commit=args.commit,inherited_source=str(source),files=files))
            pretrained=dict(path=str(root/'pretrained_external/dinov2_vits14_pretrain.pth'),repository=str(root/'external/dinov2_7764ea0'))
            if subprocess.check_output(['git','-C',pretrained['repository'],'rev-parse','HEAD'],text=True).strip()!='7764ea0f912e53c92e82eb78a2a1631e92725fc8':raise RuntimeError('DINO source commit changed')
            pretrained.update(sha256=c.sha(pretrained['path']),repository_commit='7764ea0f912e53c92e82eb78a2a1631e92725fc8')
            original=read(records/'research_phase2_matched_20261013T151120_1310582'/'pretrained.json')
            if pretrained['path']!=original['path'] or pretrained['sha256']!=original['sha256']:raise RuntimeError('public pretrained binding differs; no old fine-tuned initialization')
            c.write(base/'pretrained.json',pretrained);c.write(base/'registration.json',dict(binding=c.binding(base),manifest=manifest,observed_at=c.now()))
            c.write(base/'gpu_inventory_registration.json',inventory)
            env=c.environment(base);env['M2_TARGET_RUNTIME']='1'
            # Real import path + Linux memfd transport, no old archive re-audit.
            with (base/'target_checks.log').open('x') as log:
                subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(code/'tests'),'-p','test_phase3_m2.py','-v'],
                    cwd=code,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
            c.write(base/'target_checks.json',dict(passed=True,log_sha256=c.sha(base/'target_checks.log'),CUDA_checks='first formal update; no extra training',observed_at=c.now()))
            with (base/'nohup.log').open('x') as log:
                proc=subprocess.Popen([sys.executable,'-u','-B',str(code/'scripts/control_phase3_m2.py'),'--directory',str(base)],
                    cwd=code,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            c.write(base/'launch.json',dict(controller_pid=proc.pid,observed_at=c.now()))
            c.write(base/'queue_status.json',dict(status='LAUNCHED_PREPARING',controller_pid=proc.pid,observed_at=c.now()))
            print('M2_LAUNCHED',base,'PID='+str(proc.pid),'GPU_UUID_BOUND=0,1',flush=True)
            print('STATUS',sys.executable,'-B',code/'scripts/status_phase3_m2.py','--directory',base,flush=True)
        except BaseException as exc:
            c.write(base/'registration_failure.json',dict(error=str(exc),automatic_retry=False,observed_at=c.now()));raise

if __name__=='__main__':main()
