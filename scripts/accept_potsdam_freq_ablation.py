import csv
import json
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")

RUNS = {
    "F0": ROOT / "runs/Thesis_Ch4_NoSR_Ablation_Potsdam_F0_seed42",
    "F1": ROOT / "runs/Thesis_Ch4_NoSR_Ablation_Potsdam_F1_seed42",
    "F2": ROOT / "runs/Thesis_Ch4_NoSR_Ablation_Potsdam_F2_seed42",
    "F3": ROOT / "runs/Thesis_Ch4_NoSR_Ablation_Potsdam_F3_seed42",
}

MODULES = {
    "F0": (0, 0, 0),
    "F1": (1, 0, 0),
    "F2": (1, 1, 0),
    "F3": (1, 1, 1),
}

EXPECTED_STEPS = list(range(500, 50001, 500))

out_csv = ROOT / "records/Potsdam_frequency_ablation_summary.csv"
out_json = ROOT / "records/Potsdam_frequency_ablation_acceptance_20260828.json"

all_pass = True
acceptance = {}
summary_rows = []

print("=" * 130)
print("POTSDAM FREQUENCY ABLATION FORMAL ACCEPTANCE")
print("=" * 130)

print(
    f"{'Var':<4}"
    f"{'Status':<9}"
    f"{'Evals':>7}"
    f"{'SelIter':>9}"
    f"{'OA':>11}"
    f"{'mF1':>11}"
    f"{'mIoU':>11}"
    f"{'BestOA':>11}"
    f"{'BestF1':>11}"
    f"{'BestIoU':>11}"
)

print("-" * 130)

for v, run_dir in RUNS.items():
    log = ROOT / f"records/train_potsdam_{v}_seed42.log"
    metrics = run_dir / "metrics_history.csv"
    registry = run_dir / "best_registry.json"
    summary = run_dir / "final_summary.json"
    ckpt_dir = run_dir / "checkpoints"

    errors = []

    for p in [run_dir, log, metrics, registry, summary, ckpt_dir]:
        if not p.exists():
            errors.append(f"missing: {p}")

    rows = []
    reg = {}
    sm = {}

    if log.is_file():
        text = log.read_text(encoding="utf-8", errors="ignore")

        if "FORMAL TRAINING COMPLETE" not in text:
            errors.append("FORMAL TRAINING COMPLETE missing")

        if "Traceback (most recent call last)" in text:
            errors.append("Traceback detected")

    if metrics.is_file():
        with open(metrics, newline="") as f:
            reader = csv.reader(f)

            for row in reader:
                if not row:
                    continue
                try:
                    step = int(row[0])
                except ValueError:
                    continue
                rows.append(row)

        steps = [int(r[0]) for r in rows]

        if steps != EXPECTED_STEPS:
            errors.append(
                f"evaluation steps invalid: "
                f"count={len(steps)}, "
                f"first={steps[:3]}, last={steps[-3:] if steps else []}"
            )

    if registry.is_file():
        reg = json.loads(
            registry.read_text(encoding="utf-8")
        )

        for criterion in ["OA", "mF1_fg5", "mIoU_fg5"]:
            if criterion not in reg:
                errors.append(f"registry missing {criterion}")
                continue

            model_name = reg[criterion]["model"]
            model_path = ckpt_dir / model_name

            if not model_path.is_file():
                errors.append(
                    f"{criterion} checkpoint missing: {model_name}"
                )

    if summary.is_file():
        sm = json.loads(
            summary.read_text(encoding="utf-8")
        )

        primary = sm.get("primary_selection", {})

        if primary.get("selection_rule") != "best_noBoundary_OA":
            errors.append(
                "primary selection rule != best_noBoundary_OA"
            )

        selected_model = primary.get("model")

        if selected_model:
            if not (ckpt_dir / selected_model).is_file():
                errors.append(
                    f"primary checkpoint missing: {selected_model}"
                )

        if reg and primary:
            if int(primary["iter"]) != int(reg["OA"]["iter"]):
                errors.append(
                    "primary iter != best OA iter"
                )

    passed = len(errors) == 0
    all_pass &= passed

    if sm:
        p = sm["primary_selection"]
        nb = p["noBoundary"]

        oa = nb["OA"]
        f1 = nb["mF1_fg5"]
        iou = nb["mIoU_fg5"]

        best_oa = reg["OA"]["value"]
        best_f1 = reg["mF1_fg5"]["value"]
        best_iou = reg["mIoU_fg5"]["value"]

        lfau, sgor, hfdc = MODULES[v]

        summary_rows.append({
            "dataset": "Potsdam",
            "variant": v,
            "LFAU": lfau,
            "SGOR": sgor,
            "HFDC": hfdc,
            "selection_rule": p["selection_rule"],
            "selected_iter": p["iter"],
            "selected_epoch": p["epoch"],
            "selected_model": p["model"],
            "primary_nb_OA": oa,
            "primary_nb_mF1_fg5": f1,
            "primary_nb_mIoU_fg5": iou,
            "primary_full_OA": p["FullGT"]["OA"],
            "primary_full_mF1_fg5": p["FullGT"]["mF1_fg5"],
            "primary_full_mIoU_fg5": p["FullGT"]["mIoU_fg5"],
            "best_OA": best_oa,
            "best_OA_iter": reg["OA"]["iter"],
            "best_OA_model": reg["OA"]["model"],
            "best_mF1_fg5": best_f1,
            "best_mF1_iter": reg["mF1_fg5"]["iter"],
            "best_mF1_model": reg["mF1_fg5"]["model"],
            "best_mIoU_fg5": best_iou,
            "best_mIoU_iter": reg["mIoU_fg5"]["iter"],
            "best_mIoU_model": reg["mIoU_fg5"]["model"],
            "num_evaluations": len(rows),
            "run_dir": str(run_dir),
        })

        print(
            f"{v:<4}"
            f"{'PASS' if passed else 'FAIL':<9}"
            f"{len(rows):>7}"
            f"{p['iter']:>9}"
            f"{oa*100:>10.4f}%"
            f"{f1*100:>10.4f}%"
            f"{iou*100:>10.4f}%"
            f"{best_oa*100:>10.4f}%"
            f"{best_f1*100:>10.4f}%"
            f"{best_iou*100:>10.4f}%"
        )
    else:
        print(
            f"{v:<4}"
            f"{'FAIL':<9}"
            f"{len(rows):>7}"
        )

    acceptance[v] = {
        "pass": passed,
        "errors": errors,
        "num_evaluations": len(rows),
        "run_dir": str(run_dir),
    }

print("=" * 130)

# Sequential deltas
for i, row in enumerate(summary_rows):
    if i == 0:
        row["delta_mIoU_vs_prev_pp"] = ""
    else:
        row["delta_mIoU_vs_prev_pp"] = (
            row["primary_nb_mIoU_fg5"]
            - summary_rows[i - 1]["primary_nb_mIoU_fg5"]
        ) * 100

if summary_rows:
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=summary_rows[0].keys()
        )
        writer.writeheader()
        writer.writerows(summary_rows)

acceptance["overall_pass"] = all_pass

out_json.write_text(
    json.dumps(
        acceptance,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8",
)

print()
print("Overall:", "PASS" if all_pass else "FAIL")
print("Summary CSV:", out_csv)
print("Acceptance :", out_json)

if not all_pass:
    print()
    print("ERROR DETAILS")

    for v in ["F0", "F1", "F2", "F3"]:
        for err in acceptance[v]["errors"]:
            print(f"{v}: {err}")

    raise SystemExit(1)
