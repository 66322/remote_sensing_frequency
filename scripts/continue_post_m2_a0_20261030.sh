#!/usr/bin/env bash
# Thin stage chaining only. The frozen c22 A0 science and pair controller are reused.
set -Eeuo pipefail
STAGE=preflight
trap 'rc=$?; printf "A0_CONTINUATION_FAILED stage=%s rc=%s; inspect original pair logs; no automatic retry\n" "$STAGE" "$rc" >&2; exit "$rc"' ERR

export ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
export A0="$ROOT/records/post_m2_a0_capability_20261029"
export POST_M2_CODE_COMMIT=c22a046407daf42064cbb161429f2648c9b86d66
export POST_M2_DINO3_REPO="$ROOT/external/dinov3_6876159"
export POST_M2_DINO3_WEIGHTS="$ROOT/pretrained/dinov3/dinov3_vits16_pretrain_lvd1689m-08c60483.pth"
SCRIPT="$A0/post_m2_a0.py"
GUARD="$A0/formal_continuation_20261030.started"

# Read small existing receipts only; do not decode tiles, hash weights or rerun probes.
python -B - <<'PY'
import csv, json, os, subprocess
from pathlib import Path
a0 = Path(os.environ['A0'])
commit = os.environ['POST_M2_CODE_COMMIT']
assert (a0/'post_m2_a0.py').is_file(), 'Frozen A0 script is missing'
assert Path(os.environ['POST_M2_DINO3_WEIGHTS']).is_file(), 'Prepared DINOv3 weight is missing'
assert not (a0/'formal_continuation_20261030.started').exists(), 'Continuation already registered; inspect status, do not restart'
for kind in ('dino2', 'dino3'):
    # Profile includes a real load/forward/backward path. The earlier DINO2
    # smoke predates the no_grad repair; do not demand that it be repeated.
    value = json.loads((a0/('profile_'+kind+'.json')).read_text())
    assert value['status'] == 'PROFILE_COMPLETED_NO_SCIENTIFIC_RESULT' and value['kind'] == kind, 'Invalid readiness receipt'
    assert value['code_commit'] == commit, 'Profile belongs to a different execution commit'
    for name in ('train_started.json', 'train_complete.json', 'failure.txt', 'calibration_started.json', 'calibration_result.json', 'outer_started.json'):
        assert not (a0/kind/name).exists(), 'Existing formal evidence: '+kind+'/'+name+'; inspect, do not restart'
assert not list(a0.glob('pair_train*')), 'Existing pair training evidence; inspect, do not restart'
assert not list(a0.glob('pair_evaluate*')), 'Existing pair evaluation evidence; inspect, do not restart'
assert not (a0/'calibration_screen.json').exists(), 'Existing calibration screen; inspect, do not restart'
full = Path(os.environ['ROOT'])/'records/post_m2_multiroute_v2_20261030_r1'
pipeline_receipt = full/'pipeline_started.json'
pipeline_pid = full/'pipeline.pid'
if pipeline_receipt.is_file() or pipeline_pid.is_file():
    pid = int(json.loads(pipeline_receipt.read_text())['pid']) if pipeline_receipt.is_file() else int(pipeline_pid.read_text().strip())
    command = Path('/proc')/str(pid)/'cmdline'
    if command.is_file() and b'post_m2_multiroute.py' in command.read_bytes():
        raise RuntimeError('Full pipeline is already active, including CPU preparation; do not dispatch a competing A0 controller')
rows = subprocess.check_output(['nvidia-smi', '--query-gpu=index,name,memory.free,uuid', '--format=csv,noheader,nounits'], text=True)
gpus = {int(r[0]): [s.strip() for s in r] for r in csv.reader(rows.splitlines()) if r}
apps = subprocess.check_output(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader,nounits'], text=True)
for index in (0, 1):
    assert index in gpus and 'H100' in gpus[index][1] and int(gpus[index][2]) >= 40000, 'GPU0/1 must be H100 with >=40000 MiB free'
    assert gpus[index][3] not in apps, 'GPU'+str(index)+' is busy; no job registered or dispatched'
print('A0_PREFLIGHT_REUSED_BOTH_MODELS; GPU0/1 available; no new probes', flush=True)
PY

# New caches stay within ROOT. Reuse the verified weight through a symlink;
# leave the previous /root/.cache copy and all raw/public weights untouched.
export TORCH_HOME="$ROOT/cache/torch"
export XDG_CACHE_HOME="$ROOT/cache"
export CUDA_CACHE_PATH="$ROOT/cache/cuda"
export TMPDIR="$A0/temporary"
mkdir -p "$TORCH_HOME/hub/checkpoints" "$CUDA_CACHE_PATH" "$TMPDIR"
CACHED_WEIGHT="$TORCH_HOME/hub/checkpoints/$(basename "$POST_M2_DINO3_WEIGHTS")"
if [ ! -e "$CACHED_WEIGHT" ]; then
  ln -s "$POST_M2_DINO3_WEIGHTS" "$CACHED_WEIGHT"
fi
mkdir "$GUARD"
printf '%s\n' "$$" > "$GUARD/controller.pid"
date -Iseconds > "$GUARD/registered_at.txt"
printf '%s\n' "$POST_M2_CODE_COMMIT" > "$GUARD/a0_execution_commit.txt"

STAGE=train
python -u -B "$SCRIPT" pair --phase train
STAGE=calibration
python -u -B "$SCRIPT" pair --phase evaluate --split calibration
STAGE=screen
python -u -B "$SCRIPT" screen
SCREEN=$(python -B -c 'import json,os; from pathlib import Path; print(json.loads((Path(os.environ["A0"])/"calibration_screen.json").read_text())["status"])')
case "$SCREEN" in
  READY_FOR_OUTER_DEVELOPMENT_EVALUATION)
    STAGE=outer
    python -u -B "$SCRIPT" pair --phase evaluate --split outer
    ;;
  INVALID_PROBE|NO_INCREMENT_STOP_A_ROUTE)
    printf 'A0_SCREEN=%s; no outer evaluation or A1/A2 dispatch; independent G/Q/S and spatial-readout plans retain their own conditions\n' "$SCREEN"
    ;;
  *) printf 'Unknown calibration screen status: %s\n' "$SCREEN" >&2; exit 1 ;;
esac
STAGE=status
python -u -B "$SCRIPT" status
date -Iseconds > "$GUARD/completed_at.txt"
printf 'A0_CONTINUATION_COMPLETE screen=%s; preserve heads, trajectories, integer counts and original logs\n' "$SCREEN"
