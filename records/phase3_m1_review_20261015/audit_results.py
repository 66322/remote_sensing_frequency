"""Independent arithmetic audit of published sufficient counts, no model inference."""
import argparse, collections, hashlib, json, math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent; BASE=ROOT/'evidence'; VAL=('3_11','5_10')
MODELS=[a+'_'+str(s) for a in ('M00','M01','M10','M11','M20','M21') for s in (42,17)]
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(condition,message):
    if not condition: raise RuntimeError(message)
def integer(a,shape):
    a=np.asarray(a); check(a.shape==shape and np.issubdtype(a.dtype,np.integer) and np.all(a>=0),'invalid integer table'); return a
def score(a):
    union=a.sum(0)+a.sum(1)-a.diagonal()
    check(np.all(union[:5]>0),'missing foreground class in pooled score')
    return float(np.mean(a.diagonal()[:5]/union[:5])*100)
def iou(a):
    u=a.sum(0)+a.sum(1)-a.diagonal(); return [float(a[i,i]/u[i]*100) if u[i] else None for i in range(6)]
def flow(j):
    correct=sum(int(j[g,g,:].sum()) for g in range(5)); wrong=sum(int(j[g].sum()-j[g,g,:].sum()) for g in range(5))
    rescue=sum(int(j[g,:,g].sum()-j[g,g,g]) for g in range(5)); harm=sum(int(j[g,g,:].sum()-j[g,g,g]) for g in range(5))
    return dict(rgb_correct=correct,rgb_wrong=wrong,rescued=rescue,harmed=harm,
                rescue_rate=rescue/wrong if wrong else None,harm_rate=harm/correct if correct else None)
