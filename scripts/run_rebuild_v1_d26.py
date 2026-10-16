"""One fixed 8000-update D26 job. Original experts are read-only checkpoints."""
import argparse
from collections import Counter
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
os.environ.setdefault('XFORMERS_DISABLED','1')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from model.rebuild_v1_d26 import D26Segmenter,build_experts
from d26_common import read,write,sha,now,within,directories,validate_plan
from d26_data import Loader,Crops,PrefetchedBatches,objective
from d26_evaluation import References,FixedPair,selection,evaluate

def seed_all(seed=42):
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)

def load_anchors(root,plan):
    states={};provenance={}
    for name in ('rgb','dsm'):
        row=plan['experts'][name];path=within(root/row['path'],root)
        if sha(path)!=row['sha256']:raise RuntimeError('bound expert checkpoint changed: '+name)
        state=torch.load(path,map_location='cpu',weights_only=False)
        if state['global_step']!=row['step']:raise RuntimeError('expert selected step differs: '+name)
        states[name]=state['model'];provenance[name]=dict(path=str(path),sha256=row['sha256'],step=row['step'])
    return states,provenance

def optimizer_for(model,cfg):
    groups=[]
    def encoder(name):return name.startswith('rgb_expert.net.encoder.') or name.startswith('dsm_expert.net.transformer.encoder.layer.')
    for enc,lr in ((True,cfg['encoder_last4_lr']),(False,cfg['head_lr'])):
        params=[p for n,p in model.named_parameters() if p.requires_grad and encoder(n)==enc]
        if params:groups.append(dict(params=params,lr=lr,initial_lr=lr))
    return torch.optim.AdamW(groups,betas=tuple(cfg['betas']),weight_decay=cfg['weight_decay'])

def save(path,model,optimizer,step,signature,best,counts,gradient):
    tmp=path.with_suffix('.tmp')
    torch.save(dict(model=model.state_dict(),optimizer=optimizer.state_dict(),global_step=step,signature=signature,best=best,treatment_counts=dict(counts),gradient_check=gradient,random_state=random.getstate(),numpy_state=np.random.get_state(),torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all()),tmp)
    os.replace(tmp,path)

def copy(source,target):
    tmp=target.with_suffix('.tmp');shutil.copyfile(source,tmp);os.replace(tmp,target)

