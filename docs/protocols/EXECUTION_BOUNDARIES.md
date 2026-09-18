# Execution Boundaries

## Persistent filesystem boundary

All persistent project files must stay under:

`/home/jovyan/zzx`

The active project root is:

`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro`

New code and outputs may be written only inside these project locations:

- `configs/`
- `docs/`
- `model/`
- `records/`
- `runs/`
- `scripts/`
- `tests/`

Do not create persistent results, checkpoints, logs, reports or code outside
the project root.

## Read-only inputs

These locations are input-only:

- `/home/jovyan/zzx/projects_zys/raw_extract/Potsdam_unzipped`
- `/home/jovyan/zzx/paper_rebuild/08_assets/pretrained`

Do not modify, rename, move or overwrite the raw dataset or pretrained weights.

## GPU boundary

Every GPU task must use physical GPU 0 only.

Before starting Python:

`export CUDA_VISIBLE_DEVICES=0`

Inside that process, use:

`cuda:0`

Because only physical GPU 0 is visible, logical `cuda:0` maps to physical GPU 0.

Forbidden:

- physical GPU 1 or another GPU;
- multiple GPUs;
- distributed training;
- `torchrun`;
- fallback to another GPU;
- launching GPU work without `CUDA_VISIBLE_DEVICES=0`.

## Mandatory preflight

Before every launch:

`python scripts/validate_execution_boundaries.py --torch-check`

Every intended output path must be supplied using `--output`.

Example:

`python scripts/validate_execution_boundaries.py --torch-check --output runs/rebuild_v1/example --output records/example`

If this command fails, the experiment must not start.

## GitHub boundary

Do not upload:

- `*.pth`
- `*.pt`
- `*.ckpt`
- `last_train_state.pth`
- raw datasets
- pretrained weights
- complete `runs/` directories

For large artifacts, record only:

- server path;
- byte size;
- SHA256;
- summary and validation history.
