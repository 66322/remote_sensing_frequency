"""Independent CPU raw-count audit; never imports model, dataset or training code."""
import argparse,base64,gzip,hashlib,json,math
from collections import Counter
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent;DATA=ROOT/'received';OUT=ROOT/'analysis'
COUNTS=Counter();READ=set();MANIFEST={};ORIGINAL={};G,R,D,F=np.indices((6,)*4)
def digest(b):return hashlib.sha256(b).hexdigest()
def need(value,reason):
    if not value:raise ValueError(reason)
def read(tag,name):
    p=DATA/tag/name;raw=p.read_bytes();value=json.loads(raw)
    if name in MANIFEST.get(tag,{}):
        row=MANIFEST[tag][name];need(len(raw)==row['bytes'] and digest(raw)==row['sha256'],'uploaded bytes/SHA '+tag+'/'+name)
    if isinstance(value,dict) and value.get('record_encoding')=='gzip-base64-exact-v1' and 'payload_base64' in value:
        source=gzip.decompress(base64.b64decode(value['payload_base64'],validate=True));need(len(source)==value['original_bytes'] and digest(source)==value['original_sha256'],'decode integrity '+name)
        value=json.loads(source)
    else:source=raw
    if name in ORIGINAL.get(tag,{}):
        row=ORIGINAL[tag][name];need(len(source)==row['original_bytes'] and digest(source)==row['original_sha256'],'original binding '+name)
    READ.add((tag,name));return value,digest(source)
def get(tag,name):return read(tag,name)[0]
def close(a,b,reason):
    if isinstance(a,dict):
        need(set(a)==set(b),reason+' keys')
        for k in a:close(a[k],b[k],reason+'/'+str(k))
    elif isinstance(a,list):
        need(len(a)==len(b),reason+' length')
        for i,(x,y) in enumerate(zip(a,b)):close(x,y,reason+'/'+str(i))
    elif isinstance(a,(int,float)) and not isinstance(a,bool):need(b is not None and math.isclose(a,b,abs_tol=1e-10,rel_tol=1e-12),reason)
    else:need(a==b,reason)
def metrics(cm):
    tp=np.diag(cm);sp=cm.sum(1);fp=cm.sum(0)-tp;fn=sp-tp;u=tp+fp+fn
    iou=[float(tp[i]/u[i]) if u[i] else None for i in range(6)]
    avg=lambda x:sum(v for v in x if v is not None)/sum(v is not None for v in x) if any(v is not None for v in x) else None
    return dict(cm=cm.tolist(),support=sp.tolist(),TP=tp.tolist(),FP=fp.tolist(),FN=fn.tolist(),IoU=iou,mIoU_fg5=avg(iou[:5]),mIoU_6=avg(iou),valid=int(cm.sum()))
def matrix(row):
    cm=np.asarray(row['cm']);need(cm.shape==(6,6) and cm.dtype.kind in 'iu' and not (cm<0).any(),'integer CM')
    cm=cm.astype(np.int64);close(metrics(cm),row,'matrix-derived counts/IoU');COUNTS['matrices_checked']+=1;return cm
def joint(row):
    need(row['shape']==[6]*4 and row['dtype']=='int64' and row['format']=='sparse_flat_index_count','joint format')
    flat=np.zeros(6**4,np.int64);seen=set()
    for index,count in row['nonzero']:
        need(type(index)==int and type(count)==int and 0<=index<6**4 and count>0 and index not in seen,'sparse int joint')
        seen.add(index);flat[index]=count
    COUNTS['joints_checked']+=1;return flat.reshape((6,)*4)
def report(a):
    result={}
    for n,mask in dict(both_correct=(R==G)&(D==G),only_rgb_correct=(R==G)&(D!=G),only_dsm_correct=(R!=G)&(D==G),both_wrong=(R!=G)&(D!=G)).items():
        total=int(a[mask].sum());correct=int(a[mask&(F==G)].sum())
        result[n]=dict(valid=total,fused_correct=correct,fused_wrong=total-correct,retention=correct/total if total else None,by_class={str(c):dict(valid=int(a[mask&(G==c)].sum()),fused_correct=int(a[mask&(G==c)&(F==G)].sum())) for c in range(6)})
    return result
