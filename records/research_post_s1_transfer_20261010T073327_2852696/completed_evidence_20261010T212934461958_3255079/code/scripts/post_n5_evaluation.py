"""Whole-tile frozen U/H/L/T; original fixed anchors and raw counts."""
import os
from pathlib import Path
import numpy as np
from post_n5_common import read,write,sha,now
from post_n5_data import load_mask
from post_n2_masks import physical_view
from post_d30_evaluation import infer,regions,counts,joint_counts,encode_joint,joint_report,metric,decode_joint,save_prediction
def pool(tiles):
    pooled={}
    for condition,rows in tiles.items():
        pooled[condition]={};sample=next(iter(rows.values()))
        for scope in ('full','noboundary'):
            metrics={n:{r:metric(sum((np.asarray(row['scopes'][scope]['metrics'][n][r]['cm'],np.int64) for row in rows.values()),np.zeros((6,6),np.int64))) for r in sample['scopes'][scope]['metrics'][n]} for n in sample['scopes'][scope]['metrics']}
            js={r:sum((decode_joint(row['scopes'][scope]['joint'][r]) for row in rows.values()),np.zeros((6,)*4,np.int64)) for r in sample['scopes'][scope]['joint']}
            pooled[condition][scope]=dict(metrics=metrics,joint={r:encode_joint(x) for r,x in js.items()},joint_reports={r:joint_report(x) for r,x in js.items()})
    return pooled
def evaluate_content(model,loader,refs,plan,out,binding,progress,base,tag):
    folder=out/tag;tiles={}
    for tile in plan['data']['validation']:
        item=loader(tile,True)
        for direction in ('rgb','dsm'):
            for rule in ('U','H','L','T'):
                key=direction+'_'+rule;missing,mb=load_mask(base,tile,rule)
                view,rm,dm=physical_view(item,missing,direction,'known_missing')
                report=lambda **kw:progress(phase=tag,tile=tile,condition=key,**kw)
                report();pred,identity=infer(model,view,rm,dm,report)
                fixed,fb=refs.get(tile,'content_'+key,view,rm,dm,progress=report)
                pred.update({'fixed_'+n:p for n,p in fixed.items()})
                scopes={};rgs=regions(rm,dm)
                rgs.update(mask_location=missing,other_locations=~missing)
                for scope in ('full','noboundary'):
                    gt=item[scope+'_gt'];js={r:joint_counts(gt,fixed['rgb'],fixed['dsm'],pred['candidate'],m) for r,m in rgs.items() if r!='neither'}
                    scopes[scope]=dict(metrics={n:{r:counts(gt,p,m) for r,m in rgs.items()} for n,p in pred.items()},joint={r:encode_joint(x) for r,x in js.items()},joint_reports={r:joint_report(x) for r,x in js.items()})
                hashes={n:save_prediction(folder/key/n/(tile+'.npy'),p) for n,p in pred.items()}
                row=dict(binding=binding,tile=tile,condition=key,mask_binding=mb,fixed_reference=fb,scopes=scopes,predictions=hashes,fallback_logits_equal_own=identity,confusion_matrix_dtype='int64',test6_loaded=False,independent_final_loaded=False)
                write(folder/key/(tile+'.json'),row);tiles.setdefault(key,{})[tile]=row
                print('N5_CONTENT_EVAL',tag,tile,key,flush=True);del view,pred,fixed,scopes,js,missing
        del item
    result=dict(binding=binding,tiles=tiles,pooled=pool(tiles),test6_loaded=False,independent_final_loaded=False,metric='Potsdam Val2 native512 stride256 NoBoundary fg5',observed_at=now())
    write(folder/'summary.json',result);return result
def reuse_content(out,binding):
    source=out/'content_fixed8000';target=out/'content_evaluation';s=read(source/'summary.json')
    for key,rows in s['tiles'].items():
        for tile,row in rows.items():
            old=source/key/(tile+'.json');row['reused_from']=dict(path=str(old),sha256=sha(old));row['binding']=binding
            for n,digest in row['predictions'].items():
                p=source/key/n/(tile+'.npy');q=target/key/n/(tile+'.npy')
                if sha(p)!=digest:raise RuntimeError('reuse prediction changed')
                q.parent.mkdir(parents=True,exist_ok=True);os.link(p,q)
            write(target/key/(tile+'.json'),row)
    s['binding']=binding;s['observed_at']=now();write(target/'summary.json',s)

