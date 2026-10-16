#!/usr/bin/env bash
set -uo pipefail

R=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
O=$R/records/rebuild_v1_d7_queue_20260922
export CUDA_VISIBLE_DEVICES=0
export CUBLAS_WORKSPACE_CONFIG=:4096:8
cd "$R" || exit 2
mkdir -p "$O"
exec 9>"$O/lock"
flock -n 9 || exit 3

rec() { printf '%s\t%s\t%s\t%s\n' "$(date -Is)" "$1" "$2" "${3:-}" >> "$O/status.tsv"; }
run_stage() {
  local name=$1 limit=$2 gpu=$3
  shift 3
  local check=(python scripts/validate_execution_boundaries.py --output "$O")
  [[ "$gpu" == "gpu" ]] && check+=(--torch-check)
  "${check[@]}" >> "$O/queue.log" 2>&1
  local preflight=$?
  if [[ $preflight -ne 0 ]]; then
    rec "$name" FAILED "preflight_$preflight"
    return 0
  fi
  rec "$name" START
  timeout --foreground --signal=TERM --kill-after=60s "$limit" "$@" > "$O/$name.log" 2>&1
  local rc=$?
  if [[ $rc -eq 0 ]]; then rec "$name" COMPLETE 0; else rec "$name" FAILED "$rc"; fi
  return 0
}

rec QUEUE START "$(git rev-parse HEAD)"
run_stage D7_DATA_SMOKE 1800 cpu python -u scripts/audit_rebuild_v1_d7_data_sampling.py --smoke
run_stage D7_DATA 7200 cpu python -u scripts/audit_rebuild_v1_d7_data_sampling.py --samples 20000
run_stage D7_ERROR_SMOKE 2400 gpu python -u scripts/eval_rebuild_v1_d7_semantic_errors.py --seed 42 --smoke
run_stage D7_ERROR_SEED42 14400 gpu python -u scripts/eval_rebuild_v1_d7_semantic_errors.py --seed 42
run_stage D7_ERROR_SEED17 14400 gpu python -u scripts/eval_rebuild_v1_d7_semantic_errors.py --seed 17
run_stage D7_SUMMARY 600 cpu python -u scripts/summarize_rebuild_v1_d7.py
failures=$(awk -F '\t' '$3=="FAILED"{n++} END{print n+0}' "$O/status.tsv")
rec QUEUE FINISHED "failures=$failures"
exit 0
