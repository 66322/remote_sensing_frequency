"""Bound source audit, fit12 calibration and read-only spatial diagnosis."""
from pathlib import Path
import numpy as np
from post_n2_diag_common import *
from post_n2_masks import scores,quarter_mask,boundary_band,object_areas,small_objects

def input_contract(root,plan):
    mapping={'input_manifest_sha256':'records/rebuild_v1_d21_queue_20260928/input_manifest.json',
        'split_sha256':'configs/rebuild_v1/potsdam_split_seed20260915.json',
        'base_config_sha256':'configs/rebuild_v1/r05_quality_plus_dropout_16k.json',
        'dino_config_sha256':'configs/rebuild_v1/d18_d19_night_20260927.json'}
    if sha(root/mapping['input_manifest_sha256'])!=plan['input_manifest_sha256']:raise RuntimeError('input manifest changed')
    for name,digest in plan['expected_configs'].items():
        if name not in mapping or sha(root/mapping[name])!=digest:raise RuntimeError('bound configuration changed '+name)
    dino=read(root/mapping['dino_config_sha256'])['dino']
    import subprocess
    repo=within(root/dino['repository_dir'],'/home/jovyan/zzx')
    if subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()!=dino['repository_commit']:raise RuntimeError('DINO source changed')
    subprocess.run(['git','-C',str(repo),'diff','--exit-code','HEAD','--','dinov2','hubconf.py'],stdout=subprocess.DEVNULL,check=True)

def audit_predecessor(root,base,plan):
    from summarize_post_ab_n1 import cell
    from summarize_post_ab_n2 import screen
    from post_d30_evaluation import decode_joint,metric
    predecessor=Path(plan['predecessor_directory']);p=read(predecessor/'plan.json')
    if p['execution_commit']!=SCIENCE:raise RuntimeError('unexpected predecessor science')
    data={};matrices=0;joints=0
    for i in range(6):
        j='N2-'+str(i);binding,_,_=bind_model(root,j)
        data[j]=cell(predecessor,j,p)
        for tag,s in data[j].items():
            for condition,rows in s['tiles'].items():
                for tile,row in rows.items():
                    for scope in ('full','noboundary'):
                        for region,jr in row['scopes'][scope]['joint'].items():
                            arr=decode_joint(jr)
                            if (arr<0).any():raise RuntimeError('negative joint count')
                            cm=np.asarray(row['scopes'][scope]['metrics']['candidate'][region]['cm'],np.int64)
                            if not np.array_equal(arr.sum((1,2)),cm):raise RuntimeError('candidate joint marginal changed')
                            for axis,name in ((2,'fixed_rgb'),(1,'fixed_dsm')):
                                if not np.array_equal(arr.sum((axis,3)),np.asarray(row['scopes'][scope]['metrics'][name][region]['cm'],np.int64)):raise RuntimeError('anchor marginal changed')
                            joints+=1
                for scope in ('full','noboundary'):
                    for region,pool in s['pooled'][condition][scope]['joint'].items():
                        total=sum((decode_joint(r['scopes'][scope]['joint'][region]) for r in rows.values()),np.zeros((6,)*4,np.int64))
                        if not np.array_equal(total,decode_joint(pool)):raise RuntimeError('pooled joint differs')
                    matrices+=sum(len(v) for v in s['pooled'][condition][scope]['metrics'].values())
        print('DIAG_N2_AUDIT',j,flush=True)
    computed=screen(data,p);reported=read(predecessor/'n2_screen.json')
    for key in computed:
        if key!='observed_at' and computed[key]!=reported.get(key):raise RuntimeError('N2 screen mismatch '+key)
    result=dict(science_commit=SCIENCE,source_plan_sha256=sha(predecessor/'plan.json'),screen_sha256=sha(predecessor/'n2_screen.json'),
        source_complete_sha256={j:sha(predecessor/'jobs'/j/'complete.json') for j in data},pooled_matrix_groups=matrices,tile_joint_groups=joints,
        N2_gate=reported['passed'],verification='completion/selected/summary SHA, integer tile-to-pooled matrices and metrics, joint pooling/marginals, fixed screen',observed_at=now())
    write(base/'n2_source_audit.json',result)

