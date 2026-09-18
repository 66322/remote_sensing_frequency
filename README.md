# Remote Sensing Frequency Segmentation

Optical + DSM semantic segmentation experiments on ISPRS Vaihingen and Potsdam.

## Start here

**All experiment purposes, code mappings, datasets, results and future plans:**

[Project documentation](docs/START_HERE.md)

## Current best

E32 — P2-H + Rare30

Vaihingen @10k:

- NB OA: 92.2850%
- NB mF1_fg5: 90.4897%
- NB mIoU_fg5: **83.0658%**

## Current work

- E40 — Normal shallow detail preservation
- E41 — HF-only shallow detail preservation

## Main directories

- `model/` — model implementations
- `scripts/` — training / evaluation / audit scripts
- `runs/` — lightweight experiment outputs only
- `records/` — analyses and frozen experiment evidence
- `docs/` — project-wide experiment documentation
- `sources/` — historical local source snapshots

Large checkpoints, pretrained weights and datasets are intentionally not tracked by Git.
