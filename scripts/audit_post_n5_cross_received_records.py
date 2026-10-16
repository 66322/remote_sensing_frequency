"""Independent JSON/count audit. No project model, training or dataset imports."""
import argparse,base64,gzip,hashlib,json,math
from pathlib import Path,PurePosixPath
import numpy as np
TILES=['3_11','5_10'];MODELS=['N1-2','N2-0','N2-3']
def sha(b):return hashlib.sha256(b).hexdigest()
def close(a,b):
    if isinstance(a,(float,np.floating)) or isinstance(b,(float,np.floating)):
        return a is not None and b is not None and math.isclose(float(a),float(b),rel_tol=0,abs_tol=1e-10)
    if isinstance(a,dict) and isinstance(b,dict):return set(a)==set(b) and all(close(a[k],b[k]) for k in a)
    if isinstance(a,(list,tuple)) and isinstance(b,(list,tuple)):return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
    return a==b
def need(v,msg):
    if not v:raise ValueError(msg)
def metrics(cm):
    a=np.asarray(cm,np.int64);tp=np.diag(a);support=a.sum(1);fp=a.sum(0)-tp;fn=support-tp;u=tp+fp+fn
    iou=[float(tp[i]/u[i]) if u[i] else None for i in range(6)]
    avg=lambda xs:sum(x for x in xs if x is not None)/sum(x is not None for x in xs) if any(x is not None for x in xs) else None
    return dict(cm=a.tolist(),support=support.tolist(),TP=tp.tolist(),FP=fp.tolist(),FN=fn.tolist(),IoU=iou,mIoU_fg5=avg(iou[:5]),mIoU_6=avg(iou),valid=int(a.sum()))
def joint(row):
    need(row['shape']==[6]*4 and row['dtype']=='int64' and row['format']=='sparse_flat_index_count','joint schema')
    a=np.zeros(1296,np.int64);seen=set()
    for i,n in row['nonzero']:
        need(type(i)==int and type(n)==int and 0<=i<1296 and n>0 and i not in seen,'joint count/index')
        seen.add(i);a[i]=n
    return a.reshape([6]*4)
def joint_report(a):
    g,r,d,f=np.indices([6]*4);out={}
    for name,m in [('both_correct',(r==g)&(d==g)),('only_rgb_correct',(r==g)&(d!=g)),('only_dsm_correct',(r!=g)&(d==g)),('both_wrong',(r!=g)&(d!=g))]:
        n=int(a[m].sum());correct=int(a[m&(f==g)].sum())
        out[name]=dict(valid=n,fused_correct=correct,fused_wrong=n-correct,retention=correct/n if n else None,
            by_class={str(c):dict(valid=int(a[m&(g==c)].sum()),fused_correct=int(a[m&(g==c)&(f==g)].sum())) for c in range(6)})
    return out
