"""Reuse the verified compact archive; Git Data API writes, no Git fetch/clone."""
import argparse
import base64
import getpass
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO='66322/remote_sensing_frequency'
BRANCH='rebuild-v1-protocol-20260915'
RUN='research_phase3_m1_recovery_20261015T164357_19327'
BINDING={'plan.json':'3bf0d81cadcaeb75e0b14c9c24cdeecabe87bad6e190513d1d3799c4876fc5b0',
         'code_manifest.json':'c2c4dab784d1a14719910fcc162672a557c6a77bbb0c2fa9b98d4865f136a02a'}
PART_BYTES=2*1024**2

def sha(data): return hashlib.sha256(data).hexdigest()
def gitsha(data): return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''): h.update(b)
    return h.hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path,value):
    p=Path(path); tmp=p.with_name(p.name+'.tmp.'+str(os.getpid()))
    tmp.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n',encoding='utf-8'); os.replace(tmp,p)
def encode(value): return (json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode()

def stage_live_processes(stage):
    """Read-only guard against deleting a surviving old Git child's working directory."""
    stage=Path(stage).resolve(); found=[]; proc=Path('/proc')
    if not proc.exists(): return found
    for p in proc.iterdir():
        if not p.name.isdigit() or int(p.name)==os.getpid(): continue
        try:
            cwd=Path(os.readlink(p/'cwd')).resolve()
            if cwd==stage or stage in cwd.parents: found.append(int(p.name))
        except (OSError,ProcessLookupError): pass
    return found

class ApiError(RuntimeError):
    def __init__(self,status,message): self.status=status; super().__init__('GitHub API '+str(status)+': '+message)

class Api:
    def __init__(self,token): self.token=token
    def call(self,method,path,value=None):
        if not path.startswith('/repos/'+REPO+'/'): raise RuntimeError('unexpected API destination')
        data=None if value is None else json.dumps(value,separators=(',',':')).encode()
        for attempt in range(3):
            request=urllib.request.Request('https://api.github.com'+path,data=data,method=method,
                headers={'Authorization':'Bearer '+self.token,'Accept':'application/vnd.github+json',
                         'Content-Type':'application/json','User-Agent':'phase3-m1-compact-archive',
                         'X-GitHub-Api-Version':'2026-03-10'})
            try:
                with urllib.request.urlopen(request,timeout=120) as r: return json.load(r)
            except urllib.error.HTTPError as exc:
                try: message=json.loads(exc.read()).get('message','request failed')
                except (ValueError,UnicodeDecodeError): message='request failed'
                # Never log request headers, token, or complete error payloads.
                if exc.code not in (429,500,502,503,504) or attempt==2: raise ApiError(exc.code,message) from None
            except (urllib.error.URLError,TimeoutError):
                if attempt==2: raise RuntimeError('GitHub connection failed; checkpoints retained, token not saved') from None
            print('NETWORK_RETRY',method,path.split('/git/')[-1],flush=True); time.sleep(2**(attempt+1))
    def head(self): return self.call('GET','/repos/'+REPO+'/git/ref/heads/'+BRANCH)['object']['sha']
    def manifest(self,commit,prefix):
        path='/repos/'+REPO+'/contents/'+prefix+'/manifest.json?ref='+commit
        try: row=self.call('GET',path)
        except ApiError as exc:
            if exc.status==404: return None
            raise
        if row.get('encoding')!='base64': raise RuntimeError('unexpected remote manifest encoding')
        return json.loads(base64.b64decode(row['content']))

def raw(commit,path):
    if not re.fullmatch('[0-9a-f]{40}',commit) or '..' in Path(path).parts: raise RuntimeError('unexpected readback path')
    url='https://raw.githubusercontent.com/'+REPO+'/'+commit+'/'+urllib.parse.quote(path,safe='/')
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url,timeout=120) as r: return r.read()
        except (urllib.error.URLError,TimeoutError):
            if attempt==2: raise RuntimeError('remote readback failed; local archive retained') from None
            time.sleep(2**(attempt+1))

def archive_parts(archive):
    with Path(archive).open('rb') as f:
        for i,data in enumerate(iter(lambda:f.read(PART_BYTES),b'')):
            yield f'core_{i:03d}.gz.part',data

def put_blob(api,prefix,name,data,checkpoint,checkpoint_path):
    path=prefix+'/'+name; expected=gitsha(data)
    if checkpoint['blobs'].get(path)==expected: return expected
    row=api.call('POST','/repos/'+REPO+'/git/blobs',{'encoding':'base64','content':base64.b64encode(data).decode('ascii')})
    if row['sha']!=expected: raise RuntimeError('uploaded Git blob SHA differs: '+name)
    checkpoint['blobs'][path]=expected; write(checkpoint_path,checkpoint)
    return expected

