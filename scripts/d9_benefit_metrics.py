"""Small, dependency-light D9 score and benefit metrics."""

import numpy as np


def benefit_from_probabilities(p_rgb_true, p_dual_true, eps=1e-8):
    """CE(RGB, y) - CE(dual, y), positive when DSM lowers CE."""
    a = np.clip(np.asarray(p_rgb_true, dtype=np.float64), eps, 1.0)
    b = np.clip(np.asarray(p_dual_true, dtype=np.float64), eps, 1.0)
    return np.log(b) - np.log(a)


def rank_metrics(score, benefit, neutral=0.01):
    """Exact tie-aware AUROC/AP on non-neutral benefit and harm cases.

    Large scores predict positive benefit. Harm metrics reverse the score.
    Pixels are diagnostic observations, not independent inferential units.
    """
    score = np.asarray(score, dtype=np.float64)
    benefit = np.asarray(benefit, dtype=np.float64)
    keep = np.isfinite(score) & np.isfinite(benefit) & (np.abs(benefit) > neutral)
    x = score[keep]
    y = benefit[keep] > 0
    out = {"count": int(x.size), "benefit_count": int(y.sum()),
           "harm_count": int((~y).sum()), "neutral_excluded": int(score.size - x.size)}
    if x.size == 0 or y.all() or (~y).all():
        out.update(benefit_auroc=None, benefit_auprc=None,
                   harm_auroc=None, harm_auprc=None)
        return out
    out["benefit_auroc"], out["benefit_auprc"] = _binary_rank(x, y)
    out["harm_auroc"], out["harm_auprc"] = _binary_rank(-x, ~y)
    return out


def _binary_rank(score, label):
    order = np.argsort(score, kind="mergesort")
    x, y = score[order], label[order].astype(np.int64)
    ends = np.r_[np.flatnonzero(x[1:] != x[:-1]) + 1, x.size]
    starts = np.r_[0, ends[:-1]]
    positives = np.add.reduceat(y, starts)
    negatives = ends - starts - positives
    n_pos, n_neg = int(positives.sum()), int(negatives.sum())
    neg_before = np.cumsum(negatives) - negatives
    auroc = np.sum(positives * (neg_before + 0.5 * negatives)) / (n_pos * n_neg)
    tp = np.cumsum(positives[::-1])
    fp = np.cumsum(negatives[::-1])
    precision = tp / (tp + fp)
    auprc = np.sum(precision * positives[::-1]) / n_pos
    return float(auroc), float(auprc)


def selected_harm(choose_dual, benefit, neutral=0.01):
    choose = np.asarray(choose_dual, dtype=bool)
    delta = np.asarray(benefit)
    selected = int(choose.sum())
    harmed = int(np.count_nonzero(choose & (delta < -neutral)))
    return {"selected_dual": selected, "selected_harm": harmed,
            "selected_harm_rate": harmed / selected if selected else None,
            "harm_per_valid": harmed / choose.size if choose.size else None}


def apply_known_missing_fallback(choose_dual, region_mask, family):
    """Force RGB only where DSM is absent; degraded DSM remains selectable."""
    choose = np.asarray(choose_dual, dtype=bool)
    if family not in ("global_missing", "local_missing"):
        return choose
    if region_mask is None:
        raise ValueError("known-missing condition requires a region mask")
    mask = np.asarray(region_mask, dtype=bool)
    if mask.shape != choose.shape:
        raise ValueError("availability mask shape mismatch")
    return choose & ~mask
