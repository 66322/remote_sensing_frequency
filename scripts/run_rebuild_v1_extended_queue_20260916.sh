#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
cd "$ROOT"

STOP_FILE="records/STOP_REBUILD_V1_QUEUE"
STATUS="records/rebuild_v1_extended_queue_20260916_status.tsv"
QUEUE_LOG="records/rebuild_v1_extended_queue_20260916.log"
mkdir -p records

touch "$STATUS"

stamp() { date -Is; }
log() { echo "[$(stamp)] $*" | tee -a "$QUEUE_LOG"; }
record() { printf '%s\t%s\t%s\n' "$(stamp)" "$1" "$2" >> "$STATUS"; }

before_stage() {
  local stage="$1"
  if [[ -e "$STOP_FILE" ]]; then
    log "GRACEFUL STOP requested before stage=$stage via $STOP_FILE"
    record "$stage" "STOPPED_BEFORE_START"
    exit 0
  fi
  log "===== START $stage ====="
  record "$stage" "START"
}

after_stage() {
  local stage="$1"
  log "===== COMPLETE $stage ====="
  record "$stage" "COMPLETE"
}

json_check() {
  local path="$1"
  python - "$path" <<'PY'
import json, sys
from pathlib import Path
p=Path(sys.argv[1])
if not p.is_file():
    raise SystemExit(1)
json.load(open(p, encoding='utf-8'))
PY
}

r01_summary_check() {
  local path="$1"
  local step="$2"
  python - "$path" "$step" <<'PY'
import json, sys
s=json.load(open(sys.argv[1], encoding='utf-8'))
assert int(s.get('global_step',-1)) == int(sys.argv[2]), s
assert s.get('test6_loaded') is False, s
assert s.get('dsm_loaded') is False, s
a=s.get('structural_audit') or {}
assert a.get('pass') is True and not a.get('forbidden_parameter_names'), a
PY
}

robust_summary_check() {
  local path="$1"
  local step="$2"
  local variant="$3"
  python - "$path" "$step" "$variant" <<'PY'
import json, sys
s=json.load(open(sys.argv[1], encoding='utf-8'))
assert int(s.get('global_step',-1)) == int(sys.argv[2]), s
assert s.get('experiment_id') == sys.argv[3], s
assert s.get('test6_loaded') is False, s
aug=s.get('augmentation') or {}
assert int(aug.get('total_samples',-1)) > 0, aug
assert abs(sum((aug.get('fractions') or {}).values())-1.0) < 1e-6, aug
PY
}

log "REBUILD_V1 EXTENDED QUEUE"
log "ROOT=$ROOT"
log "PID=$$"
log "PYTHON=$(command -v python || true)"
log "BRANCH=$(git branch --show-current)"
log "HEAD=$(git rev-parse HEAD)"

before_stage "00_PREFLIGHT"
[[ "$(git branch --show-current)" == "rebuild-v1-protocol-20260915" ]] || { log "ERROR wrong branch"; exit 1; }
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || { log "ERROR tracked working tree is dirty"; git status --short; exit 1; }
python -m py_compile \
  model/rebuild_v1_optical_only.py \
  scripts/train_rebuild_v1_r01_optical_only.py \
  scripts/profile_rebuild_v1_compute.py \
  scripts/eval_rebuild_v1_fusion_gain_severity.py \
  scripts/train_rebuild_v1_dual_robust.py \
  scripts/eval_rebuild_v1_dual_robust_conditions.py \
  scripts/summarize_rebuild_v1_core_matrix.py
python - <<'PY'
import json
for p in [
 'configs/rebuild_v1/r01_optical_only_16k.json',
 'configs/rebuild_v1/r03_quality_corruption_16k.json',
 'configs/rebuild_v1/r04_modality_dropout_16k.json',
 'configs/rebuild_v1/potsdam_split_seed20260915.json',
]:
    json.load(open(p, encoding='utf-8'))
print('[PASS] configs parse')
PY
if pgrep -af 'train_rebuild_v1_r01_optical_only.py|train_rebuild_v1_dual_robust.py' >/tmp/rebuild_queue_live.$$ 2>/dev/null; then
  cat /tmp/rebuild_queue_live.$$
  rm -f /tmp/rebuild_queue_live.$$
  log "ERROR another REBUILD_V1 formal trainer is already running"
  exit 1
fi
rm -f /tmp/rebuild_queue_live.$$ || true
after_stage "00_PREFLIGHT"