class Audit:
    def __init__(self,root):
        self.root=root;self.rows={};self.raw={};self.count=dict(payloads=0,matrices=0,joints=0,case_bindings=0,prediction_index_bindings=0,source_code_index_bindings=0)
        self.tree=json.loads((root/'git_tree.json').read_text());self.blobs={x['path']:x for x in self.tree['tree'] if x['type']=='blob'}
        need(not self.tree['truncated'],'truncated Git evidence tree')
        # Local transport can add one final LF: accept only exact Git blob SHA.
        p=root/'upload_manifest.json';raw=p.read_bytes();f=self.blobs['upload_manifest.json']
        def blobsha(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        if blobsha(raw)!=f['sha'] and raw.endswith(b'\n') and blobsha(raw[:-1])==f['sha']:raw=raw[:-1];p.write_bytes(raw)
        need(blobsha(raw)==f['sha'] and len(raw)==f['size'],'manifest Git bytes')
        self.manifest=json.loads(raw);self.files={x['path']:x for x in self.manifest['files']};self.sources={x['path']:x for x in self.manifest['source_files']}
        need(set(self.files)|{'upload_manifest.json'}==set(self.blobs),'manifest path coverage')
        for name,x in self.files.items():need(x['bytes']==self.blobs[name]['size'],'Git size '+name)
    def get(self,name):
        if name in self.rows:return self.rows[name]
        p=self.root/name;raw=p.read_bytes();expected=self.files[name]
        if sha(raw)!=expected['sha256'] and raw.endswith(b'\n') and sha(raw[:-1])==expected['sha256']:raw=raw[:-1];p.write_bytes(raw)
        need(len(raw)==expected['bytes'] and sha(raw)==expected['sha256'],'uploaded bytes '+name)
        value=json.loads(raw)
        if isinstance(value,dict) and value.get('record_encoding')=='gzip-base64-exact-v1':
            raw=gzip.decompress(base64.b64decode(value['payload_base64'],validate=True))
            need(len(raw)==value['original_bytes'] and sha(raw)==value['original_sha256'],'envelope round-trip')
        if name in self.sources:
            source=self.sources[name];need(len(raw)==source['original_bytes'] and sha(raw)==source['original_sha256'],'original bytes '+name)
        self.raw[name]=raw;self.rows[name]=json.loads(raw);self.count['payloads']+=1
        return self.rows[name]
    def check_matrices(self,o,label=''):
        if isinstance(o,dict):
            if 'cm' in o:
                a=np.asarray(o['cm']);need(a.shape==(6,6) and np.issubdtype(a.dtype,np.integer) and (a>=0).all(),'CM '+label);self.count['matrices']+=1
                if 'TP' in o:
                    need(close(o,metrics(a)),'raw metrics '+label)
                else:
                    need(o['support']==int(a.sum()) and o['correct']==int(np.trace(a)),'E3 stratum counts')
            if 'metrics' in o and 'joint' in o:
                encoded='shape' in o['joint'];regions={'x':o['joint']} if encoded else o['joint']
                for region,j in regions.items():
                    a=joint(j);self.count['joints']+=1
                    names=('fixed_rgb','fixed_dsm','candidate') if 'fixed_rgb' in o['metrics'] else ('rgb','dsm','candidate')
                    for name,axes in zip(names,[(2,3),(1,3),(1,2)]):
                        m=o['metrics'][name] if encoded else o['metrics'][name][region]
                        need(np.array_equal(a.sum(axes),m['cm']),'joint marginal '+label)
                    report=o.get('joint_report',o.get('joint_reports'))
                    need(close(joint_report(a),report if encoded else report[region]),'joint quadrants '+label)
                    if encoded and 'anchor_correct_union' in o:
                        g,r,d,f=np.indices([6]*4);m=(g==r)|(g==d);n=int(a[m].sum());harm=int(a[m&(f!=g)].sum())
                        need(close(dict(denominator=n,harm=harm,harm_rate=harm/n if n else None),o['anchor_correct_union']),'anchor union')
            for k,v in o.items():self.check_matrices(v,label+'/'+k)
        elif isinstance(o,list):
            for i,v in enumerate(o):self.check_matrices(v,label+'/'+str(i))
    def run(self):
        # All uploaded light JSONs, not just the summary.
        for name in sorted(self.files):
            if name.endswith('.json') and not name.startswith('code/'):self.get(name)
        for name,o in self.rows.items():self.check_matrices(o,name)
        p=self.get('plan.json');code=self.get('code_manifest.json');prep=self.get('cpu_preparation_complete.json');screen=self.get('cross_screen.json')
        need(p['execution_commit']=='d1ed1a42093c40c979509eac54ba730d89692c1b' and p['new_optimizer_updates']==0 and not p['automatic_training'],'frozen scope')
        need(p['data']['validation']==TILES and not p['data']['test6_loaded'] and not p['data']['independent_final_loaded'] and p['physical_gpus']==[0,1],'scope/devices')
        for key,name in [('plan_sha256','plan.json'),('masks_sha256','mask_manifest.json'),('E3_sha256','e3_screen.json'),('boundary_sha256','boundary_screen.json'),('source_acceptance_sha256','source_acceptance.json')]:
            need(prep[key]==sha(self.raw[name]),'CPU preparation binding')
        for name,digest in code['files'].items():
            if 'code/'+name not in self.sources:
                self.count.setdefault('code_manifest_only_paths',[]).append(name);continue
            src=self.sources['code/'+name];need(digest==src['original_sha256'],'indexed code SHA '+name);self.count['source_code_index_bindings']+=1
        artifacts={x['path']:x for x in self.get('server_artifact_index.json')['artifacts']}
        base=self.manifest['server_directory']
        def rel(path):return str(PurePosixPath(path).relative_to(base))
        data={}
        for model in MODELS:
            job='E4_'+model;summary=self.get('jobs/'+job+'/summary.json');c=self.get('jobs/'+job+'/complete.json');binding=summary['binding']
            need(c['signature']==binding and self.get('jobs/'+job+'/binding.json')==binding,'completion signature')
            need(c['summary_sha256']==sha(self.raw['jobs/'+job+'/summary.json']) and c['inference_tile_units']==64 and c['optimizer_updates']==0 and not c['test6_loaded'] and not c['independent_final_loaded'],'completion SHA/scope')
            need(binding['plan_sha256']==sha(self.raw['plan.json']) and binding['code_manifest_sha256']==sha(self.raw['code_manifest.json']) and binding['mask_manifest_sha256']==sha(self.raw['mask_manifest.json']),'worker binding')
            need(screen['complete_bindings'][job]==sha(self.raw['jobs/'+job+'/complete.json']),'screen complete binding')
            expected={d+'_'+case+'_'+path for d in ('rgb','dsm') for case in ('known_missing','false_positive') for path in p['paths']}
            need(set(summary['records'])==set(summary['tiles'])==set(summary['pooled'])==expected,'complete case coverage')
            rows={}
            for key,ts in summary['records'].items():
                need(set(ts)==set(TILES),'case tile coverage')
                total=np.zeros((6,6),np.int64)
                for tile,ref in ts.items():
                    name=rel(ref['path']);row=self.get(name);rows[key,tile]=row
                    need(ref['sha256']==sha(self.raw[name]) and row['binding']==binding and row['tile']==tile and row['condition']==key,'case binding')
                    need(not row['test6_loaded'] and not row['independent_final_loaded'] and row['optimizer_updates']==0,'case scope')
                    cm=row['scopes']['noboundary']['metrics']['candidate']['all']['cm'];need(cm==summary['tiles'][key][tile],'summary tile CM');total+=np.asarray(cm,np.int64)
                    for n,digest in row['predictions'].items():
                        path=str(PurePosixPath(ref['path']).parent/n/(tile+'.npy'))
                        need(artifacts[path]['sha256']==digest,'prediction artifact index');self.count['prediction_index_bindings']+=1
                    if row['path']=='A1B1C1':
                        need(set(row['original_E2_parity'])=={'candidate','rgb','dsm'} and all(x['array_equal'] for x in row['original_E2_parity'].values()),'original E2 parity metadata')
                    if row['path'].endswith('C1'):need(all(row['fallback_logits_equal_own'].values()),'hard fallback metadata')
                    self.count['case_bindings']+=1
                need(close(metrics(total),summary['pooled'][key]),'independent integer pooled CM')
            for direction in ('rgb','dsm'):
                for case in ('known_missing','false_positive'):
                    for tile in TILES:
                        same=[rows[direction+'_'+case+'_'+path,tile] for path in p['paths']]
                        need(all(r['physical_input_sha256']==same[0]['physical_input_sha256'] and r['reported_mask_sha256']==same[0]['reported_mask_sha256'] for r in same),'physical/report input across paths')
                        for a in (0,1):
                            for b in (0,1):
                                pair=[rows[f'{direction}_{case}_A{a}B{b}C{cc}',tile] for cc in (0,1)]
                                need(all(pair[0]['first_batch_trace'][k]==pair[1]['first_batch_trace'][k] for k in ('expert_rgb','expert_dsm','rgb_feature','dsm_feature','raw_logits')),'C upstream trace')
                for tile in TILES:
                    for b in (0,1):
                        for cc in (0,1):
                            pair=[rows[f'{direction}_known_missing_A{a}B{b}C{cc}',tile] for a in (0,1)]
                            need(pair[0]['predictions']==pair[1]['predictions'],'zero-input A prediction negative control')
                            need(all(pair[0]['first_batch_trace'][k]==pair[1]['first_batch_trace'][k] for k in ('expert_rgb','expert_dsm','rgb_feature','dsm_feature','raw_logits','output_logits')),'zero-input intermediate negative control')
            data[model]=summary
        computed={}
        for factor,better,control in [('output','A1B1C0','A1B1C1'),('feature','A1B0C0','A1B1C0')]:
            directions={}
            for direction in ('rgb','dsm'):
                results={}
                for model,s in data.items():
                    key=lambda x:direction+'_known_missing_'+x
                    tiles={t:100*(metrics(s['tiles'][key(better)][t])['mIoU_fg5']-metrics(s['tiles'][key(control)][t])['mIoU_fg5']) for t in TILES}
                    gain=100*(s['pooled'][key(better)]['mIoU_fg5']-s['pooled'][key(control)]['mIoU_fg5'])
                    results[model]=dict(pooled_gain_pp=gain,tile_gains_pp=tiles,passed=gain>=.5-1e-9 and all(v>0 for v in tiles.values()))
                directions[direction]=results
            computed[factor]=dict(trigger=all(directions['rgb'][m]['passed'] for m in MODELS[:2]),direction='rgb',directions=directions,better=better,control=control)
        need(close(computed,screen['E4']),'independent fixed E4 gates')
        boundary_rows={};boundary_checks={}
        for model in ('N5-0','N5-3'):
            boundary_checks[model]={};boundary_rows[model]={}
            for tile in TILES:
                r=self.get('E0_postN5/'+model+'/'+tile+'.json');sc=r['scopes']['full'];ba=sc['boundary4'];ia=sc['interior']
                b=ba['anchor_correct_union'];inside=ia['anchor_correct_union']
                singles=all(sum(x['joint_report'][name]['valid'] for x in (ba,ia))>=100 for name in ('only_rgb_correct','only_dsm_correct'))
                supported=b['denominator']>=100 and inside['denominator']>=100 and singles
                gap=100*(b['harm_rate']-inside['harm_rate'])
                checks=dict(supported=supported,boundary_minus_interior_harm_pp=gap,passed=supported and gap>=1.-1e-9)
                need(close(checks,self.get('boundary_screen.json')['models'][model]['checks'][tile]),'original N5 boundary gate')
                boundary_checks[model][tile]=checks;boundary_rows[model][tile]=dict(boundary=b,interior=inside)
        boundary=all(x['passed'] for rows in boundary_checks.values() for x in rows.values())
        need(boundary==screen['N3_problem_trigger']==self.get('boundary_screen.json')['N3_problem_trigger'],'boundary screen')
        e3={}
        for model in ('A0','B1','N5-0','N5-3'):
            e3[model]={}
            for direction in ('rgb','dsm'):
                e3[model][direction]={}
                for tile in TILES:
                    r=self.get('E3/'+model+'/'+direction+'/'+tile+'.json');st=r['standardized'];weights=st['weight_counts'];strata=r['strata']
                    keys=[k for k in weights if all(x[k]['support']>=100 for x in strata.values())]
                    mass=sum(weights[k] for k in keys);total=sum(weights.values());w={k:weights[k]/mass for k in keys}
                    accuracy={rule:sum(w[k]*x[k]['correct']/x[k]['support'] for k in keys) for rule,x in strata.items()}
                    need(st['common_strata']==keys and close(w,st['normalized_weights']) and close(accuracy,st['standardized_accuracy']) and close(mass/total,st['covered_weight_fraction']),'E3 standardization')
                    # Exactly same full-tile weights for all models and directions.
                    if model!='A0' or direction!='rgb':
                        first=self.get('E3/A0/rgb/'+tile+'.json')['standardized']['weight_counts'];need(weights==first,'E3 common label weights')
                    e3[model][direction][tile]=dict(accuracy=accuracy,U_minus_H_accuracy_pp=100*(accuracy['U']-accuracy['H']),U_minus_L_accuracy_pp=100*(accuracy['U']-accuracy['L']),covered_weight_fraction=mass/total)
        next_f=[f for f,v in [('R1',computed['output']['trigger']),('N3',boundary),('S1',computed['feature']['trigger'])] if v][:2]
        need(next_f==screen['recommended_next_families']==['N3','S1'],'prospective family selection')
        return dict(status='PASS',source_commit='f60491fc1091eb7d272e081e821d9e6397aa9c82',counts=self.count,
            manifest_payloads=len(self.files),git_blobs=len(self.blobs),E4=computed,N3_boundary_checks=boundary_checks,N3_boundary_counts=boundary_rows,E3=e3,
            next_families=next_f,scope='239 JSONs independently decoded and SHA checked, all 352 manifest payload paths/sizes; no server arrays/checkpoints/mask bodies or GPU replay; trace/parity verified as recorded hashes/booleans',
            first_batch_trace_scope='native first batch only, not whole-tile activations',optimizer_updates=0)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,default=Path(__file__).parent/'received');ap.add_argument('--output',type=Path,default=Path(__file__).parent/'analysis/audit_result.json');a=ap.parse_args()
    result=Audit(a.directory).run();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('CROSS_INDEPENDENT_AUDIT',result['status'],result['counts'],result['next_families'])
if __name__=='__main__':main()
