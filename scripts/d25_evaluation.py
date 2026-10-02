"""Resume-safe Val2 evaluation; reuse bound D23 fixed-reference predictions."""
from pathlib import Path
import time
import numpy as np
import torch
import d23_engine as e
from d23_lifecycle import pool
from d25_treatments import treatment, EXTRA
from d25_common import read, write, sha, within, now


def infer(model, item, available, progress=lambda **kw: None, batch=8):
    optical, dsm = item['optical'], item['dsm']
    h, w = dsm.shape
    patch, stride = 512, 256
    coords = [(y,x) for y in e.positions(h,patch,stride) for x in e.positions(w,patch,stride)]
    scores = np.zeros((2,6,h,w), np.float32)
    coverage = np.zeros((h,w), np.uint16)
    last = time.monotonic()
    with torch.inference_mode():
        for start in range(0,len(coords),batch):
            cs = coords[start:start+batch]
            op = torch.from_numpy(np.stack([optical[y:y+patch,x:x+patch].transpose(2,0,1) for y,x in cs])).cuda()
            ds = torch.from_numpy(np.stack([dsm[y:y+patch,x:x+patch] for y,x in cs])).cuda()
            mask = torch.from_numpy(np.stack([available[y:y+patch,x:x+patch] for y,x in cs])).cuda()
            real = len(cs)
            if real < batch:
                op = torch.cat((op,op[-1:].expand(batch-real,-1,-1,-1)))
                ds = torch.cat((ds,ds[-1:].expand(batch-real,-1,-1)))
                mask = torch.cat((mask,mask[-1:].expand(batch-real,-1,-1)))
            fused, own, _, _ = model(op,ds,mask,return_parts=True)
            for target, logits in zip(scores, (fused, own)):
                values = logits[:real].float().cpu().numpy()
                for z,(y,x) in zip(values,cs):
                    target[:,y:y+patch,x:x+patch] += z
            for y,x in cs:
                coverage[y:y+patch,x:x+patch] += 1
            del op,ds,mask,fused,own,values
            if time.monotonic() - last >= 30 or start + batch >= len(coords):
                progress(windows_done=min(start+batch,len(coords)),windows_total=len(coords))
                last = time.monotonic()
    if not coverage.all() or not np.isfinite(scores).all():
        raise RuntimeError('bad stitched logits/coverage')
    equal = np.array_equal(scores[0][:,~available],scores[1][:,~available])
    if not equal:
        raise RuntimeError('missing logits differ from own optical branch')
    return scores.argmax(1).astype(np.uint8), equal


class BoundOldReferences:
    def __init__(self, root, plan):
        self.root, self.plan = Path(root), plan
        self.base = self.root / 'records/research_d23_b_formal_20261001T152548_658274'
        state = read(self.base / 'queue_status.json')
        row = state['jobs']['T0']
        if row['status'] != 'COMPLETE':
            raise RuntimeError('bound D23 T0 reference job not complete')
        self.job = within(row.get('job_directory', self.base/'jobs/T0'), self.base)
        self.manifest = sha(self.root/'records/rebuild_v1_d21_queue_20260928/input_manifest.json')

    def prediction(self, name, tile, condition):
        path = self.job/'evaluation'/condition/name/(tile+'.npy')
        row = read(path.with_suffix('.json'))
        signature = row['signature']['training']
        expected = {x['arm']:x['sha256'] for x in signature['experts']}
        if (expected != {'R0': self.plan['initialization']['R0_sha256'], 'M0': self.plan['initialization']['M0_sha256']}
            or signature['input_manifest_sha256'] != self.manifest or row['tile'] != tile
            or row['condition'] != condition or sha(path) != row['prediction_sha256']):
            raise RuntimeError('fixed prediction binding mismatch: '+str(path))
        return np.load(path), dict(path=str(path),sha256=row['prediction_sha256'],source='completed D23 fixed expert prediction')


