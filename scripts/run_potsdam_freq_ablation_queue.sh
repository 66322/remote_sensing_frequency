#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
cd "$ROOT"

export CUDA_VISIBLE_DEVICES=0

STATUS_FILE="$ROOT/records/potsdam_freq_ablation_queue_status.tsv"

echo -e "variant\tstart_time\tend_time\tstatus\trun_dir" \
> "$STATUS_FILE"

echo "======================================================================"
echo "POTSDAM FREQUENCY ABLATION FORMAL QUEUE"
echo "F0 -> F1 -> F2 -> F3"
echo "RGB + raw DSM"
echo "Train18 / Test6"
echo "START: $(date --iso-8601=seconds)"
echo "======================================================================"

for V in F0 F1 F2 F3
do
    START_TIME=$(date --iso-8601=seconds)

    RUN_DIR="$ROOT/runs/Thesis_Ch4_NoSR_Ablation_Potsdam_${V}_seed42"
    LOG="$ROOT/records/train_potsdam_${V}_seed42.log"
    SUMMARY_LOG="$ROOT/records/summary_potsdam_${V}_seed42.log"

    echo
    echo "######################################################################"
    echo "START POTSDAM ${V}"
    echo "START TIME: ${START_TIME}"
    echo "RUN DIR: ${RUN_DIR}"
    echo "LOG: ${LOG}"
    echo "######################################################################"

    if [ -e "$RUN_DIR" ]; then
        echo "ERROR: run directory already exists:"
        echo "$RUN_DIR"
        exit 10
    fi

    python -u \
        scripts/train_potsdam_freq_ablation.py \
        --variant "$V" \
        > "$LOG" \
        2>&1

    END_TIME=$(date --iso-8601=seconds)

    if ! grep -q \
        "FORMAL TRAINING COMPLETE" \
        "$LOG"
    then
        echo -e \
        "${V}\t${START_TIME}\t${END_TIME}\tFAILED\t${RUN_DIR}" \
        >> "$STATUS_FILE"

        echo "ERROR: Potsdam ${V} did not complete normally."
        echo "QUEUE STOPPED."
        exit 20
    fi

    echo "[PASS] POTSDAM ${V} FORMAL TRAINING COMPLETE"

    python \
        scripts/summarize_ablation_run.py \
        --run-dir "$RUN_DIR" \
        > "$SUMMARY_LOG" \
        2>&1

    if [ ! -f "$RUN_DIR/final_summary.json" ]; then
        echo -e \
        "${V}\t${START_TIME}\t${END_TIME}\tSUMMARY_FAILED\t${RUN_DIR}" \
        >> "$STATUS_FILE"

        echo "ERROR: final_summary.json missing for ${V}"
        exit 30
    fi

    echo -e \
    "${V}\t${START_TIME}\t${END_TIME}\tCOMPLETE\t${RUN_DIR}" \
    >> "$STATUS_FILE"

    echo
    echo "======================================================================"
    echo "POTSDAM ${V} COMPLETE"
    echo "END TIME: ${END_TIME}"
    echo "SUMMARY: ${RUN_DIR}/final_summary.json"
    echo "======================================================================"

    sync
done

echo
echo "======================================================================"
echo "POTSDAM FREQUENCY ABLATION QUEUE COMPLETE"
echo "F0 COMPLETE"
echo "F1 COMPLETE"
echo "F2 COMPLETE"
echo "F3 COMPLETE"
echo "END: $(date --iso-8601=seconds)"
echo "======================================================================"
