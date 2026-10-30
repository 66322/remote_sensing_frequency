#!/usr/bin/env bash
set -uo pipefail
R=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
O=$R/records/rebuild_v1_d12_night_queue_20260923
B=$R/records/rebuild_v1_d12_night_20260923
export CUDA_VISIBLE_DEVICES=0 CUDA_DEVICE_ORDER=PCI_BUS_ID CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
export TMPDIR=/home/jovyan/zzx/tmp
cd "$R" || exit 2
mkdir -p "$O" "$TMPDIR"
exec 9>"$O/lock"
flock -n 9 || exit 3
if [[ -e "$O/status.tsv" ]]; then
  echo "D12 queue exists; refusing to overwrite"
  exit 4
fi
start=$(date +%s)
deadline=$((start+8*3600))
failures=0
record() { printf '%s\t%s\t%s\t%s\n' "$(date -Is)" "$1" "$2" "${3:-}" >> "$O/status.tsv"; }
stage() {
  local name=$1 requested=$2 reserve=$3
  shift 3
  local remaining=$((deadline-$(date +%s)-reserve))
  if (( remaining <= 0 )); then record "$name" SKIPPED budget; return 0; fi
  local limit=$requested
  if (( remaining < limit )); then limit=$remaining; fi
  record "$name" START
  python -B scripts/validate_execution_boundaries.py --output "$O" --output "$B" --torch-check >> "$O/queue.log" 2>&1
  local rc=$?
  if (( rc == 0 )); then
    timeout --foreground --signal=TERM --kill-after=60s "${limit}s" "$@" > "$O/$name.log" 2>&1
    rc=$?
  fi
  if (( rc == 0 )); then record "$name" COMPLETE 0
  else record "$name" FAILED "$rc"; failures=$((failures+1)); fi
  return 0
}
record QUEUE START "$(git rev-parse HEAD)"
stage D12_NUMERICS 600 0 python -B -m unittest discover -s tests -p test_d12_night.py -v
if ! tail -n 1 "$O/status.tsv" | grep -q $'D12_NUMERICS\tCOMPLETE\t0'; then
  record QUEUE STOPPED numerics_failed
  exit 1
fi
stage D12_SMOKE 3600 0 python -B -u scripts/export_rebuild_v1_d12_semantic.py --seed 42 --tile 6_7 --condition clean --smoke
if ! tail -n 1 "$O/status.tsv" | grep -q $'D12_SMOKE\tCOMPLETE\t0'; then
  record QUEUE STOPPED smoke_failed
  exit 1
fi
# Clean always precedes other conditions, allowing reuse of RGB features.
for seed in 42 17; do
  for tile in 6_7 6_8 6_9 7_7 7_8 7_9 6_10 7_10 4_11 7_11; do
    for condition in clean dsm_blur5 dsm_noise_std010; do
      stage "D12_EXPORT_${seed}_${tile}_${condition}" 3600 0 \
        python -B -u scripts/export_rebuild_v1_d12_semantic.py --seed "$seed" --tile "$tile" --condition "$condition"
    done
  done
  for tile in 3_11 5_10; do
    for condition in clean dsm_blur5 dsm_noise_std010 roll4 roll16 roll32 dsm_zero; do
      stage "D12_VAL_FEATURE_${seed}_${tile}_${condition}" 3600 0 \
        python -B -u scripts/export_rebuild_v1_d12_semantic.py --seed "$seed" --tile "$tile" --condition "$condition"
    done
  done
done
# Reserve two hours for conditional full-resolution confirmation.
for model in E Ecap ES EF ESF; do
  for seed in 42 17; do
    stage "D12_FIT_${seed}_${model}" 5400 7200 \
      python -B -u scripts/run_rebuild_v1_d12_probe.py --seed "$seed" --model "$model"
  done
done
for model in ESF_shuffleS ESF_shuffleF; do
  for seed in 42 17; do
    stage "D12_FIT_${seed}_${model}" 5400 7200 \
      python -B -u scripts/run_rebuild_v1_d12_probe.py --seed "$seed" --model "$model"
  done
done
stage D12_SUMMARY 600 0 python -B -u scripts/summarize_rebuild_v1_d12_night.py
if [[ -f "$B/decision.json" ]]; then
  mapfile -t selected < <(python -B -c 'import json,sys;sys.stdout.write("".join(x+"\n" for x in json.load(open(sys.argv[1]))["full_resolution_candidates"]))' "$B/decision.json")
  if (( ${#selected[@]} > 0 )); then
    for seed in 42 17; do
      for condition in clean dsm_blur5 dsm_noise_std010 roll4 roll16 roll32 dsm_zero; do
        stage "D12_FULL_${seed}_${condition}" 3600 0 \
          python -B -u scripts/eval_rebuild_v1_d12_full.py --seed "$seed" --condition "$condition"
      done
    done
  else
    record D12_FULL SKIPPED no_candidate
  fi
  stage D12_FULL_SUMMARY 600 0 python -B -u scripts/summarize_rebuild_v1_d12_full.py
else
  record D12_FULL SKIPPED no_decision
fi
record QUEUE FINISHED "failures=$failures"
exit 0
