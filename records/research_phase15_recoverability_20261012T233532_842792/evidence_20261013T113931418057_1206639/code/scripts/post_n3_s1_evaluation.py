"""Only frozen U local-missing evaluation; no T/new content selection."""
import os
from pathlib import Path
import numpy as np
from post_n3_s1_common import read,write,sha,now
from post_n2_diag_runtime import load_mask
from post_n2_masks import physical_view
from post_d30_evaluation import infer,regions,counts,joint_counts,encode_joint,joint_report,save_prediction
from post_n5_evaluation import pool
def evaluate_U(model,loader,refs,plan,out,binding,progress,base,tag):
    folder=out/tag;tiles={}
    for tile in plan['data']['validation']:
        item=loader(tile,True);missing,mb=load_mask(base,tile,'U')
        for direction in ('rgb','dsm'):
            key=direction+'_U';view,rm,dm=physical_view(item,missing,direction,'known_missing')
            report=lambda **kw:progress(phase=tag,tile=tile,condition=key,**kw)
            report();pred,identity=infer(model,view,rm,dm,report)
            fixed,fb=refs.get(tile,'support_'+key,view,rm,dm,progress=report)
            pred.update({'fixed_'+n:p for n,p in fixed.items()});scopes={};rgs=regions(rm,dm);rgs.update(mask_location=missing,other_locations=~missing)
            for scope in ('full','noboundary'):
                gt=item[scope+'_gt'];js={r:joint_counts(gt,fixed['rgb'],fixed['dsm'],pred['candidate'],m) for r,m in rgs.items() if r!='neither'}
                scopes[scope]=dict(metrics={n:{r:counts(gt,p,m) for r,m in rgs.items()} for n,p in pred.items()},
                    joint={r:encode_joint(x) for r,x in js.items()},joint_reports={r:joint_report(x) for r,x in js.items()})
            hashes={n:save_prediction(folder/key/n/(tile+'.npy'),p) for n,p in pred.items()}
            row=dict(binding=binding,tile=tile,condition=key,mask_binding=mb,fixed_reference=fb,scopes=scopes,predictions=hashes,
                fallback_logits_equal_own=identity,confusion_matrix_dtype='int64',test6_loaded=False,independent_final_loaded=False)
            write(folder/key/(tile+'.json'),row);tiles.setdefault(key,{})[tile]=row
            print('NS_U_EVAL',tag,tile,key,flush=True);del view,pred,fixed,scopes,js
        del item,missing
    result=dict(binding=binding,tiles=tiles,pooled=pool(tiles),test6_loaded=False,independent_final_loaded=False,observed_at=now())
    write(folder/'summary.json',result);return result
def reuse_U(out,binding):
    source=out/'support_fixed8000';target=out/'support_evaluation';s=read(source/'summary.json')
    for key,rows in s['tiles'].items():
        for tile,row in rows.items():
            old=source/key/(tile+'.json');row['reused_from']=dict(path=str(old),sha256=sha(old));row['binding']=binding
            for name,digest in row['predictions'].items():
                p=source/key/name/(tile+'.npy');q=target/key/name/(tile+'.npy')
                if sha(p)!=digest:raise RuntimeError('reuse source changed')
                q.parent.mkdir(parents=True,exist_ok=True);os.link(p,q)
            write(target/key/(tile+'.json'),row)
    s['binding']=binding;s['observed_at']=now();write(target/'summary.json',s)
