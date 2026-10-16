#!/usr/bin/env bash
set -uo pipefail

R=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
O=$R/records/rebuild_v1_d9a_local_down8_fix1_queue_20260923
export CUDA_VISIBLE_DEVICES=0
export CUBLAS_WORKSPACE_CONFIG=:4096:8
cd "$R" || exit 2
mkdir -p "$O"
exec 9>"$O/lock"
flock -n 9 || exit 3

rec() { printf '%s\t%s\t%s\t%s\n' "$(date -Is)" "$1" "$2" "${3:-}" >> "$O/status.tsv"; }
run_stage() {
  local name=$1
  shift
  python scripts/validate_execution_boundaries.py --output "$O" --torch-check >> "$O/queue.log" 2>&1
  local preflight=$?
  if [[ $preflight -ne 0 ]]; then
    rec "$name" FAILED "preflight_$preflight"
    return 0
  fi
  rec "$name" START
  timeout --foreground --signal=TERM --kill-after=60s 7200 "$@" > "$O/$name.log" 2>&1
  local rc=$?
  if [[ $rc -eq 0 ]]; then rec "$name" COMPLETE 0; else rec "$name" FAILED "$rc"; fi
  return 0
}

rec QUEUE START "$(git rev-parse HEAD)"
for seed in 42 17; do
  run_stage "D9A_FIX1_${seed}_local_down8" \
    python -u scripts/eval_rebuild_v1_d9a_benefit.py \
    --seed "$seed" --condition dsm_local_down8_q1 --tag fix1
done
failures=$(awk -F '\t' '$3=="FAILED"{n++} END{print n+0}' "$O/status.tsv")
rec QUEUE FINISHED "failures=$failures"
exit 0
