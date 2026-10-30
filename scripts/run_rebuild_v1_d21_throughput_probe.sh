#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
gpu="${1:-0}"
if [[ "$gpu" != 0 && "$gpu" != 1 ]]; then
  echo 'usage: bash scripts/run_rebuild_v1_d21_throughput_probe.sh [physical_gpu_0_or_1]' >&2
  exit 2
fi
export CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES="$gpu"
export CUBLAS_WORKSPACE_CONFIG=:4096:8 XFORMERS_DISABLED=1 PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
conda_exe="${CONDA_EXE:-$(command -v conda)}"
base="$("$conda_exe" info --base)"
python_bin="$base/envs/d18_dino/bin/python"
if [[ ! -x "$python_bin" ]]; then
  echo "Missing existing d18_dino environment: $python_bin; no installation attempted" >&2
  exit 1
fi
"$python_bin" -c 'import torch,numpy,skimage,scipy,ml_collections; assert torch.cuda.is_available(); print("existing environment",torch.__version__,torch.cuda.get_device_name(0))'
IFS=',' read -r used util < <(nvidia-smi -i "$gpu" --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits)
used="${used//[[:space:]]/}"; util="${util//[[:space:]]/}"
if (( used > 1500 || util > 10 )); then
  echo "Physical GPU $gpu is busy: ${used} MiB, ${util}% utilization; probe not started" >&2
  exit 1
fi
available_kib="$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"
if (( available_kib < 48 * 1024 * 1024 )); then
  echo "Less than 48 GiB host RAM available; probe not started" >&2
  exit 1
fi
output="records/rebuild_v1_d21_throughput_probe_20260929/gpu${gpu}_F2_vaihingen_seed42.json"
mkdir -p "$(dirname "$output")"
samples="records/rebuild_v1_d21_throughput_probe_20260929/gpu${gpu}_telemetry.csv"
nvidia-smi -i "$gpu" --query-gpu=timestamp,utilization.gpu,memory.used,power.draw \
  --format=csv,noheader,nounits -l 1 > "$samples" &
sampler_pid=$!
trap 'kill "$sampler_pid" 2>/dev/null || true; wait "$sampler_pid" 2>/dev/null || true' EXIT
timeout --signal=INT --kill-after=30s 25m "$python_bin" -B -u scripts/probe_rebuild_v1_d21_throughput.py \
  --dataset vaihingen --arm F2 --warmup 2 --measured 6 --max-minutes 20 --output "$output"
