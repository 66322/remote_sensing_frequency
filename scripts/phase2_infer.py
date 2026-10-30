"""Native sliding FP32 stitching, deduplicated frozen logits, streamed CPU counts."""
import argparse
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from torch.nn import functional as F
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
from phase2_common import *
from phase2_data import Tiles,panel,case_id,legacy_mask,down4
from model.phase2_matched import observables

def coords(shape):
    from d23_engine import positions
    return [(y,x) for y in positions(shape[0],512,256) for x in positions(shape[1],512,256)]

VERIFIED_CACHE=set()

def single(model,image,base,cache_key,progress=None):
    import fcntl
    folder=Path(base)/'val_cache';folder.mkdir(exist_ok=True)
    with (folder/(cache_key+'.lock')).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return single_locked(model,image,base,cache_key,progress)

def single_locked(model,image,base,cache_key,progress=None):
    """Store native window logits at 128, retaining all overlapping window contexts."""
    folder=Path(base)/'val_cache';folder.mkdir(exist_ok=True)
    path=folder/(cache_key+'.npy');receipt=path.with_suffix('.json')
    if receipt.exists():
        r=read(receipt)
        if r['binding']!=binding(base):raise RuntimeError('validation cache binding changed')
        if str(path) not in VERIFIED_CACHE:
            if sha(path)!=r['sha256']:raise RuntimeError('validation cache changed')
            VERIFIED_CACHE.add(str(path))
        return np.load(path,mmap_mode='r',allow_pickle=False)
    cs=coords(image.shape[:2]);tmp=path.with_name(path.name+'.tmp.'+str(os.getpid()))
    values=np.lib.format.open_memmap(tmp,mode='w+',dtype=np.float32,shape=(len(cs),6,128,128))
    with torch.inference_mode():
        for start in range(0,len(cs),8):
            use=cs[start:start+8];a=np.stack([image[y:y+512,x:x+512].transpose(2,0,1) for y,x in use])
            z=torch.from_numpy(a).cuda();n=len(use)
            if n<8:z=torch.cat((z,z[-1:].expand(8-n,-1,-1,-1)))
            low=model.low(z).float()
            if low.shape[-2:]!=(128,128):raise RuntimeError('compact grid changed')
            values[start:start+n]=low[:n].cpu().numpy()
            if progress:progress(windows_done=start+n,windows_total=len(cs))
    values.flush();del values;os.replace(tmp,path)
    write(receipt,dict(sha256=sha(path),binding=binding(base),cache_key=cache_key))
    VERIFIED_CACHE.add(str(path))
    return np.load(path,mmap_mode='r',allow_pickle=False)

def stitch_one(logits,shape):
    result=np.zeros((6,*shape),np.float32);coverage=np.zeros(shape,np.uint16)
    for z,(y,x) in zip(logits,coords(shape)):
        result[:,y:y+512,x:x+512]+=np.repeat(np.repeat(z,4,-2),4,-1)
        coverage[y:y+512,x:x+512]+=1
    if not coverage.all() or not np.isfinite(result).all():raise RuntimeError('bad stitch coverage/logits')
    return result,coverage

