"""One bound checkpoint, 34 Val2 tile evaluations; no training/test access."""
import argparse,os,sys
from pathlib import Path
os.environ.setdefault('XFORMERS_DISABLED','1')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from d27_common import read,write,sha,now,within
from d27_data import Loader
from run_rebuild_v1_d27 import load_anchors
from model.rebuild_v1_d26 import build_experts,D26Segmenter
from model.rebuild_v1_d27 import D27Segmenter
from d27_evaluation import infer,FixedPair,counts,metric,joint_counts,encode_joint,joint_report,save_prediction
from d28_pressure import masks,apply,cases,regions

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--directory',type=Path,required=True);p.add_argument('--model',required=True);p.add_argument('--gpu',type=int,choices=(0,1),required=True);a=p.parse_args()
    root=a.root.resolve();base=within(a.directory,root/'records');plan=read(base/'plan.json');binding=read(base/'checkpoint_binding.json');row=binding['models'][a.model]
    if os.environ.get('CUDA_VISIBLE_DEVICES')!=str(a.gpu):raise RuntimeError('GPU binding differs')
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False
    torch.backends.cuda.matmul.allow_tf32=True;torch.backends.cudnn.allow_tf32=True
    if torch.__version__!='2.2.2+cu121':raise RuntimeError('use frozen d18_dino environment')
    source=read(base/'code_manifest.json')
    for name,digest in source['files'].items():
        if sha(base/'code'/name)!=digest:raise RuntimeError('source snapshot changed')
    parent=Path(plan['predecessor_directory']);runtime=read(parent/'plan.json')
    for config,key in (('potsdam_split_seed20260915.json','split_sha256'),('r05_quality_plus_dropout_16k.json','base_config_sha256'),('d18_d19_night_20260927.json','dino_config_sha256')):
        if sha(root/'configs/rebuild_v1'/config)!=runtime['expected_configs'][key]:raise RuntimeError('frozen configuration changed '+config)
    import subprocess
    dino=read(root/'configs/rebuild_v1/d18_d19_night_20260927.json')['dino'];repo=within(root/dino['repository_dir'],'/home/jovyan/zzx')
    if subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()!=dino['repository_commit']:raise RuntimeError('DINO revision changed')
    subprocess.run(['git','-C',str(repo),'diff','--exit-code','HEAD','--','dinov2','hubconf.py'],check=True,stdout=subprocess.DEVNULL)
    if sha(root/'records/rebuild_v1_d21_queue_20260928/input_manifest.json')!=runtime['input_manifest_sha256']:raise RuntimeError('inputs changed')
    if sha(within(row['path'],root))!=row['sha256']:raise RuntimeError('checkpoint changed '+a.model)
    anchors,_=load_anchors(root,runtime);r,d=build_experts(root,anchors);del anchors
    r.configure(False);d.configure(False)
    if a.model.endswith('_anchor'):model=FixedPair(r,d)
    elif a.model=='D26_B0':model=D26Segmenter(r,d,'B0')
    else:model=D27Segmenter(r,d,a.model.split('_',1)[1])
    if not a.model.endswith('_anchor'):
        checkpoint=torch.load(row['path'],map_location='cpu',weights_only=False)
        if checkpoint['global_step']!=row['step']:raise RuntimeError('checkpoint age differs')
        model.load_state_dict(checkpoint['model'],strict=True);del checkpoint
    model=model.cuda().eval();loader=Loader(root,runtime);out=base/'jobs'/a.model;out.mkdir(parents=True,exist_ok=True)
    signature=dict(model=a.model,checkpoint=row,binding_sha256=sha(base/'checkpoint_binding.json'),plan_sha256=sha(base/'plan.json'),source_sha256=sha(base/'code_manifest.json'),precision='FP32_TF32',batch=8,window=512,stride=256,test6_loaded=False)
    def validate_clean(record,tile):
        d26=Path(runtime['predecessor_directory'])
        folder=(d26/'jobs/B0' if a.model in ('RGB_anchor','DSM_anchor','D26_B0') else parent/'jobs'/a.model.split('_',1)[1])
        old=read(folder/'evaluation/clean'/(tile+'.json'));reference='fixed_rgb' if a.model=='RGB_anchor' else 'fixed_dsm' if a.model=='DSM_anchor' else 'candidate'
        for scope in ('full','noboundary'):
            if old['scopes'][scope]['metrics'][reference]['valid']['cm']!=record['scopes'][scope]['valid']['metric']['cm']:raise RuntimeError('clean reproduction failed before pressure evaluation '+a.model)
        if old['predictions'][reference]!=record['predictions']['candidate']:raise RuntimeError('clean prediction SHA differs before pressure evaluation')
    import fcntl
    lock=(out/'worker.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    done=0
    def progress(**kw):write(out/'progress.json',dict(model=a.model,done=done,total=34,observed_at=now(),**kw))
    for tile in ('3_11','5_10'):
        progress(phase='loading_tile',tile=tile);item=loader(tile,True);pool,meta=masks(item['dsm'].shape,tile)
        maskfile=out/('mask_'+tile+'.json')
        if maskfile.exists() and read(maskfile)!=meta:raise RuntimeError('mask binding changed')
        write(maskfile,meta)
        variants={}
        for cid,recipe,level,pair in cases():
            folder=out/'evaluation'/cid;folder.mkdir(parents=True,exist_ok=True);record=folder/(tile+'.json')
            casebinding=dict(signature=signature,case=cid,tile=tile,mask=meta['sha256'],bias_sign=meta['bias_sign'])
            if record.exists():
                existing=read(record)
                if existing['binding']!=casebinding:raise RuntimeError('existing result binding differs')
                for name,digest in existing['predictions'].items():
                    if sha(folder/name/(tile+'.npy'))!=digest:raise RuntimeError('prediction changed')
                if cid=='clean':validate_clean(existing,tile)
                done+=1;continue
            stress=item if pair is None else apply(item,pool,recipe,level,pair,tile,variants)
            valid=np.ones_like(item['dsm'],bool);progress(phase='inference',case=cid,tile=tile)
            if hasattr(model,'reset_route_stats'):model.reset_route_stats()
            predictions,identity=infer(model,stress,valid,valid,lambda **kw:progress(case=cid,tile=tile,**kw),batch=8,fixed_only=a.model.endswith('_anchor'))
            pred=predictions['rgb' if a.model=='RGB_anchor' else 'dsm' if a.model=='DSM_anchor' else 'candidate']
            rr,dd=predictions['rgb'],predictions['dsm'];scopes={}
            for scope,gt in (('full',item['full_gt']),('noboundary',item['noboundary_gt'])):
                scopes[scope]={}
                for region,mask in regions(pool,pair).items():
                    result=counts(gt,pred,mask);joint=joint_counts(gt,rr,dd,pred,mask)
                    scopes[scope][region]=dict(metric=result,joint=encode_joint(joint),joint_report=joint_report(joint))
            digests={}
            for name,value in dict(candidate=pred,rgb=rr,dsm=dd).items():
                path=folder/name/(tile+'.npy');path.parent.mkdir(parents=True,exist_ok=True);digests[name]=save_prediction(path,value)
            routes=model.route_stats() if hasattr(model,'route_stats') else None
            result=dict(binding=casebinding,availability='both_present',stress_masks_model_input=False,scopes=scopes,predictions=digests,route_diagnostics=routes,fallback=identity,test6_loaded=False)
            if cid=='clean':validate_clean(result,tile)
            write(record,result)
            done+=1;print('D28_TILE_COMPLETE',a.model,cid,tile,done,'/34',flush=True)
            del predictions,stress
        del variants,item,pool
    write(out/'input_binding.json',loader.verified)
    write(out/'complete.json',dict(signature=signature,tile_evaluations=done,observed_at=now(),test6_loaded=False));progress(phase='complete')
if __name__=='__main__':main()
