import sys
import copy
import math
import csv
from pathlib import Path
from collections import defaultdict

import numpy as np
import torch

ROOT = Path(
    "/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
)

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


# ------------------------------------------------------------
# Reuse frozen Stage-2 definitions/data/evaluation utilities.
# Importing the whole trainer would execute training, so load
# only the prefix before its training loop.
# ------------------------------------------------------------

trainer_path = (
    ROOT
    / "scripts"
    / "train_vaihingen_P1_detpair.py"
)

trainer_text = trainer_path.read_text(
    encoding="utf-8"
)

marker = "\nloss_buffer = []\n"

if marker not in trainer_text:
    raise RuntimeError(
        "trainer marker not found"
    )

prefix = trainer_text.split(
    marker,
    1,
)[0]

# Execute trainer setup in this script's namespace.
# Force formal P1 arguments but stop before training loop.
# Use an isolated smoke namespace only for reusing the
# trainer setup. No training loop is executed by this audit.
# This prevents collision with the existing formal P1 run.
sys.argv = [
    str(trainer_path),
    "--variant",
    "P1",
    "--smoke-steps",
    "991203",
]

exec(
    compile(
        prefix,
        str(trainer_path),
        "exec",
    ),
    globals(),
)


# ------------------------------------------------------------
# Replace whatever model state is currently present with the
# exact trained P1@2000 checkpoint.
# ------------------------------------------------------------

CKPT = (
    ROOT
    / "runs"
    / (
        "Thesis_Ch4_NoSR_DetPair_P1_"
        "Vaihingen_P1_seed42_formal160k"
    )
    / "checkpoints"
    / "model_iter_002000.pth"
)

if not CKPT.is_file():
    raise FileNotFoundError(
        CKPT
    )

state = torch.load(
    CKPT,
    map_location="cpu",
)

if (
    isinstance(state, dict)
    and "model" in state
):
    state = state["model"]

net.load_state_dict(
    state,
    strict=True,
)

net.eval()

print()
print("=" * 110)
print("P1 @ 2000 SCALE-BY-CLASS AUDIT")
print("=" * 110)
print("checkpoint:", CKPT)


CLASS_NAMES = [
    "Impervious",
    "Building",
    "LowVegetation",
    "Tree",
    "Car",
    "Clutter",
]


# ------------------------------------------------------------
# Weighted histogram.
#
# Avoid storing millions of scale pixels.
#
# Scale is mathematically in (0,2), use 2000 bins.
# Discrepancy uses a separate clipped histogram only for
# approximate percentiles; its mean stays unclipped.
# ------------------------------------------------------------

SCALE_BINS = 2000

stats = defaultdict(
    lambda: {
        "weight": 0.0,
        "scale_sum": 0.0,
        "disc_sum": 0.0,
        "lt095": 0.0,
        "gt105": 0.0,
        "lt050": 0.0,
        "gt150": 0.0,
        "hist": np.zeros(
            SCALE_BINS,
            dtype=np.float64,
        ),
    }
)


def weighted_quantile_from_hist(
    hist,
    q,
):
    total = hist.sum()

    if total <= 0:
        return float("nan")

    cdf = np.cumsum(hist)

    idx = int(
        np.searchsorted(
            cdf,
            q * total,
            side="left",
        )
    )

    idx = max(
        0,
        min(
            SCALE_BINS - 1,
            idx,
        ),
    )

    # bin center in [0,2]
    return (
        (idx + 0.5)
        * 2.0
        / SCALE_BINS
    )


