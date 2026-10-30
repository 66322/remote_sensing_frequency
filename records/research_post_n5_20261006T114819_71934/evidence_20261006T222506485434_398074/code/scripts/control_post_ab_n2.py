"""Wait for the original queue; run only four implemented matched N2 cells."""
import argparse,os,subprocess,sys,time
from datetime import datetime
from pathlib import Path
from post_ab_n2_common import read,write,sha,now,validate_plan,directories,predecessor_verdict,next_job,N2
from d30_common import live_owned,lock_free

def verified_parent(parent,plan):
    if sha(parent/'plan.json')!=plan['source_post_d30_plan_sha256']:raise RuntimeError('original plan changed')
    original=read(parent/'plan.json');screen=read(parent/'portfolio_screen.json')
    if screen['test6_loaded'] or screen.get('independent_final_loaded',False) or screen['completed_jobs']!=18:
        raise RuntimeError('predecessor final screen invalid')
    if screen['screens']['B3']['passed']:raise RuntimeError('unexpected B3 gate revision')
    completion={}
    for j in [f'A{i}' for i in range(6)]+[f'B{i}' for i in range(1,7)]+[f'C{i}' for i in range(6)]:
        folder=parent/'jobs'/j;record=read(folder/'complete.json')
        if record['global_step']!=8000 or record['signature']['execution_commit']!=original['execution_commit'] or record['signature']['plan_sha256']!=sha(parent/'plan.json') or record['test6_loaded']:
            raise RuntimeError('original job binding differs '+j)
        for tag in ('evaluation','fixed8000'):
            if sha(folder/tag/'summary.json')!=record[tag+'_summary_sha256']:raise RuntimeError('original summary SHA differs '+j)
        if sha(folder/'selected.pth')!=record['selected_checkpoint_sha256']:raise RuntimeError('original checkpoint changed '+j)
        completion[j]=sha(folder/'complete.json')
    return dict(directory=str(parent),queue_sha256=sha(parent/'queue_status.json'),plan_sha256=sha(parent/'plan.json'),screen_sha256=sha(parent/'portfolio_screen.json'),completion=completion,observed_at=now()),screen

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--directory',type=Path,required=True);a=p.parse_args()
    root,base=directories(a.root,a.directory);plan=read(base/'plan.json');validate_plan(plan);code=base/'code';parent=Path(plan['predecessor_directory'])
    import fcntl
    lock=(base/'controller.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    common=(root/'records/post_ab_successor.lock').open('a');fcntl.flock(common,fcntl.LOCK_EX|fcntl.LOCK_NB)
    state=read(base/'queue_status.json');state.update(controller_pid=os.getpid(),observed_at=now())
    active={}
    try:
        for name,digest in read(base/'code_manifest.json')['files'].items():
            if sha(code/name)!=digest:raise RuntimeError('execution snapshot changed '+name)
        for j,row in state['jobs'].items():
            if live_owned(row.get('pid',-1),base):raise RuntimeError('worker still live '+j)
            if row['status'] in ('TECHNICAL_FAILURE','TIMEOUT'):raise RuntimeError('worker needs explicit diagnosis '+j)
            if row['status']=='RUNNING':raise RuntimeError('interrupted worker needs explicit diagnosis '+j)
        state.update(status='CPU_VERIFYING');write(base/'queue_status.json',state)
        with (base/'cpu_checks.log').open('a') as log:
            subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(code/'tests'),'-p','test_post_ab_n2.py','-v'],cwd=code,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
        from post_d30_eval_compat import check_conditions
        from post_ab_n1_data import treatment
        print('POST_AB_CONDITIONS_PASS',len(check_conditions(plan,treatment)),flush=True)
        while True:
            previous=read(parent/'queue_status.json')
            workers=[r.get('pid',-1) for r in previous['jobs'].values() if live_owned(r.get('pid',-1),parent)]
            verdict=predecessor_verdict(previous,lock_free(parent),bool(workers),live_owned(previous.get('controller_pid',-1),parent))
            state.update(status=verdict,predecessor_status=previous['status'],predecessor_observed_at=previous.get('observed_at'),predecessor_live_workers=workers,observed_at=now())
            write(base/'queue_status.json',state);print('POST_AB_HANDOVER',verdict,previous['status'],flush=True)
            if verdict=='READY':break
            if verdict.startswith('HOLD'):return 2
            time.sleep(30)
        source=Path(plan['source_N1_directory'])
        if live_owned(read(source/'queue_status.json').get('controller_pid',-1),source) or not lock_free(source):raise RuntimeError('N1 source still active')
        if sha(source/'plan.json')!=plan['source_N1_plan_sha256']:raise RuntimeError('N1 plan changed')
        if sha(source/'jobs/N1-2/selected.pth')!=plan['jobs'][0]['initial_checkpoint_sha256']:raise RuntimeError('N1-2 base changed')
        binding,screen=verified_parent(parent,plan);write(base/'predecessor_binding.json',binding)
        write(base/'e0_diagnostic.json',dict(source='original portfolio_screen.json; derived count reports, not a new spatial audit',binding=binding,
              jobs={j:screen['jobs'][j] for j in ('A0','A2','A3','B1','B3','B4','C0','C1','C2','C3')},
              spatial_predictions_read=False,gradient_exposure_observed=False,test6_loaded=False,observed_at=now()))
        state['evaluations']['E0']='COMPLETE_DERIVED_REPORT_ONLY'
        state['original_C2_gate']=screen['screens']['C2']['passed']
        state['source_N1_directory']=plan['source_N1_directory']
        (base/'logs').mkdir(exist_ok=True)
        from launch_rebuild_v1_d27 import check_device
        uuids={int(x.split(',')[0]):x.split(',')[1].strip() for x in subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid','--format=csv,noheader'],text=True).splitlines()}
        if 0 not in uuids or 1 not in uuids:raise RuntimeError('authorized GPU0/1 absent')
        env=dict(os.environ);env.pop('CUDA_VISIBLE_DEVICES',None);state['gpu_uuids']={str(g):uuids[g] for g in (0,1)}
        state.update(status='RUNNING_N2',phase='N2');write(base/'queue_status.json',state)
        while True:
            for gpu in (0,1):
                failed=any(state['jobs'][j]['status'] in ('TECHNICAL_FAILURE','TIMEOUT') for j in N2)
                if gpu not in active and not failed:
                    j=next_job(state,gpu)
                    if j:
                        try:check_device(gpu,uuids)
                        except RuntimeError as exc:
                            state['jobs'][j]['device_wait']=str(exc);continue
                        if (base/'jobs'/j/'last_train_state.pth').exists():raise RuntimeError('existing training checkpoint requires explicit diagnosis '+j)
                        path=base/'logs'/(j+'_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log');handle=path.open('x')
                        command=[sys.executable,'-u','-B',str(code/'scripts/run_post_ab_n2.py'),'--root',str(root),'--directory',str(base),'--job',j,'--gpu',str(gpu)]
                        proc=subprocess.Popen(command,cwd=code,env=dict(env,CUDA_VISIBLE_DEVICES=str(gpu)),stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
                        active[gpu]=(j,proc,handle);state['jobs'][j].update(status='RUNNING',pid=proc.pid,log_path=str(path),started_at=now())
                        print('POST_AB_START',gpu,j,proc.pid,flush=True)
                if gpu in active:
                    j,proc,handle=active[gpu];progress=base/'jobs'/j/'progress.json'
                    if progress.exists():state['jobs'][j]['progress']=read(progress)
                    if proc.poll() is None and not state['jobs'][j].get('timed_out',False) and (datetime.now().astimezone()-datetime.fromisoformat(state['jobs'][j]['started_at'])).total_seconds()>3600*plan['runtime']['per_job_timeout_hours']:
                        proc.terminate();state['jobs'][j]['timed_out']=True
                    rc=proc.poll()
                    if rc is not None:
                        done=base/'jobs'/j/'complete.json'
                        if rc==0 and done.exists():
                            r=read(done)
                            if r['global_step']!=8000 or r['signature']['execution_commit']!=plan['execution_commit'] or r['signature']['plan_sha256']!=sha(base/'plan.json'):raise RuntimeError('new completion binding differs')
                            status='COMPLETE'
                        else:status='TIMEOUT' if state['jobs'][j].get('timed_out',False) else 'TECHNICAL_FAILURE'
                        state['jobs'][j].update(status=status,returncode=rc,completed_at=now());handle.close();del active[gpu]
                        print('POST_AB_JOB',j,status,flush=True)
            state['observed_at']=now();write(base/'queue_status.json',state)
            if not active:
                if any(state['jobs'][j]['status'] in ('TECHNICAL_FAILURE','TIMEOUT') for j in N2):
                    state.update(status='HOLD_N2_TECHNICAL_FAILURE');write(base/'queue_status.json',state);return 2
                if all(state['jobs'][j]['status']=='COMPLETE' for j in N2):break
            time.sleep(5)
        subprocess.run([sys.executable,'-B',str(code/'scripts/summarize_post_ab_n2.py'),'--directory',str(base)],cwd=code,env=env,check=True)
        result=read(base/'n2_screen.json')
        state.update(status='N2_COMPLETE_AWAITING_STAGE_PROTOCOL',n2_passed=result['passed'],next_matched_base='N1-2',observed_at=now())
        write(base/'queue_status.json',state)
        print('POST_AB_N2_COMPLETE_UPLOAD_AND_REVIEW',base,'remaining reservations are not runnable placeholders',flush=True)
        return 0
    except BaseException:
        state.update(status='CONTROLLER_INTERRUPTED',observed_at=now(),error='diagnose before resume; detached workers may still be alive')
        write(base/'queue_status.json',state);raise
    finally:
        for _,_,handle in active.values():handle.close()
if __name__=='__main__':sys.exit(main())
