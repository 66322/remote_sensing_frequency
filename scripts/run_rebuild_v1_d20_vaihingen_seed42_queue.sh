#!/usr/bin/env bash
set -euo pipefail

PROJECT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
RECORD="$PROJECT/records/rebuild_v1_d20_vaihingen_seed42_20260928"
COMPACT="$PROJECT/records/rebuild_v1_d20_vaihingen_seed42_compact_20260928"
cd "$PROJECT"
mkdir -p "$RECORD/queue" "$COMPACT"
exec 9>"$RECORD/queue.lock"
if ! flock -n 9; then
  echo 'D20 Vaihingen seed42 queue is already running' >&2
  exit 1
fi
printf '%s\tQUEUE\tSTART\t%s\n' "$(date --iso-8601=seconds)" "$(git rev-parse HEAD)" >> "$RECORD/status.tsv"
finish() {
  code=$?
  if [ "$code" -eq 0 ]; then state=COMPLETE; else state=FAILED; fi
  printf '%s\tQUEUE\t%s\t%s\n' "$(date --iso-8601=seconds)" "$state" "$code" >> "$RECORD/status.tsv"
  cp "$RECORD/status.tsv" "$COMPACT/status.tsv"
  for file in run_context.txt input_manifest.json decision.json; do
    if [ -f "$RECORD/$file" ]; then cp "$RECORD/$file" "$COMPACT/$file"; fi
  done
  for arm in P0 P1 P2; do
    train="$PROJECT/runs/rebuild_v1/D20_VAI_${arm}_seed42_8000_20260928/summary.json"
    evalfile="$RECORD/$arm/summary.json"
    if [ -f "$train" ]; then cp "$train" "$COMPACT/${arm}_train_summary.json"; fi
    if [ -f "$evalfile" ]; then cp "$evalfile" "$COMPACT/${arm}_eval_summary.json"; fi
  done
}
trap finish EXIT

