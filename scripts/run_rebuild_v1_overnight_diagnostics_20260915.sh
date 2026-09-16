#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
cd "$ROOT"

export CUDA_VISIBLE_DEVICES=0

PIDFILE="records/rebuild_v1_R02_budget_pilot_12k_20260915.pid"
TRAIN_LOG="records/rebuild_v1_R02_budget_pilot_12k_20260915.log"
RUN_DIR="runs/rebuild_v1/R02_dual_f0_seed42_sched12000_stop12000"
QUEUE_LOG="records/rebuild_v1_overnight_diagnostics_20260915.log"

exec > >(tee -a "$QUEUE_LOG") 2>&1

echo "===================================================================================================="
echo "REBUILD_V1 OVERNIGHT DIAGNOSTIC QUEUE"
date
echo "===================================================================================================="

if [[ ! -f "$PIDFILE" ]]; then
  echo "[STOP] missing PID file: $PIDFILE"
  exit 2
fi

PID="$(cat "$PIDFILE")"
echo "R02 PID=$PID"
echo "Waiting for R02 12k completion before using GPU0..."

# Completion is determined primarily by the durable run artifact rather than
# only by kill -0. A completed training process may remain visible briefly as
# a zombie/unreaped PID, in which case kill -0 still succeeds forever.
while true; do
  if [[ -f "$RUN_DIR/summary.json" ]]; then
    echo "R02 summary.json detected; advancing to completion gate."
    break
  fi

  if ! kill -0 "$PID" 2>/dev/null; then
    echo "R02 PID no longer exists; advancing to completion gate."
    break
  fi

  STAT="$(ps -o stat= -p "$PID" 2>/dev/null | awk '{print $1}' || true)"
  if [[ "$STAT" == Z* ]]; then
    echo "R02 PID is zombie/unreaped ($STAT); advancing to completion gate."
    break
  fi

  sleep 60
done

echo "Checking R02 completion gate..."

if [[ ! -f "$RUN_DIR/summary.json" ]]; then
  echo "[STOP] R02 summary.json missing; do not run downstream diagnostics."
  tail -n 120 "$TRAIN_LOG" || true
  exit 3
fi

python - <<'PY'
import json
from pathlib import Path
p = Path("runs/rebuild_v1/R02_dual_f0_seed42_sched12000_stop12000/summary.json")
s = json.loads(p.read_text(encoding="utf-8"))
print("R02 summary:", s)
if int(s.get("global_step", -1)) != 12000:
    raise SystemExit("R02 did not reach step 12000; abort overnight diagnostics")
if s.get("test6_loaded") is not False:
    raise SystemExit("unexpected test6_loaded metadata")
print("[PASS] R02 12k completion gate")
PY

echo
echo "===== syntax gates ====="
python -m py_compile \
  scripts/eval_rebuild_v1_r02_corruption_screen.py \
  scripts/audit_rebuild_v1_resume_exactness.py

echo
echo "===== A. R02 corruption screen on VAL2 only ====="
python -u scripts/eval_rebuild_v1_r02_corruption_screen.py \
  2>&1 | tee records/rebuild_v1_r02_corruption_screen_20260915.log

echo
echo "===== B. REBUILD_V1 resume exactness audit ====="
python -u scripts/audit_rebuild_v1_resume_exactness.py \
  2>&1 | tee records/rebuild_v1_resume_exactness_20260915.log

echo
echo "===================================================================================================="
echo "OVERNIGHT DIAGNOSTICS COMPLETE"
date
echo "R02 val curve: $RUN_DIR/val_history.csv"
echo "R02 corruption: records/rebuild_v1_r02_corruption_screen_20260915/dataset_metrics.csv"
echo "Resume exactness: records/rebuild_v1_resume_exactness_20260915/result.json"
echo "Queue log: $QUEUE_LOG"
echo "===================================================================================================="
