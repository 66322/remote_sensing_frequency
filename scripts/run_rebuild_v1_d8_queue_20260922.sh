#!/usr/bin/env bash
set -uo pipefail
R=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro; O=$R/records/rebuild_v1_d8_queue_20260922
export CUDA_VISIBLE_DEVICES=0 CUBLAS_WORKSPACE_CONFIG=:4096:8; cd "$R"||exit 2; mkdir -p "$O"; exec 9>"$O/lock"; flock -n 9||exit 3
rec(){ printf '%s\t%s\t%s\t%s\n' "$(date -Is)" "$1" "$2" "${3:-}" >>"$O/status.tsv"; }
run(){ local n=$1 t=$2;shift 2; python scripts/validate_execution_boundaries.py --torch-check --output "$O" >>"$O/queue.log" 2>&1; local p=$?; if [[ $p -ne 0 ]];then rec "$n" FAILED "preflight_$p";return 0;fi; rec "$n" START; timeout --foreground --signal=TERM --kill-after=60s "$t" "$@" >"$O/$n.log" 2>&1; local r=$?; [[ $r -eq 0 ]]&&rec "$n" COMPLETE 0||rec "$n" FAILED "$r"; return 0; }
rec QUEUE START "$(git rev-parse HEAD)"
run D8_C_SMOKE 1800 python -u scripts/train_rebuild_v1_d8_sampling.py --config configs/rebuild_v1/d8_c_random_ce_4k.json --smoke-steps 20 --smoke-eval --run-tag queue20260922
for arm in C A S; do
 case $arm in C) cfg=d8_c_random_ce_4k.json; mode=random_ce;; A) cfg=d8_a_any_car_4k.json; mode=any_car;; S) cfg=d8_s_small_car_4k.json; mode=small_car;; esac
 run D8_${arm}_TRAIN 14400 python -u scripts/train_rebuild_v1_d8_sampling.py --config configs/rebuild_v1/$cfg --run-tag queue20260922
 run D8_${arm}_EVAL 3600 python -u scripts/eval_rebuild_v1_d8_sampling.py --config configs/rebuild_v1/$cfg --run-dir runs/rebuild_v1/D8_${mode}_seed42_sched4000_stop4000_queue20260922 --out records/rebuild_v1_d8_${mode}_eval_20260922
done
run D8_SUMMARY 600 python -u scripts/summarize_rebuild_v1_d8.py
failures=$(awk -F '\t' '$3=="FAILED"{n++}END{print n+0}' "$O/status.tsv"); rec QUEUE FINISHED "failures=$failures"; exit 0
