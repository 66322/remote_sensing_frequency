"""User-run durable lightweight archive. No arrays, weights or recursive log collection."""
import argparse,base64,gzip,json,subprocess
from pathlib import Path
from phase24_common import *
from verify_phase24_results import verify_results
BRANCH='rebuild-v1-protocol-20260915'
def git(work,*args,capture=False):
 cmd=['git','-C',str(work),*args]
 return subprocess.check_output(cmd) if capture else subprocess.run(cmd,check=True)
def main(base):
 base=Path(base).resolve();base.relative_to(Path('/home/jovyan/zzx').resolve())
 import fcntl
 with (base/'upload.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  state=read(base/'queue_status.json')
  if live(read(base/'launch.json')['controller_pid'],base) or any(live(x['pid'],base) for x in state['workers'].values()):
   raise RuntimeError('wait for owned controller/workers to exit')
  p=verify(base);verify_results(base,True);root=Path(p['root']);work=base/'github_upload'
  prefix=Path('records')/base.name/'light_evidence';dest=work/prefix
  archive=base/'upload_evidence.jsonl.gz';prepared=base/'upload_prepared.json';marker=base/'upload_committed.json'
  if not prepared.exists():
   allowed=[]
   for section in ('results','analysis','fits','jobs'):
    for f in (base/section).rglob('*'):
     if f.is_file() and f.suffix in ('.json','.jsonl') and f.name!='progress.json':allowed.append(f)
   top=('plan.json','code_manifest.json','registration.json','registration_cpu_checks.json','technical_replacement.json','launch.json','source_bindings.json','resource_profile.json',
    'prepared.json','gpu_inventory.json','cpu_benchmark.json','smoke_pass.json','summary.json','evidence_index.json',
    'result_verification.json','cpu_checks.log','fit_sample_retirement.json','ram_retirement.json','training_artifact_retirement.json','queue_status.json')
   allowed += [base/n for n in top if (base/n).is_file()]
   for f in (base/'smoke').rglob('*.json'):allowed.append(f)
   allowed=sorted(set(allowed));rows=[]
   temp=archive.with_suffix('.tmp')
   with temp.open('wb') as stream,gzip.GzipFile(fileobj=stream,mode='wb',mtime=0) as out:
    for f in allowed:
     scoped(f,base);raw=f.read_bytes();row=dict(path=f.relative_to(base).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
     rows.append(row);out.write((json.dumps(dict(row,base64=base64.b64encode(raw).decode()),separators=(',',':'))+'\n').encode())
   os.replace(temp,archive)
   write(prepared,dict(binding=binding(base),archive_sha256=sha(archive),files=rows,created_at=now()))
  prep=read(prepared)
  if prep['binding']!=binding(base) or prep['archive_sha256']!=sha(archive):raise RuntimeError('prepared archive changed')
  if not work.exists():
   git(root,'fetch','origin',BRANCH);git(root,'worktree','add','--detach',str(work),'FETCH_HEAD')
  if not marker.exists():
   # Interrupted staging may be resumed only when all changes belong to this exact archive prefix.
   dirty=git(work,'status','--porcelain','-z',capture=True).split(b'\0')
   for row in dirty:
    if row and not row[3:].decode().replace('\\','/').startswith(prefix.as_posix()+'/'):
     raise RuntimeError('unrelated worktree changes preserved; inspect before upload')
   dest.mkdir(parents=True,exist_ok=True);parts=[]
   with archive.open('rb') as stream:
    for i,chunk in enumerate(iter(lambda:stream.read(256*1024),b'')):
     f=dest/('evidence_%04d.gz.b64'%i);f.write_bytes(base64.b64encode(chunk))
     parts.append(dict(file=f.name,sha256=sha(f),decoded_bytes=len(chunk)))
   manifest=dict(run_directory=str(base),execution_commit=p['execution_commit'],archive_sha256=sha(archive),
    archive_parts=parts,payload_count=len(prep['files']),original_bytes=sum(r['bytes'] for r in prep['files']),
    per_file_index='exact bytes, SHA256 and path in decompressed JSONL',
    arrays_weights='server-only; endpoint SHA/index retained',no_training_trigger=True)
   write(dest/'manifest.json',manifest)
   (dest/'summary.json').write_bytes((base/'summary.json').read_bytes())
   git(work,'add','--',prefix.as_posix())
   if git(work,'diff','--cached','--name-only',capture=True).strip():
    git(work,'-c','user.name=66322','-c','user.email=57258129+66322@users.noreply.github.com','commit','-m','Archive Phase2.4 protected diagnosis and conditional heads')
   write(marker,dict(commit=git(work,'rev-parse','HEAD',capture=True).decode().strip(),manifest_sha256=sha(dest/'manifest.json')))
  if git(work,'status','--porcelain',capture=True).strip():raise RuntimeError('upload checkout changed')
  git(work,'fetch','origin',BRANCH)
  git(work,'-c','user.name=66322','-c','user.email=57258129+66322@users.noreply.github.com','rebase','FETCH_HEAD')
  git(work,'push','origin','HEAD:refs/heads/'+BRANCH)
  commit=git(work,'rev-parse','HEAD',capture=True).decode().strip()
  git(work,'fetch','origin',BRANCH)
  git(work,'merge-base','--is-ancestor',commit,'FETCH_HEAD')
  for name in ('manifest.json','summary.json'):
   raw=git(work,'show','FETCH_HEAD:'+prefix.as_posix()+'/'+name,capture=True)
   if raw!=(dest/name).read_bytes():raise RuntimeError('GitHub readback differs')
  for row in read(dest/'manifest.json')['archive_parts']:
   raw=git(work,'show','FETCH_HEAD:'+prefix.as_posix()+'/'+row['file'],capture=True)
   if hashlib.sha256(raw).hexdigest()!=row['sha256']:raise RuntimeError('archive part readback differs')
  write(base/'github_upload_receipt.json',dict(commit=commit,archive_sha256=sha(archive),all_parts_readback=True,observed_at=now()))
  print('PHASE24_GITHUB_COMMIT',commit)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);main(p.parse_args().directory)
