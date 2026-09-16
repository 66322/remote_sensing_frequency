# REBUILD_V1 overnight execution plan — 2026-09-16

Status: frozen overnight screening/execution order
Timezone: UTC+08:00
Branch: `rebuild-v1-protocol-20260915`

## Objective

Use one H100 GPU0 efficiently overnight without opening too many unverified architecture branches.

The night should produce:

1. a no-retraining compute profile of the current R02 reference;
2. a genuine R01 Optical-only baseline under the frozen 16k protocol;
3. matched R01/R02 clean accuracy and latency/parameter comparison;
4. a DSM-severity Fusion-Gain diagnostic using the existing R02 reference plus R01;
5. one additional formal robustness run, prioritized as R04 modality dropout because the existing R02 diagnostic shows catastrophic failure under artificial DSM removal.

Do not run multiple random seeds tonight. Screening uses seed 42. Additional seeds 17 and 2026 are reserved for configurations retained after first-pass gates.

## Frozen references

- Train16 / Val2 split: `configs/rebuild_v1/potsdam_split_seed20260915.json`
- complete schedule: 16000 optimizer steps
- warmup: 1200 steps
- patch: 512
- effective batch: 16
- optimizer: AdamW, backbone LR 6e-5, decoder/head LR multiplier 10x
- checkpoint selection: Val2 NoBoundary mIoU_fg5
- validation interval: 1000 steps
- validation stride: 256
- historical TEST6: never loaded for development selection
- screening seed: 42

The completed R02 16k run is the canonical matched R02 development reference for tonight. Do not spend another ~6 h deterministically rerunning the same seed/config/schedule merely to rename it “formal”; the existing run was fresh-from-initialization, used the now-frozen complete schedule, used Train16/Val2 only, and did not load TEST6. Publication-critical final evaluation remains separate and sealed.

R02 reference:

- best step: 13000
- Val2 FullGT mIoU_fg5: 81.8483%
- Val2 NoBoundary mIoU_fg5: 86.2016%
- record: `records/rebuild_v1_r02_budget_16k_20260916/README.md`

## Overnight order

### Stage 0 — repository/GPU preflight

Expected duration: 2–5 min.

Gates:

- correct branch and clean/safe working tree;
- GPU0 has no live REBUILD training/evaluation process;
- configs/scripts compile;
- no pre-existing target run directory unless explicitly resuming a validated run.

A defunct/zombie PID from a completed run is not a live GPU workload; completion is determined from the run summary/log and actual GPU process state.

### Stage P0 — R02 compute profile, no retraining

Expected duration: ~10–20 min once profiling script is prepared.

Measure under one frozen timing geometry:

- H100 GPU0;
- FP32 reference;
- patch 512;
- stride 256;
- fixed inference batch;
- CUDA warm-up and synchronization;
- repeated model-only crop latency (median + spread);
- end-to-end Val2/tile latency;
- peak allocated memory;
- total parameters;
- best-effort attribution of modality-specific/deep multimodal parameters and time.

P0 is diagnostic only. Any mathematically equivalent engineering fast path must be applied symmetrically to all compared models and is not a scientific contribution.

Planned record directory:

`records/rebuild_v1_p0_r02_profile_20260916/`

### Stage R01-SMOKE — true Optical-only smoke gate

Expected duration: a few minutes.

Required structural gate:

- R01 must be genuinely Optical-only; it must not execute the DSM branch with zeros or constants;
- no DSM tensor is required by the model forward path;
- no DSM-specific parameters are trained;
- same Optical preprocessing, labels, split, patch, optimizer family/LR policy, augmentation geometry, validation metric, stride and checkpoint policy as matched R02;
- `scheduler_total_steps=16000` remains the complete schedule even for smoke;
- smoke early stop is not a shortened formal schedule;
- TEST6 is not loaded.

Run a short deterministic training+Val2 smoke before formal launch. If any gate fails, stop the overnight queue rather than consuming ~6 h on an invalid R01.

### Stage R01 — formal Optical-only 16k, seed42

Expected duration: about 6 h based on the measured R02 16k wall-clock scale.

Purpose:

1. establish the genuine Optical-only accuracy baseline;
2. establish the removable compute/latency baseline when DSM processing is absent;
3. enable clean and DSM-degraded Fusion Gain.

Required outputs:

- `run_metadata.json` with `started_at`, config/split/seed/git commit;
- `val_history.csv`;
- `best_model.pth`;
- resumable last state;
- `summary.json` with `completed_at` when successful;
- compact GitHub record after completion.

Selection remains Val2 NoBoundary mIoU_fg5. FullGT is reported together with NoBoundary.

### Stage FG — matched R01/R02 Fusion-Gain + DSM-severity inference

Expected duration: ~10–30 min, no retraining.

After R01 completes, compute the matched clean comparison first:

`Fusion Gain_clean = R02_clean - R01_clean`.

Then evaluate existing R02 under a small, predeclared DSM-only severity ladder while Optical input and labels remain unchanged:

- clean;
- DSM down2;
- DSM down4;
- DSM down8 (severe diagnostic);
- DSM zero (artificial full-modality missing).

Degradation order remains:

`raw DSM -> tile-wise min-max -> crop/resize -> synthetic degradation -> network`.

