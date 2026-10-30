"""Independent lightweight Post-S1 partial record audit; NumPy and stdlib only."""
import argparse,base64,gzip,hashlib,json
from pathlib import Path
import numpy as np
def need(x,msg):
    if not x:raise AssertionError(msg)
def digest(b):return hashlib.sha256(b).hexdigest()
def close(a,b,msg):
    if isinstance(a,dict):
        need(set(a)==set(b),msg+' keys')
        for k in a:close(a[k],b[k],msg+'/'+k)
    elif isinstance(a,list):
        need(len(a)==len(b),msg+' length')
        for x,y in zip(a,b):close(x,y,msg)
    elif isinstance(a,(float,int)) and not isinstance(a,bool):need(b is not None and abs(a-b)<1e-9,msg)
    else:need(a==b,msg)
class Audit:
    def __init__(self,b):
        self.b=b;self.count=dict(read_payloads=0,matrices=0,joints=0,embedded_case_bindings=0,prediction_bindings=0)
        self.man=json.loads((b/'upload_manifest.json').read_text());self.files={x['path']:x for x in self.man['files']}
        self.sources={x['path']:x for x in self.man['source_files']};self.raw={};self.names=[]
        tree=json.loads((b/'git_tree.json').read_text());blobs={x['path']:x for x in tree['tree'] if x['type']=='blob'}
        need(not tree['truncated'] and set(blobs)==set(self.files)|{'upload_manifest.json'},'manifest tree coverage')
        for n,row in self.files.items():need(row['bytes']==blobs[n]['size'],'manifest tree size '+n)
        self.blobs=blobs
    def read(self,n):
        raw=(self.b/n).read_bytes();expected=self.files[n]
        if digest(raw)!=expected['sha256'] and raw.endswith(b'\n'):raw=raw[:-1]
        need(len(raw)==expected['bytes'] and digest(raw)==expected['sha256'],'upload bytes '+n)
        need(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==self.blobs[n]['sha'],'Git blob '+n)
        x=json.loads(raw)
        if isinstance(x,dict) and 'payload_base64' in x and x.get('record_encoding')=='gzip-base64-exact-v1':
            raw=gzip.decompress(base64.b64decode(x['payload_base64'],validate=True))
            need(len(raw)==x['original_bytes'] and digest(raw)==x['original_sha256'],'envelope '+n);x=json.loads(raw)
        if n in self.sources:
            s=self.sources[n];need(len(raw)==s['original_bytes'] and digest(raw)==s['original_sha256'],'original '+n)
        self.raw[n]=digest(raw);self.names.append(n);self.count['read_payloads']+=1;return x
    def metric(self,row):
        cm=np.asarray(row['cm']);need(cm.shape==(6,6) and cm.dtype.kind in 'iu' and (cm>=0).all(),'CM int64')
        cm=cm.astype(np.int64);tp=np.diag(cm);su=cm.sum(1);fp=cm.sum(0)-tp;fn=su-tp;den=tp+fp+fn
        io=[float(tp[i]/den[i]) if den[i] else None for i in range(6)]
        m=lambda ids:float(np.mean([io[i] for i in ids if io[i] is not None])) if any(io[i] is not None for i in ids) else None
        for k,v in dict(support=su.tolist(),TP=tp.tolist(),FP=fp.tolist(),FN=fn.tolist(),IoU=io,mIoU_fg5=m(range(5)),mIoU_6=m(range(6)),valid=int(cm.sum())).items():close(v,row[k],'metric '+k)
        self.count['matrices']+=1;return cm
    def joint(self,j,metrics,region):
        need(j['shape']==[6]*4 and j['dtype']=='int64','joint schema')
        flat=np.zeros(6**4,np.int64);seen=set()
        for i,n in j['nonzero']:
            need(isinstance(i,int) and isinstance(n,int) and 0<=i<6**4 and n>0 and i not in seen,'joint sparse');seen.add(i);flat[i]=n
        v=flat.reshape((6,)*4)
        for name,axis in [('fixed_rgb',1),('fixed_dsm',2),('candidate',3)]:
            axes=tuple(a for a in range(4) if a not in (0,axis))
            need(np.array_equal(v.sum(axes),np.asarray(metrics[name][region]['cm'],np.int64)),'joint marginal '+name)
        self.count['joints']+=1;return v
    def summary(self,s,p,n):
        need(not s['test6_loaded'] and not s['independent_final_loaded'],'final source')
        out={'pooled':{},'tiles':{},'pooled_full':{},'cost':{}}
        for cond,rows in s['tiles'].items():
            need(set(rows)==set(p['data']['validation']),'two tiles');out['tiles'][cond]={};out['cost'][cond]={}
            for t,row in rows.items():
                need(not row.get('test6_loaded',False) and not row.get('independent_final_loaded',False),'case split')
                path=n.rsplit('/',1)[0]+'/'+cond+'/'+t+'.json'
                original=(json.dumps(row,indent=2,allow_nan=False)+'\n').encode()
                need(path in self.sources and digest(original)==self.sources[path]['original_sha256'],'embedded original '+path)
                self.count['embedded_case_bindings']+=1
                if n.startswith('jobs/P') or n.startswith('references/'):
                    need(row['binding']==s['binding'],'case training binding')
                elif n.startswith('jobs/D1/'):
                    need(row['binding']['weight']==s['binding']['weight'] and row['binding']['policy']==s['binding']['policy'],'D1 same weight policy')
                for name,d in row['predictions'].items():
                    root=self.man['server_directory']
                    nn=n.rsplit('/',1)[0]
                    if n.startswith('references/S1-0/'):
                        root=p['source_directory'];nn='jobs/S1-0/'+nn[len('references/S1-0/'):]
                    pp=root+'/'+nn+'/'+cond+'/'+name+'/'+t+'.npy'
                    need(pp in self.artifacts and self.artifacts[pp].get('sha256')==d,'prediction index '+pp)
                    self.count['prediction_bindings']+=1
                out['tiles'][cond][t]=100*row['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']
                out['cost'][cond][t]=row.get('cost')
            for scope in ('full','noboundary'):
                pooled=s['pooled'][cond][scope];sample=next(iter(rows.values()))['scopes'][scope]
                for name,regs in sample['metrics'].items():
                    for region in regs:
                        cms=[self.metric(row['scopes'][scope]['metrics'][name][region]) for row in rows.values()]
                        pc=self.metric(pooled['metrics'][name][region]);need(np.array_equal(sum(cms,np.zeros((6,6),np.int64)),pc),'pooled counts')
                for region in sample['joint']:
                    js=[self.joint(row['scopes'][scope]['joint'][region],row['scopes'][scope]['metrics'],region) for row in rows.values()]
                    pj=self.joint(pooled['joint'][region],pooled['metrics'],region);need(np.array_equal(sum(js,np.zeros((6,)*4,np.int64)),pj),'pooled joint')
                out['pooled' if scope=='noboundary' else 'pooled_full'][cond]=100*pooled['metrics']['candidate']['valid']['mIoU_fg5']
        return out
