#!/usr/bin/env bash
set -uo pipefail
R=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
O=$R/records/rebuild_v1_d10m_mechanism_queue_20260923
export CUDA_VISIBLE_DEVICES=0 CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/home/jovyan/zzx/tmp
cd "$R" || exit 2
mkdir -p "$O" "$TMPDIR"
exec 9>"$O/lock"
flock -n 9 || exit 3
failures=0
rec() { printf '%s\t%s\t%s\t%s\n' "$(date -Is)" "$1" "$2" "${3:-}" >> "$O/status.tsv"; }
run_stage() {
  local name=$1
  shift
  rec "$name" START
  python -B scripts/validate_execution_boundaries.py --output "$O" --torch-check >> "$O/queue.log" 2>&1
  local rc=$?
  if [[ $rc -eq 0 ]]; then
    timeout --foreground --signal=TERM --kill-after=60s 7200 "$@" > "$O/$name.log" 2>&1
    rc=$?
  fi
  if [[ $rc -eq 0 ]]; then rec "$name" COMPLETE 0; else rec "$name" FAILED "$rc"; failures=$((failures+1)); fi
  return 0
}
rec QUEUE START "$(git rev-parse HEAD)"
run_stage D10M_SMOKE python -B -u scripts/eval_rebuild_v1_d10m_mechanism.py --seed 42 --condition roll16 --smoke
for seed in 42 17; do
  for condition in clean roll4 roll16 roll32 edge4 edge16 edge32 dsm_blur5 dsm_noise_std010 dsm_zero; do
    run_stage "D10M_${seed}_${condition}" python -B -u scripts/eval_rebuild_v1_d10m_mechanism.py --seed "$seed" --condition "$condition"
  done
done
run_stage D10M_SUMMARY python -B -u scripts/summarize_rebuild_v1_d10m_mechanism.py
rec QUEUE FINISHED "failures=$failures"
exit 0
