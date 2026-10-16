"""Download pinned official DINOv2 artifacts; never access training/validation/test imagery."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GIT_TERMINAL_PROMPT','0')


def main():
    cfg = json.loads((ROOT/'configs/rebuild_v1/d18_d19_night_20260927.json').read_text())['dino']
    repo, weights = ROOT/cfg['repository_dir'], ROOT/cfg['weights_path']
    repo.parent.mkdir(parents=True, exist_ok=True)
    if not repo.exists():
        subprocess.run(['git', 'clone', '--no-checkout', 'https://github.com/facebookresearch/dinov2.git', str(repo)], check=True, timeout=300)
        subprocess.run(['git', 'checkout', '--detach', cfg['repository_commit']], cwd=repo, check=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    if commit != cfg['repository_commit']:
        raise RuntimeError('existing external checkout is not the pinned commit; preserved')
    weights.parent.mkdir(parents=True, exist_ok=True)
    manifest = weights.with_suffix('.manifest.json')
    if not weights.exists():
        tmp = weights.with_suffix('.download')
        with urllib.request.urlopen(cfg['weights_url'], timeout=60) as src, tmp.open('wb') as dst:
            while True:
                block = src.read(1024*1024)
                if not block:
                    break
                dst.write(block)
        if tmp.stat().st_size < 70*1024**2:
            raise RuntimeError('DINO weights download is unexpectedly small')
        os.replace(tmp, weights)
    digest = hashlib.sha256(weights.read_bytes()).hexdigest()
    if manifest.exists() and json.loads(manifest.read_text())['sha256'] != digest:
        raise RuntimeError('existing weight manifest mismatch')
    # Official source is recorded; digest pins acquired bytes, not an upstream published checksum.
    manifest.write_text(json.dumps(dict(url=cfg['weights_url'],sha256=digest,size=weights.stat().st_size,
        repository_commit=commit,license='DINOv2 Apache-2.0; see pinned LICENSE and MODEL_CARD.md',
        checksum_provenance='computed after official HTTPS download; not upstream checksum'),indent=2)+'\n')
    print('DINO ARTIFACTS READY',digest,flush=True)


if __name__ == '__main__':
    main()
