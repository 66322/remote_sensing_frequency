import csv
from pathlib import Path
from statistics import mean

ROOT = Path(
    "/home/jovyan/zzx/paper_rebuild/"
    "08_thesis_full_repro"
)

F0 = (
    ROOT
    / "runs"
    / "Thesis_Ch4_NoSR_DetPair_F0_"
      "Vaihingen_F0_seed42_formal160k"
    / "metrics_history.csv"
)

P1 = (
    ROOT
    / "runs"
    / "Thesis_Ch4_NoSR_DetPair_P1_"
      "Vaihingen_P1_seed42_formal160k"
    / "metrics_history.csv"
)

OUT = (
    ROOT
    / "records"
    / "detpair_F0_P1_40k_analysis_20260831"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


def load(path):
    with path.open(
        newline="",
        encoding="utf-8",
    ) as f:
        rows = list(
            csv.DictReader(f)
        )

    return {
        int(r["step"]): r
        for r in rows
    }


f0 = load(F0)
p1 = load(P1)

steps = sorted(
    set(f0) & set(p1)
)

metrics = [
    "full_OA",
    "full_mF1_fg5",
    "full_mIoU_fg5",
    "nb_OA",
    "nb_mF1_fg5",
    "nb_mIoU_fg5",
]

paired = []

for step in steps:
    row = {
        "step": step,
        "epoch": int(
            f0[step]["epoch"]
        ),
    }

    for m in metrics:
        a = float(
            f0[step][m]
        )
        b = float(
            p1[step][m]
        )

        row[
            f"F0_{m}"
        ] = a

        row[
            f"P1_{m}"
        ] = b

        row[
            f"delta_{m}_pp"
        ] = (
            b - a
        ) * 100.0

    paired.append(row)


paired_csv = (
    OUT
    / "paired_metrics_all_steps.csv"
)

with paired_csv.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            paired[0].keys()
        ),
    )

    writer.writeheader()
    writer.writerows(
        paired
    )


def best(rows, metric):
    return max(
        rows.values(),
        key=lambda r: float(
            r[metric]
        ),
    )


summary_rows = []

for metric in [
    "nb_OA",
    "nb_mF1_fg5",
    "nb_mIoU_fg5",
    "full_OA",
    "full_mF1_fg5",
    "full_mIoU_fg5",
]:

    a = best(
        f0,
        metric,
    )

    b = best(
        p1,
        metric,
    )

    av = float(
        a[metric]
    )

    bv = float(
        b[metric]
    )

    summary_rows.append({
        "metric": metric,
        "F0_best_pct": av * 100,
        "F0_best_step": int(
            a["step"]
        ),
        "P1_best_pct": bv * 100,
        "P1_best_step": int(
            b["step"]
        ),
        "best_delta_pp": (
            bv - av
        ) * 100,
        "F0_final40k_pct": float(
            f0[40000][metric]
        ) * 100,
        "P1_final40k_pct": float(
            p1[40000][metric]
        ) * 100,
        "final40k_delta_pp": (
            float(
                p1[40000][metric]
            )
            - float(
                f0[40000][metric]
            )
        ) * 100,
    })


summary_csv = (
    OUT
    / "best_and_final_summary.csv"
)

with summary_csv.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            summary_rows[0].keys()
        ),
    )

    writer.writeheader()
    writer.writerows(
        summary_rows
    )


windows = [
    ("all_2k_40k", 2000, 40000),
    ("late_20k_40k", 20000, 40000),
    ("late_30k_40k", 30000, 40000),
    ("plateau_32k_40k", 32000, 40000),
]

plateau_rows = []

for name, lo, hi in windows:

    sub = [
        r
        for r in paired
        if lo <= r["step"] <= hi
    ]

    ds = [
        r[
            "delta_nb_mIoU_fg5_pp"
        ]
        for r in sub
    ]

    plateau_rows.append({
        "window": name,
        "start_step": lo,
        "end_step": hi,
        "n_eval_points": len(ds),
        "mean_delta_nb_mIoU_pp": mean(ds),
        "min_delta_nb_mIoU_pp": min(ds),
        "max_delta_nb_mIoU_pp": max(ds),
        "P1_win_points": sum(
            d > 0
            for d in ds
        ),
        "F0_win_points": sum(
            d < 0
            for d in ds
        ),
        "ties": sum(
            abs(d) < 1e-12
            for d in ds
        ),
    })


plateau_csv = (
    OUT
    / "plateau_summary.csv"
)

with plateau_csv.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            plateau_rows[0].keys()
        ),
    )

    writer.writeheader()
    writer.writerows(
        plateau_rows
    )


print()
print("=" * 100)
print("BEST / FINAL SUMMARY")
print("=" * 100)

for r in summary_rows:
    print(
        f"{r['metric']:18s} | "
        f"F0 best={r['F0_best_pct']:.4f}"
        f"@{r['F0_best_step']:05d} | "
        f"P1 best={r['P1_best_pct']:.4f}"
        f"@{r['P1_best_step']:05d} | "
        f"delta={r['best_delta_pp']:+.4f} pp | "
        f"40k delta="
        f"{r['final40k_delta_pp']:+.4f} pp"
    )

print()
print("=" * 100)
print("PAIRED NB mIoU")
print("=" * 100)

for r in paired:
    print(
        f"{r['step']:05d} | "
        f"F0={r['F0_nb_mIoU_fg5']*100:.4f} | "
        f"P1={r['P1_nb_mIoU_fg5']*100:.4f} | "
        f"delta="
        f"{r['delta_nb_mIoU_fg5_pp']:+.4f} pp"
    )

print()
print("=" * 100)
print("PLATEAU SUMMARY")
print("=" * 100)

for r in plateau_rows:
    print(
        f"{r['window']:18s} | "
        f"mean delta="
        f"{r['mean_delta_nb_mIoU_pp']:+.4f} pp | "
        f"P1 wins={r['P1_win_points']}/"
        f"{r['n_eval_points']}"
    )

print()
print("[SAVED]", paired_csv)
print("[SAVED]", summary_csv)
print("[SAVED]", plateau_csv)
