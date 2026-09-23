"""CPU-only linear benefit probe. No model/data imports; labels only form targets."""
import numpy as np
from scipy.optimize import minimize, minimize_scalar
from scipy.special import logsumexp, softmax

MODELS = ("confidence", "entropy", "disagreement", "expert", "frequency", "expert_frequency")
FREQUENCY = tuple(f"{name}_r{r}" for r in (2, 8, 32)
                  for name in ("rgb_energy", "dsm_energy", "structure"))


def checkpoint_identity(meta, expected=None):
    # A completed 16k run may select an earlier best checkpoint. Never require
    # best_model.global_step == final training step.
    steps=meta["checkpoint_steps"]
    if len(steps)!=2 or any(not 0<int(step)<=16000 for step in steps):
        raise ValueError("invalid selected checkpoint step")
    identity={k:meta[k] for k in ("checkpoint_rgb","checkpoint_dual","checkpoint_steps")}
    if expected is not None and identity!=expected:
        raise ValueError("development and evaluation expert identities differ")
    return identity


def validate_roles(config, split):
    roles = [config[k] for k in ("fit", "probability_calibration", "threshold_calibration", "evaluation")]
    ids = [x for role in roles for x in role]
    if len(ids) != len(set(ids)) or set(ids) & set(split["historical_exposed_test6"]):
        raise ValueError("role overlap or forbidden Test6")
    if any(not role for role in roles) or not set(ids[:-len(roles[-1])]) <= set(split["train16"]):
        raise ValueError("head development must use Train16")
    if set(roles[-1]) != set(split["val2"]):
        raise ValueError("evaluation must be frozen Val2")


def expert_features(sample):
    a, b = np.asarray(sample["rgb_prob"], np.float64), np.asarray(sample["dual_prob"], np.float64)
    if a.ndim != 2 or a.shape != b.shape or a.shape[0] != 6:
        raise ValueError("expected matched (6,N) probabilities")
    if not np.isfinite(a).all() or not np.isfinite(b).all() or np.any(a < 0) or np.any(b < 0):
        raise ValueError("invalid probabilities")
    if not np.allclose(a.sum(0), 1, atol=1e-5) or not np.allclose(b.sum(0), 1, atol=1e-5):
        raise ValueError("probabilities must sum to one")
    e1, e5 = [-(p * np.log(p + 1e-8)).sum(0) for p in (a, b)]
    mid = (a + b) / 2
    js = .5 * ((a*np.log((a+1e-8)/(mid+1e-8))).sum(0) + (b*np.log((b+1e-8)/(mid+1e-8))).sum(0))
    f = {"confidence": b.max(0)-a.max(0), "entropy": e1-e5, "disagreement": js}
    names = [f"rgb_p{c}" for c in range(6)] + [f"dual_p{c}" for c in range(6)]
    names += ["confidence", "entropy", "disagreement", "rgb_entropy", "dual_entropy"]
    x = np.column_stack([a.T, b.T, f["confidence"], f["entropy"], js, e1, e5])
    return x, names, f


def features(sample, model):
    x, names, scores = expert_features(sample)
    if model in ("confidence", "entropy", "disagreement"):
        return scores[model][:, None], [model]
    if model == "expert":
        return x, names
    if model not in ("frequency", "expert_frequency"):
        raise ValueError(model)
    freq = np.column_stack([np.log1p(np.maximum(sample[k], 0)*10000) if "energy" in k
                            else sample[k] for k in FREQUENCY]).astype(np.float64)
    if not np.isfinite(freq).all():
        raise ValueError("nonfinite frequency feature")
    return (freq, list(FREQUENCY)) if model == "frequency" else (np.column_stack([x, freq]), names+list(FREQUENCY))


def targets(sample):
    y = np.asarray(sample["labels"])
    a, b = sample["rgb_prob"].argmax(0), sample["dual_prob"].argmax(0)
    if y.shape != a.shape or np.any(y < 0) or np.any(y >= 6):
        raise ValueError("invalid labels")
    # 0: gain; 1: harm; 2: both wrong on eligible disagreement pixels.
    target = np.where(b == y, 0, np.where(a == y, 1, 2))
    return target.astype(np.int64), a != b, a, b


