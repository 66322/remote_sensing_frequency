import concurrent.futures, gzip, hashlib, json, time, urllib.request,subprocess,tarfile,io
from pathlib import Path

B=Path(__file__).parent
R=B/'received'; R.mkdir(parents=True,exist_ok=True)
COMMIT='57ef5ad9e5238f69f94c5d8ede00023a20499144'
PREFIX='records/research_post_t_mechanism_20261011T094823_3625851/evidence_20261011T135206766012_3747898'
URL=f'https://raw.githubusercontent.com/66322/remote_sensing_frequency/{COMMIT}/{PREFIX}/'
def fetch(name):
    p=R/name
    local=B/'github'/PREFIX/name
    if local.exists():
        raw=local.read_bytes().replace(b'\r\n',b'\n');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);return raw
    if p.exists():return p.read_bytes()
    for n in range(4):
        try:
            raw=urllib.request.urlopen(URL+name,timeout=90).read()
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);return raw
        except Exception:
            if n==3:raise
            time.sleep(n+1)
def decoded(raw):
    v=json.loads(raw)
    if isinstance(v,dict) and v.get('record_encoding')=='gzip-base64-exact-v1':
        import base64
        out=gzip.decompress(base64.b64decode(v['payload_base64'],validate=True))
        assert len(out)==v['original_bytes'] and hashlib.sha256(out).hexdigest()==v['original_sha256']
        return out
    return raw
def one(row):
    raw=fetch(row['path'])
    assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],row['path']
    out=decoded(raw) if row['path'].endswith('.json') else raw
    p=B/'decoded'/row['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(out)
    return len(raw),len(out)
if __name__=='__main__':
    man=json.loads(fetch('upload_manifest.json'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        results=list(ex.map(one,man['files']))
    for row in man['source_files']:
        raw=(B/'decoded'/row['path']).read_bytes()
        assert len(raw)==row['original_bytes'] and hashlib.sha256(raw).hexdigest()==row['original_sha256'],row['path']
    listing=subprocess.check_output(['git','-C',str(B/'github'),'ls-tree','-r','--long',COMMIT,PREFIX],text=True)
    blobs={}
    for line in listing.splitlines():
        meta,path=line.split('\t',1);mode,kind,digest,size=meta.split();blobs[path[len(PREFIX)+1:]]=(digest,int(size))
    assert set(blobs)=={r['path'] for r in man['files']}|{'upload_manifest.json'}
    for name,(digest,size) in blobs.items():
        raw=(R/name).read_bytes()
        assert len(raw)==size and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+raw).hexdigest()==digest,name
    (B/'git_blob_index.json').write_text(json.dumps(blobs,indent=2)+'\n')
    report=dict(commit=COMMIT,prefix=PREFIX,payloads=len(results),git_blobs_verified=len(blobs),uploaded_bytes=sum(x[0] for x in results),decoded_bytes=sum(x[1] for x in results),source_files=len(man['source_files']),all_upload_sha_verified=True,all_source_sha_verified=True)
    (B/'receipt_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
