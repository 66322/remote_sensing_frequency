#!/usr/bin/env bash
set -euo pipefail

BASE=/home/jovyan/zzx
PROJECT="$BASE/paper_rebuild/08_thesis_full_repro"
RECORD="$PROJECT/records/rebuild_v1_d20_vaihingen_smoke_20260928"
COMPACT="$PROJECT/records/rebuild_v1_d20_vaihingen_smoke_compact_20260928"
cd "$PROJECT"
mkdir -p "$RECORD" "$COMPACT"

printf '%s\tQUEUE\tSTART\t%s\n' "$(date --iso-8601=seconds)" "$(git rev-parse HEAD)" >> "$RECORD/status.tsv"
finish() {
  code=$?
  if [ "$code" -eq 0 ]; then state=COMPLETE; else state=FAILED; fi
  printf '%s\tQUEUE\t%s\t%s\n' "$(date --iso-8601=seconds)" "$state" "$code" >> "$RECORD/status.tsv"
  cp "$RECORD/status.tsv" "$COMPACT/status.tsv"
  if [ -f "$RECORD/run_context.txt" ]; then cp "$RECORD/run_context.txt" "$COMPACT/run_context.txt"; fi
  for arm in P0 P1 P2; do
    if [ -f "$RECORD/$arm/summary.json" ]; then
      cp "$RECORD/$arm/summary.json" "$COMPACT/${arm}_summary.json"
    fi
  done
}
trap finish EXIT

SOURCES=(
  configs/rebuild_v1/d20_vaihingen_development_smoke_20260928.json
  scripts/d20_vaihingen_smoke_arm.py
  scripts/run_rebuild_v1_d20_vaihingen_smoke.sh
)
git diff --exit-code HEAD -- "${SOURCES[@]}" > /dev/null
{
  date --iso-8601=seconds
  printf 'HEAD=%s\n' "$(git rev-parse HEAD)"
  printf 'BRANCH=%s\n' "$(git branch --show-current)"
  sha256sum "${SOURCES[@]}"
} > "$RECORD/run_context.txt"

PYTHON_FILE="$PROJECT/records/rebuild_v1_d18_d19_queue_20260927/d18_python.txt"
if [ -f "$PYTHON_FILE" ]; then
  D18_PYTHON="$(cat "$PYTHON_FILE")"
else
  CONDA_BASE="$(conda info --base)"
  D18_PYTHON="$CONDA_BASE/envs/d18_dino/bin/python"
fi
if [ ! -x "$D18_PYTHON" ]; then
  echo "D18 Python unavailable: $D18_PYTHON" >&2
  exit 1
fi
printf 'D18_PYTHON=%s\n' "$D18_PYTHON" >> "$RECORD/run_context.txt"

python - <<'PY'
import json
from pathlib import Path
root=Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro')
cfg=json.loads((root/'configs/rebuild_v1/d20_vaihingen_development_smoke_20260928.json').read_text())
audit=json.loads((root/'records/rebuild_v1_d20_vaihingen_content_compact_20260928/audit.json').read_text())
if audit['status']!='CONTENT_SAMPLE_CHECKS_PASS_DEVELOPMENT_ONLY' or audit['ready_development_ids']!=cfg['development_ids']:
    raise SystemExit('D20 Vaihingen content audit does not match frozen development IDs')
data=Path(cfg['data_root']).resolve()
data.relative_to(Path('/home/jovyan/zzx').resolve())
for tile in cfg['train_ids']+cfg['development_ids']:
    gt_dir=cfg['training_label_directory'] if tile in cfg['train_ids'] else cfg['development_label_directory']
    paths=(data/'top'/f'top_mosaic_09cm_area{tile}.tif',
           data/'dsm'/f'dsm_09cm_matching_area{tile}.tif',
           data/gt_dir/f'top_mosaic_09cm_area{tile}.tif')
    if not all(p.is_file() for p in paths):
        raise SystemExit(f'Missing Vaihingen tile {tile}: {[str(p) for p in paths if not p.is_file()]}')
assert not set(cfg['train_ids']) & set(cfg['development_ids'])
assert not (set(cfg['train_ids'])|set(cfg['development_ids'])) & set(cfg['historically_used_evaluation_ids_excluded'])
print('D20 Vaihingen split/file preflight PASS')
PY

if ! nvidia-smi --query-gpu=index --format=csv,noheader | grep -qx '0'; then
  echo 'Physical GPU0 missing' >&2; exit 1
fi
if ! nvidia-smi --query-gpu=index --format=csv,noheader | grep -qx '1'; then
  echo 'Physical GPU1 missing' >&2; exit 1
fi
printf '%s\tPREFLIGHT\tCOMPLETE\tCPU data/config + physical GPU0/1\n' "$(date --iso-8601=seconds)" >> "$RECORD/status.tsv"

run_arm() {
  gpu="$1"
  arm="$2"
  printf '%s\tSMOKE_%s\tSTART\tgpu=%s\n' "$(date --iso-8601=seconds)" "$arm" "$gpu" >> "$RECORD/status.tsv"
  if CUDA_VISIBLE_DEVICES="$gpu" CUBLAS_WORKSPACE_CONFIG=:4096:8 XFORMERS_DISABLED=1 \
      "$D18_PYTHON" -B -u scripts/d20_vaihingen_smoke_arm.py --arm "$arm" \
      > "$RECORD/${arm}.log" 2>&1; then
    printf '%s\tSMOKE_%s\tCOMPLETE\tgpu=%s\n' "$(date --iso-8601=seconds)" "$arm" "$gpu" >> "$RECORD/status.tsv"
  else
    code=$?
    printf '%s\tSMOKE_%s\tFAILED\tcode=%s gpu=%s\n' "$(date --iso-8601=seconds)" "$arm" "$code" "$gpu" >> "$RECORD/status.tsv"
    return "$code"
  fi
}

run_arm 0 P0 & p0=$!
run_arm 1 P1 & p1=$!
ok0=0; ok1=0
if wait "$p0"; then ok0=1; fi
if wait "$p1"; then ok1=1; fi
if [ "$ok0" -ne 1 ] || [ "$ok1" -ne 1 ]; then
  printf '%s\tSMOKE_P2\tBLOCKED\tP0_or_P1_failed\n' "$(date --iso-8601=seconds)" >> "$RECORD/status.tsv"
  exit 1
fi
run_arm 0 P2
printf '%s\tSMOKE_GATE\tCOMPLETE\tall_three_save_reload_eval\n' "$(date --iso-8601=seconds)" >> "$RECORD/status.tsv"
echo 'D20 Vaihingen three-arm one-step smoke complete; compact summaries prepared.'
