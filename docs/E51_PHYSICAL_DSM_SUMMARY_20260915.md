# E51 Physical-DSM Frequency Calibration — Stage Summary

Date: 2026-09-15

## 1. Research question

Investigate whether frequency modeling for Optical + DSM semantic segmentation
should use modality-specific coordinate systems under changes in ground sampling
distance (GSD).

Current candidate:

- Optical: pixel-frequency coordinate.
- DSM: physical-frequency coordinate.

The main hypothesis is that DSM geometry is more naturally tied to physical
spatial scale, while optical appearance and texture remain more
sampling-dependent.

## 2. E51-A / E51-A2 mechanism audit

Dataset:
Potsdam TRAIN18 only; the formal TEST6 split was not used for this mechanism audit.

Native GSD:
5 cm.

Synthetic GSD:
6, 7, 8, 9, 10, and 12 cm.

Main observations:

1. DSM frequency profiles became substantially more stable when represented in
   physical coordinates.

2. Optical profiles did not show the same behavior. Applying physical
   normalization to Optical could worsen profile consistency.

3. The hybrid configuration

   Optical = pixel-frequency
   DSM     = physical-frequency

   was more stable than the all-pixel PP configuration across all six shifted
   GSD settings in the dense audit.

4. Therefore, a single universal physical-frequency coordinate should not be
   applied blindly to both modalities.

## 3. E51-B PH model

PH uses:

- Optical: original fixed pixel bands [3, 7, 15, 31].
- DSM: per-sample canonical physical-coordinate decomposition.
- Router: modality-specific static router inherited from R4.

Training augmentation scale s corresponds approximately to:

effective input GSD = 0.05 / s meters.

At S0, DSM features are resized to the canonical native physical grid before
the same [3, 7, 15, 31] decomposition is applied. Bands are then resized back
to the original S0 resolution.

At s = 1, the PH DSM decomposition is exactly identical to the original R4
pixel-coordinate decomposition.

## 4. Engineering gates

All gates passed:

- Gate 1: s=1 physical DSM bands exactly equal original R4 bands.
- Gate 2: zero static logits preserve exact identity reconstruction.
- Gate 3: different samples in one batch use different canonical grids.
- Gate 4: backward propagation through resize/decompose/resize is valid.

## 5. PH training trajectory

Potsdam NB mIoU_fg5:

| Step | PH |
|---:|---:|
| 2k | 79.3174 |
| 4k | 83.5771 |
| 6k | 80.6574 |

Best checkpoint:
4k.

The 4k -> 6k degradation was not caused by static-router collapse.
DSM static weights remained close to uniform at both checkpoints.

## 6. Strict same-step PP4k vs PH4k

Primary comparison:

| GSD | PP4k NB mIoU | PH4k NB mIoU | PH absolute gain |
|---:|---:|---:|---:|
| 5 cm | 82.3889 | 83.5771 | +1.1882 pp |
| 6 cm | 81.4342 | 82.7585 | +1.3244 pp |
| 7 cm | 80.0096 | 81.5495 | +1.5399 pp |
| 8 cm | 78.3468 | 80.3240 | +1.9771 pp |
| 9 cm | 76.7621 | 78.8779 | +2.1157 pp |
| 10 cm | 75.0145 | 77.2999 | +2.2854 pp |
| 12 cm | 71.9161 | 74.0833 | +2.1672 pp |

Relative robustness advantage of PH versus PP:

| GSD | PH robustness advantage |
|---:|---:|
| 6 cm | +0.1361 pp |
| 7 cm | +0.3517 pp |
| 8 cm | +0.7889 pp |
| 9 cm | +0.9275 pp |
| 10 cm | +1.0971 pp |
| 12 cm | +0.9790 pp |

Thus, under equal 4k training budget, PH improves both native accuracy and
robustness to synthetic GSD shifts.

## 7. Important negative result: test-time GSD injection

Three PH4k evaluation modes were compared:

1. correct physical scale;
2. forced scale = 1;
3. deliberately wrong/reversed scale.

The three produced nearly identical segmentation results.

Therefore, the current evidence does NOT support the claim that explicitly
injecting the correct test-time GSD is responsible for the robustness gain.

The evidence instead supports:

training-time physical DSM calibration
    ->
different learned representation / training dynamics
    ->
better native accuracy and GSD robustness.

The current PH static router is close to identity, so the benefit should not
be described as strong test-time dynamic band routing.

## 8. PP10k vs PH4k comparison

PP10k is more mature than PH4k and shows stronger absolute robustness than
PH4k. Because the optimization budgets differ, this comparison is considered
preliminary only.

The strict primary result is PP4k vs PH4k.

## 9. Current interpretation

Supported:

- Fixed pixel-frequency DSM modeling is sensitive to changes in physical scale.
- DSM benefits from physical-scale-consistent frequency treatment during training.
- Optical and DSM should not necessarily share the same frequency coordinate.
- Same-step PH4k improves native accuracy and synthetic-GSD robustness over PP4k.

Not yet supported:

- Test-time GSD injection materially improves segmentation.
- PH is robust across random seeds.
- PH generalizes across datasets without further validation.
- Physical DSM calibration is universally optimal for every modality or task.

## 10. Next experiments

Priority:

1. Per-class robustness analysis:
   Impervious, Building, LowVegetation, Tree, Car.

2. Per-tile paired analysis on the six Potsdam TEST tiles.

3. Repeat PP4k / PH4k with additional random seeds.

4. Segmentation-level PP / PH / HH / HP modality-coordinate ablation.

5. Fixed-field-of-view GSD degradation protocol to separate sampling-density
   degradation from physical field-of-view changes.

## 11. Key implementation / result locations

Models:
- model/vitcross_seg_modeling_adaptive_multiband.py
- model/vitcross_seg_modeling_adaptive_multiband_variants.py
- model/vitcross_seg_modeling_physical_dsm.py

Training:
- scripts/train_potsdam_multiband_variants.py
- scripts/train_potsdam_physical_dsm_6k.py
- scripts/train_potsdam_r4_repro4k.py

Mechanism audits:
- scripts/audit_crossdataset_physical_frequency.py
- scripts/audit_e51a_synthetic_gsd_physical_frequency.py
- scripts/audit_e51a2_dense_gsd_sweep.py
- scripts/analyze_e51a_hybrid_modality_scale.py
- scripts/analyze_e51a2_dense_hybrid.py

E51-B evaluation:
- scripts/eval_e51b_gsd_robustness.py
- scripts/eval_e51b_gsd_scale1.py
- scripts/eval_e51b_gsd_wrongscale.py
- scripts/eval_e51b_gsd_ph6k.py
- scripts/eval_e51b_same_step_pp4k_ph4k.py
- scripts/run_e51b_overnight_20260914.sh

Primary compact result:
- records/E51B_OVERNIGHT_SUMMARY_20260914.txt
