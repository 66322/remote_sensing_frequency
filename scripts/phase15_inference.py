"""Exact original model graphs and FP32 native512/micro8 logit stitching."""
import os
from pathlib import Path
import sys
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
os.environ.setdefault('XFORMERS_DISABLED', '1')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from phase15_common import *
from phase15_numeric import *
from prepare_phase15 import load_mask, old_prediction, checked_array


def environment(base, gpu):
    p = validate(base)
    verify_code(base)
    if torch.__version__ != '2.2.2+cu121' or os.environ.get('CUDA_VISIBLE_DEVICES') != str(gpu):
        raise RuntimeError('Torch/physical GPU binding differs')
    prep = read(Path(base) / 'preparation_complete.json')
    if prep['plan_sha256'] != sha(Path(base)/'plan.json') or prep['code_sha256'] != sha(Path(base)/'code_manifest.json'):
        raise RuntimeError('preparation binding differs')
    for name, digest in prep['files'].items():
        if sha(Path(base)/name) != digest:
            raise RuntimeError('prepared receipt changed')
    from post_n2_diag_runtime import input_contract
    input_contract(Path(p['root']), read(Path(base)/'source_plan.json'))
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    torch.set_grad_enabled(False)
    def forbidden(*args, **kwargs):
        raise RuntimeError('zero-training guard: optimizer/backward/checkpoint write forbidden')
    torch.optim.Optimizer.__init__ = forbidden
    torch.Tensor.backward = forbidden
    torch.autograd.backward = forbidden
    torch.save = forbidden
    return p


def fingerprint(model):
    import hashlib
    h = hashlib.sha256()
    for name, value in model.state_dict().items():
        h.update(name.encode())
        h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def make_model(base, name):
    from model.rebuild_v1_d26 import build_experts
    from model.rebuild_v1_post_ab_n1 import N1Segmenter
    from model.post_s1_transfer_model import checkpoint
    from model.post_n5_cross_paths import CrossPaths
    from model.post_t_paired_v2 import PairedAdaptation
    from run_post_s1_transfer import load_anchors, seed_all
    from post_d30_evaluation import FixedPair
    source = read(Path(base)/'source_plan.json')
    root = Path(read(Path(base)/'plan.json')['root'])
    seed_all()
    states, provenance = load_anchors(root, source)
    r, d = build_experts(root, states)
    manifest = read(Path(base)/'checkpoint_manifest.json')['experts']
    row = manifest[name]
    if sha(row['path']) != row['sha256']:
        raise RuntimeError('checkpoint binding differs')
    if name in ('RGB', 'DSM'):
        model = FixedPair(r, d)
    elif name in ('S1', 'S13'):
        model = N1Segmenter(r, d, dict(id='N1-2', information_entry='late', adaptation='last4_and_heads'))
        model.load_state_dict(checkpoint(row['path'], row['sha256']), strict=True)
        if name == 'S13':
            # Same graph as Continuation S1-3: physical-zero, retained feature support,
            # retained raw fusion in local windows, exact full-missing guard.
            model = CrossPaths(model, 'A1B0C0')
    else:
        from post_t_paired_v2_common import card
        j = card('R16')
        initial = source['initial_checkpoint']
        model = PairedAdaptation(r, d, j, initial['path'], initial['sha256'])
        state = torch.load(row['path'], map_location='cpu', weights_only=False)
        if state['global_step'] != 16000 or state['signature']['job'] != j:
            raise RuntimeError('R16 endpoint signature/age changed')
        model.load_state_dict(state['model'], strict=True)
        del state
    return model.cuda().eval().requires_grad_(False), dict(expert_sources=provenance, endpoint=row)


