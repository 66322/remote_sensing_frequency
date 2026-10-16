"""D0, fixed U and prospectively frozen stress masks. CPU, no updates."""
import argparse
from pathlib import Path
import numpy as np
from scipy.ndimage import maximum_filter,minimum_filter
from post_s1_support_common import *
from post_s1_support_evaluation import *
from post_n2_diag_runtime import input_contract
from post_n2_masks import boundary_band
from d24_data import Loader
def stress_masks(shape):
    h,w=shape;yy,xx=np.indices(shape)
    return dict(lines64w8=xx%64<8,blocks64q25=(yy%64>=16)&(yy%64<48)&(xx%64>=16)&(xx%64<48))
def prepare(root,base):
    p=validate(read(base/'plan.json'));verify_snapshot(base);input_contract(root,p)
    acceptance=released(root);write(base/'source_acceptance.json',acceptance)
    source=root/'records'/SOURCE_NAME;old=read(source/'mask_manifest.json');loader=Loader(root,p);tiles={}
    route_rows={};route_ordinary={};indices={}
    for tile in p['data']['validation']:
        item=loader(tile,True);tiles[tile]={};row=old['tiles'][tile]['U'];path=within(row['path'],source)
        if sha(path)!=row['sha256']:raise RuntimeError('original U changed')
        target=base/'masks'/tile/'U.npz';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(path.read_bytes())
        tiles[tile]['U']=dict(row,path=str(target),source_path=str(path))
        with np.load(path,allow_pickle=False) as z:m=np.unpackbits(z['bits'],bitorder='little',count=item['dsm'].size).reshape(item['dsm'].shape).astype(bool)
        if int(m.sum())*4!=m.size or list(m.shape)!=row['shape']:raise RuntimeError('U decode mismatch')
        for rule,mask in stress_masks(m.shape).items():
            target=base/'masks'/tile/(rule+'.npz')
            np.savez_compressed(target,bits=np.packbits(mask.ravel(),bitorder='little'),shape=np.array(mask.shape,np.int64))
            tiles[tile][rule]=dict(path=str(target),sha256=sha(target),shape=list(mask.shape),missing_pixels=int(mask.sum()),
                rule=rule,geometry=p['design']['E_masks'],labels_used=False)
        band=boundary_band(item['full_gt'],4);edge=maximum_filter(m,size=33,mode='constant',cval=0)!=minimum_filter(m,size=33,mode='constant',cval=0)
        overlap=dict(all=np.ones_like(m),missing_inside=m,missing_outside=~m,missing_edge16=edge,label_boundary4=band,label_interior=~band)
        # Explicit nonoverlapping priority: label edge -> missing edge -> inside -> outside.
        partitions=dict(label_edge=band,missing_edge=edge&~band,missing_inside=m&~edge&~band,other=~m&~edge&~band)
        for key in ['rgb_U','dsm_U','clean','aux_shift8','rgb_blur5+aux_shift8','aux_down4','rgb_contrast060']:
            tag='support_evaluation' if key.endswith('_U') else 'evaluation'
            controls,control_row,cb=source_case(root,'S1-0',tag,key,tile)
            if key=='rgb_U':rm,dm=~m,np.ones_like(m)
            elif key=='dsm_U':rm,dm=np.ones_like(m),~m
            else:rm=dm=np.ones_like(m)
            for name in ('S1-1','S1-2','S1-3'):
                preds,source_row,sb=source_case(root,name,tag,key,tile)
                diagnostic={scope:{n:transition(item[scope+'_gt'],controls['candidate'],preds['candidate'],region) for n,region in {**overlap,**{'exclusive_'+n:r for n,r in partitions.items()}}.items()} for scope in ('full','noboundary')}
                target=base/'D0'/name/key/(tile+'.json')
                write(target,dict(tile=tile,condition=key,control=cb,candidate=sb,regions=diagnostic,
                    overlapping_regions=list(overlap),exclusive_priority=list(partitions),test6_loaded=False))
                indices[name+'/'+key+'/'+tile]=dict(path=str(target),sha256=sha(target))
                if name=='S1-3' and key.endswith('_U'):
                    route,use=simple_route(controls['candidate'],preds['candidate'],rm,dm)
                    vals=dict(controls,candidate=route);binding=dict(control=cb,context=sb,routing='known RGB partial missing + observed DSM, no GT',new_optimizer_updates=0)
                    route_rows.setdefault(key,{})[tile]=write_case(base/'R0_U',key,tile,item,rm,dm,vals,binding)
            write(base/'preparation_progress.json',dict(phase='D0',tile=tile,condition=key,observed_at=now()))
        # Full ordinary evaluation of R0 is cheap prediction reuse and preserves denominators.
        op=torch.from_numpy(item['optical'].transpose(2,0,1).copy())[None];ds=torch.from_numpy(item['dsm'])[None]
        conditions=p['evaluation']['primary']+p['evaluation']['missing']+sum(p['evaluation']['local'].values(),[])+p['evaluation']['diagnostic']
        for key in conditions:
            a,_,ab=source_case(root,'S1-0','evaluation',key,tile);b,_,bb=source_case(root,'S1-3','evaluation',key,tile)
            _,_,rm,dm=treatment(op,ds,key,e.key(42,'D26_eval',tile));rm,dm=rm[0].numpy(),dm[0].numpy()
            routed,_=simple_route(a['candidate'],b['candidate'],rm,dm)
            vals=dict(a,candidate=routed)
            route_ordinary.setdefault(key,{})[tile]=write_case(base/'R0_ordinary',key,tile,item,rm,dm,vals,dict(control=ab,context=bb,new_optimizer_updates=0))
        del item
    write(base/'mask_manifest.json',dict(plan_sha256=sha(base/'plan.json'),tiles=tiles,source_manifest_sha256=sha(source/'mask_manifest.json'),T_read=False,E_frozen_before_new_inference=True))
    finish_summary(base/'R0_U',route_rows,dict(plan_sha256=sha(base/'plan.json'),new_optimizer_updates=0))
    finish_summary(base/'R0_ordinary',route_ordinary,dict(plan_sha256=sha(base/'plan.json'),new_optimizer_updates=0))
    write(base/'d0_index.json',dict(records=indices,region_radius=dict(missing=16,label=4),new_optimizer_updates=0,oracle_used_for_forward=False))
    write(base/'preparation_complete.json',dict(plan_sha256=sha(base/'plan.json'),mask_manifest_sha256=sha(base/'mask_manifest.json'),
        d0_sha256=sha(base/'d0_index.json'),route_U_sha256=sha(base/'R0_U/summary.json'),route_ordinary_sha256=sha(base/'R0_ordinary/summary.json'),
        source_acceptance_sha256=sha(base/'source_acceptance.json'),inputs=loader.verified,optimizer_updates=0,observed_at=now()))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);a=ap.parse_args()
    prepare(*dirs(a.root,a.directory))
if __name__=='__main__':main()

