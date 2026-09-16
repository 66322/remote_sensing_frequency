import csv
import json
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
OUT = ROOT / "records/rebuild_v1_core_matrix_20260917"


def read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main():
    fg = read(ROOT / "records/rebuild_v1_r01_r02_fusion_gain_severity_20260916/summary.json")
    r03 = read(ROOT / "records/rebuild_v1_r03_robust_eval_20260916/summary.json")
    r04 = read(ROOT / "records/rebuild_v1_r04_robust_eval_20260916/summary.json")
    p01 = read(ROOT / "records/rebuild_v1_compute_profile_20260916/r01_profile.json")
    p02 = read(ROOT / "records/rebuild_v1_compute_profile_20260916/r02_profile.json")

    r01 = fg["r01"]
    r02 = fg["r02"]
    conditions = ["clean", "dsm_down2", "dsm_down4", "dsm_down8", "dsm_zero"]
    rows = []
    for cond in conditions:
        for split in ("full", "noboundary"):
            r01m = r01[split]["mIoU_fg5"]
            r02m = r02[cond][split]["mIoU_fg5"]
            r03m = r03["results"][cond][split]["mIoU_fg5"]
            r04m = r04["results"][cond][split]["mIoU_fg5"]
            rows.append({
                "condition": cond,
                "split": split,
                "R01_mIoU_fg5": r01m,
                "R02_mIoU_fg5": r02m,
                "R03_mIoU_fg5": r03m,
                "R04_mIoU_fg5": r04m,
                "R02_Fusion_Gain_pp": 100.0 * (r02m - r01m),
                "R03_Fusion_Gain_pp": 100.0 * (r03m - r01m),
                "R04_Fusion_Gain_pp": 100.0 * (r04m - r01m),
            })

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "core_matrix.csv", rows)

    payload = {
        "recorded_at": now_iso(),
        "protocol": "REBUILD_V1 seed42 core matrix on Val2",
        "historical_test6_loaded": False,
        "conditions": conditions,
        "matrix": rows,
        "G1_from_R02": {
            "clean_nb_fusion_gain_pp": fg["noboundary_clean_fusion_gain_pp"],
            "degraded_nb_fusion_gain_pp": fg["noboundary_degraded_fusion_gain_pp"],
            "supported_on_val2": fg["G1_harmful_fusion_supported_on_this_val2_screen"],
        },
        "efficiency": {
            "R01": {
                "params": p01["params"],
                "full_forward_batch1": p01["crop_batch1_latency"]["full_forward"],
                "tile_seconds": p01["end_to_end_tile_seconds"],
                "peak_gib": p01["crop_batch1_peak_allocated_gib"],
            },
            "R02": {
                "params": p02["params"],
                "full_forward_batch1": p02["crop_batch1_latency"]["full_forward"],
                "tile_seconds": p02["end_to_end_tile_seconds"],
                "peak_gib": p02["crop_batch1_peak_allocated_gib"],
            },
        },
        "sources": {
            "fusion_gain": "records/rebuild_v1_r01_r02_fusion_gain_severity_20260916/summary.json",
            "r03": "records/rebuild_v1_r03_robust_eval_20260916/summary.json",
            "r04": "records/rebuild_v1_r04_robust_eval_20260916/summary.json",
            "r01_profile": "records/rebuild_v1_compute_profile_20260916/r01_profile.json",
            "r02_profile": "records/rebuild_v1_compute_profile_20260916/r02_profile.json"
        }
    }
    with open(OUT / "summary.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    nb = [x for x in rows if x["split"] == "noboundary"]
    lines = [
        "# REBUILD_V1 core matrix — automatic seed42 summary",
        "",
        f"Recorded: {payload['recorded_at']}",
        "",
        "Development evidence on Val2 only; historical TEST6 was not loaded.",
        "",
        "| condition | R01 NB mIoU | R02 | R03 | R04 | R02 FG pp | R03 FG pp | R04 FG pp |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for x in nb:
        lines.append(
            f"| {x['condition']} | {100*x['R01_mIoU_fg5']:.4f} | {100*x['R02_mIoU_fg5']:.4f} | "
            f"{100*x['R03_mIoU_fg5']:.4f} | {100*x['R04_mIoU_fg5']:.4f} | "
            f"{x['R02_Fusion_Gain_pp']:+.4f} | {x['R03_Fusion_Gain_pp']:+.4f} | {x['R04_Fusion_Gain_pp']:+.4f} |"
        )
    lines += [
        "",
        f"G1 harmful-fusion gate on this Val2 screen: **{payload['G1_from_R02']['supported_on_val2']}**.",
        "",
        "This automatic summary does not decide whether R03/R04 are publication-worthy; it only consolidates matched evidence for later review.",
    ]
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("CORE MATRIX COMPLETE:", OUT)


if __name__ == "__main__":
    main()