class FixedView(torch.nn.Module):
    def __init__(self, models):
        super().__init__()
        self.models=torch.nn.ModuleDict(models)
    def forward(self,op,ds,mask,return_parts=False):
        z0=self.models['R0'](op,ds)
        z1=self.models['M0'](op,ds)
        safe=torch.where(mask[:,None],z1,z0)
        return (safe,z0,None,None)

class References(BoundOldReferences):
    def __init__(self,root,plan,base,factory):
        super().__init__(root,plan)
        self.cache=Path(base)/'shared_reference'
        self.factory=factory
        self.models=None
        self.binding=dict(plan_sha256=sha(Path(base)/'plan.json'),
                          sources=read(Path(base)/'code_manifest.json'),
                          input_manifest_sha256=self.manifest,
                          R0_sha256=plan['initialization']['R0_sha256'],
                          M0_sha256=plan['initialization']['M0_sha256'])

    def prediction(self,name,tile,condition):
        if condition not in EXTRA:
            return super().prediction(name,tile,condition)
        folder=self.cache/condition/tile
        folder.mkdir(parents=True,exist_ok=True)
        # One writer across GPUs; never overwrite a bound completed prediction.
        import fcntl
        with (folder/'writer.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            record=folder/'complete.json'
            if not record.exists():
                loader=__import__('d24_data').Loader(self.root,self.plan)
                item=loader(tile,validation=True)
                op=torch.from_numpy(np.ascontiguousarray(item['optical'].transpose(2,0,1)))[None]
                ds=torch.from_numpy(np.ascontiguousarray(item['dsm']))[None]
                seed=42+sum(map(ord,tile))
                treated,aux,mask=treatment(op,ds,condition,seed)
                view=dict(optical=np.ascontiguousarray(treated[0].permute(1,2,0).numpy()),dsm=aux[0].numpy())
                if self.models is None:
                    self.models=FixedView(self.factory()).eval()
                predictions,_=infer(self.models,view,mask[0].numpy())
                hashes={}
                for arm,pred in (('R0',predictions[1]),('M0_safe',predictions[0])):
                    path=folder/(arm+'.npy')
                    temporary=path.with_suffix('.tmp')
                    with temporary.open('wb') as f:np.save(f,pred)
                    temporary.replace(path)
                    hashes[arm]=sha(path)
                write(record,dict(binding=self.binding,tile=tile,condition=condition,
                                  predictions=hashes,input_files=loader.verified,
                                  observed_at=now(),test6_loaded=False))
            row=read(record)
            path=folder/(name+'.npy')
            if row['binding']!=self.binding or row['tile']!=tile or row['condition']!=condition or sha(path)!=row['predictions'][name]:
                raise RuntimeError('extra reference binding mismatch')
            return np.load(path),dict(path=str(path),sha256=row['predictions'][name],
                                     source='D25 frozen D21 expert pressure-reference inference')


def select_validation(model, loader, plan, out, signature, step, progress):
    out = Path(out)
    target = out/'validation'/('step_%04d.json'%step)
    if target.exists():
        row = read(target)
        if row['signature'] != signature:
            raise RuntimeError('validation binding mismatch')
        return row
    rows = {}
    for tile in plan['data']['validation']:
        progress(phase='checkpoint_selection', step=step, tile=tile, condition='clean')
        item = loader(tile,validation=True)
        available = np.ones(item['dsm'].shape,bool)
        pred,_ = infer(model,item,available,progress=lambda **kw:progress(phase='checkpoint_selection',step=step,tile=tile,condition='clean',**kw))
        rows[tile] = e.count_result(item['noboundary_gt'],pred[0],pred[1],available)
        del item,pred
    result = dict(signature=signature,step=step,tiles=rows,pooled=pool(list(rows.values())),
                  observed_at=now(),test6_loaded=False)
    write(target,result)
    return result


def evaluate(model, loader, refs, plan, out, signature, progress):
    out = Path(out)/'evaluation'
    tiles = {}
    for tile in plan['data']['validation']:
        item = loader(tile,validation=True)
        op = torch.from_numpy(np.ascontiguousarray(item['optical'].transpose(2,0,1)))[None]
        ds = torch.from_numpy(np.ascontiguousarray(item['dsm']))[None]
        for condition in plan['evaluation']['conditions']:
            record = out/condition/(tile+'.json')
            if record.exists():
                row = read(record)
                if row['signature'] != signature:
                    raise RuntimeError('evaluation resume binding mismatch')
                for name,value in row['predictions'].items():
                    if sha(out/condition/name/(tile+'.npy')) != value:
                        raise RuntimeError('saved prediction checksum mismatch')
                tiles.setdefault(condition,{})[tile] = row
                continue
            progress(phase='full_evaluation',tile=tile,condition=condition)
            seed = e.key(42,'potsdam',tile,condition) if condition=='aux_noise_std020' else 42+sum(map(ord,tile))
            treated,aux,mask = treatment(op,ds,condition,seed,numpy_noise=condition=='aux_noise_std020')
            available = mask[0].numpy()
            view = dict(optical=np.ascontiguousarray(treated[0].permute(1,2,0).numpy()),dsm=aux[0].numpy())
            reuse=model.optical_only and condition.startswith('aux_')
            if reuse:
                # DSM-only changes cannot change this explicitly optical-only graph.
                # Keep all 14-condition count records without redundant GPU inference.
                predictions=np.stack([np.load(out/'clean'/name/(tile+'.npy'))
                                      for name in ('candidate','own_optical')])
                equal=True
                progress(phase='full_evaluation_reused_optical',tile=tile,condition=condition)
            else:
                predictions,equal = infer(model,view,available,progress=lambda **kw:progress(phase='full_evaluation',tile=tile,condition=condition,**kw))
            fixed, provenance = {}, {}
            for name in ('R0','M0_safe'):
                fixed[name],provenance[name] = refs.prediction(name,tile,condition)
                if fixed[name].shape != available.shape:
                    raise RuntimeError('reference shape mismatch')
            results, hashes = {}, {}
            for name,pred in (('candidate',predictions[0]),('own_optical',predictions[1])):
                path = out/condition/name/(tile+'.npy')
                path.parent.mkdir(parents=True,exist_ok=True)
                tmp = path.with_suffix('.tmp')
                with tmp.open('wb') as f:
                    np.save(f,pred)
                tmp.replace(path)
                hashes[name] = sha(path)
                results[name] = {scope:e.count_result(item[scope+'_gt'],pred,fixed['R0'],available)
                                 for scope in ('full','noboundary')}
            for name,pred in fixed.items():
                results[name] = {scope:e.count_result(item[scope+'_gt'],pred,fixed['R0'],available)
                                 for scope in ('full','noboundary')}
            own_risk = {scope:e.count_result(item[scope+'_gt'],predictions[0],predictions[1],available)
                        for scope in ('full','noboundary')}
            row = dict(signature=signature,tile=tile,condition=condition,results=results,
                       own_optical_reference=own_risk,predictions=hashes,fixed_reference_files=provenance,
                       missing_logits_equal_own_optical=equal,optical_inference_reused_from_clean=reuse,observed_at=now())
            write(record,row)
            tiles.setdefault(condition,{})[tile] = row
            print('D25_EVAL',tile,condition,flush=True)
            del treated,aux,mask,view,predictions,fixed,available
        del op,ds,item
    pooled = {condition:{name:{scope:pool([row['results'][name][scope] for row in rows.values()])
                               for scope in ('full','noboundary')}
                         for name in ('candidate','own_optical','R0','M0_safe')}
              for condition,rows in tiles.items()}
    own = {condition:{scope:pool([row['own_optical_reference'][scope] for row in rows.values()])
                      for scope in ('full','noboundary')} for condition,rows in tiles.items()}
    summary = dict(signature=signature,tiles=tiles,pooled=pooled,pooled_own_optical_reference=own,
                   test6_loaded=False,independent_final_loaded=False,
                   primary_scope='noboundary',primary_metric='mIoU_fg5',confusion_matrix_dtype='int64',observed_at=now())
    write(out/'summary.json',summary)
    return summary
