# Deterministic F0 vs P1 paired diagnostic

Date: 2026-08-29

## Protocol

- Dataset: Vaihingen
- Seed: 42
- Crop: 512
- Grid: 32x32
- Physical batch: 4
- Gradient accumulation: 4
- Effective sampled batch: 16
- AdamW
- Backbone LR: 6e-5
- Decoder/head LR: 6e-4
- P1 prefreq LR: 6e-4
- Warmup: 1500 optimizer steps
- Poly schedule denominator: 160000
- Diagnostic endpoint: 2000 optimizer steps
- Strict deterministic algorithms enabled
- CUBLAS_WORKSPACE_CONFIG=:4096:8
- Segmentation CE implemented as flattened pixel-wise CE
- P1 ReflectionPad replaced by forward-exact slice+concat implementation

## Reproducibility gates

- F0 independent A/B 200-step trajectories: exact 200/200 match
- P1 independent A/B 20-step trajectories: exact 20/20 match
- Original P1 vs deterministic P1 forward max_abs_diff: 0
- Original reflect pad vs deterministic reflect pad max_abs_diff: 0

## Results

| Metric | F0 @2k | P1 @2k | P1-F0 |
|---|---:|---:|---:|
| Full OA | 88.1123 | 88.1331 | +0.0208 pp |
| Full mF1_fg5 | 82.4948 | 83.0281 | +0.5333 pp |
| Full mIoU_fg5 | 71.6300 | 72.2007 | +0.5707 pp |
| NB OA | 91.3511 | 91.3522 | +0.0011 pp |
| NB mF1_fg5 | 86.6333 | 87.0907 | +0.4574 pp |
| NB mIoU_fg5 | 77.4944 | 78.0476 | +0.5532 pp |

## P1 step 2000 diagnostics

- hf_scale mean: 0.999415
- hf_scale min: 0.315153
- hf_scale max: 1.408206
- mean |scale-1|: 0.034737
- S < 0.95: 5.41%
- S > 1.05: 11.78%
- S < 0.5: 0.10%
- S > 1.5: 0.00%

## Current interpretation

P1-v1 passes the deterministic 2k screening gate.

The gain is visible in both FullGT and noBoundary mF1/mIoU,
while OA is essentially unchanged.

At step 2000 the learned scale has a mean close to one and contains
both suppression and enhancement regions, with almost no extreme
saturation. This is consistent with local bidirectional HF calibration
rather than global DSM HF amplification.

This is an early diagnostic result only. It is not a final superiority
claim and does not replace the historical Stage1/Stage2 experiments.

## Next

1. F0@2k vs P1@2k class-wise Precision/Recall/F1/IoU.
2. P1@2k Test4 scale distribution conditioned on semantic class.
3. If mechanism audit is sensible, extend deterministic F0/P1 pair to
   an intermediate training horizon before committing to the full run.
