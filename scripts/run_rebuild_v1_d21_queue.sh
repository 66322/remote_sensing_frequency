#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export XFORMERS_DISABLED=1 PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
# Reuse the existing isolated DINO environment; only prepare it if absent.
bash scripts/setup_rebuild_v1_d18_environment.sh --environment-only
conda_exe="${CONDA_EXE:-$(command -v conda)}"
base="$("$conda_exe" info --base)"
python_bin="$base/envs/d18_dino/bin/python"
"$python_bin" -B scripts/prepare_rebuild_v1_d18.py
exec "$python_bin" -B -u scripts/run_rebuild_v1_d21_queue.py "$@"
