# Execution Boundaries

## Experiment preparation policy

For new experiments, follow [实验规划与服务器准备规则](EXPERIMENT_PLANNING_RULES.md).
Benchmark throughput on the actual server before fixing the training configuration.
Use one seed by default and document a concrete reason for additional seeds.
Disclose downloads and environment changes before preparation; GitHub and Hugging Face
are user-reported reachable sources, while redirects and other sites require checking.
Separate resource preparation from training launch; launchers validate prepared artifacts.

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

Explicit user authorization permits physical GPU0 and GPU1 as independent
workers for D15, D16/D17 and D18/D19. The D18/D19 queue checks both physical
indices, project scope, input presence and source binding. Each worker sees
exactly its assigned GPU and uses logical cuda:0. No distributed training is
introduced. The GPU0-only rules and validator below apply to historical GPU0
queues, not these authorized dual-worker queues.
`configs/execution_boundaries.json` retains the historical GPU0 validator
settings; use the active D18/D19 protocol and queue checks for this run.

For historical GPU0-only queues, every GPU task uses physical GPU 0 only.

Before starting Python:

`export CUDA_VISIBLE_DEVICES=0`

Inside that process, use:

`cuda:0`

Because only physical GPU 0 is visible, logical `cuda:0` maps to physical GPU 0.

Forbidden:

- an unassigned physical GPU;
- multiple GPUs;
- distributed training;
- `torchrun`;
- fallback to another GPU;
- launching GPU work without `CUDA_VISIBLE_DEVICES` set to the assigned index.

## Mandatory preflight

Before launching a historical GPU0-only queue:

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
