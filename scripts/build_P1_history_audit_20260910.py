from pathlib import Path

ROOT = Path(
    "/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
)

SRC = ROOT / "scripts/train_vaihingen_P1_detpair.py"
DST = ROOT / "scripts/train_vaihingen_P1_history_audit_10k.py"

s = SRC.read_text(encoding="utf-8")


def replace_once(text, old, new, desc):
    n = text.count(old)
    print(f"{desc}: count={n}")
    if n != 1:
        raise RuntimeError(
            f"{desc}: expected exactly 1 occurrence, got {n}"
        )
    return text.replace(old, new, 1)


# ============================================================
# 1. Independent run directory
# ============================================================

s = replace_once(
    s,
    "Thesis_Ch4_NoSR_DetPair_P1_",
    "Thesis_Ch4_NoSR_HistoryAudit_P1_",
    "run prefix",
)


# ============================================================
# 2. Audit constants
# ============================================================

s = replace_once(
    s,
    "PATCH = 512\n",
    """PATCH = 512

# ------------------------------------------------------------
# Persistent Hard Region Audit
# Observation only:
# - does NOT alter the training sampler
# - does NOT use random numbers
# - fixed 512x512 windows, 50% overlap
# ------------------------------------------------------------
HISTORY_AUDIT_STRIDE = 256
HISTORY_TOP_FRACTION = 0.20
""",
    "history constants",
)


# ============================================================
# 3. Audit functions
# ============================================================

marker = """# ============================================================
# Checkpoint registry
# ============================================================
"""

