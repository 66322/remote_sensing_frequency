import os
import sys
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

ROOT = Path(
    "/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
)
sys.path.insert(0, str(ROOT))

import torch

from model.vitcross_seg_modeling_freqfusion import (
    VisionTransformerFreqFusion,
    CONFIGS,
)

from model.vitcross_seg_modeling_freq_ablation import (
    VisionTransformerFreqAblation,
)

DEVICE = torch.device("cuda:0")

# Use one real formal F3 checkpoint.
CKPT = (
    ROOT
    / "runs"
    / "Thesis_Ch4_NoSR_v1_Vaihingen_seed42"
    / "checkpoints"
    / "model_iter_026000.pth"
)


def make_config():
    c = CONFIGS["R50-ViT-B_16"]
    c.n_classes = 6
    c.n_skip = 3
    c.patches.grid = (16, 16)
    return c


print("=" * 100)
print("VERIFY OLD F3 VS NEW ABLATION F3")
print("checkpoint:", CKPT)
print("=" * 100)

if not CKPT.is_file():
    raise FileNotFoundError(CKPT)

old_model = VisionTransformerFreqFusion(
    make_config(),
    img_size=256,
    num_classes=6,
).to(DEVICE)

new_model = VisionTransformerFreqAblation(
    make_config(),
    img_size=256,
    num_classes=6,
    freq_variant="F3",
).to(DEVICE)

state = torch.load(
    CKPT,
    map_location="cpu",
)

if "model" in state:
    state_dict = state["model"]
else:
    state_dict = state

print("\n[1] Load checkpoint into verified old F3...")
old_model.load_state_dict(
    state_dict,
    strict=True,
)

print("[PASS] old F3 state_dict")

print("\n[2] Load SAME checkpoint into new ablation F3...")
new_model.load_state_dict(
    state_dict,
    strict=True,
)

print("[PASS] new F3 structural compatibility")

old_model.eval()
new_model.eval()

torch.manual_seed(123)
torch.cuda.manual_seed_all(123)

optical = torch.randn(
    1, 3, 256, 256,
    device=DEVICE,
)

dsm = torch.randn(
    1, 256, 256,
    device=DEVICE,
)

with torch.no_grad():
    old_out = old_model(
        optical,
        dsm,
    )

    new_out = new_model(
        optical,
        dsm,
    )

print("\nOUTPUT")
print(" old:", tuple(old_out.shape))
print(" new:", tuple(new_out.shape))

max_diff = float(
    (old_out - new_out)
    .abs()
    .max()
)

mean_diff = float(
    (old_out - new_out)
    .abs()
    .mean()
)

print(" max abs diff :", max_diff)
print(" mean abs diff:", mean_diff)

if old_out.shape != new_out.shape:
    raise RuntimeError(
        "F3 output shape mismatch"
    )

if max_diff > 1e-6:
    raise RuntimeError(
        f"F3 COMPATIBILITY FAIL: max_diff={max_diff}"
    )

print("\n" + "=" * 100)
print("F3 COMPATIBILITY PASS")
print("=" * 100)
