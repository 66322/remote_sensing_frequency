#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
cd "$ROOT"

export CUDA_VISIBLE_DEVICES=0

QUEUE_RECORD="$ROOT/records/vaihingen_freq_ablation_queue_status.tsv"

echo -e "variant\tstart_time\tend_time\tstatus\trun_dir" \
> "$QUEUE_RECORD"

echo "======================================================================"
echo "VAIHINGEN FREQUENCY ABLATION FORMAL QUEUE"
echo "F0 -> F1 -> F2"
echo "F3 = existing verified formal run"
echo "QUEUE START: $(date --iso-8601=seconds)"
echo "======================================================================"

for V in F0 F1 F2
do
    START_TIME=$(date --iso-8601=seconds)

    RUN_DIR="$ROOT/runs/Thesis_Ch4_NoSR_Ablation_Vaihingen_${V}_seed42"
    LOG="$ROOT/records/train_vaihingen_${V}_seed42.log"

    echo
    echo "######################################################################"
    echo "START VAIHINGEN ${V}"
    echo "START TIME: ${START_TIME}"
    echo "RUN DIR: ${RUN_DIR}"
    echo "LOG: ${LOG}"
    echo "######################################################################"

    python -u \
        scripts/train_vaihingen_freq_ablation.py \
        --variant "$V" \
        > "$LOG" \
        2>&1

    END_TIME=$(date --iso-8601=seconds)

    if ! grep -q \
        "FORMAL TRAINING COMPLETE" \
        "$LOG"
    then
        echo -e "${V}\t${START_TIME}\t${END_TIME}\tFAILED\t${RUN_DIR}" \
        >> "$QUEUE_RECORD"

        echo
        echo "ERROR: ${V} DID NOT COMPLETE NORMALLY"
        echo "QUEUE STOPPED."
        exit 20
    fi

    echo
    echo "[PASS] ${V} formal training complete"

    # ------------------------------------------------------------
    # Automatically create unified final summary
    # ------------------------------------------------------------
    python \
        scripts/summarize_ablation_run.py \
        --run-dir "$RUN_DIR" \
        > "$ROOT/records/summary_vaihingen_${V}_seed42.log" \
        2>&1

    if [ ! -f "$RUN_DIR/final_summary.json" ]; then
        echo -e "${V}\t${START_TIME}\t${END_TIME}\tSUMMARY_FAILED\t${RUN_DIR}" \
        >> "$QUEUE_RECORD"

        echo "ERROR: final_summary.json missing for ${V}"
        exit 30
    fi

    echo -e "${V}\t${START_TIME}\t${END_TIME}\tCOMPLETE\t${RUN_DIR}" \
    >> "$QUEUE_RECORD"

    echo
    echo "======================================================================"
    echo "VAIHINGEN ${V} COMPLETE"
    echo "END TIME: ${END_TIME}"
    echo "SUMMARY: ${RUN_DIR}/final_summary.json"
    echo "======================================================================"

    sync
done

echo
echo "======================================================================"
echo "VAIHINGEN FREQUENCY ABLATION QUEUE COMPLETE"
echo "F0 COMPLETE"
echo "F1 COMPLETE"
echo "F2 COMPLETE"
echo "F3 = EXISTING FORMAL RUN"
echo "END: $(date --iso-8601=seconds)"
echo "======================================================================"
