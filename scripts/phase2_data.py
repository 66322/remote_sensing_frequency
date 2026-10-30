"""Once-verified resident tiles, deterministic paired streams, legacy mask reuse."""
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import torch
from torch.nn import functional as F
from phase2_common import *

def prepare(base):
    p=verify(base,False);root=Path(p['root']);old=Path(p['previous'])
    if resources()['available_bytes']<32*1024**3:raise RuntimeError('at least 32 GiB available memory required before data preparation')
    import shutil
    if shutil.disk_usage(base).free<600*1024**3:raise RuntimeError('600 GiB disk reserve required before reading data')
    from d24_data import Loader
    source=read(old/'source_plan.json')
    from post_n2_diag_runtime import input_contract
    input_contract(root,source)
    if source['data']['fit12']!=FIT or source['data']['validation']!=VAL:raise RuntimeError('source split changed')
    loader=Loader(root,source);arrays={};source_files={};normalization={}
    for tile in FIT+VAL:
        item=loader(tile,tile in VAL)
        from PIL import Image
        a,b=map(int,tile.split('_'))
        raw_dsm=loader.data/'1_DSM/1_DSM'/('dsm_potsdam_%02d_%02d.tif'%(a,b))
        with Image.open(raw_dsm) as image:lo,hi=image.getextrema()
        normalization[tile]=dict(min=float(lo),max=float(hi),source_path=str(raw_dsm),
             before_damage=True,replicate_channels=3,mean=[.485,.456,.406],std=[.229,.224,.225])
        write(base/'preparation_progress.json',dict(tile=tile,phase='resident_tile',observed_at=now()))
        arrays[tile]={n:array_save(base/'inputs'/tile/(n+'.npy'),a) for n,a in item.items()}
        if tile in VAL:
            a=torch.from_numpy(item['optical'].transpose(2,0,1)[None]);b=torch.from_numpy(item['dsm'][None,None])
            arrays[tile]['rgb_down4']=array_save(base/'inputs'/tile/'rgb_down4.npy',down4(a)[0].numpy().transpose(1,2,0))
            arrays[tile]['dsm_down4']=array_save(base/'inputs'/tile/'dsm_down4.npy',down4(b)[0,0].numpy())
        del item
    # Full original input hashes once, outside all worker crop loops.
    paths=list(loader.verified)
    with ThreadPoolExecutor(max_workers=min(8,resources()['effective_cores'])) as pool:
        for path,h in zip(paths,pool.map(sha,paths)):
            if h!=loader.verified[path]['sha256']:raise RuntimeError('original input bytes changed: '+path)
            source_files[path]=dict(loader.verified[path],current_sha256=h)
    masks=read(old/'mask_manifest.json')
    for tile in VAL:
        for i in range(1,21):
            for family in FAMILIES:
                for ratio,row in masks['tiles'][tile][str(i)][family].items():
                    if sha(row['path'])!=row['sha256']:raise RuntimeError('legacy mask bytes changed')
    weights=root/'pretrained_external/dinov2_vits14_pretrain.pth'
    if not weights.is_file():raise RuntimeError('missing common pretrained DINO weight')
    input_bytes=sum(np.prod(v['shape'])*np.dtype(v['dtype']).itemsize for rows in arrays.values() for v in rows.values())
    profile=resources()
    import shutil
    disk=shutil.disk_usage(base)
    profile.update(disk_free_bytes=disk.free,required_disk_reserve_bytes=600*1024**3)
    if disk.free<600*1024**3:raise RuntimeError('Phase2 requires 600 GiB free disk reserve for immutable caches/evidence')
    if input_bytes>profile['hot_cache_bytes']//2:raise RuntimeError('resident input exceeds safe budget')
    write(base/'input_manifest.json',dict(arrays=arrays,source_files=source_files,normalization=normalization,total_array_bytes=int(input_bytes)))
    write(base/'mask_manifest.json',masks)
    write(base/'resource_profile.json',profile)
    write(base/'pretrained.json',dict(path=str(weights),sha256=sha(weights),repository=str(root/'external/dinov2_7764ea0'),
        repository_commit='7764ea0f912e53c92e82eb78a2a1631e92725fc8'))
    import subprocess
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.free','--format=csv,noheader,nounits'],text=True)
    write(base/'gpu_inventory.json',dict(output=gpu,observed_at=now()))
    for g in (0,1):
        row=next((r.split(',') for r in gpu.splitlines() if int(r.split(',')[0])==g),None)
        if row is None or float(row[-1])<16000:raise RuntimeError('GPU '+str(g)+' has insufficient currently free memory')
    names=['input_manifest.json','mask_manifest.json','resource_profile.json','pretrained.json','gpu_inventory.json']
    write(base/'prepared.json',dict(plan_sha256=sha(base/'plan.json'),receipts={n:sha(base/n) for n in names},prepared_at=now()))

