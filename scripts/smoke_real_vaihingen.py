import os
import sys
import random
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
DATA_ROOT = Path("/home/jovyan/zzx/projects_zys/raw_extract/Vaihingen")
PRETRAIN = Path(
    "/home/jovyan/zzx/paper_rebuild/08_assets/pretrained/"
    "ftransunet/R50+ViT-B_16.npz"
)

sys.path.insert(0, str(ROOT))

import numpy as np
import torch
import torch.nn.functional as F
from skimage import io

from model.vitcross_seg_modeling_freqfusion import (
    VisionTransformerFreqFusion,
    CONFIGS,
)

SEED = 42
PATCH = 256
DEVICE = torch.device("cuda:0")

TRAIN_IDS = [
    "1", "3", "7", "11", "13", "17",
    "23", "26", "28", "32", "34", "37"
]

# ISPRS palette
PALETTE = {
    (255, 255, 255): 0,  # Impervious
    (0, 0, 255): 1,      # Building
    (0, 255, 255): 2,    # Low vegetation
    (0, 255, 0): 3,      # Tree
    (255, 255, 0): 4,    # Car
    (255, 0, 0): 5,      # Clutter/background
}


def convert_label(rgb):
    out = np.zeros(rgb.shape[:2], dtype=np.int64)
    matched = np.zeros(rgb.shape[:2], dtype=bool)

    for color, idx in PALETTE.items():
        mask = np.all(rgb[..., :3] == np.array(color), axis=-1)
        out[mask] = idx
        matched |= mask

    if not matched.all():
        bad = int((~matched).sum())
        raise RuntimeError(
            f"Found {bad} pixels with colors outside the 6-class ISPRS palette"
        )

    return out


def load_random_patch(tile_id):
    optical_path = DATA_ROOT / "top" / f"top_mosaic_09cm_area{tile_id}.tif"
    dsm_path = DATA_ROOT / "dsm" / f"dsm_09cm_matching_area{tile_id}.tif"
    label_path = (
        DATA_ROOT / "gts_for_participants" /
        f"top_mosaic_09cm_area{tile_id}.tif"
    )

    for p in [optical_path, dsm_path, label_path]:
        if not p.is_file():
            raise FileNotFoundError(p)

    optical = io.imread(str(optical_path))
    dsm = io.imread(str(dsm_path))
    label_rgb = io.imread(str(label_path))

    if optical.ndim != 3 or optical.shape[2] < 3:
        raise RuntimeError(f"Bad optical shape: {optical.shape}")

    if optical.shape[:2] != dsm.shape[:2]:
        raise RuntimeError(
            f"Optical/DSM shape mismatch: {optical.shape} vs {dsm.shape}"
        )

    if optical.shape[:2] != label_rgb.shape[:2]:
        raise RuntimeError(
            f"Optical/label shape mismatch: {optical.shape} vs {label_rgb.shape}"
        )

    # Vaihingen optical = native 3-band IRRG
    optical = optical[..., :3].astype(np.float32) / 255.0

    dsm = dsm.astype(np.float32)
    dmin = float(dsm.min())
    dmax = float(dsm.max())

    if dmax <= dmin:
        raise RuntimeError("DSM has zero dynamic range")

    dsm = (dsm - dmin) / (dmax - dmin)

    label = convert_label(label_rgb)

    H, W = label.shape

    y = random.randint(0, H - PATCH)
    x = random.randint(0, W - PATCH)

    optical = optical[y:y+PATCH, x:x+PATCH]
    dsm = dsm[y:y+PATCH, x:x+PATCH]
    label = label[y:y+PATCH, x:x+PATCH]

    # Same simple augmentation idea as historical code
    if random.random() < 0.5:
        optical = optical[::-1, :, :]
        dsm = dsm[::-1, :]
        label = label[::-1, :]

    if random.random() < 0.5:
        optical = optical[:, ::-1, :]
        dsm = dsm[:, ::-1]
        label = label[:, ::-1]

    optical = np.ascontiguousarray(optical.transpose(2, 0, 1))
    dsm = np.ascontiguousarray(dsm)
    label = np.ascontiguousarray(label)

    return (
        torch.from_numpy(optical).unsqueeze(0),
        torch.from_numpy(dsm).unsqueeze(0),
        torch.from_numpy(label).unsqueeze(0),
        {
            "tile": tile_id,
            "crop_xy": (x, y),
            "optical_path": str(optical_path),
            "dsm_path": str(dsm_path),
            "label_path": str(label_path),
            "dsm_raw_range": (dmin, dmax),
        }
    )


random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)

