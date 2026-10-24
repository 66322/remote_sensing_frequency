"""D1 fixed weights x policies, then E frozen masks; only physical GPU0."""
import argparse,os,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
os.environ.setdefault('XFORMERS_DISABLED','1')
import numpy as np
import torch
from post_s1_support_common import *
from post_s1_support_evaluation import *
from d24_data import Loader
from run_post_s1_support import seed_all,load_anchors
from model.rebuild_v1_d26 import build_experts
from model.rebuild_v1_post_ab_n1 import N1Segmenter
from model.post_n5_cross_paths import CrossPaths
from model.post_s1_support_model import SupportResidual
from post_d30_evaluation import References,FixedPair
def old_model(root,p,name):
    binding,parent,c=source_binding(root,name)
    states,_=load_anchors(root,p);experts=build_experts(root,states);del states
    seed_all();model=N1Segmenter(*experts,dict(id='N1-2',information_entry='late',adaptation='last4_and_heads')).eval()
    state=torch.load(root/'records'/SOURCE_NAME/'jobs'/name/'selected.pth',map_location='cpu',weights_only=False)
    if state['signature']!=c['signature'] or state['global_step']!=8000:raise RuntimeError('selected state binding changed')
    model.load_state_dict(state['model'],strict=True);del state
    return model.eval().requires_grad_(False).cuda(),binding
def new_model(root,base,p,name):
    job=next(j for j in p['jobs'] if j['id']==name);accept_worker(base,name,p)
    states,_=load_anchors(root,p);experts=build_experts(root,states);del states
    seed_all();m=SupportResidual(*experts,job,p['initial_checkpoint']['path'],p['initial_checkpoint']['sha256'])
    state=torch.load(base/'jobs'/name/'selected.pth',map_location='cpu',weights_only=False)
    if state['signature']!=signature(base,p,job) or state['global_step']!=8000:raise RuntimeError('new fixed8000 binding changed')
    m.load_state_dict(state['model'],strict=True);del state
    return m.eval().requires_grad_(False).cuda(),dict(signature=signature(base,p,job),selected_checkpoint_sha256=sha(base/'jobs'/name/'selected.pth'))
def invariant_paths(model,loader,p):
    item=loader(p['data']['validation'][0],True)
    rgb=torch.from_numpy(item['optical'][:512,:512].transpose(2,0,1).copy())[None].cuda()
    ds=torch.from_numpy(item['dsm'][:512,:512].copy())[None].cuda();full=torch.ones_like(ds,dtype=torch.bool)
    checks={}
    with torch.inference_mode():
        for state,rm,dm in [('clean',full,full),('rgb_missing',~full,full),('dsm_missing',full,~full)]:
            original=None;ok=True
            for policy in POLICIES:
                value=CrossPaths(model,policy)(rgb,ds,rm,dm)
                if original is None:original=value
                else:ok&=bool(torch.equal(value,original))
            if not ok:raise RuntimeError('same-weight invariant graph differs '+state)
            checks[state]=ok
    return checks
def d1(root,base,p,out,progress):
    loader=Loader(root,p);index={};new_units=0;invariants={}
    for i,name in enumerate(SHAS):
        model,mb=old_model(root,p,name);invariants[name]=invariant_paths(model,loader,p)
        for policy in POLICIES:
            folder=out/name/policy;tiles={};wrapper=CrossPaths(model,policy).eval()
            for tile in p['data']['validation']:
                item=loader(tile,True)
                for key in ('rgb_U','dsm_U'):
                    view,rm,dm,mask=view_for(base,item,tile,key)
                    old,row,rb=source_case(root,name,'support_evaluation',key,tile)
                    if row['mask_binding']['sha256']!=mask['sha256']:raise RuntimeError('diagonal mask mismatch')
                    binding=dict(weight=mb,policy=policy,plan_sha256=sha(base/'plan.json'),source=rb,optimizer_updates=0)
                    if policy==POLICIES[i]:values=old;binding['diagonal_reused']=True
                    else:
                        report=lambda **kw:progress(phase='D1',model=name,policy=policy,tile=tile,condition=key,**kw)
                        report();pred,_=infer(wrapper,view,rm,dm,report);values=dict(old,candidate=pred['candidate']);new_units+=1
                    tiles.setdefault(key,{})[tile]=write_case(folder,key,tile,item,rm,dm,values,binding,mask,rb)
                    if wrapper.trace is not None:write(folder/'forward_trace.json',wrapper.trace)
            finish_summary(folder,tiles,dict(weight=mb,policy=policy,optimizer_updates=0))
            index[name+'/'+policy]=dict(path=str(folder/'summary.json'),sha256=sha(folder/'summary.json'))
        del model,wrapper;torch.cuda.empty_cache()
    if new_units!=48:raise RuntimeError('D1 inference budget changed')
    write(out/'summary.json',dict(records=index,new_tile_units=new_units,reused_tile_units=16,
        same_weight_invariants=invariants,plan_sha256=sha(base/'plan.json'),optimizer_updates=0))
