"""Integer evidence and fixed-class estimands; empty denominators are None."""
import numpy as np


def cm(gt, pred, support):
    if np.any((pred[support & (gt < 6)] >= 6)):
        raise ValueError('invalid prediction on valid labels')
    use = support & (gt < 6)
    return np.bincount(6*gt[use].astype(np.int64)+pred[use].astype(np.int64), minlength=36).reshape(6, 6)


def metric(matrix, classes=(0, 1, 2, 3, 4)):
    a = np.asarray(matrix, np.int64)
    if a.shape != (6, 6) or (a < 0).any():
        raise ValueError('invalid confusion matrix')
    union = a.sum(0)+a.sum(1)-a.diagonal()
    iou = np.divide(a.diagonal(), union, out=np.full(6, np.nan), where=union > 0)
    selected = iou[list(classes)]
    return float(selected.mean()) if np.isfinite(selected).all() else None


def difference(clean, damaged, classes=(0, 1, 2, 3, 4)):
    a, b = metric(clean, classes), metric(damaged, classes)
    return None if a is None or b is None else 100*(a-b)


def transitions(gt, reference, candidate, support):
    use = support & (gt < 6)
    a, b = reference == gt, candidate == gt
    def one(region):
        correct = int((region & a).sum())
        wrong = int((region & ~a).sum())
        harm = int((region & a & ~b).sum())
        rescue = int((region & ~a & b).sum())
        n = int(region.sum())
        flips = int((region & (reference != candidate)).sum())
        return dict(valid=n, reference_correct=correct, reference_wrong=wrong, harmed=harm, rescued=rescue,
                    flips=flips, flip_rate=flips/n if n else None,
                    harm_rate=harm/correct if correct else None, rescue_rate=rescue/wrong if wrong else None)
    return dict(**one(use), by_class={str(c): one(use & (gt == c)) for c in range(6)})


def evidence(item, clean, damaged, base, supports):
    result = {}
    for scope in ('full', 'noboundary'):
        gt = item[scope+'_gt']
        result[scope] = {name: dict(clean_cm=cm(gt, clean, region).tolist(),
            missing_cm=cm(gt, damaged, region).tolist(),
            clean_to_missing=transitions(gt, clean, damaged, region),
            base_to_candidate=transitions(gt, base, damaged, region)) for name, region in supports.items()}
    return result
