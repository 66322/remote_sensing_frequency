"""48 new fixed-checkpoint tile interventions; original routes reuse raw evidence."""
import argparse,os,sys
from pathlib import Path
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
os.environ.setdefault('XFORMERS_DISABLED','1')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from d30_common import read,write,sha,now,within,directories
from d27_data import Loader
from d27_evaluation import References,FixedPair,evaluate
from run_rebuild_v1_d30 import load_anchors
from model.rebuild_v1_d26 import build_experts
from model.rebuild_v1_d30 import ForcedMixture

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--job',choices=('replay_G0','replay_G1'),required=True);ap.add_argument('--gpu',type=int,choices=(0,1),required=True);a=ap.parse_args()
    root,base=directories(a.root,a.directory);plan=read(base/'plan.json');arm=a.job.split('_',1)[1]
    if os.environ.get('CUDA_VISIBLE_DEVICES')!=str(a.gpu):raise RuntimeError('GPU binding differs')
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False
    torch.backends.cuda.matmul.allow_tf32=True;torch.backends.cudnn.allow_tf32=True
    if torch.__version__!='2.2.2+cu121':raise RuntimeError('use bound d18_dino Torch2.2.2+cu121')
    manifest=read(base/'code_manifest.json')
    for name,digest in manifest['files'].items():
        if sha(base/'code'/name)!=digest:raise RuntimeError('source changed '+name)
    for name,digest in plan['expected_configs'].items():
        file={'base_config_sha256':'r05_quality_plus_dropout_16k.json','dino_config_sha256':'d18_d19_night_20260927.json','split_sha256':'potsdam_split_seed20260915.json'}[name]
        if sha(root/'configs/rebuild_v1'/file)!=digest:raise RuntimeError('config changed')
    if sha(root/'records/rebuild_v1_d21_queue_20260928/input_manifest.json')!=plan['input_manifest_sha256']:raise RuntimeError('input manifest changed')
    import subprocess
    dino=read(root/'configs/rebuild_v1/d18_d19_night_20260927.json')['dino'];repo=within(root/dino['repository_dir'],'/home/jovyan/zzx')
    if subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()!=dino['repository_commit']:raise RuntimeError('DINO source changed')
    subprocess.run(['git','-C',str(repo),'diff','--exit-code','HEAD','--','dinov2','hubconf.py'],stdout=subprocess.DEVNULL,check=True)
    parent=Path(plan['parent_D27_directory']);bound=read(base/'reuse_binding.json')['jobs'][arm]
    path=within(bound['checkpoint_path'],parent)
    if sha(path)!=bound['checkpoint_sha256']:raise RuntimeError('replay checkpoint changed')
    states,_=load_anchors(root,plan);r,d=build_experts(root,states);del states
    model=ForcedMixture(r,d,arm,'uniform')
    checkpoint=torch.load(path,map_location='cpu',weights_only=False)
    if checkpoint['signature']!=read(parent/'jobs'/arm/'complete.json')['signature'] or checkpoint['global_step']!=4000:raise RuntimeError('replay age/signature differs')
    model.load_state_dict(checkpoint['model'],strict=True);del checkpoint
    model=model.cuda().eval();out=base/'jobs'/a.job;out.mkdir(parents=True,exist_ok=True)
    import fcntl
    lock=(out/'worker.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    signature=dict(job=a.job,checkpoint=bound,plan_sha256=sha(base/'plan.json'),source_sha256=sha(base/'code_manifest.json'),execution_commit=manifest['commit'],test6_loaded=False)
    conditions=['clean','rgb_down4','aux_noise_std010']
    reused=[]
    for condition in conditions:
        for tile in plan['data']['validation']:
            record=parent/'jobs'/arm/'evaluation'/condition/(tile+'.json');row=read(record)
            if row['binding']['selected']['checkpoint_sha256']!=bound['checkpoint_sha256']:raise RuntimeError('original route evidence binding differs')
            for name,digest in row['predictions'].items():
                pred=record.parent/name/(tile+'.npy')
                if sha(pred)!=digest:raise RuntimeError('original prediction changed')
            target=out/'original_reused'/condition/(tile+'.json')
            if target.exists() and target.read_bytes()!=record.read_bytes():raise RuntimeError('conflicting original record')
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists():target.write_bytes(record.read_bytes())
            reused.append(dict(path=str(record),sha256=sha(record)))
    write(out/'original_reuse_index.json',reused)
    def fixed_factory():raise RuntimeError('replay must reuse same-forward frozen predictions')
    refs=References(base,fixed_factory);loader=Loader(root,plan);done=0
    for mode in ('uniform','expert0','expert1','expert2'):
        model.mode=mode
        def progress(**kw):write(out/'progress.json',dict(job=a.job,mode=mode,done=done,total=24,observed_at=now(),**kw))
        modeout=out/'modes'/mode
        evaluate(model,loader,refs,plan,modeout,dict(signature=signature,intervention=mode,original_route_reused=True),progress,conditions)
        done+=6;progress(phase='intervention_complete')
    write(out/'input_binding.json',dict(files=loader.verified))
    write(out/'complete.json',dict(signature=signature,new_tile_evaluations=done,original_reused=6,completed_at=now(),test6_loaded=False))
    write(out/'progress.json',dict(job=a.job,phase='complete',done=done,total=24,observed_at=now()))
    print('D30_REPLAY_COMPLETE',a.job,done,flush=True)
if __name__=='__main__':main()

