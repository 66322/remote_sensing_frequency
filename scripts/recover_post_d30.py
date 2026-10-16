"""Create immutable repair overlay, then resume existing queue without A retraining."""
import argparse,json,os,subprocess,sys
from pathlib import Path
from datetime import datetime
FILES=['scripts/post_d30_eval_compat.py','scripts/run_post_d30_repaired.py','scripts/status_post_d30.py','tests/test_post_d30_repair.py']
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--commit',required=True);a=ap.parse_args()
    root=a.root.resolve();root.relative_to(Path('/home/jovyan/zzx'));base=a.directory.resolve();base.relative_to(root/'records')
    if base.name!='research_post_d30_mechanisms_20261004T000812_2446364':raise ValueError('repair bound to this original run')
    sys.path[:0]=[str(base/'code/scripts'),str(base/'code')]
    from d30_common import live_owned,lock_free
    from d24_common import read,write,sha
    state=read(base/'queue_status.json');plan=read(base/'plan.json');original=read(base/'code_manifest.json')
    if plan['execution_commit']!='01ec8dee82f7e272f6a650aaf9f3e619a0e7c516':raise RuntimeError('execution differs')
    if live_owned(state.get('controller_pid',-1),base) or any(live_owned(r.get('pid',-1),base) for r in state['jobs'].values()) or not lock_free(base):raise RuntimeError('original controller/worker still active; nothing changed')
    if any(j.startswith(('B','C','F')) and r['status'] not in ('PENDING','COMPLETE','SKIPPED_GATE') for j,r in state['jobs'].items()):raise RuntimeError('unknown later-phase error requires diagnosis')
    for name,digest in original['files'].items():
        if sha(base/'code'/name)!=digest:raise RuntimeError('original source snapshot changed')
    commit=subprocess.check_output(['git','-C',str(root),'rev-parse',a.commit+'^{commit}'],text=True).strip()
    repair=base/('evaluation_repair_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'_'+str(os.getpid()));repair.mkdir()
    for name in FILES:
        dest=repair/Path(name).name;dest.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+name]))
    sys.path.insert(0,str(repair));from post_d30_eval_compat import ORIGINAL,check_conditions,repairable_row,transform_controller
    for j,row in state['jobs'].items():
        if row['status'] in ('TECHNICAL_FAILURE','TIMEOUT'):repairable_row(j,row,base)
    from post_d30_data import treatment
    names=check_conditions(plan,treatment)
    write(repair/'queue_before_repair.json',state)
    controller=transform_controller((base/'code/scripts/launch_post_d30.py').read_text(),repair/'run_post_d30_repaired.py')
    (repair/'controller_transformed.py').write_text(controller)
    write(repair/'repair_manifest.json',dict(repair_commit=commit,original_execution_commit=ORIGINAL,original_plan_sha256=sha(base/'plan.json'),
      original_code_manifest_sha256=sha(base/'code_manifest.json'),original_controller_pid=state.get('controller_pid'),diagnosed_error='ValueError: dsm_present_zero; subsequent summary subprocess missing model import root',
      files={p.name:sha(p) for p in repair.iterdir() if p.is_file()},condition_interface_checked=names,
      training_changes=False,A_optimizer_updates=0,original_snapshots_preserved=True,subprocess_pythonpath=[str(base/'code'),str(base/'code/scripts')],scope='evaluation compatibility, worker dispatch, and immutable snapshot import roots; original signatures preserved with additional explicit overlay binding'))
    os.environ['POST_D30_REPAIR_DIRECTORY']=str(repair)
    # Child scripts get their own sys.path; cwd=code alone does not expose model/.
    os.environ['PYTHONPATH']=os.pathsep.join((str(base/'code'),str(base/'code/scripts')))
    env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',POST_D30_BASE=str(base))
    with (repair/'cpu_checks.log').open('w') as log:
        subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(repair),'-p','test_post_d30_repair.py','-v'],cwd=repair,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,check=True)
    print('PORTFOLIO_SUMMARY_IMPORT_PASS',flush=True)
    print('PORTFOLIO_REPAIR_CHECKS_PASS','runtime_conditions='+str(len(names)),repair,flush=True)
    sys.argv=[str(repair/'controller_transformed.py'),'--root',str(root),'--directory',str(base),'--commit',ORIGINAL,'--resume-queue']
    namespace=dict(__name__='__main__',__file__=str(repair/'controller_transformed.py'),repairable_row=repairable_row)
    exec(compile(controller,str(repair/'controller_transformed.py'),'exec'),namespace)
if __name__=='__main__':main()
