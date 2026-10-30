"""Validate and archive the completed B4 seed17 queue without rerunning it."""

import argparse
import csv
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


DEFAULT_ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
LABELS = ("C17", "R05_KD17", "KD17")
RUN_SLUGS = {
    "C17": "B1_C_ce_control_seed17_sched4000_stop4000_seed17_20260921",
    "R05_KD17": "B2_R05_teacher_seed17_sched4000_stop4000_seed17_20260921",
    "KD17": "B1_KD_safe_teacher_seed17_sched4000_stop4000_seed17_20260921",
}
EXPECTED_STAGES = tuple(
    f"{label}_{stage}"
    for label in LABELS
    for stage in ("SMOKE", "TRAIN", "ROBUST", "PAIRED")
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_csv(path, rows):
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_global_metrics(path):
    selected = {}
    for row in read_csv(path):
        if row["split"] == "noboundary" and row["condition"] in {
            "clean", "dsm_down8", "dsm_zero"
        }:
            selected[row["condition"]] = 100.0 * float(row["mIoU_fg5"])
    if set(selected) != {"clean", "dsm_down8", "dsm_zero"}:
        raise RuntimeError(f"incomplete global metrics: {path}")
    return selected


def load_local_damaged(path):
    grouped = {}
    for row in read_csv(path):
        if (
            row["tile"] == "ALL"
            and row["split"] == "noboundary"
            and row["region"] == "damaged"
            and row["family"] in {"D1_local_missing", "D3_local_down8"}
        ):
            grouped.setdefault(row["family"], []).append(
                100.0 * float(row["delta_mIoU_fg5"])
            )
    if set(grouped) != {"D1_local_missing", "D3_local_down8"}:
        raise RuntimeError(f"incomplete paired metrics: {path}")
    if any(len(values) != 4 for values in grouped.values()):
        raise RuntimeError(f"expected four local conditions per family: {path}")
    return {key: sum(values) / len(values) for key, values in grouped.items()}


def build_decision(global_by_model, local_by_model):
    kd_global = global_by_model["KD17"]
    r05_global = global_by_model["R05_KD17"]
    c_global = global_by_model["C17"]
    kd_local = local_by_model["KD17"]
    r05_local = local_by_model["R05_KD17"]
    c_local = local_by_model["C17"]

    versus_r05 = {
        "clean_pp": kd_global["clean"] - r05_global["clean"],
        "dsm_down8_pp": kd_global["dsm_down8"] - r05_global["dsm_down8"],
        "dsm_zero_pp": kd_global["dsm_zero"] - r05_global["dsm_zero"],
        "local_missing_damaged_drop_improvement_pp": (
            kd_local["D1_local_missing"] - r05_local["D1_local_missing"]
        ),
        "local_down8_damaged_drop_improvement_pp": (
            kd_local["D3_local_down8"] - r05_local["D3_local_down8"]
        ),
    }
    versus_c = {
        "clean_pp": kd_global["clean"] - c_global["clean"],
        "dsm_down8_pp": kd_global["dsm_down8"] - c_global["dsm_down8"],
        "dsm_zero_pp": kd_global["dsm_zero"] - c_global["dsm_zero"],
        "local_missing_damaged_drop_improvement_pp": (
            kd_local["D1_local_missing"] - c_local["D1_local_missing"]
        ),
        "local_down8_damaged_drop_improvement_pp": (
            kd_local["D3_local_down8"] - c_local["D3_local_down8"]
        ),
    }
    gate = {
        "global_down8_better_than_r05_kd": versus_r05["dsm_down8_pp"] > 0,
        "global_zero_better_than_r05_kd": versus_r05["dsm_zero_pp"] > 0,
        "local_missing_damaged_drop_better_than_r05_kd": (
            versus_r05["local_missing_damaged_drop_improvement_pp"] > 0
        ),
        "local_down8_damaged_drop_better_than_r05_kd": (
            versus_r05["local_down8_damaged_drop_improvement_pp"] > 0
        ),
    }
    gate["replication_pass"] = all(gate.values())
    return {"kd17_minus_r05_kd17": versus_r05, "kd17_minus_c17": versus_c, "gate": gate}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument(
        "--queue-root", default="records/rebuild_v1_b4_seed17_20260921"
    )
    parser.add_argument(
        "--output", default="records/rebuild_v1_b4_seed17_compact_20260922"
    )
    args = parser.parse_args()

    root = args.project_root.resolve()
    queue = (root / args.queue_root).resolve()
    output = (root / args.output).resolve()
    queue.relative_to((root / "records").resolve())
    output.relative_to((root / "records").resolve())
    if output.exists():
        raise FileExistsError(f"refusing to overwrite: {output}")

    queue_summary = read_json(queue / "queue_summary.json")
    states = queue_summary.get("statuses", {})
    incomplete = [stage for stage in EXPECTED_STAGES if states.get(stage) != "COMPLETE"]
    if states.get("SUMMARIZE") != "COMPLETE" or states.get("QUEUE") != "COMPLETE":
        incomplete.extend(["SUMMARIZE/QUEUE"])
    if incomplete:
        raise RuntimeError("B4 queue is not complete: " + ", ".join(incomplete))
    if queue_summary.get("test6_loaded") is not False:
        raise RuntimeError("queue TEST6 safety flag is invalid")

    source_files = [
        queue / "status.tsv",
        queue / "queue_summary.json",
        queue / "preflight.json",
        queue / "b4_global_summary.csv",
        queue / "b4_paired_summary.csv",
    ]
    global_by_model, local_by_model = {}, {}
    run_records = {}
    for label in LABELS:
        run_dir = root / "runs/rebuild_v1" / RUN_SLUGS[label]
        run_summary = read_json(run_dir / "summary.json")
        run_metadata = read_json(run_dir / "run_metadata.json")
        checkpoint = run_dir / "best_model.pth"
        if run_summary.get("global_step") != 4000 or run_summary.get("test6_loaded") is not False:
            raise RuntimeError(f"incomplete or unsafe training run: {label}")
        if not checkpoint.is_file():
            raise FileNotFoundError(checkpoint)

        robust_dir = queue / f"{label}_ROBUST"
        paired_dir = queue / f"{label}_PAIRED"
        robust_summary = read_json(robust_dir / "summary.json")
        paired_summary = read_json(paired_dir / "summary.json")
        if robust_summary.get("historical_test6_loaded") is not False:
            raise RuntimeError(f"robust TEST6 safety failure: {label}")
        if paired_summary.get("test6_loaded") is not False or paired_summary.get("status") != "COMPLETE":
            raise RuntimeError(f"paired evaluation incomplete or unsafe: {label}")

        robust_metrics = robust_dir / "dataset_metrics.csv"
        paired_metrics = paired_dir / "paired_metrics.csv"
        global_by_model[label] = load_global_metrics(robust_metrics)
        local_by_model[label] = load_local_damaged(paired_metrics)
        source_files.extend([robust_dir / "summary.json", robust_metrics,
                             paired_dir / "summary.json", paired_metrics])
        run_records[label] = {
            "run_dir": str(run_dir),
            "started_at": run_summary.get("started_at"),
            "completed_at": run_summary.get("completed_at"),
            "git_commit_reported_by_trainer": run_summary.get("git_commit"),
            "source_fingerprints": run_metadata.get("signature"),
            "best": run_summary.get("best"),
            "checkpoint": {
                "server_only": True,
                "path": str(checkpoint),
                "bytes": checkpoint.stat().st_size,
                "sha256": sha256(checkpoint),
            },
        }

    missing_sources = [str(path) for path in source_files if not path.is_file()]
    if missing_sources:
        raise FileNotFoundError("missing B4 sources: " + ", ".join(missing_sources))

    decision = build_decision(global_by_model, local_by_model)
    output.mkdir(parents=True)
    for source in source_files[:5]:
        target = output / source.name
        shutil.copy2(source, target)
        if target.suffix in {".csv", ".tsv"}:
            target.write_bytes(target.read_bytes().replace(b"\r\n", b"\n"))

    global_rows = [dict(model=label, **global_by_model[label]) for label in LABELS]
    local_rows = [dict(model=label, **local_by_model[label]) for label in LABELS]
    write_csv(output / "global_metrics.csv", global_rows)
    write_csv(output / "local_damaged_metrics.csv", local_rows)
    write_json(output / "decision_evidence.json", {
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "experiment_id": "B4_SEED17_REPLICATION",
        "dataset_split": "Potsdam Train16 -> Val2",
        "seed": 17,
        "metric_units": "percentage points",
        "test6_loaded": False,
        "global_metrics": global_by_model,
        "local_damaged_corrupt_minus_clean_pp": local_by_model,
        **decision,
        "claim_boundary": (
            "Seed17 replication on the same two-tile Val2 development split; "
            "not an independent-dataset or held-out-test conclusion."
        ),
    })
    write_json(output / "run_provenance.json", run_records)

    manifest_rows = []
    for path in sorted(source_files):
        manifest_rows.append({
            "server_path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)
        })
    write_json(output / "source_artifact_manifest.json", manifest_rows)
    compact = [path for path in sorted(output.iterdir()) if path.is_file()]
    (output / "SHA256SUMS").write_text(
        "\n".join(f"{sha256(path)}  {path.name}" for path in compact) + "\n",
        encoding="utf-8",
    )
    print("B4_ARCHIVE_COMPLETE", output)
    print(json.dumps(decision, indent=2))


if __name__ == "__main__":
    main()