def e_eval(root,base,p,out,progress):
    loader=Loader(root,p)
    def factory():
        states,_=load_anchors(root,p);r,d=build_experts(root,states);r.configure(False);d.configure(False)
        return FixedPair(r,d).cuda()
    refs=References(base,factory);indices={};models=['S1-0','S1-3']+['P'+str(i) for i in range(10)]
    for name in models:
        if name.startswith('S1-'):
            model,binding=old_model(root,p,name)
            wrapper=CrossPaths(model,POLICIES[int(name[-1])]).eval()
        else:model,binding=new_model(root,base,p,name);wrapper=model
        extra_eval(wrapper,loader,refs,p,out/name,binding,progress,base,E_KEYS,'evaluation')
        indices[name]=dict(path=str(out/name/'evaluation/summary.json'),sha256=sha(out/name/'evaluation/summary.json'))
        del wrapper,model;torch.cuda.empty_cache()
    route={}
    for tile in p['data']['validation']:
        item=loader(tile,True)
        for key in E_KEYS:
            _,rm,dm,mb=view_for(base,item,tile,key)
            arow=read(out/'S1-0/evaluation'/key/(tile+'.json'));brow=read(out/'S1-3/evaluation'/key/(tile+'.json'))
            def load(name,row):
                f=out/name/'evaluation'/key;values={}
                for n in ('candidate','fixed_rgb','fixed_dsm'):
                    path=f/n/(tile+'.npy')
                    if sha(path)!=row['predictions'][n]:raise RuntimeError('E source prediction changed')
                    values[n]=np.load(path,allow_pickle=False)
                return values
            a=load('S1-0',arow);b=load('S1-3',brow);routed,_=simple_route(a['candidate'],b['candidate'],rm,dm)
            vals=dict(a,candidate=routed)
            route.setdefault(key,{})[tile]=write_case(out/'R0/evaluation',key,tile,item,rm,dm,vals,
                dict(control=arow['binding'],context=brow['binding'],optimizer_updates=0),mb)
    finish_summary(out/'R0/evaluation',route,dict(plan_sha256=sha(base/'plan.json'),optimizer_updates=0))
    indices['R0']=dict(path=str(out/'R0/evaluation/summary.json'),sha256=sha(out/'R0/evaluation/summary.json'))
    write(out/'summary.json',dict(records=indices,new_tile_units=144,optimizer_updates=0,mask_manifest_sha256=sha(base/'mask_manifest.json')))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True)
    ap.add_argument('--job',choices=('D1','E'),required=True);ap.add_argument('--gpu',type=int,choices=(0,),required=True);a=ap.parse_args()
    root,base=dirs(a.root,a.directory);p=validate(read(base/'plan.json'));verify_snapshot(base)
    from post_n2_diag_runtime import input_contract
    input_contract(root,p)
    prep=read(base/'preparation_complete.json')
    if prep['plan_sha256']!=sha(base/'plan.json') or prep['mask_manifest_sha256']!=sha(base/'mask_manifest.json'):raise RuntimeError('preparation binding changed')
    if os.environ.get('CUDA_VISIBLE_DEVICES')!='0' or torch.__version__!='2.2.2+cu121':raise RuntimeError('GPU0/bound Torch required')
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False
    torch.backends.cuda.matmul.allow_tf32=True;torch.backends.cudnn.allow_tf32=True;seed_all()
    out=base/'jobs'/a.job;out.mkdir(parents=True,exist_ok=False)
    import fcntl
    lock=(out/'worker.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    started=time.monotonic()
    def progress(**kw):write(out/'progress.json',dict(job=a.job,physical_gpu=0,optimizer_updates=0,elapsed_seconds=time.monotonic()-started,observed_at=now(),**kw))
    (d1 if a.job=='D1' else e_eval)(root,base,p,out,progress)
    write(out/'complete.json',dict(execution_commit=p['execution_commit'],plan_sha256=sha(base/'plan.json'),
        code_manifest_sha256=sha(base/'code_manifest.json'),artifacts={'summary.json':sha(out/'summary.json')},
        optimizer_updates=0,test6_loaded=False,independent_final_loaded=False,completed_at=now()))
    progress(phase='complete')
if __name__=='__main__':main()

