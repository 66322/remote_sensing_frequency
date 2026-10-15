"""Small status read; never launches, trains, uploads or deletes."""
import argparse
import json
from pathlib import Path

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--directory',type=Path,required=True); base=p.parse_args().directory
    for name in ('launch.json','queue_status.json','progress_gpu0.json','progress_gpu1.json','technical_failure.json','result_verification.json','github_upload_receipt.json'):
        f=base/name
        if f.exists():
            z=json.loads(f.read_text());
            if name=='result_verification.json': z={k:v for k,v in z.items() if k not in ('batch_streams','old_initial_checks')}
            print(name,json.dumps(z,ensure_ascii=False))

