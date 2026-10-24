"""Retire audited fixed-budget predictions from the first cleanup's skipped list."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import time
import delete_historical_val2_predictions as core

SOURCE = 'storage_prediction_cleanup_20261013T192501_1424574'
PHASES = {'fixed8000', 'support_fixed8000', 'initial_evaluation', 'stress_evaluation'}

def select(records, text):
    p = Path(text)
    rel = p.relative_to(records)
    if '..' in rel.parts or len(rel.parts) < 6 or rel.parts[0] not in core.NAMES or rel.parts[1] != 'jobs':
        raise ValueError('outside five historical jobs: ' + text)
    if rel.parts[-1] not in ('3_11.npy', '5_10.npy'):
        raise ValueError('not a Val2 prediction: ' + text)
    return rel.parts[0], rel.parts[3] in PHASES

def inventory(records, paths, progress=lambda *a: None):
    rows, groups, skipped, missing = [], {}, [], []
    if len(set(paths)) != len(paths):
        raise RuntimeError('duplicate paths in source receipt')
    for i, text in enumerate(paths, 1):
        name, accepted = select(records, text)
        if not accepted:
            skipped.append(text)
            continue
        p = Path(text)
        core.safe_file(p, records/name/'jobs')
        try:
            st = p.stat()
        except FileNotFoundError:
            missing.append(text)
            continue
        if not stat.S_ISREG(st.st_mode):
            raise RuntimeError('not regular: ' + text)
        inode = (st.st_dev, st.st_ino)
        if inode not in groups:
            core.prediction_header(p)
        row = dict(path=text, experiment=name, identity=core.identity(st), links=st.st_nlink,
                   allocated_bytes=st.st_blocks*512 if hasattr(st, 'st_blocks') else st.st_size)
        rows.append(row)
        groups.setdefault(inode, []).append(row)
        if i % 200 == 0:
            progress('INVENTORY', i, len(paths))
    summary = dict(paths=len(rows), unique_inodes=len(groups),
        unique_allocated_bytes=sum(v[0]['allocated_bytes'] for v in groups.values()),
        estimated_fully_unlinked_bytes=sum(v[0]['allocated_bytes'] for v in groups.values() if v[0]['links']==len(v)),
        external_link_inodes=sum(v[0]['links']>len(v) for v in groups.values()),
        missing_path_count=len(missing), skipped_path_count=len(skipped))
    return rows, summary, skipped, missing

def no_active_users(records):
    targets = [str(records/n) for n in core.NAMES]
    def check(value, pid):
        if any(t in value for t in targets):
            raise RuntimeError('historical experiment in use by PID ' + pid)
    print('PROCESS_AUDIT_START', flush=True)
    count = 0
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name)==os.getpid():
            continue
        try:
            with (proc/'cmdline').open('rb') as f:
                raw=f.read(4*1024*1024+1)
            if len(raw)>4*1024*1024:
                raise RuntimeError('oversized cmdline: '+proc.name)
            check(raw.decode(errors='replace'),proc.name)
            total=0
            with (proc/'maps').open('r',errors='replace') as f:
                for line in f:
                    total+=len(line)
                    if total>64*1024*1024:
                        raise RuntimeError('oversized maps: '+proc.name)
                    check(line,proc.name)
            for fd in (proc/'fd').iterdir():
                try: check(os.readlink(fd),proc.name)
                except FileNotFoundError: pass
        except (FileNotFoundError, ProcessLookupError):
            continue
        count+=1
        if count%100==0:
            print('PROCESS_AUDIT',count,flush=True)
    print('PROCESS_AUDIT_COMPLETE',count,flush=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--execute',action='store_true')
    a=ap.parse_args()
    root=a.root.resolve()
    root.relative_to(Path('/home/jovyan/zzx').resolve())
    records=root/'records'
    if records.is_symlink(): raise RuntimeError('symlink records')
    source=records/SOURCE
    if source.is_symlink(): raise RuntimeError('symlink source receipt')
    plan_raw=(source/'plan.json').read_bytes()
    plan=json.loads(plan_raw)
    done=json.loads((source/'complete.json').read_text())
    if done['deleted']!=31956 or done['total']!=31956 or plan['targets']!=core.NAMES:
        raise RuntimeError('unexpected first cleanup receipt')
    paths=plan['summary']['skipped_paths']
    if len(paths)!=21876: raise RuntimeError('unexpected skipped count')
    import fcntl
    with (records/'historical_prediction_cleanup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        receipt=records/('storage_prediction_cleanup_second_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()))
        receipt.mkdir()
        print('CLEANUP_RECEIPT',receipt,flush=True)
        for file in (Path(__file__),Path(core.__file__)):
            shutil.copyfile(file,receipt/file.name)
        count=0
        def progress(phase,n,total):
            print(phase,n,'/',total,flush=True)
            core.write(receipt/'progress.json',dict(phase=phase,completed=n,total=total,observed_at=core.stamp()))
        try:
            no_active_users(records)
            rows,summary,skipped,missing=inventory(records,paths,progress)
            core.write(receipt/'remaining_paths.json',dict(skipped=skipped,missing=missing))
            with (receipt/'manifest.jsonl').open('x',encoding='utf-8') as f:
                for row in rows: f.write(json.dumps(row)+'\n')
                f.flush();os.fsync(f.fileno())
            core.write(receipt/'plan.json',dict(summary=summary,source_receipt=str(source),
                source_plan_sha256=hashlib.sha256(plan_raw).hexdigest(),phases=sorted(PHASES),
                manifest_sha256=hashlib.sha256((receipt/'manifest.jsonl').read_bytes()).hexdigest(),
                observed_at=core.stamp(),execute=a.execute))
            print('SUMMARY',json.dumps(summary),flush=True)
            examples=defaultdict(list)
            for text in skipped:
                rel=Path(text).relative_to(records)
                key=rel.parts[0]+'/'+rel.parts[3]
                if len(examples[key])<2: examples[key].append(str(rel))
            print('REMAINING_SAMPLES',json.dumps(examples),flush=True)
            if not a.execute: return
            no_active_users(records)
            before=shutil.disk_usage(records).free
            with (receipt/'deleted.jsonl').open('x',encoding='utf-8') as log:
                for row in rows:
                    core.unlink_one(row,records)
                    log.write(json.dumps(dict(path=row['path'],deleted_at=core.stamp()))+'\n')
                    count+=1
                    if count%200==0:
                        log.flush();progress('DELETED',count,len(rows))
                log.flush();os.fsync(log.fileno())
            core.write(receipt/'complete.json',dict(deleted=count,total=len(rows),observed_at=core.stamp(),
                disk_free_before=before,disk_free_after=shutil.disk_usage(records).free,
                note='volume net change; concurrent writes and external hardlinks affect reclamation'))
            for name in core.NAMES:
                core.write(records/name/('prediction_retirement_'+receipt.name+'.json'),dict(
                    receipt_directory=str(receipt),retired_paths=sum(r['experiment']==name for r in rows),
                    checkpoint_and_metrics_retained=True,observed_at=core.stamp()))
            print('CLEANUP_COMPLETE',count,'RECEIPT',receipt,flush=True)
        except BaseException as exc:
            core.write(receipt/'failure.json',dict(deleted=count,error=str(exc),automatic_retry=False,observed_at=core.stamp()))
            raise

if __name__=='__main__': main()
