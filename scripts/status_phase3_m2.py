"""Small status only. Does not load checkpoints, data, or archived counts."""
import argparse
from pathlib import Path
import phase3_m2_common as c

def main(base):
    base=Path(base)
    for name in ['queue_status.json','controller_failure.json','publication/summary.json','github_upload_receipt.json']:
        if (base/name).exists():print(name,(base/name).read_text(encoding='utf-8'))
    for f in sorted((base/'jobs').glob('*/progress.json')):
        if not (f.parent/'complete.json').exists():
            z=c.read(f);print('ACTIVE_TRAIN',f.parent.name,z.get('step'),z.get('elapsed_seconds'),z.get('gpu_uuid'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True);main(p.parse_args().directory)
