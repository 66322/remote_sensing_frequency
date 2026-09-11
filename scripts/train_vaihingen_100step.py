import os
import sys
import csv
import time
import random
from pathlib import Path

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
DATA_ROOT = Path("/home/jovyan/zzx/projects_zys/raw_extract/Vaihingen")
PRETRAIN = Path(
    "/home/jovyan/zzx/paper_rebuild/08_assets/pretrained/"
    "ftransunet/R50+ViT-B_16.npz"
)
RUN_DIR = ROOT / "runs" / "Vaihingen_100step_seed42_20260826"
RUN_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT))

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from skimage import io

from model.vitcross_seg_modeling_freqfusion import (
    VisionTransformerFreqFusion,
    CONFIGS,
)

SEED = 42
PATCH = 256
BATCH_SIZE = 8
NUM_STEPS = 100
DEVICE = torch.device("cuda:0")

TRAIN_IDS = [
    "1", "3", "7", "11", "13", "17",
    "23", "26", "28", "32", "34", "37"
]

PALETTE = {
    (255, 255, 255): 0,
    (0, 0, 255): 1,
    (0, 255, 255): 2,
    (0, 255, 0): 3,
    (255, 255, 0): 4,
    (255, 0, 0): 5,
}


def convert_label(rgb):
    out = np.zeros(rgb.shape[:2], dtype=np.int64)
    matched = np.zeros(rgb.shape[:2], dtype=bool)

    for color, idx in PALETTE.items():
        mask = np.all(rgb[..., :3] == np.array(color), axis=-1)
        out[mask] = idx
        matched |= mask

    if not matched.all():
        raise RuntimeError(
            f"Unknown label colors: {(~matched).sum()} pixels"
        )

    return out


class VaihingenRandomDataset(Dataset):
    def __init__(self):
        self.cache = {}

    def __len__(self):
        # Enough for exactly 100 batches of size 8
        return BATCH_SIZE * NUM_STEPS

    def _load_tile(self, tile_id):
        if tile_id in self.cache:
            return self.cache[tile_id]

        op = DATA_ROOT / "top" / f"top_mosaic_09cm_area{tile_id}.tif"
        dp = DATA_ROOT / "dsm" / f"dsm_09cm_matching_area{tile_id}.tif"
        gp = (
            DATA_ROOT / "gts_for_participants" /
            f"top_mosaic_09cm_area{tile_id}.tif"
        )

        for p in (op, dp, gp):
            if not p.is_file():
                raise FileNotFoundError(p)

        optical = io.imread(str(op))[..., :3].astype(np.float32) / 255.0

        dsm = io.imread(str(dp)).astype(np.float32)
        dmin = float(dsm.min())
        dmax = float(dsm.max())
        if dmax <= dmin:
            raise RuntimeError(f"DSM zero range: tile {tile_id}")
        dsm = (dsm - dmin) / (dmax - dmin)

        label = convert_label(io.imread(str(gp)))

        if not (
            optical.shape[:2] == dsm.shape[:2] == label.shape[:2]
        ):
            raise RuntimeError(f"Shape mismatch for tile {tile_id}")

        self.cache[tile_id] = (optical, dsm, label)
        return self.cache[tile_id]

    def __getitem__(self, index):
        tile_id = random.choice(TRAIN_IDS)
        optical, dsm, label = self._load_tile(tile_id)

        H, W = label.shape
        y = random.randint(0, H - PATCH)
        x = random.randint(0, W - PATCH)

        op = optical[y:y+PATCH, x:x+PATCH]
        ds = dsm[y:y+PATCH, x:x+PATCH]
        gt = label[y:y+PATCH, x:x+PATCH]

        # Historical flip/mirror style augmentation
        if random.random() < 0.5:
            op = op[::-1, :, :]
            ds = ds[::-1, :]
            gt = gt[::-1, :]

        if random.random() < 0.5:
            op = op[:, ::-1, :]
            ds = ds[:, ::-1]
            gt = gt[:, ::-1]

        op = np.ascontiguousarray(op.transpose(2, 0, 1))
        ds = np.ascontiguousarray(ds)
        gt = np.ascontiguousarray(gt)

        return (
            torch.from_numpy(op),
            torch.from_numpy(ds),
            torch.from_numpy(gt),
        )


def grad_max(net, keyword):
    vals = []
    for name, p in net.named_parameters():
        if keyword.lower() in name.lower() and p.grad is not None:
            if torch.isfinite(p.grad).all():
                vals.append(float(p.grad.detach().abs().max()))
    return max(vals) if vals else float("nan")


random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)

print("=" * 100)
print("THESIS CH4 NOSR - VAIHINGEN REAL 100-STEP TRAINING")
print("seed       :", SEED)
print("batch size :", BATCH_SIZE)
print("steps      :", NUM_STEPS)
print("crop       :", PATCH)
print("device     :", DEVICE)
print("=" * 100)

