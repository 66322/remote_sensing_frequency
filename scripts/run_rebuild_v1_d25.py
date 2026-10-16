"""One 4000-step D25 job, direct physical batch16, validation-only selection."""
import argparse
from collections import Counter
import contextlib
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
os.environ.setdefault('XFORMERS_DISABLED', '1')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from model.rebuild_v1_d21_detail import DetailDinoSegmenter
from model.rebuild_v1_d25 import D25Segmenter
from d25_common import read, write, sha, directories, now, validate_plan, within
from d24_data import Loader, Crops, PrefetchedBatches
from d25_objectives import objective, backward, verify_gradients
from d25_evaluation import References, select_validation, evaluate


def seed_all(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def load_anchors(root, plan):
    states, provenance = {}, {}
    for arm in ('R0','M0'):
        path = root/'runs/rebuild_v1'/('D21_potsdam_'+arm+'_seed42_16000_20260928')/'last_train_state.pth'
        if sha(path) != plan['initialization'][arm+'_sha256']:
            raise RuntimeError('anchor checkpoint checksum changed: '+arm)
        state = torch.load(path,map_location='cpu',weights_only=False)
        if state['global_step'] != 16000 or state['signature']['test6_loaded']:
            raise RuntimeError('invalid D21 anchor')
        if state['signature']['torch_version'] != torch.__version__:
            raise RuntimeError('use the existing d18_dino environment: Torch version differs')
        states[arm] = state['model']
        provenance[arm] = dict(path=str(path),sha256=plan['initialization'][arm+'_sha256'],step=16000)
    return states,provenance


def make_encoder(root):
    config = read(root/'configs/rebuild_v1/d18_d19_night_20260927.json')['dino']
    repo = within(root/config['repository_dir'], '/home/jovyan/zzx')
    # Complete encoder weights are in each bound D21 model checkpoint.
    return torch.hub.load(str(repo),'dinov2_vits14',source='local',pretrained=False)


def build(root, job, anchors):
    seed_all(job['seed'])
    model=D25Segmenter(make_encoder(root),job['decoder_mode'],job['optical_only'])
    model.initialize(anchors['M0'])
    model.cuda()
    teachers={}
    if job['pair']:
        teacher=DetailDinoSegmenter(make_encoder(root),'R0')
        teacher.load_state_dict(anchors['R0'],strict=True)
        teachers['R0']=teacher.cuda().eval().requires_grad_(False)
    return model,teachers

def fixed_factory(root,plan):
    anchors,_=load_anchors(root,plan)
    models={}
    for arm in ('R0','M0'):
        model=DetailDinoSegmenter(make_encoder(root),arm)
        model.load_state_dict(anchors[arm],strict=True)
        models[arm]=model.cuda().eval().requires_grad_(False)
    return models


def optimizer_for(model, cfg):
    groups = []
    for encoder,lr in ((True,cfg['encoder_last4_lr']),(False,cfg['head_lr'])):
        params = [p for name,p in model.named_parameters() if p.requires_grad and name.startswith('encoder.')==encoder]
        if params:
            groups.append(dict(params=params,lr=lr,initial_lr=lr))
    return torch.optim.AdamW(groups,betas=tuple(cfg['betas']),weight_decay=cfg['weight_decay'])


def save_state(path, model, optimizer, step, signature, best, counts, gradient_check):
    tmp = path.with_suffix('.tmp')
    torch.save(dict(model=model.state_dict(),optimizer=optimizer.state_dict(),global_step=step,
               signature=signature,best=best,treatment_counts=dict(counts),gradient_check=gradient_check,
               random_state=random.getstate(),numpy_state=np.random.get_state(),
               torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all()),tmp)
    os.replace(tmp,path)


def restore_rng(state):
    random.setstate(state['random_state'])
    np.random.set_state(state['numpy_state'])
    torch.set_rng_state(state['torch_rng'])
    torch.cuda.set_rng_state_all(state['cuda_rng'])


def atomic_copy(source, target):
    tmp = target.with_suffix('.tmp')
    shutil.copyfile(source,tmp)
    os.replace(tmp,target)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--directory',type=Path,required=True)
    ap.add_argument('--job',required=True)
    ap.add_argument('--resume',action='store_true')
    args = ap.parse_args()
    root,base = directories(args.root,args.directory)
    plan = read(base/'plan.json')
    jobs = validate_plan(plan)
    job = next(j for j in jobs if j['id']==args.job)
    out = base/'jobs'/job['id']
    out.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock = (out/'worker.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if os.environ.get('CUDA_VISIBLE_DEVICES') != str(job['gpu']):
        raise RuntimeError('physical GPU binding mismatch')
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    anchors,provenance = load_anchors(root,plan)
    dino=read(root/'configs/rebuild_v1/d18_d19_night_20260927.json')['dino']
    dino_repo=within(root/dino['repository_dir'],'/home/jovyan/zzx')
    dino_commit=subprocess.check_output(['git','-C',str(dino_repo),'rev-parse','HEAD'],text=True).strip()
    if dino_commit!=dino['repository_commit']:
        raise RuntimeError('DINO source commit changed')
    subprocess.run(['git','-C',str(dino_repo),'diff','--exit-code','HEAD','--','dinov2','hubconf.py'],
                   stdout=subprocess.DEVNULL,check=True)
    code = read(base/'code_manifest.json')
    for path,expected in code['files'].items():
        if sha(base/'code'/path)!=expected:
            raise RuntimeError('execution snapshot changed: '+path)
    signature = dict(job=job,plan_sha256=sha(base/'plan.json'),sources=code['files'],
                     execution_commit=code['commit'],anchors=provenance,torch_version=torch.__version__,
                     base_config_sha256=sha(root/'configs/rebuild_v1/r05_quality_plus_dropout_16k.json'),
                     dino_config_sha256=sha(root/'configs/rebuild_v1/d18_d19_night_20260927.json'),dino_commit=dino_commit,
                     split_sha256=sha(root/'configs/rebuild_v1/potsdam_split_seed20260915.json'),
                     input_manifest_sha256=sha(root/'records/rebuild_v1_d21_queue_20260928/input_manifest.json'),
                     physical_batch=16,gradient_accumulation=False,train_precision='bf16',eval_precision='fp32_tf32',
                     validation_batch=8,checkpoint_selection='best_clean_Val2_NoBoundary_fg5',
                     decoder_mode=job['decoder_mode'],gradient_mode=job['gradient_mode'],
                     test6_loaded=False,independent_final_loaded=False)
    if (out/'preflight.json').exists():
        if read(out/'preflight.json')!=signature:
            raise RuntimeError('existing job binding differs')
    else:
        write(out/'preflight.json',signature)
    if (out/'complete.json').exists():
        previous=read(out/'complete.json')
        if previous['signature']!=signature or sha(out/'selected.pth')!=previous['selected_checkpoint_sha256']:
            raise RuntimeError('completed job checksum/binding mismatch')
        print('D25_ALREADY_COMPLETE',job['id'],flush=True)
        return 0
    model,teachers = build(root,job,anchors)
    del anchors
    write(out/'model_capacity.json',dict(total_parameters=sum(p.numel() for p in model.parameters()),trainable_parameters=sum(p.numel() for p in model.parameters() if p.requires_grad),shared_names=sorted(model.shared_parameter_names()),decoder_mode=job['decoder_mode'],gradient_mode=job['gradient_mode']))
    cfg=plan['training']
    optimizer=optimizer_for(model,cfg)
    last=out/'last_train_state.pth'
    best,counts,gradient_check,start = None,Counter(),None,0
    if last.exists():
        if not args.resume:
            raise RuntimeError('existing checkpoint requires explicit resume')
        state=torch.load(last,map_location='cpu',weights_only=False)
        if state['signature']!=signature:
            raise RuntimeError('resume signature mismatch')
        model.load_state_dict(state['model'],strict=True)
        optimizer.load_state_dict(state['optimizer'])
        best,counts,gradient_check,start = state['best'],Counter(state['treatment_counts']),state['gradient_check'],state['global_step']
        restore_rng(state)
        del state
    if start < 0 or start > 4000:
        raise RuntimeError('invalid resume step')
    started=time.monotonic()
    progress_state=dict(job=job['id'],step=start,target=4000)
    def progress(**kw):
        if kw.get('phase',progress_state.get('phase'))!=progress_state.get('phase'):
            for name in ('windows_done','windows_total','tile','condition','tiles_loaded','tiles_total'):
                progress_state.pop(name,None)
        progress_state.update(kw)
        progress_state.update(observed_at=now(),session_elapsed_seconds=time.monotonic()-started)
        write(out/'progress.json',progress_state)
    loader=Loader(root,plan)
    refs=References(root,plan,base,lambda:fixed_factory(root,plan))
    (out/'checkpoints').mkdir(exist_ok=True)
    def checkpoint(step):
        save_state(last,model,optimizer,step,signature,best,counts,gradient_check)
        point=out/'checkpoints'/('step_%04d.pth'%step)
        if not point.exists():
            atomic_copy(last,point)
        else:
            old=torch.load(point,map_location='cpu',weights_only=False)
            if old['signature']!=signature or old['global_step']!=step or any(
                    not torch.equal(old['model'][k].to(v.device),v) for k,v in model.state_dict().items()):
                raise RuntimeError('existing step checkpoint differs; preserve evidence')
            del old
        return point
    def validation(step):
        nonlocal best
        point=out/'checkpoints'/('step_%04d.pth'%step)
        if not point.exists():
            atomic_copy(last,point)
        binding=dict(training=signature,checkpoint_sha256=sha(point),step=step)
        model.eval()
        row=select_validation(model,loader,plan,out,binding,step,progress)
        value=row['pooled']['mIoU_fg5']
        if best is None or value>best['metric']:
            atomic_copy(point,out/'selected.pth')
            best=dict(step=step,metric=value,checkpoint_sha256=sha(point))
        if not (out/'selected.pth').exists() and best['step']==step:
            atomic_copy(point,out/'selected.pth')
        save_state(last,model,optimizer,step,signature,best,counts,gradient_check)
        model.train()
    if start in cfg['validation_steps']:
        validation(start)
    if start<4000:
        progress(phase='loading_fit_tiles')
        tiles={}
        for i,tile in enumerate(plan['data']['fit12']):
            tiles[tile]=loader(tile)
            progress(phase='loading_fit_tiles',tiles_loaded=i+1,tiles_total=12)
            print('D25_CACHE',job['id'],tile,i+1,12,flush=True)
        dataset=Crops(tiles,plan['data']['fit12'],loader.base['augmentation'],job['augmentation'],start,4000)
        batches=PrefetchedBatches(dataset,batch=16,workers=8,prefetch_batches=4,pin_memory=True)
        model.train()
        tick=time.monotonic()
        train_seconds=0.
        completed=0
        for step,batch in enumerate(batches,start+1):
            optimizer.zero_grad(set_to_none=True)
            factor=.1+.9*step/100 if step<=100 else (4000-step)/3900
            for group in optimizer.param_groups:
                group['lr']=group['initial_lr']*factor
            tensors={k:v.cuda(non_blocking=True) for k,v in batch.items() if torch.is_tensor(v)}
            present,missing,objective_counts=objective(model,teachers,job,tensors,plan)
            loss=present+missing
            if not bool(torch.isfinite(loss)):
                raise RuntimeError('nonfinite training loss')
            diagnose=(step==start+1 or step%plan['gradient']['diagnostic_every']==0 or step==4000)
            gradient_stats=backward(model,present,missing,job['gradient_mode'],diagnose)
            if diagnose and gradient_stats is not None:
                if job['decoder_mode'] in ('separate','average') and objective_counts['missing_pixels']>0 and not gradient_stats['decoder_optical.gradient_nonzero']:
                    raise RuntimeError('missing decoder has no gradient')
                write(out/'gradient_diagnostics'/('step_%04d.json'%step),dict(step=step,signature=signature,**gradient_stats,**objective_counts))
            torch.nn.utils.clip_grad_norm_(model.parameters(),float('inf'),error_if_nonfinite=True)
            if gradient_check is None:
                gradient_check=verify_gradients(model,list(teachers.values()))
                write(out/'gradient_check.json',dict(signature=signature,**gradient_check))
            optimizer.step()
            counts.update(objective_counts)
            counts.update('Q:'+v for v in batch['q'])
            counts.update('D:'+v for v in batch['d'])
            value=float(loss.detach()) if step==start+1 or step%20==0 or step==4000 else None
            del present,missing,loss,tensors
            train_seconds+=time.monotonic()-tick
            completed+=1
            if value is not None:
                torch.cuda.synchronize()
                progress(phase='training',step=step,loss=value,objective_counts=objective_counts,
                         seconds_per_train_step=train_seconds/completed,
                         remaining_training_hours=(4000-step)*train_seconds/completed/3600,
                         gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated())
                print('D25_TRAIN',job['id'],step,4000,value,flush=True)
            if step%cfg['checkpoint_every']==0:
                checkpoint(step)
            if step in cfg['validation_steps']:
                validation(step)
            tick=time.monotonic()
        if step!=4000:
            raise RuntimeError('training stream ended before the frozen budget')
        del batches,dataset,tiles
    if best is None or sha(out/'selected.pth')!=best['checkpoint_sha256']:
        raise RuntimeError('selected checkpoint is absent or changed')
    final_prototype_support=model.prototype.support.cpu().tolist() if model.prototype is not None else None
    selected=torch.load(out/'selected.pth',map_location='cpu',weights_only=False)
    model.load_state_dict(selected['model'],strict=True)
    del selected,teachers,optimizer
    torch.cuda.empty_cache()
    model.eval()
    selected_binding=dict(training=signature,selected=best)
    evaluate(model,loader,refs,plan,out,selected_binding,progress)
    write(out/'input_binding.json',dict(files=loader.verified,source_manifest=signature['input_manifest_sha256']))
    result=dict(signature=signature,selected=best,selected_checkpoint_sha256=best['checkpoint_sha256'],
                global_step=4000,gradient_check=gradient_check,treatment_counts=dict(counts),
                evaluation_summary_sha256=sha(out/'evaluation/summary.json'),last_checkpoint_sha256=sha(last),
                final_training_prototype_support=final_prototype_support,
                selected_prototype_support=model.prototype.support.cpu().tolist() if model.prototype is not None else None,
                completed_at=now(),test6_loaded=False,independent_final_loaded=False)
    write(out/'complete.json',result)
    progress(phase='complete',step=4000)
    print('D25_JOB_COMPLETE',job['id'],flush=True)
    return 0


if __name__=='__main__':
    try:
        sys.exit(main())
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
