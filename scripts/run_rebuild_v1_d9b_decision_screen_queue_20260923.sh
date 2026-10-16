#!/usr/bin/env bash
set -uo pipefail

R=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
O=$R/records/rebuild_v1_d9b_decision_screen_queue_20260923
export CUDA_VISIBLE_DEVICES=0
export CUBLAS_WORKSPACE_CONFIG=:4096:8
cd "$R" || exit 2
mkdir -p "$O"
exec 9>"$O/lock"
flock -n 9 || exit 3

rec() { printf '%s\t%s\t%s\t%s\n' "$(date -Is)" "$1" "$2" "${3:-}" >> "$O/status.tsv"; }
run_stage() {
  local name=$1 limit=$2
  shift 2
  python scripts/validate_execution_boundaries.py --output "$O" --torch-check >> "$O/queue.log" 2>&1
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
run_stage D9B_TRAIN16_PROTOTYPES 3600 python -u scripts/build_rebuild_v1_d9b_train16_prototypes.py
run_stage D9B_SMOKE 3600 python -u scripts/eval_rebuild_v1_d9b_decision_benefit.py --seed 42 --condition clean --smoke
for seed in 42 17; do
  for condition in clean dsm_zero dsm_down8 dsm_blur5 dsm_noise_std010 dsm_shift_right_4px dsm_local_zero_q1 dsm_local_down8_q1; do
    run_stage "D9B_${seed}_${condition}" 7200 python -u scripts/eval_rebuild_v1_d9b_decision_benefit.py --seed "$seed" --condition "$condition"
  done
done
failures=$(awk -F '\t' '$3=="FAILED"{n++} END{print n+0}' "$O/status.tsv")
rec QUEUE FINISHED "failures=$failures"
exit 0
