"""Explicit user-authorized retirement of five historical Val2 prediction trees."""
import argparse
import ast
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import struct

NAMES = [
 'research_post_d30_mechanisms_20261004T000812_2446364',
 'research_post_n3_s1_20261007T083203_694293',
 'research_post_s1_support_20261008T234921_1890161',
 'research_post_s1_transfer_20261010T073327_2852696',
 'research_d27_safe_routing_repair_20261003T092243758628_2001983',
]

def stamp():return datetime.now(timezone(timedelta(hours=8))).isoformat()
def write(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(tmp,path)

def safe_file(path,base):
    if base.resolve()!=base:raise RuntimeError('symlink ancestor in jobs path')
    relative=path.relative_to(base)
    current=base
    if base.is_symlink():raise RuntimeError('symlink base')
    for part in relative.parts:
        current=current/part
        if current.is_symlink():raise RuntimeError('symlink path '+str(current))
    resolved=path.resolve();resolved.relative_to(base.resolve())
    return resolved

def prediction_header(path):
    with path.open('rb') as f:
        if f.read(6)!=b'\x93NUMPY':raise RuntimeError('not NPY '+str(path))
        version=f.read(2)
        if version==b'\x01\x00':length=struct.unpack('<H',f.read(2))[0]
        elif version in (b'\x02\x00',b'\x03\x00'):length=struct.unpack('<I',f.read(4))[0]
        else:raise RuntimeError('unsupported NPY header')
        if length>65536:raise RuntimeError('unexpected large NPY header')
        header=ast.literal_eval(f.read(length).decode('utf-8' if version==b'\x03\x00' else 'latin1'))
        if header.get('descr')!='|u1' or header.get('shape')!=(6000,6000):
            raise RuntimeError('not the audited uint8 Val2 prediction '+str(path))
        expected=f.tell()+36000000
    if path.stat().st_size!=expected:raise RuntimeError('unexpected NPY byte count')

def identity(st):return [st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns]

def inventory(records):
    rows=[];groups={};skipped=[]
    for name in NAMES:
        base=records/name/'jobs'
        if not base.is_dir() or base.is_symlink():raise RuntimeError('missing/unsafe jobs '+str(base))
        for folder,dirs,files in os.walk(base,followlinks=False):
            dirs[:]=[n for n in dirs if not (Path(folder)/n).is_symlink()]
            for n in files:
                if n not in ('3_11.npy','5_10.npy'):continue
                path=Path(folder)/n;relative=path.relative_to(base)
                if len(relative.parts)<4 or relative.parts[1] not in ('evaluation','support_evaluation'):
                    skipped.append(str(path));continue
                safe_file(path,base);st=path.stat()
                if not stat.S_ISREG(st.st_mode):raise RuntimeError('not regular file')
                inode=(st.st_dev,st.st_ino)
                if inode not in groups:prediction_header(path)
                row=dict(path=str(path),experiment=name,identity=identity(st),links=st.st_nlink,
                         allocated_bytes=st.st_blocks*512 if hasattr(st,'st_blocks') else st.st_size)
                rows.append(row);groups.setdefault(inode,[]).append(row)
    complete_links=sum(v[0]['allocated_bytes'] for v in groups.values() if v[0]['links']==len(v))
    summary=dict(paths=len(rows),unique_inodes=len(groups),unique_allocated_bytes=sum(v[0]['allocated_bytes'] for v in groups.values()),
        estimated_fully_unlinked_bytes=complete_links,external_link_inodes=sum(v[0]['links']>len(v) for v in groups.values()),
        skipped_paths=skipped)
    return rows,summary

def no_active_users(records):
    targets=[str(records/n) for n in NAMES]
    if not Path('/proc').is_dir():raise RuntimeError('Linux process checks required')
    def matches(value):return any(t in value for t in targets)
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
        try:
            if matches((proc/'cmdline').read_bytes().decode(errors='replace')):
                raise RuntimeError('old experiment process is live: '+proc.name)
            if matches((proc/'maps').read_text(errors='replace')):
                raise RuntimeError('old experiment file is mapped: '+proc.name)
            for fd in (proc/'fd').iterdir():
                try:value=os.readlink(fd)
                except FileNotFoundError:continue
                if matches(value):raise RuntimeError('old experiment open file: '+proc.name+' '+value)
        except FileNotFoundError:continue
        except PermissionError as exc:raise RuntimeError('cannot complete process audit: '+proc.name) from exc

def unlink_one(row,records):
    path=Path(row['path']);base=records/row['experiment']/'jobs';safe_file(path,base)
    if identity(path.stat())!=row['identity']:raise RuntimeError('prediction changed since inventory: '+str(path))
    path.unlink()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    root=args.root.resolve();root.relative_to(Path('/home/jovyan/zzx').resolve());records=root/'records'
    import fcntl
    with (records/'historical_prediction_cleanup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        no_active_users(records);rows,summary=inventory(records)
        receipt=records/('storage_prediction_cleanup_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()))
        receipt.mkdir();shutil.copyfile(__file__,receipt/'executed_script.py')
        manifest=receipt/'deletion_manifest.jsonl'
        with manifest.open('x',encoding='utf-8') as f:
            for row in rows:f.write(json.dumps(row,ensure_ascii=False)+'\n')
            f.flush();os.fsync(f.fileno())
        write(receipt/'plan.json',dict(observed_at=stamp(),targets=NAMES,execute=args.execute,summary=summary,
            manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),archive_created=False,
            keep='all pth/json/jsonl/log/source/masks/shared_reference and current Phase2',
            consequence='historical prediction SHA paths retired; pixel-level replay needs new inference',
            authorization='user explicitly rejected compression and authorized deleting unneeded historical files'))
        print('CLEANUP_RECEIPT',receipt,flush=True);print(json.dumps(summary),flush=True)
        if not args.execute:print('PREVIEW_ONLY NO_DELETION');return
        no_active_users(records);before=shutil.disk_usage(records).free;count=0
        try:
            with (receipt/'deleted.jsonl').open('x',encoding='utf-8') as log:
                for row in rows:
                    unlink_one(row,records);log.write(json.dumps(dict(path=row['path'],deleted_at=stamp()))+'\n');count+=1
                    if count%200==0:
                        log.flush();write(receipt/'progress.json',dict(deleted=count,total=len(rows),observed_at=stamp()))
                log.flush()
            write(receipt/'complete.json',dict(deleted=count,total=len(rows),disk_free_before=before,
                disk_free_after=shutil.disk_usage(records).free,observed_at=stamp(),
                note='free-space change also includes concurrent Phase2 writes; externally linked bytes stay allocated'))
            for name in NAMES:
                write(records/name/('prediction_retirement_'+receipt.name+'.json'),
                    dict(receipt_directory=str(receipt),retired_paths=sum(row['experiment']==name for row in rows),
                         original_prediction_files_available=False,checkpoint_and_metrics_retained=True,
                         observed_at=stamp(),reason='explicit user-authorized deletion without archival'))
            print('CLEANUP_COMPLETE',count,'RECEIPT',receipt,flush=True)
        except BaseException as exc:
            write(receipt/'failure.json',dict(deleted=count,error=str(exc),observed_at=stamp(),automatic_retry=False));raise

if __name__=='__main__':main()
