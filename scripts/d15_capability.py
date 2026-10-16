"""D15 deterministic input treatments and same-pixel agreement counts."""
import numpy as np
import torch
import torch.nn.functional as F
from scipy.ndimage import uniform_filter


def as_three_channels(dsm):
    if dsm.ndim != 2 or not np.isfinite(dsm).all():
        raise RuntimeError("invalid normalized DSM")
    return np.ascontiguousarray(np.repeat(dsm[:, :, None], 3, axis=2))


def down_restore(x, factor):
    if factor not in (2, 4):
        raise ValueError(factor)
    t = torch.from_numpy(np.ascontiguousarray(x.transpose(2, 0, 1)))[None].float()
    h, w = x.shape[:2]
    small = F.interpolate(t, size=(h // factor, w // factor), mode="bilinear",
                          align_corners=False, antialias=True)
    full = F.interpolate(small, size=(h, w), mode="bilinear", align_corners=False)
    return np.ascontiguousarray(full[0].permute(1, 2, 0).numpy())


def condition_data(optical, dsm, name):
    op = np.ascontiguousarray(optical)
    ds = np.ascontiguousarray(dsm)
    if name == "clean":
        pass
    elif name == "rgb_down2":
        op = down_restore(op, 2)
    elif name in ("rgb_down4", "rgb_down4_dsm_zero"):
        op = down_restore(op, 4)
        if name == "rgb_down4_dsm_zero":
            ds = np.zeros_like(ds)
    elif name == "rgb_blur5":
        op = uniform_filter(op, size=(5, 5, 1), mode="reflect").astype(np.float32)
    elif name == "rgb_local_down4_q1":
        down = down_restore(op, 4)
        h, w = op.shape[:2]
        y, x = h // 4, w // 4
        op = op.copy()
        op[y:y + h // 2, x:x + w // 2] = down[y:y + h // 2, x:x + w // 2]
    else:
        raise ValueError(name)
    return np.ascontiguousarray(op), np.ascontiguousarray(ds)


def second_stream(model, treated_optical, treated_dsm):
    if model == "C-OO-QD":
        return np.ascontiguousarray(treated_optical.mean(axis=2).astype(np.float32))
    if model == "R05":
        return treated_dsm
    raise ValueError(model)


def joint(gt, reference, candidate, ignore_index=255):
    valid = gt != ignore_index
    a, b = reference == gt, candidate == gt
    return dict(valid=int(valid.sum()), both_correct=int((valid & a & b).sum()),
                only_r01_correct=int((valid & a & ~b).sum()),
                only_candidate_correct=int((valid & ~a & b).sum()),
                both_wrong=int((valid & ~a & ~b).sum()))
