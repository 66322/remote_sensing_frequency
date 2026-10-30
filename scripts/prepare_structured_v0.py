"""Run only after predecessor has exited: outcome-blind mask feasibility."""
import argparse
from pathlib import Path
import numpy as np
import scipy
from structured_v0_common import *
from structured_v0_masks import generate, canonical


def main(base):
    p = validate(base)
    verify_code(base)
    from post_n2_diag_runtime import input_contract
    from post_ab_n1_data import Loader
    source = read(base / 'source_plan.json')
    input_contract(Path(p['root']), source)
    loader = Loader(Path(p['root']), source)
    entries, arrays_seen = {}, {}
    for tile in TILES:
        item = loader(tile, True)
        entries[tile] = {}
        seen = {f: set() for f in FAMILIES}
        for realization in range(1, 21):
            write(base / 'preparation_progress.json', dict(tile=tile, realization=realization, phase='generating_masks', observed_at=now()))
            masks, rows = generate(item, tile, realization)
            entries[tile][str(realization)] = {}
            for family in FAMILIES:
                mask = masks[family]
                digest = canonical(mask)
                if digest in seen[family]:
                    raise RuntimeError('duplicate mask realization')
                seen[family].add(digest)
                target = base / 'masks' / tile / ('%02d_%s.npz' % (realization, family))
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    raise RuntimeError('preserve partial mask generation; no implicit retry')
                np.savez_compressed(target, bits=np.packbits(mask, bitorder='little'), shape=np.array(mask.shape))
                rows[family].update(path=str(target), file_sha256=sha(target))
                entries[tile][str(realization)][family] = rows[family]
            del masks
            print('MASK_PAIR_COMPLETE', tile, realization, flush=True)
        del item
    manifest = dict(protocol=p['protocol'], tiles=entries, input_binding=loader.verified,
                    matching_model_predictions_used=False, masks=160, created_at=now(),
                    generator_environment=dict(numpy=np.__version__, scipy=scipy.__version__),
                    mask_randomness='PCG64, SHA256(protocol/tile/realization/role) first16bytes little-endian')
    write(base / 'mask_manifest.json', manifest)
    write(base / 'preparation_complete.json', dict(plan_sha256=sha(base/'plan.json'), code_sha256=sha(base/'code_manifest.json'),
        mask_manifest_sha256=sha(base/'mask_manifest.json'), optimizer_updates=0, masks=160, generated_at=now()))


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--directory', type=Path, required=True)
    main(a.parse_args().directory.resolve())
