"""Exact integer histogram acceleration; estimands and oracle construction unchanged."""
import numpy as np
import phase15_numeric as original


def one(table):
    n=correct=wrong=harm=rescue=flips=0
    for g in range(6):
        for r in range(6):
            for c in range(6):
                v=int(table[g,r,c]);n+=v
                correct+=v*(r==g);wrong+=v*(r!=g)
                harm+=v*(r==g and c!=g);rescue+=v*(r!=g and c==g)
                flips+=v*(r!=c)
    return dict(valid=n,reference_correct=correct,reference_wrong=wrong,harmed=harm,rescued=rescue,
        flips=flips,flip_rate=flips/n if n else None,harm_rate=harm/correct if correct else None,
        rescue_rate=rescue/wrong if wrong else None)


def fast_evidence(gt,clean,pred,regions):
    result={}
    for name,support in regions.items():
        table=np.zeros(216,np.int64)
        # Bound indexing scratch; a joint histogram replaces repeated class/transition scans.
        for y in range(0,gt.shape[0],128):
            g=gt[y:y+128];r=clean[y:y+128];c=pred[y:y+128]
            use=support[y:y+128] & (g<6)
            gg,rr,cc=g[use],r[use],c[use]
            if (rr>=6).any() or (cc>=6).any():raise ValueError('invalid prediction on valid labels')
            keys=36*gg.astype(np.int16)+6*rr.astype(np.int16)+cc
            table+=np.bincount(keys,minlength=216)
        table=table.reshape(6,6,6)
        by_class={}
        for g in range(6):
            part=np.zeros_like(table);part[g]=table[g];by_class[str(g)]=one(part)
        result[name]=dict(clean_cm=table.sum(2).tolist(),missing_cm=table.sum(1).tolist(),
            transitions=dict(**one(table),by_class=by_class),confusion_matrix_dtype='int64')
    return result


def fast_oracle_evidence(gt,clean,predictions,mask,entropy,deployment_bins):
    disagreement=np.zeros(gt.shape,bool);codes=np.zeros(gt.shape,np.uint8)
    for i,p in enumerate(predictions):
        disagreement |= p!=predictions[0]
        codes |= (p==gt).astype(np.uint8)<<i
    common=(gt<6)&disagreement
    bits=np.arange(32,dtype=np.uint8)
    def condition_counts(_gt,_predictions,bins,keep):
        hist=np.zeros((256,32),np.int64)
        for y in range(0,gt.shape[0],128):
            use=common[y:y+128]&keep[y:y+128]
            keys=32*bins[y:y+128][use].astype(np.int16)+codes[y:y+128][use]
            hist+=np.bincount(keys,minlength=8192).reshape(256,32)
        return {str(v):dict(valid=int(row.sum()),correct=[int(row[(bits&(1<<i))!=0].sum())
            for i in range(5)]) for v,row in enumerate(hist) if row.sum()}
    old_evidence,old_counts=original.evidence,original.condition_counts
    try:
        original.evidence=fast_evidence;original.condition_counts=condition_counts
        return original.oracle_evidence(gt,clean,predictions,mask,entropy,deployment_bins)
    finally:original.evidence,original.condition_counts=old_evidence,old_counts
