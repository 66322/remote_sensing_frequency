"""26 fixed evaluation cells; no optimizer, no training data, GPU0 only."""
import argparse,os,sys,time
from pathlib import Path
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8');os.environ.setdefault('XFORMERS_DISABLED','1')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from post_t_mechanism_common import *
from post_s1_support_evaluation import view_for,write_case,finish_summary,simple_route,transition
from post_d30_evaluation import infer
from post_ab_n1_data import Loader
from run_post_s1_transfer import load_anchors,seed_all
from model.rebuild_v1_d26 import build_experts
from model.rebuild_v1_post_ab_n1 import N1Segmenter
from model.post_n5_cross_paths import CrossPaths
from model.post_s1_transfer_model import PrivateDecoder,checkpoint
from model.post_t_mechanism import compose
def load_model(root,p,job):
    seed_all();states,_=load_anchors(root,p);experts=build_experts(root,states);del states
    if job['kind']=='module':
        a=checkpoint(p['donors']['S1-0']['path'],SHAS['S1-0']);b=checkpoint(p['donors']['S1-3']['path'],SHAS['S1-3'])
        model=N1Segmenter(*experts,dict(id='N1-2',information_entry='late',adaptation='last4_and_heads'))
        model.load_state_dict(compose(a,b,job),strict=True);del a,b
        model=CrossPaths(model,'A1B0C0' if job['context'] else 'A1B1C0')
        binding=dict(sources={k:p['donors'][k] for k in ('S1-0','S1-3')},module_card=job,native_output='S1-0 outside observable RGB missing support')
    else:
        pred=Path(p['predecessor_directory']);parent=p['parent_transfer_plan'];j=job['source_job'];card=next(x for x in parent['jobs'] if x['id']==j)
        point=pred/'jobs'/j/'checkpoints/step_4000.pth';v=read(pred/'jobs'/j/'validation/step_4000.json');digest=sha(point)
        expected=previous.signature(pred,parent,card)
        if v['binding']['training']!=expected or v['binding']['step']!=4000 or v['binding']['checkpoint_sha256']!=digest:raise RuntimeError('midpoint validation binding changed')
        model=PrivateDecoder(*experts,card,p['initial_checkpoint']['path'],p['initial_checkpoint']['sha256'],p['donors'].get(card['donor']))
        state=torch.load(point,map_location='cpu',weights_only=False)
        if state['signature']!=expected or state['global_step']!=4000:raise RuntimeError('midpoint state changed')
        model.load_state_dict(state['model'],strict=True);del state
        binding=dict(source_job=j,step=4000,checkpoint_sha256=digest,checkpoint_path=str(point),training=expected)
    return model.eval().requires_grad_(False).cuda(),binding
