# E51-B same-step PP4k vs PH4k: per-class close-out

Date: 2026-09-15

Source experiment: `records/e51b_gsd_same_step_pp4k_ph4k_20260914/summary.json`

Comparison: PP4k vs PH4k, both checkpoint step 4000. This is historical/development evidence on the repeatedly used Potsdam TEST6 and is **not** a sealed final test.

## Dataset-level NoBoundary fg5 result

| grid-GSD (cm) | PP4k mIoU_fg5 | PH4k mIoU_fg5 | PH-PP (pp) |
|---:|---:|---:|---:|
| 5 | 82.3889 | 83.5771 | +1.1882 |
| 6 | 81.4342 | 82.7585 | +1.3244 |
| 7 | 80.0096 | 81.5495 | +1.5400 |
| 8 | 78.3468 | 80.3240 | +1.9771 |
| 9 | 76.7621 | 78.8779 | +2.1157 |
| 10 | 75.0145 | 77.2999 | +2.2854 |
| 12 | 71.9161 | 74.0833 | +2.1672 |

PH4k is above PP4k at every tested grid-GSD in the same-step comparison. The absolute PH-PP gap generally grows as the grid is coarsened, peaking at 10 cm in this sweep.

## NoBoundary per-class IoU gain (PH4k - PP4k, percentage points)

| grid-GSD (cm) | Impervious | Building | LowVegetation | Tree | Car | Clutter |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | +0.4695 | +0.3789 | +2.2273 | +1.8186 | +1.0469 | +20.5932 |
| 6 | +0.7161 | +0.2907 | +2.3093 | +1.9890 | +1.3167 | +20.9974 |
| 7 | +0.8742 | +0.2222 | +2.8023 | +2.2046 | +1.5966 | +22.7820 |
| 8 | +1.1361 | +0.3380 | +3.9424 | +2.4295 | +2.0396 | +23.4430 |
| 9 | +0.8227 | +0.3047 | +4.7173 | +2.1159 | +2.6179 | +21.5459 |
| 10 | +0.7141 | +0.3245 | +5.2138 | +2.1172 | +3.0572 | +20.1312 |
| 12 | +0.7204 | +0.0220 | +5.5418 | +1.8583 | +2.6937 | +17.5101 |

## Interpretation

1. The fg5 improvement is **not** explained only by the very large Clutter change. All five foreground classes have positive PH4k-PP4k IoU differences at every tested grid-GSD.
2. LowVegetation is the strongest foreground contributor and its gain expands markedly under coarser grids: +2.23 pp at 5 cm to +5.54 pp at 12 cm (NoBoundary).
3. Car gain also grows under moderate/strong coarsening, reaching +3.06 pp at 10 cm.
4. Tree gain is consistently positive (~+1.82 to +2.43 pp in this sweep).
5. Impervious gain is smaller but consistently positive.
6. Building gain is small and is almost zero at 12 cm (+0.02 pp), so PH does not provide a uniform class-independent margin.
7. Clutter changes are extremely large, but Clutter is excluded from fg5. It must be reported separately and should not be used as evidence for the foreground mechanism.

These findings support **consistency of the observed same-step PH advantage across foreground classes**, especially LowVegetation and Car. They do **not** establish that correct physical scale correspondence is the causal mechanism. Existing wrong-scale inference checks already show that PH4k is nearly insensitive to the tested inference scale settings. The next causal diagnostic is therefore the fixed-grid information-degradation evaluation, followed later (if the signal survives) by PH-correct vs PH-shuffled under the rebuilt training protocol.

## Next gate

Run the fixed-grid information-degradation evaluator on the same PP4k/PH4k checkpoints:

- labels unchanged;
- output/sliding-window grid unchanged;
- anti-aliased input downsample followed by restoration to the original HxW;
- native Potsdam PH inference scale fixed at 1.0;
- report accumulated dataset confusion-matrix metrics as primary;
- save per-tile paired metrics as secondary evidence.

Do not call this fixed-grid test a new GSD. It is an input information-loss test on the native grid.
