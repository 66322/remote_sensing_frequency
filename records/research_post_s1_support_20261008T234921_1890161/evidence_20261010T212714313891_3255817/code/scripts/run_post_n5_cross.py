"""One frozen model, 64 tile-path evaluations, zero optimizer updates."""
import argparse,os,sys,time,hashlib
from pathlib import Path
os.environ.setdefault('XFORMERS_DISABLED','1');os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from post_n5_cross_common import *
from post_n2_diag_runtime import construct_model,input_contract,load_mask
from post_n2_masks import physical_view
from model.post_n5_cross_paths import CrossPaths
from d24_data import Loader
from post_d30_evaluation import infer,counts,save_prediction,joint_counts,encode_joint,joint_report,metric
def array_digest(x):
    h=hashlib.sha256();h.update(str(x.shape).encode());h.update(str(x.dtype).encode());h.update(np.ascontiguousarray(x).tobytes());return h.hexdigest()
def signature_for(base,p,job,binding):
    return dict(job=job,execution_commit=p['execution_commit'],plan_sha256=sha(base/'plan.json'),
        code_manifest_sha256=sha(base/'code_manifest.json'),model_binding=binding,
        mask_manifest_sha256=sha(base/'mask_manifest.json'),optimizer_updates=0)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--job',required=True);ap.add_argument('--gpu',type=int,choices=[0,1],required=True);a=ap.parse_args()
    root,base=dirs(a.root,a.directory);p=validate(read(base/'plan.json'));job=next(j for j in p['jobs'] if j['id']==a.job)
    if job['gpu']!=a.gpu or os.environ.get('CUDA_VISIBLE_DEVICES')!=str(a.gpu):raise RuntimeError('physical GPU binding differs')
    if torch.__version__!='2.2.2+cu121':raise RuntimeError('bound Torch2.2.2+cu121 required')
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False;torch.backends.cuda.matmul.allow_tf32=True;torch.backends.cudnn.allow_tf32=True
    verify_snapshot(base);input_contract(root,p)
    prep=read(base/'cpu_preparation_complete.json')
    for k,n in [('plan_sha256','plan.json'),('masks_sha256','mask_manifest.json'),('E3_sha256','e3_screen.json'),('boundary_sha256','boundary_screen.json')]:
        if prep[k]!=sha(base/n):raise RuntimeError('preparation binding changed')
    out=base/'jobs'/a.job;out.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=(out/'worker.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (out/'complete.json').exists() or (out/'binding.json').exists():raise RuntimeError('preserve completed/partial evaluation; no automatic retry')
    began=time.monotonic();state=dict(job=a.job,model=job['model'],physical_gpu=a.gpu,optimizer_updates=0)
    def progress(**kw):
        if any(kw.get(k,state.get(k))!=state.get(k) for k in ('phase','tile','condition')):
            for key in ('windows_done','windows_total'):state.pop(key,None)
        state.update(kw,observed_at=now(),elapsed_seconds=time.monotonic()-began);write(out/'progress.json',state)
    progress(phase='loading_selected')
    original,binding=construct_model(root,base,job['model'],'cuda');model=CrossPaths(original,'A1B1C1').eval()
    signature=signature_for(base,p,job,binding);write(out/'binding.json',signature)
    loader=Loader(root,p);records={};cms={}
    for tile in p['data']['validation']:
        item=loader(tile,True);missing,mb=load_mask(base,tile,'U')
        for direction in p['E4']['directions']:
            for case in p['E4']['cases']:
                view,rm,dm=physical_view(item,missing,direction,case)
                physical={n:array_digest(x) for n,x in view.items()};reported={'rgb':array_digest(rm),'dsm':array_digest(dm)}
                for path in p['paths']:
                    key=direction+'_'+case+'_'+path;model.set_path(path);target=out/'evaluation'/key
                    progress(phase='inference',tile=tile,condition=key)
                    pred,identity=infer(model,view,rm,dm,lambda **kw:progress(phase='inference',tile=tile,condition=key,**kw),batch=8)
                    if model.C and not all(identity.values()):raise RuntimeError('hard fallback equality failed')
                    parity=None
                    if path=='A1B1C1':
                        oldfolder=Path(p['source_diag_directory'])/'jobs'/('E2_'+job['model'])
                        oldc=read(oldfolder/'complete.json');oldrow=read(oldfolder/'evaluation'/(direction+'_'+case)/(tile+'.json'))
                        if oldc['summary_sha256']!=sha(oldfolder/'summary.json') or oldrow['binding']['training']!=oldc['signature'] or oldc['signature']['model_binding']['checkpoint_sha256']!=binding['checkpoint_sha256']:raise RuntimeError('original E2 source binding changed')
                        parity={}
                        for name in ('candidate','rgb','dsm'):
                            oldpath=oldfolder/'evaluation'/(direction+'_'+case)/name/(tile+'.npy')
                            if sha(oldpath)!=oldrow['predictions'][name]:raise RuntimeError('original E2 prediction changed')
                            if not np.array_equal(pred[name],np.load(oldpath,allow_pickle=False)):raise RuntimeError('A1B1C1 differs from original E2 '+name)
                            parity[name]=dict(path=str(oldpath),sha256=sha(oldpath),array_equal=True)
                    regs=dict(all=np.ones(missing.shape,bool),mask_location=missing,other_locations=~missing)
                    scopes={}
                    for scope in ('full','noboundary'):
                        gt=item[scope+'_gt'];js={r:joint_counts(gt,pred['rgb'],pred['dsm'],pred['candidate'],m) for r,m in regs.items()}
                        scopes[scope]=dict(metrics={n:{r:counts(gt,pred[n],m) for r,m in regs.items()} for n in ('candidate','rgb','dsm')},
                            joint={r:encode_joint(v) for r,v in js.items()},joint_report={r:joint_report(v) for r,v in js.items()})
                    hashes={n:save_prediction(target/n/(tile+'.npy'),pred[n]) for n in ('candidate','rgb','dsm')}
                    row=dict(binding=signature,tile=tile,condition=key,path=path,direction=direction,case=case,
                        mask_binding=mb,physical_input_sha256=physical,reported_mask_sha256=reported,
                        first_batch_trace=model.trace,original_E2_parity=parity,predictions=hashes,scopes=scopes,
                        fallback_logits_equal_own=identity,anchor_role='adapted own branches diagnostic; not immutable original anchors',
                        optimizer_updates=0,confusion_matrix_dtype='int64',test6_loaded=False,independent_final_loaded=False)
                    record=target/(tile+'.json');write(record,row)
                    records.setdefault(key,{})[tile]=dict(path=str(record),sha256=sha(record))
                    cms.setdefault(key,{})[tile]=scopes['noboundary']['metrics']['candidate']['all']['cm']
                    print('CROSS_EVAL',a.job,tile,key,flush=True)
                    del pred,scopes,row,js
                del view
        del item,missing
    pooled={k:metric(sum((np.asarray(cm,np.int64) for cm in rows.values()),np.zeros((6,6),np.int64))) for k,rows in cms.items()}
    write(out/'summary.json',dict(binding=signature,records=records,tiles=cms,pooled=pooled,source_inputs=loader.verified,optimizer_updates=0,test6_loaded=False,independent_final_loaded=False,observed_at=now()))
    write(out/'complete.json',dict(signature=signature,summary_sha256=sha(out/'summary.json'),inference_tile_units=sum(len(x) for x in records.values()),optimizer_updates=0,completed_at=now(),test6_loaded=False,independent_final_loaded=False))
    progress(phase='complete');print('CROSS_JOB_COMPLETE',a.job,flush=True)
if __name__=='__main__':main()
