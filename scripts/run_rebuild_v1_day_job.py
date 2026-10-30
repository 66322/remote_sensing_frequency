"""One bounded A/B/C/D/E job; never loads a held-out test tile."""
import argparse
import gc
import os
from pathlib import Path
import random
import sys
import time

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
os.environ.setdefault('XFORMERS_DISABLED', '1')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from torch.nn import functional as F

import day_portfolio_common as p
import d18_d19_night as d18
import d16_d17_portfolio as old
import run_rebuild_v1_d21_job as prior
import train_rebuild_v1_r02_budget_pilot as r02
from train_rebuild_v1_d16_d17 import sample, save
from model.rebuild_v1_night_screen import load_dino
from day_dino_compat import compatible_repo
from model.rebuild_v1_day_portfolio import (
    AContinuation, BAnchoredResidual, CDRestorationSegmenter, ReconstructionAudit, highpass)
from night_boundary_metrics import boundary_counts


def model_arm(job):
    if job['direction'] == 'A':
        return job['arm'].split('_')[0]
    if job['direction'] == 'B':
        return {'gray':'B1','raw_dsm':'B2','low_high_dsm':'B3',
                'low_rolled_high_dsm':'B4'}[job['arm']]
    return {'bicubic_ce':'C0','learned_ce':'C1',
            'learned_pixel_ce':'C2','learned_pixel_high_ce':'C3',
            'learned_ce_dsm':'D_ce_dsm',
            'learned_pixel_high_ce_dsm':'D_ph_dsm',
            'learned_pixel_high_ce_gray':'D_ph_gray'}[job['arm']]


def anchor(job):
    if job['direction'] not in ('A','B'):
        return None
    arm = model_arm(job) if job['direction'] == 'A' else 'R0'
    source = p.d21.run_dir(dict(dataset=job['dataset'], arm=arm, seed=42))
    info = p.read(source/'summary.json')
    checkpoint = source/'last_train_state.pth'
    if info['global_step'] != 16000 or info['signature']['test6_loaded'] is not False:
        raise RuntimeError('D21 anchor is incomplete or unsafe: '+str(source))
    if p.sha(checkpoint) != info['checkpoint_sha256']:
        raise RuntimeError('D21 anchor checkpoint SHA mismatch: '+str(source))
    return dict(path=str(checkpoint), sha256=info['checkpoint_sha256'], arm=arm)


def signature(job, smoke=False, profile=False, physical_micro_batch=None):
    plan = p.read(p.OUT/'plan.json')
    if any(p.sha(p.ROOT/name) != value for name,value in plan['source_sha256'].items()):
        raise RuntimeError('frozen source changed')
    p.verify_inputs(p.read(p.OUT/'input_manifest.json'))
    parent = d18.binding('P0', False)
    compat_repo, compat_sha = compatible_repo(d18.artifacts()[0])
    source = anchor(job)
    if physical_micro_batch is None:
        physical_micro_batch=p.read(p.OUT/'scope.json')['physical_micro_batch']
    return dict(job_id=job['job_id'], smoke=smoke, profile=profile,
        physical_micro_batch=physical_micro_batch,
        config_sha256=p.sha(p.CONFIG), manifest_sha256=p.sha(p.ROOT/p.config()['job_manifest']),
        input_manifest_sha256=p.sha(p.OUT/'input_manifest.json'),
        source_sha256=plan['source_sha256'], anchor=source,
        dino_commit=parent['dino_commit'], dino_sha256=parent['anchor_sha256'],
        dino_import_repository=str(compat_repo), dino_compat_manifest_sha256=compat_sha,
        torch_version=torch.__version__, test6_loaded=False,
        independent_final_loaded=False, checkpoint_selection='fixed_final_step')


def build(job, state=None):
    r02.set_seed(job['seed'])
    repo, weights = d18.artifacts()
    import_repo, _ = compatible_repo(repo)
    encoder = load_dino(import_repo, weights)
    arm = model_arm(job)
    if job['direction'] == 'A':
        model = AContinuation(encoder, arm, job['arm'].endswith('last4'))
    elif job['direction'] == 'B':
        model = BAnchoredResidual(encoder, arm)
    else:
        model = CDRestorationSegmenter(encoder, arm, job['scale'] or 2)
    if state is not None:
        model.load_state_dict(state['model'], strict=True)
    elif job['direction'] in ('A','B'):
        source = anchor(job)
        checkpoint = torch.load(source['path'], map_location='cpu', weights_only=False)
        if checkpoint['global_step'] != 16000:
            raise RuntimeError('D21 anchor step mismatch')
        if job['direction'] == 'A':
            model.load_state_dict(checkpoint['model'], strict=True)
        else:
            missing, unexpected = model.load_state_dict(checkpoint['model'], strict=False)
            if unexpected or set(missing) != {k for k in model.state_dict() if k.startswith('residual.')}:
                raise RuntimeError(f'B anchor state mismatch: {missing}, {unexpected}')
    model = model.to(r02.DEVICE)
    return model


