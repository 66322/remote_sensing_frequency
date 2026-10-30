#!/usr/bin/env bash
set -euo pipefail

PROJECT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
RECORD="$PROJECT/records/rebuild_v1_d20_vaihingen_failure_inputs_20260928"
COMPACT="$PROJECT/records/rebuild_v1_d20_vaihingen_failure_inputs_compact_20260928"
SOURCE=scripts/audit_rebuild_v1_d20_vaihingen_failure_inputs.py
RUNNER=scripts/run_rebuild_v1_d20_vaihingen_failure_inputs_audit.sh
cd "$PROJECT"
mkdir -p "$RECORD" "$COMPACT"
exec 9>"$RECORD/audit.lock"
flock -n 9 || { echo 'D20 failure-input audit already running' >&2; exit 1; }
if [ -e "$RECORD/audit.json" ]; then
  echo 'Audit output already exists; inspect it before any rerun' >&2
  exit 1
fi

finish() {
  code=$?
  if [ "$code" -eq 0 ]; then state=COMPLETE; else state=FAILED; fi
  printf '%s\tAUDIT\t%s\t%s\n' "$(date --iso-8601=seconds)" "$state" "$code" >> "$RECORD/status.tsv"
  for file in status.tsv run_context.txt audit.json tiles.tsv; do
    if [ -f "$RECORD/$file" ]; then cp "$RECORD/$file" "$COMPACT/$file"; fi
  done
}
trap finish EXIT
printf '%s\tAUDIT\tSTART\t%s\n' "$(date --iso-8601=seconds)" "$(git rev-parse HEAD)" >> "$RECORD/status.tsv"

SOURCES=(
  "$SOURCE"
  "$RUNNER"
  configs/rebuild_v1/d20_vaihingen_formal_seed42_20260928.json
  records/rebuild_v1_d20_vaihingen_seed42_compact_20260928/decision.json
  records/rebuild_v1_d20_vaihingen_seed42_compact_20260928/input_manifest.json
  records/rebuild_v1_d20_vaihingen_seed42_compact_20260928/offline_audit.json
)
git diff --exit-code HEAD -- "${SOURCES[@]}" >/dev/null
git diff --cached --exit-code -- "${SOURCES[@]}" >/dev/null
{
  date --iso-8601=seconds
  printf 'HEAD=%s\n' "$(git rev-parse HEAD)"
  printf 'BRANCH=%s\n' "$(git branch --show-current)"
  sha256sum "${SOURCES[@]}"
} > "$RECORD/run_context.txt"

python - <<'PY'
import json
from pathlib import Path
root = Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro')
archive = root / 'records/rebuild_v1_d20_vaihingen_seed42_compact_20260928'
decision = json.loads((archive / 'decision.json').read_text())
offline = json.loads((archive / 'offline_audit.json').read_text())
if decision['status'] != 'COMPLETE' or decision['passed'] is not False:
    raise SystemExit('frozen seed42 decision is not the completed failed gate')
if offline['status'] != 'PASS' or offline['passed'] is not False:
    raise SystemExit('offline audit is not a passed reproduction of the failed gate')
print('PREFLIGHT PASS: archived failed gate and offline audit agree', flush=True)
PY
printf '%s\tPREFLIGHT\tCOMPLETE\tarchived_failed_gate_verified\n' "$(date --iso-8601=seconds)" >> "$RECORD/status.tsv"

CUDA_VISIBLE_DEVICES= python -B -u "$SOURCE" > "$RECORD/source_audit.log" 2>&1 || {
  tail -n 30 "$RECORD/source_audit.log" >&2
  exit 1
}
python - <<'PY'
import json
from pathlib import Path
p=Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d20_vaihingen_failure_inputs_20260928/audit.json')
d=json.loads(p.read_text())
if d['status'] != 'COMPLETE' or len(d['tiles']) != 17 or d['frozen_gate_passed'] is not False:
    raise SystemExit('diagnostic output incomplete or gate changed')
print('status:', d['status'])
print('development tiles:', len(d['tiles']))
print('failure tiles:', d['target_failure_ids'])
print('frozen gate passed:', d['frozen_gate_passed'])
print('table:', p.parent / 'tiles.tsv')
PY
