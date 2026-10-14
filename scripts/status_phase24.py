"""Read-only last-observation report; never dispatches or retries."""
import argparse
from pathlib import Path
from phase24_common import read,now,live
def main(base):
 base=Path(base).resolve();state=read(base/'queue_status.json')
 launch=read(base/'launch.json') if (base/'launch.json').exists() else {}
 print('QUERY_OBSERVED='+now(),'LAST_OBSERVED='+str(state.get('observed_at')),
  'QUEUE='+str(state.get('status')),'CONTROLLER_LIVE='+str(live(launch.get('controller_pid',0),base)))
 print('CASE_COUNTS',state.get('completed',{}),'CPU_PENDING',state.get('pending_cpu_cases',0))
 for gpu,row in state.get('workers',{}).items():print('GPU',gpu,row,'LIVE='+str(live(row.get('pid',0),base)))
 for f in sorted((base/'jobs').glob('*/progress.json')):
  print(f.parent.name,read(f))
 print('STAGE_PROGRESS',state.get('stage_cases_done'), '/',state.get('stage_cases_total'),'REMAINING_STAGE_HOURS',state.get('stage_remaining_hours'))
 for n in ('progress_gpu0.json','progress_gpu1.json','runtime_gpu0.json','runtime_gpu1.json','preparation_progress.json','cpu_benchmark.json','technical_failure.json'):
  if (base/n).exists():print(n,read(base/n))
 print('No automatic retry, extra seeds, new experts, test access or 24h deadline.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);main(p.parse_args().directory)