def verify_gradients(model):
    trainable={n:p for n,p in model.named_parameters() if p.requires_grad}
    frozen={n:p for n,p in model.named_parameters() if not p.requires_grad}
    if any(p.grad is not None for p in frozen.values()):raise RuntimeError('frozen expert received gradient')
    if any(p.grad is None or not torch.isfinite(p.grad).all() for p in trainable.values()):raise RuntimeError('missing or nonfinite trainable gradient')
    groups={prefix:any(p.grad is not None and bool(p.grad.abs().sum()>0) for n,p in trainable.items() if n.startswith(prefix)) for prefix in ('project_rgb.','project_dsm.','fusion.','interactions.','rgb_expert.','dsm_expert.')}
    required=['project_rgb.','project_dsm.','fusion.']+(['interactions.'] if model.interactions is not None else [])+(['rgb_expert.','dsm_expert.'] if model.arm=='J0' else [])
    if any(not groups[n] for n in required):raise RuntimeError('expected learned path has zero gradient')
    return dict(trainable_parameters=sum(p.numel() for p in trainable.values()),groups_nonzero=groups,frozen_gradients_absent=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--job',required=True);ap.add_argument('--gpu',type=int,choices=(0,1),required=True);ap.add_argument('--resume',action='store_true');args=ap.parse_args()
    root,base=directories(args.root,args.directory);plan=read(base/'plan.json');jobs=validate_plan(plan);job=next(j for j in jobs if j['id']==args.job)
    out=base/'jobs'/job['id'];out.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=(out/'worker.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if os.environ.get('CUDA_VISIBLE_DEVICES')!=str(args.gpu):raise RuntimeError('GPU binding differs')
    torch.set_num_threads(1)
    # J0 retains the legacy DSM bilinear decoder; CUDA backward can be nondeterministic.
    # Keep its native forward, log warnings rather than aborting the authorized baseline.
    torch.use_deterministic_algorithms(True,warn_only=job['id']=='J0');torch.backends.cudnn.benchmark=False
    torch.backends.cuda.matmul.allow_tf32=True;torch.backends.cudnn.allow_tf32=True
    if torch.__version__!='2.2.2+cu121':raise RuntimeError('use bound d18_dino environment Torch2.2.2+cu121')
    code=read(base/'code_manifest.json')
    for path,digest in code['files'].items():
        if sha(base/'code'/path)!=digest:raise RuntimeError('code snapshot changed: '+path)
    dino=read(root/'configs/rebuild_v1/d18_d19_night_20260927.json')['dino'];repo=within(root/dino['repository_dir'],'/home/jovyan/zzx')
    commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    if commit!=dino['repository_commit']:raise RuntimeError('DINO source commit changed')
    subprocess.run(['git','-C',str(repo),'diff','--exit-code','HEAD','--','dinov2','hubconf.py'],stdout=subprocess.DEVNULL,check=True)
    anchors,provenance=load_anchors(root,plan)
    signature=dict(job=job,plan_sha256=sha(base/'plan.json'),sources=code['files'],execution_commit=code['commit'],experts=provenance,torch_version=torch.__version__,input_manifest_sha256=sha(root/'records/rebuild_v1_d21_queue_20260928/input_manifest.json'),split_sha256=sha(root/'configs/rebuild_v1/potsdam_split_seed20260915.json'),base_config_sha256=sha(root/'configs/rebuild_v1/r05_quality_plus_dropout_16k.json'),dino_config_sha256=sha(root/'configs/rebuild_v1/d18_d19_night_20260927.json'),dino_commit=commit,physical_batch=16,gradient_accumulation=False,precision='trainBF16_evalFP32_TF32',determinism='strict except J0 native DSM bilinear backward warn_only; recorded in worker log',test6_loaded=False,independent_final_loaded=False)
    if signature['input_manifest_sha256']!=plan['input_manifest_sha256']:raise RuntimeError('input manifest differs')
    for name,digest in plan['expected_configs'].items():
        if signature[name]!=digest:raise RuntimeError('bound data/model config changed: '+name)
    if (out/'preflight.json').exists() and read(out/'preflight.json')!=signature:raise RuntimeError('job binding differs')
    write(out/'preflight.json',signature)
    if (out/'complete.json').exists():
        row=read(out/'complete.json')
        if row['signature']!=signature or sha(out/'selected.pth')!=row['selected_checkpoint_sha256']:raise RuntimeError('completed binding changed')
        print('D26_ALREADY_COMPLETE',job['id'],flush=True);return 0
    seed_all();experts=build_experts(root,anchors);seed_all();model=D26Segmenter(*experts,job['id']).cuda();del anchors,experts
    capacity=dict(total_parameters=sum(p.numel() for p in model.parameters()),trainable_parameters=sum(p.numel() for p in model.parameters() if p.requires_grad),trainable_names=[n for n,p in model.named_parameters() if p.requires_grad],arm=job['id'],initial_fusion_state_sha256=None)
    import hashlib
    digest=hashlib.sha256()
    for name,value in model.state_dict().items():
        if name.startswith(('project_rgb.','project_dsm.','fusion.')):digest.update(name.encode());digest.update(value.cpu().numpy().tobytes())
    capacity['initial_fusion_state_sha256']=digest.hexdigest();write(out/'model_capacity.json',capacity)
    cfg=plan['training'];optimizer=optimizer_for(model,cfg);last=out/'last_train_state.pth'
    start=0;best=None;counts=Counter();gradient=None
    if last.exists():
        if not args.resume:raise RuntimeError('existing checkpoint requires --resume')
        state=torch.load(last,map_location='cpu',weights_only=False)
        if state['signature']!=signature:raise RuntimeError('resume binding differs')
        model.load_state_dict(state['model'],strict=True);optimizer.load_state_dict(state['optimizer'])
        start=state['global_step'];best=state['best'];counts=Counter(state['treatment_counts']);gradient=state['gradient_check']
        random.setstate(state['random_state']);np.random.set_state(state['numpy_state']);torch.set_rng_state(state['torch_rng']);torch.cuda.set_rng_state_all(state['cuda_rng']);del state
    if not 0<=start<=8000:raise RuntimeError('invalid resume step')
    began=time.monotonic();state_progress=dict(job=job['id'],step=start,target=8000,physical_gpu=args.gpu)
    def progress(**kw):
        if kw.get('phase',state_progress.get('phase'))!=state_progress.get('phase'):
            for name in ('windows_done','windows_total','tile','condition'):state_progress.pop(name,None)
        state_progress.update(kw);state_progress.update(observed_at=now(),session_elapsed_seconds=time.monotonic()-began);write(out/'progress.json',state_progress)
    loader=Loader(root,plan);(out/'checkpoints').mkdir(exist_ok=True)
    def validate(step):
        nonlocal best
        save(last,model,optimizer,step,signature,best,counts,gradient)
        point=out/'checkpoints'/('step_%04d.pth'%step)
        if point.exists():
            old=torch.load(point,map_location='cpu',weights_only=False)
            if old['signature']!=signature or old['global_step']!=step or any(not torch.equal(old['model'][n].to(v.device),v) for n,v in model.state_dict().items()):raise RuntimeError('preserve conflicting step checkpoint')
            del old
        else:copy(last,point)
        binding=dict(training=signature,step=step,checkpoint_sha256=sha(point));model.eval()
        row=selection(model,loader,plan,out,binding,step,progress)
        if best is None or row['score']>best['metric']:
            copy(point,out/'selected.pth');best=dict(step=step,metric=row['score'],state_metrics=row['state_metrics'],checkpoint_sha256=sha(point))
        save(last,model,optimizer,step,signature,best,counts,gradient);model.train()
    if start in cfg['validation_steps']:validate(start)
    if start<8000:
        tiles={};progress(phase='loading_fit_tiles')
        for i,tile in enumerate(plan['data']['fit12']):
            tiles[tile]=loader(tile);progress(phase='loading_fit_tiles',tiles_loaded=i+1,tiles_total=12);print('D26_CACHE',job['id'],tile,i+1,flush=True)
        dataset=Crops(tiles,plan['data']['fit12'],loader.base['augmentation'],plan,start);batches=PrefetchedBatches(dataset,16,8,4,True);model.train()
        tick=time.monotonic();train_seconds=0.;completed=0
        for step,batch in enumerate(batches,start+1):
            optimizer.zero_grad(set_to_none=True)
            factor=.1+.9*step/100 if step<=100 else (8000-step)/7900
            for group in optimizer.param_groups:group['lr']=group['initial_lr']*factor
            tensors={k:v.cuda(non_blocking=True) for k,v in batch.items() if torch.is_tensor(v)}
            loss,denominators=objective(model,tensors)
            if not torch.isfinite(loss):raise RuntimeError('nonfinite loss')
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),float('inf'),error_if_nonfinite=True)
            if gradient is None or step%500==0:
                gradient=verify_gradients(model);write(out/'gradient_diagnostics'/('step_%04d.json'%step),dict(step=step,signature=signature,denominators=denominators,**gradient))
            optimizer.step();counts.update(denominators);counts.update(batch['treatment']);train_seconds+=time.monotonic()-tick;completed+=1
            if step==start+1 or step%20==0 or step==8000:
                value=float(loss.detach());progress(phase='training',step=step,loss=value,seconds_per_train_step=train_seconds/completed,remaining_train_hours=(8000-step)*train_seconds/completed/3600,gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated());print('D26_TRAIN',job['id'],step,8000,value,flush=True)
            del loss,tensors
            if step%500==0:save(last,model,optimizer,step,signature,best,counts,gradient)
            if step in cfg['validation_steps']:validate(step)
            tick=time.monotonic()
        if step!=8000:raise RuntimeError('stream ended early')
        del batches,dataset,tiles
    if best is None or sha(out/'selected.pth')!=best['checkpoint_sha256']:raise RuntimeError('selected checkpoint changed')
    del optimizer;torch.cuda.empty_cache()
    def fixed_factory():
        states,_=load_anchors(root,plan);r,d=build_experts(root,states)
        r.configure(False);d.configure(False);return FixedPair(r,d).cuda()
    refs=References(base,fixed_factory)
    # Fixed8000 primary diagnostics retain a common training age for interpretation.
    final=out/'checkpoints/step_8000.pth';state=torch.load(final,map_location='cpu',weights_only=False);model.load_state_dict(state['model'],strict=True);del state;model.eval()
    evaluate(model,loader,refs,plan,out,dict(training=signature,checkpoint_sha256=sha(final),step=8000),progress,plan['evaluation']['primary'],'fixed8000')
    selected=torch.load(out/'selected.pth',map_location='cpu',weights_only=False);model.load_state_dict(selected['model'],strict=True);del selected;model.eval()
    selected_binding=dict(training=signature,selected=best)
    if best['step']==8000:
        # Same exact checkpoint and input: reuse completed primary inference evidence.
        for condition in plan['evaluation']['primary']:
            for tile in plan['data']['validation']:
                source=out/'fixed8000'/condition/(tile+'.json');row=read(source)
                if row['binding']['checkpoint_sha256']!=best['checkpoint_sha256']:raise RuntimeError('fixed8000 reuse binding differs')
                row['binding']=selected_binding;row['reused_from']=dict(path=str(source),sha256=sha(source))
                for name,digest in row['predictions'].items():
                    old=out/'fixed8000'/condition/name/(tile+'.npy');new=out/'evaluation'/condition/name/(tile+'.npy')
                    if sha(old)!=digest:raise RuntimeError('fixed8000 prediction changed')
                    new.parent.mkdir(parents=True,exist_ok=True)
                    if new.exists():
                        if sha(new)!=digest:raise RuntimeError('preserve conflicting reused prediction')
                    else:os.link(old,new)
                target=out/'evaluation'/condition/(tile+'.json')
                if target.exists():
                    if read(target)!=row:raise RuntimeError('preserve conflicting reuse record')
                else:write(target,row)
    evaluate(model,loader,refs,plan,out,selected_binding,progress)
    write(out/'input_binding.json',dict(files=loader.verified,input_manifest_sha256=signature['input_manifest_sha256']))
    write(out/'complete.json',dict(signature=signature,selected=best,selected_checkpoint_sha256=best['checkpoint_sha256'],global_step=8000,treatment_counts=dict(counts),gradient_check=gradient,evaluation_summary_sha256=sha(out/'evaluation/summary.json'),fixed8000_summary_sha256=sha(out/'fixed8000/summary.json'),last_checkpoint_sha256=sha(last),completed_at=now(),test6_loaded=False,independent_final_loaded=False))
    progress(phase='complete',step=8000);print('D26_JOB_COMPLETE',job['id'],flush=True);return 0

if __name__=='__main__':
    try:sys.exit(main())
    except Exception:
        import traceback
        traceback.print_exc();sys.exit(2)
