import os
import sys
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
sys.path.insert(0, str(ROOT))

import numpy as np
import torch
import torch.nn.functional as F

from model.vitcross_seg_modeling_freqfusion import (
    VisionTransformerFreqFusion,
    CONFIGS,
)

DEVICE = torch.device("cuda:0")
PRETRAIN = Path(
    "/home/jovyan/zzx/paper_rebuild/08_assets/pretrained/"
    "ftransunet/R50+ViT-B_16.npz"
)

torch.manual_seed(42)
torch.cuda.manual_seed_all(42)

print("=" * 90)
print("THESIS CH4 NOSR - ONE OPTIMIZER STEP SMOKE")
print("device   :", DEVICE)
print("pretrain :", PRETRAIN)
print("=" * 90)

# ------------------------------------------------------------
# Model
# ------------------------------------------------------------
config = CONFIGS["R50-ViT-B_16"]
config.n_classes = 6
config.n_skip = 3
config.patches.grid = (16, 16)

net = VisionTransformerFreqFusion(
    config,
    img_size=256,
    num_classes=6,
).to(DEVICE)

print("[PASS] model constructed")

# ------------------------------------------------------------
# Pretrained R50 + ViT-B/16
# ------------------------------------------------------------
assert PRETRAIN.is_file(), PRETRAIN

weights = np.load(str(PRETRAIN))
net.load_from(weights=weights)

print("[PASS] pretrained weights loaded")

# ------------------------------------------------------------
# Confirm SGOR exists
# ------------------------------------------------------------
sgor_modules = [
    name
    for name, module in net.named_modules()
    if "dysampler" in name.lower()
]

print("\nSGOR / dysampler modules:")
for name in sgor_modules:
    print(" ", name)

if not sgor_modules:
    raise RuntimeError(
        "SGOR FAIL: feature_resample=True but no dysampler was instantiated"
    )

print("[PASS] SGOR instantiated")

# ------------------------------------------------------------
# Synthetic input
# F3 real interface:
# optical [B,3,256,256]
# DSM     [B,256,256]
# ------------------------------------------------------------
B = 1

optical = torch.randn(
    B, 3, 256, 256,
    device=DEVICE,
)

dsm = torch.randn(
    B, 256, 256,
    device=DEVICE,
)

target = torch.randint(
    0, 6,
    (B, 256, 256),
    dtype=torch.long,
    device=DEVICE,
)

print("\nINPUT")
print(" optical:", tuple(optical.shape))
print(" dsm    :", tuple(dsm.shape))
print(" target :", tuple(target.shape))

# ------------------------------------------------------------
# Optimizer
# ------------------------------------------------------------
optimizer = torch.optim.SGD(
    net.parameters(),
    lr=0.01,
    momentum=0.9,
    weight_decay=5e-4,
)

net.train()
optimizer.zero_grad(set_to_none=True)

# ------------------------------------------------------------
# Forward
# ------------------------------------------------------------
logits = net(optical, dsm)

print("\nOUTPUT")
print(" logits :", tuple(logits.shape))

if tuple(logits.shape) != (B, 6, 256, 256):
    raise RuntimeError(
        f"Unexpected logits shape: {tuple(logits.shape)}"
    )

if not torch.isfinite(logits).all():
    raise RuntimeError("logits contain NaN/Inf")

print("[PASS] forward")

# ------------------------------------------------------------
# Smoke-only loss
# ------------------------------------------------------------
loss = F.cross_entropy(logits, target)

print(" CE loss:", float(loss.detach()))

if not torch.isfinite(loss):
    raise RuntimeError("loss is NaN/Inf")

# ------------------------------------------------------------
# Backward
# ------------------------------------------------------------
loss.backward()

print("[PASS] backward")

# ------------------------------------------------------------
# Gradient audit
# ------------------------------------------------------------
def report(keyword):
    rows = []
    for name, param in net.named_parameters():
        if keyword.lower() in name.lower():
            if param.grad is None:
                grad = None
            else:
                grad = float(param.grad.detach().abs().mean())
            rows.append((name, grad))
    return rows

checks = {
    "Dynamic/root": "root",
    "Transformer": "encoder",
    "FreqFusion": "freq_fusion",
    "SGOR": "dysampler",
    "SegHead": "segmentation_head",
}

print("\nGRADIENT AUDIT")

for label, keyword in checks.items():
    rows = report(keyword)

    nonzero = [
        (name, grad)
        for name, grad in rows
        if grad is not None and grad > 0
    ]

    print(
        f"{label:14s} "
        f"matched={len(rows):4d} "
        f"nonzero={len(nonzero):4d}"
    )

    for name, grad in nonzero[:3]:
        print(f"    {name}: {grad:.6e}")

# SGOR must really receive gradient
sgor_rows = report("dysampler")
sgor_nonzero = [
    (name, grad)
    for name, grad in sgor_rows
    if grad is not None and grad > 0
]

if not sgor_nonzero:
    raise RuntimeError(
        "SGOR FAIL: dysampler exists but receives no non-zero gradient"
    )

print("[PASS] SGOR gradient")

# ------------------------------------------------------------
# Verify optimizer actually changes a trainable parameter
# Choose a parameter that really received gradient.
# ------------------------------------------------------------
tracked_name = None
tracked_param = None

for name, param in net.named_parameters():
    if (
        param.requires_grad
        and param.grad is not None
        and torch.isfinite(param.grad).all()
        and param.grad.detach().abs().sum() > 0
    ):
        tracked_name = name
        tracked_param = param
        break

if tracked_param is None:
    raise RuntimeError("No parameter with non-zero gradient found")

before = tracked_param.detach().clone()

optimizer.step()

after = tracked_param.detach()

delta = float((after - before).abs().max())
changed = delta > 0

print("\nOPTIMIZER")
print(" tracked :", tracked_name)
print(" changed :", changed)
print(" max delta:", delta)

if not changed:
    raise RuntimeError("optimizer.step() did not update parameter")

print("[PASS] optimizer.step")

print("\n" + "=" * 90)
print("SMOKE PASS")
print("=" * 90)
