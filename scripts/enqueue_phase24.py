"""User-executed one-time registration. An existing queue is queried, never repeated."""
import argparse, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path
from datetime import datetime,timezone,timedelta

FILES=['scripts/'+n+'.py' for n in ('phase24_common','phase24_numeric','phase24_fit','phase24_model',
 'phase24_ipc','phase24_runtime','prepare_phase24','phase24_analysis','control_phase24',
 'enqueue_phase24','status_phase24','verify_phase24_results','upload_phase24')]
FILES+=['tests/test_phase24.py','docs/protocols/PHASE_24_EXECUTION_20261014.md','docs/protocols/PHASE_24_IPC_PATH_FIX_20261014.md']
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()

def ipc_path_replacement_guard(directory):
 """Explicit one-time replacement of the observed zero-update registration defect."""
 d=Path(directory);expected='15fdfa4c64c4c50b631707a6d92de98642011bab'
 if d.name!='research_phase24_protected_20261014T185408_2127460':raise RuntimeError('not the observed IPC-path registration failure')
 plan=read(d/'plan.json');code=read(d/'code_manifest.json');seal=read(d/'registration.json')
 if plan['execution_commit']!=expected or code['commit']!=expected:raise RuntimeError('unexpected failed execution version')
 contract=dict(gpus=[0,1],seed=42,max_head_updates=32000,head_updates=8000,automatic_retry=False,new_seeds=False,
  test6_loaded=False,held4_loaded=False,wall_deadline_hours=None)
 if any(plan.get(n)!=v for n,v in contract.items()):raise RuntimeError('failed scientific contract differs')
 if seal['binding']!={n:sha(d/n) for n in ('plan.json','code_manifest.json')}:raise RuntimeError('failed registration binding changed')
 for n,h in code['files'].items():
  f=(d/'code'/n).resolve();f.relative_to((d/'code').resolve())
  if sha(f)!=h:raise RuntimeError('failed immutable snapshot changed: '+n)
 for n in ('launch.json','queue_status.json','smoke_pass.json','registration_cpu_checks.json','summary.json'):
  if (d/n).exists():raise RuntimeError('post-registration evidence exists; refuse replacement')
 if list((d/'jobs').rglob('*')) or list((d/'smoke').rglob('*')) or list(d.glob('nohup_*.log')) or list(d.rglob('*.pth')):
  raise RuntimeError('scientific execution artifact exists; refuse replacement')
 failure=read(d/'registration_failure.json');log=(d/'cpu_checks.log').read_text()
 if failure.get('automatic_retry') is not False or 'test_phase24.py' not in failure['error']:raise RuntimeError('unexpected registration failure')
 tests=re.findall(r'^(test_\w+) \(.+\) \.\.\. (ok|ERROR|FAIL)',log,re.MULTILINE)
 bad={name for name,status in tests if status!='ok'}
 if len(tests)!=20 or len(set(n for n,_ in tests))!=20 or bad!={'test_cross_process_readonly','test_roundtrip_and_last_close'}:
  raise RuntimeError('only the two observed IPC tests may be replaced')
 if sum(status=='ok' for _,status in tests)!=18 or log.count('OSError: AF_UNIX path too long')!=2 or 'FAILED (errors=2)' not in log:
  raise RuntimeError('IPC path defect not proven; preserve failure')
 return dict(directory=str(d),execution_commit=expected,plan_sha256=sha(d/'plan.json'),code_sha256=sha(d/'code_manifest.json'),
  cpu_checks_sha256=sha(d/'cpu_checks.log'),registration_failure_sha256=sha(d/'registration_failure.json'),
  optimizer_updates=0,controller_launched=False,reason='explicit Linux abstract AF_UNIX path compatibility replacement')

def existing_status(d):
 state=read(d/'queue_status.json').get('status') if (d/'queue_status.json').exists() else 'REGISTRATION_FAILURE_HOLD'
 print('PHASE24_ALREADY_REGISTERED',d,state)
 if (d/'queue_status.json').exists() and (d/'code/scripts/status_phase24.py').exists():
  subprocess.run([sys.executable,'-B',str(d/'code/scripts/status_phase24.py'),'--directory',str(d)],check=True)
 elif (d/'registration_failure.json').exists():print('REGISTRATION_FAILURE',read(d/'registration_failure.json'))