dataset = VaihingenRandomDataset()

# num_workers=0 deliberately:
# each of the 12 large tiles is cached only once in this process.
loader = DataLoader(
    dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=0,
    pin_memory=True,
    drop_last=True,
)

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

sgor_modules = [
    n for n, _ in net.named_modules()
    if "dysampler" in n.lower()
]
if not sgor_modules:
    raise RuntimeError("SGOR not instantiated")

print("SGOR modules:", len(sgor_modules))

optimizer = torch.optim.SGD(
    net.parameters(),
    lr=0.01,
    momentum=0.9,
    weight_decay=5e-4,
)

csv_path = RUN_DIR / "train_history.csv"

with open(csv_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "step",
        "loss",
        "loss_mean10",
        "dynamic_root_grad_max",
        "sgor_grad_max",
        "gpu_allocated_gb",
        "gpu_reserved_gb",
        "sec_per_step",
    ])

losses = []

torch.cuda.reset_peak_memory_stats()
net.train()

start_all = time.time()

for step, (optical, dsm, target) in enumerate(loader, start=1):
    if step > NUM_STEPS:
        break

    step_start = time.time()

    optical = optical.to(DEVICE, non_blocking=True)
    dsm = dsm.to(DEVICE, non_blocking=True)
    target = target.to(DEVICE, non_blocking=True)

    optimizer.zero_grad(set_to_none=True)

    logits = net(optical, dsm)

    if logits.shape != (BATCH_SIZE, 6, PATCH, PATCH):
        raise RuntimeError(
            f"Step {step}: bad logits shape {tuple(logits.shape)}"
        )

    loss = F.cross_entropy(logits, target)

    if not torch.isfinite(loss):
        raise RuntimeError(
            f"Step {step}: non-finite loss {loss}"
        )

    loss.backward()

    dynamic_grad = grad_max(net, "root")
    sgor_grad = grad_max(net, "dysampler")

    if not np.isfinite(sgor_grad) or sgor_grad <= 0:
        raise RuntimeError(
            f"Step {step}: SGOR gradient invalid: {sgor_grad}"
        )

    optimizer.step()

    torch.cuda.synchronize()

    loss_value = float(loss.detach())
    losses.append(loss_value)

    mean10 = float(np.mean(losses[-10:]))

    allocated = torch.cuda.memory_allocated() / 1024**3
    reserved = torch.cuda.memory_reserved() / 1024**3
    sec_step = time.time() - step_start

    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            step,
            f"{loss_value:.8f}",
            f"{mean10:.8f}",
            f"{dynamic_grad:.8e}",
            f"{sgor_grad:.8e}",
            f"{allocated:.4f}",
            f"{reserved:.4f}",
            f"{sec_step:.4f}",
        ])

    if step == 1 or step % 10 == 0:
        print(
            f"step {step:03d}/{NUM_STEPS} | "
            f"loss={loss_value:.6f} | "
            f"mean10={mean10:.6f} | "
            f"dyn_g={dynamic_grad:.3e} | "
            f"sgor_g={sgor_grad:.3e} | "
            f"alloc={allocated:.2f}G | "
            f"reserved={reserved:.2f}G | "
            f"{sec_step:.3f}s/step"
        )

total_time = time.time() - start_all

peak_alloc = torch.cuda.max_memory_allocated() / 1024**3
peak_reserved = torch.cuda.max_memory_reserved() / 1024**3

checkpoint = RUN_DIR / "checkpoint_step100.pth"

torch.save(
    {
        "model": net.state_dict(),
        "optimizer": optimizer.state_dict(),
        "step": NUM_STEPS,
        "seed": SEED,
        "batch_size": BATCH_SIZE,
        "crop": PATCH,
        "train_ids": TRAIN_IDS,
        "loss": losses[-1],
    },
    checkpoint,
)

# Verify saved checkpoint is readable
saved = torch.load(checkpoint, map_location="cpu")

if saved["step"] != NUM_STEPS:
    raise RuntimeError("Checkpoint reload verification failed")

print("\n" + "=" * 100)
print("100-STEP TRAINING PASS")
print("first loss          :", losses[0])
print("last loss           :", losses[-1])
print("first-10 mean       :", float(np.mean(losses[:10])))
print("last-10 mean        :", float(np.mean(losses[-10:])))
print("minimum loss        :", float(np.min(losses)))
print("peak allocated GB   :", peak_alloc)
print("peak reserved GB    :", peak_reserved)
print("total seconds       :", total_time)
print("avg sec/step        :", total_time / NUM_STEPS)
print("checkpoint          :", checkpoint)
print("history             :", csv_path)
print("=" * 100)
