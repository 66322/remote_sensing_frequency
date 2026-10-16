"""Read-only metadata inventory for six historical experiments; no array payloads."""
import argparse
import ast
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import stat
import struct
import time

NAMES = [
 'research_post_ab_followup_n2_20261005T085829_3456726',
 'research_d26_bidirectional_20261002T191253_1513109',
 'research_post_n5_20261006T114819_71934',
 'research_post_ab_followup_20261004T185950_3029215',
 'research_d23_b_formal_20261001T152548_658274',
 'research_d30_loss_decomposition_20261003T205144_2349167',
]

def now(): return datetime.now(timezone(timedelta(hours=8))).isoformat()

def header(p):
    # Only the two previously authorized Val2 tile names may be opened.
    if p.name not in ('3_11.npy','5_10.npy'): return None
    with p.open('rb',buffering=0) as f:
        if f.read(6)!=b'\x93NUMPY': return {'error':'not NPY'}
        version=f.read(2)
        if version==b'\x01\x00': n=struct.unpack('<H',f.read(2))[0]
        elif version in (b'\x02\x00',b'\x03\x00'): n=struct.unpack('<I',f.read(4))[0]
        else: return {'error':'unsupported version'}
        if n>65536: return {'error':'oversized header'}
        h=ast.literal_eval(f.read(n).decode('utf-8' if version==b'\x03\x00' else 'latin1'))
    return {k:h.get(k) for k in ('descr','shape','fortran_order')}

def scan(records,name,out):
    base=records/name
    if base.is_symlink() or base.resolve()!=base or not base.is_dir():
        raise RuntimeError('missing or symlink target '+str(base))
    groups=defaultdict(lambda:dict(paths=0,inodes={},samples=[]))
    weights=[];receipts=[];errors=[];skipped_links=0;count=0;tick=time.monotonic()
    print('SCAN_START',name,flush=True)
    with (out/(name+'.jsonl')).open('x',encoding='utf-8') as manifest:
        def onerror(e): errors.append(str(e))
        for folder,dirs,files in os.walk(base,followlinks=False,onerror=onerror):
            kept=[]
            for d in dirs:
                if (Path(folder)/d).is_symlink(): skipped_links+=1
                else: kept.append(d)
            dirs[:]=kept
            for fn in files:
                p=Path(folder)/fn
                try:
                    st=p.lstat()
                    if stat.S_ISLNK(st.st_mode): skipped_links+=1;continue
                    if not stat.S_ISREG(st.st_mode): continue
                    rel=p.relative_to(base);parts=rel.parts
                    section=parts[0] if len(parts)>1 else '(root)'
                    phase=parts[2] if section=='jobs' and len(parts)>3 else '(other)'
                    ext=p.suffix.lower() or '(none)'
                    k=(section,phase,ext);g=groups[k]
                    size=st.st_blocks*512 if hasattr(st,'st_blocks') else st.st_size
                    identity=(st.st_dev,st.st_ino)
                    row=dict(path=str(rel),section=section,phase=phase,extension=ext,
                        device=st.st_dev,inode=st.st_ino,links=st.st_nlink,
                        allocated_bytes=size,size_bytes=st.st_size,mtime_ns=st.st_mtime_ns)
                    manifest.write(json.dumps(row)+'\n')
                    g['paths']+=1;g['inodes'].setdefault(identity,size)
                    if len(g['samples'])<2:
                        sample={'path':str(rel),'size_bytes':st.st_size}
                        if fn in ('3_11.npy','5_10.npy') and section=='jobs': sample['header']=header(p)
                        g['samples'].append(sample)
                    if ext in ('.pth','.pt','.ckpt'): weights.append(row)
                    if fn in ('complete.json','summary.json','plan.json','code_manifest.json'):
                        receipts.append(str(rel))
                    count+=1
                    if time.monotonic()-tick>10:
                        print('SCAN_PROGRESS',name,count,flush=True);tick=time.monotonic()
                except (OSError,ValueError,SyntaxError,struct.error) as e:
                    errors.append(str(p)+': '+str(e))
        manifest.flush()
    report=dict(experiment=name,files=count,groups=[dict(section=k[0],phase=k[1],extension=k[2],
        paths=v['paths'],unique_inodes=len(v['inodes']),allocated_bytes=sum(v['inodes'].values()),samples=v['samples'])
        for k,v in groups.items()],weights=weights,evidence_paths=receipts,errors=errors,skipped_symlinks=skipped_links)
    (out/(name+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('SCAN_DONE',name,'files',count,'errors',len(errors),flush=True)
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    a=p.parse_args();root=a.root.resolve();root.relative_to(Path('/home/jovyan/zzx').resolve())
    records=root/'records'
    if records.resolve()!=records: raise RuntimeError('symlink records')
    out=records/('storage_old_experiments_audit_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()))
    out.mkdir();print('AUDIT_DIRECTORY',out,flush=True)
    (out/'executed_script.py').write_bytes(Path(__file__).read_bytes())
    reports=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks={pool.submit(scan,records,n,out):n for n in NAMES}
        for task in as_completed(tasks):
            try: reports.append(task.result())
            except Exception as e: reports.append(dict(experiment=tasks[task],errors=[str(e)],groups=[]))
    compact=[]
    for r in sorted(reports,key=lambda x:x['experiment']):
        print('\nEXPERIMENT',r['experiment'],flush=True)
        top=sorted(r['groups'],key=lambda x:x['allocated_bytes'],reverse=True)[:10]
        for g in top:
            print('GROUP',g['section'],g['phase'],g['extension'],round(g['allocated_bytes']/1024**3,2),'GiB',g['paths'],'paths',flush=True)
            if g['extension'] in ('.npy','.npz'):
                print('SAMPLES',json.dumps(g['samples']),flush=True)
        compact.append(dict(experiment=r['experiment'],groups=top,errors=r['errors'],
            weights_count=len(r.get('weights',[])),evidence_files=len(r.get('evidence_paths',[]))))
    result=dict(observed_at=now(),read_only=True,workers=3,experiments=compact,
        note='group inode counts deduplicate within group only; do not sum for reclaimable bytes; no completion inferred from file names')
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print('AUDIT_COMPLETE',out,'ERRORS',sum(len(r['errors']) for r in reports),flush=True)

if __name__=='__main__': main()

