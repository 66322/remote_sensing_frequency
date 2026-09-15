# REBUILD_V1 execution protocol — 2026-09-15

Base commit: `7209d99af3dc8d7bb43795d2759022ec162b5435`

This document freezes the next-stage decision protocol. Existing E50/E51 and earlier results remain historical/development evidence. New formal comparisons must follow REBUILD_V1 rather than extending the historical scripts ad hoc.

## 1. Immediate objective

Do not design HF-v3, PH+Rare30, a new shallow-detail block, or another decoder-frequency block yet.

First answer two questions under a unified protocol:

1. Does DSM provide positive clean-data fusion gain but become harmful when DSM quality degrades?
2. Does physically consistent DSM-frequency treatment provide a benefit beyond generic resampling/interpolation regularization?

The first formal training batch is therefore R01–R04. Physical-frequency experiments continue only if their controls pass the gates below.

## 2. Historical evidence status

Historical/development evidence includes:

- Vaihingen prefusion DSM HF calibration.
- Cross-modal HF Reliability and Rare30.
- Potsdam baseline / HF Reliability / HF Reliability+Rare30 10k runs.
- E50 reliability diagnostics.
- E51 physical-DSM audits and PP4k/PH4k comparisons.

These remain useful for motivation and hypothesis formation, but the repeatedly used Potsdam TEST6 is not a sealed final test set.

## 3. E51 protocol split

Two different tests must be reported separately.

### 3.1 Grid-GSD shift

Historical E51-B protocol:

- Optical, DSM, FullGT and NoBoundary GT are jointly resampled to a new grid.
- Sliding-window inference runs on that new grid.
- PH receives the actual grid scale.

This changes sampling grid spacing and window physical coverage.

### 3.2 Fixed-grid information degradation

New protocol:

- Start from the native grid.
- Apply anti-aliased downsampling to Optical/DSM as specified.
- Restore the degraded input to the original H×W grid.
- Keep FullGT and NoBoundary GT unchanged.
- Keep output grid and sliding-window coordinates unchanged.
- For PH, keep the native grid scale (`sample_scale = 1.0` for native Potsdam).

This is an information-loss / detail-loss experiment on the native grid. Do not relabel the restored grid as a new GSD.

Report the two protocols separately.

## 4. E51 historical close-out before new training

No retraining is required for the following work, although some items require new inference.

1. Extract per-class PP4k/PH4k curves from the existing E51 summary JSON.
2. Inventory whether per-tile predictions or per-tile confusion matrices were retained.
3. If not retained, rerun inference to obtain paired per-tile PP4k/PH4k results.
4. Run the fixed-grid information-degradation protocol.
5. Preserve dataset-level metrics from the accumulated confusion matrix as the primary result.
6. Per-tile metrics are secondary paired-distribution evidence only.

Per-tile mIoU rule must be fixed in advance: a class with zero GT/prediction union on a tile is unavailable for that tile-level class mean; record the number of available classes. Do not replace dataset-level accumulated-CM mIoU with the mean of tile mIoUs.

## 5. Correct interpretation of existing PH evidence

Supported wording:

> The current PH4k checkpoint is nearly insensitive to the tested correct, fixed and deliberately wrong inference-scale settings. Existing evidence therefore does not support attributing PH4k's gain to correct test-time GSD injection.

Do not claim that GSD information is universally useless.

PH 4k→6k degradation is an observed checkpoint result. It is not yet identified as overfitting, instability, or a scheduler effect. The historical 160k scheduler is a confound that must be removed in REBUILD_V1.

## 6. Physical-frequency interpolation control

PP/PH/HP/HH alone is insufficient because PH adds scale-dependent resampling.

Before treating physical correspondence as a mechanism, include:

- `PH-correct`: scale metadata correctly matched to each sample.
- `PH-shuffled`: same architecture, number of resizes, interpolation, frequency decomposition, optimizer and augmentation, but scale metadata is deterministically shuffled among samples using an independent RNG.

Interpretation gate:

- `PH-correct > PH-shuffled >≈ PP`: supports a contribution from correct physical correspondence.
- `PH-correct ≈ PH-shuffled > PP`: interpret mainly as resampling/training regularization; do not claim physical correspondence as the cause.
- no stable gain: stop the physical-frequency route.

Only after this control is informative should PP/PH/HP/HH and multi-seed expansion become priority.

## 7. DSM preprocessing and corruption order

Freeze the initial synthetic-corruption order as:

`Raw DSM -> tile-wise min-max normalization -> crop/resize -> synthetic corruption -> network`

All compared models receive the exact same corrupted input realization.

Artificial missing DSM is implemented after normalization (e.g. selected regions or the full modality set to zero) and must be called synthetic/artificial modality missing, not real DSM nodata.

Do not corrupt raw DSM and then recompute min-max for the first-round tests, because that would mix local corruption with global rescaling.

## 8. REBUILD_V1 training framework requirements

New code must separate:

- `scheduler_total_steps`: defines the complete learning-rate schedule.
- `stop_at_step`: early stop / smoke / resume boundary only.

Do not use the first N steps of a 160k schedule as a formal N-step protocol.

Required configurable fields include:

- root/data/pretrain paths;
- train/validation/final-test manifests;
- seed;
- run directory;
- model variant;
- augmentation policy;
- scheduler total steps;
- stop step;
- optimizer and LR multipliers;
- checkpoint/evaluation interval.

Save model, optimizer, scheduler, AMP (if used), Python/NumPy/Torch/CUDA RNG state and exact split/config metadata.

## 9. Validation and test boundaries

Potsdam TEST6 and previously used Vaihingen test tiles remain historical/development references because they have already influenced model decisions.

