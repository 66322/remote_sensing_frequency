"""Independent foreground compact upload; no full checkout or silent credential save."""
import argparse
import base64
import gzip
import hashlib
import json
import os
import subprocess
from pathlib import Path
from phase3_m1_common import read,write,sha,binding,verify,retire,now
BRANCH='rebuild-v1-protocol-20260915'
def git(work,*args,capture=False):
    cmd=['git','-C',str(work),*args]
    return subprocess.check_output(cmd) if capture else subprocess.run(cmd,check=True)
def evidence_files(base):
    dirs=('primary','clean','results','scale','analysis','jobs','failures','skipped','retirement')
    files=[]
    for name in dirs:
        files.extend(f for f in (base/name).rglob('*') if f.is_file() and f.suffix in ('.json','.jsonl') and f.name!='progress.json')
    files.extend(f for f in base.glob('*.json') if not f.name.startswith(('upload_','github_','progress_','runtime_')))
    files.append(base/'cpu_checks.log')
    return sorted(set(files))
def main(base):
    import fcntl
    base=Path(base).resolve(); base.relative_to(Path('/home/jovyan/zzx').resolve())
    with (base/'upload.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (base/'github_upload_receipt.json').exists(): print((base/'github_upload_receipt.json').read_text()); return
        state=read(base/'queue_status.json')['status']
        if state not in ('COMPLETE_AWAITING_REVIEW','FINISHED_WITH_FAILURES','FAILED_OR_INTERRUPTED_NO_RETRY'): raise RuntimeError('wait for computation/finalization to exit')
        with (base/'controller.lock').open('a') as compute_lock: fcntl.flock(compute_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        verify(base)
        if not (base/'result_verification.json').exists():
            from verify_phase3_m1 import verify_results
            verify_results(base)
        stage=base/'upload_tmp'; stage.mkdir(exist_ok=True); archive=stage/'core.jsonl.gz'; marker=base/'upload_prepared.json'
        files=evidence_files(base)
        current=[dict(path=f.relative_to(base).as_posix(),bytes=f.stat().st_size,sha256=sha(f)) for f in files]
        if marker.exists():
            prep=read(marker)
            if prep['binding']!=binding(base) or prep['files']!=current or sha(archive)!=prep['archive_sha256']: raise RuntimeError('prepared evidence changed; inspect rather than silently rebuild')
        else:
            print('PACKAGING_CORE',len(files),'files',flush=True)
            with archive.open('wb') as stream,gzip.GzipFile(fileobj=stream,mode='wb',mtime=0) as out:
                for f,row in zip(files,current):
                    data=f.read_bytes()
                    if hashlib.sha256(data).hexdigest()!=row['sha256']: raise RuntimeError('evidence changed during pack')
                    out.write((json.dumps(dict(row,base64=base64.b64encode(data).decode()),separators=(',',':'))+'\n').encode())
            write(marker,dict(binding=binding(base),files=current,archive_sha256=sha(archive),archive_bytes=archive.stat().st_size))
        print('CORE_MIB',round(archive.stat().st_size/1024**2,2),'NO_RETRAIN_OR_INFERENCE',flush=True)
        work=stage/'git'; prefix='records/'+base.name+'/compact_evidence'; dest=work/prefix
        if not (work/'.git').exists():
            work.mkdir(exist_ok=True); git(work,'init','-q'); git(work,'remote','add','origin','https://github.com/66322/remote_sensing_frequency.git')
        # Read trees/index without checking out historical result blobs.
        git(work,'fetch','--quiet','--depth=1','--filter=blob:none','origin',BRANCH)
        git(work,'update-ref','HEAD','FETCH_HEAD')
        git(work,'read-tree','FETCH_HEAD')
        dest.mkdir(parents=True,exist_ok=True); parts=[]
        with archive.open('rb') as src:
            for i,data in enumerate(iter(lambda:src.read(2*1024**2),b'')):
                f=dest/f'core_{i:03d}.gz.b64'; f.write_bytes(base64.b64encode(data))
                parts.append(dict(file=f.name,sha256=sha(f),decoded_bytes=len(data)))
        manifest=dict(binding=binding(base),execution_commit=read(base/'plan.json')['execution_commit'],parts=parts,
             archive_sha256=sha(archive),payload_files=len(current),raw_bytes=sum(x['bytes'] for x in current),
             scientific_evidence='all groups including failures; joint counts and streams, no model/raw/pixel files',new_training_trigger=False)
        write(dest/'manifest.json',manifest)
        for name in ('summary.json','result_verification.json','queue_status.json'):
            if (base/name).exists(): (dest/name).write_bytes((base/name).read_bytes())
        git(work,'add','--',prefix)
        different=subprocess.run(['git','-C',str(work),'diff','--cached','--quiet']).returncode
        if different not in (0,1): raise RuntimeError('cannot compare staged archive')
        if different:
            git(work,'-c','user.name=66322','-c','user.email=57258129+66322@users.noreply.github.com',
                'commit','--quiet','--no-gpg-sign','-m','Archive Phase3-M1 compact integer evidence and lifecycle receipts')
            print('PUSHING_CORE; authentication, if requested, is only for this foreground upload',flush=True)
            git(work,'push','origin','HEAD:refs/heads/'+BRANCH)
        commit=git(work,'rev-parse','HEAD',capture=True).decode().strip()
        git(work,'fetch','--quiet','--depth=1','--filter=blob:none','origin',BRANCH)
        git(work,'merge-base','--is-ancestor',commit,'FETCH_HEAD')
        for f in dest.iterdir():
            remote=git(work,'show','FETCH_HEAD:'+prefix+'/'+f.name,capture=True)
            if hashlib.sha256(remote).hexdigest()!=sha(f): raise RuntimeError('remote readback differs')
        write(base/'github_upload_receipt.json',dict(commit=commit,archive_sha256=sha(archive),all_parts_readback=True,parts=len(parts),observed_at=now()))
        retire(base,stage,'push acknowledged and every uploaded file read back; temporary archive/index/object copy no longer needed')
        print('PHASE3_M1_GITHUB_COMMIT',commit,'UPLOAD_TEMP_RETIRED',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--directory',type=Path,required=True); main(p.parse_args().directory)