class Tiles:
    def __init__(self,base,ids):
        manifest=read(Path(base)/'input_manifest.json')['arrays'];self.items={}
        for tile in ids:
            if tile not in FIT+VAL:raise ValueError('forbidden tile')
            self.items[tile]={}
            for n,row in manifest[tile].items():
                if sha(row['path'])!=row['sha256']:raise RuntimeError('resident array changed')
                arr=np.load(row['path'],mmap_mode='r',allow_pickle=False)
                self.items[tile][n]=arr
    def __getitem__(self,tile):return self.items[tile]

def sample(tiles,step,i,phase):
    rng=random.Random(key(42,phase,step,i));tile=FIT[rng.randrange(len(FIT))]
    x=tiles[tile];h,w=x['dsm'].shape;y=rng.randrange(h-511);col=rng.randrange(w-511)
    fh,fv=rng.random()<.5,rng.random()<.5
    values=[x['optical'][y:y+512,col:col+512],x['dsm'][y:y+512,col:col+512],x['full_gt'][y:y+512,col:col+512]]
    for j,a in enumerate(values):
        if fh:a=np.flip(a,1)
        if fv:a=np.flip(a,0)
        values[j]=np.ascontiguousarray(a)
    spec=dict(tile=tile,y=y,x=col,flip_h=fh,flip_v=fv)
    return values,spec

class Crops:
    def __init__(self,base,phase,start=0,stop=16000):
        self.tiles=Tiles(base,FIT);self.phase=phase;self.start=start;self.stop=stop
    def __len__(self):return (self.stop-self.start)*16
    def __getitem__(self,index):
        step=self.start+index//16+1;i=index%16;values,spec=sample(self.tiles,step,i,self.phase)
        rgb,ds,gt=values
        label_hash=digest(gt)
        batch_token=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()+label_hash.encode()).hexdigest()
        return dict(rgb=torch.from_numpy(rgb.transpose(2,0,1).copy()),dsm=torch.from_numpy(ds.copy()),
                    gt=torch.from_numpy(gt.astype(np.int64)),token=batch_token)

def batch_hash(tokens):return hashlib.sha256('|'.join(tokens).encode()).hexdigest()

def down4(x):
    from d23_engine import resize_restore
    return resize_restore(x,4)

def training_view(batch,step):
    rgb,ds=batch['rgb'].clone(),batch['dsm'].clone();rm=torch.ones_like(ds,dtype=torch.bool);dm=rm.clone()
    kinds=['clean']*2+['reported_rgb']*2+['reported_dsm']*2+['zero_rgb']*2+['zero_dsm']*2+['down_rgb']*2+['down_dsm']*2+['full_rgb','full_dsm']
    random.Random(key(42,'phase23_assignment',step)).shuffle(kinds)
    for i,kind in enumerate(kinds):
        if kind=='clean':continue
        if kind.startswith('full'):
            m=torch.ones_like(ds[i],dtype=torch.bool)
        else:
            rng=np.random.Generator(np.random.PCG64(key(42,'phase23_mask',step,i)))
            if step%2:
                a=np.zeros(512*512,bool);a[rng.permutation(a.size)[:a.size//4]]=True;m=torch.from_numpy(a.reshape(512,512)).to(ds.device)
            else:
                a=np.zeros(64,bool);a[rng.permutation(64)[:16]]=True
                m=torch.from_numpy(np.repeat(np.repeat(a.reshape(8,8),64,0),64,1)).to(ds.device)
        name=kind.split('_')[-1]
        if name=='rgb':
            if kind.startswith('down'):rgb[i,:,m]=down4(rgb[i:i+1])[0,:,m]
            else:rgb[i,:,m]=0
            if kind.startswith(('reported','full')):rm[i,m]=False
        else:
            if kind.startswith('down'):ds[i,m]=down4(ds[i:i+1,None])[0,0,m]
            else:ds[i,m]=0
            if kind.startswith(('reported','full')):dm[i,m]=False
    return rgb,ds,rm,dm,kinds

def legacy_mask(base,c):
    from phase15_numeric import decode_mask
    from structured_v0_masks import canonical
    row=read(Path(base)/'mask_manifest.json')['tiles'][c['tile']][str(c['realization'])][c['family']][str(c['ratio'])]
    mask=decode_mask(row['path'])
    if canonical(mask)!=row['canonical_sha256']:raise RuntimeError('mask identity changed')
    return mask

def panel(age):
    result=[]
    for tile in VAL:
        result.append(dict(tile=tile,panel='clean',direction='none',family='clean',realization=0,ratio=0,damage='clean'))
        for direction in ('rgb','dsm'):
            for family in FAMILIES:
                for i in range(1,21):
                    common=dict(tile=tile,direction=direction,family=family,realization=i,ratio=25)
                    result.append(dict(common,panel='P-M',damage='zero'))
                    if age==16000:
                        for damage in ('zero','down4'):result.append(dict(common,panel='P-U',damage=damage))
            if age==16000:
                for ratio in (5,10):
                    for i in range(1,21):result.append(dict(tile=tile,direction=direction,family='pixel',realization=i,ratio=ratio,panel='dose',damage='zero'))
    return result

def case_id(c):return '_'.join(str(c[n]) for n in ('tile','panel','direction','family','realization','ratio','damage'))
