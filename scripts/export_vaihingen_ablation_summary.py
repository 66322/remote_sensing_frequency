import csv
import json
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")

RUNS = {
    "F0": ROOT / "runs/Thesis_Ch4_NoSR_Ablation_Vaihingen_F0_seed42",
    "F1": ROOT / "runs/Thesis_Ch4_NoSR_Ablation_Vaihingen_F1_seed42",
    "F2": ROOT / "runs/Thesis_Ch4_NoSR_Ablation_Vaihingen_F2_seed42",
    "F3": ROOT / "runs/Thesis_Ch4_NoSR_v1_Vaihingen_seed42",
}

MODULES = {
    "F0": (0, 0, 0),
    "F1": (1, 0, 0),
    "F2": (1, 1, 0),
    "F3": (1, 1, 1),
}

OUT = ROOT / "records/Vaihingen_frequency_ablation_summary.csv"

rows = []

for variant, run_dir in RUNS.items():
    p = run_dir / "final_summary.json"
    if not p.is_file():
        raise FileNotFoundError(p)

    s = json.loads(p.read_text(encoding="utf-8"))

    primary = s["primary_selection"]
    nb = primary["noBoundary"]
    full = primary["FullGT"]
    best = s["diagnostic_best"]

    lfau, sgor, hfdc = MODULES[variant]

    rows.append({
        "dataset": "Vaihingen",
        "variant": variant,
        "LFAU": lfau,
        "SGOR": sgor,
        "HFDC": hfdc,

        "selection_rule": primary["selection_rule"],
        "selected_iter": primary["iter"],
        "selected_epoch": primary["epoch"],
        "selected_model": primary["model"],

        "primary_full_OA": full["OA"],
        "primary_full_mF1_fg5": full["mF1_fg5"],
        "primary_full_mIoU_fg5": full["mIoU_fg5"],
        "primary_full_mF1_all6": full["mF1_all6"],
        "primary_full_mIoU_all6": full["mIoU_all6"],

        "primary_nb_OA": nb["OA"],
        "primary_nb_mF1_fg5": nb["mF1_fg5"],
        "primary_nb_mIoU_fg5": nb["mIoU_fg5"],
        "primary_nb_mF1_all6": nb["mF1_all6"],
        "primary_nb_mIoU_all6": nb["mIoU_all6"],

        "best_OA": best["OA"]["value"],
        "best_OA_iter": best["OA"]["iter"],
        "best_OA_model": best["OA"]["model"],

        "best_mF1_fg5": best["mF1_fg5"]["value"],
        "best_mF1_iter": best["mF1_fg5"]["iter"],
        "best_mF1_model": best["mF1_fg5"]["model"],

        "best_mIoU_fg5": best["mIoU_fg5"]["value"],
        "best_mIoU_iter": best["mIoU_fg5"]["iter"],
        "best_mIoU_model": best["mIoU_fg5"]["model"],

        "num_evaluations": s["num_evaluations"],
        "run_dir": str(run_dir),
    })

# 加入相对前一组的主表增益
for i, row in enumerate(rows):
    if i == 0:
        row["delta_OA_vs_prev_pp"] = ""
        row["delta_mF1_vs_prev_pp"] = ""
        row["delta_mIoU_vs_prev_pp"] = ""
    else:
        prev = rows[i - 1]
        row["delta_OA_vs_prev_pp"] = (
            row["primary_nb_OA"] - prev["primary_nb_OA"]
        ) * 100
        row["delta_mF1_vs_prev_pp"] = (
            row["primary_nb_mF1_fg5"] - prev["primary_nb_mF1_fg5"]
        ) * 100
        row["delta_mIoU_vs_prev_pp"] = (
            row["primary_nb_mIoU_fg5"] - prev["primary_nb_mIoU_fg5"]
        ) * 100

with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print("=" * 105)
print("VAIHINGEN FREQUENCY ABLATION SUMMARY")
print("=" * 105)
print(
    f"{'Var':<4}"
    f"{'L':>4}{'S':>4}{'H':>4}"
    f"{'Iter':>8}"
    f"{'OA':>11}"
    f"{'mF1':>11}"
    f"{'mIoU':>11}"
    f"{'dIoU':>10}"
)
print("-" * 105)

for row in rows:
    delta = row["delta_mIoU_vs_prev_pp"]
    delta_text = "-" if delta == "" else f"{delta:+.4f}"

    print(
        f"{row['variant']:<4}"
        f"{row['LFAU']:>4}"
        f"{row['SGOR']:>4}"
        f"{row['HFDC']:>4}"
        f"{row['selected_iter']:>8}"
        f"{row['primary_nb_OA']*100:>10.4f}%"
        f"{row['primary_nb_mF1_fg5']*100:>10.4f}%"
        f"{row['primary_nb_mIoU_fg5']*100:>10.4f}%"
        f"{delta_text:>10}"
    )

print("=" * 105)
print("Saved:", OUT)
