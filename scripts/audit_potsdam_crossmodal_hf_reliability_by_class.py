import sys
import copy
import math
import csv
import shutil
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
    / "train_potsdam_crossmodal_hf_reliability_10k.py"
)

trainer_text = trainer_path.read_text(
    encoding="utf-8"
)

AUDIT_RUNTIME_DIR = (
    ROOT
    / ".local_backups"
    / "audit_potsdam_crossmodal_hf_reliability_runtime"
)

if AUDIT_RUNTIME_DIR.exists():
    shutil.rmtree(
        AUDIT_RUNTIME_DIR
    )

FORMAL_RUN_BLOCK = """RUN_DIR = (
    Path(__file__).resolve().parents[1]
    / "runs"
    / (
        "potsdam_crossmodal_hf_reliability_seed42_smoke20"
        if args.max_steps <= 20
        else "potsdam_crossmodal_hf_reliability_seed42_10k"
    )
)
"""

AUDIT_RUN_BLOCK = f"""RUN_DIR = Path(
    r"{AUDIT_RUNTIME_DIR}"
)
"""

if trainer_text.count(
    FORMAL_RUN_BLOCK
) != 1:
    raise RuntimeError(
        "Potsdam trainer RUN_DIR block not found exactly once"
    )

trainer_text = trainer_text.replace(
    FORMAL_RUN_BLOCK,
    AUDIT_RUN_BLOCK,
    1,
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
    "P2H",
    "--max-steps",
    "20",
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
    / "potsdam_crossmodal_hf_reliability_seed42_10k"
    / "checkpoints"
    / "model_iter_010000.pth"
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
print("POTSDAM CROSS-MODAL HF RELIABILITY @ 10000 | CLASS AUDIT")
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
# P2-H class-conditioned reliability statistics
#
# Quantities:
#   wo / wd:
#       Optical / DSM HF reliability weights.
#
#   So / Sd:
#       2*wo / 2*wd.
#
#   dominant_005:
#       confidence-aware modality preference using a ±0.005
#       neutral deadband around 0.5.
#
#   gap:
#       |wo-wd|, strength of modality selection.
#
#   corr(D, gap):
#       whether larger HF discrepancy is associated with
#       stronger modality selection.
# ------------------------------------------------------------

RELIABILITY_BINS = 1000

stats = defaultdict(
    lambda: {
        "weight": 0.0,

        "wo_sum": 0.0,
        "wd_sum": 0.0,

        "disc_sum": 0.0,
        "gap_sum": 0.0,

        "disc2_sum": 0.0,
        "gap2_sum": 0.0,
        "disc_gap_sum": 0.0,

        "opt_dom005": 0.0,
        "dsm_dom005": 0.0,
        "neutral005": 0.0,

        "wo_gt060": 0.0,
        "wd_gt060": 0.0,

        "hist_wo": np.zeros(
            RELIABILITY_BINS,
            dtype=np.float64,
        ),

        "hist_wd": np.zeros(
            RELIABILITY_BINS,
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
            RELIABILITY_BINS - 1,
            idx,
        ),
    )

    return (
        (idx + 0.5)
        / RELIABILITY_BINS
    )


def weighted_corr_disc_gap(d):
    w = d["weight"]

    if w <= 0:
        return float("nan")

    mx = d["disc_sum"] / w
    my = d["gap_sum"] / w

    vx = (
        d["disc2_sum"] / w
        - mx * mx
    )

    vy = (
        d["gap2_sum"] / w
        - my * my
    )

    cov = (
        d["disc_gap_sum"] / w
        - mx * my
    )

    if (
        vx <= 1e-12
        or vy <= 1e-12
    ):
        return float("nan")

    return (
        cov
        / math.sqrt(
            vx * vy
        )
    )


def add_batch(
    gt_name,
    gt,
    weight,
    reliability,
    discrepancy,
):
    """
    gt:
        B,H,W

    weight:
        B,H,W

    reliability:
        B,2,h,w
        channel0 = Optical HF weight
        channel1 = DSM HF weight

    discrepancy:
        B,1,h,w
    """

    H, W = gt.shape[-2:]

    reliability = (
        torch.nn.functional.interpolate(
            reliability.float(),
            size=(H, W),
            mode="bilinear",
            align_corners=False,
        )
    )

    discrepancy = (
        torch.nn.functional.interpolate(
            discrepancy.float(),
            size=(H, W),
            mode="bilinear",
            align_corners=False,
        )[:, 0]
    )

    # Bilinear interpolation is linear, so complementary
    # softmax weights should still sum to one.
    max_sum_err = float(
        (
            reliability.sum(
                dim=1
            )
            - 1.0
        )
        .abs()
        .max()
    )

    if max_sum_err > 1e-5:
        raise RuntimeError(
            "Interpolated P2-H reliability no longer "
            f"sums to 1: {max_sum_err}"
        )

    wo_map = reliability[:, 0]
    wd_map = reliability[:, 1]

    for cls in range(N_CLASSES):
        valid = (
            gt == cls
        )

        if not valid.any():
            continue

        wo = (
            wo_map[valid]
            .detach()
            .double()
            .cpu()
            .numpy()
        )

        wd = (
            wd_map[valid]
            .detach()
            .double()
            .cpu()
            .numpy()
        )

        disc = (
            discrepancy[valid]
            .detach()
            .double()
            .cpu()
            .numpy()
        )

        ww = (
            weight[valid]
            .detach()
            .double()
            .cpu()
            .numpy()
        )

        gap = np.abs(
            wo - wd
        )

        key = (
            gt_name,
            cls,
        )

        out = stats[key]

        out["weight"] += float(
            ww.sum()
        )

        out["wo_sum"] += float(
            (ww * wo).sum()
        )

        out["wd_sum"] += float(
            (ww * wd).sum()
        )

        out["disc_sum"] += float(
            (ww * disc).sum()
        )

        out["gap_sum"] += float(
            (ww * gap).sum()
        )

        out["disc2_sum"] += float(
            (ww * disc * disc).sum()
        )

        out["gap2_sum"] += float(
            (ww * gap * gap).sum()
        )

        out["disc_gap_sum"] += float(
            (
                ww
                * disc
                * gap
            ).sum()
        )

        out["opt_dom005"] += float(
            ww[
                wo > 0.505
            ].sum()
        )

        out["dsm_dom005"] += float(
            ww[
                wd > 0.505
            ].sum()
        )

        out["neutral005"] += float(
            ww[
                np.abs(
                    wo - 0.5
                )
                <= 0.005
            ].sum()
        )

        out["wo_gt060"] += float(
            ww[
                wo > 0.60
            ].sum()
        )

        out["wd_gt060"] += float(
            ww[
                wd > 0.60
            ].sum()
        )

        idx_wo = np.floor(
            np.clip(
                wo,
                0.0,
                0.999999,
            )
            * RELIABILITY_BINS
        ).astype(np.int64)

        idx_wd = np.floor(
            np.clip(
                wd,
                0.0,
                0.999999,
            )
            * RELIABILITY_BINS
        ).astype(np.int64)

        np.add.at(
            out["hist_wo"],
            idx_wo,
            ww,
        )

        np.add.at(
            out["hist_wd"],
            idx_wd,
            ww,
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
                .get_hfrely_diagnostics()
            )

            reliability = diag[
                "weights"
            ]

            discrepancy = diag[
                "discrepancy"
            ]

            if (
                reliability is None
                or discrepancy is None
            ):
                raise RuntimeError(
                    "Missing P2-H reliability diagnostics"
                )

            add_batch(
                "FullGT",
                fg_t,
                wt_t,
                reliability,
                discrepancy,
            )

            add_batch(
                "NB",
                ng_t,
                wt_t,
                reliability,
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
# Metrics + P2-H reliability reporting
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

        mean_wo = (
            d["wo_sum"] / w
        )

        mean_wd = (
            d["wd_sum"] / w
        )

        rows.append({
            "gt": gt_name,
            "class_id": cls,
            "class_name": (
                CLASS_NAMES[cls]
            ),

            "mean_wo": mean_wo,
            "median_wo": (
                weighted_quantile_from_hist(
                    d["hist_wo"],
                    0.50,
                )
            ),
            "p05_wo": (
                weighted_quantile_from_hist(
                    d["hist_wo"],
                    0.05,
                )
            ),
            "p95_wo": (
                weighted_quantile_from_hist(
                    d["hist_wo"],
                    0.95,
                )
            ),

            "mean_wd": mean_wd,
            "median_wd": (
                weighted_quantile_from_hist(
                    d["hist_wd"],
                    0.50,
                )
            ),
            "p05_wd": (
                weighted_quantile_from_hist(
                    d["hist_wd"],
                    0.05,
                )
            ),
            "p95_wd": (
                weighted_quantile_from_hist(
                    d["hist_wd"],
                    0.95,
                )
            ),

            "mean_optical_scale": (
                2.0 * mean_wo
            ),

            "mean_dsm_scale": (
                2.0 * mean_wd
            ),

            "opt_dominant_005": (
                d["opt_dom005"] / w
            ),

            "dsm_dominant_005": (
                d["dsm_dom005"] / w
            ),

            "neutral_005": (
                d["neutral005"] / w
            ),

            "wo_gt060": (
                d["wo_gt060"] / w
            ),

            "wd_gt060": (
                d["wd_gt060"] / w
            ),

            "mean_reliability_gap": (
                d["gap_sum"] / w
            ),

            "mean_discrepancy": (
                d["disc_sum"] / w
            ),

            "disc_gap_corr": (
                weighted_corr_disc_gap(
                    d
                )
            ),

            "effective_weight": w,
        })


OUT_DIR = (
    ROOT
    / "records"
    / "potsdam_crossmodal_hf_reliability_10k_by_class_20260913"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

out_csv = (
    OUT_DIR
    / "potsdam_crossmodal_hf_reliability_10k_by_class.csv"
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
print("=" * 178)
print(
    "POTSDAM CROSS-MODAL HF RELIABILITY @10000 BY CLASS"
)
print("=" * 178)

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
        f"{'wo':>7s} "
        f"{'wd':>7s} "
        f"{'wo50':>7s} "
        f"{'wo05':>7s} "
        f"{'wo95':>7s} "
        f"{'Opt005':>8s} "
        f"{'DSM005':>8s} "
        f"{'Neutral':>8s} "
        f"{'wo>.60':>8s} "
        f"{'wd>.60':>8s} "
        f"{'Gap':>8s} "
        f"{'Disc':>8s} "
        f"{'D-Gcorr':>8s}"
    )

    for r in rows:

        if (
            r["gt"]
            != gt_name
        ):
            continue

        print(
            f"{r['class_name']:16s} "
            f"{r['mean_wo']:7.4f} "
            f"{r['mean_wd']:7.4f} "
            f"{r['median_wo']:7.4f} "
            f"{r['p05_wo']:7.4f} "
            f"{r['p95_wo']:7.4f} "
            f"{r['opt_dominant_005']*100:7.2f}% "
            f"{r['dsm_dominant_005']*100:7.2f}% "
            f"{r['neutral_005']*100:7.2f}% "
            f"{r['wo_gt060']*100:7.2f}% "
            f"{r['wd_gt060']*100:7.2f}% "
            f"{r['mean_reliability_gap']:8.4f} "
            f"{r['mean_discrepancy']:8.4f} "
            f"{r['disc_gap_corr']:8.4f}"
        )


print()
print("=" * 110)
print(
    "POTSDAM HF RELIABILITY CHECKPOINT EVALUATION"
)
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
        f"P2-H @20000 "
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
    / "potsdam_crossmodal_hf_reliability_10k_per_class.csv"
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
    / "potsdam_crossmodal_hf_reliability_10k_cm_full.csv"
)

cm_nb_csv = (
    OUT_DIR
    / "potsdam_crossmodal_hf_reliability_10k_cm_noboundary.csv"
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