SOURCES=(
  configs/rebuild_v1/d20_vaihingen_formal_seed42_20260928.json
  scripts/d20_vaihingen_formal.py
  scripts/d20_vaihingen_decide.py
  scripts/d20_vaihingen_smoke_arm.py
  scripts/run_rebuild_v1_d20_vaihingen_seed42_queue.sh
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
import hashlib
import json
from pathlib import Path
import shutil

root=Path('/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro')
if shutil.disk_usage(root).free < 8 * 1024**3:
    raise SystemExit('Less than 8 GiB free in project filesystem; preserve full prediction evidence')
cfg=json.loads((root/'configs/rebuild_v1/d20_vaihingen_formal_seed42_20260928.json').read_text())
smoke=json.loads((root/'configs/rebuild_v1/d20_vaihingen_development_smoke_20260928.json').read_text())
probe=json.loads((root/'records/rebuild_v1_d20_vaihingen_fit_budget_probe_compact_20260928/summary.json').read_text())
audit=json.loads((root/'records/rebuild_v1_d20_vaihingen_content_compact_20260928/audit.json').read_text())
if cfg['train_ids'] != smoke['train_ids'] or cfg['development_ids'] != smoke['development_ids']:
    raise SystemExit('formal split differs from passed smoke')
if cfg['development_ids'] != audit['ready_development_ids'] or audit['status'] != 'CONTENT_SAMPLE_CHECKS_PASS_DEVELOPMENT_ONLY':
    raise SystemExit('formal dev IDs differ from content audit')
if probe['status'] != 'COMPLETE' or probe['train_tiles_loaded'] != len(cfg['train_ids']) or not probe['fit_only']:
    raise SystemExit('fit-only budget probe not complete')
if cfg['train_steps'] != 8000 or cfg['micro_batch']*cfg['accum_steps'] != 16 or cfg['evaluation_stride'] != cfg['patch']:
    raise SystemExit('formal budget/tiling mismatch')
if cfg['test6_loaded'] or cfg['independent_final_loaded'] or cfg['seed17_auto_launch']:
    raise SystemExit('sealed data / seed17 policy mismatch')
data=Path(cfg['data_root']).resolve()
data.relative_to(Path('/home/jovyan/zzx').resolve())
files={}
for tile in cfg['train_ids']+cfg['development_ids']:
    label_dir=cfg['training_label_directory'] if tile in cfg['train_ids'] else cfg['development_label_directory']
    name=f'top_mosaic_09cm_area{tile}.tif'
    paths=(data/'top'/name,data/'dsm'/f'dsm_09cm_matching_area{tile}.tif',data/label_dir/name)
    for path in paths:
        if not path.is_file():
            raise SystemExit(f'missing D20 input {path}')
        digest=hashlib.sha256()
        with path.open('rb') as handle:
            for block in iter(lambda: handle.read(8*1024*1024), b''):
                digest.update(block)
        files[str(path)]={'size':path.stat().st_size,'sha256':digest.hexdigest()}
manifest={'schema_version':'1.0','data_root':str(data),'files':files,
          'train_ids':cfg['train_ids'],'development_ids':cfg['development_ids']}
destination=root/'records/rebuild_v1_d20_vaihingen_seed42_20260928/input_manifest.json'
content=json.dumps(manifest,sort_keys=True,indent=2,ensure_ascii=False)+'\n'
if destination.exists() and destination.read_text()!=content:
    raise SystemExit('D20 input content changed since previous formal attempt')
destination.write_text(content)
print(f'D20 matched formal preflight PASS: {len(files)} exact input hashes')
PY

for gpu in 0 1; do
  if ! nvidia-smi --query-gpu=index --format=csv,noheader | grep -qx "$gpu"; then
    echo "Physical GPU$gpu missing" >&2; exit 1
  fi
done
printf '%s\tPREFLIGHT\tCOMPLETE\tinputs_hashed_GPU0+1\n' "$(date --iso-8601=seconds)" >> "$RECORD/status.tsv"

run_arm() {
  gpu="$1"
  arm="$2"
  printf '%s\tTRAIN_%s\tSTART\tgpu=%s\n' "$(date --iso-8601=seconds)" "$arm" "$gpu" >> "$RECORD/status.tsv"
  if CUDA_VISIBLE_DEVICES="$gpu" CUBLAS_WORKSPACE_CONFIG=:4096:8 XFORMERS_DISABLED=1 \
      "$D18_PYTHON" -B -u scripts/d20_vaihingen_formal.py train --arm "$arm" \
      > "$RECORD/queue/${arm}_train.log" 2>&1; then
    printf '%s\tTRAIN_%s\tCOMPLETE\tgpu=%s\n' "$(date --iso-8601=seconds)" "$arm" "$gpu" >> "$RECORD/status.tsv"
  else
    code=$?
    printf '%s\tTRAIN_%s\tFAILED\tcode=%s gpu=%s\n' "$(date --iso-8601=seconds)" "$arm" "$code" "$gpu" >> "$RECORD/status.tsv"
    return "$code"
  fi
  printf '%s\tEVAL_%s\tSTART\tgpu=%s\n' "$(date --iso-8601=seconds)" "$arm" "$gpu" >> "$RECORD/status.tsv"
  if CUDA_VISIBLE_DEVICES="$gpu" CUBLAS_WORKSPACE_CONFIG=:4096:8 XFORMERS_DISABLED=1 \
      "$D18_PYTHON" -B -u scripts/d20_vaihingen_formal.py eval --arm "$arm" \
      > "$RECORD/queue/${arm}_eval.log" 2>&1; then
    printf '%s\tEVAL_%s\tCOMPLETE\tgpu=%s\n' "$(date --iso-8601=seconds)" "$arm" "$gpu" >> "$RECORD/status.tsv"
  else
    code=$?
    printf '%s\tEVAL_%s\tFAILED\tcode=%s gpu=%s\n' "$(date --iso-8601=seconds)" "$arm" "$code" "$gpu" >> "$RECORD/status.tsv"
    return "$code"
  fi
}

run_arm 0 P0 & p0=$!
run_arm 1 P1 & p1=$!
ok0=0; ok1=0
if wait "$p0"; then ok0=1; fi
if wait "$p1"; then ok1=1; fi
if [ "$ok0" -ne 1 ] || [ "$ok1" -ne 1 ]; then
  printf '%s\tP2\tBLOCKED\tP0_or_P1_failed\n' "$(date --iso-8601=seconds)" >> "$RECORD/status.tsv"
  exit 1
fi
run_arm 0 P2
printf '%s\tANALYSIS\tSTART\tpaired_pixels_and_development_gate\n' "$(date --iso-8601=seconds)" >> "$RECORD/status.tsv"
if "$D18_PYTHON" -B -u scripts/d20_vaihingen_decide.py > "$RECORD/queue/analysis.log" 2>&1; then
  printf '%s\tANALYSIS\tCOMPLETE\tdevelopment_decision_written\n' "$(date --iso-8601=seconds)" >> "$RECORD/status.tsv"
else
  code=$?
  printf '%s\tANALYSIS\tFAILED\tcode=%s\n' "$(date --iso-8601=seconds)" "$code" >> "$RECORD/status.tsv"
  exit "$code"
fi
echo 'D20 Vaihingen seed42 matched development queue complete; seed17 was not started.'