Downsample conditions use anti-aliased bilinear downsample followed by bilinear restoration to the original grid; labels/output grid are unchanged.

Because R01 consumes only Optical, the same R01 clean score is the matched comparator for all DSM-only corruption conditions. Do not waste inference by pretending DSM perturbations alter R01.

Report for every R02 condition:

- R02 absolute FullGT/NB metrics;
- drop from R02 clean;
- `Fusion Gain = R02(condition) - R01(clean)`;
- per-class IoU where available.

G1 evidence requires clean Fusion Gain to be positive while one or more controlled degraded-DSM Fusion Gains become negative. Do not infer harmful fusion from R02 drop alone.

### Stage R04-SMOKE — modality-dropout training smoke

Expected duration: a few minutes.

Priority rationale for tonight:

The completed R02 corruption screen shows only small loss under mild DSM blur/down2 but a ~34.7 pp NoBoundary mIoU_fg5 drop under artificial DSM zero. Therefore the highest-value second complete training run tonight is R04, the predeclared simple modality-dropout baseline.

Frozen first-pass D policy:

- 80% clean;
- 10% Optical full-modality dropout;
- 10% DSM full-modality dropout;
- never drop both simultaneously.

The implementation must log realized counts/proportions. It must preserve the same 16k schedule and Train16/Val2 protocol.

If smoke fails, stop rather than launch formal R04.

### Stage R04 — modality-dropout formal 16k, seed42

Expected duration: about 6 h.

Purpose:

Test how much artificial missing-modality robustness is solved by the simplest strong training baseline before inventing a reliability/selective-fusion module.

Primary comparisons after completion:

- clean R04 vs clean R02 (cost of robustness training);
- DSM-zero R04 vs DSM-zero R02;
- Optical-zero R04 vs corresponding R02 diagnostic if evaluated;
- absolute accuracy and Fusion Gain, not corruption drop alone.

Do not combine R04 with Rare30, new frequency modules, G-H or A1 tonight.

## Why R03 is not the second training run tonight

R03 quality-corruption training remains required by REBUILD_V1, but the current R02 diagnostic shows mild DSM blur/down2 losses of only about 0.26–0.34 pp while artificial DSM removal is catastrophic. The new severity ladder after R01 will tell us whether a stronger but still partial DSM degradation actually crosses the Optical-only baseline.

Therefore tonight prioritizes R04 after R01. R03 is first in the next queue if down4/down8 produce meaningful negative Fusion Gain or otherwise reveal a clear degraded-DSM gap.

## Why G-S / G-H / A1 are not launched unattended tonight

They remain valuable screening candidates, but they require new model-graph changes and new controls. Launching an unverified architecture for a 16k unattended run risks wasting the only GPU night.

Use tonight’s P0 + R01 results to decide whether the lightweight DSM question has enough motivation:

- Is clean R02 > R01 by a meaningful margin?
- Is R02 materially slower/heavier than R01?

Only if both hold should G-S and G-H be promoted to the next training batch. A1 remains a training-side baseline after the R01 path is stable.

## Expected overnight wall-clock budget

Approximate single-GPU sequence:

- preflight: 5 min
- P0: 10–20 min
- R01 smoke: <10 min
- R01 16k: ~6 h
- Fusion-Gain/severity inference: 10–30 min
- R04 smoke: <10 min
- R04 16k: ~6 h

Total expected wall clock: roughly 12.5–13.5 h, subject to I/O/evaluation variance.

If the available window is shorter than this, R01 must take priority. Do not shorten the complete 16k schedule merely to fit the night.

## Fail-fast queue policy

The unattended queue must use fail-fast behavior (`set -euo pipefail` or equivalent) and explicit completion gates.

Stop downstream stages if any of the following occurs:

- syntax/import failure;
- wrong split or TEST6 load;
- target run directory collision;
- non-finite loss;
- missing best/summary artifact after formal training;
- R01 structural audit detects any DSM execution/dependency;
- R04 realized dropout policy cannot be audited;
- CUDA OOM or traceback.

Do not silently skip a failed stage and continue with dependent experiments.

## Morning decision table

By morning, use the following observations to choose the next branch:

| Observation | Next priority |
|---|---|
| R02 clean Fusion Gain meaningful + R02 compute premium meaningful | Open G-S/G-H lightweight DSM pair |
| Degraded DSM Fusion Gain crosses below zero at down4/down8 | Run R03 quality-corruption 16k next |
| Only full DSM missing is catastrophic and R04 repairs it with small clean cost | Missing-modality robustness is a strong baseline/result; assess whether residual gap justifies selective fusion |
| R04 solves most missing-modality gap | Do not build a complex reliability module merely to duplicate R04 |
| R02 clean Fusion Gain negligible | Stop lightweight DSM architecture line; DSM may not justify extra compute |
| R02 compute premium negligible | Stop efficiency line even if accuracy gain exists |
| R01 unexpectedly beats R02 clean | Strong negative result: reassess the premise of DSM fusion before new modules |

## Multi-seed policy

Tonight: seed42 only.

Do not claim randomness is negligible. After first-pass screening, rerun only retained configurations with seeds 17 and 2026 under the exact frozen protocol.
