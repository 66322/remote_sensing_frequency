"""Independent CPU raw-count audit; never imports model, dataset or training code."""
import argparse,base64,gzip,hashlib,json,math
from collections import Counter
from pathlib import Path,PurePosixPath
import numpy as np
ROOT=Path(__file__).resolve().parent;DATA=ROOT/'received';OUT=ROOT/'analysis'
COUNTS=Counter();READ=set();MANIFEST={};ORIGINAL={};G,R,D,F=np.indices((6,)*4)
def digest(b):return hashlib.sha256(b).hexdigest()
def need(value,reason):
    if not value:raise ValueError(reason)
def read(tag,name):
    p=DATA/tag/name;raw=p.read_bytes()
    try:value=json.loads(raw)
    except json.JSONDecodeError:
        if name.endswith('.json'):raise
        value=raw.decode('utf-8')
    if name in MANIFEST.get(tag,{}):
        row=MANIFEST[tag][name];need(len(raw)==row['bytes'] and digest(raw)==row['sha256'],'uploaded bytes/SHA '+tag+'/'+name)
    if isinstance(value,dict) and value.get('record_encoding')=='gzip-base64-exact-v1' and 'payload_base64' in value:
        source=gzip.decompress(base64.b64decode(value['payload_base64'],validate=True));need(len(source)==value['original_bytes'] and digest(source)==value['original_sha256'],'decode integrity '+name)
        value=json.loads(source) if name.endswith('.json') else source.decode('utf-8')
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
    return dict(pooled={c:100*row['noboundary']['metrics']['candidate']['valid']['mIoU_fg5'] for c,row in s['pooled'].items()},
      tiles={c:{t:100*row['scopes']['noboundary']['metrics']['candidate']['valid']['mIoU_fg5'] for t,row in rows.items()} for c,rows in s['tiles'].items()})
def mean(s,cs):return sum(s['pooled'][c] for c in cs)/len(cs)
def scores(s,p):
    d={k:mean(s,cs) for k,cs in p['evaluation']['families'].items()};d['S_available']=sum(d.values())/4;return d
def audit_summary(s,expected,signature):
    need(set(s['tiles'])==set(expected) and set(s['pooled'])==set(expected),'exact condition coverage')
    need(s['binding']['training']==signature and not s['test6_loaded'] and not s['independent_final_loaded'],'summary signature/final scope')
    retained=np.zeros((6,)*4,np.int64)
    for condition,rows in s['tiles'].items():
        need(set(rows)=={'3_11','5_10'},'tile coverage')
        for tile,row in rows.items():
            need(row['binding']==s['binding'],'tile signature')
            case_name=CURRENT_ROOT+CURRENT_TAG+'/'+condition+'/'+tile+'.json'
            serialized=(json.dumps(row,indent=2,allow_nan=False)+'\n').encode()
            need(digest(serialized)==source_hash(case_name),'embedded case source SHA')
            COUNTS['embedded_case_source_hashes_checked']+=1
            for name,dig in row['predictions'].items():
                predpath=str(PurePosixPath(SERVER_BASE)/CURRENT_ROOT/CURRENT_TAG/condition/name/(tile+'.npy'))
                need(ARTIFACTS[predpath]['sha256']==dig,'prediction artifact index')
                COUNTS['prediction_index_bindings_checked']+=1
            if CURRENT_TAG.startswith('content_'):
                need(row['mask_binding']==MASKS['tiles'][tile][condition.split('_')[1]],'content case mask binding')
        for scope in ('full','noboundary'):
            results={t:verify_scope(row['scopes'][scope]) for t,row in rows.items()}
            pc,pj=verify_scope(s['pooled'][condition][scope])
            for name,regions in pc.items():
                for region,cm in regions.items():
                    need(np.array_equal(cm,sum((x[0][name][region] for x in results.values()),np.zeros((6,6),np.int64))),'pooled matrix equality')
                    COUNTS['pooled_matrix_groups']+=1
            for region,j in pj.items():
                need(np.array_equal(j,sum((x[1][region] for x in results.values()),np.zeros((6,)*4,np.int64))),'pooled joint equality')
                COUNTS['pooled_joint_groups']+=1
        if condition in PRIMARY:
            retained+=sum((joint(row['scopes']['noboundary']['joint']['both']) for row in rows.values()),np.zeros((6,)*4,np.int64))
    rep=report(retained);harm={}
    for n,v in (('rgb',R),('dsm',D)):
        den=int(retained[v==G].sum());harm[n]=int(retained[(v==G)&(F!=G)].sum())/den if den else None
    return compact(s),dict(retentions={n:rep['only_'+n+'_correct']['retention'] for n in ('rgb','dsm')},harm=harm,joint_report=rep)