def main():
 a=argparse.ArgumentParser();a.add_argument('--root',type=Path,required=True);a.add_argument('--commit',required=True)
 a.add_argument('--replace-ipc-path-bug-directory',type=Path)
 x=a.parse_args();root=x.root.resolve();root.relative_to(Path('/home/jovyan/zzx').resolve())
 if not re.fullmatch('[0-9a-f]{40}',x.commit):raise ValueError('full immutable commit required')
 import fcntl
 records=root/'records'
 with (records/'phase24_registration.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  existing=sorted(records.glob('research_phase24_protected_*'))
  replacement=None;failed=None
  if x.replace_ipc_path_bug_directory is not None:
   failed=x.replace_ipc_path_bug_directory.resolve();failed.relative_to(records)
   marker=failed/'replacement_registered.json'
   if marker.exists():
    target=Path(read(marker)['directory']).resolve();target.relative_to(records)
    if not target.exists():raise RuntimeError('replacement marker points to absent directory; preserve and inspect')
    existing_status(target);return
   if existing!=[failed]:raise RuntimeError('replacement requires exactly the original failed registration and no other queue')
   replacement=ipc_path_replacement_guard(failed)
   for proc in Path('/proc').iterdir():
    if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
    try:cmd=(proc/'cmdline').read_bytes()
    except (FileNotFoundError,PermissionError):continue
    if str(failed).encode() in cmd:raise RuntimeError('failed registration still owns live process '+proc.name)
   existing=[]
  if existing:
   for d in existing:existing_status(d)
   return
  old=records/'research_phase2_matched_20261013T151120_1310582'
  # Predecessor process and GPU admission happen before registering any new job.
  state=read(old/'queue_status.json')
  if state['status']!='PHASE2_COMPLETE_AWAITING_REVIEW':raise RuntimeError('original Phase2 not complete')
  with (old/'controller.lock').open('a') as oldlock:fcntl.flock(oldlock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  for proc in Path('/proc').iterdir():
   if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
   try:cmd=(proc/'cmdline').read_bytes()
   except (FileNotFoundError,PermissionError):continue
   if str(old/'code/scripts/control_phase2.py').encode() in cmd or str(old/'code/scripts/phase2_train.py').encode() in cmd:
    raise RuntimeError('original scientific worker remains live')
  gpu=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.free','--format=csv,noheader,nounits'],text=True)
  selected={}
  for line in gpu.splitlines():
   row=[v.strip() for v in line.split(',')]
   if int(row[0]) in (0,1):selected[int(row[0])]=row
  if set(selected)!={0,1}:raise RuntimeError('GPU0 and GPU1 required')
  apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader,nounits'],text=True)
  if any(float(v[-1])<24000 for v in selected.values()) or any(v[1] in apps for v in selected.values()):
   print('PHASE24_NOT_REGISTERED_GPU_BUSY; release external workload before running this registrar again');return
  commit=subprocess.check_output(['git','-C',str(root),'rev-parse',x.commit+'^{commit}'],text=True).strip()
  if commit!=x.commit:raise RuntimeError('commit differs')
  base=records/('research_phase24_protected_'+datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+str(os.getpid()));base.mkdir()
  if replacement:
   (failed/'replacement_registered.json').write_text(json.dumps(dict(directory=str(base),commit=commit,
    reason=replacement['reason'],attempted_at=datetime.now(timezone(timedelta(hours=8))).isoformat()))+'\n')
   print('PHASE24_TECHNICAL_REPLACEMENT_OF',failed)
  code=base/'code'
  try:
   for n,h in read(old/'code_manifest.json')['files'].items():
    source=(old/'code'/n).resolve();source.relative_to((old/'code').resolve())
    if sha(source)!=h:raise RuntimeError('immutable inherited code changed: '+n)
    target=code/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
   for n in FILES:
    target=code/n;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(subprocess.check_output(['git','-C',str(root),'show',commit+':'+n]))
   sys.path.insert(0,str(code/'scripts'))
   from phase24_common import write,env,FIT,VAL,now,binding
   from prepare_phase24 import source_guard
   source_guard(old)
   from phase24_common import original_counts
   ordinary=[];condition_sources=[]
   for f in sorted((old/'evaluation/average_16000').glob('*/counts.json')):
    c=read(f)['case']
    if c['panel']=='ordinary':
     original_counts(old,c);ordinary.append(c['damage']);condition_sources.append(dict(path=str(f),sha256=sha(f)))
   conditions=['clean']+sorted(set(ordinary))
   from phase24_common import panel
   panel(conditions)
   write(base/'plan.json',dict(root=str(root),previous=str(old),execution_commit=commit,fit12=FIT,val2=VAL,
    gpus=[0,1],seed=42,max_head_updates=32000,max_trainings=4,head_updates=8000,
    automatic_retry=False,new_seeds=False,test6_loaded=False,held4_loaded=False,wall_deadline_hours=None,
    fixed_conditions=conditions,condition_source=condition_sources,
    input_cache='read-only shared RAM',pixel_array_disk_cache=False,registered_at=now()))
   if replacement:
    plan=read(base/'plan.json');plan['technical_replacement_of']=replacement;write(base/'plan.json',plan)
    write(base/'technical_replacement.json',replacement)
   write(base/'code_manifest.json',dict(commit=commit,files={f.relative_to(code).as_posix():sha(f) for f in code.rglob('*') if f.is_file()}))
   write(base/'registration.json',dict(binding=binding(base),registered_at=now()))
   for n in ('logs','temporary','cache/torch','cache/cuda','cache/triton','cache/kernels','jobs','smoke','analysis','results','fits'):(base/n).mkdir(parents=True,exist_ok=True)
   with (base/'cpu_checks.log').open('x') as log:
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(code/'tests'),'-p','test_phase24.py','-v'],
     cwd=code,env=env(base),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
   if 'skipped' in (base/'cpu_checks.log').read_text():raise RuntimeError('all Linux registration checks must execute')
   write(base/'registration_cpu_checks.json',dict(passed=True,log_sha256=sha(base/'cpu_checks.log'),optimizer_updates=0,
    CUDA_VISIBLE_DEVICES='',Linux_transport_checked=True,observed_at=now()))
   write(base/'queue_status.json',dict(status='REGISTERED',workers={},observed_at=now()))
   logpath=base/('nohup_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.log')
   with logpath.open('x') as log:
    proc=subprocess.Popen([sys.executable,'-u','-B',str(code/'scripts/control_phase24.py'),'--directory',str(base)],
     cwd=code,env=env(base),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   write(base/'launch.json',dict(controller_pid=proc.pid,log=str(logpath),observed_at=now()))
   print('PHASE24_REGISTERED',base,'PID='+str(proc.pid),'GPU=0,1 CORE_HEADS=1 MAX_HEADS=4 MAX_UPDATES=32000 NO24H_DEADLINE')
   print('PHASE24_LOG',logpath)
   print('PHASE24_STATUS',sys.executable,'-B',code/'scripts/status_phase24.py','--directory',base)
  except BaseException as exc:
   (base/'registration_failure.json').write_text(json.dumps(dict(error=str(exc),automatic_retry=False))+'\n')
   raise
if __name__=='__main__':main()