def optimizer_for(model):
    cfg = p.config()['optimizer']
    encoder, head = [], []
    for name, param in model.named_parameters():
        if param.requires_grad:
            (encoder if name.startswith('encoder.') else head).append(param)
    if not head:
        raise RuntimeError('empty trainable head')
    groups = []
    if encoder:
        groups.append(dict(params=encoder, lr=cfg['encoder_lr'], initial_lr=cfg['encoder_lr']))
    groups.append(dict(params=head, lr=cfg['head_lr'], initial_lr=cfg['head_lr']))
    return torch.optim.AdamW(groups, betas=tuple(cfg['betas']), weight_decay=cfg['weight_decay'])


def set_lr(opt, step, total):
    cfg = p.config()['schedule']
    warm = cfg['warmup_steps']
    factor = cfg['warmup_ratio']+(1-cfg['warmup_ratio'])*step/warm if step <= warm else (
        1-(step-warm)/(total-warm))**cfg['poly_power']
    for group in opt.param_groups:
        group['lr'] = group['initial_lr']*factor


def treatment_arm(job):
    arm = model_arm(job)
    return 'P1' if arm in ('M1','B1','D_ph_gray') else 'P2'


def transformed(op, ds, job, conditions, key):
    return d18.transform(op, ds, treatment_arm(job), conditions,
                         torch.Generator().manual_seed(key))


def loss_for(model, job, optical, aux, gt, target, key):
    if job['direction'] in ('A','B'):
        logits = model(optical, aux)
        return old.deterministic_ce(logits, gt)
    if job['direction'] == 'E':
        rng = random.Random(key+17042)
        model.scale = 2 if rng.random() < p.config()['e_mixed_scale_probability_2'] else 4
        model.blur_sigma = p.config()['e_train_blur_sigma'] if rng.random() < p.config()['e_mixed_blur_probability'] else 0.
    logits, restored = model.forward_with_restored(optical, aux)
    loss = old.deterministic_ce(logits, gt)
    arm = model_arm(job)
    if arm in ('C2','C3','D_ph_dsm','D_ph_gray'):
        loss = loss + p.config()['loss_pixel_l1_weight']*F.l1_loss(restored, target)
    if arm in ('C3','D_ph_dsm','D_ph_gray'):
        loss = loss + p.config()['loss_highpass_l1_weight']*F.l1_loss(highpass(restored), highpass(target))
    return loss


