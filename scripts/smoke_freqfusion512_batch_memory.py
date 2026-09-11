import os
import sys
import gc
import copy
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

ROOT = Path(
    "/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
)

# Make project root importable when this file is executed from scripts/.
sys.path.insert(0, str(ROOT))

import numpy as np
import torch
import torch.nn.functional as F

from model.vitcross_seg_modeling_freq_ablation import (
    VisionTransformerFreqAblation,
    CONFIGS,
)

PRETRAIN = (
    ROOT.parent
    / "08_assets"
    / "pretrained"
    / "ftransunet"
    / "R50+ViT-B_16.npz"
)

if not PRETRAIN.is_file():
    raise FileNotFoundError(
        f"Pretrained weight not found: {PRETRAIN}"
    )

DEVICE = torch.device("cuda:0")

# Test in ascending order.
# 512x512 with a 32x32 Transformer token grid is much
# more memory-intensive than the original 256x256 setup.
BATCHES = [1, 2, 4, 8, 16]

results = []


def cleanup():
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.synchronize()


def build_model():
    config = copy.deepcopy(
        CONFIGS["R50-ViT-B_16"]
    )

    config.n_classes = 6
    config.n_skip = 3

    # IMPORTANT:
    # Original 256x256 training uses:
    #   grid = 256 / 16 = 16
    #
    # For 512x512 we must preserve the same effective
    # 16-pixel token stride:
    #   grid = 512 / 16 = 32
    #
    # Otherwise Transformer output remains 16x16 while
    # ResNet skip features grow with the input, breaking
    # the required 2:1 HR/LR ratio in FreqFusion.
    config.patches.grid = (
        512 // 16,
        512 // 16,
    )

    print(
        "MODEL GRID:",
        config.patches.grid,
    )

    net = VisionTransformerFreqAblation(
        config,
        img_size=512,
        num_classes=6,
        freq_variant="F3",
    ).to(DEVICE)

    weights = np.load(
        str(PRETRAIN)
    )

    net.load_from(
        weights=weights
    )

    return net


print("=" * 110)
print("F3 512x512 REAL ADAMW MEMORY GATE")
print("=" * 110)

for batch in BATCHES:

    cleanup()

    net = None
    optimizer = None
    optical = None
    dsm = None
    target = None
    logits = None
    loss = None

    try:
        print()
        print("-" * 110)
        print(
            f"TEST batch={batch}, "
            f"crop=512, variant=F3"
        )
        print("-" * 110)

        net = build_model()
        net.train()

        optimizer = torch.optim.AdamW(
            net.parameters(),
            lr=6e-5,
            weight_decay=0.01,
        )

        torch.cuda.reset_peak_memory_stats()

        optical = torch.randn(
            batch,
            3,
            512,
            512,
            device=DEVICE,
        )

        dsm = torch.randn(
            batch,
            512,
            512,
            device=DEVICE,
        )

        target = torch.randint(
            low=0,
            high=6,
            size=(batch, 512, 512),
            device=DEVICE,
        )

        optimizer.zero_grad(
            set_to_none=True
        )

        logits = net(
            optical,
            dsm,
        )

        if logits.shape != (
            batch,
            6,
            512,
            512,
        ):
            raise RuntimeError(
                f"wrong logits shape: "
                f"{tuple(logits.shape)}"
            )

        loss = F.cross_entropy(
            logits,
            target,
        )

        loss.backward()

        # Important:
        # AdamW optimizer states are created here.
        optimizer.step()

        torch.cuda.synchronize()

        allocated = (
            torch.cuda.max_memory_allocated()
            / 1024**3
        )

        reserved = (
            torch.cuda.max_memory_reserved()
            / 1024**3
        )

        print(
            f"[PASS] batch={batch}"
        )

        print(
            f"loss          : "
            f"{loss.item():.6f}"
        )

        print(
            f"peak allocated: "
            f"{allocated:.3f} GB"
        )

        print(
            f"peak reserved : "
            f"{reserved:.3f} GB"
        )

        results.append(
            (
                batch,
                "PASS",
                allocated,
                reserved,
            )
        )

    except torch.cuda.OutOfMemoryError:

        print(
            f"[OOM] batch={batch}"
        )

        results.append(
            (
                batch,
                "OOM",
                None,
                None,
            )
        )

    finally:

        try:
            del loss
            del logits
            del target
            del dsm
            del optical
            del optimizer
            del net
        except Exception:
            pass

        cleanup()


print()
print("=" * 110)
print("SUMMARY")
print("=" * 110)

for batch, status, allocated, reserved in results:

    if status == "PASS":

        print(
            f"batch={batch:<3d} "
            f"PASS | "
            f"allocated={allocated:.3f} GB | "
            f"reserved={reserved:.3f} GB"
        )

    else:

        print(
            f"batch={batch:<3d} OOM"
        )

print("=" * 110)

# Conservative recommendation:
# leave substantial memory headroom for real augmentation
# and runtime fluctuations.

safe = []

for batch, status, allocated, reserved in results:

    if (
        status == "PASS"
        and reserved is not None
        and reserved <= 68.0
    ):
        safe.append(batch)

if safe:

    print(
        "RECOMMENDED MAX PHYSICAL BATCH:",
        max(safe),
    )

    print(
        "Target effective batch = 16"
    )

    if 16 % max(safe) == 0:

        print(
            "Gradient accumulation steps:",
            16 // max(safe),
        )

else:

    print(
        "NO CONSERVATIVE SAFE BATCH FOUND"
    )
