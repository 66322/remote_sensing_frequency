"""Explicit retirement after uploaded Phase2 counts verification; no weights removed."""
import argparse
import base64
from collections import Counter
from datetime import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import delete_remaining_val2_predictions as guards
core=guards.core

RUN='research_phase2_matched_20261013T151120_1310582'
EXPECTED=Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records')/RUN
UPLOAD='dc335e0d13d3a1bb4b58e253feaa22cc516275ef'
ARCHIVE_SHA='cc9ea1d202110ebd281e95550d962d13d6adc64a16e0804e833f5f515b38a5e7'
CASES={'average_8000':322,'average_16000':1164,'B0_16000':1164,'B2_16000':1164}
ARRAY_NAMES={'pred','rgb','dsm','entropy_bin','mask','rm','dm'}

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def owned(path,base):return core.safe_file(Path(path),base)
def safe_candidate(rel):
    q=Path(rel)
    if q.is_absolute() or '..' in q.parts:return False
    s=q.parts
    return (len(s)==2 and ((s[0]=='val_cache' and q.suffix=='.npy') or (s[0]=='head_cache' and q.suffix=='.npz'))) or (
        len(s)==4 and s[0]=='evaluation' and s[1] in CASES and q.stem in ARRAY_NAMES and q.suffix=='.npy')
def row_for(p,base):
    owned(p,base);rel=p.relative_to(base)
    if not safe_candidate(rel):raise RuntimeError('outside data retirement whitelist '+str(p))
    st=p.stat()
    if not stat.S_ISREG(st.st_mode):raise RuntimeError('not regular data')
    return dict(path=str(p),relative=str(rel),identity=core.identity(st),links=st.st_nlink,
        allocated_bytes=st.st_blocks*512 if hasattr(st,'st_blocks') else st.st_size)
def unlink(row,base):
    p=Path(row['path']);owned(p,base)
    if not safe_candidate(p.relative_to(base)) or core.identity(p.stat())!=row['identity']:raise RuntimeError('data changed '+str(p))
    p.unlink()

