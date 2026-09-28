#!/usr/bin/env bash
set -euo pipefail

BASE=/home/jovyan/zzx
PROJECT="$BASE/paper_rebuild/08_thesis_full_repro"
RECORD="$PROJECT/records/rebuild_v1_d20_source_acceptance_20260928"
TORRENT="$BASE/datasets/rebuild_v1_d10_dfc19/official_metadata/DFC2019_track1_trainval_v1.0.0.torrent"

cd "$PROJECT"
mkdir -p "$RECORD"

printf '%s\tD20_TRANSFER_PREFLIGHT\tSTART\t%s\n'   "$(date --iso-8601=seconds)" "$(git rev-parse HEAD)" >> "$RECORD/status.tsv"

finish() {
  code=$?
  if [ "$code" -eq 0 ]; then state=COMPLETE; else state=FAILED; fi
  printf '%s\tD20_TRANSFER_PREFLIGHT\t%s\t%s\n'     "$(date --iso-8601=seconds)" "$state" "$code" >> "$RECORD/status.tsv"
}
trap finish EXIT

python -B scripts/audit_rebuild_v1_d20_torrent_route.py   --torrent "$TORRENT"   --out "$RECORD/transfer_route_preflight.json"   2>&1 | tee "$RECORD/transfer_route_preflight.log"

echo
echo "===== compact transfer decision ====="
python - <<'PY'
import json
from pathlib import Path
p = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d20_source_acceptance_20260928/transfer_route_preflight.json")
x = json.loads(p.read_text())
print("status:", x["status"])
print("webseeds:", x["webseed_uris"])
for p in x["tracker_probes"]:
    print("tracker:", p["uri"])
    if "tcp" in p:
        print("  tcp:", p["tcp"].get("ok"), p["tcp"].get("error", ""))
    if "direct_http_no_announce_args" in p:
        q = p["direct_http_no_announce_args"]
        print("  direct_http:", q.get("ok"), q.get("response_first_line", q.get("error", "")))
    if "udp_connect_only" in p:
        q = p["udp_connect_only"]
        print("  udp_connect:", q.get("ok"), q.get("error", ""))
print("clients:", x["commands"])
print("next:", x["next_action"])
PY
