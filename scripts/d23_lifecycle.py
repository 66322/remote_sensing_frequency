"""Fixed-final gate checkpoint lifecycle and full/NoBoundary development records."""
import os
from pathlib import Path
import time
import numpy as np
import torch
import d23_engine as e


def train(pair,gate,cache,ids,augmentation,out,signature,core,io,guard,resume=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);ck=out/'last_train_state.pth'
    optimizer=torch.optim.AdamW(gate.parameters(),lr=3e-4,weight_decay=.01)
    start=0
    if resume:
        state=torch.load(ck,map_location='cpu',weights_only=False)
        if state['signature']!=signature:raise RuntimeError('resume signature mismatch')
        gate.load_state_dict(state['model'],strict=True);optimizer.load_state_dict(state['optimizer']);start=state['global_step']
    elif ck.exists():raise RuntimeError('existing training requires explicit resume')
    if (out/'training_complete.json').exists():
        result=io.read(out/'training_complete.json')
        if not resume or result['signature']!=signature or result['checkpoint_sha256']!=io.sha(ck) or start!=4000:
            raise RuntimeError('completed training binding mismatch')
        return result
    began=time.monotonic()
    for step in range(start+1,4001):
        factor=.1+.9*step/100 if step<=100 else (4000-step)/3900
        for group in optimizer.param_groups:group['lr']=3e-4*factor
        logical=e.logical_batch(cache,ids,step-1,augmentation)
        value,counts=e.fit_update(pair,gate,optimizer,logical,core.loss_sums,combine=core.combine_loss_sums)
        guard()
        if step==1 or step%100==0 or step==4000:
            print('D23_GATE_TRAIN',gate.arm,step,value,flush=True)
            # Atomic overwrite only this run's resumable checkpoint, never expert files.
            temp=ck.with_suffix('.tmp');torch.save(dict(model=gate.state_dict(),optimizer=optimizer.state_dict(),
              global_step=step,signature=signature),temp);os.replace(temp,ck)
    state=torch.load(ck,map_location='cpu',weights_only=False)
    clone=core.DenseBenefitGate(gate.arm).to(next(gate.parameters()).device);clone.load_state_dict(state['model'],strict=True)
    if any(not torch.equal(a,b) for a,b in zip(gate.state_dict().values(),clone.state_dict().values())):
        raise RuntimeError('final gate state reload mismatch')
    result=dict(global_step=4000,checkpoint_sha256=io.sha(ck),signature=signature,
                checkpoint_selection='fixed_final_step_protocol_exception',train_ids=ids,seconds=time.monotonic()-began,
                test6_loaded=False,development_labels_loaded=False)
    io.write(out/'training_complete.json',result)
    return result


def pool(rows):
    cm=sum((np.asarray(r['cm'],np.int64) for r in rows),np.zeros((6,6),np.int64))
    tp=np.diag(cm);support=cm.sum(1);fp=cm.sum(0)-tp;fn=support-tp;union=tp+fp+fn
    iou=np.divide(tp,union,out=np.full(6,np.nan),where=union>0)
    def average(x):return float(np.nanmean(x)) if np.isfinite(x).any() else None
    return dict(cm=cm.tolist(),support=support.tolist(),TP=tp.tolist(),FP=fp.tolist(),FN=fn.tolist(),
                mIoU_fg5=average(iou[:5]),mIoU_6=average(iou),
                **{region:{k:sum(r[region][k] for r in rows) for k in ('valid','harm','rescue')} for region in ('all','available','missing')},
                by_class={str(c):{k:sum(r['by_class'][str(c)][k] for r in rows) for k in ('valid','harm','rescue')} for c in range(6)})


def evaluate(pair,gates,loader,ids,out,signature,core,io,guard):
    if list(ids)!=['3_11','5_10']:raise RuntimeError('only fixed Potsdam Val2 development permitted')
    out=Path(out);out.mkdir(parents=True,exist_ok=True);results={}
    for tile in ids:
        item=loader(tile,need_nb=True)
        op=torch.from_numpy(np.ascontiguousarray(item['optical'].transpose(2,0,1)))[None]
        ds=torch.from_numpy(np.ascontiguousarray(item['dsm']))[None]
        for condition in e.CONDITIONS:
            seed=e.key(42,'potsdam',tile,condition) if condition=='aux_noise_std020' else 42+sum(map(ord,tile))
            treated,aux,mask=e.treatment(op,ds,condition,seed,numpy_noise=condition=='aux_noise_std020')
            models={name:None for name in e.FIXED};models.update(gates)
            distributions={}
            score=e.infer(pair,models,np.ascontiguousarray(treated[0].permute(1,2,0).numpy()),aux[0].numpy(),mask[0].numpy(),core.fixed_blend,guard=guard,diagnostics=distributions)
            ref=score['R0'].argmax(0).astype(np.uint8);available=mask[0].numpy()
            rows={}
            for name,z in score.items():
                path=out/condition/name/(tile+'.npy');path.parent.mkdir(parents=True,exist_ok=True)
                if path.exists():raise RuntimeError('refuse existing evaluation prediction')
                pred=z.argmax(0).astype(np.uint8);np.save(path,pred)
                rows[name]=dict(signature=signature,tile=tile,condition=condition,prediction_sha256=io.sha(path),
                  scopes={scope:e.count_result(item[scope+'_gt'],pred,ref,available) for scope in ('full','noboundary')},
                  missing_logits_equal=np.array_equal(z[:,~available],score['R0'][:,~available]),gate_distribution=distributions.get(name))
                io.write(path.with_suffix('.json'),rows[name])
            results.setdefault(condition,{})[tile]=rows
            if condition.startswith('aux_') and rows['R0']['prediction_sha256']!=results['clean'][tile]['R0']['prediction_sha256']:
                raise RuntimeError('optical-only full-image auxiliary invariance failed')
            del score,treated,aux,mask;guard();print('D23_DEVELOPMENT_EVAL',tile,condition,flush=True)
    pooled={condition:{name:{scope:pool([rows[tile][name]['scopes'][scope] for tile in ids])
              for scope in ('full','noboundary')} for name in next(iter(rows.values()))} for condition,rows in results.items()}
    result=dict(signature=signature,tiles=results,pooled=pooled,test6_loaded=False,
                independent_final_loaded=False,primary_scope='noboundary',primary_metric='mIoU_fg5')
    io.write(out/'summary.json',result)
    return result