def add_batch(
    gt_name,
    gt,
    weight,
    scale,
    discrepancy,
):
    """
    gt:
        B,H,W

    weight:
        B,H,W

    scale/discrepancy:
        B,1,h,w
    """

    H, W = gt.shape[-2:]

    scale = torch.nn.functional.interpolate(
        scale.float(),
        size=(H, W),
        mode="bilinear",
        align_corners=False,
    )[:, 0]

    discrepancy = torch.nn.functional.interpolate(
        discrepancy.float(),
        size=(H, W),
        mode="bilinear",
        align_corners=False,
    )[:, 0]

    for cls in range(N_CLASSES):
        valid = (
            gt == cls
        )

        if not valid.any():
            continue

        s = (
            scale[valid]
            .detach()
            .double()
            .cpu()
            .numpy()
        )

        d = (
            discrepancy[valid]
            .detach()
            .double()
            .cpu()
            .numpy()
        )

        w = (
            weight[valid]
            .detach()
            .double()
            .cpu()
            .numpy()
        )

        key = (
            gt_name,
            cls,
        )

        out = stats[key]

        out["weight"] += float(
            w.sum()
        )

        out["scale_sum"] += float(
            (w * s).sum()
        )

        out["disc_sum"] += float(
            (w * d).sum()
        )

        out["lt095"] += float(
            w[s < 0.95].sum()
        )

        out["gt105"] += float(
            w[s > 1.05].sum()
        )

        out["lt050"] += float(
            w[s < 0.50].sum()
        )

        out["gt150"] += float(
            w[s > 1.50].sum()
        )

        # Weighted histogram.
        idx = np.floor(
            np.clip(
                s,
                0.0,
                1.999999,
            )
            / 2.0
            * SCALE_BINS
        ).astype(np.int64)

        np.add.at(
            out["hist"],
            idx,
            w,
        )


# ------------------------------------------------------------
# Sliding inference
# ------------------------------------------------------------

cm_full = np.zeros(
    (N_CLASSES, N_CLASSES),
    dtype=np.int64,
)

cm_nb = np.zeros(
    (N_CLASSES, N_CLASSES),
    dtype=np.int64,
)


with torch.no_grad():

    for tile_id in TEST_IDS:

        data = test_cache[
            tile_id
        ]

        optical = data[
            "optical"
        ]

        dsm = data[
            "dsm"
        ]

        full_gt = data[
            "full_gt"
        ]

        nb_gt = data[
            "noboundary_gt"
        ]

        H, W = optical.shape[:2]

        ys = make_positions(H)
        xs = make_positions(W)

        coords = [
            (y, x)
            for y in ys
            for x in xs
        ]

        coverage = np.zeros(
            (H, W),
            dtype=np.float32,
        )

        for y, x in coords:
            coverage[
                y:y+PATCH,
                x:x+PATCH,
            ] += 1.0

        if np.any(
            coverage <= 0
        ):
            raise RuntimeError(
                f"coverage zero in tile {tile_id}"
            )

        score = np.zeros(
            (
                N_CLASSES,
                H,
                W,
            ),
            dtype=np.float32,
        )

        print(
            "[TILE]",
            tile_id,
            "| windows:",
            len(coords),
        )

        for start in range(
            0,
            len(coords),
            INFER_BATCH,
        ):

            batch_coords = coords[
                start:start+INFER_BATCH
            ]

            op = np.stack(
                [
                    optical[
                        y:y+PATCH,
                        x:x+PATCH,
                        :
                    ].transpose(
                        2,
                        0,
                        1,
                    )
                    for y, x
                    in batch_coords
                ],
                axis=0,
            )

            ds = np.stack(
                [
                    dsm[
                        y:y+PATCH,
                        x:x+PATCH
                    ]
                    for y, x
                    in batch_coords
                ],
                axis=0,
            )

            fg = np.stack(
                [
                    full_gt[
                        y:y+PATCH,
                        x:x+PATCH
                    ]
                    for y, x
                    in batch_coords
                ],
                axis=0,
            )

            ng = np.stack(
                [
                    nb_gt[
                        y:y+PATCH,
                        x:x+PATCH
                    ]
                    for y, x
                    in batch_coords
                ],
                axis=0,
            )

            wt = np.stack(
                [
                    1.0
                    / coverage[
                        y:y+PATCH,
                        x:x+PATCH
                    ]
                    for y, x
                    in batch_coords
                ],
                axis=0,
            )

            op_t = torch.from_numpy(
                np.ascontiguousarray(op)
            ).to(
                DEVICE,
                non_blocking=True,
            )

            ds_t = torch.from_numpy(
                np.ascontiguousarray(ds)
            ).to(
                DEVICE,
                non_blocking=True,
            )

            fg_t = torch.from_numpy(
                np.ascontiguousarray(fg)
            ).to(
                DEVICE,
                non_blocking=True,
            ).long()

            ng_t = torch.from_numpy(
                np.ascontiguousarray(ng)
            ).to(
                DEVICE,
                non_blocking=True,
            ).long()

            wt_t = torch.from_numpy(
                np.ascontiguousarray(wt)
            ).to(
                DEVICE,
                non_blocking=True,
            ).float()

            logits = net(
                op_t,
                ds_t,
            )

            diag = (
                net
                .get_prefreq_diagnostics()
            )

            scale = diag[
                "scale"
            ]

            discrepancy = diag[
                "discrepancy"
            ]

            add_batch(
                "FullGT",
                fg_t,
                wt_t,
                scale,
                discrepancy,
            )

            add_batch(
                "NB",
                ng_t,
                wt_t,
                scale,
                discrepancy,
            )

            logits_np = (
                logits
                .detach()
                .cpu()
                .numpy()
            )

            for output, (
                y,
                x,
            ) in zip(
                logits_np,
                batch_coords,
            ):
                score[
                    :,
                    y:y+PATCH,
                    x:x+PATCH,
                ] += output

        pred = np.argmax(
            score,
            axis=0,
        ).astype(np.uint8)

        update_cm(
            cm_full,
            full_gt,
            pred,
        )

        update_cm(
            cm_nb,
            nb_gt,
            pred,
        )


