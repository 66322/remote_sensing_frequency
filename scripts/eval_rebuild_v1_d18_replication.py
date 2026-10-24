"""Resumable seed17 Val2 evaluation with seed42-matched corruptions."""
import argparse
import os
from pathlib import Path

os.environ.setdefault('CUDA_VISIBLE_DEVICES', '0')
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import numpy as np
import torch
import train_rebuild_v1_r01_optical_only as r01
import train_rebuild_v1_r02_budget_pilot as r02
from d15_capability import joint
import d18_replication as p
import d16_d17_portfolio as old
from night_boundary_metrics import boundary_counts


def safe_metrics(cm):
    return {key:(None if isinstance(value,float) and not np.isfinite(value) else value)
            for key,value in r02.metrics_from_cm(cm).items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', choices=p.ARMS, required=True)
    ap.add_argument('--seed', type=int, choices=(17,), default=17)
    ap.add_argument('--smoke', action='store_true')
    args = ap.parse_args()
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError('exactly one visible CUDA GPU required')
    rep, cfg = p.validate()
    split = p.read(p.ROOT / cfg['split_file'])
    ids = split['val2'][:1] if args.smoke else split['val2']
    if set(ids) & set(split['train16'] + split['historical_exposed_test6']) or len(split['val2']) != 2:
        raise RuntimeError('Val2 split boundary failed')
    run = p.output(args.arm,args.seed,args.smoke)
    ck = run / 'last_train_state.pth'
    train = p.read(run / 'summary.json')
    base_path = p.base_config()
    expected = p.binding(args.arm,args.smoke)
    if train['signature'] != expected or train['global_step'] != (1 if args.smoke else p.steps(args.arm)):
        raise RuntimeError('train binding/budget mismatch')
    checksum = p.sha(ck)
    if checksum != train['checkpoint_sha256']:
        raise RuntimeError('checkpoint changed after training completion')
    refdir, refpath = old.anchor_paths('R01',rep['historical_r01_reference_seed'])
    refck = refdir / 'best_model.pth'
    signature = dict(training=expected, checkpoint_sha256=checksum, reference_sha256=p.sha(refck),
                     reference_config_sha256=p.sha(refpath), evaluation_sources={name:p.sha(p.ROOT/name) for name in (
                     'scripts/eval_rebuild_v1_d18_replication.py','scripts/train_rebuild_v1_r01_optical_only.py',
                     'scripts/d15_capability.py','model/rebuild_v1_optical_only.py')})
    out = p.evaluation_output(args.arm,args.seed,args.smoke)
    summary = out / 'summary.json'
    if summary.is_file():
        if p.read(summary)['signature'] != signature:
            raise RuntimeError('evaluation binding mismatch')
        print('EVAL REUSED', out, flush=True)
        return
    out.mkdir(parents=True,exist_ok=True)
    r02.set_seed(args.seed)
    base = p.read(base_path)
    refcfg = p.read(refpath)
    state = torch.load(ck,map_location='cpu',weights_only=False)
    if state['signature'] != expected:
        raise RuntimeError('checkpoint signature mismatch')
    net = p.build(args.arm,base,r02.DEVICE,state)
    probe_path = run/'clean_probe.pth'
    if p.sha(probe_path) != train['clean_probe_sha256']:
        raise RuntimeError('clean probe changed')
    probe = torch.load(probe_path,map_location='cpu',weights_only=False)
    net.eval()
    with torch.no_grad():
        reproduced = net(probe['rgb'].to(r02.DEVICE),probe['aux'].to(r02.DEVICE)).argmax(1).cpu()
    if not torch.equal(reproduced,probe['pred']):
        raise RuntimeError('saved clean probe reproduction failed')
    print('CLEAN CHECKPOINT REPRODUCTION PASS',flush=True)
    del probe,reproduced
    reference,_,_ = r01.build_model(refcfg,Path(refcfg['pretrain']),
        resume_state=torch.load(refck,map_location='cpu',weights_only=False))
    net.eval()
    reference.eval()
    def finite_output(_module, _inputs, logits):
        if not bool(torch.isfinite(logits).all()):
            raise RuntimeError('nonfinite inference logits; preserve checkpoint for diagnosis')
    net.register_forward_hook(finite_output)
    reference.register_forward_hook(finite_output)
    conditions = ['clean','rgb_contrast060','aux_shift8'] if args.smoke else cfg['evaluation_conditions']+cfg['diagnostics']
    result = {}
    for condition in conditions:
        file = out / f'{condition}.json'
        if file.is_file():
            saved = p.read(file)
            if saved['signature'] != signature:
                raise RuntimeError('partial evaluation binding mismatch')
            result[condition] = saved['result']
            continue
        pooled = {scope:np.zeros((6,6),dtype=np.int64) for scope in ('full','noboundary')}
        fallback_pooled = {scope:np.zeros((6,6),dtype=np.int64) for scope in pooled}
        total = {k:0 for k in ('valid','both_correct','only_r01_correct','only_candidate_correct','both_wrong')}
        tiles = {}
        for tile in ids:
            item = r02.load_tile(Path(base['data_root']),tile,need_nb=True)
            if args.smoke:
                item = {k:v[:512,:512] if getattr(v,'ndim',0)>=2 else v for k,v in item.items()}
            op = torch.from_numpy(np.ascontiguousarray(item['optical'].transpose(2,0,1)))[None]
            ds = torch.from_numpy(np.ascontiguousarray(item['dsm']))[None]
            treated, aux, available = p.transform(op,ds,args.arm,[condition],
                torch.Generator().manual_seed(rep['evaluation_corruption_seed']+sum(map(ord,tile))))
            optical = np.ascontiguousarray(treated[0].permute(1,2,0).numpy())
            secondary = np.ascontiguousarray(aux[0].numpy())
            patch = base['patch']
            stride = base['validation']['stride']
            batch = base['validation']['inference_batch']
            pred = r02.infer_tile(net,optical,secondary,patch,stride,batch)
            ref = r01.infer_tile(reference,optical,refcfg['patch'],refcfg['validation']['stride'],refcfg['validation']['inference_batch'])
            if args.smoke:
                repeated = r02.infer_tile(net,optical,secondary,patch,stride,batch)
                if not np.array_equal(pred,repeated):
                    p.write(out / 'diagnostic.json',dict(error='nondeterministic clean prediction',signature=signature))
                    raise RuntimeError('clean deterministic reproduction failed')
            fallback = np.where(available[0].numpy(),pred,ref)
            details = {}
            for scope,label in (('full',item['full_gt']),('noboundary',item['noboundary_gt'])):
                cm = np.zeros((6,6),dtype=np.int64)
                fcm = np.zeros_like(cm)
                r02.update_cm(cm,label,pred)
                r02.update_cm(fcm,label,fallback)
                pooled[scope] += cm
                fallback_pooled[scope] += fcm
                details[scope] = dict(cm=cm.tolist(),metrics=safe_metrics(cm),
                                     availability_fallback_cm=fcm.tolist(),availability_fallback_metrics=safe_metrics(fcm))
            counts = joint(item['noboundary_gt'],ref,pred)
            for k,v in counts.items():
                total[k] += v
            boundaries = boundary_counts(item['full_gt'],pred,cfg['boundary_tolerance_pixels'])
            np.savez_compressed(out/f'{condition}_{tile}_prediction.npz',prediction=pred)
            tiles[tile] = dict(metrics=details,joint_noboundary=counts,boundary_counts=boundaries)
            print(f'EVAL {args.arm} seed{args.seed} {condition} {tile}',flush=True)
        value = dict(tiles=tiles,joint_noboundary=total,
                     pooled={scope:dict(cm=cm.tolist(),metrics=safe_metrics(cm),
                        availability_fallback_cm=fallback_pooled[scope].tolist(),
                        availability_fallback_metrics=safe_metrics(fallback_pooled[scope])) for scope,cm in pooled.items()})
        p.write(file,dict(signature=signature,result=value))
        result[condition] = value
    if args.arm == 'P0':
        for condition in conditions:
            if condition.startswith('aux_'):
                for scope in ('full','noboundary'):
                    if result[condition]['pooled'][scope]['cm'] != result['clean']['pooled'][scope]['cm']:
                        raise RuntimeError('RGB-only auxiliary invariance check failed')
    p.write(summary,dict(arm=args.arm,seed=args.seed,smoke=args.smoke,signature=signature,
                        conditions=result,val2_loaded=True,test6_loaded=False,
                        config_sha256=p.sha(p.CONFIG), replication_config_sha256=p.sha(p.REPLICATION),
                        evaluation_corruption_seed=rep['evaluation_corruption_seed'],
                        historical_r01_reference_seed=rep['historical_r01_reference_seed'],
                        physical_gpu=os.environ['CUDA_VISIBLE_DEVICES'],
                        auxiliary_semantics='gray damage' if args.arm=='P1' else ('unused auxiliary' if args.arm=='P0' else 'DSM damage'),
                        boundary_protocol=dict(tolerance_pixels=cfg['boundary_tolerance_pixels'],source='FullGT',classes=5),
                        trainable_parameters=train['trainable_parameters'],total_parameters=train['total_parameters'],
                        added_module_conv_attention_MACs_per_patch=train['added_module_conv_attention_MACs_per_patch'],
                        clean_reproduction_pass=True))
    print('EVAL COMPLETE',out,flush=True)


if __name__ == '__main__':
    main()
