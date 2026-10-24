# REBUILD_V1 core matrix — completed 2026-09-17

Status: complete
Timezone: UTC+08:00
Execution commit on server: `3e5cff755316d4c14b170a60a012c26555c9fbbf`
Queue completion: `2026-09-17T11:04:42+08:00`
Historical TEST6 loaded during training/selection: false

## Purpose

The core matrix was designed to answer four questions before inventing a new fusion module:

1. Does clean Optical+DSM fusion outperform a matched true Optical-only model?
2. Can DSM degradation turn positive fusion gain into negative fusion gain?
3. How much of degraded-modality robustness is solved by ordinary quality-corruption training?
4. How much of missing-modality robustness is solved by ordinary modality-dropout training?

The experiments use the frozen Train16/Val2 split, seed42, complete 16k schedule, and Val2 NoBoundary mIoU_fg5 checkpoint selection.

## Core clean results

| Model | Meaning | FullGT mIoU_fg5 | NB mIoU_fg5 | Best step |
|---|---|---:|---:|---:|
| R01 | true Optical-only | 80.6883 | 85.3713 | 10000 |
| R02 | clean Optical+DSM dual F0 | 81.8483 | 86.2016 | 13000 |
| R03 | R02 architecture + quality-corruption training | 82.1069 | 86.5251 | 14000 |
| R04 | R02 architecture + modality-dropout training | 81.6042 | 85.9818 | best checkpoint used by evaluator |

Clean system-level Fusion Gain relative to R01:

- R02: +1.1600 pp FullGT, +0.8303 pp NB.
- R03: +1.4186 pp FullGT, +1.1538 pp NB.
- R04: +0.9159 pp FullGT, +0.6105 pp NB.

Interpretation: clean multimodal systems provide a positive gain over the matched single-stream Optical-only baseline, but R01↔R02 is still a system-level comparison because R02 also contains extra dual-stream capacity and cross-modal computation.

## G1: conditional / harmful fusion diagnostic

Matched Fusion Gain is defined as:

`Fusion Gain(condition) = dual-modal mIoU_fg5 under the DSM condition - R01 Optical-only clean mIoU_fg5`

### R02 severity curve

| DSM condition | FullGT Fusion Gain (pp) | NB Fusion Gain (pp) |
|---|---:|---:|
| clean | +1.1600 | +0.8303 |
| down2 | +0.9701 | +0.6127 |
| down4 | +0.6667 | +0.3033 |
| down8 | -0.0111 | -0.4096 |
| zero | -34.6382 | -36.6016 |

Decision: **G1 is supported on the development Val2 screen.** Clean Fusion Gain is positive, while sufficiently degraded DSM (`down8`) makes Fusion Gain negative. Artificial DSM zero causes catastrophic negative Fusion Gain.

Scope limitation: this is development Val2 evidence, not a sealed external final test, and `dsm_zero` is an artificial missing-modality condition rather than a physical GSD condition.

## R03 quality-corruption training

Training distribution realized over 256000 samples:

- clean: 69.98125%
- Optical blur5: 7.50430%
- Optical down2: 7.54531%
- DSM blur5: 7.46875%
- DSM down2: 7.50039%

### R03 robustness

| DSM condition | FullGT mIoU_fg5 | NB mIoU_fg5 | NB Fusion Gain vs R01 (pp) |
|---|---:|---:|---:|
| clean | 82.1069 | 86.5251 | +1.1538 |
| down2 | 81.9937 | 86.3878 | +1.0166 |
| down4 | 81.7112 | 86.0985 | +0.7273 |
| down8 | 80.9568 | 85.2979 | -0.0734 |
| zero | 39.2449 | 41.2815 | -44.0897 |

Decision: ordinary quality-corruption training is a strong baseline for clean and mild/moderate degradation and even improves clean Val2 performance over R02, but it does **not** solve severe/missing DSM. Under DSM zero it is worse than R02 and far worse than R01.

Important implication: a new robustness method must compare against R03 for mild degradation; beating only clean R02 is insufficient.

## R04 modality-dropout training

Frozen training policy: 80% clean, 10% Optical dropout, 10% DSM dropout, never both simultaneously.

### R04 robustness

| DSM condition | FullGT mIoU_fg5 | NB mIoU_fg5 | NB Fusion Gain vs R01 (pp) |
|---|---:|---:|---:|
| clean | 81.6042 | 85.9818 | +0.6105 |
| down2 | 81.5705 | 85.9560 | +0.5848 |
| down4 | 81.4054 | 85.8095 | +0.4382 |
| down8 | 80.7021 | 85.0726 | -0.2986 |
| zero | 78.7059 | 83.1375 | -2.2338 |

Decision: modality dropout dramatically repairs the catastrophic DSM-zero failure while keeping clean cost small, but it still does not recover the true Optical-only fallback level.

Residual gap at DSM zero:

- R01 NB: 85.3713
- R04 NB with DSM zero: 83.1375
- residual gap: 2.2338 pp

This residual gap is the strongest current motivation for selective / reliability-aware DSM usage: under unreliable DSM, a robust multimodal model should approach the matched Optical-only fallback while preserving clean multimodal gain.

R04 under Optical zero remains very poor (NB mIoU_fg5 61.3945), so the trained system remains strongly Optical-dependent. This is not a DSM-only model result and should not be described as one.

## Route decisions after the core matrix

### Supported

1. **Conditional DSM utility / harmful fusion** is empirically supported on Val2: clean DSM helps, severe DSM degradation can make the dual system worse than true Optical-only.
2. **Simple training baselines are strong and necessary controls.** R03 handles mild degradation well; R04 handles full DSM missing much better than R02.
3. **A residual fallback gap remains.** R04 still fails to reach R01 under DSM zero, leaving room for a selective/reliability-aware mechanism.

### Not yet isolated

R01↔R02 does not isolate pure DSM-information value from extra dual-stream capacity. Add a matched `Optical+Optical` dual-stream capacity control before attributing the full clean gain to DSM itself.

### Next experimental priority

1. `C-OO`: Optical+Optical through the same dual-stream architecture as R02, to separate capacity/architecture effects from DSM-specific information.
2. If R02 still shows clear DSM-specific gain after C-OO, develop a selective/reliability-aware DSM mechanism whose target is:
   - preserve clean / mild DSM gain,
   - avoid negative Fusion Gain under severe degradation,
   - approach R01 when DSM is unusable,
   - outperform R03/R04 matched baselines.
3. In parallel, use R01/R02 compute profiles to decide whether lightweight DSM (`G-S`/`G-H`) is worth pursuing as an accuracy-compute route.
4. Do not launch R05 Q+D automatically unless the residual problem specifically requires it; R03 and R04 already reveal different failure regimes.

## Writing discipline

Do not claim:

- that DSM itself contributes the whole R02-R01 delta before the capacity control;
- that down8 is a real physical GSD condition;
- that DSM zero represents real nodata;
- that R03 solves missing modality;
- that R04 is modality-independent;
- that one seed proves random-seed stability.

Current results are seed42 screening/development evidence. Additional seeds should be reserved for the final retained method and key baselines.