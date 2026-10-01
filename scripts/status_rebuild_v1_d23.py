"""Read-only D23 progress, including the temporary GPU0 recovery worker."""
import argparse
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import re
import statistics

ARMS={0:('TSF','TS','TCAP','TSF_shuffleS'),1:('T0','TF','TSF_CE','TSF_shuffleF')}

def read(path):return json.loads(path.read_text())
def bounded(base,value):
    path=Path(value).resolve();path.relative_to(base);return path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True)
    base=ap.parse_args().directory.resolve();state=read(base/'queue_status.json')
    events=sorted(base.glob('resume_event_gpu0repair_*.json'))
    event=read(events[-1]) if events else {}
    now=datetime.now(timezone(timedelta(hours=8)))
    print('查询时间:',now.isoformat(timespec='seconds'))
    print('队列记录:',state['status'],'记录时间:',state.get('observed_at'))
    print('恢复记录:',event.get('status','无'))
    rows={};speeds=[];eval_times=[];finished=0
    for gpu,arms in ARMS.items():
        for arm in arms:
            row=state.get('jobs',{}).get(arm,{})
            job=bounded(base,row.get('job_directory',base/'jobs'/arm))
            logfile=bounded(base,row.get('log_path',base/'logs'/(arm+'.log')))
            pid=row.get('pid')
            if arm=='TS' and event.get('TS_job_directory') and event.get('status')!='MERGED_TS_COMPLETE':
                job=bounded(base,event['TS_job_directory']);logfile=bounded(base,event['TS_log']);pid=event.get('TS_pid')
            text=logfile.read_text(errors='replace') if logfile.exists() else ''
            steps=[int(v) for v in re.findall(r'D23_GATE_TRAIN\s+'+re.escape(arm)+r'\s+(\d+)\s',text)]
            step=steps[-1] if steps else 0
            evaluation=len(set(re.findall(r'D23_DEVELOPMENT_EVAL\s+(\S+)\s+(\S+)',text)))
            marker=job/'formal_complete.json';training=job/'training/training_complete.json'
            done=marker.is_file() and read(marker).get('global_step')==4000 and (job/'evaluation/summary.json').is_file()
            proc=Path('/proc')/str(pid)/'cmdline'
            try:alive=proc.exists() and str(job).encode() in proc.read_bytes()
            except FileNotFoundError:alive=False
            if training.is_file():
                step=4000
                start=0 if not steps or steps[0]==1 else steps[0]-100
                seconds=read(training).get('seconds',0)
                if seconds>0 and start<4000:speeds.append(seconds/(4000-start))
            if done:
                finished+=1;step=4000;evaluation=28;phase='完成'
                if training.exists():
                    duration=datetime.fromisoformat(read(marker)['observed_at']).timestamp()-training.stat().st_mtime
                    if duration>0:eval_times.append(duration)
            elif alive:phase='评价中' if step==4000 else ('训练中' if step else '初始化')
            elif step:phase='未确认存活/需看日志'
            else:phase='等待或启动失败'
            print('GPU%d %-12s %-12s step=%4d/4000 eval=%2d/28 pid=%s'%(gpu,arm,phase,step,evaluation,pid))
            rows[arm]=dict(done=done,step=step,evaluation=evaluation,alive=alive)
    print('完整训练及评价已完成: %d/8'%finished)
    if finished==8:
        result=bounded(base,state.get('screen_result',base/'screen_result.json'))
        print('八组汇总结果:', '已生成' if result.is_file() else '尚未生成/需看controller日志')
    elif speeds and eval_times:
        rate=statistics.median(speeds);evaluation_seconds=statistics.median(eval_times)
        def remaining(arm):
            row=rows[arm]
            if row['done']:return 0
            return (4000-row['step'])*rate+(28-row['evaluation'])/28*evaluation_seconds+(120 if row['step']==0 else 0)
        if event.get('TS_job_directory') and event.get('status')!='MERGED_TS_COMPLETE':
            seconds=max(remaining('TS'),remaining('TF'))+max(sum(remaining(a) for a in ARMS[0][2:]),sum(remaining(a) for a in ARMS[1][2:]))
        else:seconds=max(sum(remaining(a) for a in arms) for arms in ARMS.values())
        print('按已完成组耗时粗估: 剩余约 %.1f小时，中心结束时间 %s'%(seconds/3600,(now+timedelta(seconds=seconds)).strftime('%m-%d %H:%M')))
        print('参考范围: %s 至 %s；假设后续连续执行、无报错；不是承诺。'%((now+timedelta(seconds=seconds*.8)).strftime('%H:%M'),(now+timedelta(seconds=seconds*1.3)).strftime('%H:%M')))
    else:print('现有耗时证据不足，暂不估算结束时间。')

if __name__=='__main__':main()
