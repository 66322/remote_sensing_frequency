"""Read-only inference diagnostics for four completed D16/D17 seed42 checkpoints."""
import argparse
import os
from pathlib import Path
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import numpy as np
import torch
import d18_d19_night as p
import d16_d17_portfolio as old
import train_rebuild_v1_r02_budget_pilot as r02
from night_boundary_metrics import boundary_counts


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--arm',choices=['A0','A2','B1','B2'],required=True)
    args=ap.parse_args()
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1:
        raise RuntimeError('one visible GPU required')
    run=old.output(args.arm,42)
    ck=run/'last_train_state.pth'
    train=p.read(run/'summary.json')
    expected=old.binding(args.arm,42,old.anchor_paths('R05',42)[0]/'best_model.pth',False)
    if train['signature']!=expected:
        raise RuntimeError('old source/config/anchor binding changed')
    signature=dict(checkpoint_sha256=p.sha(ck),config_sha256=p.sha(p.CONFIG),
        source_sha256=p.sha(Path(__file__)),old_signature=train['signature'])
    if train['checkpoint_sha256']!=signature['checkpoint_sha256'] or train['global_step']!=4000:
        raise RuntimeError('old checkpoint incomplete or changed')
    out=p.ROOT/'records/rebuild_v1_d18_d19_20260927'/f'LEGACY_{args.arm}_seed42'
    out.mkdir(parents=True,exist_ok=True)
    if (out/'summary.json').exists():
        if p.read(out/'summary.json')['signature']!=signature:
            raise RuntimeError('diagnostic binding mismatch')
        print('LEGACY DIAGNOSTICS REUSED',args.arm,flush=True)
        return
    cfg=p.read(p.CONFIG)
    base=p.read(p.base_config())
    split=p.read(p.ROOT/cfg['split_file'])
    assert not set(split['val2']) & set(split['historical_exposed_test6'])
    r02.set_seed(42)
    state=torch.load(ck,map_location='cpu',weights_only=False)
    if state['signature']!=train['signature']:
        raise RuntimeError('old state signature mismatch')
    net,_=r02.build_model(base,Path(base['pretrain']),resume_state=state)
    net.eval()
    rows={}
    for condition in ['clean']+cfg['diagnostics']:
        tiles={}
        for tile in split['val2']:
            item=r02.load_tile(Path(base['data_root']),tile,need_nb=True)
            op=torch.from_numpy(np.ascontiguousarray(item['optical'].transpose(2,0,1)))[None]
            ds=torch.from_numpy(np.ascontiguousarray(item['dsm']))[None]
            rgb,aux,_=p.transform(op,ds,'C0',[condition],torch.Generator().manual_seed(42))
            pred=r02.infer_tile(net,rgb[0].permute(1,2,0).numpy(),aux[0].numpy(),base['patch'],base['validation']['stride'],base['validation']['inference_batch'])
            cm=np.zeros((6,6),dtype=np.int64)
            r02.update_cm(cm,item['full_gt'],pred)
            tiles[tile]=dict(full_cm=cm.tolist(),boundaries=boundary_counts(item['full_gt'],pred,3))
            np.savez_compressed(out/f'{condition}_{tile}_prediction.npz',prediction=pred)
            print('LEGACY',args.arm,condition,tile,flush=True)
        rows[condition]=tiles
    p.write(out/'summary.json',dict(signature=signature,arm=args.arm,seed=42,conditions=rows,
        test6_loaded=False,val2_exploratory=True,diagnostic_only=True,
        does_not_reopen_failed_gate=True,boundary_tolerance_pixels=3))


if __name__=='__main__':
    main()
