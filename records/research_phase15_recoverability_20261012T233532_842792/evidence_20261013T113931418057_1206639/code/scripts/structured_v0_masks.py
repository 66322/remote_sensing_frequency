"""Outcome-blind masks; bounded semantic matching, no post-result redraw."""
import hashlib
import json
import numpy as np
from scipy.ndimage import sobel, maximum_filter, minimum_filter


def availability_diagnostics(mask, window=512, stride=256):
    from scipy.ndimage import distance_transform_edt
    def positions(length):
        if length < window:
            raise ValueError('tile smaller than window')
        return sorted(set(list(range(0, length-window+1, stride))+[length-window]))
    rows = {str(k):dict(valid=0,total=0) for k in (4,8,16)}
    missing_windows = total_windows = 0
    for y in positions(mask.shape[0]):
        for x in positions(mask.shape[1]):
            received = ~mask[y:y+window,x:x+window]
            missing_windows += int(not received.any())
            total_windows += 1
            for k in (4,8,16):
                if window % k:
                    raise ValueError('grid must divide window')
                valid = received.reshape(window//k,k,window//k,k).all(axis=(1,3))
                rows[str(k)]['valid'] += int(valid.sum())
                rows[str(k)]['total'] += valid.size
    distance = distance_transform_edt(mask)[mask]
    bins = [0,1,2,4,8,16,32,64,128,256,512,float('inf')]
    hist = np.histogram(distance,bins=bins)[0]
    return dict(masked_path_full_valid_pooling=rows,windows=total_windows,fully_missing_windows=missing_windows,
        missing_pixel_distance_bins=['0','1','2','4','8','16','32','64','128','256','512','inf'],
        missing_pixel_distance_histogram=hist.tolist(),scope='mask-derived per-window availability at native pyramid scales; not learned activation evidence')


def rng_for(tile, realization, role):
    b = ('STRUCTURED_V0_1/%s/%s/%s' % (tile, realization, role)).encode()
    return np.random.Generator(np.random.PCG64(int.from_bytes(hashlib.sha256(b).digest()[:16], 'little')))


def canonical(mask):
    a = np.asarray(mask, dtype=np.uint8, order='C')
    head = json.dumps(dict(dtype='uint8', shape=list(a.shape), order='C', one='missing'), sort_keys=True).encode() + b'\n'
    return hashlib.sha256(head + a.tobytes()).hexdigest()


def rectangle_sums(array, rects):
    a = np.pad(np.asarray(array, np.int64).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    y, x, k = np.asarray(rects).T
    return a[y+k, x+k] - a[y, x+k] - a[y+k, x] + a[y, x]


def raster(shape, rects):
    a = np.zeros(shape, bool)
    for y, x, k in rects:
        if y < 0 or x < 0 or y+k > shape[0] or x+k > shape[1] or a[y:y+k, x:x+k].any():
            raise ValueError('overlap or clipping')
        a[y:y+k, x:x+k] = True
    return a


def semantic_error(total, target, area):
    # Six NB proportions among NB-valid pixels, and NB coverage of full mask.
    if total.sum() <= 0 or target.sum() <= 0:
        return np.inf
    delta = np.abs(total / total.sum() - target / target.sum())
    tolerance = np.array([.01, .01, .01, .01, .002, .01])
    return max(float(np.max(delta / tolerance)), abs(float(total.sum()-target.sum())) / area / .01)


def match_indices(hist, initial, target, extra, area, rng, attempts=50000):
    chosen = np.array(initial, copy=True)
    unused = np.setdiff1d(np.arange(len(hist)), chosen)
    total = hist[chosen].sum(0) + extra
    error = semantic_error(total, target, area)
    used = 0
    while error > 1 and used < attempts:
        used += 1
        i = int(rng.integers(len(chosen)))
        j = int(rng.integers(len(unused)))
        candidate = total - hist[chosen[i]] + hist[unused[j]]
        value = semantic_error(candidate, target, area)
        if value < error:
            chosen[i], unused[j] = unused[j], chosen[i]
            total, error = candidate, value
    if error > 1:
        raise RuntimeError('HOLD_MASK_MATCH_INFEASIBLE error=%.6f attempts=%d' % (error, used))
    return chosen, dict(attempts=used, normalized_error=error, nb_counts=total.tolist())


def generate(item, tile, realization):
    ds, gt = item['dsm'], item['noboundary_gt']
    shape = ds.shape
    if shape != (6000, 6000) or not np.isfinite(ds).all():
        raise RuntimeError('frozen 6000-square finite DSM required')
    area = 9000000
    phase = rng_for(tile, realization, 'grid').integers(0, 8, size=2)
    rects = np.array([(y, x, 128) for y in range(int(phase[0]), 5873, 136)
                     for x in range(int(phase[1]), 5873, 136)], np.int64)
    small_index = int(rng_for(tile, realization, 'small').integers(len(rects)))
    small = rects[small_index].copy()
    small[2] = 72
    rects = np.delete(rects, small_index, 0)
    gx, gy = sobel(ds, 1, mode='reflect'), sobel(ds, 0, mode='reflect')
    g = np.hypot(gx, gy)
    threshold = float(np.percentile(g, 90))
    high = g > threshold
    scores = rectangle_sums(high, rects) / 128**2
    if float(scores.std()) == 0:
        raise RuntimeError('HOLD_NO_GRADIENT_CONTRAST')
    # Fixed exponential tilt, clipped z-score, no outcome calibration.
    weights = np.exp(2 * np.clip((scores-scores.mean())/scores.std(), -3, 3))
    weights /= weights.sum()
    ri = rng_for(tile, realization, 'random').choice(len(rects), 549, replace=False)
    si = rng_for(tile, realization, 'gradient').choice(len(rects), 549, replace=False, p=weights)
    hist = np.stack([rectangle_sums(gt == c, rects) for c in range(6)], 1)
    extra = np.array([int((gt[small[0]:small[0]+72, small[1]:small[1]+72] == c).sum()) for c in range(6)])
    target = hist[si].sum(0) + extra
    initial = rng_for(tile, realization, 'twin_initial').choice(len(rects), 549, replace=False)
    mi, match = match_indices(hist, initial, target, extra, area, rng_for(tile, realization, 'twin_swaps'))
    masks, metadata = {}, {}
    for name, ids in [('random', ri), ('gradient', si), ('matched', mi)]:
        blocks = np.vstack((rects[ids], small[None]))
        masks[name] = raster(shape, blocks)
        metadata[name] = dict(primitives=blocks.tolist(), high_gradient_fraction=float(high[masks[name]].mean()),
                              grid_phase=phase.tolist(), grid_spacing=136, primitive_gap_min=8,
                              component_count=550, perimeter=549*4*128+4*72)
    if metadata['gradient']['high_gradient_fraction'] <= metadata['matched']['high_gradient_fraction']:
        raise RuntimeError('HOLD_MATCHED_GRADIENT_CONTRAST_LOST')
    pixel = np.zeros(shape, bool)
    pixel.ravel()[rng_for(tile, realization, 'pixel').choice(pixel.size, area, replace=False)] = True
    masks['pixel'] = pixel
    metadata['pixel'] = dict(sampling='uniform_exact_area_without_replacement')
    for name, mask in masks.items():
        if int(mask.sum()) != area:
            raise RuntimeError('area mismatch')
        metadata[name].update(shape=list(shape), missing_pixels=area, canonical_sha256=canonical(mask),
            full_counts=np.bincount(item['full_gt'][mask & (item['full_gt']<6)], minlength=6).tolist(),
            nb_counts=np.bincount(gt[mask & (gt<6)], minlength=6).tolist(),
            gradient_threshold=threshold, gradient_quantile=90, role=name,
            boundary_pixels=int((mask & (item['full_gt']<6) & (gt==255)).sum()))
    metadata['matched']['matching'] = match
    metadata['matched']['label_assisted'] = True
    return masks, metadata


def supports(mask):
    dilated = maximum_filter(mask, size=17, mode='constant', cval=0).astype(bool)
    eroded = minimum_filter(mask, size=17, mode='constant', cval=0).astype(bool)
    return dict(missing=mask, observed=~mask, healthy=~dilated, edge=dilated & ~eroded,
                all=np.ones_like(mask))