before_stage "A0_P0_R02_PROFILE"
P0_R02="records/rebuild_v1_compute_profile_20260916/r02_profile.json"
if json_check "$P0_R02" 2>/dev/null; then log "SKIP valid existing $P0_R02"; else
  python -u scripts/profile_rebuild_v1_compute.py --model R02 > records/rebuild_v1_p0_r02_profile_20260916.log 2>&1
  json_check "$P0_R02"
fi
after_stage "A0_P0_R02_PROFILE"

before_stage "A1_R01_SMOKE"
R01_SMOKE="runs/rebuild_v1/R01_optical_only_seed42_smoke20_queuegate"
if r01_summary_check "$R01_SMOKE/summary.json" 20 2>/dev/null; then log "SKIP valid R01 smoke"; else
  [[ ! -e "$R01_SMOKE" ]] || { log "ERROR incomplete/colliding R01 smoke dir: $R01_SMOKE"; exit 1; }
  python -u scripts/train_rebuild_v1_r01_optical_only.py --config configs/rebuild_v1/r01_optical_only_16k.json --smoke-steps 20 --smoke-eval --run-tag queuegate > records/rebuild_v1_r01_smoke_20260916.log 2>&1
  r01_summary_check "$R01_SMOKE/summary.json" 20
fi
after_stage "A1_R01_SMOKE"

before_stage "A2_R01_FORMAL_16K"
R01_RUN="runs/rebuild_v1/R01_optical_only_seed42_sched16000_stop16000"
if r01_summary_check "$R01_RUN/summary.json" 16000 2>/dev/null; then log "SKIP valid completed R01 formal"; else
  if [[ -e "$R01_RUN" ]]; then
    [[ -f "$R01_RUN/last_train_state.pth" ]] || { log "ERROR R01 dir exists without resumable state"; exit 1; }
    log "RESUME R01 formal"
    python -u scripts/train_rebuild_v1_r01_optical_only.py --config configs/rebuild_v1/r01_optical_only_16k.json --resume > records/rebuild_v1_r01_formal_16k_20260916.log 2>&1
  else
    log "FRESH R01 formal"
    python -u scripts/train_rebuild_v1_r01_optical_only.py --config configs/rebuild_v1/r01_optical_only_16k.json > records/rebuild_v1_r01_formal_16k_20260916.log 2>&1
  fi
  r01_summary_check "$R01_RUN/summary.json" 16000
fi
after_stage "A2_R01_FORMAL_16K"

before_stage "A3_R01_PROFILE"
P0_R01="records/rebuild_v1_compute_profile_20260916/r01_profile.json"
if json_check "$P0_R01" 2>/dev/null; then log "SKIP valid existing $P0_R01"; else
  python -u scripts/profile_rebuild_v1_compute.py --model R01 > records/rebuild_v1_p0_r01_profile_20260916.log 2>&1
  json_check "$P0_R01"
fi
after_stage "A3_R01_PROFILE"

before_stage "A4_R01_R02_FUSION_GAIN_SEVERITY"
FG="records/rebuild_v1_r01_r02_fusion_gain_severity_20260916/summary.json"
if json_check "$FG" 2>/dev/null; then log "SKIP valid existing Fusion-Gain result"; else
  python -u scripts/eval_rebuild_v1_fusion_gain_severity.py > records/rebuild_v1_fusion_gain_severity_20260916.log 2>&1
  json_check "$FG"
fi
after_stage "A4_R01_R02_FUSION_GAIN_SEVERITY"

before_stage "B1_R04_SMOKE"
R04_SMOKE="runs/rebuild_v1/R04_dual_f0_modality_dropout_seed42_smoke20_queuegate"
if robust_summary_check "$R04_SMOKE/summary.json" 20 R04 2>/dev/null; then log "SKIP valid R04 smoke"; else
  [[ ! -e "$R04_SMOKE" ]] || { log "ERROR incomplete/colliding R04 smoke dir"; exit 1; }
  python -u scripts/train_rebuild_v1_dual_robust.py --config configs/rebuild_v1/r04_modality_dropout_16k.json --smoke-steps 20 --smoke-eval --run-tag queuegate > records/rebuild_v1_r04_smoke_20260916.log 2>&1
  robust_summary_check "$R04_SMOKE/summary.json" 20 R04
fi
after_stage "B1_R04_SMOKE"

