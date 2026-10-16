# REBUILD_V1 extended unattended queue — 2026-09-16

Status: execution-priority addendum
Timezone: UTC+08:00
Branch: `rebuild-v1-protocol-20260915`

This document extends the overnight plan into a longer unattended queue. The purpose is to keep GPU0 useful even when results are not inspected immediately, while preserving scientific priority and fail-fast engineering gates.

The queue is ordered so that later stages may be stopped without invalidating the higher-priority evidence already collected.

## Queue policy

Three different events must be treated differently:

1. **engineering failure** (syntax/import error, TEST6 leakage, invalid model graph, NaN, CUDA OOM, missing completion artifact): stop the queue immediately;
2. **scientific negative result** (no gain, negative Fusion Gain, robustness method ineffective): record it and continue only through stages that remain independently interpretable;
3. **user-requested stop**: finish the current safe stage if possible, then stop before launching the next stage.

Recommended graceful-stop marker for the launcher:

`records/STOP_REBUILD_V1_QUEUE`

The queue launcher should check for this file before every new stage. Creating it must prevent any later stage from starting, while leaving the currently running stage untouched.

A hard stop of a currently running formal training process is allowed only when necessary. REBUILD_V1 resume exactness has already passed, and formal trainers should save resumable state periodically, but graceful between-stage stopping is preferred.

## Priority tier A — must run first

### A0. Preflight and P0 R02 profiling

No retraining.

- verify branch/config/split;
- verify TEST6 exclusion;
- profile canonical R02 16k best checkpoint under fixed FP32, patch512, stride256, fixed inference batch;
- record model-only crop latency, end-to-end Val2/tile latency, peak memory and parameter count.

Why first: it is cheap and establishes the compute side of the lightweight-DSM question.

### A1. R01 true Optical-only smoke

Fail-fast structural gate.

R01 must genuinely remove DSM execution/parameters; DSM=0 through the dual model is not R01.

### A2. R01 true Optical-only formal 16k, seed42

Frozen Train16/Val2 protocol, 16k complete schedule, Val2 NB mIoU_fg5 selection.

This is the highest-priority missing experiment because it enables both clean Fusion Gain and the efficiency comparison against R02.

### A3. R01/R02 matched profiling and clean Fusion Gain

After R01 completes:

- profile R01 with the exact same timing protocol as R02;
- report R01 vs R02 parameters, latency and memory;
- compute clean Fusion Gain for FullGT and NB.

### A4. DSM severity Fusion-Gain diagnostic on R02

No retraining.

Evaluate canonical R02 under:

- clean;
- DSM down2;
- DSM down4;
- DSM down8;
- DSM zero.

R01 clean is the matched comparator because R01 does not consume DSM.

Report absolute metrics, R02 clean-to-corrupt drop and `Fusion Gain = R02(condition) - R01(clean)`.

Do not call harmful fusion unless clean Fusion Gain is positive and at least one degraded-DSM Fusion Gain becomes negative.

## Priority tier B — frozen causal baselines

These stages are part of the already-declared REBUILD_V1 matrix and may be queued without waiting for manual inspection of A-tier results.

### B1. R04 modality-dropout smoke

Frozen policy:

- 80% clean;
- 10% Optical dropout;
- 10% DSM dropout;
- never both simultaneously.

Require auditable realized counts/proportions.

### B2. R04 formal 16k, seed42

Purpose: test the strongest simple missing-modality baseline before any selective/reliability module.

### B3. R04 matched corruption evaluation

Evaluate at minimum:

- clean;
- DSM zero;
- Optical zero;
- DSM down2/down4/down8 if the shared evaluator supports the same exact corruption realization/protocol.

Report clean cost and robustness recovery relative to R02 and R01.

### B4. R03 quality-corruption smoke

Frozen first-pass Q policy:

- 70% clean;
- 15% Optical degraded;
- 15% DSM degraded;
- within degraded branch, blur5/down2 = 50/50.

Log realized frequencies.

### B5. R03 formal 16k, seed42

Purpose: test how much degraded-modality robustness is solved by simple corruption training.

### B6. R03 matched corruption evaluation

Evaluate the same clean / mild / severity conditions used for R02 wherever valid, so the robustness comparison is matched.

