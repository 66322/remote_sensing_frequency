"""One detached bootstrap, two independent experiment directories, no D29."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from datetime import datetime
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--commit',required=True);p.add_argument('--directory',type=Path,required=True);a=p.parse_args()
    root=a.root.resolve();root.relative_to(Path('/home/jovyan/zzx'));bundle=a.directory.resolve();bundle.relative_to(root/'records')
    if not bundle.name.startswith('research_d27_d28_linked_'):raise ValueError('unexpected bundle directory')
    if (bundle/'linked_execution.json').exists():raise RuntimeError('already launched; inspect recorded controllers, do not duplicate')
    bundle.mkdir(parents=True,exist_ok=True);commit=subprocess.check_output(['git','-C',str(root),'rev-parse',a.commit+'^{commit}'],text=True).strip()
    for command in Path('/proc').glob('[0-9]*/cmdline'):
        try:raw=command.read_bytes()
        except (OSError,PermissionError):continue
        if str(root).encode() in raw and b'--parent' in raw and (b'research_d27_safe_routing_repair_' in raw or b'research_d28_pressure_' in raw):raise RuntimeError('another linked controller is alive; inspect its status instead of starting a duplicate')
    stamp=datetime.now().strftime('%Y%m%dT%H%M%S%f')+'_'+str(os.getpid());d27=root/'records'/('research_d27_safe_routing_repair_'+stamp);d28=root/'records'/('research_d28_pressure_'+stamp);parent=root/'records/research_d26_bidirectional_20261002T191253_1513109'
    if not (parent/'queue_status.json').exists():raise RuntimeError('known completed D26 directory absent')
    execution=dict(commit=commit,D26=str(parent),D27=str(d27),D28=str(d28),GPUs=[0,1],D29_queued=False,created_at=datetime.now().astimezone().isoformat(),controllers={})
    def persist():
        t=bundle/'linked_execution.tmp';t.write_text(json.dumps(execution,indent=2)+'\n');os.replace(t,bundle/'linked_execution.json')
    persist()
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(bundle/'temporary'),XDG_CACHE_HOME=str(bundle/'cache'));(bundle/'temporary').mkdir();(bundle/'cache').mkdir()
    for round_,base,previous in ((27,d27,parent),(28,d28,d27)):
        base.mkdir();name=f'scripts/launch_rebuild_v1_d{round_}.py';target=base/'launch.py';target.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+name]));log=base/'nohup.log'
        with log.open('x') as handle:
            process=subprocess.Popen([sys.executable,'-u','-B',str(target),'--root',str(root),'--directory',str(base),'--parent',str(previous),'--commit',commit],cwd=root,env=env,stdout=handle,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
        (base/'controller.pid').write_text(str(process.pid)+'\n');execution['controllers'][str(round_)]=dict(pid=process.pid,log=str(log));persist();print('LINKED_CONTROLLER_STARTED',round_,process.pid,str(base),flush=True)
        # Startup acknowledgement is bounded and not a resource/performance audit.
        for _ in range(60):
            if process.poll() is not None:raise RuntimeError(f'D{round_} controller exited: inspect {log}')
            if (base/'queue_status.json').exists():break
            time.sleep(1)
        else:raise RuntimeError(f'D{round_} has no startup state yet; inspect {log}, do not relaunch')
    print('D27_D28_LINKED_EXECUTION',str(bundle/'linked_execution.json'),flush=True)
if __name__=='__main__':main()
