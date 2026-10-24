# E51-C fixed-grid information degradation — close-out

Date: 2026-09-15

Checkpoints: PP4k vs PH4k, both step 4000.
Dataset: historical/development Potsdam TEST6 (not a sealed final test).

## Protocol

This experiment is **not** a new-GSD test.

For `information_loss_factor = 2.0`:

- selected input modalities are anti-aliased, downsampled by x2, then bilinearly restored to the original native grid;
- FullGT and NoBoundary GT are unchanged;
- output grid and sliding-window coordinates are unchanged;
- native Potsdam grid remains 5 cm;
- PH receives inference scale `1.0` at every factor;
- historical inference geometry is preserved (`patch=512`, `stride=64`, `infer_batch=8`, FP32).

The x1.0 native reproduction gate matched historical PP4k and PH4k metrics exactly (`max_diff = 0`).

The clean x1.0 joint run is used as the canonical clean reference for all modality-specific x2 comparisons because factor=1.0 performs no degradation and is mathematically identical across `joint`, `dsm`, and `optical` modes.

## Dataset-level results

### NoBoundary fg5

| condition | PP4k mIoU_fg5 | PH4k mIoU_fg5 | PH-PP (pp) | PP drop from clean (pp) | PH drop from clean (pp) | PH robustness advantage (pp) |
|---|---:|---:|---:|---:|---:|---:|
| clean x1.0 | 82.3889 | 83.5771 | +1.1882 | 0.0000 | 0.0000 | 0.0000 |
| joint x2.0 | 82.2682 | 83.4258 | +1.1576 | +0.1207 | +0.1513 | -0.0306 |
| DSM-only x2.0 | 82.5376 | 83.6246 | +1.0870 | -0.1488 | -0.0475 | -0.1012 |

Negative `drop from clean` means the degraded condition performed slightly **better** than clean.

### FullGT fg5

| condition | PP4k mIoU_fg5 | PH4k mIoU_fg5 | PH-PP (pp) | PP drop from clean (pp) | PH drop from clean (pp) | PH robustness advantage (pp) |
|---|---:|---:|---:|---:|---:|---:|
| clean x1.0 | 77.4655 | 78.5089 | +1.0435 | 0.0000 | 0.0000 | 0.0000 |
| joint x2.0 | 77.2880 | 78.3167 | +1.0287 | +0.1775 | +0.1923 | -0.0148 |
| DSM-only x2.0 | 77.6060 | 78.5593 | +0.9533 | -0.1405 | -0.0503 | -0.0902 |

## Joint x2 result

Joint Optical+DSM x2 information loss barely changes either model.

NoBoundary:

- PP4k drop: +0.1207 pp;
- PH4k drop: +0.1513 pp;
- PH robustness advantage: -0.0306 pp;
- PH-PP absolute gap changes from +1.1882 pp clean to +1.1576 pp.

PH4k remains above PP4k on all six TEST6 tiles and all five foreground classes, but the result supports persistence of the pre-existing PH accuracy margin rather than superior robustness to generic joint information loss.

## DSM-only x2 result

DSM-only x2 closes the remaining attribution gap from the joint perturbation.

NoBoundary:

- PP4k improves by +0.1488 pp relative to clean;
- PH4k improves by +0.0475 pp relative to clean;
- therefore `PH robustness advantage = -0.1012 pp`;
- PH-PP gap narrows from +1.1882 pp clean to +1.0870 pp.

FullGT shows the same direction:

- PP4k improves by +0.1405 pp;
- PH4k improves by +0.0503 pp;
- PH robustness advantage = -0.0902 pp;
- PH-PP gap narrows from +1.0435 pp to +0.9533 pp.

Thus DSM-only smoothing/downsample-restore does **not** reveal a PH-specific robustness advantage. If anything, PP4k benefits slightly more from this perturbation.

This small improvement after DSM smoothing may indicate that some fine-scale DSM variation behaves like nuisance/noise for both checkpoints, but E51-C alone does not establish that mechanism. Do not claim denoising causality from this result.

## Relation to historical Grid-GSD result

Historical Grid-GSD E51-B showed a growing PH4k-PP4k NoBoundary fg5 gap as the entire raster grid became coarser:

- 5 cm: +1.1882 pp;
- 8 cm: +1.9771 pp;
- 10 cm: +2.2854 pp;
- 12 cm: +2.1672 pp.

By contrast, fixed-grid information loss does not reproduce that growth:

- clean: +1.1882 pp;
- joint x2: +1.1576 pp;
- DSM-only x2: +1.0870 pp.

Therefore the historical growth cannot be explained simply as PH being more tolerant to blur/downsample information loss. The Grid-GSD protocol also changes sampling-grid spacing and the physical area covered by a fixed 512-pixel inference window, among other consequences.

## Fast-path note

A diagnostic GPU-resident inference path was benchmarked with the formal geometry unchanged (`512/64/batch8/FP32`). On a 2048x2048 benchmark region it produced zero final-label differences for both PP4k and PH4k while improving speed by approximately 1.22-1.25x.

DSM-only x2 was run with that exact-gated diagnostic fast path and took about 844.2 s per model. Historical/reference results remain the frozen formal reference. If DSM-only x2 is later promoted to a publication-critical final table, rerun the retained condition once with the original reference path for whole-TEST6 confirmation.

## E51-C decision

**Stop E51-C factor expansion.**

The fixed-grid tests do not support a PH-specific robustness mechanism:

1. joint x2: both models barely degrade and PH has essentially zero robustness advantage;
2. DSM-only x2: both models improve slightly, with PP improving more;
3. the absolute PH4k advantage remains real and spatially/class-wise consistent, but E51-C does not identify its cause;
4. earlier wrong/fixed-scale inference tests also showed PH4k to be nearly insensitive to tested inference-scale settings.

Do not spend additional compute on 1.2/1.4/1.6/1.8/2.4 fixed-grid sweeps for these historical checkpoints.

## Next research priority

Return to the frozen REBUILD_V1 causal protocol rather than extending historical PH4k diagnostics.

Primary priority:

1. build/finalize the unified REBUILD_V1 training framework;
2. run a baseline budget/scheduler pilot;
3. freeze the complete schedule;
4. train R01 true Optical-only and R02 matched clean Optical+DSM baseline;
5. test controlled DSM corruption to determine whether harmful fusion actually exists;
6. then train R03 quality-corruption and R04 modality-dropout baselines.

Physical-frequency work is now a secondary branch. If retained, its next meaningful test is **new-training `PH-correct` vs `PH-shuffled`**, where all architecture/resampling/interpolation/training details are matched and only the correctness of physical-scale correspondence differs. Do not use more historical inference sweeps as a substitute for that causal control.
