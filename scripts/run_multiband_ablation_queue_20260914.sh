#!/usr/bin/env bash

set -uo pipefail

ROOT="/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"

cd "$ROOT" || exit 1

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate remote_sensing || exit 2

export CUDA_VISIBLE_DEVICES=0
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONPATH="$ROOT:${PYTHONPATH:-}"

mkdir -p .local_backups

# ============================================================
# Current R2 main run
# ============================================================

R2_PID=404289

R2_LOG=".local_backups/potsdam_adaptive_multiband_R2_10k_20260913.log"

R2_RUN="runs/potsdam_adaptive_multiband_seed42_10k"

QUEUE_LOG=".local_backups/multiband_ablation_queue_20260914.log"


stamp () {
    date '+%Y-%m-%d %H:%M:%S'
}


fail () {
    echo "[$(stamp)] [QUEUE FAIL] $*" \
        | tee -a "$QUEUE_LOG"
    exit 1
}


# ============================================================
# Validate completed experiment
# ============================================================

validate_run () {

    local run_dir="$1"
    local expected_step="$2"
    local name="$3"

    local train_csv="$run_dir/train_history.csv"
    local metric_csv="$run_dir/metrics_history.csv"

    if [ ! -f "$train_csv" ]; then
        fail "$name missing train_history.csv"
    fi

    if [ ! -f "$metric_csv" ]; then
        fail "$name missing metrics_history.csv"
    fi

    local last_step

    last_step="$(
        tail -n 1 "$train_csv" \
        | cut -d',' -f1
    )"

    echo \
        "[$(stamp)] $name last_step=$last_step" \
        | tee -a "$QUEUE_LOG"

    if [ "$last_step" != "$expected_step" ]; then
        fail \
            "$name expected step=$expected_step but got $last_step"
    fi

    if ! grep -q \
        "^${expected_step}," \
        "$metric_csv"
    then
        fail \
            "$name has no evaluation at step $expected_step"
    fi

    echo \
        "[$(stamp)] [PASS] $name validated" \
        | tee -a "$QUEUE_LOG"
}


# ============================================================
# Run one controlled ablation
# ============================================================

run_variant () {

    local label="$1"
    local mode="$2"

    local run_dir="runs/potsdam_multiband_${mode}_seed42"

    local log=".local_backups/potsdam_multiband_${label}_${mode}_6k_20260914.log"

    echo \
        "[$(stamp)] ============================================================" \
        | tee -a "$QUEUE_LOG"

    echo \
        "[$(stamp)] START $label : $mode -> 6000" \
        | tee -a "$QUEUE_LOG"

    echo \
        "[$(stamp)] run_dir=$run_dir" \
        | tee -a "$QUEUE_LOG"

    echo \
        "[$(stamp)] log=$log" \
        | tee -a "$QUEUE_LOG"

    # Never overwrite an existing experiment.
    if [ -e "$run_dir" ]; then
        fail \
            "$label run directory already exists: $run_dir"
    fi

    python -u \
        scripts/train_potsdam_multiband_variants.py \
        --variant F0 \
        --router-mode "$mode" \
        --max-steps 6000 \
        > "$log" \
        2>&1

    rc=$?

    if [ "$rc" -ne 0 ]; then

        echo \
            "[$(stamp)] [FAIL] $label exited rc=$rc" \
            | tee -a "$QUEUE_LOG"

        tail -80 "$log" \
            | tee -a "$QUEUE_LOG"

        exit "$rc"
    fi

    if ! grep -q \
        "FORMAL TRAINING COMPLETE" \
        "$log"
    then
        fail \
            "$label exited without FORMAL TRAINING COMPLETE"
    fi

    validate_run \
        "$run_dir" \
        "6000" \
        "$label"

    echo \
        "[$(stamp)] COMPLETE $label : $mode" \
        | tee -a "$QUEUE_LOG"
}


# ============================================================
# Queue start
# ============================================================

echo \
    "[$(stamp)] MULTI-BAND ABLATION QUEUE START" \
    | tee -a "$QUEUE_LOG"

echo \
    "[$(stamp)] Waiting for R2 PID=$R2_PID" \
    | tee -a "$QUEUE_LOG"


# ============================================================
# Wait for the currently running R2.
#
# R2 was launched from another shell, so shell `wait` cannot
# retrieve its exit code. We therefore wait for the process to
# disappear and then validate its persistent outputs.
# ============================================================

while true
do

    cmd="$(
        ps -p "$R2_PID" \
        -o args= \
        2>/dev/null \
        || true
    )"

    if echo "$cmd" \
        | grep -q \
        "train_potsdam_adaptive_multiband_10k.py"
    then

        sleep 60

    else

        break
    fi

done


echo \
    "[$(stamp)] R2 process ended; validating persistent outputs" \
    | tee -a "$QUEUE_LOG"


# ============================================================
# Validate R2
# ============================================================

if [ ! -f "$R2_LOG" ]; then
    fail \
        "R2 log missing: $R2_LOG"
fi

if ! grep -q \
    "FORMAL TRAINING COMPLETE" \
    "$R2_LOG"
then
    fail \
        "R2 terminated without FORMAL TRAINING COMPLETE"
fi

validate_run \
    "$R2_RUN" \
    "10000" \
    "R2_modality_spatial"


# ============================================================
# Controlled ablation sequence
#
# R3 first:
#   Does spatially varying routing matter?
#
# R1 second:
#   Does modality-specific routing matter?
#
# R4 last:
#   Does content adaptation matter?
# ============================================================

run_variant \
    "R3" \
    "modality_global"

run_variant \
    "R1" \
    "shared_spatial"

run_variant \
    "R4" \
    "modality_static"


echo \
    "[$(stamp)] ============================================================" \
    | tee -a "$QUEUE_LOG"

echo \
    "[$(stamp)] ALL SCHEDULED MULTI-BAND ABLATIONS COMPLETE" \
    | tee -a "$QUEUE_LOG"

echo \
    "[$(stamp)] Queue intentionally stops here." \
    | tee -a "$QUEUE_LOG"

exit 0
