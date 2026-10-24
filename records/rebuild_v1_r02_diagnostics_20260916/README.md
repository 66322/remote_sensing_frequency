# REBUILD_V1 R02 diagnostics — 2026-09-16

Branch: `rebuild-v1-protocol-20260915`

This record summarizes the completed R02 12k development-only diagnostics. Potsdam historical TEST6 was not loaded for these checks.

## 1. R02 12k clean validation reference

R02 is the clean dual-modal F0 baseline trained on REBUILD_V1 Train16 and selected on Val2 (`3_11`, `5_10`).

At the completed 12k schedule:

- FullGT mIoU_fg5: **80.9842%**
- NoBoundary mIoU_fg5: **85.4135%**
- best validation step: **12000**
- `test6_loaded = false`

The best validation score occurring at the schedule endpoint is why 12k is not yet frozen as the formal R01–R04 budget. A fresh complete 16k pilot is the next convergence check.

## 2. Val2 corruption screen

Checkpoint:

`runs/rebuild_v1/R02_dual_f0_seed42_sched12000_stop12000/best_model.pth`

Protocol:

- Val2 only: `3_11`, `5_10`
- patch 512
- stride 256
- inference batch 8
- labels unchanged
- blur5 = 5x5 mean filter with reflect boundary handling
- down2 = antialiased bilinear x2 downsample followed by bilinear restoration

### Dataset-level mIoU_fg5

| Condition | FullGT | Full drop (pp) | NoBoundary | NB drop (pp) |
|---|---:|---:|---:|---:|
| clean | 80.9842 | 0.0000 | 85.4135 | 0.0000 |
| DSM blur5 | 80.6571 | 0.3272 | 85.0769 | 0.3365 |
| DSM down2 | 80.7346 | 0.2496 | 85.1568 | 0.2567 |
| DSM zero | 47.9901 | 32.9941 | 50.6945 | 34.7190 |
| Optical blur5 | 79.6024 | 1.3819 | 84.2223 | 1.1912 |
| Optical down2 | 80.2620 | 0.7223 | 84.8649 | 0.5485 |

### Interpretation

Supported observations:

1. Mild DSM detail degradation (`blur5`, `down2`) causes only a small drop on this R02 checkpoint.
2. Mild Optical degradation causes a larger drop than the matched mild DSM degradation conditions.
3. Complete DSM removal (`DSM zero`) causes a catastrophic drop, showing that the trained dual-modal model strongly depends on the DSM branch under this artificial missing-modality condition.

Do **not** interpret this as evidence of harmful fusion yet. Harmful fusion requires a matched, genuinely trained R01 Optical-only control and Fusion Gain under the same input condition.

The DSM-zero result is an artificial missing-modality diagnostic, not evidence about real DSM nodata.

## 3. Resume exactness audit

Protocol:

- reference: uninterrupted 40 optimizer steps
- resumed path: 20 steps -> save model/optimizer/RNG -> reload -> restore RNG -> 20 steps
- scheduler total steps: 12000
- same Train16 sampler and seed 42

Result:

- `loss_exact = true`
- `max_abs_loss_diff = 0.0`
- `model_state_exact = true`
- `optimizer_state_exact = true`
- overall `pass = true`
- temporary resume checkpoint removed after the audit

Reference and resumed model SHA256:

`9a6c1eacbb13cd5c0fe7fb9de7a68877dc566b335023ec3e50af2becce4fc486`

Reference and resumed optimizer SHA256:

`8d533113d68a8831dab2f7d0ad4a0d6f0b81087f400c6e6e1065ab9e1d9b0200`

Therefore the current REBUILD_V1 save/load/RNG restoration path is exact for this deterministic audit.

## 4. Decision

- R02 12k training: **PASS**
- R02 corruption diagnostic: **COMPLETE**
- REBUILD_V1 resume exactness: **EXACT PASS**
- freeze 12k as formal budget: **NO, not yet**
- next GPU budget test: **fresh complete R02 16k schedule**
- next framework work in parallel: prepare and smoke-test a genuinely trained R01 Optical-only path before formal R01–R04 execution.
