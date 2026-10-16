"""FullGT class boundaries, three-pixel Chebyshev tolerance and invalid-neighbour exclusion."""
import numpy as np
from scipy.ndimage import maximum_filter, minimum_filter


def boundary_counts(gt, pred, tolerance=3):
    valid = (gt >= 0) & (gt < 6)
    eligible = minimum_filter(valid.astype(np.uint8), size=2*tolerance+3, mode='constant', cval=0).astype(bool)
    rows = []
    for c in range(5):
        truth = (gt == c).astype(np.uint8)
        estimate = (pred == c).astype(np.uint8)
        tb = ((maximum_filter(truth, size=3) != minimum_filter(truth, size=3)) & eligible)
        pb = ((maximum_filter(estimate, size=3) != minimum_filter(estimate, size=3)) & eligible)
        near_t = maximum_filter(tb.astype(np.uint8), size=2*tolerance+1).astype(bool)
        near_p = maximum_filter(pb.astype(np.uint8), size=2*tolerance+1).astype(bool)
        rows.append(dict(class_id=c, predicted=int(pb.sum()), truth=int(tb.sum()),
                         matched_predicted=int((pb & near_t).sum()), matched_truth=int((tb & near_p).sum())))
    return rows
