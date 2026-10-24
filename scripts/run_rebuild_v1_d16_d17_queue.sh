#!/usr/bin/env bash
set -euo pipefail
R=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
cd "$R"
export CUDA_DEVICE_ORDER=PCI_BUS_ID CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
export PYTHONDONTWRITEBYTECODE=1
exec python -B -u scripts/run_rebuild_v1_d16_d17_queue.py
