#!/usr/bin/env bash
set -uo pipefail
R=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
O=$R/records/rebuild_v1_d13_residual_queue_20260924
B=$R/records/rebuild_v1_d13_residual_20260924
export CUDA_VISIBLE_DEVICES=0 CUDA_DEVICE_ORDER=PCI_BUS_ID CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
export TMPDIR=/home/jovyan/zzx/tmp
cd "$R" || exit 2
mkdir -p "$O" "$B" "$TMPDIR"
exec 9>"$O/lock"
flock -n 9 || exit 3
if [[ -e "$O/status.tsv" ]]; then
  echo "D13 queue already exists; refusing to overwrite"
  exit 4
fi
start=$(date +%s)
deadline=$((start+86400))
failures=0
last_rc=0
record() { printf '%s\t%s\t%s\t%s\n' "$(date -Is)" "$1" "$2" "${3:-}" >> "$O/status.tsv"; }
stage() {
  local name=$1 requested=$2 reserve=$3
  shift 3
  local remaining=$((deadline-$(date +%s)-reserve))
  if (( remaining <= 0 )); then record "$name" SKIPPED time_budget; last_rc=124; return 0; fi
  local limit=$requested
  if (( remaining < limit )); then limit=$remaining; fi
  record "$name" START
  timeout --foreground --signal=TERM --kill-after=60s "${limit}s" "$@" > "$O/$name.log" 2>&1
  last_rc=$?
  if (( last_rc == 0 )); then
    record "$name" COMPLETE 0
  else
    record "$name" FAILED "$last_rc"
    failures=$((failures+1))
  fi
  return 0
}
record QUEUE START "$(git rev-parse HEAD)"
if ! git diff --quiet HEAD -- configs/rebuild_v1/d13_residual_overnight_20260924.json scripts/d13_residual.py scripts/train_rebuild_v1_d13_residual.py scripts/eval_rebuild_v1_d13_residual.py scripts/summarize_rebuild_v1_d13_residual.py scripts/train_rebuild_v1_r01_optical_only.py scripts/train_rebuild_v1_r02_budget_pilot.py model/rebuild_v1_optical_only.py; then
  record QUEUE STOPPED tracked_source_differs_from_commit
  exit 1
fi
stage D13_BOUNDARIES 300 900 python -B scripts/validate_execution_boundaries.py --output "$O" --output "$B" --torch-check
if (( last_rc != 0 )); then record QUEUE STOPPED boundaries_failed; exit 1; fi
stage D13_NUMERICS 600 900 python -B -m unittest discover -s tests -p test_d13_residual.py -v
if (( last_rc != 0 )); then record QUEUE STOPPED numerics_failed; exit 1; fi
stage D13_SMOKE 1800 900 python -B -u scripts/train_rebuild_v1_d13_residual.py --arm dsm_risk --seed 42 --smoke-steps 2
if (( last_rc != 0 )); then record QUEUE STOPPED smoke_failed; exit 1; fi
stage D13_EVAL_SMOKE 1800 900 python -B -u scripts/eval_rebuild_v1_d13_residual.py --arm dsm_risk --seed 42 --smoke
if (( last_rc != 0 )); then record QUEUE STOPPED evaluation_smoke_failed; exit 1; fi

for arm in rgb_ce dsm_ce rgb_risk dsm_risk; do
  for seed in 42 17; do
    stage "D13_TRAIN_${arm}_${seed}" 5400 900 python -B -u scripts/train_rebuild_v1_d13_residual.py --arm "$arm" --seed "$seed"
    if (( last_rc == 0 )); then
      stage "D13_EVAL_${arm}_${seed}" 3600 900 python -B -u scripts/eval_rebuild_v1_d13_residual.py --arm "$arm" --seed "$seed"
    else
      record "D13_EVAL_${arm}_${seed}" SKIPPED incomplete_train
    fi
  done
done
stage D13_STAGE1_SUMMARY 600 0 python -B -u scripts/summarize_rebuild_v1_d13_residual.py --stage stage1

stage1_ok=false
if [[ -f "$B/stage1_decision.json" ]]; then
  stage1_ok=$(python -B -c 'import json,sys; print(str(json.load(open(sys.argv[1]))["stage1_pass"]).lower())' "$B/stage1_decision.json")
fi
if [[ "$stage1_ok" == true ]]; then
  for arm in dsm_capacity dsm_semantic dsm_frequency dsm_semantic_frequency; do
    # Start optional work only with room for both seeds, both evaluations,
    # and the final three-hour reservation. Do not leave a planned arm half-paired.
    if (( deadline-$(date +%s)-10800 < 2*(5400+3600) )); then
      record "D13_STAGE2_${arm}" SKIPPED insufficient_pair_budget
      continue
    fi
    for seed in 42 17; do
      stage "D13_TRAIN_${arm}_${seed}" 5400 10800 python -B -u scripts/train_rebuild_v1_d13_residual.py --arm "$arm" --seed "$seed"
      if (( last_rc == 0 )); then
        stage "D13_EVAL_${arm}_${seed}" 3600 10800 python -B -u scripts/eval_rebuild_v1_d13_residual.py --arm "$arm" --seed "$seed"
      else
        record "D13_EVAL_${arm}_${seed}" SKIPPED incomplete_train
      fi
    done
  done
else
  record D13_STAGE2 SKIPPED stage1_not_passed_or_incomplete
fi
stage D13_FINAL_SUMMARY 600 0 python -B -u scripts/summarize_rebuild_v1_d13_residual.py --stage final
record QUEUE FINISHED "failures=$failures"
exit 0
