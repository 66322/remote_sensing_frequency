"""Label-free perturbations/features and tie-aware diagnostic routing curves."""
import numpy as np

CONDITIONS = ("clean", "roll4", "roll16", "roll32", "edge4", "edge16", "edge32",
              "dsm_blur5", "dsm_noise_std010", "dsm_zero")
RADII = (2, 8, 32)


def translate(dsm, pixels, circular):
    if not 0 < pixels < dsm.shape[1]:
        raise ValueError("invalid horizontal shift")
    out = np.roll(dsm, pixels, axis=1)
    if not circular:
        out[:, :pixels] = dsm[:, :1]
    return np.ascontiguousarray(out)


def amplitude_error(reference, treated):
    # Full-tile Fourier amplitude, including DC; never compare cropped spectra.
    ref = np.abs(np.fft.rfft2(reference))
    obs = np.abs(np.fft.rfft2(treated))
    return float(np.linalg.norm(obs - ref) / max(np.linalg.norm(ref), 1e-12))


def sampled_structure(rgb, dsm, yy, xx):
    """Local band-pass energy and cross-modal spatial correlation, not reliability.

    Box-filter residuals are frequency-selective descriptors, not a DCT/SGMA
    implementation. Return individual scales; do not fit a weighted combination.
    """
    from scipy.ndimage import uniform_filter
    gray = np.asarray(rgb, np.float32) @ np.array([.299, .587, .114], np.float32)
    height = np.asarray(dsm, np.float32)
    out = {}
    for radius in RADII:
        width = 2 * radius + 1
        a = gray - uniform_filter(gray, size=width, mode="reflect")
        b = height - uniform_filter(height, size=width, mode="reflect")
        ea = uniform_filter(a * a, size=width, mode="reflect")
        eb = uniform_filter(b * b, size=width, mode="reflect")
        cross = uniform_filter(a * b, size=width, mode="reflect")
        corr = np.clip(cross / np.sqrt(ea * eb + 1e-12), -1, 1)
        out[f"rgb_energy_r{radius}"] = ea[yy, xx]
        out[f"dsm_energy_r{radius}"] = eb[yy, xx]
        out[f"structure_r{radius}"] = np.abs(corr[yy, xx])
    return out


def rescue_at_harm(score, rgb_correct, dual_correct, available, budgets=(0., .001, .005, .01, .02)):
    """Post-hoc ranking envelope, NOT calibrated deployment thresholds.

    H and R use all supplied valid pixels as denominator. Include whole score
    tie groups only, and allow choosing none. Thus a constant score cannot
    exploit the ordering of ground-truth labels inside a tied group.
    """
    score = np.asarray(score)
    rgb_correct, dual_correct = np.asarray(rgb_correct, bool), np.asarray(dual_correct, bool)
    eligible = np.asarray(available, bool) & np.isfinite(score)
    n = len(score)
    if not n:
        return []
    idx = np.flatnonzero(eligible)
    idx = idx[np.argsort(-score[idx], kind="stable")]
    if len(idx):
        ends = np.r_[np.flatnonzero(score[idx][1:] != score[idx][:-1]) + 1, len(idx)]
        h = np.r_[0, np.cumsum(rgb_correct[idx] & ~dual_correct[idx])[ends - 1]] / n
        r = np.r_[0, np.cumsum(~rgb_correct[idx] & dual_correct[idx])[ends - 1]] / n
        coverage = np.r_[0, ends] / n
    else:
        h = r = coverage = np.array([0.])
    rows = []
    for budget in budgets:
        feasible = np.flatnonzero(h <= budget)
        # Best rescue at or below budget; for ties keep the smaller coverage.
        i = feasible[np.argmax(r[feasible])]
        rows.append(dict(harm_budget=budget, harm=float(h[i]), rescue=float(r[i]),
                         accuracy_gain=float(r[i] - h[i]), coverage=float(coverage[i])))
    return rows
