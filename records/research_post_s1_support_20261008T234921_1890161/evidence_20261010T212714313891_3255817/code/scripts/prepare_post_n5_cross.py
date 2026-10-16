"""Existing predictions only: composition and frozen N5 boundary recheck."""
import argparse
from pathlib import Path
import numpy as np
from post_n5_cross_common import *
from post_n2_diag_common import bind_model
from post_n2_diag_runtime import input_contract,spatial_stats,e0_gate,read_prediction,source_row
from post_n2_masks import boundary_band
from post_d30_evaluation import counts
def decode_mask(row,allowed):
    path=within(row['path'],allowed)
    if sha(path)!=row['sha256']:raise RuntimeError('mask SHA changed')
    with np.load(path,allow_pickle=False) as z:
        shape=tuple(int(x) for x in z['shape'])
        m=np.unpackbits(z['bits'],bitorder='little',count=int(np.prod(shape))).reshape(shape).astype(bool)
    if list(m.shape)!=row['shape'] or int(m.sum())!=row['missing_pixels'] or int(m.sum())*4!=m.size:raise RuntimeError('mask content contract changed')
    return m
def strata(gt,pred,band,mask):
    result={}
    for c in range(5):
        for side,partition in [('boundary',band),('interior',~band)]:
            key=f'{c}_{side}';region=mask&(gt==c)&partition;cm=counts(gt,pred,region)
            result[key]=dict(cm=cm['cm'],support=cm['valid'],correct=sum(cm['TP']))
    return result
def standardize(rows,weights,min_support=100):
    keys=[k for k in weights if all(row[k]['support']>=min_support for row in rows.values())]
    mass=sum(weights[k] for k in keys);total=sum(weights.values())
    normalized={k:weights[k]/mass for k in keys} if mass else {}
    return dict(common_strata=keys,weight_counts=weights,normalized_weights=normalized,
        covered_weight_fraction=mass/total if total else None,
        standardized_accuracy={name:sum(normalized[k]*row[k]['correct']/row[k]['support'] for k in keys) if mass else None for name,row in rows.items()},
        claim='masked-pixel class/boundary standardized accuracy; not corrected mIoU or causal effect')
def n5_row(root,name,condition,tile,tag='evaluation'):
    binding,p,c=n5_binding(root,name);folder=Path(binding['directory'])/'jobs'/name
    record=folder/tag/condition/(tile+'.json');row=read(record)
    if row['binding']['training']!=c['signature'] or row['binding']['selected']!=c['selected']:raise RuntimeError('N5 case completion binding differs')
    return folder,row,record
def n5_preds(folder,row,condition,tile,tag,names):
    out={}
    for name in names:
        path=folder/tag/condition/name/(tile+'.npy')
        if sha(path)!=row['predictions'][name]:raise RuntimeError('source prediction SHA changed')
        out[name]=np.load(path,allow_pickle=False)
    return out
