"""Raw matrices, native U/E masks, source reuse and observable R0 routing."""
from pathlib import Path
import time
import numpy as np
import torch
import d23_engine as e
from post_s1_support_common import *
from post_d30_data import treatment
from post_d30_evaluation import infer,counts,regions,joint_counts,encode_joint,joint_report,save_prediction
from post_n5_evaluation import pool
from post_n2_masks import physical_view
def support_objective(model,batch):
    # Exactly the inherited paired-view CE, with separate branch exposure logs.
    from d26_data import ce
    full=torch.ones_like(batch['gt'],dtype=torch.bool);terms=[];denominators={};exposures={}
    for tag,rgb,ds,rm,dm in (('clean',batch['rgb'],batch['aux'],full,full),('aug',batch['rgb2'],batch['aux2'],batch['rm2'],batch['dm2'])):
        with torch.autocast(device_type=rgb.device.type,dtype=torch.bfloat16,enabled=rgb.is_cuda):parts=model(rgb,ds,rm,dm,return_parts=True)
        main,n=ce(parts['logits'],batch['gt'],rm|dm);r,nr=ce(parts['rgb'],batch['gt'],rm);d,nd=ce(parts['dsm'],batch['gt'],dm)
        terms.append(.5*main+.125*(r+d));exposures[tag]=dict(model.exposure)
        denominators.update({tag+'_fusion_pixels':n,tag+'_rgb_pixels':nr,tag+'_dsm_pixels':nd,
            tag+'_residual_support_pixels':model.exposure['residual_support_pixels']})
    model.exposure=dict(views=exposures,residual_support_pixels=sum(v['residual_support_pixels'] for v in exposures.values()),
        moved_tokens=sum(v['moved_tokens'] for v in exposures.values()),total_tokens=sum(v['total_tokens'] for v in exposures.values()))
    return sum(terms),denominators
def load_mask(base,tile,rule):
    row=read(base/'mask_manifest.json')['tiles'][tile][rule];path=within(row['path'],base)
    if sha(path)!=row['sha256']:raise RuntimeError('mask changed')
    with np.load(path,allow_pickle=False) as z:
        shape=tuple(int(x) for x in z['shape'])
        mask=np.unpackbits(z['bits'],bitorder='little',count=int(np.prod(shape))).reshape(shape).astype(bool)
    if list(mask.shape)!=row['shape'] or int(mask.sum())!=row['missing_pixels']:raise RuntimeError('decoded mask differs')
    return mask,row
def view_for(base,item,tile,key):
    if key in ('rgb_U','dsm_U'):
        m,mb=load_mask(base,tile,'U');v,rm,dm=physical_view(item,m,key.split('_')[0],'known_missing')
        return v,rm,dm,mb
    if key in E_KEYS:
        shape,quality=key[4:].split('__');m,mb=load_mask(base,tile,shape)
        op=torch.from_numpy(item['optical'].transpose(2,0,1).copy())[None];ds=torch.from_numpy(item['dsm'])[None]
        op,ds,rm,dm=treatment(op,ds,quality,e.key(42,'D26_eval',tile))
        rm[0]&=torch.from_numpy(~m);op=op.masked_fill(~rm[:,None],0)
        return dict(optical=op[0].permute(1,2,0).numpy(),dsm=ds[0].numpy()),rm[0].numpy(),dm[0].numpy(),mb
    raise ValueError('unregistered evaluation condition')
def source_case(root,name,tag,key,tile):
    binding,_,c=source_binding(root,name,checkpoint=False);f=root/'records'/SOURCE_NAME/'jobs'/name
    record=f/tag/key/(tile+'.json');row=read(record)
    if row['binding']['training']!=c['signature']:raise RuntimeError('source prediction training differs')
    if tag in ('evaluation','support_evaluation') and row['binding']['selected']!=c['selected']:raise RuntimeError('source selected differs')
    pred={}
    for n in ('candidate','fixed_rgb','fixed_dsm'):
        path=record.parent/n/(tile+'.npy')
        if sha(path)!=row['predictions'][n]:raise RuntimeError('source prediction SHA changed')
        pred[n]=np.load(path,allow_pickle=False)
    return pred,row,dict(record=str(record),record_sha256=sha(record),binding=binding)