print("=" * 100)
print("THESIS CH4 NOSR - REAL VAIHINGEN ONE-STEP SMOKE")
print("=" * 100)

# ----------------------------------------------------------------------
# Real sample
# ----------------------------------------------------------------------
tile_id = random.choice(TRAIN_IDS)

optical, dsm, target, meta = load_random_patch(tile_id)

optical = optical.to(DEVICE)
dsm = dsm.to(DEVICE)
target = target.to(DEVICE)

print("\nDATA")
for k, v in meta.items():
    print(f"  {k}: {v}")

print("  optical shape:", tuple(optical.shape))
print("  dsm shape    :", tuple(dsm.shape))
print("  target shape :", tuple(target.shape))
print("  optical range:",
      float(optical.min()), float(optical.max()))
print("  dsm range    :",
      float(dsm.min()), float(dsm.max()))
print("  label ids    :",
      torch.unique(target).detach().cpu().tolist())

assert optical.shape == (1, 3, PATCH, PATCH)
assert dsm.shape == (1, PATCH, PATCH)
assert target.shape == (1, PATCH, PATCH)

# ----------------------------------------------------------------------
# Model
# ----------------------------------------------------------------------
config = CONFIGS["R50-ViT-B_16"]
config.n_classes = 6
config.n_skip = 3
config.patches.grid = (16, 16)

net = VisionTransformerFreqFusion(
    config,
    img_size=256,
    num_classes=6,
).to(DEVICE)

weights = np.load(str(PRETRAIN))
net.load_from(weights=weights)

print("\n[PASS] model + pretrained weights")

# Confirm SGOR still active
sgor = [
    n for n, _ in net.named_modules()
    if "dysampler" in n.lower()
]
print("SGOR modules:", len(sgor))

if not sgor:
    raise RuntimeError("SGOR not instantiated")

# ----------------------------------------------------------------------
# One real optimizer step
# ----------------------------------------------------------------------
optimizer = torch.optim.SGD(
    net.parameters(),
    lr=0.01,
    momentum=0.9,
    weight_decay=5e-4,
)

net.train()
optimizer.zero_grad(set_to_none=True)

logits = net(optical, dsm)

print("\nMODEL OUTPUT")
print("  logits:", tuple(logits.shape))

if logits.shape != (1, 6, PATCH, PATCH):
    raise RuntimeError(
        f"Unexpected output shape {tuple(logits.shape)}"
    )

loss = F.cross_entropy(logits, target)

print("  CE loss:", float(loss.detach()))

if not torch.isfinite(loss):
    raise RuntimeError("Non-finite loss")

loss.backward()

# ----------------------------------------------------------------------
# Gradient checks
# ----------------------------------------------------------------------
def grad_stats(keyword):
    matched = 0
    nonzero = 0
    max_grad = 0.0

    for name, p in net.named_parameters():
        if keyword.lower() in name.lower():
            matched += 1
            if p.grad is not None:
                g = float(p.grad.detach().abs().max())
                if g > 0:
                    nonzero += 1
                    max_grad = max(max_grad, g)

    return matched, nonzero, max_grad


checks = {
    "Dynamic/root": "root",
    "Transformer": "encoder",
    "FreqFusion": "freq_fusion",
    "SGOR": "dysampler",
    "SegHead": "segmentation_head",
}

print("\nGRADIENT AUDIT")

for label, key in checks.items():
    m, nz, mg = grad_stats(key)
    print(
        f"  {label:14s} "
        f"matched={m:4d} "
        f"nonzero={nz:4d} "
        f"max_grad={mg:.6e}"
    )

m, nz, _ = grad_stats("dysampler")
if m == 0 or nz == 0:
    raise RuntimeError("SGOR gradient failure")

# ----------------------------------------------------------------------
# Parameter update
# ----------------------------------------------------------------------
tracked_name = None
tracked_param = None

for name, p in net.named_parameters():
    if (
        p.requires_grad
        and p.grad is not None
        and p.grad.detach().abs().sum() > 0
    ):
        tracked_name = name
        tracked_param = p
        break

if tracked_param is None:
    raise RuntimeError("No trainable parameter received gradient")

before = tracked_param.detach().clone()

optimizer.step()

after = tracked_param.detach()
delta = float((after - before).abs().max())

print("\nOPTIMIZER")
print("  tracked  :", tracked_name)
print("  max delta:", delta)

if delta <= 0:
    raise RuntimeError("optimizer.step() changed no parameter")

print("\n" + "=" * 100)
print("REAL VAIHINGEN SMOKE PASS")
print("=" * 100)