def infer_one(model, name, optical, dsm, rm, dm, progress, entropy=False, batch=8):
    from d23_engine import positions
    h, w = rm.shape
    coords = [(y,x) for y in positions(h,512,256) for x in positions(w,512,256)]
    score = np.zeros((6,h,w), np.float32)
    coverage = np.zeros((h,w), np.uint16)
    own = {'rgb_only': True, 'dsm_only': True}
    with torch.inference_mode():
        for start in range(0,len(coords),batch):
            cs = coords[start:start+batch]
            n = len(cs)
            arrays = [np.stack([optical[y:y+512,x:x+512].transpose(2,0,1) for y,x in cs]),
                      np.stack([dsm[y:y+512,x:x+512] for y,x in cs]),
                      np.stack([rm[y:y+512,x:x+512] for y,x in cs]),
                      np.stack([dm[y:y+512,x:x+512] for y,x in cs])]
            tensors = []
            for a in arrays:
                t = torch.from_numpy(a).cuda()
                if n < batch:
                    t = torch.cat((t,t[-1:].expand((batch-n,)+t.shape[1:])))
                tensors.append(t)
            op, ds, rmask, dmask = tensors
            parts = model(op, ds, rmask, dmask, return_parts=True)
            z = parts['rgb' if name == 'RGB' else 'dsm' if name == 'DSM' else 'logits'].float()
            if name not in ('RGB','DSM'):
                for tag, use, ref in (('rgb_only',rmask&~dmask,'rgb'),('dsm_only',dmask&~rmask,'dsm')):
                    own[tag] &= bool(torch.equal(z.masked_select(use[:,None]), parts[ref].float().masked_select(use[:,None])))
                if name == 'S1' and not all(own.values()):
                    raise RuntimeError('S1 exact own-logit fallback differs')
            for a,(y,x) in zip(z[:n].cpu().numpy(),cs):
                score[:,y:y+512,x:x+512] += a
                coverage[y:y+512,x:x+512] += 1
            del tensors, arrays, parts, z, op, ds, rmask, dmask
            progress(windows_done=min(start+batch,len(coords)),windows_total=len(coords))
    if not coverage.all() or not np.isfinite(score).all():
        raise RuntimeError('stitch coverage/nonfinite scores')
    pred = score.argmax(0).astype(np.uint8)
    pred[~(rm|dm)] = 255
    bins = None
    if entropy:
        bins = np.empty((h,w),np.uint8)
        for y in range(0,h,64):
            z = score[:,y:y+64] / coverage[None,y:y+64]
            z -= z.max(0,keepdims=True)
            probabilities = np.exp(z)
            probabilities /= probabilities.sum(0,keepdims=True)
            ent = -(probabilities*np.log(np.maximum(probabilities,np.finfo(np.float32).tiny))).sum(0)/np.log(6)
            bins[y:y+64] = np.digitize(np.clip(ent,0,1),(.25,.5,.75)).astype(np.uint8)
    return pred, bins, own


def input_view(base, item, c):
    tile = c['tile']
    if c['family'] == 'clean':
        mask = np.zeros(item['dsm'].shape, bool)
        mb = None
    else:
        mask, mb = load_mask(base,tile,c['realization'],c['family'],c['ratio'])
    op = item['optical'].copy()
    op[mask] = 0
    if c['dsm'] == 'zero':
        ds = np.zeros_like(item['dsm'])  # Existing dsm_present_zero, availability=True.
        map_sha = None
    elif c['dsm'] == 'intact':
        ds, map_sha = item['dsm'], None
    else:
        mapping = read(Path(base)/'map_manifest.json')['tiles'][tile][c['dsm']]
        checked_array(mapping)
        with np.load(mapping['path'],allow_pickle=False) as z:
            ds = item['dsm'].ravel()[z['index']].reshape(item['dsm'].shape)
        map_sha = mapping['canonical_index_sha256']
    return op, ds, ~mask, np.ones_like(mask), mask, mb, map_sha


