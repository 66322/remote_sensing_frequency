import csv
import json
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--run-dir", required=True)
args = parser.parse_args()

run_dir = Path(args.run_dir)

registry_path = run_dir / "best_registry.json"
metrics_path = run_dir / "metrics_history.csv"

if not registry_path.is_file():
    raise FileNotFoundError(registry_path)

if not metrics_path.is_file():
    raise FileNotFoundError(metrics_path)

registry = json.loads(
    registry_path.read_text(encoding="utf-8")
)

# ------------------------------------------------------------
# Primary selection:
# uniformly use best noBoundary OA checkpoint
# ------------------------------------------------------------
primary_iter = int(
    registry["OA"]["iter"]
)

with open(metrics_path, newline="") as f:
    rows = list(csv.DictReader(f))

primary_rows = [
    r for r in rows
    if int(r["step"]) == primary_iter
]

if len(primary_rows) != 1:
    raise RuntimeError(
        f"Cannot uniquely find metrics for iter {primary_iter}"
    )

r = primary_rows[0]

primary = {
    "selection_rule": "best_noBoundary_OA",
    "iter": primary_iter,
    "epoch": int(r["epoch"]),
    "model": registry["OA"]["model"],

    "FullGT": {
        "OA": float(r["full_OA"]),
        "mF1_fg5": float(r["full_mF1_fg5"]),
        "mIoU_fg5": float(r["full_mIoU_fg5"]),
        "mF1_all6": float(r["full_mF1_all6"]),
        "mIoU_all6": float(r["full_mIoU_all6"]),
    },

    "noBoundary": {
        "OA": float(r["nb_OA"]),
        "mF1_fg5": float(r["nb_mF1_fg5"]),
        "mIoU_fg5": float(r["nb_mIoU_fg5"]),
        "mF1_all6": float(r["nb_mF1_all6"]),
        "mIoU_all6": float(r["nb_mIoU_all6"]),
    },
}

summary = {
    "primary_selection": primary,
    "diagnostic_best": registry,
    "num_evaluations": len(rows),
}

out = run_dir / "final_summary.json"

out.write_text(
    json.dumps(
        summary,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print("=" * 80)
print("FINAL RUN SUMMARY")
print("=" * 80)

print("Primary selection rule : best noBoundary OA")
print("Primary iter           :", primary["iter"])
print("Primary epoch          :", primary["epoch"])
print("Primary model          :", primary["model"])

print()
print("PRIMARY noBoundary")
for k, v in primary["noBoundary"].items():
    print(f"  {k:12s}: {v * 100:.4f}%")

print()
print("DIAGNOSTIC BEST")
for key, x in registry.items():
    print(
        f"  {key:10s}: "
        f"{x['value'] * 100:.4f}% "
        f"@ iter {x['iter']} "
        f"({x['model']})"
    )

print()
print("Saved:", out)
