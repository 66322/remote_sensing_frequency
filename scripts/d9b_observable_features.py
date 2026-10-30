"""Fixed, label-free inference features for the exploratory D9B screen."""

import numpy as np

RADII = (2, 8)
GRAY_WEIGHTS = np.array([0.299, 0.587, 0.114], np.float32)


def _at(image, y, x):
    return image[np.clip(y, 0, image.shape[0] - 1),
                 np.clip(x, 0, image.shape[1] - 1)]


def sampled_observables(rgb, dsm, y, x):
    """Return RGB/DSM appearance and unsigned cross-modal edge alignment.

    `y,x` may come from ground truth for prototype construction, but inference
    features read only RGB, DSM and pixel coordinates. Both radii are fixed.
    """
    y, x = np.asarray(y, np.int64), np.asarray(x, np.int64)
    if y.shape != x.shape or rgb.shape[:2] != dsm.shape:
        raise ValueError("coordinate or modality shape mismatch")
    color = _at(rgb, y, x).astype(np.float32)
    height = _at(dsm, y, x).astype(np.float32)
    rgb_parts, dsm_parts, alignments = [color], [height[:, None]], []
    for radius in RADII:
        rgb_x = (_at(rgb, y, x + radius) - _at(rgb, y, x - radius)) @ GRAY_WEIGHTS
        rgb_y = (_at(rgb, y + radius, x) - _at(rgb, y - radius, x)) @ GRAY_WEIGHTS
        dsm_x = _at(dsm, y, x + radius) - _at(dsm, y, x - radius)
        dsm_y = _at(dsm, y + radius, x) - _at(dsm, y - radius, x)
        rgb_mag = np.sqrt(rgb_x * rgb_x + rgb_y * rgb_y)
        dsm_mag = np.sqrt(dsm_x * dsm_x + dsm_y * dsm_y)
        alignment = np.abs(rgb_x * dsm_x + rgb_y * dsm_y) / (rgb_mag * dsm_mag + 1e-6)
        rgb_parts.append(rgb_mag[:, None])
        dsm_parts.append(dsm_mag[:, None])
        alignments.append(np.clip(alignment, 0, 1))
    return (np.concatenate(rgb_parts, axis=1),
            np.concatenate(dsm_parts, axis=1),
            np.mean(np.stack(alignments, axis=1), axis=1))


def prototype_similarity(features, predicted_class, stats, modality):
    """Class-conditional Gaussian similarity with Train16-only statistics."""
    values = np.asarray(features, np.float64)
    classes = np.asarray(predicted_class, np.int64)
    spec = stats[modality]
    global_mean = np.asarray(spec["global_mean"])
    global_std = np.asarray(spec["global_std"])
    class_mean = np.asarray(spec["class_mean"])
    class_std = np.asarray(spec["class_std"])
    if values.ndim != 2 or values.shape[1] != global_mean.size or classes.shape != (values.shape[0],):
        raise ValueError("prototype feature dimensions mismatch")
    if classes.min() < 0 or classes.max() >= class_mean.shape[0]:
        raise ValueError("predicted class outside prototype table")
    z = (values - global_mean) / global_std
    dist = np.mean(((z - class_mean[classes]) / np.maximum(class_std[classes], 0.5)) ** 2, axis=1)
    return np.exp(-0.5 * dist)


def screen_scores(rgb_prob, dual_prob, rgb_features, dsm_features, alignment, stats):
    """Predeclared unfitted controls; larger values favour the dual expert."""
    p1, p5 = np.asarray(rgb_prob), np.asarray(dual_prob)
    if p1.shape != p5.shape or p1.ndim != 2:
        raise ValueError("probability arrays must match (classes, pixels)")
    cls1, cls5 = p1.argmax(0), p5.argmax(0)
    sim1 = prototype_similarity(rgb_features, cls1, stats, "rgb")
    sim5_rgb = prototype_similarity(rgb_features, cls5, stats, "rgb")
    sim5_dsm = prototype_similarity(dsm_features, cls5, stats, "dsm")
    semantic = 0.5 * (sim5_rgb + sim5_dsm) - sim1
    frequency = 2 * np.asarray(alignment) - 1
    eps = 1e-8
    e1 = -(p1 * np.log(p1 + eps)).sum(0)
    e5 = -(p5 * np.log(p5 + eps)).sum(0)
    entropy = e1 - e5
    mid = (p1 + p5) / 2
    js = 0.5 * ((p1 * np.log((p1 + eps) / (mid + eps))).sum(0)
                + (p5 * np.log((p5 + eps) / (mid + eps))).sum(0))
    signed_js = np.sign(entropy) * (js / np.log(2))
    entropy_norm = entropy / np.log(p1.shape[0])
    scores = {
        "confidence_margin": p5.max(0) - p1.max(0),
        "entropy_margin": entropy,
        "semantic_prototype": semantic,
        "frequency_alignment": frequency,
        "semantic_plus_frequency": 0.5 * (semantic + frequency),
        "semantic_frequency_expert": 0.25 * (semantic + frequency + entropy_norm + signed_js),
    }
    if any(not np.all(np.isfinite(value)) for value in scores.values()):
        raise RuntimeError("nonfinite D9B score")
    return scores, cls1, cls5