def train(job, smoke=False, profile=False, physical_micro_batch=None):
    cfg = p.config()
    target_steps = cfg['profile_steps'] if profile else cfg['smoke_steps'] if smoke else job['steps']
    binding = signature(job, smoke, profile, physical_micro_batch)
    physical_micro_batch=binding['physical_micro_batch']
    if physical_micro_batch not in (2,4,8,16) or cfg['effective_batch']%physical_micro_batch:
        raise RuntimeError('invalid physical micro batch')
    out = p.run_dir(job, smoke, profile, physical_micro_batch if profile else None)
    out.mkdir(parents=True, exist_ok=True)
    ck, summary = out/'last_train_state.pth', out/'summary.json'
    if summary.is_file():
        previous = p.read(summary)
        if previous['signature'] != binding or previous['global_step'] != target_steps or p.sha(ck) != previous['checkpoint_sha256']:
            raise RuntimeError('existing job binding mismatch')
        return
    state = torch.load(ck,map_location='cpu',weights_only=False) if ck.is_file() else None
    if state is not None and state['signature'] != binding:
        raise RuntimeError('resume binding mismatch')
    model = build(job,state)
    optimizer = optimizer_for(model)
    if state is not None:
        optimizer.load_state_dict(state['optimizer'])
        old.restore_rng(state)
    start = int(state['global_step']) if state else 0
    counts = state['treatment_counts'] if state else {k:0 for k in p.read(d18.CONFIG)['treatment_probabilities']}
    del state
    ids = p.datasets()[job['dataset']]['train']
    if smoke or profile:
        ids = ids[:1]
    cache = {}
    for tile in ids:
        item = prior.load(job['dataset'],tile)
        cache[str(tile)] = (item['optical'],item['dsm'],item['full_gt'])
    base = p.read(d18.base_config())
    sampler = dict(base, patch=cfg['patch'], micro_batch=cfg['initial_micro_batch'])
    accum = cfg['initial_accum_steps']
    if sampler['micro_batch']*accum != cfg['effective_batch']:
        raise RuntimeError('effective batch mismatch')
    parent = p.read(d18.CONFIG)
    names,weights = list(parent['treatment_probabilities']),list(parent['treatment_probabilities'].values())
    model.train()
    began = time.monotonic()
    step_times=[]
    for step in range(start+1,target_steps+1):
        step_started=time.monotonic()
        optimizer.zero_grad(set_to_none=True)
        set_lr(optimizer,step,job['steps'])
        loss_value = 0.
        logical=[]
        for micro in range(accum):
            logical_step = step+16000 if job['direction']=='A' else step
            key = job['seed']*1000000+logical_step*100+micro
            op,ds,gt,_ = sample(cache,list(cache),sampler,key)
            conditions = random.Random(key+1).choices(names,weights=weights,k=len(op))
            for condition in conditions:
                counts[condition]+=1
            op2,ds2,_ = transformed(op,ds,job,conditions,key+2)
            clean_aux = op.mean(1) if treatment_arm(job)=='P1' else ds
            logical.append((op,clean_aux,op2,ds2,gt,key))
        per_group=physical_micro_batch//cfg['initial_micro_batch']
        for begin in range(0,accum,per_group):
            chunk=logical[begin:begin+per_group]
            gt=torch.cat([x[4] for x in chunk])
            target=torch.cat([x[0] for x in chunk])
            for clean in (True,False):
                view=torch.cat([x[0] if clean else x[2] for x in chunk])
                aux=torch.cat([x[1] if clean else x[3] for x in chunk])
                loss = .5*loss_for(model,job,view,aux,gt,target,chunk[0][5])
                if not bool(torch.isfinite(loss)):
                    raise RuntimeError(f'nonfinite loss at step {step}')
                weight=len(chunk)/accum
                loss_value += float(loss.detach())*weight
                (loss*weight).backward()
            del view,aux,gt,target
        del logical
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(),float('inf'),error_if_nonfinite=True)
        if not bool(torch.isfinite(norm)):
            raise RuntimeError('nonfinite gradient norm')
        optimizer.step()
        if profile:
            torch.cuda.synchronize()
            step_times.append(time.monotonic()-step_started)
        if step==1 or step%100==0 or step==target_steps:
            torch.cuda.synchronize()
            elapsed = time.monotonic()-began
            p.write(out/'progress.json',dict(job_id=job['job_id'],step=step,target=target_steps,
                elapsed_seconds=elapsed,seconds_per_step=elapsed/max(1,step-start),
                remaining_hours=(target_steps-step)*elapsed/max(1,step-start)/3600,
                gpu_peak_memory_mib=torch.cuda.max_memory_allocated()/1024**2,loss=loss_value))
            print('TRAIN',job['job_id'],step,target_steps,loss_value,flush=True)
        if step%cfg['checkpoint_every']==0 or step==target_steps:
            save(ck,model,None,optimizer,step,binding,counts)
    training_seconds=time.monotonic()-began
    model.eval()
    if job['direction']=='E':
        model.scale,model.blur_sigma=2,0.
    op,ds,_,_=sample(cache,list(cache),dict(sampler,micro_batch=1),job['seed']*1000000+999999)
    aux=op.mean(1) if treatment_arm(job)=='P1' else ds
    with torch.no_grad():
        pred=model(op,aux).argmax(1).cpu()
    probe=out/'clean_probe.pth'
    tmp=probe.with_suffix('.tmp')
    torch.save(dict(rgb=op.cpu(),aux=aux.cpu(),pred=pred),tmp)
    os.replace(tmp,probe)
    profile_eval=None
    if profile:
        optical,dsm,_=cache[str(ids[0])]
        secondary=np.ascontiguousarray(optical.mean(2) if treatment_arm(job)=='P1' else dsm)
        eval_started=time.monotonic()
        inference_model=model if job['direction'] in ('A','B') else ReconstructionAudit(model)
        prediction=r02.infer_tile(inference_model,np.ascontiguousarray(optical),secondary,
            cfg['patch'],cfg['evaluation_stride'][job['dataset']],cfg['evaluation_batch'])
        torch.cuda.synchronize()
        profile_eval=dict(train_tile=str(ids[0]),shape=list(prediction.shape),
            full_train_tile_evaluation_seconds=time.monotonic()-eval_started,
            prediction_checksum=int(prediction.astype(np.int64).sum()),
            reconstruction=None if inference_model is model else inference_model.summary())
    p.write(summary,dict(job=job,signature=binding,global_step=target_steps,
        checkpoint_sha256=p.sha(ck),clean_probe_sha256=p.sha(probe),
        treatment_counts=counts,training_seconds=training_seconds,
        seconds_this_session=time.monotonic()-began,
        train_tiles=ids,development_labels_loaded=False,test6_loaded=False,
        trainable_parameters=sum(x.numel() for x in model.parameters() if x.requires_grad),
        total_parameters=sum(x.numel() for x in model.parameters()),
        gpu_peak_memory_mib=torch.cuda.max_memory_allocated()/1024**2,
        gpu_peak_reserved_mib=torch.cuda.max_memory_reserved()/1024**2,
        steady_step_median_seconds=float(np.median(step_times[5:])) if len(step_times)>5 else None,
        profile_full_train_tile_evaluation=profile_eval))


