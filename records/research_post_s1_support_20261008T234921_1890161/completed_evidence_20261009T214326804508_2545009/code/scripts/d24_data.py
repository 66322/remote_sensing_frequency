"""Read only fit12/Val2; resident host tiles and keyed multiworker crops."""
import random
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset
from torch.utils.data._utils.collate import default_collate
import d23_engine as e
from d24_common import read, within

COLORS = ((255,255,255), (0,0,255), (0,255,255), (0,255,0), (255,255,0), (255,0,0))
Q = ('clean','rgb_down2','rgb_down4','rgb_blur5','rgb_local_down4_q1','aux_down4','aux_noise_std010')


class Loader:
    def __init__(self, root, plan):
        self.root, self.plan = Path(root), plan
        self.base = read(self.root / 'configs/rebuild_v1/r05_quality_plus_dropout_16k.json')
        self.data = within(self.base['data_root'], '/home/jovyan/zzx')
        rows = read(self.root / 'records/rebuild_v1_d21_queue_20260928/input_manifest.json')['files']
        self.inputs = {row['path']: row for row in rows}
        self.verified = {}

    def __call__(self, tile, validation=False):
        allowed = self.plan['data']['validation'] if validation else self.plan['data']['fit12']
        if tile not in allowed:
            raise RuntimeError('tile outside fit12/Val2: ' + tile)
        a, b = map(int, tile.split('_'))
        paths = dict(optical=self.data / '2_Ortho_RGB' / ('top_potsdam_' + tile + '_RGB.tif'),
                     dsm=self.data / '1_DSM/1_DSM' / ('dsm_potsdam_%02d_%02d.tif' % (a, b)),
                     full_gt=self.data / '5_Labels_for_participants' / ('top_potsdam_' + tile + '_label.tif'))
        if validation:
            paths['noboundary_gt'] = self.data / '5_Labels_for_participants_no_Boundary' / ('top_potsdam_' + tile + '_label_noBoundary.tif')
        arrays = {}
        for name, path in paths.items():
            row = self.inputs.get(str(path))
            stat = path.stat()
            if row is None or stat.st_size != row['size'] or stat.st_mtime_ns != row['mtime_ns']:
                raise RuntimeError('known input metadata changed: ' + str(path))
            self.verified[str(path)] = dict(size=stat.st_size, mtime_ns=stat.st_mtime_ns, sha256=row['sha256'],
                                           sha_source='existing D21 input manifest; current size/mtime checked')
            with Image.open(path) as im:
                arrays[name] = np.array(im if name == 'dsm' else im.convert('RGB'))
        ds = arrays.pop('dsm').astype(np.float32)
        if not np.isfinite(ds).all() or ds.max() <= ds.min():
            raise RuntimeError('invalid DSM range')
        ds = (ds - ds.min()) / (ds.max() - ds.min())
        result = dict(optical=arrays.pop('optical').astype(np.float32) / 255, dsm=ds)
        for name, colors in arrays.items():
            gt = np.full(ds.shape, 255, np.uint8)
            recognized = np.all(colors == 0, -1) if name == 'noboundary_gt' else np.zeros(ds.shape, bool)
            for c, color in enumerate(COLORS):
                region = np.all(colors == color, -1)
                gt[region] = c
                recognized |= region
            if not recognized.all():
                raise RuntimeError('unrecognized label color: ' + tile)
            result[name] = gt
        if result['optical'].shape[:2] != ds.shape:
            raise RuntimeError('unaligned input shapes')
        return result


def views(op, ds, policy, step, sample_index):
    q_rng = random.Random(e.key(42, 'D24_Q', step, sample_index))
    d_rng = random.Random(e.key(42, 'D24_D', step, sample_index))
    q = q_rng.choice(Q)
    d = d_rng.choices(('clean', 'aux_zero', 'aux_local_zero_q1'), weights=(.5,.25,.25))[0]
    if 'Q' not in policy:
        q = 'clean'
    if 'D' not in policy:
        d = 'clean'
    op2, ds2, mask = e.treatment(op[None], ds[None], q, e.key(42, 'D24_noise', step, sample_index))
    if d != 'clean':
        op2, ds2, mask = e.treatment(op2, ds2, d, e.key(42, 'D24_drop', step, sample_index))
    return op2[0], ds2[0], mask[0], q, d


class Crops(Dataset):
    def __init__(self, tiles, ids, augmentation, policy, start_step=0, stop_step=4000):
        self.cache = {tile:tiles[tile] for tile in ids}
        self.ids, self.augmentation, self.policy = ids, augmentation, policy
        self.start, self.stop = start_step, stop_step

    def __len__(self):
        return (self.stop - self.start) * 16

    def __getitem__(self, index):
        step, i = self.start + index // 16, index % 16
        # Identical crop/scale/flip stream to D23, independent of route/device.
        token = e.key(42, 'fit', step) * 16 + i
        spec = e.sample_spec(self.ids, token, self.augmentation, 512)
        spec['treatment'] = 'clean'
        op, ds, gt, _ = e.materialize(self.cache, spec)
        op2, ds2, mask2, q, d = views(op, ds, self.policy, step, i)
        return dict(rgb=op, aux=ds, gt=gt, rgb2=op2, aux2=ds2, mask2=mask2,
                    prototype_seed=e.key(42, 'bucket', spec['tile']) % (2 ** 31), q=q, d=d)


class PrefetchedBatches:
    """Threads share resident tiles; no multi-gigabyte multiprocessing IPC queue."""
    def __init__(self,dataset,batch=16,workers=8,prefetch_batches=4,pin_memory=True):
        if len(dataset)%batch:
            raise ValueError('partial logical batch is forbidden')
        self.dataset,self.batch,self.workers=dataset,batch,workers
        self.prefetch,self.pin=prefetch_batches,pin_memory

    def __iter__(self):
        with ThreadPoolExecutor(max_workers=self.workers,thread_name_prefix='d24_crop') as executor:
            ready=deque();next_index=0
            def submit():
                nonlocal next_index
                if next_index>=len(self.dataset):return False
                ready.append([executor.submit(self.dataset.__getitem__,i)
                              for i in range(next_index,next_index+self.batch)])
                next_index+=self.batch
                return True
            for _ in range(self.prefetch):
                if not submit():break
            while ready:
                samples=[future.result() for future in ready.popleft()]
                value=default_collate(samples)
                del samples
                if self.pin:
                    value={k:v.pin_memory() if torch.is_tensor(v) else v for k,v in value.items()}
                submit()
                yield value
