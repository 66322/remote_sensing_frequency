# Remote Sensing Frequency Segmentation

Optical and DSM semantic-segmentation experiments on ISPRS Vaihingen and
Potsdam.

## Start here

[Project documentation](docs/START_HERE.md)

## Current work

The active line is REBUILD_V1 multimodal capacity and robustness analysis.

Active research branch: **`rebuild-v1-protocol-20260915`**. The GitHub default
is `main`; a bare repository link does not select this research branch.

R01-R05, C-OO and C-OO-QD seed42 have committed compact evidence. A1/A2,
seed17 and D1-D6 follow-ups are reported complete from server logs, with
original compact artifacts still pending archival. B1 is **running as last
reported on 2026-09-20; no final B1 conclusion is available**.
Training code at launch: `e2ad594` (12:56 +08:00, fix2).

Read the [current handoff](docs/current/HANDOFF.md) before proposing work.
Do not restart B1 or interpret QUEUE FINISHED as every stage passing.
This repository is a recorded snapshot, not a live server monitor.

## Mandatory execution boundaries

- Physical GPU 0 only.
- `CUDA_VISIBLE_DEVICES=0` is required.
- Persistent files must remain under `/home/jovyan/zzx`.
- Project outputs must remain inside this repository.
- Raw datasets and pretrained weights are read-only.
- Checkpoints and complete run directories are not uploaded to GitHub.

Full policy:

[Execution boundaries](docs/protocols/EXECUTION_BOUNDARIES.md)

## Main directories

- `model/`: model implementations
- `scripts/`: training, evaluation and audit scripts
- `configs/`: configurations and execution policy
- `runs/`: server-only runtime outputs
- `records/`: compact frozen evidence
- `docs/`: documentation and experiment reports