def prepare_masks(root,base,plan,loader):
    samples={n:[] for n in ('H','L')};areas={str(c):[] for c in range(5)}
    for tile in plan['data']['fit12']:
        item=loader(tile);fields=scores(item['optical'],item['dsm'],5)
        for n,x in fields.items():samples[n].append(x[::16,::16].ravel().copy())
        for c,a in object_areas(item['full_gt']).items():areas[c].extend(a)
        write(base/'cpu_progress.json',dict(phase='fit12_calibration',tile=tile,observed_at=now()))
        print('DIAG_CALIBRATION',tile,flush=True);del item,fields
    calibration=dict(H_high=float(np.quantile(np.concatenate(samples['H']),.75)),L_low=float(np.quantile(np.concatenate(samples['L']),.25)),
        small_object_cutoffs={c:float(np.quantile(a,.25)) if a else 0 for c,a in areas.items()},fit12=plan['data']['fit12'],quantiles=dict(H=.75,L=.25,objects=.25),sample_stride=16,window=5,labels_used_for='object-size diagnostic cutoff only; never mask selection',observed_at=now())
    write(base/'calibration.json',calibration)
    metadata={}
    for tile in plan['data']['validation']:
        item=loader(tile,True);fields=scores(item['optical'],item['dsm'],5);metadata[tile]={}
        for rule in ('U','H','L'):
            mask,boxes=quarter_mask(item['dsm'].shape,rule,fields.get(rule),tile)
            target=base/'masks'/tile/(rule+'.npz');target.parent.mkdir(parents=True,exist_ok=True)
            np.savez_compressed(target,bits=np.packbits(mask.ravel(),bitorder='little'),shape=np.array(mask.shape,np.int64))
            metadata[tile][rule]=dict(path=str(target),sha256=sha(target),shape=list(mask.shape),missing_pixels=int(mask.sum()),fraction=.25,blocks=boxes,component_count=len(boxes),bit_order='little')
        signatures=[sorted((b[2],b[3]) for b in metadata[tile][r]['blocks']) for r in ('U','H','L')]
        if not signatures[0]==signatures[1]==signatures[2]:raise RuntimeError('mask shapes differ')
        print('DIAG_MASKS',tile,metadata[tile]['U']['missing_pixels'],flush=True);del item,fields
    write(base/'mask_manifest.json',dict(plan_sha256=sha(base/'plan.json'),calibration_sha256=sha(base/'calibration.json'),tiles=metadata,T_evaluated=False,source_inputs=loader.verified,observed_at=now()))

def load_mask(base,tile,rule):
    row=read(base/'mask_manifest.json')['tiles'][tile][rule];path=within(row['path'],base)
    if sha(path)!=row['sha256']:raise RuntimeError('mask bytes changed')
    with np.load(path,allow_pickle=False) as z:
        shape=tuple(int(x) for x in z['shape']);m=np.unpackbits(z['bits'],bitorder='little',count=int(np.prod(shape))).reshape(shape).astype(bool)
    if m.shape!=tuple(row['shape']) or int(m.sum())!=row['missing_pixels'] or int(m.sum())*4!=m.size:raise RuntimeError('decoded mask changed')
    return m,row

def source_row(root,model,condition,tile):
    source,folder=model_folder(root,model);complete=read(folder/'complete.json')
    row=read(folder/'evaluation'/condition/(tile+'.json'))
    if row['binding']['training']!=complete['signature'] or row['binding']['selected']!=complete['selected']:raise RuntimeError('prediction binding differs')
    return folder,row

def read_prediction(folder,row,condition,tile,name):
    path=folder/'evaluation'/condition/name/(tile+'.npy')
    if sha(path)!=row['predictions'][name]:raise RuntimeError('prediction changed '+str(path))
    return np.load(path,allow_pickle=False)

def spatial_stats(gt,preds,region):
    from post_d30_evaluation import counts,joint_counts,encode_joint,joint_report
    r,d,f=(preds[n] for n in ('fixed_rgb','fixed_dsm','candidate'))
    valid=region&(gt<6)&(r<6)&(d<6)&(f<6);correct=(r==gt)|(d==gt)
    denominator=int((valid&correct).sum());harm=int((valid&correct&(f!=gt)).sum())
    jr=joint_counts(gt,r,d,f,valid)
    return dict(metrics={n:counts(gt,p,valid) for n,p in preds.items()},joint=encode_joint(jr),joint_report=joint_report(jr),
        anchor_correct_union=dict(denominator=denominator,harm=harm,harm_rate=harm/denominator if denominator else None),valid=int(valid.sum()))

def e0_gate(clean_rows,contract):
    checks={}
    for tile,row in clean_rows.items():
        b=row['full']['boundary4'];inside=row['full']['interior'];ba=b['anchor_correct_union'];ia=inside['anchor_correct_union']
        singles=sum(x['joint_report']['only_rgb_correct']['valid'] for x in (b,inside))>=contract['min_single_correct_pixels'] and sum(x['joint_report']['only_dsm_correct']['valid'] for x in (b,inside))>=contract['min_single_correct_pixels']
        supported=ba['denominator']>=contract['min_anchor_pixels'] and ia['denominator']>=contract['min_anchor_pixels']
        delta=100*(ba['harm_rate']-ia['harm_rate']) if supported else None
        checks[tile]=dict(supported=bool(supported and singles),boundary_minus_interior_harm_pp=delta,passed=bool(supported and singles and delta>=contract['boundary_harm_gap_pp']-1e-9))
    return dict(N3_problem_trigger=set(clean_rows)=={'3_11','5_10'} and all(x['passed'] for x in checks.values()),checks=checks,scope='full',model='N1-2',automatic_training=False)

