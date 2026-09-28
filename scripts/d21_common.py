"""Standard-library D21 plan, provenance, and resume checks."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'configs/rebuild_v1/d21_detail_frequency_20260928.json'
OUT = ROOT / 'records/rebuild_v1_d21_queue_20260928'
COMPACT = ROOT / 'records/rebuild_v1_d21_compact_20260928'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(8*1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def config():
    cfg = read(CONFIG)
    assert cfg['arms'] == ['R0', 'R1', 'M0', 'M1', 'F0', 'F1', 'F2', 'F3']
    assert cfg['seeds'] == [42, 17] and cfg['datasets'] == ['potsdam', 'vaihingen']
    assert cfg['steps'] == 16000 and cfg['micro_batch'] * cfg['accum_steps'] == 16
    assert cfg['test6_loaded'] is False and cfg['independent_final_loaded'] is False
    return cfg


def jobs():
    cfg = config()
    # Complete the first matched seed across both datasets before subsequent seeds.
    return [dict(dataset=d, arm=a, seed=s) for s in cfg['seeds']
            for a in cfg['arms'] for d in cfg['datasets']]


def key(job, smoke=False):
    return f"{job['dataset']}_{job['arm']}_seed{job['seed']}" + ('_smoke' if smoke else '')


def run_dir(job, smoke=False):
    return ROOT / 'runs/rebuild_v1' / ('D21_' + key(job, smoke) + '_16000_20260928')


def eval_dir(job, smoke=False):
    return ROOT / 'records/rebuild_v1_d21_20260928' / key(job, smoke)


def datasets():
    base = read(ROOT / 'configs/rebuild_v1/r05_quality_plus_dropout_16k.json')
    split = read(ROOT / base['split_file'])
    vai = read(ROOT / 'configs/rebuild_v1/d20_vaihingen_formal_seed42_20260928.json')
    result = dict(potsdam=dict(root=base['data_root'], train=split['train16'],
                  dev=split['val2'], excluded=split['historical_exposed_test6']),
                  vaihingen=dict(root=vai['data_root'], train=vai['train_ids'],
                  dev=vai['development_ids'], excluded=vai['excluded_historical_eval_ids']))
    for item in result.values():
        train, dev, excluded = map(set, (item['train'], item['dev'], item['excluded']))
        if train & dev or (train | dev) & excluded:
            raise RuntimeError('split leakage')
    return result


def input_paths():
    result = []
    for name, spec in datasets().items():
        root = Path(spec['root'])
        for split in ('train', 'dev'):
            for tile in spec[split]:
                if name == 'potsdam':
                    a, b = map(int, tile.split('_'))
                    paths = [root/'2_Ortho_RGB'/f'top_potsdam_{tile}_RGB.tif',
                             root/'1_DSM/1_DSM'/f'dsm_potsdam_{a:02d}_{b:02d}.tif',
                             root/'5_Labels_for_participants'/f'top_potsdam_{tile}_label.tif']
                    if split == 'dev':
                        paths.append(root/'5_Labels_for_participants_no_Boundary'/f'top_potsdam_{tile}_label_noBoundary.tif')
                else:
                    labels = 'gts_for_participants' if split == 'train' else 'gts_complete_full'
                    paths = [root/'top'/f'top_mosaic_09cm_area{tile}.tif',
                             root/'dsm'/f'dsm_09cm_matching_area{tile}.tif',
                             root/labels/f'top_mosaic_09cm_area{tile}.tif']
                result.extend(paths)
    return result


def snapshot():
    names = subprocess.check_output(['git', 'ls-files', '*.py', 'configs/rebuild_v1/*.json',
                'scripts/run_rebuild_v1_d21*.sh'], cwd=ROOT, text=True).splitlines()
    subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--', *names], cwd=ROOT,
                   check=True, stdout=subprocess.DEVNULL)
    if 'model/rebuild_v1_d21_detail.py' not in names:
        raise RuntimeError('D21 code must be committed before execution')
    return {name: sha(ROOT/name) for name in names}


def verify_inputs(manifest):
    for row in manifest['files']:
        stat = Path(row['path']).stat()
        if stat.st_size != row['size'] or stat.st_mtime_ns != row['mtime_ns']:
            raise RuntimeError('input changed; preserve evidence: ' + row['path'])
