"""Third cleanup: receipt-bound historical predictions, retaining raw counts."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import os
import shutil
import stat
import audit_old_experiment_storage as audit
import delete_remaining_val2_predictions as previous
core=previous.core
SOURCE='storage_old_experiments_audit_20261013T200442_1456518'
PHASES={'evaluation','fixed8000','content_evaluation','content_fixed8000'}

def allowed(rel):
    p=Path(rel)
    if p.is_absolute() or '..' in p.parts: raise ValueError('unsafe relative path')
    q=p.parts
    if len(q)<6 or q[0]!='jobs' or q[-1] not in ('3_11.npy','5_10.npy'): return False
    return (len(q)==6 and q[2] in PHASES) or (len(q)==8 and q[2]=='modes' and q[4]=='evaluation')

def has_counts(x):
    if isinstance(x,dict):
        for k,v in x.items():
            if k in ('cm','confusion_matrix') and isinstance(v,list) and len(v)==6:
                if all(isinstance(row,list) and len(row)==6 and all(type(a) is int and a>=0 for a in row) for row in v): return True
            if has_counts(v): return True
    elif isinstance(x,list):
        return any(has_counts(v) for v in x)
    return False

def inventory(records,source):
    rows=[];groups={};skipped=[];proofs={};seen=set()
    for name in audit.NAMES:
        report=source/(name+'.json');core.safe_file(report,source)
        r=json.loads(report.read_text())
        if r['errors']: raise RuntimeError('audit errors '+name)
        manifest=source/(name+'.jsonl');core.safe_file(manifest,source)
        with manifest.open() as f:
            for line in f:
                old=json.loads(line)
                if not allowed(old['path']): continue
                p=records/name/old['path'];base=records/name/'jobs';core.safe_file(p,base)
                if str(p) in seen: raise RuntimeError('duplicate audit path')
                seen.add(str(p))
                if not p.exists(): skipped.append(dict(path=str(p),reason='already_missing'));continue
                st=p.stat()
                expected=[old['device'],old['inode'],old['size_bytes'],old['mtime_ns']]
                if core.identity(st)!=expected or not stat.S_ISREG(st.st_mode): raise RuntimeError('changed since audit '+str(p))
                evidence=p.parent.parent/(p.stem+'.json');core.safe_file(evidence,base)
                if str(evidence) not in proofs:
                    if not evidence.is_file(): skipped.append(dict(path=str(p),reason='missing_metrics'));continue
                    raw=evidence.read_bytes()
                    if not has_counts(json.loads(raw)):
                        skipped.append(dict(path=str(p),reason='no_integer_6x6_counts'));continue
                    proofs[str(evidence)]=hashlib.sha256(raw).hexdigest()
                key=(st.st_dev,st.st_ino)
                if key not in groups: core.prediction_header(p)
                row=dict(path=str(p),experiment=name,identity=expected,links=st.st_nlink,
                    allocated_bytes=st.st_blocks*512 if hasattr(st,'st_blocks') else st.st_size)
                rows.append(row);groups.setdefault(key,[]).append(row)
                if len(rows)%200==0: print('INVENTORY',len(rows),flush=True)
        print('EXPERIMENT_CHECKED',name,flush=True)
    summary=dict(paths=len(rows),unique_inodes=len(groups),
        unique_allocated_bytes=sum(v[0]['allocated_bytes'] for v in groups.values()),
        estimated_fully_unlinked_bytes=sum(v[0]['allocated_bytes'] for v in groups.values() if v[0]['links']==len(v)),
        external_link_inodes=sum(v[0]['links']>len(v) for v in groups.values()),skipped_paths=len(skipped),metrics_files=len(proofs))
    return rows,summary,skipped,proofs

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--execute',action='store_true');a=ap.parse_args()
    root=a.root.resolve();root.relative_to(Path('/home/jovyan/zzx').resolve());records=root/'records';source=records/SOURCE
    if records.resolve()!=records or source.resolve()!=source: raise RuntimeError('symlink receipt path')
    import fcntl
    with (records/'historical_prediction_cleanup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        out=records/('storage_prediction_cleanup_third_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()));out.mkdir()
        print('CLEANUP_RECEIPT',out,flush=True)
        for module in (Path(__file__),Path(core.__file__),Path(previous.__file__),Path(audit.__file__)):
            shutil.copyfile(module,out/module.name)
        core.NAMES=list(audit.NAMES);count=0
        try:
            previous.no_active_users(records)
            rows,summary,skipped,proofs=inventory(records,source)
            core.write(out/'plan.json',dict(source=str(source),summary=summary,metrics_sha256=proofs,skipped=skipped,
                source_manifest_sha256={n:hashlib.sha256((source/(n+'.jsonl')).read_bytes()).hexdigest() for n in audit.NAMES},
                execute=a.execute,observed_at=core.stamp()))
            with (out/'manifest.jsonl').open('x') as f:
                for row in rows:f.write(json.dumps(row)+'\n')
                f.flush();os.fsync(f.fileno())
            print('SUMMARY',json.dumps(summary),flush=True)
            if not a.execute:return
            previous.no_active_users(records)
            for path,h in proofs.items():
                if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=h: raise RuntimeError('metrics changed '+path)
            before=shutil.disk_usage(records).free
            with (out/'deleted.jsonl').open('x') as log:
                for row in rows:
                    core.unlink_one(row,records);log.write(json.dumps(dict(path=row['path'],deleted_at=core.stamp()))+'\n');count+=1
                    if count%200==0:
                        log.flush();core.write(out/'progress.json',dict(deleted=count,total=len(rows),observed_at=core.stamp()));print('DELETED',count,'/',len(rows),flush=True)
                log.flush();os.fsync(log.fileno())
            core.write(out/'complete.json',dict(deleted=count,total=len(rows),disk_free_before=before,
                disk_free_after=shutil.disk_usage(records).free,observed_at=core.stamp(),note='net volume change includes concurrent activity'))
            for name in audit.NAMES:
                core.write(records/name/('prediction_retirement_'+out.name+'.json'),dict(receipt=str(out),
                    deleted=sum(r['experiment']==name for r in rows),metrics_and_weights_retained=True,observed_at=core.stamp()))
            print('CLEANUP_COMPLETE',count,'RECEIPT',out,flush=True)
        except BaseException as e:
            core.write(out/'failure.json',dict(deleted=count,error=str(e),automatic_retry=False,observed_at=core.stamp()));raise

if __name__=='__main__':main()
