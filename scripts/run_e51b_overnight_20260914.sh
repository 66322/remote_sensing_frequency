#!/usr/bin/env bash

set -euo pipefail

ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
cd "$ROOT"

export CUDA_VISIBLE_DEVICES=0
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONPATH="$ROOT"

LOGDIR="$ROOT/.local_backups/e51b_overnight_20260914"
mkdir -p "$LOGDIR"

NATIVE_PID=1210021

echo "======================================================================"
echo "E51-B OVERNIGHT MASTER QUEUE"
date
echo "======================================================================"

echo
echo "[STAGE 0] Waiting current native gate PID=$NATIVE_PID"

while true; do
    if ! ps -p "$NATIVE_PID" >/dev/null 2>&1; then
        break
    fi

    STATE="$(
        ps -p "$NATIVE_PID" -o stat= 2>/dev/null         | awk '{print $1}'
    )"

    CMD="$(
        ps -p "$NATIVE_PID" -o cmd= 2>/dev/null || true
    )"

    if [[ "$STATE" == Z* ]]; then
        echo "[STAGE 0] Native PID became zombie; treat as exited."
        break
    fi

    if [[ "$CMD" != *"eval_e51b_gsd_robustness.py --native-only"* ]]; then
        echo "[STOP] PID $NATIVE_PID was reused by another process:"
        echo "$CMD"
        exit 19
    fi

    echo "[STAGE 0] native still running | state=$STATE | $(date)"
    sleep 30
done

echo "[STAGE 0] Native process exited"
date

GATE_JSON="$ROOT/records/e51b_gsd_robustness_screen_20260914/native_gate_summary.json"
GATE_CSV="$ROOT/records/e51b_gsd_robustness_screen_20260914/native_gate_metrics.csv"

if [[ ! -s "$GATE_JSON" || ! -s "$GATE_CSV" ]]; then
    echo "[STOP] Native gate artifacts missing."
    exit 20
fi

python - <<'PY'
import json
from pathlib import Path

p = Path(
    "records/e51b_gsd_robustness_screen_20260914/"
    "native_gate_summary.json"
)

d = json.loads(
    p.read_text(
        encoding="utf-8"
    )
)

required = {
    "PP10k_0.05",
    "PH4k_0.05",
}

missing = required - set(d)

if missing:
    raise SystemExit(
        f"[STOP] native gate incomplete: {missing}"
    )

print(
    "[PASS] STAGE 0 native-gate artifacts verified"
)
PY


echo
echo "======================================================================"
echo "[V1] CORRECT PHYSICAL SCALE — FULL 5/6/7/8/9/10/12cm"
date
echo "======================================================================"

python -u \
scripts/eval_e51b_gsd_robustness.py \
> "$LOGDIR/V1_correct_scale.log" \
2>&1

echo "[PASS] V1"
date


echo
echo "======================================================================"
echo "[V2] SCALE-BLIND PH — 5/7/9/12cm"
date
echo "======================================================================"

python -u \
scripts/eval_e51b_gsd_scale1.py \
> "$LOGDIR/V2_scale1.log" \
2>&1

echo "[PASS] V2"
date


echo
echo "======================================================================"
echo "[V3] WRONG-DIRECTION SCALE — 5/7/9/12cm"
date
echo "======================================================================"

python -u \
scripts/eval_e51b_gsd_wrongscale.py \
> "$LOGDIR/V3_wrongscale.log" \
2>&1

echo "[PASS] V3"
date


echo
echo "======================================================================"
echo "[V4] PH6K ROBUSTNESS — 5/7/9/12cm"
date
echo "======================================================================"

python -u \
scripts/eval_e51b_gsd_ph6k.py \
> "$LOGDIR/V4_ph6k.log" \
2>&1

echo "[PASS] V4"
date


echo
echo "======================================================================"
echo "[V5] DETERMINISTIC PP-R4 REPRODUCTION TO 4K"
date
echo "======================================================================"

PP_RUN="$ROOT/runs/potsdam_r4_repro4k_modality_static_seed42"

if [[ -e "$PP_RUN" ]]; then
    echo "[STOP] V5 run directory already exists:"
    echo "$PP_RUN"
    exit 30
fi

python -u \
scripts/train_potsdam_r4_repro4k.py \
  --variant F0 \
  --router-mode modality_static \
  --max-steps 4000 \
> "$LOGDIR/V5_PP4k_train.log" \
2>&1

echo "[PASS] V5 PP4k training complete"
date


echo
echo "======================================================================"
echo "[V6] SAME-STEP PP4K VS PH4K — FULL GSD SWEEP"
date
echo "======================================================================"

python -u \
scripts/eval_e51b_same_step_pp4k_ph4k.py \
> "$LOGDIR/V6_same_step.log" \
2>&1

echo "[PASS] V6"
date


echo
echo "======================================================================"
echo "BUILD FINAL OVERNIGHT SUMMARY"
echo "======================================================================"

python - <<'PY'
from pathlib import Path

ROOT = Path(
    "/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro"
)

items = [
    (
        "V1_CORRECT_SCALE",
        ROOT
        / "records/e51b_gsd_robustness_screen_20260914"
        / "pp_vs_ph_relative_robustness.csv",
    ),
    (
        "V2_SCALE1",
        ROOT
        / "records/e51b_gsd_robustness_scale1_20260914"
        / "pp_vs_ph_relative_robustness.csv",
    ),
    (
        "V3_WRONG_SCALE",
        ROOT
        / "records/e51b_gsd_robustness_wrongscale_20260914"
        / "pp_vs_ph_relative_robustness.csv",
    ),
    (
        "V4_PH6K",
        ROOT
        / "records/e51b_gsd_robustness_ph6k_20260914"
        / "pp_vs_ph_relative_robustness.csv",
    ),
    (
        "V6_SAME_STEP_PP4K_PH4K",
        ROOT
        / "records/e51b_gsd_same_step_pp4k_ph4k_20260914"
        / "pp_vs_ph_relative_robustness.csv",
    ),
]

out = (
    ROOT
    / "records"
    / "E51B_OVERNIGHT_SUMMARY_20260914.txt"
)

lines = []

for title, path in items:

    lines.append(
        "=" * 100
    )
    lines.append(
        title
    )
    lines.append(
        str(path)
    )
    lines.append(
        "=" * 100
    )

    if path.is_file():
        lines.append(
            path.read_text(
                encoding="utf-8"
            )
        )
    else:
        lines.append(
            "[MISSING]"
        )

    lines.append("")

out.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print(out)
PY

echo
echo "======================================================================"
echo "E51-B OVERNIGHT MASTER QUEUE COMPLETE"
date
echo "======================================================================"