class Runner:
    def __init__(self,base,gpu,progress):
        from post_ab_n1_data import Loader
        self.base, self.gpu, self.progress = Path(base), gpu, progress
        p = environment(base,gpu)
        self.loader = Loader(Path(p['root']),read(self.base/'source_plan.json'))
        self.item = self.tile = self.model = self.name = None

    def run(self,c,target=None):
        import time
        target = target or self.base/'cases'/(case_id(c)+'.json')
        b = binding(self.base)
        if target.exists():
            row = read(target)
            if row['case'] != c or row['binding'] != b:
                raise RuntimeError('case cache binding differs')
            for a in row['arrays'].values():
                checked_array(a)
            return row
        if self.tile != c['tile']:
            self.item = self.loader(c['tile'],True)
            self.tile = c['tile']
        if self.name != c['model']:
            self.finish()
            self.model = None
            torch.cuda.empty_cache()
            self.model,self.provenance = make_model(self.base,c['model'])
            self.name = c['model']
            self.frozen = fingerprint(self.model)
        if any(v.requires_grad for v in self.model.parameters()):
            raise RuntimeError('unexpected trainable evaluation parameter')
        op, ds, rm, dm, mask, mb, map_sha = input_view(self.base,self.item,c)
        start = time.monotonic()
        entropy = c['model'] == 'S1' and c['dsm'] == 'intact' and c['family'] != 'clean' and c['ratio'] == 25
        if c == case('S1',c['tile']):
            pred, ent, own = old_prediction(self.base,'S1',c['tile']), None, dict(reused=True)
            reused = True
        else:
            def report(**kw):
                self.progress(case=case_id(c),physical_gpu=self.gpu,phase='inference',**kw)
            pred,ent,own = infer_one(self.model,c['model'],op,ds,rm,dm,report,entropy=entropy)
            reused = False
        if entropy:
            original = old_prediction(self.base,'S1',c['tile'],c['realization'],c['family'])
            if not np.array_equal(original,pred):
                raise RuntimeError('S1 archived replay label mismatch')
        arrays = {}
        for name,value in (('prediction',pred),('entropy',ent)):
            if value is not None:
                path = target.with_name(target.stem+'_'+name+'.npz')
                save_npz(path,value=value)
                arrays[name] = dict(path=str(path),sha256=sha(path),shape=list(value.shape),dtype=str(value.dtype))
        from structured_v0_masks import supports
        clean_case = case(c['model'],c['tile'],c['dsm'])
        if c['family'] == 'clean':
            clean = pred
        else:
            clean_row = read(self.base/'cases'/(case_id(clean_case)+'.json'))
            with np.load(checked_array(clean_row['arrays']['prediction']),allow_pickle=False) as z:
                clean = z['value']
        regions = supports(mask)
        if c['family'] != 'clean' and c['family'] == 'pixel':
            core,_ = load_mask(self.base,c['tile'],c['realization'],'pixel',5)
            regions['core5'] = core
        result = {scope:evidence(self.item[scope+'_gt'],clean,pred,regions) for scope in ('full','noboundary')}
        if c['family'] != 'clean' and c['model'] in ('S1','R16'):
            intact_ref = read(self.base/'cases'/(case_id(case(c['model'],c['tile']))+'.json'))
            with np.load(checked_array(intact_ref['arrays']['prediction']),allow_pickle=False) as z:
                intact_clean = z['value']
            for scope in ('full','noboundary'):
                for region,support in regions.items():
                    result[scope][region]['intact_clean_cm'] = cm(self.item[scope+'_gt'],intact_clean,support).tolist()
        row = dict(case=c,binding=b,arrays=arrays,mask_sha256=mb['canonical_sha256'] if mb else None,
            DSM_index_sha256=map_sha,provenance=self.provenance,scopes=result,physical_gpu=self.gpu,
            inference_seconds=time.monotonic()-start,reused_old_prediction=reused,own_logit_identity=own,
            entropy_definition='softmax(mean stitched FP32 logits); H/log6; fixed quartile bins',
            optimizer_updates=0,test6_loaded=False,held4_loaded=False,independent_final_loaded=False,
            frozen_all_parameters=True,observed_at=now(),gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated())
        write(target,row)
        write(self.base/('input_binding_last_'+str(self.gpu)+'.json'),dict(files=self.loader.verified,optimizer_updates=0))
        return row

    def finish(self):
        if self.model is not None and fingerprint(self.model) != self.frozen:
            raise RuntimeError('frozen model state changed')
