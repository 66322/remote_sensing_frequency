"""Outcome-blind spatial transforms and integer diagnostic estimands."""
import hashlib
import numpy as np
from scipy import ndimage as ndi
from phase15_common import key
from structured_v0_masks import canonical
from structured_v0_metrics import cm, metric, transitions


def save_npz(path, **arrays):
    from pathlib import Path
    import os
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp.' + str(os.getpid()))
    with tmp.open('wb') as f:
        np.savez_compressed(f, **arrays)
    os.replace(tmp, path)


def decode_mask(path):
    with np.load(path, allow_pickle=False) as z:
        shape = tuple(map(int, z['shape']))
        return np.unpackbits(z['bits'], bitorder='little', count=int(np.prod(shape))).reshape(shape).astype(bool)


def nested(m25, tile, realization):
    ids = np.flatnonzero(m25)
    np.random.Generator(np.random.PCG64(key(tile, realization, 'nested'))).shuffle(ids)
    result = {25: m25}
    for ratio in (5, 10):
        value = np.zeros(m25.size, bool)
        value[ids[:m25.size * ratio // 100]] = True
        result[ratio] = value.reshape(m25.shape)
    if not ((result[5] <= result[10]).all() and (result[10] <= m25).all()):
        raise RuntimeError('nested mask failure')
    return result


def permutation(shape, tile, mode, block=512):
    h, w = shape
    n = h * w
    rng = np.random.Generator(np.random.PCG64(key(tile, mode, 'DSM-map')))
    if mode == 'tile_shuffle':
        return rng.permutation(n).astype(np.int32)
    if mode != 'crop_shuffle':
        raise ValueError(mode)
    grid = np.arange(n, dtype=np.int32).reshape(shape)
    result = np.empty_like(grid)
    groups = {}
    for y in range(0, h, block):
        for x in range(0, w, block):
            sh = (min(block, h - y), min(block, w - x))
            groups.setdefault(sh, []).append((y, x))
    for sh, coords in sorted(groups.items()):
        order = rng.permutation(len(coords))
        for (y, x), src in zip(coords, order):
            yy, xx = coords[int(src)]
            result[y:y+sh[0], x:x+sh[1]] = grid[yy:yy+sh[0], xx:xx+sh[1]]
    return result.ravel()


def map_check(mapping, shape):
    n = int(np.prod(shape))
    if mapping.shape != (n,) or mapping.min() != 0 or mapping.max() != n-1:
        raise ValueError('permutation range')
    # Exact O(n) bijection check; no 36M-element Python set.
    if not np.all(np.bincount(mapping, minlength=n) == 1):
        raise ValueError('not a bijection')
    return dict(bijective=True, pixels=n, fixed_points=int((mapping == np.arange(n)).sum()),
                canonical_index_sha256=hashlib.sha256(mapping.astype('<i4', copy=False).tobytes()).hexdigest())


def distance_bins(mask):
    # False halo defines tile-edge boundary; original pixel-center EDT convention.
    dist = ndi.distance_transform_edt(np.pad(mask, 1, constant_values=False))[1:-1, 1:-1]
    bins = np.digitize(dist, (4, 16, 64), right=False).astype(np.uint8)
    bins[~mask] = 255
    return bins


def feature_arrays(optical, dsm):
    avg = ndi.uniform_filter(dsm, size=9, mode='reflect')
    variance = np.maximum(ndi.uniform_filter(dsm*dsm, size=9, mode='reflect') - avg*avg, 0)
    gradient = np.hypot(ndi.sobel(dsm, axis=0, mode='reflect'), ndi.sobel(dsm, axis=1, mode='reflect'))
    zero = ndi.uniform_filter(np.all(optical == 0, axis=-1).astype(np.float32), size=9, mode='reflect')
    return dict(dsm_mean=avg, dsm_variance=variance, dsm_gradient=gradient, rgb_zero_fraction=zero)


def evidence(gt, clean, pred, regions):
    out = {}
    for name, support in regions.items():
        a, b = cm(gt, clean, support), cm(gt, pred, support)
        t = transitions(gt, clean, pred, support)
        out[name] = dict(clean_cm=a.tolist(), missing_cm=b.tolist(), transitions=t,
                        confusion_matrix_dtype='int64')
    return out


def profile(gt, clean, pred, mask):
    bins = distance_bins(mask)
    return {str(i): transitions(gt, clean, pred, bins == i) for i in range(4)}


def seam_smooth(raw, mask):
    band = ndi.maximum_filter(mask, size=3, mode='nearest') != ndi.minimum_filter(mask, size=3, mode='nearest')
    # Compute only seam neighborhoods, row chunks; retain raw on a modal tie.
    out = raw.copy()
    padded = np.pad(raw, 1, mode='edge')
    for start in range(0, raw.shape[0], 128):
        end = min(start+128, raw.shape[0])
        b = band[start:end]
        yy, xx = np.nonzero(b)
        yy = yy + start
        if not len(yy):
            continue
        counts = np.zeros((6, len(yy)), np.uint8)
        for dy in range(3):
            for dx in range(3):
                values = padded[yy+dy, xx+dx]
                for c in range(6):
                    counts[c] += values == c
        best = counts.max(0)
        unique = (counts == best).sum(0) == 1
        out[yy[unique], xx[unique]] = counts[:, unique].argmax(0)
    if not np.array_equal(out[~band], raw[~band]):
        raise RuntimeError('smoothing escaped seam')
    return out, band


def oracle(gt, predictions, patch=None):
    out = predictions[0].copy()
    source = np.zeros(gt.shape, np.uint8)
    valid = gt < 6
    if patch is None:
        assigned = predictions[0] == gt
        for i, pred in enumerate(predictions[1:], 1):
            use = valid & ~assigned & (pred == gt)
            out[use] = pred[use]
            source[use] = i
            assigned |= use
    else:
        for y in range(0, gt.shape[0], patch):
            for x in range(0, gt.shape[1], patch):
                sl = (slice(y, y+patch), slice(x, x+patch))
                n = [int(((p[sl] == gt[sl]) & valid[sl]).sum()) for p in predictions]
                i = int(np.argmax(n))
                out[sl], source[sl] = predictions[i][sl], i
    return out, source


def condition_counts(gt, predictions, bins, keep):
    disagreements = np.zeros(gt.shape, bool)
    for p in predictions[1:]:
        disagreements |= p != predictions[0]
    use = keep & (gt < 6) & disagreements
    result = {}
    for value in sorted(np.unique(bins[use]).tolist()):
        region = use & (bins == value)
        result[str(int(value))] = dict(valid=int(region.sum()),
            correct=[int((region & (p == gt)).sum()) for p in predictions])
    return result


def oracle_evidence(gt, clean, predictions, mask, entropy, deployment_bins):
    from phase15_common import EXPERTS
    from structured_v0_masks import supports
    regions = supports(mask)
    regions['valid'] = np.ones_like(mask)
    regions['mask'] = mask
    regions['outside'] = ~mask
    raw = np.where(mask, predictions[3], predictions[0]).astype(np.uint8)
    smooth, _ = seam_smooth(raw, mask)
    systems = dict(zip(EXPERTS, predictions))
    systems.update(known_mask_raw=raw, known_mask_smoothed=smooth)
    sources = {}
    for name, patch in (('oracle_pixel', None), ('oracle_patch128', 128), ('oracle_patch256', 256)):
        systems[name], origin = oracle(gt, predictions, patch)
        sources[name] = {r: np.bincount(origin[(gt < 6) & support], minlength=5).tolist() for r, support in regions.items()}
    rows = {name: evidence(gt, clean, pred, regions) for name, pred in systems.items()}
    codes = np.zeros(gt.shape, np.uint8)
    for i, p in enumerate(predictions):
        codes |= ((p == gt).astype(np.uint8) << i)
    hist = {r: np.bincount((gt[s & (gt < 6)].astype(np.int64)*32 + codes[s & (gt < 6)]), minlength=6*32).reshape(6, 32).tolist() for r, s in regions.items()}
    distance = distance_bins(mask)
    labeled, _ = ndi.label(mask)  # 4-connected components, explicit.
    sizes = np.bincount(labeled.ravel())
    component = np.digitize(sizes[labeled], (16, 256, 4096, 65536)).astype(np.uint8)
    component[~mask] = 255
    agree = np.zeros(gt.shape, np.uint8)
    for p in predictions:
        agree += p == predictions[0]
    diagnostic = dict(gt_class=gt, true_mask_distance=distance, true_component_size=component)
    observable = dict(deployment_bins, s1_entropy=entropy, agreement_with_s1=agree,
                      s1_dsm_disagreement=(predictions[0] != predictions[3]).astype(np.uint8))
    bins = {name: {r: condition_counts(gt, predictions, b, s) for r, s in {'valid': regions['valid'], 'mask': mask}.items()}
            for name, b in {**diagnostic, **observable}.items()}
    return dict(systems=rows, oracle_sources=sources, joint_correct_by_class=hist, conditional_counts=bins,
                mechanism_only_bins=list(diagnostic), observable_bins=list(observable), oracle_priority=list(EXPERTS))


def bootstrap(values, n=5000):
    values = np.asarray(values, np.float64)
    if len(values) != 20 or not np.isfinite(values).all():
        return dict(mean=None, CI95=None, verdict='INCONCLUSIVE_LOW_SUPPORT')
    rng = np.random.Generator(np.random.PCG64(61011))
    means = values[rng.integers(0, len(values), size=(n, len(values)))].mean(1)
    return dict(mean=float(values.mean()), CI95=np.quantile(means, [.025, .975]).tolist(), positive=int((values > 0).sum()), n_mask_realizations=20)


def exact_signflip(values):
    x = np.asarray(values, np.float64)
    if len(x) != 20 or not np.isfinite(x).all():
        return None
    x=x[x!=0]
    if not len(x):
        return 1.0
    k=len(x)
    observed = abs(x.sum())
    count = 0
    for start in range(0, 1 << k, 8192):
        ids = np.arange(start, min(start+8192, 1 << k), dtype=np.uint32)
        signs = (((ids[:, None] >> np.arange(k, dtype=np.uint32)) & 1).astype(np.int8)*2-1)
        count += int((np.abs(signs @ x) >= observed - 1e-12).sum())
    return count / (1 << k)
