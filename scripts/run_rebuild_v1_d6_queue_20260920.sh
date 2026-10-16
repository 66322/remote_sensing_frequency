#!/usr/bin/env bash
set -uo pipefail
R=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro; O=$R/records/rebuild_v1_d6_queue_20260920
export CUDA_VISIBLE_DEVICES=0 CUBLAS_WORKSPACE_CONFIG=:4096:8; cd "$R"||exit 2; mkdir -p "$O"; exec 9>"$O/lock"; flock -n 9||exit 3
rec(){ printf '%s\t%s\t%s\t%s\n' "$(date -Is)" "$1" "$2" "${3:-}" >>"$O/status.tsv"; }
run(){ n=$1;t=$2;shift 2; python scripts/validate_execution_boundaries.py --torch-check --output "$O/boundary.json" >>"$O/queue.log" 2>&1||exit 90; rec "$n" START; timeout --foreground --signal=TERM --kill-after=60s "$t" "$@" >"$O/$n.log" 2>&1;r=$?; [[ $r == 0 ]]&&rec "$n" COMPLETE 0||rec "$n" FAILED "$r"; return $r; }
rec QUEUE START "$(git rev-parse HEAD)"; run D6_SMOKE 1800 python -u scripts/eval_rebuild_v1_d6_mask_generalization.py --seed 42 --smoke && run D6_SEED42 14400 python -u scripts/eval_rebuild_v1_d6_mask_generalization.py --seed 42; run D6_SEED17 14400 python -u scripts/eval_rebuild_v1_d6_mask_generalization.py --seed 17; rec QUEUE FINISHED 0