def publish(api,entries,prefix,archive_hash,binding):
    """Fresh base tree plus our paths only; force=false, no historical blob download."""
    for attempt in range(4):
        head=api.head(); existing=api.manifest(head,prefix)
        if existing:
            if existing.get('archive_sha256')!=archive_hash or existing.get('binding')!=binding:
                raise RuntimeError('remote run archive already differs; refuse overwrite')
            return head,existing
        parent=api.call('GET','/repos/'+REPO+'/git/commits/'+head)
        tree=api.call('POST','/repos/'+REPO+'/git/trees',{'base_tree':parent['tree']['sha'],'tree':entries})['sha']
        commit=api.call('POST','/repos/'+REPO+'/git/commits',{
            'message':'Archive Phase3-M1 compact evidence via API without historical checkout',
            'tree':tree,'parents':[head]})['sha']
        if api.head()!=head: print('BRANCH_ADVANCED_REBASE_METADATA_ONLY',flush=True); continue
        try:
            updated=api.call('PATCH','/repos/'+REPO+'/git/refs/heads/'+BRANCH,{'sha':commit,'force':False})
            if updated['object']['sha']!=commit: raise RuntimeError('unexpected branch update response')
            return commit,None
        except (ApiError,RuntimeError) as exc:
            observed=api.head()
            if observed==commit: return commit,None
            if observed!=head:
                print('BRANCH_RACE_RETRY_METADATA_ONLY',flush=True); continue
            raise exc
    raise RuntimeError('branch kept advancing; uploaded blobs/checkpoints retained, no force push')

def readback(commit,prefix,manifest,archive_hash,small,get=None):
    if get is None: get=raw
    remote=get(commit,prefix+'/manifest.json')
    if json.loads(remote)!=manifest: raise RuntimeError('remote manifest differs')
    h=hashlib.sha256(); binary=manifest.get('part_encoding')=='binary'
    for i,row in enumerate(manifest['parts'],1):
        name=row['file']
        if not re.fullmatch(r'core_\d{3}\.gz\.(?:part|b64)',name): raise RuntimeError('unexpected archive part name')
        data=get(commit,prefix+'/'+name)
        if sha(data)!=row['sha256']: raise RuntimeError('remote part SHA differs '+name)
        decoded=data if binary else base64.b64decode(data,validate=True)
        if len(decoded)!=row['decoded_bytes']: raise RuntimeError('remote part length differs')
        h.update(decoded); print('READBACK_PART',i,'/',len(manifest['parts']),flush=True)
    if h.hexdigest()!=archive_hash: raise RuntimeError('remote reconstructed archive differs')
    for name,data in small.items():
        if get(commit,prefix+'/'+name)!=data: raise RuntimeError('remote summary differs '+name)

