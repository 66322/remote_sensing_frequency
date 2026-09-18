# Next Experiment: D1-D3 Local Failure Diagnostics

- Status: code preparation
- Priority: only active experiment
- Models: R05 and C-OO-QD
- Training: none; existing best checkpoints only
- Device: physical GPU 0 only
- Dataset: Potsdam Val2 only
- TEST6: prohibited

## Purpose

Determine whether the observed R05 advantage is spatially local and measure
sensitivity to local missing input, cross-modal misalignment and local severe
quality degradation.

## D1: local second-stream missing

Zero each of four quadrants separately. Report whole-image, affected-region and
unaffected-region metrics.

## D2: spatial misalignment

Shift the second stream up, down, left and right by 2, 4 and 8 pixels. Use zero
padding and no circular wrapping. Report directional mean and worst direction.

## D3: local quality degradation

Apply down8 only inside each of four quadrants. Report whole-image,
affected-region and unaffected-region metrics.

## Fixed protocol

- Val2 tiles: `3_11`, `5_10`
- splits: FullGT and NoBoundary
- metrics: OA, mF1_fg5, mIoU_fg5 and mIoU_all6
- checkpoint: each model's own `best_model.pth`
- smoke: one tile and four representative conditions
- formal evaluation: 21 conditions per model

## Completion gate

Do not push experimental artifacts until the formal evaluation has been checked
and analyzed. The final closure must contain:

- evaluation script;
- `dataset_metrics.csv`;
- `per_tile_metrics.csv`;
- `summary.json`;
- `comparison.csv`;
- `EXPERIMENT_REPORT.md`;
- `artifact_manifest.sha256`;
- updated registry, project status, do-not-repeat list, index and next step.
