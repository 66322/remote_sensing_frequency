"""One idempotent light JSONL archive commit; originals stay on server."""
import argparse
import gzip
import json
from pathlib import Path
import subprocess
from phase2_common import *

def main(base):
    base=Path(base);p=verify(base);state=read(base/'queue_status.json')
    if state['status']!='PHASE2_COMPLETE_AWAITING_REVIEW':raise RuntimeError('queue not complete')
    launch=read(base/'launch.json')
    if live(launch['controller_pid'],base):raise RuntimeError('wait for controller exit before uploading')
    for row in state['workers'].values():
        if live(row['pid'],base):raise RuntimeError('owned worker still live')
    root=Path(p['root']);work=base/'github_upload';branch='rebuild-v1-protocol-20260915'
    if not work.exists():
        subprocess.run(['git','-C',str(root),'fetch','origin',branch],check=True)
        subprocess.run(['git','-C',str(root),'worktree','add','--detach',str(work),'FETCH_HEAD'],check=True)
        prefix=Path('records')/base.name/'light_evidence';dest=work/prefix;dest.mkdir(parents=True)
        rows=[];archive=base/'upload_counts.jsonl.gz'
        with archive.open('xb') as stream,gzip.GzipFile(fileobj=stream,mode='wb',mtime=0) as z:
            for f in sorted(base.rglob('*')):
                if not f.is_file() or f.suffix not in ('.json','.jsonl'):continue
                if work in f.parents or base/'code' in f.parents:continue
                raw=f.read_bytes();name=f.relative_to(base).as_posix()
                rows.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
                # Exact original bytes, including JSONL, encoded once within one archive.
                import base64
                z.write((json.dumps(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),base64=base64.b64encode(raw).decode()),separators=(',',':'))+'\n').encode())
        import base64
        parts=[]
        with archive.open('rb') as f:
            index=0
            for chunk in iter(lambda:f.read(256*1024),b''):
                target=dest/('counts_%04d.gz.b64'%index);target.write_bytes(base64.b64encode(chunk))
                parts.append(dict(file=target.name,sha256=sha(target),decoded_bytes=len(chunk)));index+=1
        write(dest/'manifest.json',dict(run_directory=str(base),execution_commit=p['execution_commit'],archive_sha256=sha(archive),archive_parts=parts,
             payload_count=len(rows),original_bytes=sum(r['bytes'] for r in rows),per_file_index='exact path/sha256/bytes within each decompressed JSONL record',
             arrays_weights_logs='server-only, indexed by complete.json and cache receipts',no_training_trigger=True))
        (dest/'summary.json').write_bytes((base/'summary.json').read_bytes())
        subprocess.run(['git','-C',str(work),'add','--',str(prefix)],check=True)
        subprocess.run(['git','-C',str(work),'-c','user.name=66322','-c','user.email=57258129+66322@users.noreply.github.com',
                        'commit','--quiet','-m','Archive Phase2 matched expert and gated fusion evidence'],check=True)
    else:
        if subprocess.check_output(['git','-C',str(work),'status','--porcelain'],text=True).strip():
            raise RuntimeError('existing upload worktree has uncommitted content; preserve and inspect')
    subprocess.run(['git','-C',str(work),'fetch','origin',branch],check=True)
    subprocess.run(['git','-C',str(work),'-c','user.name=66322','-c','user.email=57258129+66322@users.noreply.github.com','rebase','FETCH_HEAD'],check=True)
    subprocess.run(['git','-C',str(work),'push','origin','HEAD:refs/heads/'+branch],check=True)
    commit=subprocess.check_output(['git','-C',str(work),'rev-parse','HEAD'],text=True).strip()
    print('PHASE2_GITHUB_COMMIT',commit)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);main(p.parse_args().directory.resolve())
