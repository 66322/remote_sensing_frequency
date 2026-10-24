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
    def run(self):
        p=self.read('plan.json');snap=self.read('completed_snapshot.json');q=self.read('queue_status.json');code=self.read('code_manifest.json');masks=self.read('mask_manifest.json');prep=self.read('preparation_complete.json')
        self.artifacts={a['path']:a for a in self.read('server_artifact_index.json')['artifacts']}
        need(p['execution_commit']==code['commit']=='2c5e7d6f383cfe454415d4e106179930264f1141','execution')
        need(p['physical_gpus']==[0] and p['max_gpu_workers']==1 and p['training']['seed']==42 and p['training']['primary_checkpoint_step']==8000,'GPU/seed/step')
        need(p['data']['validation']==['3_11','5_10'] and not p['data']['test6_loaded'] and not p['data']['independent_final_loaded'] and not p['test_release'],'source')
        need(prep['plan_sha256']==masks['plan_sha256']==self.raw['plan.json'] and prep['mask_manifest_sha256']==self.raw['mask_manifest.json'],'prep binding')
        need(snap['queue_last_observed']==q['observed_at'] and snap['included_jobs']==['D1','P6','P7','P8','P9','P4','P5','P2'],'membership')
        need(snap['excluded_jobs']=={'P3':'RUNNING','P0':'PENDING','P1':'PENDING','E':'PENDING'} and not snap['scientific_final_gate_available'],'pending')
        for j in snap['excluded_jobs']:need(not any(n.startswith('jobs/'+j+'/') for n in self.files),'excluded records '+j)
        science=[n for n in self.files if n.startswith('code/') and 'post_s1_support' in n]
        need(len(science)==12,'12 sources')
        for n in science:
            raw=(self.b/n).read_bytes();expected=code['files'][n[5:]]
            need(digest(raw)==expected==self.sources[n]['original_sha256'],'science hash '+n)
            remote=(self.b.parent/'execution_source'/n[5:]).read_bytes()
            need(raw==remote,'science execution equality '+n)
        ordinary={};U={};capacity={};completes={};protection={}
        for j in snap['included_jobs'][1:]:
            prefix='jobs/'+j;c=self.read(prefix+'/complete.json');completes[j]=c;sig=c['signature']
            need(c['global_step']==c['optimizer_updates']==c['selected']['step']==8000 and c['selected']['selection']=='prospectively fixed8000','fixed selection '+j)
            card=next(x for x in p['jobs'] if x['id']==j)
            need(sig['job']==card and sig['physical_gpu']==0 and sig['plan_sha256']==self.raw['plan.json'] and sig['code_manifest_sha256']==self.raw['code_manifest.json'] and sig['mask_manifest_sha256']==self.raw['mask_manifest.json'] and sig['initial_checkpoint_sha256']==p['initial_checkpoint']['sha256'],'complete binding '+j)
            need(self.raw[prefix+'/complete.json']==snap['completed_bindings'][j]['complete_sha256'],'snapshot complete')
            for tag in ['evaluation','fixed8000','support_evaluation']:
                n=prefix+'/'+tag+'/summary.json';s=self.read(n)
                need(s['binding']['training']==sig and s['binding'].get('checkpoint_sha256',s['binding'].get('selected',{}).get('checkpoint_sha256'))==c['selected']['checkpoint_sha256'],'summary selected '+n)
                result=self.summary(s,p,n)
                if tag=='evaluation':ordinary[j]=result
                elif tag=='support_evaluation':U[j]=result
                else:
                    need(set(result['pooled'])==set(p['fixed_conditions']),'22 fixed conditions')
                    for k in result['pooled']:close(result['pooled'][k],ordinary[j]['pooled'][k],'selected/fixed score')
                need(self.raw[n]==c['artifacts'][tag+'/summary.json'],'complete summary SHA')
            need(len(ordinary[j]['pooled'])==32 and set(U[j]['pooled'])=={'rgb_U','dsm_U'},'conditions')
            for name in ['model_capacity.json','input_binding.json']:
                x=self.read(prefix+'/'+name);need(self.raw[prefix+'/'+name]==c['artifacts'][name],'artifact digest')
                if name=='model_capacity.json':capacity[j]=x
            for step in (4000,8000):
                v=self.read(prefix+'/validation/step_'+str(step)+'.json');need(v['step']==step,'validation step')
                need(v['binding']['training']==sig and v['binding']['step']==step,'validation binding')
                if step==8000:need(v['binding']['checkpoint_sha256']==c['selected']['checkpoint_sha256'],'validation checkpoint')
                for k,rows in v['tiles'].items():
                    cms=[self.metric(row) for row in rows.values()];cm=sum(cms,np.zeros((6,6),np.int64));tp=np.diag(cm);den=cm.sum(0)+cm.sum(1)-tp
                    val=float(np.mean(tp[:5]/den[:5]));close(val,v['state_metrics'][k],'validation states')
                close(sum(v['state_metrics'].values())/3,v['score'],'validation score')
                if step==8000:close(v['score'],c['selected']['metric'],'selected metric')
            if card['frozen_base'] and card['local_only']:
                x=self.read(prefix+'/protection.json');need(x['base_parameter_digest_equal'] and x['native_prediction_outside_support_equal'] and x['initial_base_sha256']==x['final_base_sha256'],'frozen local protection');protection[j]=x
            for name,sha in c['artifacts'].items():
                if name.endswith('.pth'):need(self.artifacts[self.man['server_directory']+'/'+prefix+'/'+name]['sha256']==sha,'checkpoint index')
            env=self.read(prefix+'/environment.json');need(env['physical_batch']==16 and env['input_manifest_sha256']==p['input_manifest_sha256'] and not env['test6_loaded'] and not env['independent_final_loaded'],'environment scope')
        base={}
        bc=self.read('references/S1-0/complete.json');need(bc['selected']['step']==8000 and bc['selected']['checkpoint_sha256']==p['initial_checkpoint']['sha256'],'base8000')
        for tag in ['evaluation','fixed8000','support_evaluation','support_fixed8000']:
            n='references/S1-0/'+tag+'/summary.json';s=self.read(n);need(s['binding'].get('checkpoint_sha256',s['binding'].get('selected',{}).get('checkpoint_sha256'))==p['initial_checkpoint']['sha256'],'base summary binding');base[tag]=self.summary(s,p,n)
        route={tag:self.summary(self.read(tag+'/summary.json'),p,tag+'/summary.json') for tag in ['R0_U','R0_ordinary']}
        dc=self.read('jobs/D1/complete.json');dindex=self.read('jobs/D1/summary.json');need(dc['optimizer_updates']==0 and self.raw['jobs/D1/summary.json']==dc['artifacts']['summary.json'],'D1 zero updates digest')
        need(self.raw['jobs/D1/complete.json']==snap['completed_bindings']['D1']['complete_sha256'],'D1 completion binding')
        D1={}
        for name,entry in dindex['records'].items():
            n=entry['path'].split(self.man['server_directory']+'/')[1];s=self.read(n);need(self.raw[n]==entry['sha256'],'D1 index SHA')
            need(s['binding']['weight']['checkpoint_sha256']==p['reference_shas'][name.split('/')[0]] and s['binding']['optimizer_updates']==0,'D1 checkpoint')
            D1[name]=self.summary(s,p,n)
        d0={};dindex0=self.read('d0_index.json')
        for name,entry in dindex0['records'].items():
            n=entry['path'].split(self.man['server_directory']+'/')[1];s=self.read(n);need(self.raw[n]==entry['sha256'] and not s['test6_loaded'],'D0 index')
            need(s['control']['binding']['checkpoint_sha256']==p['reference_shas']['S1-0'] and s['candidate']['binding']['checkpoint_sha256']==p['reference_shas'][name.split('/')[0]],'D0 weights')
            for scope,regions in s['regions'].items():
                for reg,r in regions.items():
                    ctrl=self.metric(r['control']);cand=self.metric(r['candidate'])
                    need(r['valid']==r['rescued']+r['harmed']+r['both_correct']+r['both_wrong']==int(ctrl.sum())==int(cand.sum()),'D0 denominator')
                    need(int(np.trace(cand)-np.trace(ctrl))==r['rescued']-r['harmed'],'D0 net')
                    for cl,by in r['by_class'].items():
                        i=int(cl);need(by['valid']==int(ctrl[i].sum())==int(cand[i].sum()) and by['rescued']-by['harmed']==int(cand[i,i]-ctrl[i,i]),'D0 per class')
                    for k in ('valid','rescued','harmed'):need(sum(x[k] for x in r['by_class'].values())==r[k],'D0 class pool')
                for names in [('missing_inside','missing_outside'),('label_boundary4','label_interior'),('exclusive_label_edge','exclusive_missing_edge','exclusive_missing_inside','exclusive_other')]:
                    for key in ('valid','rescued','harmed','both_correct','both_wrong'):need(sum(regions[x][key] for x in names)==regions['all'][key],'D0 partition')
            d0[name]={k:{reg:{x:r[x] for x in ['valid','rescued','harmed','both_correct','both_wrong']} for reg,r in regs.items()} for k,regs in s['regions'].items()}
        r0s=self.read('R0_U/summary.json')
        for t in p['data']['validation']:
            d=self.read('D0/S1-3/rgb_U/'+t+'.json')
            for scope in ('full','noboundary'):
                rr=d['regions'][scope]
                composed=np.asarray(rr['missing_inside']['candidate']['cm'],np.int64)+np.asarray(rr['missing_outside']['control']['cm'],np.int64)
                need(np.array_equal(composed,np.asarray(r0s['tiles']['rgb_U'][t]['scopes'][scope]['metrics']['candidate']['valid']['cm'],np.int64)),'R0 observable splice count composition')
        def compare(a,b,k,floor=0,both=False):
            pooled=a['pooled'][k]-b['pooled'][k];tiles={t:a['tiles'][k][t]-b['tiles'][k][t] for t in p['data']['validation']}
            return dict(pooled_gain_pp=pooled,tile_gains_pp=tiles,threshold_pp=floor,passed=bool(pooled>=floor-1e-9 and (not both or all(v>0 for v in tiles.values()))))
        g=p['design']['gates'];rgb={'base':compare(U['P7'],base['support_evaluation'],'rgb_U',g['rgb_base_pp'],True)}
        rgb.update({j:compare(U['P7'],U[j],'rgb_U',g['mechanism_pp'],True) for j in ['P6','P8','P9']});rgb['R0']=compare(U['P7'],route['R0_U'],'rgb_U',g['route_floor_pp'])
        protect={k:compare(ordinary['P7'],base['evaluation'],k,g['clean_missing_floor_pp']) for k in ['clean','rgb_missing','dsm_missing']}
        worst=lambda a,b:min([dict(condition=k,tile=t,gain_pp=a['tiles'][k][t]-b['tiles'][k][t]) for k in p['evaluation']['primary'] for t in p['data']['validation']],key=lambda x:x['gain_pp'])
        wt=worst(ordinary['P7'],base['evaluation']);dsm=compare(U['P7'],base['support_evaluation'],'dsm_U',g['dsm_U_floor_pp'])
        passU=all(x['passed'] for x in rgb.values()) and all(x['passed'] for x in protect.values()) and wt['gain_pp']>=g['worst_tile_floor_pp']-1e-9 and dsm['passed']
        paired={a+'-'+b:{k:compare(U[a],U[b],k) for k in ['rgb_U','dsm_U']} for a,b in [('P7','P6'),('P5','P4'),('P6','P4'),('P7','P5'),('P6','P2')]}
        arms={j:dict(rgb_U=U[j]['pooled']['rgb_U'],dsm_U=U[j]['pooled']['dsm_U'],S_available=sum(ordinary[j]['pooled'][k] for k in p['evaluation']['primary'])/10,worst_primary_tile=worst(ordinary[j],base['evaluation']),clean_missing={k:compare(ordinary[j],base['evaluation'],k) for k in ['clean','rgb_missing','dsm_missing']},vs_base_U={k:compare(U[j],base['support_evaluation'],k) for k in ['rgb_U','dsm_U']},effective_branch_updates=completes[j]['treatment_counts']['branch_nonzero_updates'],capacity=capacity[j],U_inference_cost=U[j]['cost']) for j in ordinary}
        signal=compare(D1['S1-0/A1B0C0'],D1['S1-0/A1B1C1'],'dsm_U',g['D1_DSM_signal_pp'],True)
        result=dict(status='PASS',evidence_commit='77d3970fdfcf3d72524f8c31ff412110196161a6',count=self.count,manifest_payloads=len(self.files),included=snap['included_jobs'],excluded=snap['excluded_jobs'],snapshot=snap,primary_candidate='P7',P7_U_protection_passed=bool(passU),P7=dict(rgb=rgb,protection=protect,worst_primary_tile=wt,dsm_U=dsm),E_status='NOT_RECEIVED',final_gate_passed=False,final_gate_status='NOT_AVAILABLE; failed U/protection alone can reject candidate',Q_signal=signal,Q_auto_training=False,Q_eligible=False,D1_same_weight_invariants=dindex['same_weight_invariants'],D1_scores={n:{k:r['pooled'][k] for k in ['rgb_U','dsm_U']} for n,r in D1.items()},D1_policy_effects={j:{k:compare(D1[j+'/A1B0C0'],D1[j+'/A1B1C1'],k) for k in ['rgb_U','dsm_U']} for j in p['reference_shas']},paired_available=paired,per_arm=arms,base=dict(rgb_U=base['support_evaluation']['pooled']['rgb_U'],dsm_U=base['support_evaluation']['pooled']['dsm_U'],S_available=sum(base['evaluation']['pooled'][k] for k in p['evaluation']['primary'])/10),R0={k:dict(pooled=v['pooled'],tiles=v['tiles']) for k,v in route.items()},protection=protection,D0_counts=d0,decoded_original_sha256=self.raw,scope='Val2 seed42 development; no GPU reproduction; arrays/checkpoints server-only; snapshot array bodies not rehashed')
        return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--received',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    result=Audit(a.received).run();a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8');print(json.dumps({k:result[k] for k in ['status','count','P7_U_protection_passed','P7','Q_signal','base']},indent=2))
