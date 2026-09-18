# Remote Sensing Frequency Segmentation

Optical and DSM semantic-segmentation experiments on ISPRS Vaihingen and
Potsdam.

## Start here

[Project documentation](docs/START_HERE.md)

## Current work

The active line is REBUILD_V1 multimodal capacity and robustness analysis.

R01-R05, C-OO and C-OO-QD are complete. The only active next experiment is
D1-D3 local failure diagnostics.

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
