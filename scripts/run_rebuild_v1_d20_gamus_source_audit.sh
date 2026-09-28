#!/usr/bin/env bash
set -euo pipefail

PROJECT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
RECORD="$PROJECT/records/rebuild_v1_d20_gamus_source_acceptance_20260928"
COMPACT="$PROJECT/records/rebuild_v1_d20_gamus_source_acceptance_compact_20260928"
SOURCE=scripts/audit_rebuild_v1_d20_gamus_source.py
RUNNER=scripts/run_rebuild_v1_d20_gamus_source_audit.sh
cd "$PROJECT"
mkdir -p "$RECORD" "$COMPACT"
exec 9>"$RECORD/audit.lock"
flock -n 9 || { echo 'D20 GAMUS source audit is already running' >&2; exit 1; }
if [ -e "$RECORD/audit.json" ]; then
  echo 'GAMUS source audit output already exists; inspect it before rerun' >&2
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

python - <<'PY'
import h5py, numpy
from pathlib import Path
root=Path('/home/jovyan/zzx')
assert root.is_dir()
print('PREFLIGHT PASS: CPU dependencies and zzx root', h5py.__version__, numpy.__version__, flush=True)
PY
printf '%s\tPREFLIGHT\tCOMPLETE\tCPU_dependencies_and_zzx_root\n' "$(date --iso-8601=seconds)" >> "$RECORD/status.tsv"
CUDA_VISIBLE_DEVICES= python -B -u "$SOURCE" > "$RECORD/source_audit.log" 2>&1 || {
  tail -n 35 "$RECORD/source_audit.log" >&2
  exit 1
}
python - <<'PY'
import json
from pathlib import Path
p=Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d20_gamus_source_acceptance_20260928/audit.json')
d=json.loads(p.read_text())
assert d['sample_count']==3 and d['metadata_pairing_all_splits']
print('status:',d['status'])
print('pinned revision:',d['revision'])
print('sample cities:',[x['city'] for x in d['samples']])
print('next: review underlying rights, city provenance and spatial split; no GPU training')
PY
