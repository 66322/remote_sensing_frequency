"""Read-only fixed-commit download and independent SHA validation; no source execution."""
import base64, concurrent.futures, gzip, hashlib, json, time, urllib.request
from pathlib import Path, PurePosixPath
ROOT=Path(__file__).resolve().parent
COMMIT='09fb57a6ec26f6367c9891f2aa924cc4bf7219cc'
PREFIX='records/research_phase3_m1_recovery_20261015T164357_19327/compact_evidence'
def digest(data): return hashlib.sha256(data).hexdigest()
def get(name):
    for i in range(3):
        try:
            with urllib.request.urlopen('https://raw.githubusercontent.com/66322/remote_sensing_frequency/'+COMMIT+'/'+PREFIX+'/'+name,timeout=90) as r: return r.read()
        except Exception:
            if i==2: raise
            time.sleep(2)
def main():
    m=json.loads((ROOT/'manifest.json').read_text()); parts=ROOT/'parts'; parts.mkdir(exist_ok=True)
    if json.loads(get('manifest.json'))!=m: raise RuntimeError('fixed-commit manifest differs')
    def download(row):
        p=parts/row['file']
        data=p.read_bytes() if p.exists() else get(row['file'])
        if digest(data)!=row['sha256'] or len(data)!=row['decoded_bytes']: raise RuntimeError('part differs '+row['file'])
        if not p.exists(): p.write_bytes(data)
        return p
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for i,p in enumerate(pool.map(download,m['parts']),1): print('PART_VERIFIED',i,'/',len(m['parts']),flush=True)
    archive=ROOT/'core.jsonl.gz'; h=hashlib.sha256()
    with archive.open('wb') as out:
        for row in m['parts']:
            data=(parts/row['file']).read_bytes(); h.update(data); out.write(data)
    if h.hexdigest()!=m['archive_sha256']: raise RuntimeError('archive differs')
    target=ROOT/'evidence'; target.mkdir(exist_ok=True); inventory={}; total=0
    with gzip.open(archive,'rt',encoding='utf-8') as f:
        for line in f:
            z=json.loads(line); name=z['path']; posix=PurePosixPath(name)
            if posix.is_absolute() or '..' in posix.parts or ':' in name or '\\' in name: raise RuntimeError('invalid payload path')
            if name in inventory: raise RuntimeError('duplicate payload')
            data=base64.b64decode(z['base64'],validate=True)
            if len(data)!=z['bytes'] or digest(data)!=z['sha256']: raise RuntimeError('payload differs '+name)
            p=target/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(data)
            inventory[name]={'bytes':len(data),'sha256':z['sha256']}; total+=len(data)
    if len(inventory)!=m['payload_files'] or total!=m['raw_bytes']: raise RuntimeError('payload inventory differs')
    for name in ('summary.json','result_verification.json','queue_status.json'):
        if get(name)!=(target/name).read_bytes(): raise RuntimeError('direct summary differs '+name)
    receipt={'commit':COMMIT,'archive_sha256':h.hexdigest(),'parts_verified':len(m['parts']),
             'files_verified':len(inventory),'raw_bytes_verified':total,'direct_summaries_exact':True,'files':inventory}
    (ROOT/'archive_verification.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ARCHIVE_VERIFIED',len(inventory),'FILES',total,'BYTES',flush=True)
if __name__=='__main__': main()
