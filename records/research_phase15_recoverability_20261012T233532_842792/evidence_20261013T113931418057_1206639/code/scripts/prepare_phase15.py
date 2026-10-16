"""Reuse immutable old masks/predictions; create only nested subsets/DSM maps."""
import argparse
from pathlib import Path
import numpy as np
from phase15_common import *
from phase15_numeric import *


def checked_array(row):
    f = Path(row['path'])
    if sha(f) != row['sha256']:
        raise RuntimeError('array receipt changed: ' + str(f))
    return f


def load_mask(base, tile, i, family, ratio=25):
    row = read(Path(base) / 'mask_manifest.json')['tiles'][tile][str(i)][family][str(ratio)]
    m = decode_mask(checked_array(row))
    if canonical(m) != row['canonical_sha256'] or int(m.sum()) != m.size*ratio//100:
        raise RuntimeError('mask identity/count changed')
    return m, row


def old_prediction(base, model, tile, i=0, family='clean'):
    index = read(Path(base) / 'old_cache.json')['predictions']
    row = index[f'{model}/{tile}/{i}/{family}']
    checked_array(row)
    record = Path(row['record'])
    if sha(record) != row['record_sha256']:
        raise RuntimeError('old prediction record changed')
    with np.load(row['path'], allow_pickle=False) as z:
        return z['prediction']


