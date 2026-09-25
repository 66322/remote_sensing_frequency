#!/usr/bin/env bash
set -uo pipefail
R=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
O=$R/records/rebuild_v1_d15_capability_queue_20260926
B=$R/records/rebuild_v1_d15_capability_20260926
export CUDA_DEVICE_ORDER=PCI_BUS_ID CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
export TMPDIR=/home/jovyan/zzx/tmp
cd "$R" || exit 2
mkdir -p "$O" "$B" "$TMPDIR"
exec 9>"$O/lock"
flock -n 9 || exit 3
record() { printf '%s\t%s\t%s\t%s\n' "$(date -Is)" "$1" "$2" "${3:-}" >> "$O/status.tsv"; }
if ! git diff --quiet HEAD -- configs/rebuild_v1/d15_capability_20260926.json scripts/d15_capability.py scripts/train_rebuild_v1_d15_dsm_only.py scripts/eval_rebuild_v1_d15_capability.py scripts/summarize_rebuild_v1_d15_capability.py scripts/train_rebuild_v1_r01_optical_only.py scripts/train_rebuild_v1_r02_budget_pilot.py; then
  record QUEUE STOPPED tracked_source_differs_from_commit
  exit 1
fi
record QUEUE START "$(git rev-parse HEAD)"
if ! python -B -m unittest discover -s tests -p test_d15_capability.py -v > "$O/preflight.log" 2>&1; then
  record PREFLIGHT FAILED test
  exit 1
fi
record PREFLIGHT COMPLETE 0
if ! nvidia-smi --query-gpu=index --format=csv,noheader | tr -d ' ' | grep -qx 0 || ! nvidia-smi --query-gpu=index --format=csv,noheader | tr -d ' ' | grep -qx 1; then
  record QUEUE STOPPED physical_gpu_0_or_1_missing
  exit 1
fi
valid_summary() {
  python - "$1" "$2" "$3" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); kind=sys.argv[2]; seed=int(sys.argv[3])
if not p.is_file(): sys.exit(1)
d=json.loads(p.read_text())
if d.get('seed') != seed or d.get('test6_loaded') is not False: sys.exit(1)
if kind == 'smoke':
    if d.get('smoke') is not True: sys.exit(1)
elif d.get('smoke'): sys.exit(1)
if kind == 'train':
    if d.get('experiment') != 'D15_DSM_ONLY' or d.get('global_step') != 16000: sys.exit(1)
elif kind != 'smoke':
    if d.get('model') != kind or len(d.get('conditions',{})) != 6: sys.exit(1)
PY
}
stage() {
  local gpu=$1 name=$2 summary=$3 kind=$4 seed=$5
  shift 5
  if valid_summary "$summary" "$kind" "$seed"; then
    record "$name" REUSED validated_summary
    return 0
  fi
  record "$name" START "gpu=$gpu"
  CUDA_VISIBLE_DEVICES="$gpu" python -B -u "$@" > "$O/$name.log" 2>&1
  local rc=$?
  if (( rc == 0 )) && valid_summary "$summary" "$kind" "$seed"; then
    record "$name" COMPLETE 0
    return 0
  fi
  record "$name" FAILED "$rc"
  return 1
}
train_dsm() {
  local gpu=$1 seed=$2
  local output=$R/runs/rebuild_v1/D15_dsm_only_seed${seed}_sched16000_stop16000
  if [[ -e "$output/last_train_state.pth" && ! -e "$output/summary.json" ]]; then
    stage "$gpu" "TRAIN_DSM_${seed}" "$output/summary.json" train "$seed" \
      scripts/train_rebuild_v1_d15_dsm_only.py --seed "$seed" --resume
  else
    stage "$gpu" "TRAIN_DSM_${seed}" "$output/summary.json" train "$seed" \
      scripts/train_rebuild_v1_d15_dsm_only.py --seed "$seed"
  fi
}
eval_model() {
  local gpu=$1 model=$2 seed=$3
  stage "$gpu" "EVAL_${model}_${seed}" "$B/${model}_seed${seed}/summary.json" "$model" "$seed" \
    scripts/eval_rebuild_v1_d15_capability.py --model "$model" --seed "$seed"
}
worker0() {
  export CUDA_VISIBLE_DEVICES=0
  if ! stage 0 SMOKE_TRAIN "$R/runs/rebuild_v1/D15_dsm_only_seed42_sched16000_stop16000_smoke/summary.json" smoke 42 \
    scripts/train_rebuild_v1_d15_dsm_only.py --seed 42 --smoke-steps 1; then return 1; fi
  train_dsm 0 42 || return 1
  eval_model 0 D15_DSM_ONLY 42 || return 1
  return 0
}
worker1() {
  export CUDA_VISIBLE_DEVICES=1
  if ! stage 1 SMOKE_EVAL "$B/smoke_R01_seed42/summary.json" smoke 42 \
    scripts/eval_rebuild_v1_d15_capability.py --model R01 --seed 42 --smoke; then return 1; fi
  train_dsm 1 17 || return 1
  eval_model 1 D15_DSM_ONLY 17 || return 1
  for seed in 42 17; do
    for model in R01 R05 C-OO-QD; do
      eval_model 1 "$model" "$seed" || return 1
    done
  done
  return 0
}
worker0 & p0=$!
worker1 & p1=$!
wait "$p0"; rc0=$?
wait "$p1"; rc1=$?
if python -B -u scripts/summarize_rebuild_v1_d15_capability.py > "$O/summary.log" 2>&1; then
  record SUMMARY COMPLETE 0
else
  record SUMMARY FAILED "$?"
fi
record QUEUE FINISHED "worker0=$rc0 worker1=$rc1"
if (( rc0 != 0 || rc1 != 0 )); then exit 1; fi