def prepare(root,base):
    p=validate(read(base/'plan.json'));verify_snapshot(base);input_contract(root,p)
    acceptance=released(root);write(base/'source_acceptance.json',acceptance)
    diag=Path(p['source_diag_directory']);manifest=read(diag/'mask_manifest.json')
    n5=Path(p['source_N5_directory']);n5_masks=read(n5/'mask_manifest.json')
    prep=read(diag/'cpu_preparation_complete.json')
    if prep['masks_sha256']!=sha(diag/'mask_manifest.json'):raise RuntimeError('source diagnostic mask manifest changed')
    masks={};decoded={}
    for tile in p['data']['validation']:
        masks[tile]={}
        for rule in p['E3']['rules']:
            original=manifest['tiles'][tile][rule];m=decode_mask(original,diag)
            if not np.array_equal(m,decode_mask(n5_masks['tiles'][tile][rule],n5)):raise RuntimeError('N5 vs diagnostic masks differ')
            target=base/'masks'/tile/(rule+'.npz');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(Path(original['path']).read_bytes())
            masks[tile][rule]=dict(original,path=str(target),reused_source=dict(path=original['path'],sha256=original['sha256']))
            decoded[tile,rule]=m
    write(base/'mask_manifest.json',dict(plan_sha256=sha(base/'plan.json'),source_manifest_sha256=sha(diag/'mask_manifest.json'),tiles=masks))
    from d24_data import Loader
    loader=Loader(root,p);e3_index={};boundaries={}
    # No fit12 loading, calibration, new masks, training or reserved T evaluation.
    for tile in p['data']['validation']:
        item=loader(tile,True);band=boundary_band(item['full_gt'],4);nb=item['noboundary_gt']
        weights={f'{c}_{side}':int(((nb==c)&partition).sum()) for c in range(5) for side,partition in [('boundary',band),('interior',~band)]}
        for name in p['E3']['models']:
            if name.startswith('N5'):
                binding,_,completion=n5_binding(root,name)
            else:
                binding,_,_=bind_model(root,name,checkpoint=False)
                folder=diag/'jobs'/('E1_'+name);completion=read(folder/'complete.json')
                if completion['optimizer_updates']!=0 or sha(folder/'summary.json')!=completion['summary_sha256']:raise RuntimeError('E1 completion changed')
                if completion['signature']['model_binding']['checkpoint_sha256']!=binding['checkpoint_sha256']:raise RuntimeError('E1 model binding changed')
            for direction in p['E3']['directions']:
                rows={};sources={};whole={}
                for rule in p['E3']['rules']:
                    key=direction+'_'+rule
                    if name.startswith('N5'):
                        folder,row,record=n5_row(root,name,key,tile,'content_evaluation')
                        pred=n5_preds(folder,row,key,tile,'content_evaluation',['candidate'])['candidate']
                        if row['mask_binding']['sha256']!=n5_masks['tiles'][tile][rule]['sha256']:raise RuntimeError('N5 source case mask differs')
                    else:
                        record=folder/'evaluation'/key/(tile+'.json');row=read(record)
                        if row['binding']['training']!=completion['signature']:raise RuntimeError('E1 case binding changed')
                        if row['mask_binding']['sha256']!=manifest['tiles'][tile][rule]['sha256']:raise RuntimeError('E1 source case mask differs')
                        pred=read_prediction(folder,row,key,tile,'candidate')
                    if pred.shape!=nb.shape or not np.isin(pred,[0,1,2,3,4,5,255]).all():raise RuntimeError('invalid source prediction')
                    current=row['scopes']['noboundary']['metrics']['candidate']
                    old=current.get('valid',current.get('all'))
                    whole[rule]=counts(nb,pred,np.ones(nb.shape,bool))
                    if whole[rule]['cm']!=old['cm']:raise RuntimeError('original whole-tile CM does not reproduce')
                    rows[rule]=strata(nb,pred,band,decoded[tile,rule])
                    sources[rule]=dict(record=str(record),record_sha256=sha(record),prediction_sha256=row['predictions']['candidate'])
                    del pred
                target=base/'E3'/name/direction/(tile+'.json')
                write(target,dict(model=name,tile=tile,direction=direction,binding=binding,sources=sources,
                    scope='noboundary',boundary_definition='Full gt radius4, labels for post-hoc evaluation only',
                    strata=rows,whole=whole,standardized=standardize(rows,weights,p['E3']['min_stratum_pixels']),
                    mask_manifest_sha256=sha(base/'mask_manifest.json'),optimizer_updates=0,test6_loaded=False))
                e3_index[name+'/'+direction+'/'+tile]=dict(path=str(target),sha256=sha(target))
            if name in ('N5-0','N5-3'):
                folder,row,record=n5_row(root,name,'clean',tile)
                preds=n5_preds(folder,row,'clean',tile,'evaluation',['candidate','fixed_rgb','fixed_dsm'])
                if any(x.shape!=nb.shape for x in preds.values()):raise RuntimeError('clean prediction shape differs')
                scopes={scope:{'boundary4':spatial_stats(item[scope+'_gt'],preds,band),
                    'interior':spatial_stats(item[scope+'_gt'],preds,(item[scope+'_gt']<6)&~band)} for scope in ('full','noboundary')}
                original=counts(nb,preds['candidate'],np.ones(nb.shape,bool))
                if original['cm']!=row['scopes']['noboundary']['metrics']['candidate']['valid']['cm']:raise RuntimeError('N5 clean CM differs')
                target=base/'E0_postN5'/name/(tile+'.json')
                write(target,dict(model=name,tile=tile,binding=binding,source_record=str(record),source_sha256=sha(record),
                    predictions=row['predictions'],scopes=scopes,optimizer_updates=0,test6_loaded=False))
                boundaries.setdefault(name,{})[tile]=scopes;del preds,scopes
            write(base/'cpu_progress.json',dict(phase='existing_predictions',model=name,tile=tile,observed_at=now()))
            print('CROSS_CPU_MODEL_TILE',name,tile,flush=True)
        del item,band,nb
    gates={name:e0_gate(rows,p['E0']) for name,rows in boundaries.items()}
    for name,g in gates.items():g['model']=name
    write(base/'e3_screen.json',dict(records=e3_index,scope='noboundary',automatic_training=False))
    write(base/'boundary_screen.json',dict(models=gates,N3_problem_trigger=all(x['N3_problem_trigger'] for x in gates.values()) and set(gates)=={'N5-0','N5-3'}))
    write(base/'cpu_preparation_complete.json',dict(plan_sha256=sha(base/'plan.json'),masks_sha256=sha(base/'mask_manifest.json'),
        E3_sha256=sha(base/'e3_screen.json'),boundary_sha256=sha(base/'boundary_screen.json'),
        source_acceptance_sha256=sha(base/'source_acceptance.json'),source_inputs=loader.verified,optimizer_updates=0,observed_at=now()))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args()
    root,base=dirs(a.root,a.directory);prepare(root,base)
if __name__=='__main__':main()
