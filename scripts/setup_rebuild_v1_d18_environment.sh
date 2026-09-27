#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
conda_exe="${CONDA_EXE:-$(command -v conda)}"
base="$("$conda_exe" info --base)"
python_bin="$base/envs/d18_dino/bin/python"
marker="$base/envs/d18_dino/.rebuild_v1_d18_ready"
if [[ ! -f "$marker" ]]; then
  if [[ ! -x "$python_bin" ]]; then
    "$conda_exe" create -y -n d18_dino python=3.10 pip
  fi
  "$python_bin" -m pip install torch==2.2.2 torchvision==0.17.2 --index-url https://download.pytorch.org/whl/cu121
  "$python_bin" -m pip install 'numpy<2' scipy scikit-image imageio tifffile pillow ml-collections absl-py omegaconf tqdm
  "$python_bin" -c "import torch,numpy,skimage,scipy,ml_collections; assert torch.__version__.startswith('2.2.2'); assert torch.cuda.is_available()"
  touch "$marker"
fi
if [[ "${1:-}" == "--environment-only" ]]; then
  "$python_bin" -c "import torch,numpy,skimage,scipy,ml_collections; assert torch.__version__.startswith('2.2.2'); assert int(numpy.__version__.split('.')[0]) < 2; assert torch.cuda.is_available(); print('D18 ENVIRONMENT READY', torch.__version__, torch.cuda.get_device_name(0))"
  exit 0
fi
cd "$root"
"$python_bin" -B -u scripts/prepare_rebuild_v1_d18.py
"$python_bin" -c "import torch,numpy,skimage,scipy,ml_collections; assert torch.__version__.startswith('2.2.2'); assert torch.cuda.is_available()"
"$python_bin" -B -m unittest discover -s tests -p test_d18_d19_night.py -v
printf '%s\n' "$python_bin" > records/rebuild_v1_d18_d19_queue_20260927/d18_python.txt