def verified_payloads(base,out):
    archive=base/'upload_counts.jsonl.gz';owned(archive,base)
    print('VERIFY_UPLOAD_ARCHIVE_START',flush=True)
    if sha(archive)!=ARCHIVE_SHA:raise RuntimeError('uploaded archive bytes differ')
    root=base.parent.parent
    raw=subprocess.check_output(['git','-C',str(root),'show',UPLOAD+':records/'+RUN+'/light_evidence/manifest.json'])
    manifest=json.loads(raw)
    if manifest['archive_sha256']!=ARCHIVE_SHA or manifest['run_directory']!=str(base):raise RuntimeError('remote archive contract differs')
    entries={};arrays={};completed=Counter();proofs={};nbytes=0
    binding={n:sha(base/n) for n in ('plan.json','code_manifest.json','prepared.json')}
    with gzip.open(archive,'rb') as f:
        for line in f:
            e=json.loads(line);name=e['path'];rel=Path(name)
            if rel.is_absolute() or '..' in rel.parts or name in entries:raise RuntimeError('unsafe/duplicate evidence')
            payload=base64.b64decode(e['base64'],validate=True)
            if len(payload)!=e['bytes'] or hashlib.sha256(payload).hexdigest()!=e['sha256']:raise RuntimeError('payload SHA differs')
            entries[name]=e['sha256'];nbytes+=len(payload)
            parts=rel.parts
            critical=name in ('plan.json','code_manifest.json','prepared.json','queue_status.json','summary.json','launch.json') or (
                len(parts)==4 and parts[0]=='evaluation' and parts[1] in CASES and parts[-1] in ('counts.json','arrays.json','complete.json')) or name.startswith('analysis/')
            if critical:
                p=base/rel;owned(p,base)
                if sha(p)!=e['sha256']:raise RuntimeError('current evidence changed '+name)
                proofs[name]=e['sha256']
            if len(parts)==4 and parts[0]=='evaluation' and parts[1] in CASES and parts[-1] in ('arrays.json','counts.json','complete.json'):
                data=json.loads(payload)
                if data['binding']!=binding:raise RuntimeError('case binding differs')
                if parts[-1]=='arrays.json':arrays[str(rel.parent)]=data
                if parts[-1]=='counts.json':
                    if data['fallback_exact'] is not True:raise RuntimeError('fallback not verified')
                    for systems in data['matrices'].values():
                        for system in ('rgb','dsm','candidate','oracle','oracle_dsm_priority','availability_oracle'):
                            for cm in systems[system].values():
                                if len(cm)!=6 or any(len(r)!=6 or any(type(x) is not int or x<0 for x in r) for r in cm):raise RuntimeError('invalid retained CM')
                    completed[parts[1]]+=1
            if len(entries)%2000==0:print('VERIFY_PAYLOADS',len(entries),flush=True)
    if len(entries)!=manifest['payload_count'] or nbytes!=manifest['original_bytes'] or dict(completed)!=CASES:raise RuntimeError('incomplete retained evidence')
    for case,data in arrays.items():
        done=read(base/case/'complete.json')
        if done['files'].get('counts.json')!=entries[case+'/counts.json']:raise RuntimeError('counts completion differs')
    core.write(out/'evidence_verification.json',dict(upload_commit=UPLOAD,archive_sha256=ARCHIVE_SHA,
        verified_payloads=len(entries),case_counts=dict(completed),retained_file_sha256=proofs,observed_at=core.stamp()))
    print('VERIFY_UPLOAD_ARCHIVE_COMPLETE',len(entries),flush=True)
    return arrays,entries,binding

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--execute',action='store_true');a=ap.parse_args()
    base=a.directory
    if base!=EXPECTED or base.resolve()!=EXPECTED:raise RuntimeError('only exact Phase2 run is authorized')
    state=read(base/'queue_status.json')
    if state['status']!='PHASE2_COMPLETE_AWAITING_REVIEW':raise RuntimeError('queue not complete')
    import fcntl
    with (base/'artifact_cleanup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        # Hold the original controller lock to exclude any active controller.
        with (base/'controller.lock').open('a') as controller_lock:
            fcntl.flock(controller_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            out=base/('artifact_cleanup_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()));out.mkdir()
            print('CLEANUP_RECEIPT',out,flush=True);shutil.copyfile(__file__,out/'executed_script.py')
            core.NAMES=[RUN];deleted=0
            try:
                guards.no_active_users(base.parent)
                arrays,entries,binding=verified_payloads(base,out)
                paths=set()
                for cache,suffix in (('val_cache','.npy'),('head_cache','.npz')):
                    folder=base/cache
                    if folder.resolve()!=folder:raise RuntimeError('symlink cache')
                    for p in folder.glob('*'+suffix):
                        receipt=p.with_suffix('.json');owned(receipt,base)
                        name=receipt.relative_to(base).as_posix()
                        if name not in entries or sha(receipt)!=entries[name] or read(receipt)['binding']!=binding:raise RuntimeError('unbound cache data '+str(p))
                        paths.add(p)
                for case,data in arrays.items():
                    for name,r in data['arrays'].items():
                        if name not in ARRAY_NAMES or r['path']!=str(base/case/(name+'.npy')):raise RuntimeError('unexpected case array path')
                        p=Path(r['path'])
                        if p.exists():paths.add(p)
                rows=[row_for(p,base) for p in sorted(paths)];groups={}
                for r in rows:groups.setdefault(tuple(r['identity'][:2]),[]).append(r)
                summary=dict(paths=len(rows),unique_inodes=len(groups),
                    unique_allocated_bytes=sum(v[0]['allocated_bytes'] for v in groups.values()),
                    estimated_fully_unlinked_bytes=sum(v[0]['allocated_bytes'] for v in groups.values() if v[0]['links']==len(v)),
                    external_link_inodes=sum(v[0]['links']>len(v) for v in groups.values()),
                    by_section=dict(Counter(Path(r['relative']).parts[0] for r in rows)))
                core.write(out/'plan.json',dict(summary=summary,execute=a.execute,observed_at=core.stamp(),
                    retained='all code/config/counts/JSON/log/weights/input tiles/upload evidence; only cache and compact evaluation arrays retired'))
                with (out/'manifest.jsonl').open('x') as f:
                    for r in rows:f.write(json.dumps(r)+chr(10))
                    f.flush();os.fsync(f.fileno())
                print('SUMMARY',json.dumps(summary),flush=True)
                if not a.execute:return
                guards.no_active_users(base.parent);before=shutil.disk_usage(base).free
                with (out/'deleted.jsonl').open('x') as log:
                    for r in rows:
                        unlink(r,base);log.write(json.dumps(dict(path=r['path'],deleted_at=core.stamp()))+chr(10));deleted+=1
                        if deleted%200==0:
                            log.flush();core.write(out/'progress.json',dict(deleted=deleted,total=len(rows),observed_at=core.stamp()));print('DELETED',deleted,'/',len(rows),flush=True)
                    log.flush();os.fsync(log.fileno())
                core.write(out/'complete.json',dict(deleted=deleted,total=len(rows),disk_free_before=before,
                    disk_free_after=shutil.disk_usage(base).free,observed_at=core.stamp(),note='net volume change includes concurrent activity'))
                core.write(base/'artifact_retirement.json',dict(receipt=str(out),upload_commit=UPLOAD,
                    cache_and_case_arrays_available=False,counts_weights_code_retained=True,
                    original_array_completion_manifests_are_historical=True,
                    consequence='old raw-array SHA paths cannot replay; offline metrics use retained integer counts',observed_at=core.stamp()))
                print('CLEANUP_COMPLETE',deleted,'RECEIPT',out,flush=True)
            except BaseException as e:
                core.write(out/'failure.json',dict(deleted=deleted,error=str(e),automatic_retry=False,observed_at=core.stamp()));raise

if __name__=='__main__':main()