def main(base):
    base = base.resolve()
    p = validate(base)
    verify_code(base)
    structured, paired = Path(p['structured']), Path(p['paired'])
    from structured_v0_common import JOBS
    # Reuse completed receipts, not the prior full scientific audit/unused arrays.
    for job in JOBS:
        complete = read(structured / 'jobs' / job / 'complete.json')
        if complete['job'] != job or complete['optimizer_updates'] != 0:
            raise RuntimeError('old complete receipt differs')
        for field, filename in (('plan_sha256','plan.json'),('code_sha256','code_manifest.json'),('mask_manifest_sha256','mask_manifest.json')):
            if complete[field] != sha(structured / filename):
                raise RuntimeError('old receipt binding differs')
    source = read(base / 'source_plan.json')
    if source['data']['validation'] != list(TILES):
        raise RuntimeError('validation split changed')
    from post_n2_diag_runtime import input_contract
    from post_ab_n1_data import Loader
    input_contract(Path(p['root']), source)
    loader = Loader(Path(p['root']), source)
    old_manifest = read(base / 'old_mask_manifest.json')
    cache = {}
    for tile in TILES:
        for i in range(21):
            for family in (('clean',) if i == 0 else FAMILIES):
                folder = structured / 'jobs' / (('clean_' + tile) if not i else f'pair_{i:02d}_{tile}')
                for model, name in (('S1', 'S1'), ('RGB', 'RGB')):
                    f = folder / ((name if not i else family+'_'+name) + '.json')
                    row = read(f)
                    complete = read(folder / 'complete.json')
                    if sha(f) != complete['records'][f.name]:
                        raise RuntimeError('old case receipt changed')
                    if i and row['mask_sha256']!=old_manifest['tiles'][tile][str(i)][family]['canonical_sha256']:
                        raise RuntimeError('cached prediction uses a different old mask')
                    path = within(folder / row['prediction_file'], structured)
                    if sha(path) != row['prediction_sha256']:
                        raise RuntimeError('required cached array changed')
                    cache[f'{model}/{tile}/{i}/{family}'] = dict(path=str(path), sha256=row['prediction_sha256'],
                        record=str(f), record_sha256=sha(f))
    write(base / 'old_cache.json', dict(predictions=cache))
    entries, mappings, stats = {}, {}, {}
    feature_samples = {n: [] for n in ('dsm_mean', 'dsm_variance', 'dsm_gradient')}
    for tile in TILES:
        item = loader(tile, True)
        if item['dsm'].shape != (6000, 6000):
            raise RuntimeError('bound native tile shape differs')
        fields = feature_arrays(item['optical'], item['dsm'])
        for name in feature_samples:
            feature_samples[name].append(fields[name].ravel())
        for name, arr in fields.items():
            f = base / 'features' / tile / (name + '.npz')
            save_npz(f, value=arr)
        mappings[tile] = {}
        for mode in ('crop_shuffle', 'tile_shuffle'):
            mapping = permutation(item['dsm'].shape, tile, mode)
            check = map_check(mapping, item['dsm'].shape)
            f = base / 'maps' / tile / (mode+'.npz')
            save_npz(f, index=mapping)
            mappings[tile][mode] = dict(path=str(f), sha256=sha(f), **check)
            del mapping
        entries[tile] = {}
        for i in range(1, 21):
            write(base / 'preparation_progress.json', dict(tile=tile, realization=i, observed_at=now(), phase='binding_masks'))
            entries[tile][str(i)] = {}
            for family in FAMILIES:
                old = old_manifest['tiles'][tile][str(i)][family]
                f = within(old['path'], structured)
                if sha(f) != old['file_sha256']:
                    raise RuntimeError('old mask archive changed')
                m = decode_mask(f)
                if canonical(m) != old['canonical_sha256'] or int(m.sum()) != 9000000:
                    raise RuntimeError('old M25 changed')
                entries[tile][str(i)][family] = {'25': dict(path=str(f), sha256=sha(f), canonical_sha256=canonical(m), pixels=int(m.sum()))}
                if family == 'pixel':
                    for ratio, value in nested(m, tile, i).items():
                        if ratio == 25:
                            continue
                        target = base / 'masks' / tile / f'{i:02d}_pixel_{ratio}.npz'
                        save_npz(target, bits=np.packbits(value, bitorder='little'), shape=np.array(value.shape, np.int64))
                        entries[tile][str(i)][family][str(ratio)] = dict(path=str(target), sha256=sha(target),
                            canonical_sha256=canonical(value), pixels=int(value.sum()))
                del m
        stats[tile] = dict(shape=list(item['dsm'].shape), zero_definition='post_d30_data.dsm_present_zero; normalized DSM=0, dm=True',
            optical_preprocessing='uint8/255 before model ImageNet normalization', dsm_preprocessing='original per-tile minmax before permutations')
        del item, fields
    calibration = {name: np.quantile(np.concatenate(values), [.25, .5, .75]).tolist() for name, values in feature_samples.items()}
    # Defined before correctness analysis, no GT used for bins.
    calibration.update(rgb_zero_fraction=[.25, .5, .75], s1_entropy=[.25, .5, .75])
    write(base / 'calibration.json', dict(thresholds=calibration, source='clean Val2 full pixels, no GT/correctness', local_window=9, boundary='reflect'))
    write(base / 'mask_manifest.json', dict(tiles=entries, legacy_sha256=p['source_files']['old_mask_manifest.json'], original_realizations=list(range(1,21)), new_realizations=0))
    write(base / 'map_manifest.json', dict(tiles=mappings, fixed_across_realizations_and_models=True, details=stats))
    # Model binding includes exact old train-state age, not a filename inference.
    checkpoints = dict(source['donors'])
    checkpoints['R16'] = dict(path=str(paired/'jobs/R16/endpoint.pth'),
        sha256=read(base/'R16_complete.json')['artifacts']['endpoint.pth'])
    checkpoints['RGB'] = dict(source['experts']['rgb'], path=str(Path(p['root'])/source['experts']['rgb']['path']))
    checkpoints['DSM'] = dict(source['experts']['dsm'], path=str(Path(p['root'])/source['experts']['dsm']['path']), compatibility='LEGACY_TRAIN16_R50_VIT_B16_SEED42')
    checkpoints['S1'] = checkpoints.pop('S1-0')
    checkpoints['S13'] = checkpoints.pop('S1-3')
    checkpoints = {n: checkpoints[n] for n in EXPERTS}
    for row in checkpoints.values():
        within(row['path'], '/home/jovyan/zzx')
        if sha(row['path']) != row['sha256']:
            raise RuntimeError('frozen checkpoint changed')
    write(base / 'checkpoint_manifest.json', dict(experts=checkpoints, preprocessing=stats, source_plan_sha256=sha(base/'source_plan.json')))
    write(base / 'input_binding.json', dict(files=loader.verified, test6_loaded=False, held4_loaded=False, independent_final_loaded=False))
    names = ('mask_manifest.json','map_manifest.json','checkpoint_manifest.json','calibration.json','old_cache.json','input_binding.json')
    write(base / 'preparation_complete.json', dict(plan_sha256=sha(base/'plan.json'), code_sha256=sha(base/'code_manifest.json'),
        files={n:sha(base/n) for n in names}, optimizer_updates=0, prepared_at=now()))


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--directory', type=Path, required=True)
    main(a.parse_args().directory)