def clean_validation(base,model,job,out):
    from structured_v0_metrics import cm,metric
    out=Path(out);out.mkdir(parents=True,exist_ok=False);tiles=Tiles(base,VAL);model.eval()
    total={n:np.zeros((6,6),np.int64) for n in ('full','noboundary')}
    for tile in VAL:
        item=tiles[tile];image=item['optical'] if job=='A_RGB' else np.repeat(item['dsm'][...,None],3,-1)
        cs=coords(item['dsm'].shape);score=np.zeros((6,*item['dsm'].shape),np.float32)
        with torch.inference_mode():
            for start in range(0,len(cs),8):
                use=cs[start:start+8];a=np.stack([image[y:y+512,x:x+512].transpose(2,0,1) for y,x in use]);n=len(use)
                x=torch.from_numpy(a).cuda()
                if n<8:x=torch.cat((x,x[-1:].expand(8-n,-1,-1,-1)))
                logits=model(x).float()[:n].cpu().numpy()
                for z,(y,col) in zip(logits,use):score[:,y:y+512,col:col+512]+=z
        pred=score.argmax(0).astype(np.uint8);del score
        matrices={s:cm(item[s+'_gt'],pred,np.ones(pred.shape,bool)) for s in total}
        for s in total:total[s]+=matrices[s]
        write(out/(tile+'.json'),dict(cm={s:m.tolist() for s,m in matrices.items()},fg5={s:100*metric(m) for s,m in matrices.items()}))
    scores={s+'_fg5':100*metric(m) for s,m in total.items()}
    write(out/'pooled.json',dict(cm={s:m.tolist() for s,m in total.items()},**scores));return scores

def view(base,item,c):
    shape=item['dsm'].shape;rgb=np.array(item['optical']);ds=np.array(item['dsm']);rm=np.ones(shape,bool);dm=rm.copy();mask=np.zeros(shape,bool)
    if c['panel']=='clean':return rgb,ds,rm,dm,mask
    if c['panel']=='ordinary':
        from post_d30_data import treatment
        a,b,r,d=treatment(torch.from_numpy(rgb.transpose(2,0,1)[None]),torch.from_numpy(ds[None]),c['damage'],key(42,'ordinary',c['tile'],c['damage']))
        return a[0].numpy().transpose(1,2,0),b[0].numpy(),r[0].numpy(),d[0].numpy(),~(r[0].numpy()&d[0].numpy())
    mask=legacy_mask(base,c)
    if c['direction']=='rgb':
        if c['damage']=='zero':rgb[mask]=0
        else:
            bad=np.load(Path(base)/'inputs'/c['tile']/'rgb_down4.npy',mmap_mode='r');rgb[mask]=bad[mask]
        if c['panel']!='P-U':rm[mask]=False
    else:
        if c['damage']=='zero':ds[mask]=0
        else:
            bad=np.load(Path(base)/'inputs'/c['tile']/'dsm_down4.npy',mmap_mode='r');ds[mask]=bad[mask]
        if c['panel']!='P-U':dm[mask]=False
    return rgb,ds,rm,dm,mask