def evaluation_conditions(job,smoke):
    if smoke:
        return ['clean','aux_zero']
    cfg=p.config()
    if job['direction'] in ('A','B'):
        return cfg['evaluation_conditions_ab']
    if job['direction']=='E':
        return ['scale2_clean','scale4_clean','scale2_unseen_blur','scale4_unseen_blur']
    return cfg['evaluation_conditions_cde']


def evaluate(job,smoke=False):
    cfg=p.config()
    binding=signature(job,smoke)
    run,out=p.run_dir(job,smoke),p.eval_dir(job,smoke)
    info=p.read(run/'summary.json')
    ck=run/'last_train_state.pth'
    if info['signature']!=binding or p.sha(ck)!=info['checkpoint_sha256']:
        raise RuntimeError('training/checkpoint binding mismatch')
    signature_eval=dict(training=binding,checkpoint_sha256=p.sha(ck))
    out.mkdir(parents=True,exist_ok=True)
    state=torch.load(ck,map_location='cpu',weights_only=False)
    if state['signature']!=binding:
        raise RuntimeError('checkpoint signature mismatch')
    model=build(job,state).eval()
    if job['direction']=='E':
        model.scale,model.blur_sigma=2,0.
    probe=torch.load(run/'clean_probe.pth',map_location='cpu',weights_only=False)
    if p.sha(run/'clean_probe.pth')!=info['clean_probe_sha256']:
        raise RuntimeError('training probe hash mismatch')
    with torch.no_grad():
        reproduced=model(probe['rgb'].to(r02.DEVICE),probe['aux'].to(r02.DEVICE)).argmax(1).cpu()
    if not torch.equal(reproduced,probe['pred']):
        raise RuntimeError('checkpoint reload did not reproduce training probe')
    ids=p.datasets()[job['dataset']]['train'][:1] if smoke else p.datasets()[job['dataset']]['dev']
    conditions=evaluation_conditions(job,smoke)
    scopes=['full'] if smoke or job['dataset']=='vaihingen' else ['full','noboundary']
    began=time.monotonic()
    for tile in ids:
        item=None
        for condition in conditions:
            predpath,detail=out/condition/f'{tile}.npy',out/condition/f'{tile}.json'
            if detail.is_file() and predpath.is_file():
                row=p.read(detail)
                if row['signature']!=signature_eval or row['prediction_sha256']!=p.sha(predpath):
                    raise RuntimeError('existing prediction binding mismatch')
                continue
            if item is None:
                item=prior.load(job['dataset'],tile,development=not smoke)
                if smoke:
                    item={k:v[:512,:512] if v is not None else None for k,v in item.items()}
            op=torch.from_numpy(np.ascontiguousarray(item['optical'].transpose(2,0,1)))[None]
            ds=torch.from_numpy(np.ascontiguousarray(item['dsm']))[None]
            if job['direction']=='E':
                model.scale=2 if condition.startswith('scale2') else 4
                model.blur_sigma=cfg['e_unseen_eval_blur_sigma'] if 'unseen_blur' in condition else 0.
                transform_condition='clean'
            else:
                transform_condition=condition
            treated,aux,_=transformed(op,ds,job,[transform_condition],42+sum(map(ord,str(tile))))
            optical=np.ascontiguousarray(treated[0].permute(1,2,0).numpy())
            secondary=np.ascontiguousarray(aux[0].numpy())
            inference_model=model if job['direction'] in ('A','B') else ReconstructionAudit(model)
            pred=r02.infer_tile(inference_model,optical,secondary,cfg['patch'],
                    cfg['evaluation_stride'][job['dataset']],cfg['evaluation_batch'])
            reconstruction=None if inference_model is model else inference_model.summary()
            if job['direction']=='B' and condition=='aux_zero' and not smoke:
                old_job=dict(dataset=job['dataset'],arm='R0',seed=42)
                reference=p.d21.eval_dir(old_job)/'aux_zero'/f'{tile}.npy'
                reference_detail=p.d21.eval_dir(old_job)/'aux_zero'/f'{tile}.json'
                if not reference.is_file() or not reference_detail.is_file():
                    raise RuntimeError('D21 R0 reference prediction missing: '+str(reference))
                if p.sha(reference)!=p.read(reference_detail)['prediction_sha256']:
                    raise RuntimeError('D21 R0 reference prediction SHA mismatch')
                if not np.array_equal(pred,np.load(reference)):
                    raise RuntimeError('B auxiliary-zero prediction differs from frozen R0 anchor')
            values={}
            for scope in scopes:
                label=item[scope+'_gt']
                cm=np.zeros((6,6),dtype=np.int64)
                r02.update_cm(cm,label,pred)
                expected=int(((label>=0)&(label<6)).sum())
                if int(cm.sum())!=expected:
                    raise RuntimeError('confusion matrix count mismatch')
                values[scope]=dict(cm=cm.tolist(),metrics=prior.metrics(cm))
            boundaries=boundary_counts(item['full_gt'],pred,cfg['boundary_tolerance_pixels']) if condition in ('clean','scale2_clean','scale4_clean') else None
            predpath.parent.mkdir(parents=True,exist_ok=True)
            tmp=predpath.with_suffix('.tmp.npy')
            np.save(tmp,pred)
            os.replace(tmp,predpath)
            p.write(detail,dict(signature=signature_eval,tile=str(tile),condition=condition,
                scopes=values,prediction_sha256=p.sha(predpath),boundary_counts=boundaries,
                reconstruction=reconstruction,
                model_scale=getattr(model,'scale',None),model_blur_sigma=getattr(model,'blur_sigma',None)))
            print('EVAL',job['job_id'],tile,condition,flush=True)
    results={}
    for condition in conditions:
        rows={str(tile):p.read(out/condition/f'{tile}.json') for tile in ids}
        pooled={}
        for scope in scopes:
            cm=sum((np.asarray(row['scopes'][scope]['cm'],dtype=np.int64) for row in rows.values()),
                   np.zeros((6,6),dtype=np.int64))
            pooled[scope]=dict(cm=cm.tolist(),metrics=prior.metrics(cm))
        results[condition]=dict(pooled=pooled,tiles={tile:{k:v for k,v in row.items() if k!='signature'}
            for tile,row in rows.items()})
    p.write(out/'summary.json',dict(job=job,signature=signature_eval,smoke=smoke,
        conditions=results,evaluation_ids=ids,trainable_parameters=info['trainable_parameters'],
        checkpoint_reload_pass=True,test6_loaded=False,independent_final_loaded=False,
        primary_scope=cfg['primary_scope'][job['dataset']],
        evaluation_seconds=time.monotonic()-began))
    print('JOB COMPLETE',job['job_id'],flush=True)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--job-id',required=True)
    ap.add_argument('--smoke',action='store_true')
    ap.add_argument('--profile',action='store_true')
    ap.add_argument('--micro-batch',type=int)
    args=ap.parse_args()
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1:
        raise RuntimeError('exactly one visible CUDA GPU required')
    job=next((j for j in p.jobs() if j['job_id']==args.job_id),None)
    if job is None:
        raise ValueError(args.job_id)
    train(job,args.smoke,args.profile,args.micro_batch)
    gc.collect()
    torch.cuda.empty_cache()
    if not args.profile:
        evaluate(job,args.smoke)


if __name__=='__main__':
    main()