def verify_scope(scope,rgb='fixed_rgb',dsm='fixed_dsm'):
    cms={n:{r:matrix(x) for r,x in regions.items()} for n,regions in scope['metrics'].items()};js={}
    for region,j in scope['joint'].items():
        a=joint(j);js[region]=a
        for n,axes in (('candidate',(1,2)),(rgb,(2,3)),(dsm,(1,3))):need(np.array_equal(a.sum(axes),cms[n][region]),'joint marginal '+n)
        if 'joint_reports' in scope:close(report(a),scope['joint_reports'][region],'joint report')
    return cms,js
def compact(s):
    return dict(pooled={c:100*row['noboundary']['metrics']['candidate']['valid']['mIoU_fg5'] for c,row in s['pooled'].items()},tiles={c:{t:100*row['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5'] for t,row in rows.items()} for c,rows in s['tiles'].items()})
def mean(s,cs):return sum(s['pooled'][c] for c in cs)/len(cs)
def scores(s,p):
    d={k:mean(s,cs) for k,cs in p['evaluation']['families'].items()};d['S_available']=sum(d.values())/4;return d
def n2_screen(sel,fix,p,retentions):
    candidate=sel['N2-3'];checks={};deltas={};tile_deltas={}
    specs=dict(spatial=('N2-0',p['evaluation']['primary'],.3),dsm_degraded_vs_height_only=('N2-1',p['evaluation']['families']['QD'],.2),rgb_degraded_vs_semantic_only=('N2-2',p['evaluation']['families']['QR'],.2),height_correspondence=('N2-4',p['evaluation']['families']['QR'],.2),semantic_correspondence=('N2-5',p['evaluation']['families']['QD'],.2))
    for name,(ref,cs,floor) in specs.items():
        d=scores(candidate,p)['S_available']-scores(sel[ref],p)['S_available'] if name=='spatial' else mean(candidate,cs)-mean(sel[ref],cs)
        deltafix=scores(fix['N2-3'],p)['S_available']-scores(fix[ref],p)['S_available'] if name=='spatial' else mean(fix['N2-3'],cs)-mean(fix[ref],cs)
        deltas[name]=d;checks[name]=d>=floor-1e-9;checks['fixed_sign_'+name]=deltafix>0
        tile_deltas[name]={}
        for t in p['data']['validation']:
            cc=list(p['evaluation']['families'].values()) if name=='spatial' else [cs]
            tile_deltas[name][t]=sum(sum(candidate['tiles'][c][t]-sel[ref]['tiles'][c][t] for c in family)/len(family) for family in cc)/len(cc)
        checks['both_tiles_positive_'+name]=all(v>0 for v in tile_deltas[name].values())
    for c in ('clean','dsm_missing','rgb_missing'):checks[c+'_floor']=candidate['pooled'][c]-sel['N2-0']['pooled'][c]>=-.1-1e-9
    checks['worst_floor']=min(candidate['tiles'][c][t]-sel['N2-0']['tiles'][c][t] for c in p['evaluation']['primary'] for t in p['data']['validation'])>=-.2-1e-9
    return dict(primary_candidate='N2-3',passed=all(checks.values()),checks=checks,deltas_pp=deltas,tile_deltas_pp=tile_deltas,scores_pp={j:scores(s,p) for j,s in sel.items()},fixed8000_scores_pp={j:scores(s,p) for j,s in fix.items()},harm_and_retention=retentions,base='N1-2',single_seed_development=True,new_contribution_established=False,test6_loaded=False,independent_final_loaded=False)
def artifact_lookup(tag):return {r['path']:r for r in get(tag,'server_artifact_index.json')['artifacts']}
def scope_e0(scope):
    for name,row in scope.items():
        verify_scope(dict(metrics={n:{name:m} for n,m in row['metrics'].items()},joint={name:row['joint']}))
        a=joint(row['joint']);close(report(a),row['joint_report'],'E0 report')
        mask=(R==G)|(D==G);den=int(a[mask].sum());harm=int(a[mask&(F!=G)].sum());close(dict(denominator=den,harm=harm,harm_rate=harm/den if den else None),row['anchor_correct_union'],'E0 union');need(row['valid']==int(a.sum()),'E0 denominator')
