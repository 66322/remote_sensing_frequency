"""Detached D28 queue waits for terminal D27 AND released controller lock."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
from datetime import datetime

FILES=['scripts/d28_pressure.py','scripts/run_rebuild_v1_d28.py','scripts/summarize_rebuild_v1_d28.py','scripts/status_rebuild_v1_d28.py','scripts/upload_rebuild_v1_d28_records.py','scripts/launch_rebuild_v1_d28.py','tests/test_d28.py']
MODELS=['RGB_anchor','DSM_anchor','D26_B0','D27_S1','D27_G0','D27_G1','D27_L1']
def now():return datetime.now().astimezone().isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def write(p,row):
    t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(row,indent=2,allow_nan=False)+'\n',encoding='utf-8');os.replace(t,p)
def terminal(state):
    expected={'S0','S1','G0','G1','L0','L1','C0','C1','L1-sh','C1-sh'}
    return state.get('status') in ('COMPLETE','COMPLETE_WITH_TECHNICAL_FAILURES') and set(state.get('jobs',{}))==expected and all(r.get('status') in ('COMPLETE','TECHNICAL_FAILURE','TIMEOUT') for r in state['jobs'].values())
def released(parent):
    import fcntl
    with (parent/'controller.lock').open('r') as f:
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return False
        return True
def checkpoints(root,parent,plan):
    runtime=read(parent/'plan.json');d26=Path(runtime['predecessor_directory']);models={};missing=[]
    for name in MODELS:
        if name.endswith('_anchor'):
            row=runtime['experts']['rgb' if name=='RGB_anchor' else 'dsm'];path=(root/row['path']).resolve();step=row['step'];digest=row['sha256']
        else:
            folder=(d26 if name=='D26_B0' else parent)/'jobs'/name.split('_',1)[1];complete=folder/'complete.json'
            if not complete.exists():missing.append(name);continue
            row=read(complete)
            if row.get('test6_loaded') or row['global_step']!=8000:raise RuntimeError('invalid completed training binding')
            if name!='D26_B0' and row['signature']['execution_commit']!=runtime['execution_commit']:raise RuntimeError('D27 execution differs')
            if name!='D26_B0' and row['signature']['plan_sha256']!=sha(parent/'plan.json'):raise RuntimeError('D27 runtime plan changed')
            path=folder/'selected.pth';step=row['selected']['step'];digest=row['selected_checkpoint_sha256']
            if name=='D26_B0' and digest!='8c1b517311afa4188a01750b2d2edfd0fb84446d8062a65133fcfa3f0783ceee':raise RuntimeError('D26 B0 differs')
        path.relative_to(root)
        if not path.exists():missing.append(name);continue
        if sha(path)!=digest:raise RuntimeError('selected checkpoint checksum differs '+name)
        models[name]=dict(path=str(path),sha256=digest,step=step)
    return dict(models=models,missing=missing,test6_loaded=False,observed_at=now())
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--directory',type=Path,required=True);p.add_argument('--parent',type=Path,required=True);p.add_argument('--commit',required=True);p.add_argument('--resume-queue',action='store_true');a=p.parse_args()
    root=a.root.resolve();root.relative_to(Path('/home/jovyan/zzx'));base=a.directory.resolve();base.relative_to(root/'records');parent=a.parent.resolve();parent.relative_to(root/'records')
    if not base.name.startswith('research_d28_pressure_') or not parent.name.startswith('research_d27_safe_routing_repair_'):raise ValueError('unexpected experiment directories')
    base.mkdir(parents=True,exist_ok=True);import fcntl
    lock=(base/'controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    commit=subprocess.check_output(['git','-C',str(root),'rev-parse',a.commit+'^{commit}'],text=True).strip();code=base/'code'
    if a.resume_queue:
        plan=read(base/'plan.json')
        if plan['execution_commit']!=commit or plan['predecessor_directory']!=str(parent):raise RuntimeError('resume binding differs')
    else:
        if (base/'plan.json').exists() or code.exists():raise RuntimeError('existing directory requires resume')
        code.mkdir();design=json.loads(subprocess.check_output(['git','-C',str(root),'show',commit+':records/research_d28_pressure_plan_20261003/plan.json']))
        plan=dict(design=design['phases'][1],models=MODELS,execution_commit=commit,predecessor_directory=str(parent),test6_loaded=False,created_at=now())
        write(base/'plan.json',plan)
        (base/'execution_commit.txt').write_text(commit+'\n')
        for name in FILES:
            dest=code/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+name]))
    state=read(base/'queue_status.json') if (base/'queue_status.json').exists() else dict(jobs={n:dict(status='PENDING') for n in MODELS})
    state.update(status='WAITING_D27',controller_pid=os.getpid(),observed_at=now());write(base/'queue_status.json',state)
    while True:
        if (parent/'queue_status.json').exists():
            previous=read(parent/'queue_status.json');state.update(predecessor_status=previous.get('status'),predecessor_observed_at=previous.get('observed_at'))
            pid=previous.get('controller_pid');cmdline=Path('/proc')/str(pid)/'cmdline'
            if not terminal(previous) and (not cmdline.exists() or str(parent).encode() not in cmdline.read_bytes()):
                state.update(status='PREDECESSOR_CONTROLLER_STOPPED',observed_at=now());write(base/'queue_status.json',state);print('D28_PREDECESSOR_STOPPED inspect D27 logs; no duplicate restart',flush=True);return 2
            if terminal(previous):
                if released(parent):break
        state['observed_at']=now();write(base/'queue_status.json',state);print('D28_WAITING_D27',state.get('predecessor_status','STARTING'),flush=True);time.sleep(30)
    frozen=checkpoints(root,parent,plan)
    if frozen['missing']:
        state.update(status='WAITING_EVIDENCE',missing_checkpoints=frozen['missing'],observed_at=now());write(base/'queue_status.json',state);print('D28_WAITING_EVIDENCE',frozen['missing'],flush=True);return 2
    if (base/'checkpoint_binding.json').exists():
        if read(base/'checkpoint_binding.json')['models']!=frozen['models']:raise RuntimeError('resume checkpoints changed')
    else:write(base/'checkpoint_binding.json',frozen)
    inherited=read(parent/'code_manifest.json')
    if inherited['commit']!=commit:raise RuntimeError('D27 and D28 must use combined frozen commit')
    for name,digest in inherited['files'].items():
        source=parent/'code'/name
        if sha(source)!=digest:raise RuntimeError('D27 snapshot changed')
        dest=code/name
        if dest.exists():
            if sha(dest)!=digest:raise RuntimeError('source conflict')
        else:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(source.read_bytes())
    sources={str(x.relative_to(code)).replace('\\','/'):sha(x) for x in code.rglob('*') if x.is_file()}
    if (base/'code_manifest.json').exists() and read(base/'code_manifest.json')['files']!=sources:raise RuntimeError('resume source differs')
    write(base/'code_manifest.json',dict(commit=commit,inherited_D27_commit=inherited['commit'],inherited_D26_commit=inherited['inherited_commit'],files=sources))
    sys.path.insert(0,str(code/'scripts'));from launch_rebuild_v1_d27 import check_device
    uuids={int(line.split(',')[0]):line.split(',')[1].strip() for line in subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid','--format=csv,noheader'],text=True).splitlines()}
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(base/'temporary'),XDG_CACHE_HOME=str(base/'cache'),TORCH_HOME=str(base/'cache/torch'))
    for directory in ('temporary','cache/torch','logs','jobs'):(base/directory).mkdir(parents=True,exist_ok=True)
    active={};state['status']='RUNNING'
    for name,row in state['jobs'].items():
        if row.get('pid') and Path('/proc/'+str(row['pid'])+'/cmdline').exists() and str(base).encode() in Path('/proc/'+str(row['pid'])+'/cmdline').read_bytes():raise RuntimeError('existing worker alive')
        if (base/'jobs'/name/'complete.json').exists():row['status']='COMPLETE'
        elif row['status']=='RUNNING':row['status']='PENDING'
    while True:
        for gpu in (0,1):
            if gpu not in active:
                name=next((n for n in MODELS if state['jobs'][n]['status']=='PENDING'),None)
                if name:
                    try:check_device(gpu,uuids)
                    except RuntimeError as exc:print('D28_DEVICE_WAIT',gpu,str(exc),flush=True);continue
                    log=base/'logs'/(name+'_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log');handle=log.open('x')
                    cmd=[sys.executable,'-u','-B',str(code/'scripts/run_rebuild_v1_d28.py'),'--root',str(root),'--directory',str(base),'--model',name,'--gpu',str(gpu)]
                    process=subprocess.Popen(cmd,cwd=code,env=dict(env,CUDA_VISIBLE_DEVICES=str(gpu)),stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
                    active[gpu]=(name,process,handle);state['jobs'][name].update(status='RUNNING',gpu=gpu,pid=process.pid,log_path=str(log));print('D28_STARTED',gpu,name,process.pid,flush=True)
            if gpu in active:
                name,process,handle=active[gpu];progress=base/'jobs'/name/'progress.json'
                if progress.exists():state['jobs'][name]['progress']=read(progress)
                rc=process.poll()
                if rc is not None:
                    state['jobs'][name].update(status='COMPLETE' if rc==0 and (base/'jobs'/name/'complete.json').exists() else 'TECHNICAL_FAILURE',returncode=rc);handle.close();del active[gpu];print('D28_JOB_STATUS',name,state['jobs'][name]['status'],flush=True)
        state['observed_at']=now();write(base/'queue_status.json',state)
        if not active and not any(r['status']=='PENDING' for r in state['jobs'].values()):break
        time.sleep(5)
    state.update(status='COMPLETE' if all(r['status']=='COMPLETE' for r in state['jobs'].values()) else 'COMPLETE_WITH_TECHNICAL_FAILURES',observed_at=now());write(base/'queue_status.json',state)
    result=subprocess.run([sys.executable,'-B',str(code/'scripts/summarize_rebuild_v1_d28.py'),'--directory',str(base)],cwd=code,env=env)
    print('D28_QUEUE_FINISHED',state['status'],'summary_exit='+str(result.returncode),flush=True)
    return 0 if state['status']=='COMPLETE' and result.returncode==0 else 2
if __name__=='__main__':sys.exit(main())
