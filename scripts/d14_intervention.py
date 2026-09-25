"""Pure DSM content interventions; none represents recorded missingness."""
import numpy as np

CONDITIONS = ("clean", "zero_present", "shift_half")


def intervene(dsm, condition):
    if dsm.ndim != 2 or not np.isfinite(dsm).all():
        raise ValueError("DSM must be a finite 2D array")
    if condition == "clean":
        result = dsm
    elif condition == "zero_present":
        result = np.zeros_like(dsm)
    elif condition == "shift_half":
        result = np.roll(dsm, (dsm.shape[0] // 2, dsm.shape[1] // 2), axis=(0, 1))
    else:
        raise ValueError(condition)
    return np.ascontiguousarray(result), None  # None means every pixel available.


def changed_predictions(gt, clean, altered):
    if gt.shape != clean.shape or gt.shape != altered.shape:
        raise ValueError("prediction/label shape mismatch")
    valid = (gt != 255) & (gt < 6)
    flipped = valid & (clean != altered)
    counts = np.bincount(gt[flipped], minlength=6).astype(np.int64)
    support = np.bincount(gt[valid], minlength=6).astype(np.int64)
    return dict(flip_count=int(flipped.sum()), valid=int(valid.sum()),
                flip_fraction=float(flipped.sum() / valid.sum()),
                flip_by_true_class=counts.tolist(), support_by_true_class=support.tolist())