def source_hash(name):return ORIGINAL['N5'][name]['original_sha256']
def main():
    global DATA,OUT,PRIMARY,CURRENT_ROOT,CURRENT_TAG,SERVER_BASE,ARTIFACTS,MASKS
    ap=argparse.ArgumentParser();ap.add_argument('--input-directory',type=Path,default=ROOT/'received');ap.add_argument('--output-directory',type=Path,default=ROOT/'analysis');args=ap.parse_args()
    DATA=args.input_directory;OUT=args.output_directory;OUT.mkdir(parents=True,exist_ok=True)
    tree=json.loads((DATA/'N5/git_tree.json').read_text());need(not tree['truncated'],'untruncated tree')
    entries={r['path']:r for r in tree['tree'] if r['type']=='blob'}
    manifest=get('N5','upload_manifest.json')
    MANIFEST['N5']={r['path']:r for r in manifest['files']};ORIGINAL['N5']={r['path']:r for r in manifest['source_files']}
    for local in (DATA/'N5').rglob('*'):
        if local.is_file() and local.relative_to(DATA/'N5').as_posix() in MANIFEST['N5']:get('N5',local.relative_to(DATA/'N5').as_posix())
    need(set(entries)==set(MANIFEST['N5'])|{'upload_manifest.json'},'complete Git payload inventory')
    for n,row in MANIFEST['N5'].items():
        need(entries[n]['size']==row['bytes'],'tree size '+n);COUNTS['manifest_payload_paths_sizes_checked']+=1
    need(manifest['upload_total_bytes']==sum(r['bytes'] for r in manifest['files']) and manifest['source_total_bytes']==sum(r['original_bytes'] for r in manifest['source_files']),'manifest totals')
    p=get('N5','plan.json');PRIMARY=p['evaluation']['primary']
    need(p['execution_commit']=='2e565cca04d84d8605a96105d12fb6c0871e464d' and p['initial_checkpoint']['sha256']=='28bc6f8ca5e1221392598b0a6f2d160e8c633a6a9cf63827067df3e7b81a144b','frozen science/base')
    need(p['data']['dataset']=='Potsdam' and p['data']['validation']==['3_11','5_10'] and len(p['data']['fit12'])==12 and not set(p['data']['fit12'])&set(p['data']['validation']),'split')
    need(p['training']['seed']==42 and p['training']['steps']==8000 and p['training']['physical_batch']==16 and not p['training']['gradient_accumulation'] and p['training']['validation_steps']==[4000,8000] and p['training']['selection_states']==['clean','dsm_missing','rgb_missing'],'training budget')
    need(p['physical_gpus']==[0,1] and [r['gpu'] for r in p['jobs']]==[0,1,0,1] and not p['data']['test6_loaded'] and not p['data']['independent_final_loaded'],'resources/scope')
    need(p['total_optimizer_steps']==32000 and p['N5_gate']==dict(T_mean_gain_pp=.5,clean_full_missing_floor_pp=-.1,old_random_mean_floor_pp=-.1,worst_primary_tile_floor_pp=-.2,both_tiles_positive=True,fixed_main_positive=True),'frozen gate/budget')
    need(p['mask_contract']==dict(rules=['U','H','L','T'],cell=128,fraction=.25,window=5,T='maximum luminance local standard deviation; same geometry as H/L',train_rules=['U','H','L']),'mask contract')
    need(p['crop_contract']['rules']=={'N5-1':['U']*4,'N5-2':['H','L','H','L'],'N5-3':['U','U','H','L']} and p['crop_contract']['replaced_sample_indices']==list(range(8,16)) and p['crop_contract']['origin_multiple']==128,'crop/condition contract')
    code=get('N5','code_manifest.json');need(code['commit']==p['execution_commit'],'execution snapshot')
    published=get('N5','published_validation.json')
    for name,dig in published['new_files_sha256'].items():need(code['files'][name]==dig,'frozen published N5 source hash '+name)
    matched_code=0
    for n,dig in code['files'].items():
        if 'code/'+n in ORIGINAL['N5']:need(source_hash('code/'+n)==dig,'source snapshot metadata '+n);matched_code+=1
    masks=get('N5','mask_manifest.json');need(masks['plan_sha256']==source_hash('plan.json') and masks['T_generated_after_plan_freeze'] and not masks['T_training'],'mask freeze')
    artifacts={r['path']:r for r in get('N5','server_artifact_index.json')['artifacts']}
    MASKS=masks;ARTIFACTS=artifacts;SERVER_BASE=p['server_root']+'/records/research_post_n5_20261006T114819_71934'
    mask_count=0
    for tile,rs in masks['tiles'].items():
        need(set(rs)==({'U','H','L'} if tile in p['data']['fit12'] else {'U','H','L','T'}),'mask train/evaluation separation')
        shapes=[];counts=[]
        for rule,row in rs.items():
            h,w=row['shape'];need(row['missing_pixels']*4==h*w,'mask area')
            need(artifacts[row['path']]['sha256']==row['sha256'],'mask artifact binding')
            area=0
            for y,x,bh,bw in row['blocks']:
                need(0<=y and 0<=x and y+bh<=h and x+bw<=w,'mask bounds');area+=bh*bw
            need(area==row['missing_pixels'],'mask block area metadata')
            shapes.append([(r[2],r[3]) for r in row['blocks']]);counts.append(len(row['blocks']));mask_count+=1
        need(all(x==shapes[0] for x in shapes) and len(set(counts))==1,'paired shape/count')
    need(set(masks['tiles'])==set(p['data']['fit12']+p['data']['validation']) and mask_count==44,'mask coverage')
    prep=get('N5','preparation_complete.json');need(prep['plan_sha256']==source_hash('plan.json') and prep['mask_manifest_sha256']==source_hash('mask_manifest.json') and prep['optimizer_updates']==0,'preparation binding')
    q=get('N5','queue_status.json');need(q['status']=='N5_COMPLETE_AWAITING_REVIEW' and all(r['status']=='COMPLETE' and r['returncode']==0 for r in q['jobs'].values()),'queue completion')
    raw=get('N5','n5_screen.json');need(q['screen_sha256']==source_hash('n5_screen.json'),'queue screen binding')
    result={};retentions={};completes={};capacity=[];source_bindings=[];exposures={}
    standard=p['evaluation']['primary']+p['evaluation']['missing']+sum(p['evaluation']['local'].values(),[])+p['evaluation']['diagnostic']
    fixed=p['evaluation']['primary']+p['design']['geometry_conditions']+p['design']['missing_conditions']
    extra=[d+'_'+r for d in ('rgb','dsm') for r in ('U','H','L','T')]
    for i in range(4):
        j='N5-'+str(i);root='jobs/'+j+'/';c=get('N5',root+'complete.json');completes[j]=c['completed_at']
        tc=c['treatment_counts']
        exposures[j]=dict(pixels={k:v for k,v in tc.items() if k.endswith('_pixels')},new_conditions={k:v for k,v in tc.items() if k.startswith('N5_')},original_conditions={k:v for k,v in tc.items() if ';geom=' in k and not k.startswith('N5_')})
        need(sum(exposures[j]['original_conditions'].values())+sum(exposures[j]['new_conditions'].values())==128000,'crop exposure total')
        sig=c['signature']
        need(c['global_step']==8000 and sig['execution_commit']==p['execution_commit'] and sig['plan_sha256']==source_hash('plan.json') and sig['mask_manifest_sha256']==source_hash('mask_manifest.json') and sig['initial_checkpoint_sha256']==p['initial_checkpoint']['sha256'],'completion binding '+j)
        expected_experts={n:dict(path=str(PurePosixPath(p['server_root'])/p['experts'][n]['path']),sha256=p['experts'][n]['sha256'],step=p['experts'][n]['step']) for n in ('rgb','dsm')}
        need(sig['job']==p['jobs'][i] and sig['sources']==code['files'] and sig['experts']==expected_experts,'job/code/expert binding '+j)
        need(sig['input_manifest_sha256']==p['input_manifest_sha256'] and all(sig[k]==v for k,v in p['expected_configs'].items()) and not c['test6_loaded'] and not c['independent_final_loaded'],'input/final binding')
        initial=get('N5',root+'initial_checkpoint_binding.json');need(initial['checkpoint_sha256']==p['initial_checkpoint']['sha256'] and initial['full_state_loaded'] and initial['optimizer_reinitialized'],'full-state init');source_bindings.append(initial)
        cap=get('N5',root+'model_capacity.json');capacity.append({k:v for k,v in cap.items() if k!='arm'})
        selected_path=str(PurePosixPath(p['server_root'])/'records/research_post_n5_20261006T114819_71934/jobs'/j/'selected.pth')
        need(artifacts[selected_path]['sha256']==c['selected_checkpoint_sha256']==c['selected']['checkpoint_sha256'],'selected artifact index')
        vals={}
        for step in (4000,8000):
            row=get('N5',root+'validation/step_%04d.json'%step);need(row['binding']['training']==sig,'validation signature')
            state_metrics={}
            for cond,rows in row['tiles'].items():
                total=sum((matrix(x) for x in rows.values()),np.zeros((6,6),np.int64));state_metrics[cond]=metrics(total)['mIoU_fg5']
            close(state_metrics,row['state_metrics'],'selection metrics');v=sum(state_metrics.values())/3;close(v,row['score'],'selection mean');vals[step]=v
        best=max(vals,key=lambda step:(vals[step],-step));need(c['selected']['step']==best,'earliest selection');close(c['selected']['metric'],vals[best],'selected score')
        result[j]={}
        for tag,conditions in [('evaluation',standard),('fixed8000',fixed),('content_evaluation',extra),('content_fixed8000',extra)]:
            name=root+tag+'/summary.json';s,hashval=read('N5',name);need(hashval==c[tag+'_summary_sha256'],'complete-to-summary SHA')
            if tag in ('evaluation','content_evaluation'):need(s['binding']['selected']==c['selected'],'selected summary binding')
            else:need(s['binding']['step']==8000,'fixed age')
            CURRENT_ROOT=root;CURRENT_TAG=tag
            tiny,ret=audit_summary(s,conditions,sig);result[j][tag]=tiny
            if tag=='evaluation':retentions[j]=ret
            del s
        print('AUDIT_COMPLETE',j,flush=True)
    need(all(c==capacity[0] for c in capacity),'matched parameter/init capacity')
    need(all(c==source_bindings[0] for c in source_bindings),'same complete base binding')
    for j in ('N5-1','N5-2','N5-3'):
        need(exposures[j]['pixels']==exposures['N5-1']['pixels'] and exposures[j]['original_conditions']==exposures['N5-1']['original_conditions'],'paired supervision/original exposure')
    for j,rules in {'N5-1':{'U':32000},'N5-2':{'H':16000,'L':16000},'N5-3':{'U':16000,'H':8000,'L':8000}}.items():
        expected={f'N5_{d}_{r};geom=(0, 0)':n for d in ('rgb','dsm') for r,n in rules.items()}
        need(exposures[j]['new_conditions']==expected,'exact direction/rule exposure')
    a=result['N5-3']['content_evaluation'];b=result['N5-1']['content_evaluation'];cs=['rgb_T','dsm_T']
    delta=lambda x,y,cc:mean(x,cc)-mean(y,cc)
    d=dict(T_mean_vs_random=delta(a,b,cs),T_tile_mean={t:sum(a['tiles'][c][t]-b['tiles'][c][t] for c in cs)/2 for t in p['data']['validation']},fixed_T_mean_vs_random=delta(result['N5-3']['content_fixed8000'],result['N5-1']['content_fixed8000'],cs))
    for c in ('clean','dsm_missing','rgb_missing'):d[c+'_vs_original']=delta(result['N5-3']['evaluation'],result['N5-0']['evaluation'],[c])
    d['old_random_vs_random']=delta(result['N5-3']['evaluation'],result['N5-1']['evaluation'],p['N5_old_random_conditions'])
    d['worst_primary_vs_random']=min(result['N5-3']['evaluation']['tiles'][c][t]-result['N5-1']['evaluation']['tiles'][c][t] for c in PRIMARY for t in p['data']['validation'])
    checks=dict(T_mean_gain=d['T_mean_vs_random']>=.5-1e-9,T_both_tiles_positive=all(v>0 for v in d['T_tile_mean'].values()),fixed_T_positive=d['fixed_T_mean_vs_random']>0,clean_floor=d['clean_vs_original']>=-.1-1e-9,dsm_missing_floor=d['dsm_missing_vs_original']>=-.1-1e-9,rgb_missing_floor=d['rgb_missing_vs_original']>=-.1-1e-9,old_random_floor=d['old_random_vs_random']>=-.1-1e-9,worst_primary_floor=d['worst_primary_vs_random']>=-.2-1e-9)
    directions={v:dict(pooled_gain_pp=delta(a,b,[v+'_T']),tile_gains_pp={t:a['tiles'][v+'_T'][t]-b['tiles'][v+'_T'][t] for t in p['data']['validation']}) for v in ('rgb','dsm')}
    bilateral=all(checks.values()) and all(v['pooled_gain_pp']>0 and all(x>0 for x in v['tile_gains_pp'].values()) for v in directions.values())
    ordinary={j:scores(rows['evaluation'],p) for j,rows in result.items()}
    for key,value in dict(primary_candidate='N5-3',passed=all(checks.values()),bilateral_candidate=bilateral,checks=checks,deltas_pp=d,directions=directions,ordinary_scores=ordinary,harm_and_retention=retentions,old_random_conditions=p['N5_old_random_conditions']).items():close(value,raw[key],'screen '+key)
    answer=dict(status='ANALYZED_OFFLINE_PASS',execution_commit=p['execution_commit'],source_upload_commit='1bd58b6a64e07e8b4ee8d5e87e91f76b8df93898',queue_observed_at=q['observed_at'],counts=dict(COUNTS),fetched_payloads_checked=sum(name in MANIFEST[tag] for tag,name in READ),git_blobs_including_manifest=len(entries),indexed_code_hashes_compared=matched_code,published_N5_source_hashes_compared=len(published['new_files_sha256']),mask_metadata_count=mask_count,complete_times=completes,exposures={j:{k:v for k,v in x.items() if k!='original_conditions'} for j,x in exposures.items()},capacity={k:v for k,v in capacity[0].items() if k!='trainable_names'},screen=raw,compact_results=result,
      scope='payload inventory paths/sizes; retrieved upload/original SHA; 16 summary counts, joint marginals/reports/pooling, checkpoint selection, provenance, fixed gates; server weight/prediction/mask binary bodies not re-read',
      metadata_drift=['inherited created_at,directory_pattern,automatic_followup,verification_status,architecture and fixed10/selected22 labels are historical; actual worker is N5/N1 unchanged model, selected32/fixed22 + content8 each'])
    (OUT/'audit_result.json').write_text(json.dumps(answer,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in answer.items() if k not in ('compact_results','screen')},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