def evaluate_case(base,rmodel,dmodel,head,item,c,age,system,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);shape=item['dsm'].shape;rgb,ds,rm,dm,mask=view(base,item,c)
    def progress(**kw):write(out/'progress.json',dict(case=c,system=system,age=age,phase='frozen_forward',observed_at=now(),**kw))
    # Cache key is the physical single-modal input, not the availability/report metadata.
    token=lambda name:('%s_%d_%s_'%(c['tile'],age,name))+('clean' if c['panel']=='clean' or (c['panel']!='ordinary' and c['direction']!=name) else
        (c['damage']+'_'+c['family']+'_'+str(c['realization'])+'_'+str(c['ratio'])))
    a=single(rmodel,rgb,base,token('rgb'),progress);b=single(dmodel,np.repeat(ds[...,None],3,-1),base,token('dsm'),progress)
    sr,cov=stitch_one(a,shape);sd,_=stitch_one(b,shape);pr=sr.argmax(0).astype(np.uint8);pd=sd.argmax(0).astype(np.uint8);del sr,sd
    score=np.zeros((6,*shape),np.float32);entropy_delta=np.zeros(shape,np.float32);identity=True
    with torch.inference_mode():
        cs=coords(shape)
        for start in range(0,len(cs),8):
            use=cs[start:start+8]
            ra=torch.from_numpy(np.array(a[start:start+len(use)])).cuda();da=torch.from_numpy(np.array(b[start:start+len(use)])).cuda()
            ro=torch.from_numpy(np.stack([rgb[y:y+512,x:x+512].transpose(2,0,1) for y,x in use])).cuda()
            de=torch.from_numpy(np.stack([ds[y:y+512,x:x+512] for y,x in use])).cuda()
            mr=torch.from_numpy(np.stack([rm[y:y+512,x:x+512] for y,x in use])).cuda();md=torch.from_numpy(np.stack([dm[y:y+512,x:x+512] for y,x in use])).cuda()
            obs=observables(ra,da,ro,de,mr,md)
            ar=F.interpolate(ra,size=(512,512),mode='nearest');ad=F.interpolate(da,size=(512,512),mode='nearest')
            if head is None:
                z=torch.where((mr&md)[:,None],(ar+ad)/2,torch.where(mr[:,None],ar,ad))
            else:z=head(ra,da,obs,mr,md)
            identity &= bool(torch.equal(z.masked_select((~mr&md)[:,None]),ad.masked_select((~mr&md)[:,None])))
            identity &= bool(torch.equal(z.masked_select((mr&~md)[:,None]),ar.masked_select((mr&~md)[:,None])))
            ent=F.interpolate(obs[:,:1]-obs[:,1:2],size=(512,512),mode='nearest')[:,0]
            for zz,ee,(y,x) in zip(z.cpu().numpy(),ent.cpu().numpy(),use):
                score[:,y:y+512,x:x+512]+=zz;entropy_delta[y:y+512,x:x+512]+=ee
            progress(windows_done=start+len(use),windows_total=len(cs))
    if not identity:raise RuntimeError('exact single-available fallback failed')
    pred=score.argmax(0).astype(np.uint8);pred[~(rm|dm)]=255;del score
    entropy_delta/=cov
    bins=np.where(entropy_delta<=-.25,0,np.where(entropy_delta>=.25,2,1)).astype(np.uint8)
    rows={n:compact_save(out/(n+'.npy'),v,'labels3') for n,v in dict(pred=pred,rgb=pr,dsm=pd,entropy_bin=bins).items()}
    rows.update({n:compact_save(out/(n+'.npy'),v,'bool') for n,v in dict(mask=mask,rm=rm,dm=dm).items()})
    write(out/'arrays.json',dict(case=c,system=system,age=age,arrays=rows,fallback_exact=identity,binding=binding(base)))
    return out

def run(base,gpu,system,age):
    from phase2_train import trained,load_head
    from phase2_analysis import analyze_case
    p=verify(base);r=trained(base,'A_RGB',age);d=trained(base,'A_DSM',age);head=load_head(base,system)
    tiles=Tiles(base,VAL);cases=panel(age)
    if age==16000:
        conditions=read(Path(p['previous'])/'paired_plan.json')['fixed_conditions']
        for tile in VAL:
            for kind in conditions:
                if kind=='clean':continue
                cases.append(dict(tile=tile,panel='ordinary',direction='none',family=kind,realization=0,ratio=0,damage=kind))
    cases=cases[gpu::2];folder=Path(base)/'evaluation'/('%s_%d'%(system,age));folder.mkdir(parents=True,exist_ok=True)
    count=read(Path(base)/'resource_profile.json')['analysis_workers'];pending=[]
    with ProcessPoolExecutor(max_workers=max(1,count//2),mp_context=mp.get_context('spawn')) as cpu:
        for c in cases:
            out=evaluate_case(base,r,d,head,tiles[c['tile']],c,age,system,folder/case_id(c))
            pending.append(cpu.submit(analyze_case,str(base),str(out)))
            # Bounded disk-backed pipeline; futures return compact count receipts only.
            if len(pending)>=max(2,count):pending.pop(0).result()
        for f in pending:f.result()
    lane=Path(base)/('eval_'+system+'_'+str(age)+'_lane'+str(gpu));complete(base,lane,dict(cases=len(cases),system=system,age=age))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--gpu',type=int,required=True);parser.add_argument('--system',default='average');parser.add_argument('--age',type=int,default=16000)
    args=parser.parse_args();runtime(args.directory,args.gpu);run(args.directory,args.gpu,args.system,args.age)
