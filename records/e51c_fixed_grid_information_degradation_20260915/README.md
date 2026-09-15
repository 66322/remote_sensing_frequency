# E51-C fixed-grid information degradation — joint x2 close-out

Date: 2026-09-15

Checkpoints: PP4k vs PH4k, both step 4000.
Dataset: historical/development Potsdam TEST6 (not a sealed final test).

## Protocol

This experiment is **not** a new-GSD test.

For `information_loss_factor = 2.0`:

- Optical and DSM are anti-aliased, downsampled by x2, then bilinearly restored to the original native grid.
- FullGT and NoBoundary GT are unchanged.
- Output grid and sliding-window coordinates are unchanged.
- Native Potsdam grid remains 5 cm.
- PH receives inference scale `1.0` at every factor.
- Historical sliding-window inference is preserved (`patch=512`, `stride=64`, `infer_batch=8`).

The x1.0 native reproduction gate matched the historical metrics exactly for both PP4k and PH4k (`max_diff = 0`).

## Dataset-level results

### FullGT

| factor | PP4k mIoU_fg5 | PH4k mIoU_fg5 | PH-PP (pp) | PP drop from clean (pp) | PH drop from clean (pp) | PH robustness advantage (pp) |
|---:|---:|---:|---:|---:|---:|---:|
| 1.0 | 77.4655 | 78.5089 | +1.0435 | 0.0000 | 0.0000 | 0.0000 |
| 2.0 | 77.2880 | 78.3167 | +1.0287 | 0.1775 | 0.1923 | -0.0148 |

### NoBoundary

| factor | PP4k mIoU_fg5 | PH4k mIoU_fg5 | PH-PP (pp) | PP drop from clean (pp) | PH drop from clean (pp) | PH robustness advantage (pp) |
|---:|---:|---:|---:|---:|---:|---:|
| 1.0 | 82.3889 | 83.5771 | +1.1882 | 0.0000 | 0.0000 | 0.0000 |
| 2.0 | 82.2682 | 83.4258 | +1.1576 | 0.1207 | 0.1513 | -0.0306 |

## Paired per-tile result

At x2.0, PH4k is above PP4k on all six TEST6 tiles for both FullGT and NoBoundary.

NoBoundary PH4k-PP4k mIoU_fg5 differences at x2.0:

- `2_11`: +0.9540 pp
- `3_10`: +1.2545 pp
- `4_10`: +1.3322 pp
- `5_11`: +0.8933 pp
- `6_11`: +1.5394 pp
- `7_12`: +0.5528 pp

This supports distributional consistency of the absolute PH4k>PP4k margin across tiles, but does not identify the cause.

## Per-class result at x2.0

NoBoundary PH4k-PP4k IoU differences:

- Impervious: +0.5151 pp
- Building: +0.4966 pp
- LowVegetation: +2.2399 pp
- Tree: +1.4332 pp
- Car: +1.1034 pp
- Clutter: +22.7338 pp

All five foreground classes remain positive. As in E51-B, LowVegetation is the largest foreground contributor. Clutter remains very large but is excluded from fg5 and must not be used as the main mechanism evidence.

## Interpretation

The fixed-grid x2 result **does not show a PH robustness advantage to generic joint information loss**.

The key observation is that both models barely degrade under the x2 downsample-restore perturbation:

- NoBoundary PP4k drop: only 0.1207 pp.
- NoBoundary PH4k drop: only 0.1513 pp.
- PH robustness advantage: -0.0306 pp (slightly worse, effectively near zero at this screening scale).

At the same time, the absolute PH4k-PP4k gap is almost unchanged:

- clean: +1.1882 pp
- fixed-grid x2: +1.1576 pp

Therefore the x2 fixed-grid result supports **persistence of the pre-existing PH4k accuracy margin**, not improved robustness to joint information loss.

This materially weakens an interpretation that the growing PH advantage in historical Grid-GSD tests was simply due to better tolerance of generic blur/downsample information loss. The historical Grid-GSD protocol changes more than information content: it also changes the sampling grid and the physical coverage of each fixed 512-pixel window.

However, this joint perturbation degrades Optical and DSM together. Since the physical-frequency hypothesis specifically concerns DSM treatment, one attribution gap remains.

## Decision gate

Do **not** run the entire factor sweep yet.

Next run only one additional condition:

- `modality=dsm`
- `information_loss_factor=2.0`
- same PP4k/PH4k checkpoints
- same stride=64 formal geometry
- same native PH inference scale=1.0

Use the existing x1.0 joint run as the canonical clean reference because factor=1.0 performs no modality-specific degradation and is mathematically identical across `joint`, `dsm`, and `optical` modes.

If DSM-only x2 still shows essentially identical PP/PH drops and a stable absolute PH margin, stop expanding E51-C factors and move to the rebuilt-training causal control (`PH-correct` vs `PH-shuffled`).

If DSM-only x2 produces a materially different robustness pattern, then add stronger DSM-only factors before deciding whether the physical-frequency route deserves more work.
