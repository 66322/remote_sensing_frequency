import concurrent.futures as cf
import hashlib, json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent
SHA='acd2dbfbcf18ef792840bfe3f5465207a74a13c2'
EV='records/research_d24_overnight_20261002T000843_877409/evidence_20261002T121402814506_1365054'
JOBS=['A0','A1','A2','A3','B0','B1','B2','B3','C0','C1','C2','C3','D0','D1','D2']
def fetch(path):
    dst=ROOT/'source'/path
    if not dst.exists():
        raise FileNotFoundError(f'Populate source/{path} from the authorized GitHub connector at {SHA}:{EV}; no server training needed')
    return path,dst.read_bytes()
paths=['upload_manifest.json','screen_result.json','plan.json','queue_status.json','code_manifest.json']
paths += [f'jobs/{j}/{p}' for j in JOBS for p in ['evaluation/summary.json','complete.json','gradient_check.json','input_binding.json']]
with cf.ThreadPoolExecutor(max_workers=6) as pool:
    data=dict(pool.map(fetch,paths))
manifest=json.loads(data['upload_manifest.json']);expected={r['path']:r for r in manifest['files']}
for p,v in data.items():
    if p!='upload_manifest.json':
        assert hashlib.sha256(v).hexdigest()==expected[p]['sha256'],p
        assert len(v)==expected[p]['bytes'],p
def fg(cm):
    cm=np.asarray(cm,np.int64);tp=np.diag(cm);den=cm.sum(0)+cm.sum(1)-tp
    return float(np.nanmean(np.divide(tp,den,out=np.full(6,np.nan),where=den>0)[:5]))*100
analysis={'source_commit':SHA,'source_directory':EV,'downloaded_manifest_payloads_verified':len(data)-1,'jobs':{}}
count=0
for j in JOBS:
    s=json.loads(data[f'jobs/{j}/evaluation/summary.json'])
    for condition,tiles in s['tiles'].items():
        for tile,row in tiles.items():
            for model,scopes in row['results'].items():
                for scope,value in scopes.items():
                    cm=np.asarray(value['cm']);assert cm.shape==(6,6) and cm.dtype.kind in 'iu' and (cm>=0).all()
                    tp=np.diag(cm);fp=cm.sum(0)-tp;fn=cm.sum(1)-tp
                    for name,arr in [('TP',tp),('support',cm.sum(1)),('FP',fp),('FN',fn)]:assert np.array_equal(arr,value[name])
                    assert int(cm.sum())==value['all']['valid']
                    for key in ('valid','harm','rescue'):
                        assert value['all'][key]==value['available'][key]+value['missing'][key]
                        assert value['all'][key]==sum(r[key] for r in value['by_class'].values())
                    assert abs(fg(cm)-value['mIoU_fg5']*100)<1e-9
                    assert sum(value['TP'])-sum(row['results']['R0'][scope]['TP'])==value['all']['rescue']-value['all']['harm']
                    count+=1
            for scope,value in row['own_optical_reference'].items():
                assert value['missing']['harm']==value['missing']['rescue']==0
                assert value['cm']==row['results']['candidate'][scope]['cm']
                assert sum(row['results']['candidate'][scope]['TP'])-sum(row['results']['own_optical'][scope]['TP'])==value['all']['rescue']-value['all']['harm']
        for model,scopes in s['pooled'][condition].items():
            for scope,value in scopes.items():
                cm=sum(np.asarray(row['results'][model][scope]['cm'],np.int64) for row in tiles.values())
                assert np.array_equal(cm,value['cm'])
                assert abs(fg(cm)-value['mIoU_fg5']*100)<1e-9
    conditions={c:{m:fg(v['noboundary']['cm']) for m,v in models.items()} for c,models in s['pooled'].items()}
    complete=json.loads(data[f'jobs/{j}/complete.json'])
    assert complete['evaluation_summary_sha256']==hashlib.sha256(data[f'jobs/{j}/evaluation/summary.json']).hexdigest()
    assert complete['signature']['execution_commit']=='cf1955d966163978b5c8af433f3845b5ca05da9e'
    assert complete['signature']['plan_sha256']==hashlib.sha256(data['plan.json']).hexdigest()
    assert complete['selected']['checkpoint_sha256']==complete['selected_checkpoint_sha256']
    assert complete['global_step']==4000
    assert complete['signature']['test6_loaded'] is False
    assert abs(complete['selected']['metric']*100-conditions['clean']['candidate'])<1e-9
    analysis['jobs'][j]={'conditions':conditions,'complete':complete,'gradient_check':json.loads(data[f'jobs/{j}/gradient_check.json'])}
