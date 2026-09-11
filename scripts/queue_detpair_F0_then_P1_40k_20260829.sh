#!/usr/bin/env bash
set -u

ROOT="/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
PYTHON="/home/jovyan/miniconda3/envs/remote_sensing/bin/python"

F0_PID=2505501

F0_STATE="$ROOT/runs/Thesis_Ch4_NoSR_DetPair_F0_Vaihingen_F0_seed42_formal160k/last_train_state.pth"

P1_LOG="$ROOT/records/detpair_P1_resume2k_to40k_20260829.log"

cd "$ROOT" || exit 1

export CUDA_VISIBLE_DEVICES=0
export PYTHONHASHSEED=42
export CUBLAS_WORKSPACE_CONFIG=:4096:8

echo "============================================================"
echo "QUEUE START"
echo "time: $(date)"
echo "waiting for F0 PID: $F0_PID"
echo "check interval: 300 s"
echo "============================================================"

while true; do

    CMD="$(
        ps -p "$F0_PID" -o args= 2>/dev/null || true
    )"

    if echo "$CMD" | grep -q \
        "train_vaihingen_F0_detpair.py"; then

        echo "[$(date)] F0 still running..."
        sleep 300

    else
        break
    fi
done

echo
echo "[$(date)] F0 process exited."
echo "Checking last_train_state..."

if [ ! -f "$F0_STATE" ]; then
    echo "[ERROR] F0 last_train_state.pth not found."
    echo "[ERROR] P1 will NOT start."
    exit 1
fi

"$PYTHON" - <<PY
import torch
from pathlib import Path

p = Path("$F0_STATE")

obj = torch.load(
    p,
    map_location="cpu",
)

step = int(
    obj.get(
        "global_step",
        -1,
    )
)

print(
    "F0 global_step =",
    step,
)

if step != 40000:
    raise SystemExit(
        f"F0 incomplete: global_step={step}, expected 40000"
    )

print(
    "[PASS] F0 completed exactly 40000 steps"
)
PY

STATUS=$?

if [ "$STATUS" -ne 0 ]; then
    echo "[ERROR] F0 completion check failed."
    echo "[ERROR] P1 will NOT start."
    exit 1
fi

# Avoid duplicate P1 launch.
if pgrep -af \
    "train_vaihingen_P1_detpair.py" \
    | grep -q \
    -- "--max-steps 40000"; then

    echo "[ERROR] P1 40k appears to already be running."
    exit 1
fi

echo
echo "============================================================"
echo "START P1: 2k -> 40k"
echo "time: $(date)"
echo "============================================================"

"$PYTHON" -u \
    scripts/train_vaihingen_P1_detpair.py \
    --variant P1 \
    --resume \
    --max-steps 40000 \
    > "$P1_LOG" \
    2>&1

STATUS=$?

echo
echo "============================================================"
echo "P1 FINISHED"
echo "time: $(date)"
echo "exit code: $STATUS"
echo "============================================================"

exit "$STATUS"