# ------------------------------------------------------------
# Metrics + reporting
# ------------------------------------------------------------

full_metrics = metrics_from_cm(
    cm_full
)

nb_metrics = metrics_from_cm(
    cm_nb
)

rows = []

for gt_name in [
    "FullGT",
    "NB",
]:

    for cls in range(
        N_CLASSES
    ):

        d = stats[
            (
                gt_name,
                cls,
            )
        ]

        w = d[
            "weight"
        ]

        if w <= 0:
            continue

        rows.append({
            "gt": gt_name,
            "class_id": cls,
            "class_name": (
                CLASS_NAMES[cls]
            ),
            "mean_scale": (
                d["scale_sum"] / w
            ),
            "median_scale": (
                weighted_quantile_from_hist(
                    d["hist"],
                    0.50,
                )
            ),
            "p05_scale": (
                weighted_quantile_from_hist(
                    d["hist"],
                    0.05,
                )
            ),
            "p95_scale": (
                weighted_quantile_from_hist(
                    d["hist"],
                    0.95,
                )
            ),
            "pct_scale_lt095": (
                d["lt095"] / w
            ),
            "pct_scale_gt105": (
                d["gt105"] / w
            ),
            "pct_scale_lt050": (
                d["lt050"] / w
            ),
            "pct_scale_gt150": (
                d["gt150"] / w
            ),
            "mean_discrepancy": (
                d["disc_sum"] / w
            ),
            "effective_weight": w,
        })


OUT_DIR = (
    ROOT
    / "records"
    / "DetPair_P1_scale_by_class_20260829"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

out_csv = (
    OUT_DIR
    / "DetPair_P1_iter2000_scale_by_class.csv"
)

with out_csv.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            rows[0].keys()
        ),
    )

    writer.writeheader()
    writer.writerows(
        rows
    )


print()
print("=" * 130)
print("P1 @2000 SCALE BY CLASS")
print("=" * 130)

for gt_name in [
    "FullGT",
    "NB",
]:

    print()
    print(
        f"--- {gt_name} ---"
    )

    print(
        f"{'Class':16s} "
        f"{'MeanS':>8s} "
        f"{'MedS':>8s} "
        f"{'P05':>8s} "
        f"{'P95':>8s} "
        f"{'<.95':>8s} "
        f"{'>1.05':>8s} "
        f"{'<.5':>8s} "
        f"{'>1.5':>8s} "
        f"{'Disc':>9s}"
    )

    for r in rows:

        if r[
            "gt"
        ] != gt_name:
            continue

        print(
            f"{r['class_name']:16s} "
            f"{r['mean_scale']:8.4f} "
            f"{r['median_scale']:8.4f} "
            f"{r['p05_scale']:8.4f} "
            f"{r['p95_scale']:8.4f} "
            f"{r['pct_scale_lt095']*100:7.2f}% "
            f"{r['pct_scale_gt105']*100:7.2f}% "
            f"{r['pct_scale_lt050']*100:7.2f}% "
            f"{r['pct_scale_gt150']*100:7.2f}% "
            f"{r['mean_discrepancy']:9.4f}"
        )


print()
print("=" * 110)
print("P1 CHECKPOINT EVALUATION")
print("=" * 110)

print(
    "FULL | "
    f"OA={full_metrics['OA']*100:.4f} | "
    f"mF1={full_metrics['mF1_fg5']*100:.4f} | "
    f"mIoU={full_metrics['mIoU_fg5']*100:.4f}"
)

