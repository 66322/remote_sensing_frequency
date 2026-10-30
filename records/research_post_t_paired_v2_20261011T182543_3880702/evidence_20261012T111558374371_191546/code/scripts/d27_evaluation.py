"""Val2 only. Stitched predictions, bilateral fallback and raw joint counts."""
from pathlib import Path
import time
import numpy as np
import torch
import d23_engine as e
from d27_data import treatment
from d26_common import read,write,sha,now

def metric(cm):
    cm=np.asarray(cm,np.int64);tp=np.diag(cm);support=cm.sum(1);fp=cm.sum(0)-tp;fn=support-tp
    union=tp+fp+fn;iou=np.divide(tp,union,out=np.full(6,np.nan),where=union>0)
    avg=lambda x:float(np.nanmean(x)) if np.isfinite(x).any() else None
    return dict(cm=cm.tolist(),support=support.tolist(),TP=tp.tolist(),FP=fp.tolist(),FN=fn.tolist(),IoU=[float(v) if np.isfinite(v) else None for v in iou],mIoU_fg5=avg(iou[:5]),mIoU_6=avg(iou),valid=int(cm.sum()))

def counts(gt,pred,region):
    if not region.any():return metric(np.zeros((6,6),np.int64))
    keep=(gt<6)&region&(pred<6)
    return metric(np.bincount(6*gt[keep].astype(np.int64)+pred[keep].astype(np.int64),minlength=36).reshape(6,6))

def regions(rm,dm):
    from scipy.ndimage import minimum_filter
    both=rm&dm;valid=rm|dm
    # A declared 16px border diagnostic, not a complete expert receptive field.
    interior=minimum_filter(both,size=33,mode='constant',cval=0)
    if rm.all() and dm.all():
        empty=np.zeros_like(both)
        return dict(valid=both,both=both,rgb_only=empty,dsm_only=empty,neither=empty,missing_union=empty,boundary16=both&~interior)
    return dict(valid=valid,both=both,rgb_only=rm&~dm,dsm_only=dm&~rm,neither=~valid,missing_union=~both&valid,boundary16=valid&~interior)

def joint_counts(gt,rgb,dsm,candidate,region):
    if not region.any():return np.zeros((6,)*4,np.int64)
    keep=(gt<6)&region&(rgb<6)&(dsm<6)&(candidate<6)
    g,r,d,f=(x[keep].astype(np.int64) for x in (gt,rgb,dsm,candidate))
    return np.bincount(((g*6+r)*6+d)*6+f,minlength=6**4).reshape((6,)*4).astype(np.int64)

def encode_joint(array):
    flat=np.asarray(array,np.int64).reshape(-1);indices=np.flatnonzero(flat)
    return dict(shape=[6,6,6,6],dtype='int64',format='sparse_flat_index_count',nonzero=[[int(i),int(flat[i])] for i in indices])

def decode_joint(row):
    flat=np.zeros(6**4,np.int64)
    if row['shape']!=[6,6,6,6] or row['dtype']!='int64':raise ValueError('joint format differs')
    for index,count in row['nonzero']:flat[index]=count
    return flat.reshape((6,)*4)

def joint_report(joint):
    out={};g,r,d,f=np.indices((6,)*4)
    for name,mask in {'both_correct':(r==g)&(d==g),'only_rgb_correct':(r==g)&(d!=g),'only_dsm_correct':(r!=g)&(d==g),'both_wrong':(r!=g)&(d!=g)}.items():
        total=int(joint[mask].sum());correct=int(joint[mask&(f==g)].sum())
        out[name]=dict(valid=total,fused_correct=correct,fused_wrong=total-correct,retention=correct/total if total else None,
                       by_class={str(c):dict(valid=int(joint[mask&(g==c)].sum()),fused_correct=int(joint[mask&(g==c)&(f==g)].sum())) for c in range(6)})
    return out

