"""Independent lightweight N3/S1 record audit; NumPy and stdlib only."""
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
    def summary(self,s,p,n,signature,checkpoint):
        need(not s['test6_loaded'] and not s['independent_final_loaded'],'final source')
        need(s['binding']['training']==signature,'summary training')
        ck=s['binding'].get('checkpoint_sha256',s['binding'].get('selected',{}).get('checkpoint_sha256'));need(ck==checkpoint,'summary checkpoint')
        out={'pooled':{},'tiles':{},'pooled_full':{}}
        for cond,rows in s['tiles'].items():
            need(set(rows)==set(p['data']['validation']),'two tiles');out['tiles'][cond]={}
            for t,row in rows.items():
                need(row['binding']==s['binding'],'case binding')
                path=n.rsplit('/',1)[0]+'/'+cond+'/'+t+'.json'
                original=(json.dumps(row,indent=2,allow_nan=False)+'\n').encode()
                need(path in self.sources and digest(original)==self.sources[path]['original_sha256'],'embedded original case '+path)
                self.count['embedded_case_bindings']+=1
                for name,d in row['predictions'].items():
                    pp=self.man['server_directory']+'/'+n.rsplit('/',1)[0]+'/'+cond+'/'+name+'/'+t+'.npy'
                    need(pp in self.artifacts and self.artifacts[pp].get('sha256')==d,'prediction index');self.count['prediction_bindings']+=1
                out['tiles'][cond][t]=100*row['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5']
            for scope in ('full','noboundary'):
                pooled=s['pooled'][cond][scope];sample=next(iter(rows.values()))['scopes'][scope]
                for name,regs in sample['metrics'].items():
                    for region in regs:
                        cms=[self.metric(row['scopes'][scope]['metrics'][name][region]) for row in rows.values()]
                        pc=self.metric(pooled['metrics'][name][region]);need(np.array_equal(sum(cms,np.zeros((6,6),np.int64)),pc),'pooled integer counts')
                for region in sample['joint']:
                    js=[self.joint(row['scopes'][scope]['joint'][region],row['scopes'][scope]['metrics'],region) for row in rows.values()]
                    pj=self.joint(pooled['joint'][region],pooled['metrics'],region);need(np.array_equal(sum(js,np.zeros((6,)*4,np.int64)),pj),'pooled joint')
                if scope=='noboundary':out['pooled'][cond]=100*pooled['metrics']['candidate']['valid']['mIoU_fg5']
                else:out['pooled_full'][cond]=100*pooled['metrics']['candidate']['valid']['mIoU_fg5']
        return out
    def run(self):
        p=self.read('plan.json');screen=self.read('n3_s1_screen.json');q=self.read('queue_status.json');code=self.read('code_manifest.json');mask=self.read('mask_manifest.json');prep=self.read('preparation_complete.json')
        artifact=self.read('server_artifact_index.json');self.artifacts={a['path']:a for a in artifact['artifacts']}
        need(p['execution_commit']==code['commit']=='0e22438a7131a0a1f28098e675c3367d40236398','execution commit')
        need(p['data']['validation']==['3_11','5_10'] and p['physical_gpus']==[0,1] and not p['data']['test6_loaded'] and not p['data']['independent_final_loaded'],'scope')
        need(p['total_optimizer_steps']==72000 and p['training']['seed']==42,'budget seed')
        need(mask['plan_sha256']==prep['plan_sha256']==self.raw['plan.json'] and prep['mask_manifest_sha256']==self.raw['mask_manifest.json'] and not mask['T_read'] and prep['optimizer_updates']==0,'mask preparation')
        data={};caps={};selected={}
        for job in p['jobs']:
            j=job['id'];f='jobs/'+j;c=self.read(f+'/complete.json');sig=c['signature']
            need(c['global_step']==8000 and sig['job']==job and sig['sources']==code['files'] and sig['plan_sha256']==self.raw['plan.json'] and sig['execution_commit']==p['execution_commit'],'complete '+j)
            need(sig['initial_checkpoint_sha256']==p['initial_checkpoint']['sha256']=='28bc6f8ca5e1221392598b0a6f2d160e8c633a6a9cf63827067df3e7b81a144b' and sig['mask_manifest_sha256']==self.raw['mask_manifest.json'],'base mask')
            need(not c['test6_loaded'] and not c['independent_final_loaded'],'final scope')
            for file,key in [('selected.pth','selected_checkpoint_sha256'),('last_train_state.pth','last_checkpoint_sha256')]:
                need(self.artifacts[self.man['server_directory']+'/'+f+'/'+file]['sha256']==c[key],'checkpoint index')
            vals=[]
            for step in (4000,8000):
                v=self.read(f+'/validation/step_'+str(step)+'.json');need(v['step']==step and v['binding']['training']==sig and not v['test6_loaded'],'selection binding')
                states={}
                for cond,rows in v['tiles'].items():
                    cms=[self.metric(r) for r in rows.values()];cm=sum(cms,np.zeros((6,6),np.int64));tp=np.diag(cm);den=cm.sum(0)+cm.sum(1)-tp
                    states[cond]=float(np.mean((tp/den)[:5]))
                close(states,v['state_metrics'],'selection state');mean=float(np.mean(list(states.values())));close(mean,v['score'],'selection score');vals.append((mean,step,v))
            best=max(vals,key=lambda x:(x[0],-x[1]));need(best[1]==c['selected']['step'],'selected age');close(best[0],c['selected']['metric'],'selected metric');close(best[2]['state_metrics'],c['selected']['state_metrics'],'selected state')
            selected[j]=best[1];caps[j]=self.read(f+'/model_capacity.json');data[j]={}
            for tag in ('evaluation','fixed8000','support_evaluation','support_fixed8000'):
                n=f+'/'+tag+'/summary.json';s=self.read(n);need(self.raw[n]==c[tag+'_summary_sha256'],'complete summary sha')
                ck=c['selected_checkpoint_sha256'] if tag in ('evaluation','support_evaluation') else s['binding']['checkpoint_sha256']
                data[j][tag]=self.summary(s,p,n,sig,ck);del s
            need(set(data[j]['evaluation']['pooled'])==set(data[p['jobs'][0]['id']]['evaluation']['pooled']),'ordinary condition set')
            need(set(data[j]['fixed8000']['pooled'])==set(p['fixed_conditions']),'fixed condition set')
            for tag in ('support_evaluation','support_fixed8000'):need(set(data[j][tag]['pooled'])=={'rgb_U','dsm_U'},'U conditions')
        need(q['status']=='N3_S1_COMPLETE_AWAITING_REVIEW' and all(q['jobs'][j]['status']=='COMPLETE' for j in data),'queue complete')
        for family in ('N3','S1'):
            cs=[v for j,v in caps.items() if j.startswith(family)]
            need(len({v['trainable_parameters'] for v in cs})==len({v['total_parameters'] for v in cs})==len({v['initial_fusion_state_sha256'] for v in cs})==1,'matched capacity init')
        need(caps['N3-0']['total_parameters']-caps['S1-0']['total_parameters']==32768,'N3 capacity')
        families=p['evaluation']['families'];tiles=p['data']['validation']
        M=lambda s,cs:float(np.mean([s['pooled'][c] for c in cs]))
        S=lambda s:float(np.mean([M(s,cs) for cs in families.values()]))
        TS=lambda s,t:float(np.mean([np.mean([s['tiles'][c][t] for c in cs]) for cs in families.values()]))
        U=lambda s:M(s,['rgb_U','dsm_U'])
        UT=lambda s,t:float(np.mean([s['tiles'][c][t] for c in ('rgb_U','dsm_U')]))
        worst=lambda a,b:sorted([dict(condition=c,tile=t,gain_pp=a['tiles'][c][t]-b['tiles'][c][t]) for c in p['evaluation']['primary'] for t in tiles],key=lambda x:x['gain_pp'])
        sel={j:d['evaluation'] for j,d in data.items()};fix={j:d['fixed8000'] for j,d in data.items()};us={j:d['support_evaluation'] for j,d in data.items()};uf={j:d['support_fixed8000'] for j,d in data.items()}
        checks={};deltas={}
        for b in ('N3-0','N3-1'):
            d=S(sel['N3-4'])-S(sel[b]);deltas['S_vs_'+b]=d;checks['S_vs_'+b]=d>=.3-1e-9;checks['fixed_S_vs_'+b]=S(fix['N3-4'])>S(fix[b]);checks['tiles_S_vs_'+b]=all(TS(sel['N3-4'],t)>TS(sel[b],t) for t in tiles)
        for family,b in [('QR','N3-2'),('QD','N3-3')]:
            cs=families[family];d=M(sel['N3-4'],cs)-M(sel[b],cs);deltas[family+'_vs_'+b]=d;checks[family+'_vs_'+b]=d>=.2-1e-9;checks['fixed_'+family+'_vs_'+b]=M(fix['N3-4'],cs)>M(fix[b],cs);checks['tiles_'+family+'_vs_'+b]=all(np.mean([sel['N3-4']['tiles'][c][t]-sel[b]['tiles'][c][t] for c in cs])>0 for t in tiles)
        for b in ('N3-0','N3-1'):
            for cond in ('clean','dsm_missing','rgb_missing'):checks[cond+'_floor_vs_'+b]=sel['N3-4']['pooled'][cond]-sel[b]['pooled'][cond]>=-.1-1e-9
            checks['worst_vs_'+b]=worst(sel['N3-4'],sel[b])[0]['gain_pp']>=-.2-1e-9
        close(checks,screen['N3']['checks'],'N3 checks');close(deltas,screen['N3']['deltas_pp'],'N3 delta');need(bool(all(checks.values()))==screen['N3']['passed'],'N3 gate')
        checks={};deltas={}
        for b,th in [('S1-0',.5),('S1-1',.2),('S1-2',.2)]:
            d=U(us['S1-3'])-U(us[b]);deltas['U_mean_vs_'+b]=d;checks['U_mean_vs_'+b]=d>=th-1e-9;checks['fixed_U_vs_'+b]=U(uf['S1-3'])>U(uf[b]);checks['tile_U_vs_'+b]=all(UT(us['S1-3'],t)>UT(us[b],t) for t in tiles)
        for cond in ('clean','dsm_missing','rgb_missing'):checks[cond+'_floor']=sel['S1-3']['pooled'][cond]-sel['S1-0']['pooled'][cond]>=-.1-1e-9
        w=worst(sel['S1-3'],sel['S1-0']);checks['worst_primary_floor']=w[0]['gain_pp']>=-.2-1e-9
        directions={d:{b:dict(pooled_gain_pp=us['S1-3']['pooled'][d+'_U']-us[b]['pooled'][d+'_U'],tile_gains_pp={t:us['S1-3']['tiles'][d+'_U'][t]-us[b]['tiles'][d+'_U'][t] for t in tiles}) for b in ('S1-0','S1-1','S1-2')} for d in ('rgb','dsm')}
        close(checks,screen['S1']['checks'],'S1 checks');close(deltas,screen['S1']['deltas_pp'],'S1 deltas');close(directions,screen['S1']['directions'],'S1 directions')
        need(bool(all(checks.values()))==screen['S1']['passed']==False,'S1 failed gate')
        bilateral=all(v['pooled_gain_pp']>0 and all(x>0 for x in v['tile_gains_pp'].values()) for ds in directions.values() for v in ds.values())
        need(bool(all(checks.values()) and bilateral)==screen['S1']['bilateral_candidate'],'bilateral gate')
        scores={j:S(s) for j,s in sel.items()};uu={j:U(s) for j,s in us.items()};close(scores,screen['scores_pp'],'S scores');close(uu,screen['U_pp'],'U scores')
        inter=U(us['S1-3'])-U(us['S1-2'])-U(us['S1-1'])+U(us['S1-0']);close(inter,screen['S1']['interaction_U_pp'],'interaction')
        report={j:dict(selected_step=selected[j],S_available=scores[j],U_mean=uu[j],families={f:M(sel[j],cs) for f,cs in families.items()},clean=sel[j]['pooled']['clean'],dsm_missing=sel[j]['pooled']['dsm_missing'],rgb_missing=sel[j]['pooled']['rgb_missing'],U_directions=us[j]['pooled'],fixed_S=S(fix[j]),fixed_U=U(uf[j])) for j in data}
        return dict(status='PASS',source_commit='38d205591abe00179bebfb36a17595d4d7b75f47',manifest_payloads=len(self.files),git_blobs=len(self.blobs),counts=self.count,selected_steps=selected,N3=screen['N3'],S1=screen['S1'],S1_worst_primary=w,S1_protection_pp={c:sel['S1-3']['pooled'][c]-sel['S1-0']['pooled'][c] for c in ('clean','dsm_missing','rgb_missing')},jobs=report,ordinary_selected_conditions=len(sel['S1-0']['pooled']),fixed_conditions=len(fix['S1-0']['pooled']),source_boundaries='read 79 selected JSON payloads plus manifest; all payload paths/sizes checked; no server arrays/checkpoints/masks or GPU replay; source files manifest indexed, not all reread; joint raw marginals and pooling verified, joint_reports derived fields not all recomputed')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();x=Audit(a.directory).run();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n');print('N3_S1_INDEPENDENT_AUDIT',x['status'],x['counts']);print('WORST',x['S1_worst_primary'][:5]);print('PROTECTION',x['S1_protection_pp'])
if __name__=='__main__':main()

