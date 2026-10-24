#!/usr/bin/env bash
set -uo pipefail

ROOT="/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
RECORDS="$ROOT/records/rebuild_v1_d4_queue_20260920"
STATUS="$RECORDS/status.tsv"
QUEUE_LOG="$RECORDS/queue.log"
LOCK_FILE="$RECORDS/queue.lock"

export CUDA_VISIBLE_DEVICES=0
export CUBLAS_WORKSPACE_CONFIG=:4096:8

cd "$ROOT" || exit 2
mkdir -p "$RECORDS"
touch "$STATUS" "$QUEUE_LOG"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  printf '[%s] another D4 queue owns the lock\n' "$(date -Is)" | tee -a "$QUEUE_LOG"
  exit 3
fi

stamp() { date -Is; }
log() { printf '[%s] %s\n' "$(stamp)" "$*" | tee -a "$QUEUE_LOG"; }
record() { printf '%s\t%s\t%s\t%s\n' "$(stamp)" "$1" "$2" "${3:-}" >> "$STATUS"; }

boundary_check() {
  [[ "$PWD" == "$ROOT" ]] || return 90
  [[ "$ROOT" == /home/jovyan/zzx/* ]] || return 91
  [[ "${CUDA_VISIBLE_DEVICES:-}" == "0" ]] || return 92
  python scripts/validate_execution_boundaries.py \
    --torch-check --output "$RECORDS/boundary_latest.json" \
    >> "$QUEUE_LOG" 2>&1
}

run_stage() {
  local stage="$1"
  local seconds="$2"
  shift 2
  boundary_check
  local rc=$?
  if [[ $rc -ne 0 ]]; then
    log "BOUNDARY FAILURE before $stage rc=$rc; stopping queue"
    record "$stage" "BOUNDARY_FAILED" "$rc"
    exit "$rc"
  fi
  log "START $stage"
  record "$stage" "START" ""
  timeout --foreground --signal=TERM --kill-after=60s "$seconds" \
    "$@" > "$RECORDS/${stage}.log" 2>&1
  rc=$?
  if [[ $rc -eq 0 ]]; then
    log "COMPLETE $stage"
    record "$stage" "COMPLETE" "0"
  else
    log "FAILED $stage rc=$rc; continuing"
    record "$stage" "FAILED" "$rc"
  fi
  return "$rc"
}

log "REBUILD_V1 D4 EXPERT COMPLEMENTARITY QUEUE"
log "ROOT=$ROOT GPU_PHYSICAL=0 PID=$$ BRANCH=$(git branch --show-current) HEAD=$(git rev-parse HEAD)"
record "QUEUE" "START" "$(git rev-parse HEAD)"

if run_stage "D4_SEED42_SMOKE" 1800 \
  python -u scripts/eval_rebuild_v1_d4_expert_complementarity.py --seed 42 --smoke; then
  run_stage "D4_SEED42" 14400 \
    python -u scripts/eval_rebuild_v1_d4_expert_complementarity.py --seed 42
else
  record "D4_SEED42" "SKIPPED_DEPENDENCY" "D4_SEED42_SMOKE"
fi

run_stage "D4_SEED17" 14400 \
  python -u scripts/eval_rebuild_v1_d4_expert_complementarity.py --seed 17

run_stage "D4_SUMMARY" 600 \
  python -u scripts/summarize_rebuild_v1_d4_expert_complementarity.py

log "D4 QUEUE FINISHED; see $STATUS"
record "QUEUE" "FINISHED" "0"