def infer(model,item,rm,dm,progress=lambda **kw:None,batch=8,fixed_only=False):
    h,w=rm.shape;coords=[(y,x) for y in e.positions(h,512,256) for x in e.positions(w,512,256)]
    names=['rgb','dsm','probability_average','availability_switch'] if fixed_only else ['candidate','rgb','dsm','probability_average','availability_switch']
    scores={n:np.zeros((6,h,w),np.float32) for n in names};coverage=np.zeros((h,w),np.uint16)
    identity={'rgb_only':True,'dsm_only':True};last=time.monotonic()
    device=next(model.parameters()).device
    with torch.inference_mode():
        for start in range(0,len(coords),batch):
            cs=coords[start:start+batch];real=len(cs)
            arrays=[np.stack([item['optical'][y:y+512,x:x+512].transpose(2,0,1) for y,x in cs]),np.stack([item['dsm'][y:y+512,x:x+512] for y,x in cs]),np.stack([rm[y:y+512,x:x+512] for y,x in cs]),np.stack([dm[y:y+512,x:x+512] for y,x in cs])]
            tensors=[]
            for value in arrays:
                t=torch.from_numpy(value).to(device)
                if real<batch:t=torch.cat((t,t[-1:].expand((batch-real,)+t.shape[1:])))
                tensors.append(t)
            op,ds,r_mask,d_mask=tensors
            parts=model(op,ds,r_mask,d_mask,return_parts=True)
            zr,zd=parts['rgb'].float(),parts['dsm'].float()
            both=(r_mask&d_mask)[:,None]
            single=torch.where(r_mask[:,None],zr,zd)
            values=dict(rgb=zr,dsm=zd,probability_average=torch.where(both,(zr.softmax(1)+zd.softmax(1))/2,single),availability_switch=torch.where(r_mask[:,None],zr,zd))
            if not fixed_only:
                values['candidate']=parts['logits'].float()
                for key,mask,reference in (('rgb_only',r_mask&~d_mask,zr),('dsm_only',d_mask&~r_mask,zd)):
                    identity[key]&=bool(torch.equal(values['candidate'].masked_select(mask[:,None]),reference.masked_select(mask[:,None])))
            for name,z in values.items():
                for a,(y,x) in zip(z[:real].cpu().numpy(),cs):scores[name][:,y:y+512,x:x+512]+=a
            for y,x in cs:coverage[y:y+512,x:x+512]+=1
            del tensors,op,ds,parts,zr,zd,values,single
            if time.monotonic()-last>=30 or start+batch>=len(coords):
                progress(windows_done=min(start+batch,len(coords)),windows_total=len(coords));last=time.monotonic()
    if not coverage.all() or any(not np.isfinite(z).all() for z in scores.values()):raise RuntimeError('invalid stitch/coverage')
    valid=rm|dm
    if not fixed_only:
        for key,mask,ref in (('rgb_only',rm&~dm,'rgb'),('dsm_only',dm&~rm,'dsm')):
            identity[key]&=np.array_equal(scores['candidate'][:,mask],scores[ref][:,mask])
            if not identity[key]:raise RuntimeError('bilateral own-logit fallback broken')
    predictions={n:z.argmax(0).astype(np.uint8) for n,z in scores.items()}
    for pred in predictions.values():pred[~valid]=255
    return predictions,identity

