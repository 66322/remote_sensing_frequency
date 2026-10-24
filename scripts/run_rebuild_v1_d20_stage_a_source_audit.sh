#!/usr/bin/env bash
set -euo pipefail

BASE=/home/jovyan/zzx
PROJECT="$BASE/paper_rebuild/08_thesis_full_repro"
RECORD="$PROJECT/records/rebuild_v1_d20_source_acceptance_20260928"
mkdir -p "$RECORD"
cd "$PROJECT"

{
  echo "===== D20 Stage A source acceptance ====="
  date --iso-8601=seconds
  echo "HEAD=$(git rev-parse HEAD)"
  echo "BRANCH=$(git branch --show-current)"
  echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES-UNSET}"
  echo "This probe is CPU-only and will not retry Google Drive."
} | tee "$RECORD/run_context.txt"

printf '%s\tD20_STAGE_A\tSTART\t%s\n'   "$(date --iso-8601=seconds)" "$(git rev-parse HEAD)" >> "$RECORD/status.tsv"

finish() {
  code=$?
  if [ "$code" -eq 0 ]; then state=COMPLETE; else state=FAILED; fi
  printf '%s\tD20_STAGE_A\t%s\t%s\n'     "$(date --iso-8601=seconds)" "$state" "$code" >> "$RECORD/status.tsv"
}
trap finish EXIT

python -B scripts/audit_rebuild_v1_d20_dfc19_source.py   --data-root "$BASE/datasets/rebuild_v1_d10_dfc19"   --record-dir "$RECORD"   2>&1 | tee "$RECORD/source_audit.log"

echo
echo "===== compact decision ====="
python - <<'PY'
import json
from pathlib import Path
p = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d20_source_acceptance_20260928/source_audit.json")
x = json.loads(p.read_text())
print("status:", x["status"])
print("decision:", x["decision"])
print("local triplets:", x["local_inventory"]["matched_triplet_count"])
print("city tiles:", x["local_inventory"]["city_tile_counts"])
print("torrent metadata:", x["torrent_download"].get("ok"))
print("DataPort probe:", x["network_probes"]["dataport"])
print("next:", x["next_action"])
PY
