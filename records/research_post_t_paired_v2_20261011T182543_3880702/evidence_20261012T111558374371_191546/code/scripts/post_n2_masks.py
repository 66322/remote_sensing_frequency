"""Content masks: exact quarter area, paired shapes, separated blocks, no labels."""
import hashlib
import numpy as np
from scipy.ndimage import uniform_filter,maximum_filter,minimum_filter,label

def scores(optical,dsm,window=5):
    if optical.shape!=dsm.shape+(3,) or not np.isfinite(optical).all() or not np.isfinite(dsm).all():raise ValueError('invalid paired inputs')
    lum=np.asarray(optical,np.float32)@np.array([.299,.587,.114],np.float32)
    contrast=np.sqrt(np.maximum(uniform_filter(lum*lum,size=window,mode='reflect')-uniform_filter(lum,size=window,mode='reflect')**2,0))
    variation=maximum_filter(dsm,size=window,mode='reflect')-minimum_filter(dsm,size=window,mode='reflect')
    return dict(H=variation.astype(np.float32),L=contrast.astype(np.float32))
def quarter_mask(shape,rule,score=None,tile='',cell=128):
    h,w=shape
    if h<cell or w<cell or h%2 or w%2:raise ValueError('even whole-tile dimensions >=128 required for exact quarter masks')
    if rule not in ('U','H','L'):raise ValueError('reserved or unknown rule')
    if rule!='U' and (score is None or score.shape!=shape or not np.isfinite(score).all()):raise ValueError('content score missing')
    mask=np.zeros(shape,bool);boxes=[]
    for y in range(0,h,cell):
        ch=min(cell,h-y);bh=ch//2
        for x in range(0,w,cell):
            cw=min(cell,w-x);bw=cw//2
            # Fixed geometry: one half-height/half-width block per cell,
            # each with at least 1px margin; identical edge shapes in all rules.
            offsets=[(max(1,ch//8),max(1,cw//8)),(max(1,ch//8),max(1,3*cw//8)),(max(1,3*ch//8),max(1,cw//8)),(max(1,3*ch//8),max(1,3*cw//8))]
            if any(dy+bh>=ch or dx+bw>=cw for dy,dx in offsets):raise ValueError('edge cell too small for separated blocks')
            if rule=='U':k=int.from_bytes(hashlib.sha256(('42:postN2mask:'+tile+':'+str(y)+':'+str(x)).encode()).digest()[:4],'little')%4
            else:
                values=[float(score[y+dy:y+dy+bh,x+dx:x+dx+bw].mean()) for dy,dx in offsets]
                k=int(np.argmax(values) if rule=='H' else np.argmin(values))
            dy,dx=offsets[k];box=[y+dy,x+dx,bh,bw];boxes.append(box);mask[box[0]:box[0]+bh,box[1]:box[1]+bw]=True
    if int(mask.sum())*4!=h*w:raise RuntimeError('quarter area mismatch')
    return mask,boxes
def physical_view(item,missing,direction,case):
    if direction not in ('rgb','dsm') or case not in ('clean','false_positive','known_missing','false_negative'):raise ValueError('unlisted fault case')
    op=item['optical'].copy();ds=item['dsm'].copy();rm=np.ones(ds.shape,bool);dm=rm.copy()
    if case in ('known_missing','false_negative'):
        if direction=='rgb':op[missing]=0
        else:ds[missing]=0
    if case in ('known_missing','false_positive'):
        if direction=='rgb':rm[missing]=False
        else:dm[missing]=False
    return dict(optical=op,dsm=ds),rm,dm
def boundary_band(gt,radius=4):
    valid=gt<6;edge=np.zeros(gt.shape,bool)
    diff=(gt[1:]!=gt[:-1])&valid[1:]&valid[:-1];edge[1:]|=diff;edge[:-1]|=diff
    diff=(gt[:,1:]!=gt[:,:-1])&valid[:,1:]&valid[:,:-1];edge[:,1:]|=diff;edge[:,:-1]|=diff
    return maximum_filter(edge,size=2*radius+1,mode='constant')&valid
def object_areas(gt):
    out={};structure=np.array([[0,1,0],[1,1,1],[0,1,0]])
    for c in range(5):
        components,n=label(gt==c,structure=structure);areas=np.bincount(components.ravel())[1:];out[str(c)]=areas.tolist()
    return out
def small_objects(gt,cutoffs):
    out=np.zeros(gt.shape,bool);structure=np.array([[0,1,0],[1,1,1],[0,1,0]])
    for c in range(5):
        components,n=label(gt==c,structure=structure);sizes=np.bincount(components.ravel());keep=sizes<=cutoffs[str(c)];keep[0]=False;out|=keep[components]
    return out
def e1_gate(rows,pooled,gap=.5):
    checks={};deltas={}
    for direction in ('rgb','dsm'):
        for rule in ('H','L'):
            name=direction+'_'+rule;values={};ok=True
            for model in ('A0','B1'):
                key=lambda r:direction+'_'+r
                delta=100*(pooled[model][key('U')]-pooled[model][key(rule)])
                tiles={t:100*(rows[model][key('U')][t]-rows[model][key(rule)][t]) for t in ('3_11','5_10')}
                values[model]=dict(pooled_gap_pp=delta,tile_gaps_pp=tiles)
                ok&=delta>=gap-1e-9 and all(x>0 for x in tiles.values())
            checks[name]=bool(ok);deltas[name]=values
    return dict(N5_problem_trigger=any(checks.values()),checks=checks,deltas=deltas,automatic_training=False)
