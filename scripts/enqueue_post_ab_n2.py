"""Idempotent N2 activation after the audited N1 handover; no old queue restart."""
import argparse,datetime,fcntl,json,os,subprocess,sys
from pathlib import Path
FILES=['model/post_ab_n2_relation.py','model/rebuild_v1_post_ab_n2.py','scripts/post_ab_n2_common.py',
 'scripts/run_post_ab_n2.py','scripts/post_ab_n2_recovery.py','scripts/control_post_ab_n2.py','scripts/summarize_post_ab_n2.py',
 'scripts/enqueue_post_ab_n2.py','scripts/upload_post_ab_n2_records.py','tests/test_post_ab_n2.py','docs/protocols/POST_AB_N2_EXECUTION_20261005.md']
SOURCE='research_post_ab_followup_20261004T185950_3029215'
EXPECTED_N1_COMMIT='99acf754aaf3f6b1d119f42a5dab7297a263e4b4'
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--commit',required=True);a=p.parse_args()
    root=a.root.resolve();root.relative_to(Path('/home/jovyan/zzx'));records=root/'records';source=records/SOURCE
    sys.path.insert(0,str(source/'code/scripts'))
    from post_ab_queue_common import read,write,sha
    from d30_common import live_owned,lock_free
    with (records/'post_ab_n2_registration.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        existing=sorted(p for p in records.glob('research_post_ab_followup_n2_*') if (p/'plan.json').exists())
        if existing:
            for b in existing:print('POST_AB_N2_ALREADY_REGISTERED',b,read(b/'queue_status.json')['status'],flush=True)
            return 0
        state=read(source/'queue_status.json');plan=read(source/'plan.json');manifest=read(source/'code_manifest.json')
        if state['status']!='N1_COMPLETE_AWAITING_STAGE_PROTOCOL' or any(state['jobs'][f'N1-{i}']['status']!='COMPLETE' for i in range(4)):raise RuntimeError('N1 handover incomplete')
        if live_owned(state.get('controller_pid',-1),source) or not lock_free(source):raise RuntimeError('N1 controller not released')
        if any(live_owned(x.get('pid',-1),source) for x in state['jobs'].values()):raise RuntimeError('source worker active')
        if plan['execution_commit']!=EXPECTED_N1_COMMIT or manifest['commit']!=EXPECTED_N1_COMMIT:raise RuntimeError('N1 execution differs')
        screen=read(source/'n1_screen.json')
        if screen['passed'] or screen['baseline_for_reserved_N2']!='N1-2' or state['next_matched_base']!='N1-2':raise RuntimeError('unexpected frozen base decision')
        if any(state['jobs'][f'N6-{i}']['status']!='SKIPPED_GATE' for i in range(3)):raise RuntimeError('unexpected C gate revision')
        for i in range(4):
            b=source/'jobs'/f'N1-{i}';c=read(b/'complete.json')
            if c['global_step']!=8000 or c['signature']['plan_sha256']!=sha(source/'plan.json') or c['signature']['execution_commit']!=EXPECTED_N1_COMMIT or c['test6_loaded']:raise RuntimeError('source completion differs')
            for tag in ('evaluation','fixed8000'):
                if sha(b/tag/'summary.json')!=c[tag+'_summary_sha256']:raise RuntimeError('source summary changed')
        commit=subprocess.check_output(['git','-C',str(root),'rev-parse',a.commit+'^{commit}'],text=True).strip()
        base=records/('research_post_ab_followup_n2_'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()))
        base.mkdir();code=base/'code'
        for name,digest in manifest['files'].items():
            src=source/'code'/name
            if sha(src)!=digest:raise RuntimeError('source immutable code changed '+name)
            dst=code/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes())
        for name in FILES:
            dst=code/name;dst.parent.mkdir(parents=True,exist_ok=True)
            dst.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+name]))
        sys.path.insert(0,str(code/'scripts'))
        from post_ab_n2_common import runtime_plan,validate_plan,initial_state,N1_PLAN_SHA,BASE_SHA
        if sha(source/'plan.json')!=N1_PLAN_SHA or sha(source/'jobs/N1-2/selected.pth')!=BASE_SHA:raise RuntimeError('audited base binding changed')
        new=runtime_plan(plan,commit,base);new['created_at']=datetime.datetime.now().astimezone().isoformat();validate_plan(new)
        write(base/'plan.json',new);(base/'execution_commit.txt').write_text(commit+'\n')
        write(base/'code_manifest.json',dict(commit=commit,inherited_commit=EXPECTED_N1_COMMIT,
            files={p.relative_to(code).as_posix():sha(p) for p in code.rglob('*') if p.is_file()}))
        write(base/'queue_status.json',initial_state(new))
        write(base/'n1_base_binding.json',dict(source_directory=str(source),source_plan_sha256=N1_PLAN_SHA,
            source_screen_sha256=sha(source/'n1_screen.json'),selected_checkpoint_sha256=BASE_SHA,
            completion_sha256={f'N1-{i}':sha(source/'jobs'/f'N1-{i}'/'complete.json') for i in range(4)}))
        for d in ['temporary','cache/torch','logs']:(base/d).mkdir(parents=True,exist_ok=True)
        env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
            PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(base/'temporary'),XDG_CACHE_HOME=str(base/'cache'),TORCH_HOME=str(base/'cache/torch'))
        env['PYTHONPATH']=os.pathsep.join([str(code),str(code/'scripts')])
        log=base/('nohup_'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log')
        cmd=[sys.executable,'-u','-B',str(code/'scripts/control_post_ab_n2.py'),'--root',str(root),'--directory',str(base)]
        with log.open('x') as h:
            proc=subprocess.Popen(['nohup',*cmd],cwd=code,env=env,stdin=subprocess.DEVNULL,stdout=h,stderr=subprocess.STDOUT,start_new_session=True)
        write(base/'launch.json',dict(controller_pid=proc.pid,controller_command=cmd,controller_log=str(log)))
        (base/'controller.pid').write_text(str(proc.pid)+'\n')
        print('POST_AB_N2_QUEUE_REGISTERED',base,'PID='+str(proc.pid),'EXECUTABLE=6',flush=True)
        print('POST_AB_N2_LOG',log,flush=True)
    return 0
if __name__=='__main__':sys.exit(main())

