#!/usr/bin/env bash
set -uo pipefail
ROOT="/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
REC="$ROOT/records/rebuild_v1_d5_queue_20260920"
export CUDA_VISIBLE_DEVICES=0 CUBLAS_WORKSPACE_CONFIG=:4096:8
cd "$ROOT" || exit 2; mkdir -p "$REC"; exec 9>"$REC/queue.lock"; flock -n 9 || exit 3
stamp(){ date -Is; }; record(){ printf '%s\t%s\t%s\t%s\n' "$(stamp)" "$1" "$2" "${3:-}" >> "$REC/status.tsv"; }
check(){ [[ "$PWD" == "$ROOT" && "$ROOT" == /home/jovyan/zzx/* && "$CUDA_VISIBLE_DEVICES" == 0 ]] && python scripts/validate_execution_boundaries.py --torch-check --output "$REC/boundary_latest.json" >>"$REC/queue.log" 2>&1; }
run(){ local n="$1" t="$2"; shift 2; check || exit 90; record "$n" START; timeout --foreground --signal=TERM --kill-after=60s "$t" "$@" >"$REC/$n.log" 2>&1; local r=$?; if [[ $r == 0 ]]; then record "$n" COMPLETE 0; else record "$n" FAILED "$r"; fi; return "$r"; }
record QUEUE START "$(git rev-parse HEAD)"
if run D5_SEED42_SMOKE 1800 python -u scripts/eval_rebuild_v1_d5_confidence_routing.py --seed 42 --smoke; then
  run D5_SEED42 14400 python -u scripts/eval_rebuild_v1_d5_confidence_routing.py --seed 42
else record D5_SEED42 SKIPPED_DEPENDENCY D5_SEED42_SMOKE; fi
run D5_SEED17 14400 python -u scripts/eval_rebuild_v1_d5_confidence_routing.py --seed 17
run D5_SUMMARY 600 python -u scripts/summarize_rebuild_v1_d5_confidence_routing.py
record QUEUE FINISHED 0