def main():
    global DATA,OUT
    ap=argparse.ArgumentParser();ap.add_argument('--input-directory',type=Path,default=DATA);ap.add_argument('--output-directory',type=Path,default=OUT);args=ap.parse_args();DATA=args.input_directory;OUT=args.output_directory;OUT.mkdir(parents=True,exist_ok=True)
    for tag in ('N2','DIAG'):
        manifest=get(tag,'upload_manifest.json');MANIFEST[tag]={r['path']:r for r in manifest['files']};ORIGINAL[tag]={r['path']:r for r in manifest['source_files']}
        tree={r['path']:r for r in get(tag,'git_tree.json') if r['type']=='blob'}
        need(set(tree)==set(MANIFEST[tag])|{'upload_manifest.json'},'manifest paths '+tag)
        for name,row in MANIFEST[tag].items():need(tree[name]['size']==row['bytes'],'manifest size '+name)
        COUNTS['manifest_payload_paths_sizes_checked']+=len(MANIFEST[tag]);COUNTS['git_files_including_manifests']+=len(tree)
    p,ph=read('N2','plan.json');dp,dph=read('DIAG','plan.json');manifest=get('N2','code_manifest.json');dc=get('DIAG','code_manifest.json');art=artifact_lookup('N2');dart=artifact_lookup('DIAG');sel={};fix={};ret={};raw_primary={};completion={}
    need(p['execution_commit']=='86b6a70e5c3482314986fb1259e2fccbd0a5a38b' and p['data']['validation']==['3_11','5_10'],'N2 science/scope')
    need(manifest['commit']==p['execution_commit'] and dc['commit']==dp['execution_commit']=='883fccc0b97714cfe0a87b54bfeb2a2fc09820d7','execution commits')
    need(p['physical_gpus']==dp['physical_gpus']==[0,1] and p['data']==dp['data'] and p['training']['seed']==42 and p['training']['physical_batch']==16 and p['training']['steps']==8000 and not p['training']['gradient_accumulation'],'devices/data/budget')
    need(not p['data']['test6_loaded'] and not p['data']['independent_final_loaded'] and dp['new_optimizer_updates']==0 and not dp['automatic_training'],'no final/new training')
    for j in ('N2-'+str(i) for i in range(6)):
        complete,ch=read('N2','jobs/'+j+'/complete.json');completion[j]=ch
        need(complete['signature']['job']==next(row for row in p['jobs'] if row['id']==j) and not complete['test6_loaded'] and not complete['independent_final_loaded'],'N2 scientific job binding')
        need(complete['global_step']==8000 and complete['signature']['plan_sha256']==ph and complete['signature']['execution_commit']==p['execution_commit'],'N2 completion '+j)
        need(complete['signature']['sources']==manifest['files'],'N2 source manifest')
        for kind,key in (('selected.pth','selected_checkpoint_sha256'),('last_train_state.pth','last_checkpoint_sha256')):
            path=p['jobs'][0]['initial_checkpoint_path'].split('/records/')[0]+'/records/research_post_ab_followup_n2_20261005T085829_3456726/jobs/'+j+'/'+kind
            need(art[path]['sha256']==complete[key],'N2 server checkpoint index')
        for tag,target in (('evaluation',sel),('fixed8000',fix)):
            s,sh=read('N2','jobs/'+j+'/'+tag+'/summary.json');need(sh==complete[tag+'_summary_sha256'] and s['binding']['training']==complete['signature'],'N2 summary binding')
            if tag=='evaluation':need(s['binding']['selected']==complete['selected'],'N2 selected binding')
            need(not s['test6_loaded'] and not s['independent_final_loaded'],'final scope')
            expected=p['evaluation']['primary']+p['design']['geometry_conditions']+p['design']['missing_conditions'] if tag=='fixed8000' else p['evaluation']['primary']+p['evaluation']['missing']+sum(p['evaluation']['local'].values(),[])+p['evaluation']['diagnostic']
            need(set(s['tiles'])==set(expected) and set(s['pooled'])==set(expected),'condition coverage')
            for c,tiles in s['tiles'].items():
                need(set(tiles)=={'3_11','5_10'},'Val2 coverage')
                for scope in ('full','noboundary'):
                    tcs=[];tjs=[]
                    for row in tiles.values():
                        need(row['binding']==s['binding'],'tile training binding');cms,js=verify_scope(row['scopes'][scope]);tcs.append(cms);tjs.append(js)
                    pooled_cms,pooled_js=verify_scope(s['pooled'][c][scope])
                    for n,regions in pooled_cms.items():
                        for region,cm in regions.items():need(np.array_equal(cm,sum((v[n][region] for v in tcs),np.zeros((6,6),np.int64))),'pooling CM');COUNTS['pooled_matrix_groups']+=1
                    for region,a in pooled_js.items():need(np.array_equal(a,sum((v[region] for v in tjs),np.zeros((6,)*4,np.int64))),'pooling joint');COUNTS['pooled_joint_groups']+=1
            if tag=='evaluation':
                a=sum((joint(s['tiles'][c][t]['scopes']['noboundary']['joint']['both']) for c in p['evaluation']['primary'] for t in p['data']['validation']),np.zeros((6,)*4,np.int64));jr=report(a)
                rates={n:float(a[(x==G)&(F!=G)].sum()/a[x==G].sum()) for n,x in (('rgb',R),('dsm',D))}
                ret[j]=dict(retentions={n:jr['only_'+n+'_correct']['retention'] for n in ('rgb','dsm')},harm=rates,joint_report=jr)
                raw_primary[j]={c:{t:{scope:s['tiles'][c][t]['scopes'][scope]['metrics']['candidate']['valid']['cm'] for scope in ('full','noboundary')} for t in tiles} for c,tiles in s['tiles'].items() if c in p['evaluation']['primary']}
            target[j]=compact(s);del s
        print('AUDIT_N2_COMPLETE',j,flush=True)
    calculated=n2_screen(sel,fix,p,ret);reported=get('N2','n2_screen.json');close(calculated,{k:reported[k] for k in calculated},'N2 fixed screen')
    source_audit=get('DIAG','n2_source_audit.json');need(source_audit['N2_gate']==calculated['passed'],'predecessor scientific gate');close(completion,source_audit['source_complete_sha256'],'predecessor complete SHAs')
    clean_e0={};descriptive={}
    for model in dp['E0_models']:
        descriptive[model]={}
        for c in dp['primary']:
            for t in dp['data']['validation']:
                row,sh=read('DIAG','E0/'+model+'/'+c+'/'+t+'.json');need(row['tile']==t and row['condition']==c and not row['test6_loaded'] and not row['independent_final_loaded'],'E0 scope/binding')
                for scope in row['scopes']:scope_e0(row['scopes'][scope])
                if model.startswith('N2-'):
                    close(row['scopes']['noboundary']['all']['metrics']['candidate']['cm'],raw_primary[model][c][t]['noboundary'],'E0 original candidate CM')
                    need(row['source_record_sha256']==ORIGINAL['N2']['jobs/'+model+'/evaluation/'+c+'/'+t+'.json']['original_sha256'],'E0 source record SHA')
                if c=='clean':descriptive[model][t]={n:{k:r[k] for k in ('anchor_correct_union','valid')} for n,r in row['scopes']['full'].items()}
                if model=='N1-2' and c=='clean':clean_e0[t]=row['scopes']
        print('AUDIT_E0_COMPLETE',model,flush=True)
    e0_checks={}
    for t,row in clean_e0.items():
        b=row['full']['boundary4'];inside=row['full']['interior'];ba=b['anchor_correct_union'];ia=inside['anchor_correct_union'];delta=100*(ba['harm_rate']-ia['harm_rate'])
        supported=ba['denominator']>=100 and ia['denominator']>=100 and all(sum(x['joint_report'][name]['valid'] for x in (b,inside))>=100 for name in ('only_rgb_correct','only_dsm_correct'))
        e0_checks[t]=dict(supported=supported,boundary_minus_interior_harm_pp=delta,passed=supported and delta>=1.-1e-9)
    e0=dict(N3_problem_trigger=all(r['passed'] for r in e0_checks.values()),checks=e0_checks,scope='full',model='N1-2',automatic_training=False);diag_screen=get('DIAG','diagnostic_screen.json');close(e0,diag_screen['E0'],'E0 gate')
    e1rows={};e1pool={};e1cm={};e1class={};e2={};maskman,mmh=read('DIAG','mask_manifest.json');mask_art={r['path']:r for r in dart.values() if r['path'].endswith('.npz')};mask_shapes={}
    need(not maskman['T_evaluated'] and not diag_screen['T_evaluated'] and not diag_screen['test6_loaded'] and not diag_screen['independent_final_loaded'],'reserved rule/final scope')
    for t,rules in maskman['tiles'].items():
        mask_shapes[t]={}
        for rule,mb in rules.items():
            boxes=mb['blocks'];need(mb['fraction']==.25 and mb['missing_pixels']*4==math.prod(mb['shape']) and sum(b[2]*b[3] for b in boxes)==mb['missing_pixels'],'quarter area')
            need(mask_art[mb['path']]['sha256']==mb['sha256'],'mask server index');mask_shapes[t][rule]=sorted((b[2],b[3]) for b in boxes)
        need(mask_shapes[t]['U']==mask_shapes[t]['H']==mask_shapes[t]['L'],'matched mask shape multiset')
    for job in dp['jobs']:
        j=job['id'];complete=get('DIAG','jobs/'+j+'/complete.json');s,sh=read('DIAG','jobs/'+j+'/summary.json');binding=s['binding']
        need(sh==complete['summary_sha256'] and binding==complete['signature'] and binding['job']==job and binding['plan_sha256']==dph and binding['mask_manifest_sha256']==mmh and binding['optimizer_updates']==0 and complete['optimizer_updates']==0,'diagnostic binding')
        need(not complete['test6_loaded'] and not complete['independent_final_loaded'] and binding['code_manifest_sha256']==read('DIAG','code_manifest.json')[1],'diagnostic scope/code manifest')
        source=binding['model_binding']
        if job['model'].startswith('N2-'):need(source['complete_sha256']==completion[job['model']] and source['plan_sha256']==ph,'N2 diagnostic model provenance')
        if job['model']=='N1-2':need(source['checkpoint_sha256']=='28bc6f8ca5e1221392598b0a6f2d160e8c633a6a9cf63827067df3e7b81a144b','fixed N1-2 base')
        result={};rawrows={}
        for c,tiles in s['records'].items():
            need(set(tiles)=={'3_11','5_10'},'diagnostic Val2');result[c]={};rawrows[c]={}
            for t,index in tiles.items():
                local='jobs/'+j+'/evaluation/'+c+'/'+t+'.json';row,rh=read('DIAG',local);need(rh==index['sha256'] and row['binding']['training']==binding and row['binding']['tile']==t,'diagnostic source binding')
                need(row['mask_binding']==maskman['tiles'][t][c.split('_',1)[1] if job['stage']=='E1' else 'U'],'paired mask identity')
                for scope in ('full','noboundary'):
                    cms,js=verify_scope(row['scopes'][scope],rgb='rgb',dsm='dsm')
                    for n,regions in cms.items():need(np.array_equal(regions['all'],regions['mask_location']+regions['other_locations']),'location partition')
                    close(row['scopes'][scope]['label_class_counts_at_mask'],cms['candidate']['mask_location'].sum(1).tolist(),'mask class composition')
                result[c][t]=np.asarray(row['scopes']['noboundary']['metrics']['candidate']['all']['cm'],np.int64);rawrows[c][t]=row
                for n,d in row['predictions'].items():
                    path=index['path'].rsplit('/',1)[0]+'/'+n+'/'+t+'.npy';need(dart[path]['sha256']==d,'prediction SHA server index')
        clean={t:matrix(r['metrics']['noboundary']) for t,r in s['clean'].items()}
        if job['stage']=='E1':
            e1rows[job['model']]={c:{t:metrics(cm)['mIoU_fg5'] for t,cm in ts.items()} for c,ts in result.items()};e1pool[job['model']]={c:metrics(sum(ts.values(),np.zeros((6,6),np.int64)))['mIoU_fg5'] for c,ts in result.items()};e1cm[job['model']]={c:sum(ts.values(),np.zeros((6,6),np.int64)).tolist() for c,ts in result.items()};e1class[job['model']]={c:{t:r['scopes']['noboundary']['label_class_counts_at_mask'] for t,r in ts.items()} for c,ts in rawrows.items()}
        else:
            e2[job['model']]={}
            for d in ('rgb','dsm'):
                known=result[d+'_known_missing'];miss=result[d+'_false_negative'];fp=result[d+'_false_positive'];delta=100*(metrics(sum(known.values(),np.zeros((6,6),np.int64)))['mIoU_fg5']-metrics(sum(miss.values(),np.zeros((6,6),np.int64)))['mIoU_fg5']);td={t:100*(metrics(known[t])['mIoU_fg5']-metrics(miss[t])['mIoU_fg5']) for t in known}
                for t in known:
                    rk=rawrows[d+'_known_missing'][t];rn=rawrows[d+'_false_negative'][t];rf=rawrows[d+'_false_positive'][t]
                    need(rk['physical_input_sha256']==rn['physical_input_sha256'] and rk['reported_mask_sha256']!=rn['reported_mask_sha256'],'physical damaged inputs paired')
                    need(rk['reported_mask_sha256']==rf['reported_mask_sha256'] and rk['physical_input_sha256']!=rf['physical_input_sha256'],'false positive actual input intact')
                    need(rk['predictions']==rf['predictions'] and np.array_equal(known[t],fp[t]),'model zeroing false-positive equivalence')
                e2[job['model']][d]=dict(missed_flag_cost_pp=delta,tile_costs_pp=td,problem_signal=delta>=.5-1e-9 and all(x>0 for x in td.values()),false_positive_vs_clean_pp=100*(metrics(sum(clean.values(),np.zeros((6,6),np.int64)))['mIoU_fg5']-metrics(sum(fp.values(),np.zeros((6,6),np.int64)))['mIoU_fg5']),raw_matrices={k:{t:cm.tolist() for t,cm in result[d+'_'+k].items()} for k in ('known_missing','false_negative','false_positive')})
        print('AUDIT_DIAGNOSTIC_COMPLETE',j,flush=True)
    checks={};deltas={}
    for d in ('rgb','dsm'):
        for rule in ('H','L'):
            n=d+'_'+rule;deltas[n]={};ok=True
            for model in ('A0','B1'):
                gap=100*(e1pool[model][d+'_U']-e1pool[model][n]);td={t:100*(e1rows[model][d+'_U'][t]-e1rows[model][n][t]) for t in ('3_11','5_10')};deltas[n][model]=dict(pooled_gap_pp=gap,tile_gaps_pp=td);ok&=gap>=.5-1e-9 and all(x>0 for x in td.values())
            checks[n]=bool(ok)
    e1=dict(N5_problem_trigger=any(checks.values()),checks=checks,deltas=deltas,automatic_training=False)
    close(e1,diag_screen['E1'],'E1 screen');close(e1rows,diag_screen['E1_tile_metrics_fraction'],'E1 tile metric');close(e1pool,diag_screen['E1_pooled_metrics_fraction'],'E1 pooled metric');close(e1cm,diag_screen['E1_pooled_matrices'],'E1 matrices');close(e2,diag_screen['E2'],'E2 screen')
    COUNTS['fetched_payloads_sha_and_decode_checked']=len(READ)-4 # manifests and local git-tree exports
    audit=dict(status='PASS',counters=dict(COUNTS),N2=calculated,E0=e0,E1=e1,E2=e2,E1_class_composition=e1class,E0_clean_profiles=descriptive,read_files=[tag+'/'+n for tag,n in sorted(READ)],weights_predictions_masks_downloaded=False,training_rerun=False,scope='Potsdam fit12/Val2 seed42 development; no Test6')
    (OUT/'audit.json').write_text(json.dumps(audit,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print('AUDIT_PASS',json.dumps(dict(COUNTS)),flush=True)
if __name__=='__main__':main()