## Priority tier C — automatic low-cost analysis after R01/R03/R04

These stages should not consume another 16k training run.

### C1. Unified R01/R02/R03/R04 matrix summary

Produce one machine-readable and one human-readable summary containing:

- clean FullGT/NB absolute metrics;
- corrupted FullGT/NB absolute metrics;
- corruption drop;
- Fusion Gain under the same Optical condition;
- per-class IoU;
- raw confusion matrices;
- best checkpoint step;
- run timing metadata;
- parameter/latency/memory table where available.

### C2. Per-Val-tile analysis

Report `3_11` and `5_10` separately to detect one-tile-driven gains. Dataset-level accumulated-confusion metrics remain primary.

### C3. Boundary / object diagnostics, only if implementation is already validated

Low-cost additions:

- FullGT boundary metric for boundary claims;
- size-stratified Car recall/IoU if object extraction is reproducible and frozen.

Do not delay A/B-tier training to invent these diagnostics.

## Priority tier D — queued conceptually, disabled by default

Do not auto-launch these until their model graphs and controls are implemented and smoke-tested. They are intentionally placed after the causal matrix so the queue can be stopped at any time without losing the central evidence.

### D1. R05 Q+D

Conditional only. Do not launch automatically unless R03/R04 leave a meaningful residual robustness gap under a predeclared criterion.

### D2. G-S spatial-relation control

No DSM values; isolates the structural/spatial-attention change.

### D3. G-H lightweight DSM relative-height guidance

Run only paired with G-S. The useful quantity is G-H minus G-S plus the retained fraction of R02's clean DSM benefit at lower measured cost.

### D4. small-DSM-CNN baseline

Only if G-H passes the first screen; checks whether a generic cheap DSM branch explains the same accuracy/latency tradeoff more simply.

### D5. A1 training-side auxiliary supervision

Strong training baseline, not automatically a contribution. Run after the R01 path and causal matrix are stable.

### D6. token pruning

Disabled until P0 proves Transformer/token processing is a meaningful end-to-end bottleneck. Start with one retention budget and a matched simple retention control; report wall-clock, not FLOPs alone.

## Expected long-queue order

Recommended concrete order:

1. preflight
2. P0 R02 profile
3. R01 smoke
4. R01 16k
5. R01 profile + clean Fusion Gain
6. R02 DSM severity diagnostic
7. R04 smoke
8. R04 16k
9. R04 robustness evaluation
10. R03 smoke
11. R03 16k
12. R03 robustness evaluation
13. unified R01/R02/R03/R04 summary
14. per-Val-tile analysis
15. optional validated boundary/object diagnostics
16. STOP by default before R05/G-S/G-H/A1/pruning unless explicitly enabled later

With one H100 and the observed ~6 h scale for one 16k run, stages through R03 can occupy roughly 18–20+ hours including evaluation/profiling. This is acceptable because later stages are lower priority and may be stopped without affecting earlier completed evidence.

## Queue implementation requirements

The launcher should be idempotent and restartable:

- each stage has a unique stage ID;
- each stage writes a compact status/result artifact;
- a completed stage is skipped on relaunch only after validating its completion artifact;
- a failed/incomplete stage is never silently skipped;
- formal run directories are never overwritten;
- the launcher checks `records/STOP_REBUILD_V1_QUEUE` before every stage;
- current Git commit, config path, `started_at`, `completed_at`, status and result paths are recorded;
- TEST6 leakage is a hard stop;
- smoke failure is a hard stop for its dependent formal run;
- scientific underperformance is recorded as data, not treated as a shell failure.

## Stop behavior

Preferred graceful stop while a stage is running:

```bash
touch records/STOP_REBUILD_V1_QUEUE
```

This means: let the current stage finish, do not launch the next one.

To resume the queue later:

```bash
rm -f records/STOP_REBUILD_V1_QUEUE
```

Then relaunch the queue. Completed stages should be detected from validated artifacts and skipped.

## Multi-seed policy

The extended queue remains seed42 screening only.

Do not spend unattended compute on seed17/2026 until the R01/R02/R03/R04 matrix and any retained lightweight candidate are reviewed. Multi-seed runs belong after method selection, not before it.
