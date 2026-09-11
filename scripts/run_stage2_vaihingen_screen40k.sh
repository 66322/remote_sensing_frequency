#!/usr/bin/env bash

set -euo pipefail

cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro

export CUDA_VISIBLE_DEVICES=0

LOG_DIR="records"
STATUS="$LOG_DIR/stage2_vaihingen_screen40k_status.tsv"

mkdir -p "$LOG_DIR"

echo -e "variant\tstatus\tstart\tend" > "$STATUS"

run_one () {
    VARIANT="$1"

    LOG="$LOG_DIR/stage2_vaihingen_${VARIANT}_screen40k_20260828.log"

    START="$(date '+%F %T %z')"

    echo -e "${VARIANT}\tRUNNING\t${START}\t-" \
        >> "$STATUS"

    echo "============================================================"
    echo "START ${VARIANT} @ ${START}"
    echo "============================================================"

    python -u \
        scripts/train_vaihingen_freqfusion_recipe.py \
        --variant "$VARIANT" \
        --max-steps 40000 \
        2>&1 | tee "$LOG"

    END="$(date '+%F %T %z')"

    echo -e "${VARIANT}\tCOMPLETE\t${START}\t${END}" \
        >> "$STATUS"

    echo "============================================================"
    echo "COMPLETE ${VARIANT} @ ${END}"
    echo "============================================================"
}

run_one F0
run_one F3

echo "ALL STAGE-2 40K SCREENING COMPLETE"