def save_prediction(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp')
    with tmp.open('wb') as f:np.save(f,value)
    tmp.replace(path);return sha(path)

class FixedPair(torch.nn.Module):
    def __init__(self,rgb,dsm):super().__init__();self.rgb_expert=rgb;self.dsm_expert=dsm
    def forward(self,op,ds,rm,dm,return_parts=True):
        op=op.masked_fill(~rm[:,None],0);ds=ds.masked_fill(~dm,0)
        r,_=self.rgb_expert(op,ds);d,_=self.dsm_expert(op,ds)
        return dict(rgb=r,dsm=d)

class References:
    def __init__(self,base,factory):
        self.base=Path(base);self.factory=factory;self.model=None
        self.binding=dict(experts=read(self.base/'plan.json')['experts'],sources=read(self.base/'code_manifest.json'),input_manifest=read(self.base/'plan.json')['input_manifest_sha256'])
    def get(self,tile,condition,item,rm,dm,provided=None,progress=lambda **kw:None):
        folder=self.base/'shared_reference'/condition/tile;folder.mkdir(parents=True,exist_ok=True)
        import fcntl
        with (folder/'writer.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            record=folder/'complete.json'
            if not record.exists():
                if provided is None:
                    if self.model is None:self.model=self.factory().eval().requires_grad_(False)
                    predictions,_=infer(self.model,item,rm,dm,progress,fixed_only=True)
                else:predictions={n:p for n,p in provided.items() if n!='candidate'}
                hashes={n:save_prediction(folder/(n+'.npy'),p) for n,p in predictions.items()}
                write(record,dict(binding=self.binding,tile=tile,condition=condition,predictions=hashes,test6_loaded=False))
            row=read(record)
            if row['binding']!=self.binding or row['tile']!=tile or row['condition']!=condition:raise RuntimeError('reference binding changed')
            result={}
            for n,digest in row['predictions'].items():
                path=folder/(n+'.npy')
                if sha(path)!=digest:raise RuntimeError('reference prediction changed')
                result[n]=np.load(path)
                if provided is not None and not np.array_equal(provided[n],result[n]):raise RuntimeError('frozen experts differ from shared reference')
            return result,dict(path=str(record),sha256=sha(record))

def selection(model,loader,plan,out,binding,step,progress):
    target=Path(out)/'validation'/('step_%04d.json'%step)
    if target.exists():
        row=read(target)
        if row['binding']!=binding:raise RuntimeError('selection binding changed')
        return row
    rows={};values=[]
    for condition in plan['training']['selection_states']:
        rows[condition]={}
        for tile in plan['data']['validation']:
            item=loader(tile,True);op=torch.from_numpy(item['optical'].transpose(2,0,1).copy())[None];ds=torch.from_numpy(item['dsm'])[None]
            op,ds,rm,dm=treatment(op,ds,condition,e.key(42,'D26_eval',tile))
            view=dict(optical=op[0].permute(1,2,0).numpy(),dsm=ds[0].numpy())
            progress(phase='checkpoint_selection',step=step,tile=tile,condition=condition)
            pred,_=infer(model,view,rm[0].numpy(),dm[0].numpy(),progress=lambda **kw:progress(phase='checkpoint_selection',step=step,tile=tile,condition=condition,**kw))
            rows[condition][tile]=counts(item['noboundary_gt'],pred['candidate'],(rm|dm)[0].numpy())
        values.append(metric(sum(np.asarray(r['cm'],np.int64) for r in rows[condition].values()))['mIoU_fg5'])
    result=dict(binding=binding,step=step,tiles=rows,state_metrics=dict(zip(plan['training']['selection_states'],values)),score=sum(values)/3,test6_loaded=False,observed_at=now())
    write(target,result);return result

def evaluate(model,loader,refs,plan,out,binding,progress,conditions=None,tag='evaluation'):
    out=Path(out)/tag;tiles={}
    conditions=conditions or (plan['evaluation']['primary']+plan['evaluation']['missing']+sum(plan['evaluation']['local'].values(),[])+plan['evaluation']['diagnostic'])
    for tile in plan['data']['validation']:
        item=loader(tile,True);op=torch.from_numpy(item['optical'].transpose(2,0,1).copy())[None];ds=torch.from_numpy(item['dsm'])[None]
        for condition in conditions:
            record=out/condition/(tile+'.json')
            if record.exists():
                row=read(record)
                if row['binding']!=binding:raise RuntimeError('evaluation binding changed')
                for n,digest in row['predictions'].items():
                    if sha(out/condition/n/(tile+'.npy'))!=digest:raise RuntimeError('candidate prediction changed')
                tiles.setdefault(condition,{})[tile]=row;continue
            op2,ds2,rm,dm=treatment(op,ds,condition,e.key(42,'D26_eval',tile))
            rm,dm=rm[0].numpy(),dm[0].numpy();view=dict(optical=op2[0].permute(1,2,0).numpy(),dsm=ds2[0].numpy())
            report=lambda **kw:progress(phase=tag,tile=tile,condition=condition,**kw)
            report();model.reset_route_stats();preds,identity=infer(model,view,rm,dm,report);route_stats=model.route_stats()
            fixed,provenance=refs.get(tile,condition,view,rm,dm,provided=preds if model.arm!='J0' else None,progress=report)
            # Own branches of J0 are diagnostic; scientific partitions use fixed anchors.
            preds.update({'fixed_'+n:(preds[n] if model.arm!='J0' else p) for n,p in fixed.items()})
            hashes={n:save_prediction(out/condition/n/(tile+'.npy'),p) for n,p in preds.items()}
            scopes={};rgs=regions(rm,dm)
            for scope in ('full','noboundary'):
                gt=item[scope+'_gt']
                metric_cache={};joint_cache={};metrics={};joints={}
                for n,p in preds.items():
                    metrics[n]={}
                    for region,mask in rgs.items():
                        key=(id(p),id(mask))
                        if key not in metric_cache:metric_cache[key]=counts(gt,p,mask)
                        metrics[n][region]=metric_cache[key]
                for region,mask in rgs.items():
                    if region=='neither':continue
                    key=id(mask)
                    if key not in joint_cache:joint_cache[key]=joint_counts(gt,fixed['rgb'],fixed['dsm'],preds['candidate'],mask)
                    joints[region]=joint_cache[key]
                scopes[scope]=dict(metrics=metrics,joint={r:encode_joint(v) for r,v in joints.items()},joint_reports={r:joint_report(v) for r,v in joints.items()})
            row=dict(binding=binding,tile=tile,condition=condition,route_diagnostics=route_stats,scopes=scopes,predictions=hashes,fixed_reference=provenance,fallback_logits_equal_own=identity,coverage={r:int(m.sum()) for r,m in rgs.items()},confusion_matrix_dtype='int64',joint_axes=['truth','fixed_rgb','fixed_dsm','candidate'],observed_at=now())
            write(record,row);tiles.setdefault(condition,{})[tile]=row;print('D26_EVAL',tag,tile,condition,flush=True)
            del op2,ds2,view,preds,fixed,scopes,joints,rgs
    pooled={}
    for condition,rows in tiles.items():
        pooled[condition]={}
        sample=next(iter(rows.values()))
        for scope in ('full','noboundary'):
            metrics={n:{region:metric(sum(np.asarray(r['scopes'][scope]['metrics'][n][region]['cm'],np.int64) for r in rows.values())) for region in sample['scopes'][scope]['metrics'][n]} for n in sample['scopes'][scope]['metrics']}
            joint={region:sum(decode_joint(r['scopes'][scope]['joint'][region]) for r in rows.values()) for region in sample['scopes'][scope]['joint']}
            pooled[condition][scope]=dict(metrics=metrics,joint={r:encode_joint(v) for r,v in joint.items()},joint_reports={r:joint_report(v) for r,v in joint.items()})
    result=dict(binding=binding,pooled=pooled,tiles=tiles,test6_loaded=False,independent_final_loaded=False,metric='Potsdam Val2 native512 stride256 NoBoundary fg5',confusion_matrix_dtype='int64',observed_at=now())
    write(out/'summary.json',result);return result
