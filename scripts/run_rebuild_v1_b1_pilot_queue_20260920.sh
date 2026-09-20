#!/usr/bin/env bash
set -uo pipefail

R=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
O=$R/records/rebuild_v1_b1_pilot_queue_fix2_20260920
export CUDA_VISIBLE_DEVICES=0
export CUBLAS_WORKSPACE_CONFIG=:4096:8
cd "$R" || exit 2
mkdir -p "$O"
exec 9>"$O/lock"
flock -n 9 || exit 3

rec() {
  printf '%s\t%s\t%s\t%s\n' "$(date -Is)" "$1" "$2" "${3:-}" >>"$O/status.tsv"
}

run() {
  local name=$1
  local limit=$2
  shift 2
  python scripts/validate_execution_boundaries.py \
    --torch-check --output "$O/boundary.json" >>"$O/queue.log" 2>&1 || return 90
  rec "$name" START
  timeout --foreground --signal=TERM --kill-after=60s "$limit" "$@" \
    >"$O/$name.log" 2>&1
  local rc=$?
  if [[ $rc == 0 ]]; then
    rec "$name" COMPLETE 0
  else
    rec "$name" FAILED "$rc"
  fi
  return "$rc"
}

train_and_evaluate() {
  local label=$1
  local config=$2
  local run_dir=$3
  local eval_out=$4

  if run "${label}_SMOKE" 2400 python -u scripts/train_rebuild_v1_b1_distillation.py \
      --config "$config" --smoke-steps 20 --smoke-eval --run-tag queue20260920_fix2; then
    if run "$label" 64800 python -u scripts/train_rebuild_v1_b1_distillation.py \
        --config "$config"; then
      run "${label}_ROBUST_EVAL" 21600 python -u \
        scripts/eval_rebuild_v1_dual_robust_conditions.py \
        --variant R05 --config "$config" --run-dir "$run_dir" --out "$eval_out"
    else
      rec "${label}_ROBUST_EVAL" SKIPPED "training_failed"
    fi
  else
    rec "$label" SKIPPED "smoke_failed"
    rec "${label}_ROBUST_EVAL" SKIPPED "smoke_failed"
  fi
  return 0
}

rec QUEUE START "$(git rev-parse HEAD)"

train_and_evaluate \
  B1_C \
  configs/rebuild_v1/b1_c_ce_control_4k.json \
  runs/rebuild_v1/B1_C_ce_control_seed42_sched4000_stop4000 \
  records/rebuild_v1_b1_c_robust_eval_20260920

train_and_evaluate \
  B1_KD \
  configs/rebuild_v1/b1_kd_safe_teacher_4k.json \
  runs/rebuild_v1/B1_KD_safe_teacher_seed42_sched4000_stop4000 \
  records/rebuild_v1_b1_kd_robust_eval_20260920

train_and_evaluate \
  B1_SAFE \
  configs/rebuild_v1/b1_safe_fallback_4k.json \
  runs/rebuild_v1/B1_SAFE_fallback_seed42_sched4000_stop4000 \
  records/rebuild_v1_b1_safe_robust_eval_20260920

run B1_SUMMARY 600 python -u scripts/summarize_rebuild_v1_b1_pilot.py
rec QUEUE FINISHED 0
