# Next Experiment: D1-D3 Local Failure Diagnostics

- Status: queued for execution
- Priority: D1-D3 first, then optical-fallback ablations and one replication seed
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

## Follow-on queue

The queue continues after D1-D3 without requiring manual intervention:

1. A1 removes Optical dropout while retaining 10% DSM dropout and the same
   overall 24% quality-corruption probability.
2. A2 uses 20% DSM dropout and no Optical dropout to strengthen the Optical
   fallback path.
3. R05, R01 and C-OO-QD are repeated with seed 17 after the two ablations.
4. Every new training policy is evaluated under the existing nine-condition
   clean/global-corruption protocol.

Each A1/A2 formal run is gated by its own 20-step smoke run. A failed smoke
skips only the dependent formal run. Any other failed stage is recorded and the
queue proceeds to the next independent experiment. There is no automatic retry.

The executable queue is
`scripts/run_rebuild_v1_next_experiments_20260918.sh`. It exports only physical
GPU 0, validates the execution boundaries before every stage, applies hard
timeouts, and writes all logs/status files below
`records/rebuild_v1_next_queue_20260918`.

## Completion gate

Do not push experimental artifacts until the formal evaluation has been checked
and analyzed. The final closure must contain:

- evaluation script;
- `dataset_metrics.csv`;
- `per_tile_metrics.csv`;
- `summary.json`;
- `paired_condition_comparison.csv`;
- `family_summary.csv` and `decision_evidence.json`;
- `EXPERIMENT_REPORT.md`;
- `artifact_manifest.sha256`;
- updated registry, project status, do-not-repeat list, index and next step.