print(
    "NB   | "
    f"OA={nb_metrics['OA']*100:.4f} | "
    f"mF1={nb_metrics['mF1_fg5']*100:.4f} | "
    f"mIoU={nb_metrics['mIoU_fg5']*100:.4f}"
)

print()
print(
    "[SAVED]",
    out_csv,
)


# ============================================================
# Per-class segmentation metrics from the exact same
# FullGT / noBoundary confusion matrices used above.
# ============================================================

def class_stats_from_cm(cm):
    cm = cm.astype(
        np.float64,
        copy=False,
    )

    tp = np.diag(cm)

    gt_support = cm.sum(
        axis=1
    )

    pred_support = cm.sum(
        axis=0
    )

    fp = pred_support - tp
    fn = gt_support - tp

    precision = np.divide(
        tp,
        pred_support,
        out=np.zeros_like(tp),
        where=pred_support > 0,
    )

    recall = np.divide(
        tp,
        gt_support,
        out=np.zeros_like(tp),
        where=gt_support > 0,
    )

    denom_f1 = (
        precision + recall
    )

    f1 = np.divide(
        2.0 * precision * recall,
        denom_f1,
        out=np.zeros_like(tp),
        where=denom_f1 > 0,
    )

    denom_iou = (
        tp + fp + fn
    )

    iou = np.divide(
        tp,
        denom_iou,
        out=np.zeros_like(tp),
        where=denom_iou > 0,
    )

    return {
        "gt_support": gt_support,
        "pred_support": pred_support,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "iou": iou,
    }


per_class_rows = []

for split_name, cm in [
    ("full", cm_full),
    ("noboundary", cm_nb),
]:
    cls_stats = (
        class_stats_from_cm(
            cm
        )
    )

    print()
    print("=" * 110)
    print(
        f"P1 @2000 "
        f"{split_name.upper()} "
        f"PER-CLASS"
    )
    print("=" * 110)

    print(
        f"{'Class':16s} "
        f"{'GT':>12s} "
        f"{'Pred':>12s} "
        f"{'Prec':>9s} "
        f"{'Recall':>9s} "
        f"{'F1':>9s} "
        f"{'IoU':>9s}"
    )

    for cls, name in enumerate(
        CLASS_NAMES
    ):
        row = {
            "split": split_name,
            "class_id": cls,
            "class_name": name,
            "gt_support": int(
                cls_stats[
                    "gt_support"
                ][cls]
            ),
            "pred_support": int(
                cls_stats[
                    "pred_support"
                ][cls]
            ),
            "precision": float(
                cls_stats[
                    "precision"
                ][cls]
            ),
            "recall": float(
                cls_stats[
                    "recall"
                ][cls]
            ),
            "f1": float(
                cls_stats[
                    "f1"
                ][cls]
            ),
            "iou": float(
                cls_stats[
                    "iou"
                ][cls]
            ),
        }

        per_class_rows.append(
            row
        )

        print(
            f"{name:16s} "
            f"{row['gt_support']:12d} "
            f"{row['pred_support']:12d} "
            f"{row['precision']*100:8.4f}% "
            f"{row['recall']*100:8.4f}% "
            f"{row['f1']*100:8.4f}% "
            f"{row['iou']*100:8.4f}%"
        )


per_class_csv = (
    OUT_DIR
    / "DetPair_P1_iter2000_per_class.csv"
)

with per_class_csv.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "split",
            "class_id",
            "class_name",
            "gt_support",
            "pred_support",
            "precision",
            "recall",
            "f1",
            "iou",
        ],
    )

    writer.writeheader()

    writer.writerows(
        per_class_rows
    )


cm_full_csv = (
    OUT_DIR
    / "DetPair_P1_iter2000_cm_full.csv"
)

cm_nb_csv = (
    OUT_DIR
    / "DetPair_P1_iter2000_cm_noboundary.csv"
)

np.savetxt(
    cm_full_csv,
    cm_full,
    delimiter=",",
    fmt="%d",
)

np.savetxt(
    cm_nb_csv,
    cm_nb,
    delimiter=",",
    fmt="%d",
)

print()
print(
    "[SAVED]",
    per_class_csv,
)

print(
    "[SAVED]",
    cm_full_csv,
)

print(
    "[SAVED]",
    cm_nb_csv,
)