def reference(base,p,key,tile,which,cache):
    name=('base_U' if which=='base' else 'R0_U') if key in ('rgb_U','dsm_U') else ('E_S1-0' if which=='base' else 'E_R0')
    ix=read(base/'reference_index.json')[name]
    if name not in cache:
        if sha(ix['path'])!=ix['sha256']:raise RuntimeError('reference digest changed')
        cache[name]=read(ix['path'])
    row=cache[name]['tiles'][key][tile]
    parent=within(Path(ix['source_path']).parent,Path(p['predecessor_directory']).parents[1])
    values={}
    for n in ('candidate','fixed_rgb','fixed_dsm'):
        path=parent/key/n/(tile+'.npy')
        if sha(path)!=row['predictions'][n]:raise RuntimeError('native reference prediction changed')
        values[n]=np.load(path,allow_pickle=False)
    return values,dict(record=str(parent/key/(tile+'.json')),summary_sha256=ix['sha256'],prediction_sha256=row['predictions'])
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--job',required=True);ap.add_argument('--gpu',type=int,choices=(0,),required=True);a=ap.parse_args()
    root,base=dirs(a.root,a.directory);p=validate(read(base/'plan.json'));verify_snapshot(base)
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='0' or torch.__version__!='2.2.2+cu121':raise RuntimeError('GPU0 and bound Torch required')
    from post_n2_diag_runtime import input_contract
    input_contract(root,p)
    prep=read(base/'preparation_complete.json')
    if prep['plan_sha256']!=sha(base/'plan.json') or prep['mask_manifest_sha256']!=sha(base/'mask_manifest.json') or prep['reference_index_sha256']!=sha(base/'reference_index.json'):raise RuntimeError('preparation changed')
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False;torch.backends.cuda.matmul.allow_tf32=True;torch.backends.cudnn.allow_tf32=True
    job=next(j for j in p['jobs'] if j['id']==a.job);out=base/'jobs'/a.job;out.mkdir(parents=True,exist_ok=False)
    import fcntl
    lock=(out/'worker.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    began=time.monotonic()
    def progress(**kw):write(out/'progress.json',dict(job=a.job,physical_gpu=0,optimizer_updates=0,elapsed_seconds=time.monotonic()-began,observed_at=now(),**kw))
    progress(phase='loading_bound_weights');model,mb=load_model(root,p,job)
    binding=dict(execution_commit=p['execution_commit'],plan_sha256=sha(base/'plan.json'),code_manifest_sha256=sha(base/'code_manifest.json'),job=job,checkpoint=mb,optimizer_updates=0)
    write(out/'checkpoint_binding.json',binding)
    loader=Loader(root,p);tiles={};cache={};case_artifacts={};endpoint=[]
    for tile in p['data']['validation']:
        item=loader(tile,True)
        for key in job['keys']:
            view,rm,dm,mask=view_for(base,item,tile,key)
            report=lambda **kw:progress(phase='inference',tile=tile,condition=key,**kw)
            report();tick=time.monotonic()
            with torch.inference_mode():pred,_=infer(model,view,rm,dm,report)
            elapsed=time.monotonic()-tick
            control,rb=reference(base,p,key,tile,'base',cache);route,rr=reference(base,p,key,tile,'R0',cache)
            if job['kind']=='module':candidate,use=simple_route(control['candidate'],pred['candidate'],rm,dm)
            else:candidate=pred['candidate'];use=(~rm)&dm
            if not np.array_equal(candidate[~use],control['candidate'][~use]):raise RuntimeError('outside-support output changed')
            if job['id']=='M333_context':
                if not np.array_equal(candidate,route['candidate']):raise RuntimeError('same-source endpoint did not reproduce R0')
                endpoint.append(dict(tile=tile,condition=key,exact=True))
            row=write_case(out,key,tile,item,rm,dm,dict(control,candidate=candidate),binding,mask,rb)
            row['cost']=dict(candidate_native_tile_inference_seconds=elapsed,base_prediction_reused=True,peak_allocated_bytes=torch.cuda.max_memory_allocated())
            row['transition_vs_base']={scope:transition(item[scope+'_gt'],control['candidate'],candidate,use) for scope in ('full','noboundary')}
            row['transition_vs_R0']={scope:transition(item[scope+'_gt'],route['candidate'],candidate,use) for scope in ('full','noboundary')}
            row['R0_reference']=rr;write(out/key/(tile+'.json'),row);tiles.setdefault(key,{})[tile]=row
            case_artifacts[key+'/'+tile+'.json']=sha(out/key/(tile+'.json'))
            print('MECHANISM_CASE',job['id'],tile,key,flush=True)
        del item
    finish_summary(out,tiles,binding)
    write(out/'endpoint_checks.json',endpoint)
    arts={n:sha(out/n) for n in ('summary.json','checkpoint_binding.json','endpoint_checks.json')};arts.update(case_artifacts)
    write(out/'complete.json',dict(execution_commit=p['execution_commit'],plan_sha256=sha(base/'plan.json'),code_manifest_sha256=sha(base/'code_manifest.json'),job=job,artifacts=arts,optimizer_updates=0,test6_loaded=False,independent_final_loaded=False,completed_at=now()))
    progress(phase='complete')
    lock.close()
if __name__=='__main__':main()