REBUILD_V1 must introduce a validation entry used for checkpoint/model selection. The final independent external dataset/test scene should be screened and sealed early rather than selected after method development.

External-data screening records only:

- Optical channels/bands;
- DSM/nDSM definition and quality;
- GSD;
- semantic class mapping;
- geographic independence;
- official split availability;
- license.

Do not inspect final external performance to choose the method.

## 10. First formal training matrix

Use Potsdam development data first, ordinary random sampling, no Rare30, no new boundary loss, no TTA and no post-processing differences.

| ID | Model | Training treatment | Question |
|---|---|---|---|
| R01 | true Optical-only | standard augmentation | What can Optical alone do? |
| R02 | matched Optical+DSM baseline | standard augmentation | What is clean DSM fusion gain? |
| R03 | matched dual baseline | quality corruption Q | How much is solved by simple corruption training? |
| R04 | matched dual baseline | modality dropout D | How much is solved by simple missing-modality training? |
| R05 | matched dual baseline | Q+D | Run only if R03/R04 leave a meaningful gap |

Optical-only must be a genuinely trained single-modality path. Testing a dual model with DSM zeroed is only a missing-input diagnostic.

## 11. Initial Q and D definitions

Q initial engineering policy (freeze for the first comparison; do not tune ratios yet):

- 70% clean;
- 15% Optical degradation;
- 15% DSM degradation;
- within a degraded branch: blur5 vs down2 at 50/50.

`blur5` means 5×5 mean filtering with the documented boundary handling, not Gaussian blur.

`down2` means anti-aliased bilinear downsample followed by bilinear restoration to the original grid; labels are unchanged.

D initial policy:

- 80% clean;
- 10% Optical full-modality dropout;
- 10% DSM full-modality dropout;
- do not drop both simultaneously in the first version.

Q+D, if run: draw D first; apply Q only if D did not occur. Log realized probabilities.

## 12. Fairness under Optical corruption

DSM-corruption conditions provide the cleanest first Fusion-Gain comparison because the Optical-only and dual models receive the same clean Optical input.

If Optical corruption becomes part of the final main table, train a matched Optical-only augmentation control (e.g. `R01-Qopt`). Do not compare a dual model trained with Optical corruption against an Optical-only model that never saw that augmentation and attribute the difference solely to fusion.

## 13. Training budget

20k steps, LR, warmup and evaluation interval are candidates, not frozen facts.

Run a baseline budget pilot first. Choose the complete schedule before formal R01–R04. If the complete schedule is changed to 12k (or another value), rerun all formal comparisons on that same complete schedule. The first 12k steps of a 20k schedule are not equivalent to a complete 12k schedule.

Candidate starting point for pilot only:

- crop 512;
- effective batch 16;
- AdamW;
- backbone LR 6e-5;
- matched new-module LR multiplier 10× where applicable;
- random scale [0.5, 2.0];
- seed 42 for screening;
- additional seeds 17 and 2026 for retained configurations.

## 14. Required evaluation quantities

For every retained model/condition report together:

1. clean absolute accuracy;
2. corrupted absolute accuracy;
3. corruption drop = clean − corrupted;
4. Fusion Gain = matched dual − matched Optical-only under the same input condition;
5. FullGT and NoBoundary metrics;
6. per-class IoU and raw confusion matrices.

Do not rank robustness by corruption drop alone.

## 15. Go / No-Go gates

### G1 — harmful fusion

If R02 > R01 on clean input but Fusion Gain becomes negative under controlled DSM corruption, harmful fusion is supported as a research problem.

### G2 — simple robustness baseline

If R03/R04/R05 remove most of the harmful-fusion gap, they become the strong baseline. Do not build a complex reliability module merely to reproduce the same gain.

### G3 — selective DSM route

Only if G1 holds and simple robustness training leaves a stable residual gap, test:

- M1: Optical base path + static DSM residual correction;
- M2: same path + local adaptive DSM residual coefficient.

M1/M2 use the same augmentation as the strongest simple baseline.

### G4 — physical-frequency route

Continue only if the fixed-grid evaluation retains a signal and, under the new training protocol, `PH-correct` is stably better than PP and meaningfully better than `PH-shuffled`.

Then expand to PP/PH/HP/HH and multiple seeds.

If both selective-DSM and physical-frequency routes fail the gates, consider DSM teacher→Optical student distillation or a separately evidenced small-object problem instead of adding modules.

## 16. Immediate execution order

Parallel preparation:

1. freeze historical remote state at base commit and record server-side `git status` before syncing;
2. extract E51 per-class curves from existing JSON;
3. inventory checkpoints, prediction caches and per-tile outputs;
4. document the known E51 metadata naming error;
5. build the unified config/validation/Optical-only framework;
6. screen and seal a plausible external final test dataset early.

First GPU work:

1. clean reproduction gates;
2. representative corruption inference on existing baseline/HF/HF+Rare30 checkpoints;
3. baseline budget pilot under REBUILD_V1;
4. lock the complete schedule;
5. R01 -> R02 -> R03 -> R04;
6. let the Go/No-Go gates decide the next branch.

## 17. Known E51 metadata erratum

`records/e51b_gsd_same_step_pp4k_ph4k_20260914/summary.json` currently contains a stale `comparison_note` referring to PP10k vs PH4k although the stored result keys/checkpoint steps are PP4k/PH4k.

The generator `scripts/eval_e51b_same_step_pp4k_ph4k.py` also uses stale output field names `PP10k_nb_mIoU` and `PP10k_drop_pp` in the paired CSV section while it actually loads PP4k.

Until the historical artifact is regenerated or safely patched, treat PP4k/PH4k as the authoritative interpretation for this same-step result.
