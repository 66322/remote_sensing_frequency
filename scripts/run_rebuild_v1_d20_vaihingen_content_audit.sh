#!/usr/bin/env bash
set -euo pipefail

PROJECT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
RECORD="$PROJECT/records/rebuild_v1_d20_vaihingen_content_20260928"
COMPACT="$PROJECT/records/rebuild_v1_d20_vaihingen_content_compact_20260928"

cd "$PROJECT"
mkdir -p "$RECORD" "$COMPACT"
{
  date --iso-8601=seconds
  printf 'HEAD=%s\n' "$(git rev-parse HEAD)"
  printf 'BRANCH=%s\n' "$(git branch --show-current)"
  printf 'PYTHON=%s\n' "$(command -v python)"
  printf 'CUDA_VISIBLE_DEVICES=%s\n' "${CUDA_VISIBLE_DEVICES-UNSET}"
} > "$RECORD/run_context.txt"

printf '%s\tD20_VAI_CONTENT_AUDIT\tSTART\t%s\n' \
  "$(date --iso-8601=seconds)" "$(git rev-parse HEAD)" >> "$RECORD/status.tsv"

finish() {
  code=$?
  if [ "$code" -eq 0 ]; then state=COMPLETE; else state=REVIEW_REQUIRED; fi
  printf '%s\tD20_VAI_CONTENT_AUDIT\t%s\t%s\n' \
    "$(date --iso-8601=seconds)" "$state" "$code" >> "$RECORD/status.tsv"
  for name in run_context.txt status.tsv audit.json tiles.tsv; do
    if [ -f "$RECORD/$name" ]; then cp "$RECORD/$name" "$COMPACT/$name"; fi
  done
}
trap finish EXIT

python -B scripts/audit_rebuild_v1_d20_vaihingen_content.py \
  --output-dir "$RECORD" 2>&1 | tee "$RECORD/audit.log"

echo '===== D20 Vaihingen compact decision ====='
python - <<'PY'
import json
from pathlib import Path
p = Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d20_vaihingen_content_20260928/audit.json')
x = json.loads(p.read_text())
print('status:', x['status'])
print('ready development IDs:', x['ready_development_ids'])
print('review IDs:', [r['id'] for r in x['tiles'] if r['id'] not in x['ready_development_ids']])
print('record:', p)
PY
