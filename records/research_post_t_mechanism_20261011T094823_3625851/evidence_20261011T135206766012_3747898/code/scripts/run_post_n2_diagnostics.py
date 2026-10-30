"""One bound checkpoint, inference only; no optimizer or training entry."""
import argparse,os,sys,time
from pathlib import Path
os.environ.setdefault('XFORMERS_DISABLED','1');os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from post_n2_diag_common import *
from post_n2_masks import physical_view
from post_n2_diag_runtime import construct_model,input_contract,load_mask,source_row,read_prediction
from d24_data import Loader
from post_d30_evaluation import infer,counts,joint_counts,encode_joint,joint_report,save_prediction

def tensor_digest(value):
    h=__import__('hashlib').sha256();h.update(str(value.shape).encode());h.update(str(value.dtype).encode());h.update(np.ascontiguousarray(value).tobytes());return h.hexdigest()

def evaluate_case(model,item,missing,direction,case,stage,target,binding,mask_binding,progress):
    view,rm,dm=physical_view(item,missing,direction,case)
    physical_hash={n:tensor_digest(v) for n,v in view.items()};reported_hash={n:tensor_digest(v) for n,v in {'rgb':rm,'dsm':dm}.items()}
    predictions,identity=infer(model,view,rm,dm,progress,batch=8)
    hashes={n:save_prediction(target/n/(binding['tile']+'.npy'),p) for n,p in predictions.items() if n in ('candidate','rgb','dsm')}
    # E1 A0/B1 own experts are the immutable original anchors. For E2 these
    # adapted own branches are diagnostics, not scientific fixed anchors.
    regions={'all':np.ones(missing.shape,bool),'mask_location':missing,'other_locations':~missing,'physically_missing':missing if case in ('known_missing','false_negative') else np.zeros(missing.shape,bool)}
    scopes={}
    for scope in ('full','noboundary'):
        gt=item[scope+'_gt'];metrics={n:{r:counts(gt,p,m) for r,m in regions.items()} for n,p in predictions.items() if n in ('candidate','rgb','dsm')}
        jr={r:joint_counts(gt,predictions['rgb'],predictions['dsm'],predictions['candidate'],m) for r,m in regions.items()}
        scopes[scope]=dict(metrics=metrics,joint={r:encode_joint(v) for r,v in jr.items()},joint_reports={r:joint_report(v) for r,v in jr.items()},label_class_counts_at_mask=counts(gt,gt,missing)['support'])
    row=dict(binding=binding,stage=stage,direction=direction,case=case,mask_binding=mask_binding,physical_input_sha256=physical_hash,reported_mask_sha256=reported_hash,
        predictions=hashes,fallback_logits_equal_own=identity,scopes=scopes,anchor_role='immutable original experts' if stage=='E1' else 'adapted own logits diagnostic; not original anchor partitions',
        confusion_matrix_dtype='int64',metric='Potsdam Val2 native512 stride256 NoBoundary fg5; Full diagnostics',test6_loaded=False,independent_final_loaded=False,observed_at=now())
    write(target/(binding['tile']+'.json'),row);return row

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--job',required=True);ap.add_argument('--gpu',type=int,choices=[0,1],required=True);a=ap.parse_args()
    root,base=dirs(a.root,a.directory);plan=validate(read(base/'plan.json'));job=next(j for j in plan['jobs'] if j['id']==a.job)
    if job['gpu']!=a.gpu or os.environ.get('CUDA_VISIBLE_DEVICES')!=str(a.gpu):raise RuntimeError('GPU binding changed')
    if torch.__version__!='2.2.2+cu121':raise RuntimeError('bound Torch2.2.2+cu121 required')
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False;torch.backends.cuda.matmul.allow_tf32=True;torch.backends.cudnn.allow_tf32=True
    verify_snapshot(base);input_contract(root,plan)
    prep=read(base/'cpu_preparation_complete.json')
    if prep['plan_sha256']!=sha(base/'plan.json') or prep['masks_sha256']!=sha(base/'mask_manifest.json'):raise RuntimeError('preparation binding differs')
    out=base/'jobs'/a.job;out.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=(out/'worker.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (out/'complete.json').exists():raise RuntimeError('completed diagnostic not rerun automatically')
    if any(out.glob('*/**/*.json')):raise RuntimeError('partial evaluation requires explicit diagnosis, no automatic retry')
    began=time.monotonic();state=dict(job=a.job,model=job['model'],physical_gpu=a.gpu,optimizer_updates=0)
    def progress(**kw):
        if kw.get('phase',state.get('phase'))!=state.get('phase'):
            for n in ('windows_done','windows_total'):state.pop(n,None)
        state.update(kw,observed_at=now(),elapsed_seconds=time.monotonic()-began);write(out/'progress.json',state)
    progress(phase='loading_bound_checkpoint')
    model,model_binding=construct_model(root,base,job['model'],'cuda');loader=Loader(root,plan)
    signature=dict(job=job,execution_commit=plan['execution_commit'],plan_sha256=sha(base/'plan.json'),code_manifest_sha256=sha(base/'code_manifest.json'),model_binding=model_binding,
        mask_manifest_sha256=sha(base/'mask_manifest.json'),input_manifest_sha256=plan['input_manifest_sha256'],torch_version=torch.__version__,optimizer_updates=0)
    write(out/'binding.json',signature);records={};clean={}
    for tile in plan['data']['validation']:
        item=loader(tile,True);folder,old=source_row(root,job['model'],'clean',tile)
        old_candidate=read_prediction(folder,old,'clean',tile,'candidate')
        # Check clean CM independently from existing prediction, with no GPU rerun.
        expected=old['scopes']['noboundary']['metrics']['candidate']['valid']['cm']
        actual=counts(item['noboundary_gt'],old_candidate,np.ones(old_candidate.shape,bool))
        if actual['cm']!=expected:raise RuntimeError('clean prediction counts changed')
        clean[tile]=dict(metrics={scope:counts(item[scope+'_gt'],old_candidate,np.ones(old_candidate.shape,bool)) for scope in ('full','noboundary')},source_record_sha256=sha(folder/'evaluation/clean'/(tile+'.json')),binding=old['binding']);del old_candidate
        for direction in ('rgb','dsm'):
            rules=('U','H','L') if job['stage']=='E1' else ('U',)
            for rule in rules:
                missing,mb=load_mask(base,tile,rule)
                cases=('known_missing',) if job['stage']=='E1' else ('false_positive','known_missing','false_negative')
                for case in cases:
                    key=direction+'_'+rule if job['stage']=='E1' else direction+'_'+case
                    target=out/'evaluation'/key;target.mkdir(parents=True,exist_ok=True)
                    progress(phase='inference',tile=tile,condition=key)
                    row=evaluate_case(model,item,missing,direction,case,job['stage'],target,dict(training=signature,tile=tile),mb,lambda **kw:progress(phase='inference',tile=tile,condition=key,**kw))
                    records.setdefault(key,{})[tile]=dict(path=str(target/(tile+'.json')),sha256=sha(target/(tile+'.json')))
                    print('DIAG_EVAL',a.job,tile,key,flush=True);del row
                del missing
        del item
    summary=dict(binding=signature,records=records,clean=clean,source_inputs=loader.verified,test6_loaded=False,independent_final_loaded=False,optimizer_updates=0,observed_at=now())
    write(out/'summary.json',summary)
    write(out/'complete.json',dict(signature=signature,summary_sha256=sha(out/'summary.json'),optimizer_updates=0,inference_tile_units=sum(len(x) for x in records.values()),clean_reused_tile_units=len(clean),completed_at=now(),test6_loaded=False,independent_final_loaded=False))
    progress(phase='complete');print('DIAG_JOB_COMPLETE',a.job,flush=True)
if __name__=='__main__':main()