def objective(flat, x, y, l2):
    w = flat.reshape(x.shape[1], 3)
    logits = x @ w
    loss = np.mean(logsumexp(logits, axis=1)-logits[np.arange(len(y)), y])
    loss += .5*l2*np.sum(w[:-1]**2)
    residual = softmax(logits, axis=1)
    residual[np.arange(len(y)), y] -= 1
    grad = x.T @ residual / len(y)
    grad[:-1] += l2*w[:-1]
    return float(loss), grad.ravel()


def fit(x, y, l2=.01, maxiter=300):
    if min(np.bincount(y, minlength=3)) < 20:
        raise ValueError("need >=20 training disagreements of each outcome; no automatic relabeling")
    mean, scale = x.mean(0), np.maximum(x.std(0), 1e-6)
    design = np.column_stack([(x-mean)/scale, np.ones(len(x))])
    result = minimize(objective, np.zeros(design.shape[1]*3), args=(design, y, l2),
                      jac=True, method="L-BFGS-B", options={"maxiter": maxiter, "ftol": 1e-10})
    if not result.success:
        raise RuntimeError(f"probe optimization failed: {result.message}")
    return dict(mean=mean.tolist(), scale=scale.tolist(), weights=result.x.reshape(-1, 3).tolist(),
                temperature=1., optimizer_iterations=int(result.nit), training_n=int(len(y)),
                training_outcomes=np.bincount(y, minlength=3).tolist())


def logits(model, x):
    z = (x-np.asarray(model["mean"]))/np.asarray(model["scale"])
    return np.column_stack([z, np.ones(len(z))]) @ np.asarray(model["weights"])


def calibrate_temperature(model, x, y, bounds):
    raw = logits(model, x)
    def loss(t):
        z = raw/t
        return float(np.mean(logsumexp(z, axis=1)-z[np.arange(len(y)), y]))
    result = minimize_scalar(loss, bounds=tuple(bounds), method="bounded")
    if not result.success or not np.isfinite(result.fun):
        raise RuntimeError("temperature calibration failed")
    return float(result.x)


def probabilities(model, x):
    return softmax(logits(model, x)/model["temperature"], axis=1)


def choose_threshold(groups, thresholds, budget):
    """Only threshold-calibration groups; H denominator includes agreements."""
    rows = []
    for threshold in thresholds:
        harms, rescues = [], []
        for score, target, eligible in groups:
            choose = eligible & (score > threshold)
            harms.append(float(np.mean(choose & (target == 1))))
            rescues.append(float(np.mean(choose & (target == 0))))
        rows.append(dict(threshold=threshold, worst_group_harm=max(harms), mean_rescue=float(np.mean(rescues))))
    feasible = [r for r in rows if r["worst_group_harm"] <= budget]
    if not feasible:
        raise RuntimeError("no feasible threshold including RGB fallback")
    best = max(feasible, key=lambda r: (r["mean_rescue"], r["threshold"]))
    return best, rows


def binary_calibration(p, y, bins=15):
    p, y = np.asarray(p), np.asarray(y, float)
    if not len(p):
        return dict(ece=None, brier=None, positive_rate=None)
    index = np.minimum((np.clip(p, 0, 1)*bins).astype(int), bins-1)
    ece = sum(np.mean(index == b)*abs(p[index == b].mean()-y[index == b].mean())
              for b in range(bins) if np.any(index == b))
    return dict(ece=float(ece), brier=float(np.mean((p-y)**2)), positive_rate=float(y.mean()))


def routing_metrics(labels, rgb, dual, choose):
    labels, rgb, dual, choose = map(np.asarray, (labels, rgb, dual, choose))
    pred = np.where(choose, dual, rgb)
    cm = np.bincount(6*labels.astype(int)+pred.astype(int), minlength=36).reshape(6,6)
    tp = np.diag(cm)
    union = cm.sum(0)+cm.sum(1)-tp
    iou = np.divide(tp, union, out=np.full(6, np.nan), where=union > 0)
    harm = float(np.mean((rgb == labels) & (pred != labels)))
    rescue = float(np.mean((rgb != labels) & (pred == labels)))
    return dict(sample_n=len(labels), harm=harm, rescue=rescue, accuracy_gain=rescue-harm,
                coverage=float(np.mean(choose)), sampled_mIoU_fg5=float(np.nanmean(iou[:5])),
                Car_IoU=None if not np.isfinite(iou[4]) else float(iou[4]),
                Building_IoU=None if not np.isfinite(iou[1]) else float(iou[1]))
