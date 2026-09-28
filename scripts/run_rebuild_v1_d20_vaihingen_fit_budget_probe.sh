#!/usr/bin/env bash
set -euo pipefail

PROJECT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
RECORD="$PROJECT/records/rebuild_v1_d20_vaihingen_fit_budget_probe_20260928"
COMPACT="$PROJECT/records/rebuild_v1_d20_vaihingen_fit_budget_probe_compact_20260928"
cd "$PROJECT"
mkdir -p "$RECORD" "$COMPACT"
printf '%s\tQUEUE\tSTART\t%s\n' "$(date --iso-8601=seconds)" "$(git rev-parse HEAD)" >> "$RECORD/status.tsv"
finish() {
  code=$?
  if [ "$code" -eq 0 ]; then state=COMPLETE; else state=FAILED; fi
  printf '%s\tQUEUE\t%s\t%s\n' "$(date --iso-8601=seconds)" "$state" "$code" >> "$RECORD/status.tsv"
  cp "$RECORD/status.tsv" "$COMPACT/status.tsv"
  if [ -f "$RECORD/run_context.txt" ]; then cp "$RECORD/run_context.txt" "$COMPACT/run_context.txt"; fi
  if [ -f "$RECORD/summary.json" ]; then cp "$RECORD/summary.json" "$COMPACT/summary.json"; fi
}
trap finish EXIT

SOURCES=(
  configs/rebuild_v1/d20_vaihingen_fit_budget_probe_20260928.json
  scripts/d20_vaihingen_fit_budget_probe.py
  scripts/d20_vaihingen_smoke_arm.py
  scripts/run_rebuild_v1_d20_vaihingen_fit_budget_probe.sh
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
if [ ! -x "$D18_PYTHON" ]; then echo "D18 Python unavailable: $D18_PYTHON" >&2; exit 1; fi
printf 'D18_PYTHON=%s\n' "$D18_PYTHON" >> "$RECORD/run_context.txt"

python - <<'PY'
import json
from pathlib import Path
root=Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro')
cfg=json.loads((root/'configs/rebuild_v1/d20_vaihingen_fit_budget_probe_20260928.json').read_text())
smoke=json.loads((root/'configs/rebuild_v1/d20_vaihingen_development_smoke_20260928.json').read_text())
status=(root/'records/rebuild_v1_d20_vaihingen_smoke_compact_20260928/status.tsv').read_text()
if '\tSMOKE_GATE\tCOMPLETE\t' not in status or '\tQUEUE\tCOMPLETE\t0' not in status:
    raise SystemExit('matched three-arm smoke gate not archived as complete')
if cfg['train_ids'] != smoke['train_ids'] or cfg['data_root'] != smoke['data_root']:
    raise SystemExit('fit-budget probe data/split differs from the passed smoke')
data=Path(cfg['data_root']).resolve()
data.relative_to(Path('/home/jovyan/zzx').resolve())
for tile in cfg['train_ids']:
    name=f'top_mosaic_09cm_area{tile}.tif'
    files=(data/'top'/name,data/'dsm'/f'dsm_09cm_matching_area{tile}.tif',
           data/cfg['training_label_directory']/name)
    if not all(path.is_file() for path in files):
        raise SystemExit(f'missing fit tile {tile}')
print('D20 fit-only budget preflight PASS')
PY

if ! nvidia-smi --query-gpu=index --format=csv,noheader | grep -qx '0'; then
  echo 'Physical GPU0 missing' >&2; exit 1
fi
printf '%s\tPREFLIGHT\tCOMPLETE\tfit_only_and_physical_GPU0\n' "$(date --iso-8601=seconds)" >> "$RECORD/status.tsv"
printf '%s\tFIT_P2_20_STEPS\tSTART\tgpu=0\n' "$(date --iso-8601=seconds)" >> "$RECORD/status.tsv"
if CUDA_VISIBLE_DEVICES=0 CUBLAS_WORKSPACE_CONFIG=:4096:8 XFORMERS_DISABLED=1 \
    "$D18_PYTHON" -B -u scripts/d20_vaihingen_fit_budget_probe.py > "$RECORD/fit_p2.log" 2>&1; then
  printf '%s\tFIT_P2_20_STEPS\tCOMPLETE\tgpu=0\n' "$(date --iso-8601=seconds)" >> "$RECORD/status.tsv"
else
  code=$?
  printf '%s\tFIT_P2_20_STEPS\tFAILED\tcode=%s gpu=0\n' "$(date --iso-8601=seconds)" "$code" >> "$RECORD/status.tsv"
  exit "$code"
fi
echo 'D20 fit-only P2 timing probe complete; no development evaluation or formal training started.'
