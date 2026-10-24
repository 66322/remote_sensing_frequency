"""Matched seed17 D18 training; no validation imagery loaded during training."""
import argparse
import os
import random
import time
from pathlib import Path

os.environ.setdefault('CUDA_VISIBLE_DEVICES', '0')
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import torch
import d18_replication as p
import d16_d17_portfolio as old
import train_rebuild_v1_r02_budget_pilot as r02
from train_rebuild_v1_d16_d17 import sample, save


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--arm', choices=p.ARMS, required=True)
    ap.add_argument('--seed', type=int, choices=[17], default=17)
    ap.add_argument('--smoke', action='store_true')
    args = ap.parse_args()
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError('one visible CUDA GPU required')
    _, cfg = p.validate()
    base = p.read(p.base_config())
    split = p.read(p.ROOT/cfg['split_file'])
    ids = split['train16'][:1] if args.smoke else split['train16']
    assert len(split['train16']) == 16 and not set(ids) & set(split['val2']+split['historical_exposed_test6'])
    signature = p.binding(args.arm, args.smoke)
    out = p.output(args.arm, args.seed, smoke=args.smoke)
    out.mkdir(parents=True, exist_ok=True)
    full_steps = cfg['pretrained_steps']
    target = 1 if args.smoke else full_steps
    summary_path, ck = out/'summary.json', out/'last_train_state.pth'
    if summary_path.exists():
        done = p.read(summary_path)
        if done['signature'] != signature or done['global_step'] != target or p.sha(ck) != done['checkpoint_sha256']:
            raise RuntimeError('completed checkpoint binding changed')
        print('TRAIN REUSED', out, flush=True)
        return
    r02.set_seed(args.seed)
    state = torch.load(ck, map_location='cpu', weights_only=False) if ck.exists() else None
    if state and state['signature'] != signature:
        raise RuntimeError('resume binding mismatch; preserve original source/config')
    p.write(out/'run_metadata.json',dict(signature=signature,physical_gpu=os.environ['CUDA_VISIBLE_DEVICES'],
        target_step=target,train_tiles=ids,val2_loaded=False,test6_loaded=False))
    net = p.build(args.arm, base, r02.DEVICE, state)
    optcfg = dict(base, optimizer=cfg['pretrained_optimizer'], schedule=cfg['schedule'])
    optimizer = r02.build_optimizer(net, optcfg)
    if state:
        optimizer.load_state_dict(state['optimizer'])
        old.restore_rng(state)
    else:
        r02.set_seed(args.seed)
    start = int(state['global_step']) if state else 0
    counts = state['treatment_counts'] if state else {k:0 for k in cfg['treatment_probabilities']}
    cache, _ = r02.preload(Path(base['data_root']), ids, [])
    sampler = dict(base, micro_batch=1 if args.smoke else cfg['micro_batch'])
    accum = 1 if args.smoke else cfg['accum_steps']
    names, weights = list(cfg['treatment_probabilities']), list(cfg['treatment_probabilities'].values())
    net.train()
    started = time.time()
    for step in range(start+1, target+1):
        optimizer.zero_grad(set_to_none=True)
        r02.set_lr(optimizer, optcfg, step, full_steps)
        total = 0.
        for micro in range(accum):
            key = args.seed*1000000+step*100+micro
            op, ds, gt, _ = sample(cache, ids, sampler, key)
            kinds = random.Random(key+1).choices(names, weights=weights, k=len(op))
            for kind in kinds:
                counts[kind] += 1
            op2, aux2, available = p.training_transform(op, ds, args.arm, kinds, key,cfg['structured_mask'])
            aux = op.mean(1) if args.arm == 'P1' else ds
            clean = net(op, aux)
            loss = .5*old.deterministic_ce(clean, gt)
            if not torch.isfinite(loss):
                raise RuntimeError('nonfinite clean loss')
            total += float(loss.detach())/accum
            (loss/accum).backward()
            del loss, clean
            damaged = net(op2, aux2)
            loss = .5*old.deterministic_ce(damaged, gt)
            if not torch.isfinite(loss):
                raise RuntimeError('nonfinite perturbed loss')
            total += float(loss.detach())/accum
            (loss/accum).backward()
            del loss, damaged, op, ds, gt, op2, aux2, aux, available
        torch.nn.utils.clip_grad_norm_(net.parameters(), float('inf'), error_if_nonfinite=True)
        optimizer.step()
        if step == 1 or step % 20 == 0 or step == target:
            print(f'{args.arm} seed{args.seed} step={step}/{target} loss={total:.6f} elapsed={time.time()-started:.1f}s', flush=True)
        if step % cfg['checkpoint_every'] == 0 or step == target:
            save(ck, net, None, optimizer, step, signature, counts)
    # Bind a train-only clean inference probe to the exact saved final checkpoint.
    op, ds, _, _ = sample(cache, ids, dict(base, micro_batch=1), args.seed*1000000+999999)
    aux = op.mean(1) if args.arm == 'P1' else ds
    net.eval()
    with torch.no_grad():
        pred = net(op, aux).argmax(1).cpu()
    probe = out/'clean_probe.pth'
    torch.save(dict(rgb=op.cpu(), aux=aux.cpu(), pred=pred), probe)
    added_macs = None
    p.write(summary_path, dict(arm=args.arm, seed=args.seed, smoke=args.smoke, signature=signature,
        global_step=target, checkpoint_sha256=p.sha(ck), clean_probe_sha256=p.sha(probe),
        treatment_counts=counts, seconds_this_session=time.time()-started, train_tiles=ids,
        val2_loaded=False, test6_loaded=False, checkpoint_selection='fixed_final_step',
        total_parameters=sum(x.numel() for x in net.parameters()),
        added_module_conv_attention_MACs_per_patch=added_macs,
        MAC_estimate_exclusions='bias, gating elementwise ops, softmax and unchanged base network',
        trainable_parameters=sum(x.numel() for x in net.parameters() if x.requires_grad)))
    print('TRAIN COMPLETE', out, flush=True)


if __name__ == '__main__':
    main()