before_stage "B2_R04_FORMAL_16K"
R04_RUN="runs/rebuild_v1/R04_dual_f0_modality_dropout_seed42_sched16000_stop16000"
if robust_summary_check "$R04_RUN/summary.json" 16000 R04 2>/dev/null; then log "SKIP valid completed R04"; else
  if [[ -e "$R04_RUN" ]]; then
    [[ -f "$R04_RUN/last_train_state.pth" ]] || { log "ERROR R04 dir exists without resumable state"; exit 1; }
    python -u scripts/train_rebuild_v1_dual_robust.py --config configs/rebuild_v1/r04_modality_dropout_16k.json --resume > records/rebuild_v1_r04_formal_16k_20260916.log 2>&1
  else
    python -u scripts/train_rebuild_v1_dual_robust.py --config configs/rebuild_v1/r04_modality_dropout_16k.json > records/rebuild_v1_r04_formal_16k_20260916.log 2>&1
  fi
  robust_summary_check "$R04_RUN/summary.json" 16000 R04
fi
after_stage "B2_R04_FORMAL_16K"

before_stage "B3_R04_EVAL"
R04_EVAL="records/rebuild_v1_r04_robust_eval_20260916/summary.json"
if json_check "$R04_EVAL" 2>/dev/null; then log "SKIP valid existing R04 eval"; else
  python -u scripts/eval_rebuild_v1_dual_robust_conditions.py --variant R04 > records/rebuild_v1_r04_eval_20260916.log 2>&1
  json_check "$R04_EVAL"
fi
after_stage "B3_R04_EVAL"

before_stage "B4_R03_SMOKE"
R03_SMOKE="runs/rebuild_v1/R03_dual_f0_quality_corruption_seed42_smoke20_queuegate"
if robust_summary_check "$R03_SMOKE/summary.json" 20 R03 2>/dev/null; then log "SKIP valid R03 smoke"; else
  [[ ! -e "$R03_SMOKE" ]] || { log "ERROR incomplete/colliding R03 smoke dir"; exit 1; }
  python -u scripts/train_rebuild_v1_dual_robust.py --config configs/rebuild_v1/r03_quality_corruption_16k.json --smoke-steps 20 --smoke-eval --run-tag queuegate > records/rebuild_v1_r03_smoke_20260916.log 2>&1
  robust_summary_check "$R03_SMOKE/summary.json" 20 R03
fi
after_stage "B4_R03_SMOKE"

before_stage "B5_R03_FORMAL_16K"
R03_RUN="runs/rebuild_v1/R03_dual_f0_quality_corruption_seed42_sched16000_stop16000"
if robust_summary_check "$R03_RUN/summary.json" 16000 R03 2>/dev/null; then log "SKIP valid completed R03"; else
  if [[ -e "$R03_RUN" ]]; then
    [[ -f "$R03_RUN/last_train_state.pth" ]] || { log "ERROR R03 dir exists without resumable state"; exit 1; }
    python -u scripts/train_rebuild_v1_dual_robust.py --config configs/rebuild_v1/r03_quality_corruption_16k.json --resume > records/rebuild_v1_r03_formal_16k_20260916.log 2>&1
  else
    python -u scripts/train_rebuild_v1_dual_robust.py --config configs/rebuild_v1/r03_quality_corruption_16k.json > records/rebuild_v1_r03_formal_16k_20260916.log 2>&1
  fi
  robust_summary_check "$R03_RUN/summary.json" 16000 R03
fi
after_stage "B5_R03_FORMAL_16K"

before_stage "B6_R03_EVAL"
R03_EVAL="records/rebuild_v1_r03_robust_eval_20260916/summary.json"
if json_check "$R03_EVAL" 2>/dev/null; then log "SKIP valid existing R03 eval"; else
  python -u scripts/eval_rebuild_v1_dual_robust_conditions.py --variant R03 > records/rebuild_v1_r03_eval_20260916.log 2>&1
  json_check "$R03_EVAL"
fi
after_stage "B6_R03_EVAL"

before_stage "C1_CORE_MATRIX_SUMMARY"
CORE="records/rebuild_v1_core_matrix_20260917/summary.json"
if json_check "$CORE" 2>/dev/null; then log "SKIP valid existing core matrix"; else
  python -u scripts/summarize_rebuild_v1_core_matrix.py > records/rebuild_v1_core_matrix_20260917.log 2>&1
  json_check "$CORE"
fi
after_stage "C1_CORE_MATRIX_SUMMARY"

log "REBUILD_V1 EXTENDED QUEUE CORE A+B+C1 COMPLETE"
record "QUEUE" "CORE_ABC1_COMPLETE"
log "Default stop before conditional R05/G-S/G-H/A1/pruning."
