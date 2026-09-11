import os
import sys
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

ROOT = Path(
    "/home/jovyan/zzx/paper_rebuild/"
    "08_thesis_full_repro"
)

sys.path.insert(
    0,
    str(ROOT),
)

import numpy as np
import torch
import torch.nn.functional as F

from model.vitcross_seg_modeling_freq_ablation import (
    VisionTransformerFreqAblation,
    CONFIGS,
)

DEVICE = torch.device("cuda:0")

PRETRAIN = Path(
    "/home/jovyan/zzx/paper_rebuild/"
    "08_assets/pretrained/ftransunet/"
    "R50+ViT-B_16.npz"
)


def build(variant):
    config = CONFIGS["R50-ViT-B_16"]

    config.n_classes = 6
    config.n_skip = 3
    config.patches.grid = (16, 16)

    model = VisionTransformerFreqAblation(
        config,
        img_size=256,
        num_classes=6,
        freq_variant=variant,
    ).to(DEVICE)

    model.load_from(
        np.load(str(PRETRAIN))
    )

    return model


def count_named(model, key):
    return sum(
        1
        for name, _ in model.named_modules()
        if key.lower() in name.lower()
    )


for variant in [
    "F0",
    "F1",
    "F2",
    "F3",
]:
    print("\n" + "=" * 100)
    print("VARIANT", variant)
    print("=" * 100)

    torch.manual_seed(42)
    torch.cuda.manual_seed_all(42)

    net = build(variant)

    n_freq = count_named(
        net,
        "freq_fusion",
    )

    n_sgor = count_named(
        net,
        "dysampler",
    )

    n_hfdc = count_named(
        net,
        "content_encoder2",
    )

    print(
        "freq modules :",
        n_freq,
    )

    print(
        "SGOR modules :",
        n_sgor,
    )

    print(
        "HFDC encoders:",
        n_hfdc,
    )

    if variant == "F0":
        assert n_freq == 0
        assert n_sgor == 0
        assert n_hfdc == 0

    elif variant == "F1":
        assert n_freq > 0
        assert n_sgor == 0
        assert n_hfdc == 0

    elif variant == "F2":
        assert n_freq > 0
        assert n_sgor > 0
        assert n_hfdc == 0

    elif variant == "F3":
        assert n_freq > 0
        assert n_sgor > 0
        assert n_hfdc > 0

    optical = torch.randn(
        1, 3, 256, 256,
        device=DEVICE,
    )

    dsm = torch.randn(
        1, 256, 256,
        device=DEVICE,
    )

    gt = torch.randint(
        0,
        6,
        (1, 256, 256),
        device=DEVICE,
    )

    net.train()
    net.zero_grad(
        set_to_none=True
    )

    logits = net(
        optical,
        dsm,
    )

    assert logits.shape == (
        1, 6, 256, 256
    )

    loss = F.cross_entropy(
        logits,
        gt,
    )

    loss.backward()

    assert torch.isfinite(loss)

    if variant in ("F2", "F3"):
        sgor_grad = 0.0

        for name, p in (
            net.named_parameters()
        ):
            if (
                "dysampler" in name
                and p.grad is not None
            ):
                sgor_grad += float(
                    p.grad
                    .detach()
                    .abs()
                    .sum()
                )

        assert sgor_grad > 0

        print(
            "SGOR grad sum:",
            sgor_grad,
        )

    print(
        "logits:",
        tuple(logits.shape),
    )

    print(
        "loss:",
        float(loss.detach()),
    )

    print(
        f"[PASS] {variant}"
    )

    del net
    del optical
    del dsm
    del gt
    del logits

    torch.cuda.empty_cache()


print("\n" + "=" * 100)
print("ALL ABLATION VARIANTS PASS")
print("=" * 100)
