"""Frozen decoder measurements at fixed pixels, with sliding-window averaging."""
import numpy as np
import torch
import torch.nn.functional as F


def decoder_maps(value):
    if value.ndim != 4:
        raise ValueError("decoder hook did not return BCHW")
    mean = value.mean(dim=1)
    magnitude = value.abs().mean(dim=1)
    local = (mean - F.avg_pool2d(mean[:, None], 5, stride=1, padding=2)[:, 0]).abs()
    return torch.stack((mean, magnitude, local), dim=1)


def infer_at_pixels(net, optical, dsm, yy, xx, patch, stride, batch, optical_only,
                    return_scores=False):
    """Average decoder features over every covering inference window.

    Coordinates are supplied by a frozen cache or by the complete valid image.
    No label is consulted by this function. Logits use the same window averaging
    as the existing R01/R05 inference code when return_scores=True.
    """
    from train_rebuild_v1_r02_budget_pilot import positions, DEVICE
    h, w = optical.shape[:2]
    yy, xx = np.asarray(yy), np.asarray(xx)
    if yy.shape != xx.shape or yy.ndim != 1 or not len(yy):
        raise ValueError("invalid sample coordinates")
    if np.any(yy < 0) or np.any(xx < 0) or np.any(yy >= h) or np.any(xx >= w):
        raise ValueError("coordinates outside tile")
    if len(np.unique(yy.astype(np.int64) * w + xx)) != len(yy):
        raise ValueError("duplicate coordinates")
    index = np.full((h, w), -1, dtype=np.int32)
    index[yy, xx] = np.arange(len(yy), dtype=np.int32)
    feature_sum = np.zeros((3, len(yy)), np.float32)
    feature_count = np.zeros(len(yy), np.uint16)
    score_sum = np.zeros((6, len(yy)), np.float32) if return_scores else None
    hook_values = []

    def capture(_module, _inputs, output):
        hook_values.append(output)

    handle = net.decoder.register_forward_hook(capture)
    coords = [(y, x) for y in positions(h, patch, stride)
                    for x in positions(w, patch, stride)]
    try:
        with torch.inference_mode():
            for start in range(0, len(coords), batch):
                bc = coords[start:start + batch]
                op = np.stack([optical[y:y+patch, x:x+patch].transpose(2, 0, 1) for y, x in bc])
                op_t = torch.from_numpy(np.ascontiguousarray(op)).to(DEVICE)
                if optical_only:
                    logits = net(op_t)
                else:
                    ds = np.stack([dsm[y:y+patch, x:x+patch] for y, x in bc])
                    ds_t = torch.from_numpy(np.ascontiguousarray(ds)).to(DEVICE)
                    logits = net(op_t, ds_t)
                if len(hook_values) != 1:
                    raise RuntimeError("decoder hook expected exactly one call")
                maps = decoder_maps(hook_values.pop()).cpu().numpy()
                if maps.shape[2:] != (patch, patch):
                    raise RuntimeError("decoder and prediction grids differ")
                values = logits.detach().cpu().numpy() if return_scores else None
                for j, (top, left) in enumerate(bc):
                    local_index = index[top:top+patch, left:left+patch]
                    sy, sx = np.nonzero(local_index >= 0)
                    if not len(sy):
                        continue
                    ids = local_index[sy, sx]
                    feature_sum[:, ids] += maps[j, :, sy, sx].T
                    feature_count[ids] += 1
                    if return_scores:
                        score_sum[:, ids] += values[j, :, sy, sx].T
    finally:
        handle.remove()
    if np.any(feature_count == 0):
        raise RuntimeError("some sampled pixels lacked inference coverage")
    features = feature_sum / feature_count[None]
    scores = score_sum / feature_count[None] if return_scores else None
    if not np.isfinite(features).all() or (scores is not None and not np.isfinite(scores).all()):
        raise RuntimeError("nonfinite frozen expert output")
    return features, scores
