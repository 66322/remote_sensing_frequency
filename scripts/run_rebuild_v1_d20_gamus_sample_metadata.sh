#!/usr/bin/env bash
set -euo pipefail

PROJECT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
RECORD="$PROJECT/records/rebuild_v1_d20_gamus_sample_metadata_20260928"
COMPACT="$PROJECT/records/rebuild_v1_d20_gamus_sample_metadata_compact_20260928"
SOURCE=scripts/audit_rebuild_v1_d20_gamus_sample_metadata.py
RUNNER=scripts/run_rebuild_v1_d20_gamus_sample_metadata.sh

cd "$PROJECT"
mkdir -p "$RECORD" "$COMPACT"
exec 9>"$RECORD/audit.lock"
flock -n 9 || { echo 'GAMUS sample metadata audit is already running' >&2; exit 1; }
if [ -e "$RECORD/audit.json" ]; then
  echo 'GAMUS sample metadata audit already exists; inspect it before rerun' >&2
  exit 1
fi

finish() {
  code=$?
  if [ "$code" -eq 0 ]; then state=COMPLETE; else state=FAILED; fi
  printf '%s\tAUDIT\t%s\t%s\n' "$(date --iso-8601=seconds)" "$state" "$code" >> "$RECORD/status.tsv"
  for file in status.tsv run_context.txt audit.json; do
    if [ -f "$RECORD/$file" ]; then cp "$RECORD/$file" "$COMPACT/$file"; fi
  done
}
trap finish EXIT

printf '%s\tAUDIT\tSTART\t%s\n' "$(date --iso-8601=seconds)" "$(git rev-parse HEAD)" >> "$RECORD/status.tsv"
git diff --exit-code HEAD -- "$SOURCE" "$RUNNER" >/dev/null
git diff --cached --exit-code -- "$SOURCE" "$RUNNER" >/dev/null
{
  date --iso-8601=seconds
  printf 'HEAD=%s\n' "$(git rev-parse HEAD)"
  printf 'BRANCH=%s\n' "$(git branch --show-current)"
  printf 'PYTHON=%s\n' "$(command -v python)"
  python --version
  sha256sum "$SOURCE" "$RUNNER"
} > "$RECORD/run_context.txt"

PYDEPS="$PROJECT/records/rebuild_v1_d20_gamus_source_acceptance_20260928/pydeps"
if ! python -c 'import h5py' >/dev/null 2>&1; then
  if [ ! -f "$PYDEPS/h5py/__init__.py" ]; then
    echo 'Isolated h5py from completed Stage A is missing; stop without modifying the environment' >&2
    exit 1
  fi
  export PYTHONPATH="$PYDEPS${PYTHONPATH:+:$PYTHONPATH}"
fi
CUDA_VISIBLE_DEVICES= python -B -u "$SOURCE" > "$RECORD/audit.log" 2>&1 || {
  tail -n 35 "$RECORD/audit.log" >&2
  exit 1
}
cat "$RECORD/audit.log"
