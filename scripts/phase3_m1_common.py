"""Pure CPU contracts, compact evidence, task scheduling and scoped retirement."""
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import numpy as np

FIT = ['2_12','2_10','7_8','3_12','5_12','7_9','6_9','7_7','4_12','6_8','6_12','6_7']
VAL = ['3_11','5_10']
ARMS = {'M00':('R0',False),'M01':('R0',True),'M10':('R1',False),
        'M11':('R1',True),'M20':('R2',False),'M21':('R2',True),'C21':('R2',True)}
DATA = {}
STATS = {}
def now(): return datetime.now(timezone(timedelta(hours=8))).isoformat()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p, value):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    q=p.with_name(p.name+'.tmp.'+str(os.getpid()))
    q.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n',encoding='utf-8')
    os.replace(q,p)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024**2),b''): h.update(b)
    return h.hexdigest()
def key(*x): return int.from_bytes(hashlib.sha256('|'.join(map(str,x)).encode()).digest()[:8],'big')
def binding(base): return {n:sha(Path(base)/n) for n in ('plan.json','code_manifest.json')}
def scoped(p,root):
    root=Path(root).resolve(); p=Path(p)
    for node in [p,*p.parents]:
        if node==root: break
        if node.is_symlink(): raise RuntimeError('symlink refused: '+str(node))
    out=p.resolve(); out.relative_to(root)
    if out==root: raise RuntimeError('refuse root itself')
    return out
def identity(p):
    s=Path(p).stat(); return [s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns]
def retire(base,target,reason):
    """Only own temporary/cache or rolling optimizer files; never arbitrary run data."""
    base=Path(base).resolve(); target=scoped(target,base); rel=target.relative_to(base)
    allowed=rel.parts[0] in ('temporary','cache','upload_tmp') or (len(rel.parts)==3 and
             rel.parts[0]=='jobs' and rel.name=='last_resume.pth')
    if not allowed: raise RuntimeError('not registered temporary artifact: '+str(rel))
    if not target.exists(): return []
    files=[target] if target.is_file() else sorted((p for p in target.rglob('*') if p.is_file()),key=str)
    rows=[]; seen=set()
    for f in files:
        f=scoped(f,base); before=identity(f); ino=tuple(before[:2])
        rows.append(dict(path=f.relative_to(base).as_posix(),identity=before,
                         unique_bytes=0 if ino in seen else before[2]))
        seen.add(ino)
    receipt=base/'retirement'/(str(key(str(rel),now()))+'.json')
    import shutil
    before_free=shutil.disk_usage(base).free
    write(receipt,dict(status='PREPARED',target=str(rel),reason=reason,files=rows,observed_at=now()))
    try:
        for row in rows:
            f=scoped(base/row['path'],base)
            if identity(f)!=row['identity']: raise RuntimeError('file changed before retirement')
            f.unlink()
        if target.is_dir():
            for d in sorted((p for p in target.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
                scoped(d,base).rmdir()
            target.rmdir()
        write(receipt,dict(status='RETIRED',target=str(rel),reason=reason,files=rows,
              inode_unique_bytes=sum(x['unique_bytes'] for x in rows),disk_free_before=before_free,
              disk_free_after=shutil.disk_usage(base).free,observed_at=now()))
    except BaseException as exc:
        write(receipt,dict(status='FAILED',target=str(rel),reason=reason,files=rows,error=str(exc),observed_at=now()))
        raise
    return rows
def verify(base):
    base=Path(base); p=read(base/'plan.json')
    if read(base/'registration.json')['binding']!=binding(base): raise RuntimeError('binding changed')
    if p['fit12']!=FIT or p['val2']!=VAL or p['gpus']!=[0,1] or p['seeds']!=[42,17]:
        raise RuntimeError('split/GPU/seed contract changed')
    if p['updates']!=16000 or p['batch']!=16 or p['automatic_retry']: raise RuntimeError('budget changed')
    for n,h in read(base/'code_manifest.json')['files'].items():
        if sha(scoped(base/'code'/n,base/'code'))!=h: raise RuntimeError('code changed: '+n)
    return p
def cm(gt,pred,support):
    use=support&(gt<6)
    if np.any(pred[use]>=6): raise ValueError('invalid prediction')
    return np.bincount(gt[use].astype(np.int64)*6+pred[use],minlength=36).reshape(6,6)
def metric(a):
    a=np.asarray(a)
    if a.shape!=(6,6) or not np.issubdtype(a.dtype,np.integer) or (a<0).any(): raise ValueError('invalid CM')
    d=a.sum(0)+a.sum(1)-a.diagonal()
    if (d[:5]==0).any(): return None
    return float(100*(a.diagonal()[:5]/d[:5]).mean())
def joint(gt,r,p,support):
    use=support&(gt<6)
    return np.bincount((gt[use].astype(np.int64)*6+r[use])*6+p[use],minlength=216).reshape(6,6,6)
def flow(j):
    j=np.asarray(j); rescued=harmed=rc=rw=0
    for g in range(5):
        rc+=int(j[g,g,:].sum()); rw+=int(j[g].sum()-j[g,g,:].sum())
        rescued+=int(j[g,:,g].sum()-j[g,g,g]); harmed+=int(j[g,g,:].sum()-j[g,g,g])
    return dict(rgb_correct=rc,rgb_wrong=rw,rescued=rescued,harmed=harmed,
                rescue_rate=rescued/rw if rw else None,harm_rate=harmed/rc if rc else None)
def gate(rows):
    """Only prespecified M21-M11; missing/failed pairs never become a pass."""
    deltas={}; tiles={}
    for seed in (42,17):
        keys=[f'{a}_{seed}' for a in ('M21','M11')]
        if any(k not in rows for k in keys): return None
        if any(rows[k].get('failed') for k in keys): return dict(accepted=False,reason='required_pair_failed')
        ms=[]
        for k in keys:
            a=sum((np.asarray(rows[k]['tiles'][t]['noboundary'],np.int64) for t in VAL))
            ms.append(metric(a))
        if None in ms: return dict(accepted=False,reason='missing_class')
        deltas[str(seed)]=ms[0]-ms[1]
        for t in VAL:
            vs=[metric(np.asarray(rows[k]['tiles'][t]['noboundary'],np.int64)) for k in keys]
            if None in vs: return dict(accepted=False,reason='missing_tile_class')
            tiles[f'{seed}/{t}']=vs[0]-vs[1]
    return dict(accepted=all(x>0 for x in deltas.values()) and np.mean(list(deltas.values()))>=.5
                and min(tiles.values())>=-.2,seed_pooled_gain_pp=deltas,seed_tile_gain_pp=tiles,
                rule='both seed pooled >0; mean >=0.5pp; all seed/tile >=-0.2pp')
def job_list():
    # Pair-relevant jobs first; no GPU/seed affinity barrier.
    return [dict(kind='TRAIN',job=f'{a}_{s}',arm=a,seed=s) for a in
            ('M11','M21','M10','M20','M01','M00') for s in (42,17) if (a,s)!=('M00',42)]

def release_fit(base,owner):
    """Drop only own RAM references after every training consumer has exited."""
    removed={}
    for tile in FIT:
        item=DATA.pop(tile,None)
        if item is not None: removed[tile]=sum(a.nbytes for a in item.values() if hasattr(a,'nbytes'))
    import gc
    gc.collect()
    write(Path(base)/'retirement'/('fit_ram_'+str(owner)+'.json'),dict(owner=owner,logical_array_bytes=removed,
         physical_shared_bytes_not_summed=True,source_disk_files_deleted=False,reason='all training tasks including conditional counter settled',observed_at=now()))

