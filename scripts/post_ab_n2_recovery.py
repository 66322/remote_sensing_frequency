"""Controller-only recovery. Never restart a dispatched worker or alter its plan."""
import hashlib,json,math,os,signal
from pathlib import Path

def timeout_hours(value):
    if value is None:return 8.0
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:
        raise ValueError('invalid per_job_timeout_hours')
    return float(value)

def read(path):return json.loads(Path(path).read_text())
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def process_identity(pid,base,job,gpu):
    """Return kernel start tick for the exact immutable worker, None if exited."""
    p=Path('/proc')/str(pid)
    try:
        args=(p/'cmdline').read_bytes().decode().strip('\0').split('\0')
        stat=(p/'stat').read_text().rsplit(')',1)[1].split()
    except FileNotFoundError:return None
    if not args[0] or stat[0]=='Z':return None
    script=str(Path(base)/'code/scripts/run_post_ab_n2.py')
    expected=[script,'--root',str(Path(base).parent.parent),'--directory',str(base),'--job',job,'--gpu',str(gpu)]
    if not any(args[i:i+len(expected)]==expected for i in range(len(args))):
        raise RuntimeError('PID ownership mismatch '+str(pid)+' '+job)
    return stat[19]  # /proc stat field22, starttime; prevents PID reuse.

def verify_complete(base,job,plan):
    folder=Path(base)/'jobs'/job;c=read(folder/'complete.json')
    if c['global_step']!=8000 or c['signature']['execution_commit']!=plan['execution_commit'] or c['signature']['plan_sha256']!=sha(Path(base)/'plan.json') or c.get('test6_loaded',True) or c.get('independent_final_loaded',True):
        raise RuntimeError('completion binding differs '+job)
    for tag in ('evaluation','fixed8000'):
        if sha(folder/tag/'summary.json')!=c[tag+'_summary_sha256']:raise RuntimeError('summary changed '+job)
    if sha(folder/'selected.pth')!=c['selected_checkpoint_sha256'] or sha(folder/'last_train_state.pth')!=c['last_checkpoint_sha256']:
        raise RuntimeError('checkpoint changed '+job)
    return c

class AdoptedWorker:
    def __init__(self,pid,base,job,gpu,plan,identity):
        self.pid=pid;self.base=base;self.job=job;self.gpu=gpu;self.plan=plan;self.identity=identity;self.rc=None
    def poll(self):
        if self.rc is not None:return self.rc
        current=process_identity(self.pid,self.base,self.job,self.gpu)
        if current is not None:
            if current!=self.identity:raise RuntimeError('PID reused '+self.job)
            return None
        if (Path(self.base)/'jobs'/self.job/'complete.json').exists():
            verify_complete(self.base,self.job,self.plan);self.rc=0
        else:self.rc=2
        return self.rc
    def terminate(self):
        # Linux pidfd pins the target process, preventing a recycled PID signal.
        fd=os.pidfd_open(self.pid)
        try:
            if process_identity(self.pid,self.base,self.job,self.gpu)!=self.identity:raise RuntimeError('worker exited or PID reused')
            signal.pidfd_send_signal(fd,signal.SIGTERM)
        finally:os.close(fd)

def reconcile(base,plan,state,identity=process_identity):
    """Validate everything before mutating state; return adoptions/completed IDs."""
    active={};completed=[]
    for job,row in state['jobs'].items():
        status=row['status'];gpu=row['gpu'];pid=row.get('pid',-1)
        if status in ('TECHNICAL_FAILURE','TIMEOUT'):raise RuntimeError('diagnosis required '+job)
        if status=='RUNNING':
            tick=identity(pid,base,job,gpu)
            if tick is not None:
                if gpu in active:raise RuntimeError('multiple workers on GPU'+str(gpu))
                if not row.get('started_at'):raise RuntimeError('missing worker start time '+job)
                active[gpu]=AdoptedWorker(pid,base,job,gpu,plan,tick)
            elif (Path(base)/'jobs'/job/'complete.json').exists():
                verify_complete(base,job,plan);completed.append(job)
            else:raise RuntimeError('dispatched worker exited without valid completion; no automatic retry '+job)
        elif status=='COMPLETE':verify_complete(base,job,plan)
        elif status=='PENDING':
            folder=Path(base)/'jobs'/job
            if pid>0 or (folder.exists() and any(folder.iterdir())):raise RuntimeError('pending job has execution evidence '+job)
        else:raise RuntimeError('unexpected job state '+job+' '+status)
    return active,completed

def unknown_workers(base,known):
    """Detect dispatch-before-status crash windows, rather than duplicate them."""
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:args=(p/'cmdline').read_bytes().split(b'\0')
        except (FileNotFoundError,PermissionError):continue
        if str(Path(base)/'code/scripts/run_post_ab_n2.py').encode() in args and str(base).encode() in args and int(p.name) not in known:
            raise RuntimeError('unregistered worker found '+p.name+'; diagnosis required')
