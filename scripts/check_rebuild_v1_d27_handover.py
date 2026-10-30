"""Read-only controller liveness and predecessor handover, no GPU/resource probe."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path

DEFAULT=Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d27_safe_routing_after_d26_20261002T191253_1513109')
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def process_state(stat):return stat.rsplit(')',1)[1].split()[0]
def alive(pid,base):
    try:
        proc=Path('/proc')/str(int(pid))
        return process_state((proc/'stat').read_text()) not in ('Z','X') and str(base).encode() in (proc/'cmdline').read_bytes()
    except (OSError,ValueError,IndexError,TypeError):return False
def lock_free(path):
    if not path.is_file():return None
    import fcntl
    with path.open('r') as handle:
        try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return False
        else:fcntl.flock(handle,fcntl.LOCK_UN);return True
def terminal(state):
    rows=state.get('jobs',{})
    return state.get('status') in ('COMPLETE','COMPLETE_WITH_TECHNICAL_FAILURES') and len(rows)==9 and all(r.get('status') in ('COMPLETE','TECHNICAL_FAILURE','TIMEOUT') for r in rows.values())
def classify(status,live,age,parent_done,parent_free,workers):
    if status in ('COMPLETE','COMPLETE_WITH_TECHNICAL_FAILURES'):return 'QUEUE_FINISHED'
    if not live:return 'CONTROLLER_DEAD_WORKERS_STILL_RUNNING' if workers else 'NOT_ACTIVE_CONTROLLER_DEAD'
    if age is None or age>180:return 'CONTROLLER_LIVE_HEARTBEAT_STALE_CHECK_LOG'
    if status=='WAITING_D26':
        if parent_done and parent_free:return 'ACTIVE_WAITING_NEXT_POLL_EXPECT_START_WITHIN_60S'
        return 'ACTIVE_QUEUED_WAITING_PREDECESSOR' if not parent_done or parent_free is False else 'WAITING_PARENT_LOCK_MISSING_CHECK_LOG'
    if status=='RUNNING':return 'HANDOVER_STARTED' if workers else 'CONTROLLER_RUNNING_CHECK_JOB_LOGS'
    return 'CHECK_CONTROLLER_LOG'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,default=DEFAULT);args=ap.parse_args()
    base=args.directory.resolve();base.relative_to(Path('/home/jovyan/zzx').resolve())
    path=base/'queue_status.json'
    if not path.is_file():
        print('D27_VERDICT=NO_QUEUE_STATUS_NOT_CONFIRMED_ENQUEUED')
    else:
        state=read(path);plan=read(base/'plan.json');pid=state.get('controller_pid');live=alive(pid,base)
        try:age=(datetime.now(timezone.utc)-datetime.fromisoformat(state['observed_at']).astimezone(timezone.utc)).total_seconds()
        except (KeyError,ValueError):age=None
        parent=Path(plan['predecessor_directory']).resolve();parent.relative_to(base.parent)
        predecessor=read(parent/'queue_status.json');done=terminal(predecessor);free=lock_free(parent/'controller.lock')
        workers=[name for name,row in state.get('jobs',{}).items() if alive(row.get('pid'),base)]
        print('D27_STATUS='+str(state.get('status')),'PID='+str(pid),'LIVE='+str(live))
        print('D27_LAST_OBSERVED='+str(state.get('observed_at')),'HEARTBEAT_AGE_SECONDS='+str(None if age is None else round(age,1)))
        print('D27_EXECUTION_COMMIT='+str(plan.get('execution_commit')),'LIVE_WORKERS='+str(workers))
        print('D26_STATUS='+str(predecessor.get('status')),'COMPLETE='+str(sum(r.get('status')=='COMPLETE' for r in predecessor.get('jobs',{}).values()))+'/9',
              'LAST_OBSERVED='+str(predecessor.get('observed_at')))
        print('D26_TERMINAL_9_JOBS='+str(done),'D26_CONTROLLER_LOCK_FREE='+str(free))
        print('D27_VERDICT='+classify(state.get('status'),live,age,done,free,workers))
    logs=sorted(base.glob('nohup*.log'),key=lambda p:p.stat().st_mtime,reverse=True)
    if logs:
        print('D27_LOG='+str(logs[0]))
        print('\n'.join(logs[0].read_text(encoding='utf-8',errors='replace').splitlines()[-8:]))
    else:print('D27_LOG=NONE')
if __name__=='__main__':main()

