#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${CONDA_DEFAULT_ENV:-}" != "remote_sensing" ]]; then
  echo "Activate existing remote_sensing environment first; this script does not install packages." >&2
  exit 2
fi
case "${1:---launch}" in
  --prepare-only) exec python -B -u scripts/run_rebuild_v1_day_queue.py --prepare-only ;;
  --profile-only) exec python -B -u scripts/run_rebuild_v1_day_queue.py --profile-only ;;
  --launch) exec python -B -u scripts/run_rebuild_v1_day_queue.py ;;
  *) echo "Usage: $0 [--prepare-only|--profile-only|--launch]" >&2; exit 2 ;;
esac