def summary(j):
    cm=j.sum(1); rgb=j.sum(2); f=flow(j)
    return dict(miou_fg5=score(cm),rgb_miou_fg5=score(rgb),gain_over_rgb_pp=score(cm)-score(rgb),
        class_iou=iou(cm),**f,rescue_rate_percent=None if f['rescue_rate'] is None else f['rescue_rate']*100,
        harm_rate_percent=None if f['harm_rate'] is None else f['harm_rate']*100)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--source-code',type=Path); args=parser.parse_args()
    archive=load(ROOT/'archive_verification.json'); verification=load(BASE/'result_verification.json'); original=load(BASE/'summary.json')
    binding={n:sha(BASE/n) for n in ('plan.json','code_manifest.json')}; check(binding==verification['binding'],'binding mismatch')
    check(load(BASE/'registration.json')['binding']==binding,'registration differs')
    plan=load(BASE/'plan.json'); recovery=load(BASE/'recovery_manifest.json')
    check(sha(BASE/'recovery_manifest.json')==plan['recovery_manifest_sha256'],'recovery binding differs')
    source=args.source_code or ROOT.parent/'phase3_m1_recovery/code'; manifest=load(BASE/'code_manifest.json'); source_checked=0
    for name,h in manifest['files'].items():
        check((source/name).exists() and sha(source/name)==h,'local audit source differs '+name); source_checked+=1
    primary={p.stem:load(p) for p in (BASE/'primary').glob('*.json')}; check(set(primary)==set(MODELS),'primary model coverage differs')
    clean_scores={}; matrices=0
    for job,z in primary.items():
        check(z['binding']==binding and z['job']==job,'primary binding')
        for scope in ('full','noboundary'):
            ms={t:integer(z['tiles'][t][scope],(6,6)) for t in VAL}; matrices+=2
            for t,m in dict(ms,pooled=sum(ms.values())).items():
                clean_scores['|'.join((job,scope,t))]={'miou_fg5':score(m),'class_iou':iou(m)}
    comparisons={}
    for a,b in (('M21','M11'),('M20','M10'),('M11','M10'),('M21','M20'),('M01','M00'),('M10','M00')):
        for seed in (42,17):
            row={t:clean_scores[f'{a}_{seed}|noboundary|{t}']['miou_fg5']-clean_scores[f'{b}_{seed}|noboundary|{t}']['miou_fg5'] for t in (*VAL,'pooled')}
            comparisons[f'{a}-{b}/{seed}']=row
            check(all(abs(row[t]-original['contrasts_pp'][f'{a}-{b}/{seed}'][t])<1e-10 for t in row),'primary contrast differs')
    interaction={str(s):{t:comparisons[f'M21-M11/{s}'][t]-comparisons[f'M20-M10/{s}'][t] for t in (*VAL,'pooled')} for s in (42,17)}
    gains=[comparisons[f'M21-M11/{s}']['pooled'] for s in (42,17)]
    tiles=[comparisons[f'M21-M11/{s}'][t] for s in (42,17) for t in VAL]
    gate=all(x>0 for x in gains) and sum(gains)/2>=.5 and min(tiles)>=-.2
    check(gate==original['amplitude_gate']['accepted']==load(BASE/'analysis/amplitude_gate.json')['accepted'],'gate differs')
    check(not gate and not any((BASE/'jobs'/j).exists() for j in ('C21_42','C21_17')),'unexpected counterfactual training')
    stream_by_seed={}; trainable_sets={}; jobs=[]; available_lineage=0; unavailable_weights=[]
    for job in MODELS:
        if job=='M00_42': continue
        folder=BASE/'jobs'/job; done=load(folder/'complete.json'); p=load(folder/'parameters.json')
        check(done['optimizer_updates']==16000 and done['frozen_parameters_unchanged'] and done['trainable_gradients_connected'],'training complete contract')
        arm,seed_text=job.split('_'); adapted=arm.endswith('1'); rep={'M00':'R0','M01':'R0','M10':'R1','M11':'R1','M20':'R2','M21':'R2'}[arm]
        check(p['input_representation']==rep and p['stem_trainable']==adapted and p['batch']==16 and p['updates']==16000,'factor metadata differs')
        names={row[0] for row in p['trainable']}
        if adapted in trainable_sets: check(trainable_sets[adapted]==names,'trainable scope differs across representations/seeds')
        else: trainable_sets[adapted]=names
        check(not any(n.startswith('encoder.blocks.'+str(i)+'.') for n in names for i in range(8)),'early block unexpectedly trainable')
        if done['binding']!=binding:
            check(job in recovery['completed'] and done['binding']==recovery['previous_binding'],'unbridged job binding')
        stream=[json.loads(x) for x in (folder/'batch_hashes.jsonl').read_text().splitlines()]
        check(len(stream)==16000 and [r['step'] for r in stream]==list(range(1,16001)),'sample step coverage')
        seed=p['seed']; reference=stream_by_seed.setdefault(seed,stream); check(stream==reference,'within-seed stream mismatch')
        if p['stem_trainable']:
            proof=load(folder/'gradient_path.json'); check(proof['stem_changed'] and proof['early8_weights_frozen'],'stem gradient proof')
        check(done['initial_state_sha256']==p['initial_state_sha256'],'initial metadata mismatch')
        if job in recovery['completed']:
            for name,h in recovery['completed'][job]['files'].items():
                if (folder/name).exists(): check(sha(folder/name)==h,'inherited file changed '+job+'/'+name); available_lineage+=1
                elif name.endswith('.pth'): unavailable_weights.append(job+'/'+name)
                elif name!='progress.json': raise RuntimeError('missing retained lineage '+job+'/'+name)
        if job in recovery['resumed']:
            row=recovery['resumed'][job]; restored=load(folder/'resume_loaded.json')
            check(restored['step']==row['step'] and restored['source_sha256']==row['sha256'] and restored['prefix_sha256']==row['prefix_sha256'],'resume provenance')
            check(restored['optimizer_restored'] and restored['cpu_cuda_rng_restored'],'resume state flags')
            lines=(folder/'batch_hashes.jsonl').read_bytes().splitlines(keepends=True)
            check(hashlib.sha256(b''.join(lines[:row['step']])).hexdigest()==row['prefix_sha256'],'resume stream prefix changed')
        jobs.append({'job':job,'seed':seed,'initial':p['initial_state_sha256'],'worker_gpu_label':done['physical_gpu'],'endpoint_sha256_record':done['checkpoint_sha256']})
    for seed in (42,17): check(len({j['initial'] for j in jobs if j['seed']==seed})==1,'within-seed initialization metadata differs')
    check(trainable_sets[True]-trainable_sets[False]=={'encoder.patch_embed.proj.weight','encoder.patch_embed.proj.bias'} and trainable_sets[False]<=trainable_sets[True],'adaptation is not exactly stem weight/bias')
    counts=collections.Counter(); pooled=collections.defaultdict(lambda:np.zeros((6,6,6),np.int64)); refs={}; joints=0; case_metrics={}
    for section in ('clean','results'):
        for f in sorted((BASE/section).rglob('*.json')):
            z=load(f)
            if 'counts' not in z: continue
            check(z['binding']==binding,'count binding mismatch '+str(f)); job=z['job']; check(job in MODELS,'unknown count model')
            if section=='clean':
                tile=z['tile']; panel='clean_'+z['availability']; identity=(panel,tile)
            else:
                task=z['case']; tile=task['tile']; panel=task['kind']+'_'+task['damage']
                identity=(panel,tile,task.get('family','global'),task.get('realization',0))
            counts[(job,panel,tile)]+=1
            check(set(z['counts'])=={'full','noboundary'},'scope coverage')
            for scope,rois in z['counts'].items():
                check(set(rois)=={'all','healthy','damaged'},'ROI coverage')
                for roi,systems in rois.items():
                    check(set(systems)=={'dsm','logit_mix','probability_mix'},'system coverage')
                    first=None
                    for system,stats in systems.items():
                        j=integer(stats['joint'],(6,6,6)); cm=integer(stats['cm'],(6,6)); rgb=integer(stats['rgb_cm'],(6,6))
                        check(np.array_equal(j.sum(1),cm) and np.array_equal(j.sum(2),rgb),'joint marginal mismatch')
                        check(stats['flow']==flow(j),'rescue/harm mismatch')
                        if first is not None: check(np.array_equal(first,rgb),'RGB marginal differs by system')
                        first=rgb
                        refkey=(identity,scope,roi)
                        if refkey in refs: check(np.array_equal(refs[refkey],rgb),'shared RGB reference differs by DSM model')
                        else: refs[refkey]=rgb.copy()
                        if section=='clean' and system!='dsm':
                            expected=rgb if z['availability']=='dsm_missing' else integer(systems['dsm']['cm'],(6,6)) if z['availability']=='rgb_missing' else None
                            if expected is not None: check(np.array_equal(cm,expected),'explicit fallback not exact')
                        if system=='dsm' and roi=='all' and (section=='clean' or panel.startswith('RGB_FAULT_')):
                            check(np.array_equal(cm,np.asarray(primary[job]['tiles'][tile][scope])),'unchanged DSM clean prediction differs')
                        key='|'.join((panel,job,scope,roi,system)); pooled[key]+=j
                        if scope=='noboundary' and roi=='all':
                            for suffix in ('tile='+tile, 'family='+str(z.get('case',{}).get('family','global'))): pooled[key+'|'+suffix]+=j
                            if section=='results' and panel.startswith('RGB_FAULT_'):
                                case_metrics['|'.join((job,panel,tile,str(task['family']),str(task['realization']),system))]=score(cm)
                        matrices+=2; joints+=1
                for system in ('dsm','logit_mix','probability_mix'):
                    check(np.all(np.asarray(rois['all'][system]['joint'])-np.asarray(rois['healthy'][system]['joint'])-np.asarray(rois['damaged'][system]['joint'])>=0),'ROI counts overlap beyond support')
    for job in MODELS:
        for tile in VAL:
            for panel,n in [('clean_both',1),('clean_rgb_missing',1),('clean_dsm_missing',1),('RGB_FAULT_zero',80),('RGB_FAULT_down4',80),('DSM_FAULT_down4',1),('DSM_FAULT_shift8',1)]:
                check(counts[(job,panel,tile)]==n,'required case count differs '+str((job,panel,tile)))
    check(joints==verification['joint_tables_verified'] and matrices==verification['integer_matrices_verified'],'server table totals differ')
    panel_metrics={k:summary(j) for k,j in pooled.items() if j[:5].sum()>0}
    paired={}
    for seed in (42,17):
        for damage in ('zero','down4'):
            for system in ('dsm','logit_mix','probability_mix'):
                ds=[]
                for t in VAL:
                    for family in ('pixel','random','gradient','matched'):
                        for n in range(1,21):
                            tail='|'.join(('RGB_FAULT_'+damage,t,family,str(n),system))
                            ds.append(case_metrics[f'M21_{seed}|'+tail]-case_metrics[f'M11_{seed}|'+tail])
                paired[f'{seed}|{damage}|{system}']={'cases':len(ds),'positive':sum(d>0 for d in ds),'negative':sum(d<0 for d in ds),'mean_case_delta_pp':float(np.mean(ds)),'min_case_delta_pp':min(ds),'max_case_delta_pp':max(ds)}
    scale=collections.defaultdict(lambda:np.zeros((6,6),np.int64)); supports={}; scale_count=0
    for f in (BASE/'scale').glob('*.json'):
        z=load(f); seen=set()
        for row in z['rows']:
            m=integer(row['cm'],(6,6)); pair=(row['gsd_cm'],row['fov_m']); identity=(row['y'],row['x'],*pair)
            check(identity not in seen,'duplicate scale ROI'); seen.add(identity)
            check(pair in ((5,25.6),(10,25.6),(5,51.2),(10,51.2)),'unexpected scale setting')
            key=(z['tile'],row['y'],row['x']); support=m.sum(1)
            if key in supports: check(np.array_equal(supports[key],support),'scale ROI label support differs')
            else: supports[key]=support
            scale[f"{z['job']}|{row['gsd_cm']}|{row['fov_m']}"]+=m; scale_count+=1
        check(len(seen)==64,'scale diagnostic coverage')
    check(scale_count==1536,'scale matrix total')
    result={'archive_commit':archive['commit'],'verification_status':'VERIFIED_COUNT_ARITHMETIC_AND_ARCHIVE_ONLY',
        'archive_files_verified':archive['files_verified'],'integer_matrices_recomputed':matrices,'joint_tables_recomputed':joints,
        'additional_scale_matrices_checked':scale_count,'bound_source_files_locally_matched':source_checked,
        'main_jobs':len(jobs),'new_optimizer_updates':len(jobs)*16000,'within_seed_streams_exact':True,'trainable_scope_factor_exact':True,
        'recovery_retained_file_hashes_checked':available_lineage,'scientific_gate_accepted':gate,
        'main_contrasts_pp':comparisons,'interaction_pp':interaction,'clean_scores':clean_scores,
        'panel_metrics':panel_metrics,'paired_mask_descriptive':paired,
        'scale_metrics':{k:{'miou_fg5':score(v),'class_iou':iou(v)} for k,v in scale.items()},
        'jobs_metadata':jobs,'inference_rerun':False,'server_checkpoint_hashes_independently_read':False,
        'physical_gpu_UUID_attribution_independently_verified':False,
        'limits':['No model/raw-data inference rerun; checkpoint tensors were intentionally excluded from archive.',
                  'Two reused development tiles; two DSM seeds share one fixed RGB seed42; masks/pixels are not independent scenes.',
                  'External historical seed42 stream/legacy CM checks rely on retained server receipts; archived new streams match within seed.',
                  'No new mechanism or cross-scene generalization claim; no p-values or seed confidence intervals inferred.']}
    (ROOT/'audit_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print('AUDIT_PASSED',joints,'JOINTS',matrices,'MATRICES','SCALE',scale_count,flush=True)
    print('CLEAN_POOLED',json.dumps({k:v for k,v in clean_scores.items() if '|noboundary|pooled' in k}),flush=True)
    for seed in (42,17):
        for panel in ('clean_both','RGB_FAULT_down4','RGB_FAULT_zero','DSM_FAULT_down4','DSM_FAULT_shift8'):
            for job in (f'M11_{seed}',f'M21_{seed}'):
                for system in ('dsm','logit_mix','probability_mix'):
                    print('PANEL',panel,job,system,json.dumps(panel_metrics[f'{panel}|{job}|noboundary|all|{system}']),flush=True)
if __name__=='__main__': main()
