#!/usr/bin/env bash
set -uo pipefail
R=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
O=$R/records/rebuild_v1_d14_intervention_queue_20260926
B=$R/records/rebuild_v1_d14_dsm_intervention_20260926
export CUDA_VISIBLE_DEVICES=0 CUDA_DEVICE_ORDER=PCI_BUS_ID CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
export TMPDIR=/home/jovyan/zzx/tmp
cd "$R" || exit 2
mkdir -p "$O" "$B" "$TMPDIR"
exec 9>"$O/lock"
flock -n 9 || exit 3
if [[ -e "$O/status.tsv" ]]; then
  echo "D14 queue already exists; refusing to overwrite"
  exit 4
fi
deadline=$(($(date +%s)+3600))
failures=0
last_rc=0
record() { printf '%s\t%s\t%s\t%s\n' "$(date -Is)" "$1" "$2" "${3:-}" >> "$O/status.tsv"; }
stage() {
  local name=$1 requested=$2
  shift 2
  local remaining=$((deadline-$(date +%s)))
  if (( remaining <= 0 )); then record "$name" SKIPPED time_budget; last_rc=124; return 0; fi
  local limit=$requested
  if (( remaining < limit )); then limit=$remaining; fi
  record "$name" START
  timeout --foreground --signal=TERM --kill-after=60s "${limit}s" "$@" > "$O/$name.log" 2>&1
  last_rc=$?
  if (( last_rc == 0 )); then record "$name" COMPLETE 0
  else record "$name" FAILED "$last_rc"; failures=$((failures+1)); fi
  return 0
}
record QUEUE START "$(git rev-parse HEAD)"
if ! git diff --quiet HEAD -- configs/rebuild_v1/d13_residual_overnight_20260924.json configs/rebuild_v1/d14_dsm_intervention_20260926.json scripts/d13_residual.py scripts/d14_intervention.py scripts/train_rebuild_v1_d13_residual.py scripts/eval_rebuild_v1_d13_residual.py scripts/eval_rebuild_v1_d14_intervention.py; then
  record QUEUE STOPPED tracked_source_differs_from_commit
  exit 1
fi
stage D14_BOUNDARIES 300 python -B scripts/validate_execution_boundaries.py --output "$O" --output "$B" --torch-check
if (( last_rc != 0 )); then record QUEUE STOPPED boundaries_failed; exit 1; fi
stage D14_NUMERICS 300 python -B -m unittest discover -s tests -p test_d14_intervention.py -v
if (( last_rc != 0 )); then record QUEUE STOPPED numerics_failed; exit 1; fi
stage D14_SMOKE_DSM 600 python -B -u scripts/eval_rebuild_v1_d14_intervention.py --arm dsm_ce --seed 42 --smoke
if (( last_rc != 0 )); then record QUEUE STOPPED dsm_smoke_failed; exit 1; fi
stage D14_SMOKE_RGB 600 python -B -u scripts/eval_rebuild_v1_d14_intervention.py --arm rgb_ce --seed 42 --smoke
if (( last_rc != 0 )); then record QUEUE STOPPED rgb_smoke_failed; exit 1; fi
for arm in rgb_ce dsm_ce rgb_risk dsm_risk; do
  for seed in 42 17; do
    stage "D14_EVAL_${arm}_${seed}" 600 python -B -u scripts/eval_rebuild_v1_d14_intervention.py --arm "$arm" --seed "$seed"
  done
done
stage D14_SUMMARY 300 python -B -u scripts/summarize_rebuild_v1_d14_intervention.py
record QUEUE FINISHED "failures=$failures"
