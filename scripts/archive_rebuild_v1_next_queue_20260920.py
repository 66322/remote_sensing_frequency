import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
RUNS = ROOT / "runs/rebuild_v1"
RECORDS = ROOT / "records"

EXPERIMENTS = {
    "A1": {
        "run": RUNS / "R05_dual_f0_quality_plus_dropout_seed42_sched16000_stop16000_a1_no_optical_dropout",
        "record": RECORDS / "rebuild_v1_a1_formal_16k_20260919",
    },
    "A2": {
        "run": RUNS / "R05_dual_f0_quality_plus_dropout_seed42_sched16000_stop16000_a2_dsm_dropout20",
        "record": RECORDS / "rebuild_v1_a2_formal_16k_20260919",
    },
    "R05-seed17": {
        "run": RUNS / "R05_dual_f0_quality_plus_dropout_seed17_sched16000_stop16000",
        "record": RECORDS / "rebuild_v1_r05_seed17_formal_16k_20260919",
    },
    "R01-seed17": {
        "run": RUNS / "R01_optical_only_seed17_sched16000_stop16000",
        "record": RECORDS / "rebuild_v1_r01_seed17_formal_16k_20260919",
    },
    "C-OO-QD-seed17": {
        "run": RUNS / "C_OO_QD_dual_optical_gray_quality_plus_dropout_seed17_sched16000_stop16000",
        "record": RECORDS / "rebuild_v1_c_oo_qd_seed17_formal_16k_20260919",
    },
}

SMALL_FILES = (
    "summary.json",
    "run_metadata.json",
    "val_history.csv",
    "augmentation_counts.json",
)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_manifest(directory):
    rows = []
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.name != "artifact_manifest.sha256":
            rows.append(f"{sha256_file(path)}  {path.name}")
    (directory / "artifact_manifest.sha256").write_text(
        "\n".join(rows) + "\n", encoding="utf-8"
    )


def main():
    archived = {}
    for experiment_id, spec in EXPERIMENTS.items():
        run_dir = spec["run"]
        record_dir = spec["record"]
        summary_path = run_dir / "summary.json"
        checkpoint = run_dir / "best_model.pth"
        if not summary_path.is_file() or not checkpoint.is_file():
            raise FileNotFoundError(f"missing completed run: {run_dir}")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if int(summary.get("global_step", -1)) != 16000:
            raise RuntimeError(f"incomplete run: {run_dir}")
        if summary.get("test6_loaded") is not False:
            raise RuntimeError(f"TEST6 safety failure: {run_dir}")

        record_dir.mkdir(parents=True, exist_ok=True)
        copied = []
        for name in SMALL_FILES:
            source = run_dir / name
            if source.is_file():
                target = record_dir / name
                shutil.copy2(source, target)
                if target.suffix == ".csv":
                    target.write_bytes(target.read_bytes().replace(b"\r\n", b"\n"))
                copied.append(name)

        checkpoint_reference = {
            "experiment_id": experiment_id,
            "server_only": True,
            "uploaded_to_git": False,
            "path": str(checkpoint.resolve()),
            "size_bytes": checkpoint.stat().st_size,
            "sha256": sha256_file(checkpoint),
            "reason_not_uploaded": "Large binary checkpoint retained on the experiment server.",
        }
        write_json(record_dir / "checkpoint_reference.json", checkpoint_reference)
        write_manifest(record_dir)
        archived[experiment_id] = {
            "record_directory": str(record_dir.relative_to(ROOT)),
            "copied_files": copied,
            "checkpoint_reference": str((record_dir / "checkpoint_reference.json").relative_to(ROOT)),
        }
        print("ARCHIVED", experiment_id, record_dir, flush=True)

    queue_source = RECORDS / "rebuild_v1_next_queue_20260918/status.tsv"
    queue_archive = RECORDS / "rebuild_v1_next_queue_archive_20260920"
    queue_archive.mkdir(parents=True, exist_ok=True)
    if not queue_source.is_file():
        raise FileNotFoundError(queue_source)
    shutil.copy2(queue_source, queue_archive / "queue_status.txt")

    index = {
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "historical_test6_loaded": False,
        "experiments": archived,
        "existing_evaluation_records": [
            "records/rebuild_v1_r05_local_failure_diagnostics_20260918/",
            "records/rebuild_v1_c_oo_qd_local_failure_diagnostics_20260918/",
            "records/rebuild_v1_local_failure_comparison_20260918/",
            "records/rebuild_v1_a1_robust_eval_20260918/",
            "records/rebuild_v1_a2_robust_eval_20260918/",
            "records/rebuild_v1_r05_seed17_robust_eval_20260918/",
            "records/rebuild_v1_c_oo_qd_seed17_robust_eval_20260918/",
        ],
        "queue_status": "records/rebuild_v1_next_queue_archive_20260920/queue_status.txt",
    }
    write_json(queue_archive / "archive_index.json", index)
    write_manifest(queue_archive)
    print("ARCHIVE COMPLETE", queue_archive)


if __name__ == "__main__":
    main()