def upload(base,commit,api,c,prepared,archive):
    checkpoint_path=base/'upload_api_checkpoint.json'
    context={'archive_sha256':prepared['archive_sha256'],'binding':c.binding(base),'part_bytes':PART_BYTES}
    checkpoint=read(checkpoint_path) if checkpoint_path.exists() else dict(context,blobs={})
    if any(checkpoint.get(k)!=v for k,v in context.items()): raise RuntimeError('API checkpoint binding changed')
    prefix='records/'+base.name+'/compact_evidence'
    small={name:(base/name).read_bytes() for name in ('summary.json','result_verification.json','queue_status.json')}
    head=api.head(); existing=api.manifest(head,prefix); verify_only=bool(existing)
    if existing:
        if existing.get('archive_sha256')!=prepared['archive_sha256'] or existing.get('binding')!=c.binding(base):
            raise RuntimeError('existing remote archive differs; preserve both, no overwrite')
        final=head; manifest=existing; print('EXISTING_REMOTE_ARCHIVE_VERIFY_ONLY',flush=True)
    else:
        entries=[]; parts=[]; total=(archive.stat().st_size+PART_BYTES-1)//PART_BYTES
        for i,(name,data) in enumerate(archive_parts(archive),1):
            blob=put_blob(api,prefix,name,data,checkpoint,checkpoint_path)
            entries.append(dict(path=prefix+'/'+name,mode='100644',type='blob',sha=blob))
            parts.append(dict(file=name,sha256=sha(data),decoded_bytes=len(data)))
            print('UPLOAD_PART',i,'/',total,'BINARY_MIB',round(len(data)/1024**2,2),flush=True)
        manifest=dict(binding=c.binding(base),execution_commit=c.read(base/'plan.json')['execution_commit'],
            parts=parts,part_encoding='binary',archive_sha256=prepared['archive_sha256'],
            payload_files=len(prepared['files']),raw_bytes=sum(x['bytes'] for x in prepared['files']),
            scientific_evidence='all groups including failures; joint counts and streams, no model/raw/pixel files',
            new_training_trigger=False,transport='Git Data API; no Git fetch/clone',
            uploader_commit=commit,uploader_sha256=file_sha(Path(__file__)))
        for name,data in dict(small,**{'manifest.json':encode(manifest)}).items():
            blob=put_blob(api,prefix,name,data,checkpoint,checkpoint_path)
            entries.append(dict(path=prefix+'/'+name,mode='100644',type='blob',sha=blob))
        final,remote_manifest=publish(api,entries,prefix,prepared['archive_sha256'],c.binding(base))
        if remote_manifest is not None: manifest=remote_manifest; verify_only=True
        write(base/'upload_api_committed.json',dict(commit=final,archive_sha256=prepared['archive_sha256'],parts=len(manifest['parts'])))
        print('COMMITTED',final,'READBACK_START',flush=True)
    readback(final,prefix,manifest,prepared['archive_sha256'],small)
    receipt=dict(commit=final,archive_sha256=prepared['archive_sha256'],all_parts_readback=True,
        parts=len(manifest['parts']),transport='existing remote archive verification only' if verify_only else 'Git Data API; no Git fetch/clone',
        uploader_commit=commit,uploader_sha256=file_sha(Path(__file__)),observed_at=c.now())
    write(base/'github_upload_receipt.json',receipt)
    # The caller still holds upload.lock. Retire only this run's upload copy AFTER verified readback.
    live=stage_live_processes(base/'upload_tmp')
    if live:
        print('CLEANUP_DEFERRED_STAGE_HAS_LIVE_PROCESSES',live,flush=True)
        print('PHASE3_M1_GITHUB_COMMIT',final,'UPLOAD_TEMP_RETAINED',flush=True)
    else:
        c.retire(base,base/'upload_tmp','API commit acknowledged and every part read back; prepared archive and old Git download no longer needed')
        print('PHASE3_M1_GITHUB_COMMIT',final,'UPLOAD_TEMP_RETIRED',flush=True)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--directory',type=Path,required=True); p.add_argument('--commit',required=True); args=p.parse_args()
    base=args.directory.resolve(); base.relative_to(Path('/home/jovyan/zzx').resolve())
    if base.name!=RUN or not re.fullmatch('[0-9a-f]{40}',args.commit): raise RuntimeError('identified run and fixed uploader commit required')
    os.environ['CUDA_VISIBLE_DEVICES']=''; os.environ['PYTHONDONTWRITEBYTECODE']='1'
    sys.path.insert(0,str(base/'code/scripts')); sys.path.insert(0,str(base/'code'))
    import fcntl
    import phase3_m1_common as c
    from upload_phase3_m1 import evidence_files
    with (base/'upload.lock').open('a') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError('original uploader still running; no second uploader started') from None
        if (base/'github_upload_receipt.json').exists(): print((base/'github_upload_receipt.json').read_text()); return
        live=stage_live_processes(base/'upload_tmp')
        if live: raise RuntimeError('old upload-stage processes still present '+str(live)+'; no second uploader started')
        with (base/'controller.lock').open('a') as compute_lock: fcntl.flock(compute_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        c.verify(base)
        if c.binding(base)!=BINDING or c.read(base/'queue_status.json')['status']!='COMPLETE_AWAITING_REVIEW': raise RuntimeError('expected completed bound run')
        verification=c.read(base/'result_verification.json')
        if not verification['all_required_evidence_complete'] or verification['missing_or_failed']: raise RuntimeError('complete self-verification required')
        prepared=c.read(base/'upload_prepared.json'); archive=base/'upload_tmp/core.jsonl.gz'
        current=[dict(path=f.relative_to(base).as_posix(),bytes=f.stat().st_size,sha256=c.sha(f)) for f in evidence_files(base)]
        if prepared['binding']!=c.binding(base) or prepared['files']!=current or file_sha(archive)!=prepared['archive_sha256']:
            raise RuntimeError('prepared evidence/archive changed; preserve and inspect, no silent repack')
        print('REUSE_PREPARED_ARCHIVE',len(current),'FILES',round(archive.stat().st_size/1024**2,2),'MiB; NO_GIT_FETCH_NO_GPU',flush=True)
        print('Only this archive is uploaded; API base64 adds about 1/3; readback downloads this archive once.',flush=True)
        if not sys.stdin.isatty(): raise RuntimeError('foreground terminal required for one-use token; do not pipe or nohup')
        token=getpass.getpass('GitHub token (Contents write; hidden, not saved): ').strip()
        if not token: raise RuntimeError('no token supplied; original archive retained')
        api=Api(token)
        try: upload(base,args.commit,api,c,prepared,archive)
        finally: api.token=''; token=''

if __name__=='__main__':
    try: main()
    except KeyboardInterrupt: print('\nUPLOAD_INTERRUPTED; prepared archive/checkpoints retained; experiment unchanged',flush=True); sys.exit(130)
    except Exception as exc: print('UPLOAD_STOPPED:',str(exc),'; archive/checkpoints retained until verified readback',flush=True); sys.exit(1)
