#!/usr/bin/env bash
set -uo pipefail

ROOT="/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
RECORDS="$ROOT/records/rebuild_v1_next_queue_20260918"
STATUS="$RECORDS/status.tsv"
QUEUE_LOG="$RECORDS/queue.log"
STOP_FILE="$RECORDS/STOP_AFTER_CURRENT_STAGE"
LOCK_FILE="$RECORDS/queue.lock"

export CUDA_VISIBLE_DEVICES=0
export CUBLAS_WORKSPACE_CONFIG=:4096:8

cd "$ROOT" || exit 2
mkdir -p "$RECORDS"
touch "$STATUS" "$QUEUE_LOG"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  printf '[%s] another queue instance owns %s\n' "$(date -Is)" "$LOCK_FILE" | tee -a "$QUEUE_LOG"
  exit 3
fi

stamp() { date -Is; }
log() { printf '[%s] %s\n' "$(stamp)" "$*" | tee -a "$QUEUE_LOG"; }
record() { printf '%s\t%s\t%s\t%s\n' "$(stamp)" "$1" "$2" "${3:-}" >> "$STATUS"; }

boundary_check() {
  [[ "$PWD" == "$ROOT" ]] || return 90
  [[ "$ROOT" == /home/jovyan/zzx/* ]] || return 91
  [[ "${CUDA_VISIBLE_DEVICES:-}" == "0" ]] || return 92
  python scripts/validate_execution_boundaries.py --torch-check --output "$RECORDS/boundary_latest.json" >> "$QUEUE_LOG" 2>&1
}

run_stage() {
  local stage="$1"
  local seconds="$2"
  local logfile="$3"
  shift 3
  if [[ -e "$STOP_FILE" ]]; then
    log "STOP requested before $stage"
    record "$stage" "STOPPED" "stop file"
    record "QUEUE" "STOPPED" "$stage"
    exit 0
  fi
  boundary_check
  local rc=$?
  if [[ $rc -ne 0 ]]; then
    log "BOUNDARY FAILURE before $stage rc=$rc; stopping queue"
    record "$stage" "BOUNDARY_FAILED" "$rc"
    exit "$rc"
  fi
  log "START $stage"
  record "$stage" "START" ""
  timeout --foreground --signal=TERM --kill-after=60s "$seconds" "$@" > "$logfile" 2>&1
  local rc=$?
  if [[ $rc -eq 0 ]]; then
    log "COMPLETE $stage"
    record "$stage" "COMPLETE" "0"
  else
    log "FAILED $stage rc=$rc; continuing"
    record "$stage" "FAILED" "$rc"
  fi
  return "$rc"
}

summary_ok() {
  local path="$1"
  local step="$2"
  python - "$path" "$step" <<'PY' >/dev/null 2>&1
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
if not p.is_file():
    raise SystemExit(1)
s = json.load(open(p, encoding="utf-8"))
assert int(s.get("global_step", -1)) == int(sys.argv[2]), s
assert s.get("test6_loaded") is False, s
PY
}

train_stage() {
  local stage="$1"
  local script="$2"
  local config="$3"
  local run_dir="$4"
  local tag="$5"
  local seed_override="$6"
  local logfile="$RECORDS/${stage}.log"
  local -a cmd=(python -u "$script" --config "$config")
  [[ -n "$tag" ]] && cmd+=(--run-tag "$tag")
  [[ -n "$seed_override" ]] && cmd+=(--seed-override "$seed_override")
  if summary_ok "$run_dir/summary.json" 16000; then
    log "SKIP $stage: valid completed summary"
    record "$stage" "SKIPPED_COMPLETE" "0"
    return 0
  fi
  if [[ -f "$run_dir/last_train_state.pth" ]]; then
    cmd+=(--resume)
  elif [[ -e "$run_dir" ]]; then
    log "FAILED $stage: collision without resumable state; continuing"
    record "$stage" "FAILED_COLLISION" "73"
    return 73
  fi
  run_stage "$stage" 43200 "$logfile" "${cmd[@]}"
}

smoke_stage() {
  local stage="$1"
  local config="$2"
  local tag="$3"
  local run_dir="$4"
  if summary_ok "$run_dir/summary.json" 20; then
    log "SKIP $stage: valid completed smoke"
    record "$stage" "SKIPPED_COMPLETE" "0"
    return 0
  fi
  if [[ -e "$run_dir" ]]; then
    log "FAILED $stage: smoke directory collision; continuing"
    record "$stage" "FAILED_COLLISION" "73"
    return 73
  fi
  run_stage "$stage" 3600 "$RECORDS/${stage}.log" \
    python -u scripts/train_rebuild_v1_r05_quality_plus_dropout.py \
    --config "$config" --smoke-steps 20 --smoke-eval --run-tag "$tag"
}

log "REBUILD_V1 NEXT EXPERIMENT QUEUE"
log "ROOT=$ROOT GPU_PHYSICAL=0 PID=$$ BRANCH=$(git branch --show-current) HEAD=$(git rev-parse HEAD)"
record "QUEUE" "START" "$(git rev-parse HEAD)"

if run_stage "D1_D3_R05_SMOKE" 1800 "$RECORDS/D1_D3_R05_SMOKE.log" \
  python -u scripts/eval_rebuild_v1_local_failure_diagnostics.py --variant R05 --smoke; then
  run_stage "D1_D3_R05" 10800 "$RECORDS/D1_D3_R05.log" \
    python -u scripts/eval_rebuild_v1_local_failure_diagnostics.py --variant R05
else
  record "D1_D3_R05" "SKIPPED_DEPENDENCY" "D1_D3_R05_SMOKE"
fi
if run_stage "D1_D3_C_OO_QD_SMOKE" 1800 "$RECORDS/D1_D3_C_OO_QD_SMOKE.log" \
  python -u scripts/eval_rebuild_v1_local_failure_diagnostics.py --variant C-OO-QD --smoke; then
  run_stage "D1_D3_C_OO_QD" 10800 "$RECORDS/D1_D3_C_OO_QD.log" \
    python -u scripts/eval_rebuild_v1_local_failure_diagnostics.py --variant C-OO-QD
else
  record "D1_D3_C_OO_QD" "SKIPPED_DEPENDENCY" "D1_D3_C_OO_QD_SMOKE"
fi
run_stage "D1_D3_SUMMARY" 600 "$RECORDS/D1_D3_SUMMARY.log" \
  python -u scripts/summarize_rebuild_v1_local_failure_diagnostics.py

A1_CONFIG="configs/rebuild_v1/a1_no_optical_dropout_16k.json"
A1_SMOKE="runs/rebuild_v1/R05_dual_f0_quality_plus_dropout_seed42_smoke20_a1_smoke"
A1_RUN="runs/rebuild_v1/R05_dual_f0_quality_plus_dropout_seed42_sched16000_stop16000_a1_no_optical_dropout"
if smoke_stage "A1_SMOKE" "$A1_CONFIG" "a1_smoke" "$A1_SMOKE"; then
  if train_stage "A1_FORMAL" scripts/train_rebuild_v1_r05_quality_plus_dropout.py "$A1_CONFIG" "$A1_RUN" "a1_no_optical_dropout" ""; then
    run_stage "A1_ROBUST_EVAL" 10800 "$RECORDS/A1_ROBUST_EVAL.log" \
      python -u scripts/eval_rebuild_v1_dual_robust_conditions.py --variant R05 \
      --config "$A1_CONFIG" --run-dir "$A1_RUN" \
      --out records/rebuild_v1_a1_robust_eval_20260918
  else
    record "A1_ROBUST_EVAL" "SKIPPED_DEPENDENCY" "A1_FORMAL"
  fi
else
  record "A1_FORMAL" "SKIPPED_DEPENDENCY" "A1_SMOKE"
  record "A1_ROBUST_EVAL" "SKIPPED_DEPENDENCY" "A1_SMOKE"
fi

A2_CONFIG="configs/rebuild_v1/a2_dsm_dropout20_no_optical_dropout_16k.json"
A2_SMOKE="runs/rebuild_v1/R05_dual_f0_quality_plus_dropout_seed42_smoke20_a2_smoke"
A2_RUN="runs/rebuild_v1/R05_dual_f0_quality_plus_dropout_seed42_sched16000_stop16000_a2_dsm_dropout20"
if smoke_stage "A2_SMOKE" "$A2_CONFIG" "a2_smoke" "$A2_SMOKE"; then
  if train_stage "A2_FORMAL" scripts/train_rebuild_v1_r05_quality_plus_dropout.py "$A2_CONFIG" "$A2_RUN" "a2_dsm_dropout20" ""; then
    run_stage "A2_ROBUST_EVAL" 10800 "$RECORDS/A2_ROBUST_EVAL.log" \
      python -u scripts/eval_rebuild_v1_dual_robust_conditions.py --variant R05 \
      --config "$A2_CONFIG" --run-dir "$A2_RUN" \
      --out records/rebuild_v1_a2_robust_eval_20260918
  else
    record "A2_ROBUST_EVAL" "SKIPPED_DEPENDENCY" "A2_FORMAL"
  fi
else
  record "A2_FORMAL" "SKIPPED_DEPENDENCY" "A2_SMOKE"
  record "A2_ROBUST_EVAL" "SKIPPED_DEPENDENCY" "A2_SMOKE"
fi

R05_S17="runs/rebuild_v1/R05_dual_f0_quality_plus_dropout_seed17_sched16000_stop16000"
if train_stage "R05_SEED17" scripts/train_rebuild_v1_r05_quality_plus_dropout.py configs/rebuild_v1/r05_quality_plus_dropout_16k.json "$R05_S17" "" "17"; then
  run_stage "R05_SEED17_ROBUST_EVAL" 10800 "$RECORDS/R05_SEED17_ROBUST_EVAL.log" \
    python -u scripts/eval_rebuild_v1_dual_robust_conditions.py --variant R05 \
    --run-dir "$R05_S17" --out records/rebuild_v1_r05_seed17_robust_eval_20260918
else
  record "R05_SEED17_ROBUST_EVAL" "SKIPPED_DEPENDENCY" "R05_SEED17"
fi

R01_S17="runs/rebuild_v1/R01_optical_only_seed17_sched16000_stop16000"
train_stage "R01_SEED17" scripts/train_rebuild_v1_r01_optical_only.py configs/rebuild_v1/r01_optical_only_16k.json "$R01_S17" "" "17"

COOQD_S17="runs/rebuild_v1/C_OO_QD_dual_optical_gray_quality_plus_dropout_seed17_sched16000_stop16000"
if train_stage "C_OO_QD_SEED17" scripts/train_rebuild_v1_c_oo_qd.py configs/rebuild_v1/c_oo_qd_optical_gray_16k.json "$COOQD_S17" "" "17"; then
  run_stage "C_OO_QD_SEED17_ROBUST_EVAL" 10800 "$RECORDS/C_OO_QD_SEED17_ROBUST_EVAL.log" \
    python -u scripts/eval_rebuild_v1_dual_robust_conditions.py --variant C-OO-QD \
    --run-dir "$COOQD_S17" --out records/rebuild_v1_c_oo_qd_seed17_robust_eval_20260918
else
  record "C_OO_QD_SEED17_ROBUST_EVAL" "SKIPPED_DEPENDENCY" "C_OO_QD_SEED17"
fi

log "QUEUE FINISHED; see $STATUS"
record "QUEUE" "FINISHED" "0"