def e0(root,base,plan,loader):
    calibration=read(base/'calibration.json');index={};clean_rows={}
    for model in plan['E0_models']:
        binding,_,_=bind_model(root,model,checkpoint=False);index[model]={}
        for tile in plan['data']['validation']:
            item=loader(tile,True);fields=scores(item['optical'],item['dsm']);band=boundary_band(item['full_gt'],4)
            regions=dict(all=np.ones(band.shape,bool),boundary4=band,interior=(item['full_gt']<6)&~band,
                small_objects=small_objects(item['full_gt'],calibration['small_object_cutoffs']),high_dsm_change=fields['H']>=calibration['H_high'],low_rgb_contrast=fields['L']<=calibration['L_low'])
            for condition in plan['primary']:
                folder,row=source_row(root,model,condition,tile)
                preds={n:read_prediction(folder,row,condition,tile,n) for n in ('candidate','fixed_rgb','fixed_dsm')}
                if any(x.shape!=band.shape for x in preds.values()):raise RuntimeError('prediction shape differs')
                support=np.ones(band.shape,bool)
                if 'geom_' in condition:
                    support[:8]=False;support[-8:]=False;support[:,:8]=False;support[:,-8:]=False
                scopes={scope:{n:spatial_stats(item[scope+'_gt'],preds,region&support) for n,region in regions.items()} for scope in ('full','noboundary')}
                target=base/'E0'/model/condition/(tile+'.json')
                write(target,dict(binding=binding,tile=tile,condition=condition,source_record_sha256=sha(folder/'evaluation'/condition/(tile+'.json')),scopes=scopes,calibration_sha256=sha(base/'calibration.json'),metric='Potsdam Val2 native512 stride256; Full diagnostic and NoBoundary fg5',confusion_matrix_dtype='int64',joint_axes=['truth','fixed_rgb','fixed_dsm','candidate'],test6_loaded=False,independent_final_loaded=False,observed_at=now()))
                index[model][condition+'/'+tile]=dict(path=str(target),sha256=sha(target))
                if model=='N1-2' and condition=='clean':clean_rows[tile]=scopes
                write(base/'cpu_progress.json',dict(phase='E0',model=model,tile=tile,condition=condition,observed_at=now()));del preds,scopes
            del item,fields,regions,band
        print('DIAG_E0_MODEL_COMPLETE',model,flush=True)
    result=dict(records=index,gate=e0_gate(clean_rows,plan['E0']),new_predictions_generated=False,test6_loaded=False,independent_final_loaded=False,observed_at=now())
    write(base/'e0_screen.json',result)

def construct_model(root,base,model_name,device):
    import torch
    from run_post_ab_n2 import load_anchors
    from model.rebuild_v1_d26 import build_experts
    binding,source_plan,complete=bind_model(root,model_name);source,folder=model_folder(root,model_name)
    source_files=read(source/'code_manifest.json')['files']
    used_files=[n for n in source_files if n.startswith('model/') or n in ('scripts/d24_data.py','scripts/post_d30_evaluation.py','scripts/d23_engine.py')]
    for name in used_files:
        if sha(base/'code'/name)!=source_files[name]:raise RuntimeError('model/inference/loader execution source differs '+name)
    binding['verified_source_files']={n:source_files[n] for n in used_files}
    # Old sampler/summary helpers changed during N1; neither is executed by
    # these new mask conditions. Model, inference, Loader and inputs are bound.
    anchors,_=load_anchors(root,source_plan);experts=build_experts(root,anchors);del anchors
    job=next(j for j in source_plan['jobs'] if j['id']==model_name)
    if model_name in ('A0','B1'):
        from model.rebuild_v1_post_d30 import PortfolioSegmenter
        model=PortfolioSegmenter(*experts,job)
    elif model_name.startswith('N1-'):
        from model.rebuild_v1_post_ab_n1 import N1Segmenter
        model=N1Segmenter(*experts,job)
    else:
        from model.rebuild_v1_post_ab_n2 import N2Segmenter
        model=N2Segmenter(*experts,job)
    state=torch.load(folder/'selected.pth',map_location='cpu',weights_only=False)
    if state['signature']!=complete['signature'] or state['global_step']!=complete['selected']['step']:raise RuntimeError('selected state signature differs')
    model.load_state_dict(state['model'],strict=True);del state
    return model.eval().requires_grad_(False).to(device),binding

def prepare_main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args()
    root,base=dirs(a.root,a.directory);plan=validate(read(base/'plan.json'));verify_snapshot(base);input_contract(root,plan)
    audit_predecessor(root,base,plan)
    from d24_data import Loader
    # Loader only permits declared fit12/Val2; no test/source discovery.
    loader=Loader(root,plan);prepare_masks(root,base,plan,loader);e0(root,base,plan,loader)
    write(base/'cpu_preparation_complete.json',dict(plan_sha256=sha(base/'plan.json'),source_audit_sha256=sha(base/'n2_source_audit.json'),masks_sha256=sha(base/'mask_manifest.json'),E0_sha256=sha(base/'e0_screen.json'),optimizer_updates=0,observed_at=now()))
if __name__=='__main__':prepare_main()