helper = r'''
# ============================================================
# Persistent Hard Region Audit
# ============================================================

def history_audit_positions(length):
    """
    Deterministic fixed-window positions.

    No random calls are used so this audit must not change
    the training sampling RNG stream.
    """
    if length <= PATCH:
        return [0]

    positions = list(
        range(
            0,
            length - PATCH + 1,
            HISTORY_AUDIT_STRIDE,
        )
    )

    last = length - PATCH

    if positions[-1] != last:
        positions.append(last)

    return positions


def history_window_metrics(gt, pred):
    """
    Region difficulty.

    Main score:
        hard_score = 1 - mean IoU over fg5 classes
                     that are actually present in GT.

    Classes absent from this region's GT are NOT forced to
    contribute zero IoU.
    """
    cm = np.zeros(
        (N_CLASSES, N_CLASSES),
        dtype=np.int64,
    )

    update_cm(
        cm,
        gt,
        pred,
    )

    x = cm.astype(np.float64)

    tp = np.diag(x)
    row = x.sum(axis=1)
    col = x.sum(axis=0)

    fp = col - tp
    fn = row - tp

    denom = tp + fp + fn

    iou = np.divide(
        tp,
        denom,
        out=np.zeros_like(tp),
        where=denom > 0,
    )

    total = x.sum()

    pixel_acc = (
        float(tp.sum() / total)
        if total > 0
        else float("nan")
    )

    present_fg5 = [
        c
        for c in range(5)
        if row[c] > 0
    ]

    if present_fg5:
        miou_present = float(
            np.mean(
                iou[present_fg5]
            )
        )
        hard_score = (
            1.0 - miou_present
        )
    else:
        miou_present = float("nan")
        hard_score = float("nan")

    valid = (
        (gt != IGNORE_INDEX)
        & (gt < N_CLASSES)
    )

    valid_n = int(valid.sum())

    fractions = []

    for c in range(N_CLASSES):
        if valid_n > 0:
            fractions.append(
                float(
                    np.sum(
                        gt[valid] == c
                    )
                    / valid_n
                )
            )
        else:
            fractions.append(
                float("nan")
            )

    return {
        "hard_score": hard_score,
        "pixel_accuracy": pixel_acc,
        "error_rate": (
            1.0 - pixel_acc
            if np.isfinite(pixel_acc)
            else float("nan")
        ),
        "mIoU_present_fg5": miou_present,
        "n_present_fg5": len(
            present_fg5
        ),
        "fractions": fractions,
        "iou": iou.tolist(),
    }


def run_history_audit(
    net,
    train_cache,
    global_step,
    run_dir,
    max_windows=None,
):
    """
    Fixed-window training-set audit.

    IMPORTANT:
    This function is observational only.
    It never:
      - changes sampling weights
      - calls random / numpy.random
      - performs backward()
      - updates optimizer
      - updates BatchNorm running statistics
    """
    print(
        "\n"
        + "=" * 100
    )

    print(
        f"HISTORY AUDIT @ ITER "
        f"{global_step}"
    )

    print(
        f"window={PATCH} "
        f"stride={HISTORY_AUDIT_STRIDE}"
    )

    start_time = time.time()

    coords = []

    for tile_id in TRAIN_IDS:
        optical, dsm, gt = (
            train_cache[tile_id]
        )

        H, W = gt.shape

        ys = history_audit_positions(
            H
        )
        xs = history_audit_positions(
            W
        )

        for y in ys:
            for x in xs:
                coords.append(
                    (
                        tile_id,
                        y,
                        x,
                    )
                )

    total_possible = len(coords)

    if (
        max_windows is not None
        and len(coords) > max_windows
    ):
        coords = coords[:max_windows]

    csv_path = (
        run_dir
        / "history_audit_windows.csv"
    )

    summary_path = (
        run_dir
        / "history_audit_summary.csv"
    )

    if not csv_path.is_file():
        with open(
            csv_path,
            "w",
            newline="",
        ) as f:
            csv.writer(f).writerow([
                "step",
                "window_id",
                "tile_id",
                "y",
                "x",
                "hard_score",
                "pixel_accuracy",
                "error_rate",
                "mIoU_present_fg5",
                "n_present_fg5",
                "frac_impervious",
                "frac_building",
                "frac_lowveg",
                "frac_tree",
                "frac_car",
                "frac_clutter",
                "iou_impervious",
                "iou_building",
                "iou_lowveg",
                "iou_tree",
                "iou_car",
            ])

    if not summary_path.is_file():
        with open(
            summary_path,
            "w",
            newline="",
        ) as f:
            csv.writer(f).writerow([
                "step",
                "n_windows",
                "n_total_possible",
                "hard_mean",
                "hard_median",
                "hard_p80",
                "hard_p90",
                "top20_count",
                "seconds",
            ])

    records = []

    was_training = net.training
    net.eval()

    try:
        with torch.no_grad():
            for start in range(
                0,
                len(coords),
                INFER_BATCH,
            ):
                batch_coords = coords[
                    start:start + INFER_BATCH
                ]

                optical_batch = []
                dsm_batch = []
                gt_batch = []

                for tile_id, y, x in batch_coords:
                    optical, dsm, gt = (
                        train_cache[tile_id]
                    )

                    op = optical[
                        y:y + PATCH,
                        x:x + PATCH,
                        :
                    ]

                    ds = dsm[
                        y:y + PATCH,
                        x:x + PATCH
                    ]

                    label = gt[
                        y:y + PATCH,
                        x:x + PATCH
                    ]

                    optical_batch.append(
                        np.ascontiguousarray(
                            op.transpose(
                                2, 0, 1
                            )
                        )
                    )

                    dsm_batch.append(
                        np.ascontiguousarray(
                            ds
                        )
                    )

                    gt_batch.append(
                        np.ascontiguousarray(
                            label
                        )
                    )

                optical_tensor = (
                    torch.from_numpy(
                        np.stack(
                            optical_batch,
                            axis=0,
                        )
                    )
                    .to(
                        DEVICE,
                        non_blocking=True,
                    )
                )

                dsm_tensor = (
                    torch.from_numpy(
                        np.stack(
                            dsm_batch,
                            axis=0,
                        )
                    )
                    .to(
                        DEVICE,
                        non_blocking=True,
                    )
                )

                logits = net(
                    optical_tensor,
                    dsm_tensor,
                )

                preds = (
                    torch.argmax(
                        logits,
                        dim=1,
                    )
                    .detach()
                    .cpu()
                    .numpy()
                    .astype(np.uint8)
                )

                for (
                    tile_id,
                    y,
                    x,
                ), gt_np, pred_np in zip(
                    batch_coords,
                    gt_batch,
                    preds,
                ):
                    m = (
                        history_window_metrics(
                            gt_np,
                            pred_np,
                        )
                    )

                    window_id = (
                        f"{tile_id}"
                        f"_y{y:04d}"
                        f"_x{x:04d}"
                    )

                    records.append({
                        "step": global_step,
                        "window_id": window_id,
                        "tile_id": tile_id,
                        "y": y,
                        "x": x,
                        **m,
                    })

                del optical_tensor
                del dsm_tensor
                del logits
                del preds

    finally:
        if was_training:
            net.train()

    with open(
        csv_path,
        "a",
        newline="",
    ) as f:
        writer = csv.writer(f)

        for r in records:
            writer.writerow([
                r["step"],
                r["window_id"],
                r["tile_id"],
                r["y"],
                r["x"],
                r["hard_score"],
                r["pixel_accuracy"],
                r["error_rate"],
                r["mIoU_present_fg5"],
                r["n_present_fg5"],
                *r["fractions"],
                *r["iou"][:5],
            ])

    hard_values = np.array(
        [
            r["hard_score"]
            for r in records
            if np.isfinite(
                r["hard_score"]
            )
        ],
        dtype=np.float64,
    )

    if len(hard_values) > 0:
        hard_mean = float(
            np.mean(hard_values)
        )

        hard_median = float(
            np.median(hard_values)
        )

        hard_p80 = float(
            np.percentile(
                hard_values,
                80,
            )
        )

        hard_p90 = float(
            np.percentile(
                hard_values,
                90,
            )
        )

        top20_count = int(
            np.ceil(
                len(hard_values)
                * HISTORY_TOP_FRACTION
            )
        )
    else:
        hard_mean = float("nan")
        hard_median = float("nan")
        hard_p80 = float("nan")
        hard_p90 = float("nan")
        top20_count = 0

    seconds = (
        time.time()
        - start_time
    )

    with open(
        summary_path,
        "a",
        newline="",
    ) as f:
        csv.writer(f).writerow([
            global_step,
            len(records),
            total_possible,
            hard_mean,
            hard_median,
            hard_p80,
            hard_p90,
            top20_count,
            seconds,
        ])

    print(
        "[HISTORY-AUDIT] "
        f"windows={len(records)}/"
        f"{total_possible} | "
        f"hard_mean="
        f"{hard_mean:.6f} | "
        f"median="
        f"{hard_median:.6f} | "
        f"p80="
        f"{hard_p80:.6f} | "
        f"p90="
        f"{hard_p90:.6f} | "
        f"seconds="
        f"{seconds:.2f}"
    )

    print(
        "=" * 100
        + "\n"
    )

    return records


'''

s = replace_once(
    s,
    marker,
    helper + marker,
    "insert history audit helpers",
)


# ============================================================
# 4. Call audit at the SAME 2k evaluation points
# ============================================================

needle = '''            full = result["full"]
            nb = result["noboundary"]
'''

replacement = '''            full = result["full"]
            nb = result["noboundary"]

            # ------------------------------------------------
            # Observation-only persistent hard-region audit.
            #
            # For smoke tests only 16 fixed windows are used.
            # Formal runs audit every fixed training window.
            # ------------------------------------------------
            run_history_audit(
                net,
                train_cache,
                global_step,
                RUN_DIR,
                max_windows=(
                    16
                    if args.smoke_steps > 0
                    else None
                ),
            )
'''

s = replace_once(
    s,
    needle,
    replacement,
    "insert audit call",
)


DST.write_text(
    s,
    encoding="utf-8",
)

print()
print("WROTE:")
print(DST)
print()
print("History Audit design:")
print("  model        = P1")
print("  train sampler= original 100% Random")
print("  patch        = 512")
print("  audit stride = 256")
print("  audit points = every normal evaluation")
print("  formal target= 10k")