def write_case(folder,key,tile,item,rm,dm,preds,binding,mb=None,reference=None):
    rgs=regions(rm,dm);missing=(~dm)&rm if key=='dsm_U' else (~rm)&dm
    rgs.update(mask_location=missing,other_locations=~missing)
    if 'geom_' in key:
        interior=np.zeros_like(rm);interior[8:-8,8:-8]=True
        rgs={n:m&interior for n,m in rgs.items()}
    scopes={}
    for scope in ('full','noboundary'):
        gt=item[scope+'_gt'];js={r:joint_counts(gt,preds['fixed_rgb'],preds['fixed_dsm'],preds['candidate'],m) for r,m in rgs.items() if r!='neither'}
        scopes[scope]=dict(metrics={n:{r:counts(gt,p,m) for r,m in rgs.items()} for n,p in preds.items()},
            joint={r:encode_joint(x) for r,x in js.items()},joint_reports={r:joint_report(x) for r,x in js.items()})
    hashes={n:save_prediction(folder/key/n/(tile+'.npy'),p) for n,p in preds.items()}
    row=dict(binding=binding,tile=tile,condition=key,mask_binding=mb,fixed_reference=reference,scopes=scopes,
        predictions=hashes,confusion_matrix_dtype='int64',test6_loaded=False,independent_final_loaded=False)
    write(folder/key/(tile+'.json'),row);return row
def finish_summary(folder,tiles,binding):
    result=dict(binding=binding,tiles=tiles,pooled=pool(tiles),test6_loaded=False,independent_final_loaded=False,
        metric='Potsdam Val2 native512 stride256 NoBoundary fg5; Full diagnostic',observed_at=now())
    write(folder/'summary.json',result);return result
def extra_eval(model,loader,refs,p,out,binding,progress,base,keys,tag):
    folder=out/tag;tiles={}
    for tile in p['data']['validation']:
        item=loader(tile,True)
        for key in keys:
            view,rm,dm,mb=view_for(base,item,tile,key)
            report=lambda **kw:progress(phase=tag,tile=tile,condition=key,**kw)
            report();began=time.monotonic();pred,_=infer(model,view,rm,dm,report)
            inference_seconds=time.monotonic()-began
            fixed,fb=refs.get(tile,'support_'+key,view,rm,dm,progress=report)
            values=dict(candidate=pred['candidate'],fixed_rgb=fixed['rgb'],fixed_dsm=fixed['dsm'])
            row=write_case(folder,key,tile,item,rm,dm,values,binding,mb,fb)
            row['cost']=dict(candidate_native_tile_inference_seconds=inference_seconds,batch=8,
                peak_allocated_bytes=torch.cuda.max_memory_allocated() if torch.cuda.is_available() else None,
                fixed_reference_inference_excluded=True)
            write(folder/key/(tile+'.json'),row);tiles.setdefault(key,{})[tile]=row
            if getattr(model,'frozen_base',False) and model.job['local_only'] and key in ('rgb_U','dsm_U'):
                ref,_,_=source_case(loader.root,'S1-0','support_evaluation',key,tile)
                allowed=(~rm)&dm
                if not np.array_equal(values['candidate'][~allowed],ref['candidate'][~allowed]):raise RuntimeError('frozen local tile protection differs from S1-0')
            if getattr(model,'frozen_base',False) and model.job['local_only'] and key in E_KEYS:
                f=Path(p['predecessor_directory'])/'jobs/E/S1-0/evaluation'/key
                row=read(f/(tile+'.json'));path=f/'candidate'/(tile+'.npy')
                if sha(path)!=row['predictions']['candidate']:raise RuntimeError('E base changed')
                ref=np.load(path,allow_pickle=False);allowed=(~rm)&dm
                if not np.array_equal(values['candidate'][~allowed],ref[~allowed]):raise RuntimeError('E tile outside-support changed')
            print('SUPPORT_EXTRA_EVAL',tag,tile,key,flush=True)
        del item
    return finish_summary(folder,tiles,binding)
def simple_route(control,context,rm,dm,window=512,stride=256):
    """Observable hard splice; conservative all-missing window guard, no labels."""
    from scipy.ndimage import minimum_filter
    # Per-window guard must not depend on labels or a corruption identifier.
    observed=np.zeros_like(rm)
    for y in e.positions(rm.shape[0],window,stride):
        for x in e.positions(rm.shape[1],window,stride):
            crop=rm[y:y+window,x:x+window]
            if crop.any():observed[y:y+window,x:x+window]=True
    use=(~rm)&dm&observed
    return np.where(use,context,control).astype(np.uint8),use
def transition(gt,control,candidate,mask):
    valid=(gt<6)&(control<6)&(candidate<6)&mask
    a=control==gt;b=candidate==gt
    return dict(valid=int(valid.sum()),rescued=int((valid&~a&b).sum()),harmed=int((valid&a&~b).sum()),
        both_correct=int((valid&a&b).sum()),both_wrong=int((valid&~a&~b).sum()),
        by_class={str(c):dict(valid=int((valid&(gt==c)).sum()),rescued=int((valid&(gt==c)&~a&b).sum()),harmed=int((valid&(gt==c)&a&~b).sum())) for c in range(6)},
        control=counts(gt,control,mask),candidate=counts(gt,candidate,mask))
