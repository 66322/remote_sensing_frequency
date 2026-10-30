"""One raw-height read, shared fork-COW input and deterministic paired crops."""
import hashlib
import io
import random
from pathlib import Path
import numpy as np
from phase3_m1_common import *

def normalize(h,tile,representation,seed=None,counter=False):
    st=STATS[tile]
    if representation=='R0': return (h-np.float32(st['min']))/np.float32(st['max']-st['min'])
    scale=st['span'] if representation=='R1' else STATS['_S']
    gain=1.
    if counter:
        order=sorted(FIT,key=lambda t:key(seed,'amplitude_derangement',t))
        dst=order[(order.index(tile)+1)%len(order)]
        gain=STATS[dst]['span']/st['span']
    return np.float32(.5)+np.float32(gain)*(h-np.float32(st['median']))/np.float32(scale)

def prepare(base):
    from PIL import Image
    from prepare_phase24 import source_guard
    from phase24_common import profile, scoped as old_scoped
    base=Path(base); p=verify(base); old=Path(p['previous']); source_guard(old)
    m=read(old/'input_manifest.json'); audits={}; DATA.clear(); STATS.clear()
    if set(m['arrays'])!=set(FIT+VAL): raise RuntimeError('unexpected source tile')
    needed=sum(int(np.prod(row['shape']))*np.dtype(row['dtype']).itemsize
               for tile in FIT+VAL for name,row in m['arrays'][tile].items()
               if name in (('optical','dsm','full_gt','noboundary_gt','rgb_down4') if tile in VAL else ('dsm','full_gt')))
    pf=profile(); rough=needed+len(FIT+VAL)*6000*6000*4+36*1024**3
    if pf['available_bytes']<rough+8*1024**3: raise RuntimeError('insufficient safe RAM envelope for shared inputs and registered logits')
    for tile in FIT+VAL:
        fields={}
        for name in ('optical','dsm','full_gt','noboundary_gt','rgb_down4'):
            if tile in FIT and name not in ('dsm','full_gt'): continue  # DSM training has no RGB consumer.
            if name not in m['arrays'][tile]: continue
            row=m['arrays'][tile][name]; f=old_scoped(row['path'],old/'inputs'); before=identity(f)
            raw=f.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=row['sha256'] or identity(f)!=before: raise RuntimeError('input changed: '+str(f))
            a=np.load(io.BytesIO(raw),allow_pickle=False); a.flags.writeable=False; fields[name]=a
            audits[str(f)]=dict(sha256=row['sha256'],identity=before)
        rawpath=old_scoped(m['normalization'][tile]['source_path'],'/home/jovyan/zzx')
        expected=m['source_files'].get(str(rawpath))
        if not expected: raise RuntimeError('unbound raw height source')
        before=identity(rawpath); hsh=sha(rawpath)
        if hsh!=expected.get('current_sha256',expected.get('sha256')): raise RuntimeError('raw height SHA changed')
        with Image.open(rawpath) as im:
            if im.mode!='F': raise RuntimeError('expected float32 DSM TIFF; inspect units/type')
            height=np.array(im,dtype=np.float32)
        if identity(rawpath)!=before or not np.isfinite(height).all(): raise RuntimeError('invalid/raw height changed')
        qs=np.quantile(height,[.05,.5,.95],method='linear')
        st=dict(min=float(height.min()),max=float(height.max()),median=float(qs[1]),span=float(qs[2]-qs[0]),q05=float(qs[0]),q95=float(qs[2]))
        if st['span']<=0 or height.shape!=fields['dsm'].shape: raise RuntimeError('height shape/span invalid')
        STATS[tile]=st
        # Exact legacy min-max equivalence, not an approximate baseline relabel.
        if not np.array_equal(normalize(height,tile,'R0'),fields['dsm']): raise RuntimeError('raw-to-legacy normalization not exact')
        height.flags.writeable=False; fields['height']=height; DATA[tile]=fields
        if tile in VAL:
            import torch
            from torch.nn import functional as F
            with torch.inference_mode():
                low=F.interpolate(torch.from_numpy(height.copy())[None,None],size=(height.shape[0]//2,height.shape[1]//2),
                                  mode='bilinear',align_corners=False,antialias=True)[0,0].numpy()
            q=np.quantile(low,[.05,.5,.95],method='linear')
            STATS[tile]['gsd10']=dict(min=float(low.min()),max=float(low.max()),median=float(q[1]),span=float(q[2]-q[0]))
            low.flags.writeable=False; fields['height_gsd10']=low
        audits[str(rawpath)]=dict(sha256=hsh,identity=before,units='Potsdam source heights; no nDSM conversion')
        write(base/'preparation_progress.json',dict(tile=tile,done=len(DATA),total=14,observed_at=now()))
        print('M1_INPUT_VERIFIED',tile,len(DATA),'/14',flush=True)
    STATS['_S']=float(np.median([STATS[t]['span'] for t in FIT]))
    masks=read(old/'mask_manifest.json')
    for t in VAL:
        for i in range(1,21):
            for family in ('pixel','random','gradient','matched'):
                row=masks['tiles'][t][str(i)][family]['25']; f=old_scoped(row['path'],p['root'])
                if sha(f)!=row['sha256']: raise RuntimeError('fixed mask changed')
    weights={}
    for name in ('A_RGB','A_DSM'):
        f=old/'jobs'/name/'step_16000.pth'; h=sha(f); done=read(f.parent/'complete.json')
        if h!=read(f.with_suffix('.json'))['sha256'] or done['files'].get(f.name)!=h: raise RuntimeError('old endpoint changed')
        weights[name]=dict(path=str(f),sha256=h)
    source=read(old/'pretrained.json')
    if sha(source['path'])!=source['sha256']: raise RuntimeError('pretrained changed')
    write(base/'source_bindings.json',dict(inputs=audits,weights=weights,pretrained=source,old_binding=read(old/'registration.json').get('binding'),observed_at=now()))
    write(base/'height_statistics.json',dict(values=STATS,quantile_algorithm='numpy linear',clipping=False,
          relative_height_not_ndsm=True,units='raw Potsdam TIFF height unit; use native values',observed_at=now()))
    pf.update(estimated_peak_host_bytes=rough,crop_workers=min(8,max(1,pf['effective_cores']//8)),
              analysis_threads=min(16,max(2,pf['effective_cores']//4)),disk_array_cache=False)
    write(base/'resource_profile.json',pf)
    write(base/'prepared.json',dict(binding=binding(base),source_sha256=sha(base/'source_bindings.json'),stats_sha256=sha(base/'height_statistics.json'),observed_at=now()))
    return pf

class Crops:
    def __init__(self,arm,seed,start_step=0):
        if not 0<=start_step<16000: raise ValueError('invalid crop restart step')
        self.arm=arm; self.seed=seed; self.start_step=start_step
    def __len__(self): return (16000-self.start_step)*16
    def __getitem__(self,index):
        import torch
        from phase2_common import digest
        index+=self.start_step*16
        step=index//16+1; i=index%16; rng=random.Random(key(self.seed,'phase21',step,i))
        tile=FIT[rng.randrange(len(FIT))]; item=DATA[tile]; h,w=item['height'].shape
        y=rng.randrange(h-511); x=rng.randrange(w-511); fh,fv=rng.random()<.5,rng.random()<.5
        rep=ARMS[self.arm][0]
        ds=item['dsm'][y:y+512,x:x+512] if rep=='R0' else normalize(item['height'][y:y+512,x:x+512],tile,rep,self.seed,self.arm=='C21')
        gt=item['full_gt'][y:y+512,x:x+512]
        vals=[ds,gt]
        for j,v in enumerate(vals):
            if fh: v=np.flip(v,1)
            if fv: v=np.flip(v,0)
            vals[j]=np.ascontiguousarray(v)
        spec=dict(tile=tile,y=y,x=x,flip_h=fh,flip_v=fv)
        token=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()+digest(vals[1]).encode()).hexdigest()
        return dict(dsm=torch.from_numpy(vals[0].copy()),gt=torch.from_numpy(vals[1].astype(np.int64)),token=token)