analysis['tile_matrices_recomputed']=count
screen=json.loads(data['screen_result.json'])
rgb=['rgb_down2','rgb_down4','rgb_blur5','rgb_local_down4_q1'];aux=['aux_down4','aux_noise_std010']
def scores(j):
    c=analysis['jobs'][j]['conditions'];clean=c['clean']['candidate'];r=np.mean([c[k]['candidate'] for k in rgb]);a=np.mean([c[k]['candidate'] for k in aux])
    return dict(clean=clean,rgb_family=float(r),aux_family=float(a),composite=float((clean+r+a)/3))
for row in screen['rows']:
    for name,value in scores(row['id']).items():assert abs(value-row[name])<1e-9
for pair,result in screen['matched_comparisons'].items():
    a,b=pair.split('-')
    for name,value in scores(a).items():assert abs(value-scores(b)[name]-result['delta_pp'][name])<1e-9
compact=dict(source_commit=SHA,source_directory=EV,manifest_payloads_verified=len(data)-1,total_uploaded_files=len(expected)+1,tile_matrices_recomputed=count,pooled_matrices_recomputed=15*14*4*2,complete_bindings_verified=15,printed_screen_scores_and_matched_pooled_deltas_recomputed=True,raw_checkpoints_or_predictions_received=False,checkpoint_selection_candidates_independently_reviewed=False,verification_level='offline_record_recomputation_not_training_reproduction',invalid_mechanism_comparisons=['A1-A0','A3-A2','Pair_x_last4'],invalidation_reason='Case-sensitive Pair membership check is false for actual CE+clean_R0_anchored_pair config; loss remains CE',rows=[])
for j in JOBS:
    c=analysis['jobs'][j]['conditions'];complete=analysis['jobs'][j]['complete'];s=scores(j)
    compact['rows'].append(dict(id=j,**s,missing_macro=float(np.mean([c[k]['candidate'] for k in ['aux_zero','aux_local_zero_q1','aux_local_zero_stripe_eighth']])),aux_zero=c['aux_zero']['candidate'],local_zero=c['aux_local_zero_q1']['candidate'],stripe_zero=c['aux_local_zero_stripe_eighth']['candidate'],selected_step=complete['selected']['step'],own_optical_clean=c['clean']['own_optical'],fusion_minus_own_optical_clean=c['clean']['candidate']-c['clean']['own_optical'],selected_checkpoint_sha256=complete['selected_checkpoint_sha256'],treatment_counts=complete['treatment_counts']))
compact['comparisons']=screen['matched_comparisons'];compact['C_region_screen']=screen['C_region_screen'];compact['mechanism_screen_corrected']={**screen['mechanism_screen'],'Pair_frozen':None,'Pair_last4':None};compact['factorial_interaction_corrected']={'Pair_x_last4':None,'Q_x_D':screen['factorial_interaction_composite_pp']['Q_x_D']}
(ROOT/'compact_analysis.json').write_text(json.dumps(compact,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'analysis.json').write_text(json.dumps(analysis,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'payloads_checked':len(data)-1,'tile_matrices_recomputed':count,'jobs':{j:{c:analysis['jobs'][j]['conditions'][c] for c in ['clean','aux_zero','aux_shift16','aux_noise_std020','aux_local_zero_q1']} for j in ['A2','D0','D1','D2','C0']}},indent=2))
