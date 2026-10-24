#!/usr/bin/env bash
set -euo pipefail

BASE=/home/jovyan/zzx
PROJECT="$BASE/paper_rebuild/08_thesis_full_repro"
DEPS="$BASE/tools/rebuild_v1_d10_gdown"
RECORD="$PROJECT/records/rebuild_v1_d10_dfc19_acquire_20260923"
export CUDA_VISIBLE_DEVICES=0
export PIP_CACHE_DIR="$BASE/cache/pip_d10"
export TMPDIR="$BASE/tmp/d10_dfc19"
mkdir -p "$DEPS" "$RECORD" "$PIP_CACHE_DIR" "$TMPDIR"
cd "$PROJECT"

printf '%s\tACQUIRE\tSTART\t%s\n' "$(date --iso-8601=seconds)" "$(git rev-parse HEAD)" >> "$RECORD/status.tsv"
finish() {
    code=$?
    if [ "$code" -eq 0 ]; then state=COMPLETE; else state=FAILED; fi
    printf '%s\tACQUIRE\t%s\t%s\n' "$(date --iso-8601=seconds)" \
        "$state" "$code" >> "$RECORD/status.tsv"
}
trap finish EXIT
if ! PYTHONPATH="$DEPS${PYTHONPATH:+:$PYTHONPATH}" python -B -c 'import gdown' >/dev/null 2>&1; then
    python -m pip install --disable-pip-version-check --target "$DEPS" 'gdown==4.7.3' \
        > "$RECORD/dependency_install.log" 2>&1
fi
PYTHONPATH="$DEPS${PYTHONPATH:+:$PYTHONPATH}" python -B \
    scripts/acquire_rebuild_v1_d10_dfc19.py --download \
    > "$RECORD/acquire.log" 2>&1
