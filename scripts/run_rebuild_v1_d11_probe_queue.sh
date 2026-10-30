#!/usr/bin/env bash
set -uo pipefail
R=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
O=$R/records/rebuild_v1_d11_probe_queue_20260923
export CUDA_VISIBLE_DEVICES=0 CUDA_DEVICE_ORDER=PCI_BUS_ID CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
export TMPDIR=/home/jovyan/zzx/tmp
cd "$R" || exit 2
mkdir -p "$O" "$TMPDIR"
exec 9>"$O/lock"
flock -n 9 || exit 3
if [[ -e "$O/status.tsv" ]]; then echo "Existing queue record; refusing to overwrite. Use a versioned fix if needed."; exit 4; fi
failures=0
rec() { printf '%s\t%s\t%s\t%s\n' "$(date -Is)" "$1" "$2" "${3:-}" >> "$O/status.tsv"; }
run_stage() {
  local name=$1 limit=$2
  shift 2
  rec "$name" START
  python -B scripts/validate_execution_boundaries.py --output "$O" --torch-check >> "$O/queue.log" 2>&1
  local rc=$?
  if [[ $rc -eq 0 ]]; then
    timeout --foreground --signal=TERM --kill-after=60s "$limit" "$@" > "$O/$name.log" 2>&1
    rc=$?
  fi
  if [[ $rc -eq 0 ]]; then rec "$name" COMPLETE 0; else rec "$name" FAILED "$rc"; failures=$((failures+1)); fi
  return 0
}
rec QUEUE START "$(git rev-parse HEAD)"
run_stage D11_NUMERICS 600 python -B -m unittest discover -s tests -p test_d11_benefit_probe.py -v
run_stage D11_SMOKE 7200 python -B -u scripts/export_rebuild_v1_d11_samples.py --seed 42 --tile 6_7 --smoke
for seed in 42 17; do
  for tile in 6_7 6_8 6_9 7_7 7_8 7_9 6_10 7_10 4_11 7_11; do
    run_stage "D11_EXPORT_${seed}_${tile}" 10800 python -B -u scripts/export_rebuild_v1_d11_samples.py --seed "$seed" --tile "$tile"
  done
  for model in confidence entropy disagreement expert frequency expert_frequency; do
    run_stage "D11_FIT_${seed}_${model}" 7200 python -B -u scripts/run_rebuild_v1_d11_probe.py --seed "$seed" --model "$model"
  done
done
run_stage D11_SUMMARY 600 python -B -u scripts/summarize_rebuild_v1_d11_probe.py
rec QUEUE FINISHED "failures=$failures"
exit 0
