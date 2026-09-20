"""Pure protocol helpers; no model imports or CUDA initialization."""
import hashlib
import json
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
MODES = {"B2-R05": "r05_teacher_kd", "B2-AVG": "safe_average_teacher_kd"}


def fingerprint(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": h.hexdigest()}


def validate_matched_config(cfg, reference):
    if cfg.get("model_id") not in MODES:
        raise ValueError("Unknown B2 arm")
    if cfg["distillation"]["mode"] != MODES[cfg["model_id"]]:
        raise ValueError("Model/mode mismatch")
    # Only identity and teacher target may differ from the existing B1-KD.
    def controlled(c):
        c = json.loads(json.dumps(c))
        for k in ("model_id", "version", "purpose"):
            c.pop(k, None)
        c["distillation"].pop("mode", None)
        return c
    if controlled(cfg) != controlled(reference):
        raise ValueError("B2 differs from B1-KD beyond teacher target/identity")
    if cfg["seed"] != 42 or cfg["schedule"]["stop_at_step"] != 4000:
        raise ValueError("Expected seed42, 4000-step continuation")
    if cfg["distillation"]["missing_fallback_kl_weight"] != 0:
        raise ValueError("No extra missing-region KL allowed")


def teacher_distribution(logits1, logits5, missing, temperature, mode):
    import torch
    import torch.nn.functional as F
    if temperature <= 0 or missing.dtype != torch.bool:
        raise ValueError("Invalid temperature or mask")
    p1 = F.softmax(logits1 / temperature, dim=1)
    p5 = F.softmax(logits5 / temperature, dim=1)
    if mode == "r05_teacher_kd":
        return p5, p1, torch.ones_like(missing, dtype=p1.dtype)
    if mode == "safe_average_teacher_kd":
        target = torch.where(missing[:, None], p1, (p1 + p5) * 0.5)
        return target, p1, (~missing).to(p1.dtype) * 0.5
    raise ValueError(mode)


def region_masks(damage, radius=8):
    """Chebyshev-distance band around the synthetic corruption interface.
    Image edges alone are NOT interfaces. Boundary overlaps damaged/intact.
    """
    import numpy as np
    from scipy.ndimage import maximum_filter, minimum_filter
    if radius < 1:
        raise ValueError("Boundary radius must be positive")
    damage = np.asarray(damage, dtype=bool)
    outer = maximum_filter(damage, size=2 * radius + 1, mode="nearest")
    inner = minimum_filter(damage, size=2 * radius + 1, mode="nearest")
    return {"whole": np.ones_like(damage), "damaged": damage,
            "intact": ~damage, "boundary": outer & ~inner}


def confusion(gt, pred, mask, classes=6):
    import numpy as np
    valid = mask & (gt >= 0) & (gt < classes)
    g, p = gt[valid].astype(np.int64), pred[valid].astype(np.int64)
    if np.any((p < 0) | (p >= classes)):
        raise ValueError("Prediction out of range")
    return np.bincount(classes * g + p, minlength=classes ** 2).reshape(classes, classes).astype(np.int64)


def safe_output(path, category="records"):
    path = Path(path).resolve()
    path.relative_to((ROOT / category).resolve())
    if path.exists():
        raise FileExistsError("Refusing existing output: " + str(path))
    return path

