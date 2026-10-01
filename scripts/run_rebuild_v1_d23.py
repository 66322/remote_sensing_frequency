"""D23 engine admission: bounded engineering smoke/profile; formal mode locked."""
import argparse
from datetime import datetime
import gc
import importlib.util
import json
import os
from pathlib import Path
import sys
import time


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--gpu',type=int,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--mode',choices=('smoke','profile','budget','formal'),required=True)
    ap.add_argument('--arm',default='TSF')
    ap.add_argument('--runtime-lock',type=Path)
    ap.add_argument('--resume',action='store_true')
    args=ap.parse_args();root=args.root.resolve();out=args.output.resolve()
    scope=Path('/home/jovyan/zzx').resolve();root.relative_to(scope);out.relative_to(root/'records')
    if out.exists() and not (args.mode=='formal' and args.resume):raise RuntimeError('refuse existing output directory')
    out.mkdir(parents=True,exist_ok=True)
    import probe_rebuild_v1_d23_gate as probe
    write,read,sha=probe.write,probe.read,probe.sha
    began=time.monotonic()
    formal_started=False
    try:
        lock=None
        if args.mode=='formal':
            if args.runtime_lock is None:raise RuntimeError('formal requires measured runtime lock; queue not admitted yet')
            args.runtime_lock.resolve().relative_to(root/'records')
            lock=read(args.runtime_lock)
            if lock.get('status')!='FULL_ENGINE_RUNTIME_ADMITTED' or lock.get('expert_micro_batch')!=8 or lock.get('gate_batch')!=16 or lock.get('backward_calls_per_step')!=1:
                raise RuntimeError('runtime lock not admitted for this batch execution')
            for name in ('job_wall_seconds','host_rss_bytes','gpu_allocated_bytes','gpu_reserved_bytes','job_disk_bytes'):
                if not isinstance(lock.get(name),(int,float)) or lock[name]<=0:raise RuntimeError('runtime budget absent '+name)
            for name in ('d23_engine.py','d23_lifecycle.py','run_rebuild_v1_d23.py','probe_rebuild_v1_d23_gate.py'):
                if lock.get('source_sha256',{}).get(name)!=sha(Path(__file__).parent/name):raise RuntimeError('runtime source binding mismatch')
        inv=probe.gpu_inventory();gpu=inv[args.gpu];probe.require_idle(gpu);probe.reject_existing_compute(gpu['uuid'])
        os.environ['CUDA_VISIBLE_DEVICES']=gpu['uuid'];os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8';os.environ['XFORMERS_DISABLED']='1'
        import resource
        import numpy as np
        from PIL import Image
        import torch
        sys.path.insert(0,str(root))
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
        import d23_engine as e
        gate_path=Path(__file__).resolve().parents[1]/'model/rebuild_v1_d23_gate.py'
        spec=importlib.util.spec_from_file_location('d23_gate_execution',gate_path)
        g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
        from model.rebuild_v1_night_screen import load_dino
        from model.rebuild_v1_d21_detail import DetailDinoSegmenter
        if torch.cuda.device_count()!=1:raise RuntimeError('one visible GPU required')
        torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
        torch.manual_seed(42);torch.cuda.manual_seed_all(42)
        def guard():
            caps=lock or dict(job_wall_seconds=1800,host_rss_bytes=(64 if args.mode=='budget' else 24)*1024**3,gpu_allocated_bytes=32*1024**3,gpu_reserved_bytes=40*1024**3,job_disk_bytes=32*1024**3)
            if time.monotonic()-began>caps['job_wall_seconds']:raise RuntimeError('wall limit')
            if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>caps['host_rss_bytes']:raise RuntimeError('host RSS limit')
            if torch.cuda.max_memory_allocated()>caps['gpu_allocated_bytes'] or torch.cuda.max_memory_reserved()>caps['gpu_reserved_bytes']:
                raise RuntimeError('engineering allocated/reserved GPU limit')
            if sum(p.stat().st_size for p in out.rglob('*') if p.is_file())>caps['job_disk_bytes']:raise RuntimeError('job disk limit')
        base=read(root/'configs/rebuild_v1/r05_quality_plus_dropout_16k.json')
        split=read(root/base['split_file']);fit,held=e.partition(split)
        dino=read(root/'configs/rebuild_v1/d18_d19_night_20260927.json')['dino']
        repo=(root/dino['repository_dir']).resolve();weights=(root/dino['weights_path']).resolve()
        repo.relative_to(scope);weights.relative_to(scope)
        commit=probe.subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
        probe.subprocess.run(['git','diff','--exit-code','HEAD','--','dinov2','hubconf.py'],cwd=repo,check=True)
        experts={};bindings=[]
        for arm,expected in probe.EXPECTED.items():
            run=root/'runs/rebuild_v1'/('D21_potsdam_'+arm+'_seed42_16000_20260928')
            row=read(run/'summary.json');ck=run/'last_train_state.pth';sig=row['signature']
            if row['job']!={'dataset':'potsdam','arm':arm,'seed':42} or row['global_step']!=16000 or row['test6_loaded'] is not False:
                raise RuntimeError('expert identity mismatch')
            if row['checkpoint_sha256']!=expected or sha(ck)!=expected:raise RuntimeError('expert bytes mismatch')
            for name in ('model/rebuild_v1_d21_detail.py','model/rebuild_v1_night_screen.py','configs/rebuild_v1/r05_quality_plus_dropout_16k.json',base['split_file']):
                if sha(root/name)!=sig['source_sha256'].get(name):raise RuntimeError('D21 source changed '+name)
            if sig['dino_commit']!=commit or sig['dino_sha256']!=sha(weights) or sig['torch_version']!=torch.__version__:
                raise RuntimeError('DINO or torch binding mismatch')
            state=torch.load(ck,map_location='cpu',weights_only=False)
            if state['signature']!=sig:raise RuntimeError('checkpoint signature mismatch')
            net=DetailDinoSegmenter(load_dino(repo,weights),arm).cuda().eval();net.load_state_dict(state['model'],strict=True)
            del state
            saved_path=run/'clean_probe.pth'
            if sha(saved_path)!=row['clean_probe_sha256']:raise RuntimeError('saved training probe hash mismatch')
            saved=torch.load(saved_path,map_location='cpu',weights_only=False)
            with torch.no_grad():pred=net(saved['rgb'].cuda(),saved['aux'].cuda()).argmax(1).cpu()
            if not torch.equal(pred,saved['pred']):raise RuntimeError('saved D21 prediction changed')
            experts[arm]=net;bindings.append(dict(arm=arm,sha256=expected,saved_probe_reproduced=True));del saved,pred
        pair=g.FrozenExpertPair(experts['R0'],experts['M0'])
        manifest=read(root/'records/rebuild_v1_d21_queue_20260928/input_manifest.json')
        input_rows={r['path']:r for r in manifest['files']}
        data=Path(base['data_root']).resolve();data.relative_to(scope)
        verified_cache={}
        def load(tile,need_nb=False):
            permitted=split['val2'] if need_nb and args.mode=='formal' else fit
            if tile not in permitted:raise RuntimeError('tile outside gate-fit/development phase')
            cache_root=out/'normalized_fit_cache'/tile
            if args.mode in ('formal','budget') and not need_nb and tile in verified_cache:
                return {name:np.load(cache_root/(name+'.npy'),mmap_mode='r') for name in ('optical','dsm','full_gt')}
            a,b=map(int,tile.split('_'))
            paths={'optical':data/'2_Ortho_RGB'/('top_potsdam_'+tile+'_RGB.tif'),
                   'dsm':data/'1_DSM/1_DSM'/('dsm_potsdam_%02d_%02d.tif'%(a,b)),
                   'full_gt':data/'5_Labels_for_participants'/('top_potsdam_'+tile+'_label.tif')}
            if need_nb:paths['noboundary_gt']=data/'5_Labels_for_participants_no_Boundary'/('top_potsdam_'+tile+'_label_noBoundary.tif')
            arrays={}
            for name,path in paths.items():
                if str(path) not in input_rows or sha(path)!=input_rows[str(path)]['sha256']:raise RuntimeError('training data binding mismatch')
                with Image.open(path) as im:arrays[name]=np.array(im if name=='dsm' else im.convert('RGB'))
            rgb=arrays['optical'].astype(np.float32)/255;ds=arrays['dsm'].astype(np.float32)
            if not np.isfinite(ds).all() or ds.max()<=ds.min():raise RuntimeError('bad DSM')
            ds=(ds-ds.min())/(ds.max()-ds.min())
            colors=((255,255,255),(0,0,255),(0,255,255),(0,255,0),(255,255,0),(255,0,0))
            gt=np.full(ds.shape,255,np.uint8)
            for c,color in enumerate(colors):gt[np.all(arrays['full_gt']==color,axis=-1)]=c
            if (gt==255).any() or rgb.shape[:2]!=ds.shape:raise RuntimeError('bad training labels/shape')
            result=dict(optical=rgb,dsm=ds,full_gt=gt)
            if need_nb:
                nb=np.full(ds.shape,255,np.uint8);recognized=np.all(arrays['noboundary_gt']==0,axis=-1)
                for c,color in enumerate(colors):
                    region=np.all(arrays['noboundary_gt']==color,axis=-1);nb[region]=c;recognized|=region
                if not recognized.all():raise RuntimeError('unknown NoBoundary color')
                result['noboundary_gt']=nb
            if args.mode in ('formal','budget') and not need_nb:
                cache_root.mkdir(parents=True,exist_ok=True)
                meta=cache_root/'binding.json'
                source={name:sha(path) for name,path in paths.items()}
                if meta.exists():
                    cached=read(meta)
                    if cached['source']!=source:raise RuntimeError('normalized cache source binding mismatch')
                    for name,value in cached['arrays'].items():
                        if sha(cache_root/(name+'.npy'))!=value:raise RuntimeError('normalized cache bytes changed')
                else:
                    for name,value in result.items():
                        path=cache_root/(name+'.npy')
                        if path.exists():raise RuntimeError('partial normalized cache retained; new run required')
                        np.save(path,value)
                    write(meta,dict(source=source,arrays={name:sha(cache_root/(name+'.npy')) for name in result}))
                verified_cache[tile]=True
                result={name:np.load(cache_root/(name+'.npy'),mmap_mode='r') for name in result}
            return result
        tile='2_12';initial_load_started=time.monotonic();cache=e.TileCache(load,[tile]);item=cache.get(tile)
        initial_load_seconds=time.monotonic()-initial_load_started
        signature=dict(experts=bindings,sources={p.name:sha(p) for p in (Path(__file__),Path(e.__file__),Path(g.__file__),Path(probe.__file__),Path(__file__).parent/'d23_lifecycle.py')},
          base_sha256=sha(root/'configs/rebuild_v1/r05_quality_plus_dropout_16k.json'),split_sha256=sha(root/base['split_file']),
          input_manifest_sha256=sha(root/'records/rebuild_v1_d21_queue_20260928/input_manifest.json'),
          torch_version=torch.__version__,matmul_allow_tf32=torch.backends.cuda.matmul.allow_tf32,cudnn_allow_tf32=torch.backends.cudnn.allow_tf32,
          gpu=args.gpu,uuid=gpu['uuid'],expert_micro_batch=8,gate_batch=16,backward_calls_per_step=1,
          gpu_name=torch.cuda.get_device_properties(0).name,gpu_total_memory_bytes=torch.cuda.get_device_properties(0).total_memory,
          gate_trainable_parameters=18145,gate_convolution_macs_per_512_crop=296222720,
          test6_loaded=False,development_labels_loaded=args.mode=='formal',formal_training_started=args.mode=='formal')
        if args.mode=='formal':
            import d23_lifecycle as life
            if args.arm not in g.ARMS:raise ValueError(args.arm)
            if lock.get('gate_source_sha256')!=sha(Path(g.__file__)) or lock.get('matmul_allow_tf32')!=signature['matmul_allow_tf32'] or lock.get('cudnn_allow_tf32')!=signature['cudnn_allow_tf32']:
                raise RuntimeError('runtime gate/backend binding mismatch')
            signature.update(arm=args.arm,runtime_lock_sha256=sha(args.runtime_lock),checkpoint_selection='fixed_final_step_protocol_exception',
                train_fit_ids=fit,held_train_diagnostic_ids=held,formal_stats_samples=256)
            if (out/'preflight.json').exists():
                if read(out/'preflight.json')!=signature:raise RuntimeError('existing formal signature differs')
            else:write(out/'preflight.json',signature)
            cache=e.TileCache(load,fit)
            stats_path=out/'formal_fit_statistics.json'
            if stats_path.exists():
                stats=read(stats_path)
                if stats['signature']!=signature:raise RuntimeError('fit statistics binding changed')
            else:
                moments=e.Moments()
                for i in range(256):
                    spec=e.sample_spec(fit,e.key(42,'formal_stats',i),base['augmentation'])
                    spec['tile']=fit[i%len(fit)]
                    clean_op,clean_ds,_,treated=e.materialize(cache,spec)
                    # Accumulate at canonical expert batch8; label never enters moments.
                    if i%8==0:stats_samples=[]
                    stats_samples.append((clean_op,clean_ds,treated))
                    if i%8==7:
                        for view in (0,1):
                            op=torch.stack([s[0] if view==0 else s[2][0] for s in stats_samples]).cuda()
                            ds=torch.stack([s[1] if view==0 else s[2][1] for s in stats_samples]).cuda()
                            inp=pair(op,ds);moments.add(inp['E']);del inp
                        guard()
                stats=moments.result();stats.update(signature=signature,formal_fit_statistics=True,fit_tiles=fit)
                write(stats_path,stats)
            torch.manual_seed(42);gate=g.DenseBenefitGate(args.arm).cuda()
            if args.arm=='TCAP':gate.set_fit_statistics(stats['mean'],stats['std'])
            formal_started=True
            info=life.train(pair,gate,cache,fit,base['augmentation'],out/'training',signature,g,probe,guard,args.resume)
            signature_eval=dict(training=signature,checkpoint_sha256=info['checkpoint_sha256'],fit_statistics_sha256=sha(stats_path))
            # Evaluation is deliberately not implicitly resumed or overwritten.
            result=life.evaluate(pair,{args.arm:gate},load,split['val2'],out/'evaluation',signature_eval,g,probe,guard)
            for arm,expected in probe.EXPECTED.items():
                if sha(root/'runs/rebuild_v1'/('D21_potsdam_'+arm+'_seed42_16000_20260928')/'last_train_state.pth')!=expected:raise RuntimeError('expert bytes changed')
            write(out/'formal_complete.json',dict(observed_at=datetime.now().astimezone().isoformat(),signature=signature_eval,
              formal_training_started=True,global_step=4000,test6_loaded=False,independent_final_loaded=False))
            print('D23_FORMAL_JOB_COMPLETE',args.arm,flush=True)
            return 0
        write(out/'preflight.json',signature)
        cache_measurement={};cache_seconds=initial_load_seconds
        if args.mode=='budget':
            # Measure the exact formal disk-cache loader and its mmap reopen path.
            cache=e.TileCache(load,fit)
            for fit_tile in fit:
                started=time.monotonic();value=cache.get(fit_tile);guard()
                cache_measurement[fit_tile]=dict(seconds=time.monotonic()-started,
                    bytes=sum(v.nbytes for v in value.values()),shape=list(value['dsm'].shape))
                del value
            cache_seconds+=sum(v['seconds'] for v in cache_measurement.values())
            write(out/'cache_measurement.json',dict(tiles=cache_measurement,seconds=cache_seconds,
                initial_tile_load_seconds=initial_load_seconds,initial_tile=tile,
                formal_cache_format=True,test6_loaded=False))
        statistics_started=time.monotonic()
        if args.mode=='budget':
            moments=e.Moments()
            for i in range(256):
                spec=e.sample_spec(fit,e.key(42,'formal_stats',i),base['augmentation'])
                spec['tile']=fit[i%len(fit)]
                clean_op,clean_ds,_,treated=e.materialize(cache,spec)
                if i%8==0:stats_samples=[]
                stats_samples.append((clean_op,clean_ds,treated))
                if i%8==7:
                    for view in (0,1):
                        op=torch.stack([v[0] if view==0 else v[2][0] for v in stats_samples]).cuda()
                        ds=torch.stack([v[1] if view==0 else v[2][1] for v in stats_samples]).cuda()
                        inp=pair(op,ds);moments.add(inp['E']);del inp,op,ds
                    guard()
            stats=moments.result()
            stats.update(scope='BUDGET_ONLY_12_FIT_TILES_256_SAMPLES',fit_tiles=fit,
                samples=256,formal_fit_statistics=False)
            write(out/'budget_fit_statistics.json',stats)
        else:
            # Formal TCAP statistics must use all 12 gate-fit tiles, not this smoke file.
            moments=e.Moments()
            for step in range(2):
                clean,treated,labels=e.logical_batch(cache,[tile],step,base['augmentation'],stream='stats_admission')
                for view in (clean,treated):
                    for sl in e.slices(16,8):
                        inp=pair(view[0][sl].cuda(),view[1][sl].cuda());moments.add(inp['E']);del inp
                guard()
            stats=moments.result();stats.update(scope='ADMISSION_ONLY_TRAIN_TILE_2_12',formal_fit_statistics=False)
            write(out/'admission_fit_statistics.json',stats)

        statistics_seconds=time.monotonic()-statistics_started
        train_rows={};selected=g.ARMS if args.mode in ('smoke','budget') else ('TSF',)
        for arm in selected:
            torch.manual_seed(42);gate=g.DenseBenefitGate(arm).cuda()
            if arm=='TCAP':gate.set_fit_statistics(stats['mean'],stats['std'])
            optimizer=torch.optim.AdamW(gate.parameters(),lr=3e-4,weight_decay=.01)
            torch.cuda.reset_peak_memory_stats();times=[]
            for step in range(16 if args.mode=='budget' else (2 if args.mode=='smoke' else 12)):
                torch.cuda.synchronize();started=time.monotonic()
                logical=e.logical_batch(cache,fit if args.mode=='budget' else [tile],step,base['augmentation'])
                value,counts=e.fit_update(pair,gate,optimizer,logical,g.loss_sums,combine=g.combine_loss_sums)
                torch.cuda.synchronize();times.append(time.monotonic()-started);guard()
            # Check saved gate state reload independently of the original instance.
            saved=out/(arm+'_admission_state.pth');torch.save(dict(model=gate.state_dict(),signature=signature,arm=arm),saved)
            clone=g.DenseBenefitGate(arm).cuda();clone.load_state_dict(torch.load(saved,map_location='cpu',weights_only=False)['model'],strict=True)
            inp=pair(logical[0][0][:8].cuda(),logical[0][1][:8].cuda());mask=logical[0][2][:8].cuda()
            with torch.no_grad():
                z=gate(inp['E'],inp['S'],inp['F'],inp['z0'],inp['z1'],mask)['logits']
                z2=clone(inp['E'],inp['S'],inp['F'],inp['z0'],inp['z1'],mask)['logits']
            if not torch.equal(z,z2):raise RuntimeError('gate reload logits changed')
            train_rows[arm]=dict(loss=value,utility_counts=counts,step_seconds=times,
              gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated(),gpu_peak_reserved_bytes=torch.cuda.max_memory_reserved(),
              checkpoint_sha256=sha(saved),checkpoint_reload_equal=True,train_steps=len(times))
            write(out/(arm+'_training.json'),train_rows[arm]);print('D23_ENGINE_TRAIN_ADMISSION',arm,flush=True)
            del clone,inp,z,z2,optimizer,logical;gc.collect()
            if args.mode in ('smoke','budget'):del gate
        # Profile uses full 6000x6000 training tile; smoke uses >patch image with tail.
        if args.mode=='smoke':
            gate=g.DenseBenefitGate('TSF').cuda()
            eval_item={name:value[:768,:768] for name,value in item.items()}
            kinds=e.CONDITIONS
        elif args.mode=='budget':
            gate=g.DenseBenefitGate('TSF').cuda()
            gate.load_state_dict(torch.load(out/'TSF_admission_state.pth',map_location='cpu',weights_only=False)['model'],strict=True)
            eval_item=item;kinds=e.CONDITIONS
        else:eval_item=item;kinds=('clean','aux_zero','aux_local_zero_stripe_eighth')
        evaluations={}
        op=torch.from_numpy(np.ascontiguousarray(eval_item['optical'].transpose(2,0,1)))[None]
        ds=torch.from_numpy(np.ascontiguousarray(eval_item['dsm']))[None]
        for condition in kinds:
            seed=e.key(42,'potsdam',tile,condition) if condition in ('aux_noise_std020',) else 42+sum(map(ord,tile))
            treated,aux,mask=e.treatment(op,ds,condition,seed,numpy_noise=condition=='aux_noise_std020')
            optical=np.ascontiguousarray(treated[0].permute(1,2,0).numpy());secondary=aux[0].numpy();available=mask[0].numpy()
            models={name:None for name in e.FIXED} if args.mode in ('smoke','budget') else {'R0':None,'M0_safe':None}
            models['TSF']=gate;started=time.monotonic()
            scores=e.infer(pair,models,optical,secondary,available,g.fixed_blend,guard=guard)
            ref=scores['R0'].argmax(0).astype(np.uint8);rows={}
            for name,score in scores.items():
                pred=score.argmax(0).astype(np.uint8)
                path=out/(condition+'_'+name+'.npy');np.save(path,pred)
                rows[name]=dict(full=e.count_result(eval_item['full_gt'],pred,ref,available),prediction_sha256=sha(path),
                  missing_logits_equal=np.array_equal(score[:,~available],scores['R0'][:,~available]))
            evaluations[condition]=dict(seconds=time.monotonic()-started,shape=list(ref.shape),results=rows)
            if condition.startswith('aux_') and rows['R0']['prediction_sha256']!=evaluations['clean']['results']['R0']['prediction_sha256']:
                raise RuntimeError('R0 auxiliary invariance failed')
            write(out/(condition+'_evaluation.json'),evaluations[condition]);print('D23_ENGINE_EVAL_ADMISSION',condition,flush=True)
            del scores,treated,aux,mask;gc.collect();guard()
        for arm,expected in probe.EXPECTED.items():
            if sha(root/'runs/rebuild_v1'/('D21_potsdam_'+arm+'_seed42_16000_20260928')/'last_train_state.pth')!=expected:
                raise RuntimeError('expert file changed during run')
        write(out/'summary.json',dict(status='ENGINE_BUDGET_COMPLETE' if args.mode=='budget' else 'ENGINE_ADMISSION_COMPLETE',mode=args.mode,signature=signature,
          observed_at=datetime.now().astimezone().isoformat(),train=train_rows,evaluation=evaluations,
          rss_peak_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,elapsed_seconds=time.monotonic()-began,
          gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated(),gpu_peak_reserved_bytes=torch.cuda.max_memory_reserved(),
          formal_training_started=False,formal_fit_statistics=False,
          cache_measurement=cache_measurement,cache_seconds=cache_seconds,statistics_seconds=statistics_seconds,
          timing_scope='logical_batch_cpu_io_plus_cuda_step',
          budget_statistics_samples=256 if args.mode=='budget' else 32,
          train_fit_ids=fit if args.mode=='budget' else [tile],
          remaining=['server full-engine admission','formal 12-tile TCAP/data-cache measurement',
                     'server eight-arm screen binding verification','dual concurrency/runtime budget lock']))
        print('D23_ENGINE_ADMISSION_COMPLETE',str(out),flush=True)
        return 0
    except Exception as exc:
        failure=out/('failure_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.json')
        write(failure,dict(status='ENGINE_TECHNICAL_FAILURE',observed_at=datetime.now().astimezone().isoformat(),error=str(exc),formal_training_started=formal_started))
        print('D23_ENGINE_FAILURE',str(exc),file=sys.stderr,flush=True)
        return 2


if __name__=='__main__':sys.exit(main())
