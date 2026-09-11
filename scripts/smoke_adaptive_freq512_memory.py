import sys
from copy import deepcopy
from pathlib import Path

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model.vitcross_seg_modeling_freqfusion import CONFIGS
from model.vitcross_seg_modeling_adaptive_freq import (
    VisionTransformerAdaptiveFreq,
)


DEVICE = torch.device("cuda")
PATCH = 512
GRID = (32, 32)
BATCH = 4
NUM_CLASSES = 6


def make_config():
    config = deepcopy(
        CONFIGS["R50-ViT-B_16"]
    )

    config.n_classes = NUM_CLASSES
    config.n_skip = 3
    config.patches.grid = GRID

    return config


print("=" * 100)
print("F4 ADAPTIVE FREQUENCY 512 MEMORY GATE")
print("=" * 100)
print("device :", DEVICE)
print("patch  :", PATCH)
print("grid   :", GRID)
print("batch  :", BATCH)
print()


torch.manual_seed(42)
torch.cuda.manual_seed_all(42)

model = VisionTransformerAdaptiveFreq(
    make_config(),
    img_size=PATCH,
    num_classes=NUM_CLASSES,
    gate_init=0.10,
).to(DEVICE)

model.train()

# Same optimizer family as Stage-2/Stage-3.
optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=6e-5,
    betas=(0.9, 0.999),
    weight_decay=0.01,
)

x = torch.randn(
    BATCH,
    3,
    PATCH,
    PATCH,
    device=DEVICE,
)

# Real model interface:
# DSM = [B, H, W]
dsm = torch.randn(
    BATCH,
    PATCH,
    PATCH,
    device=DEVICE,
)

target = torch.randint(
    0,
    NUM_CLASSES,
    (
        BATCH,
        PATCH,
        PATCH,
    ),
    device=DEVICE,
    dtype=torch.long,
)

torch.cuda.empty_cache()
torch.cuda.reset_peak_memory_stats()

optimizer.zero_grad(
    set_to_none=True
)

print("[RUN] forward")

logits = model(
    x,
    dsm,
)

print(
    "[PASS] forward",
    tuple(logits.shape),
)

loss = F.cross_entropy(
    logits,
    target,
)

print(
    f"[RUN] loss={loss.item():.6f}"
)

print("[RUN] backward")

loss.backward()

print("[PASS] backward")

print("[RUN] optimizer.step")

optimizer.step()

torch.cuda.synchronize()

print("[PASS] optimizer.step")

allocated = (
    torch.cuda.memory_allocated()
    / 1024**3
)

reserved = (
    torch.cuda.memory_reserved()
    / 1024**3
)

peak_alloc = (
    torch.cuda.max_memory_allocated()
    / 1024**3
)

print()
print("=" * 100)
print("MEMORY RESULT")
print("=" * 100)

print(
    f"current allocated : "
    f"{allocated:.3f} GB"
)

print(
    f"current reserved  : "
    f"{reserved:.3f} GB"
)

print(
    f"peak allocated    : "
    f"{peak_alloc:.3f} GB"
)

print()

# Inspect adaptive gates after one train-mode
# forward by temporarily running eval.
model.eval()

with torch.no_grad():
    _ = model(
        x[:1],
        dsm[:1],
    )

print("GATES AFTER INITIALIZATION")

for stage, gate in (
    model.get_last_gates()
):
    print(
        f"stage={stage} | "
        f"shape={tuple(gate.shape)} | "
        f"mean={gate.mean().item():.6f} | "
        f"min={gate.min().item():.6f} | "
        f"max={gate.max().item():.6f}"
    )

print()
print(
    "ALL F4 512 MEMORY "
    "CHECKS PASSED"
)
