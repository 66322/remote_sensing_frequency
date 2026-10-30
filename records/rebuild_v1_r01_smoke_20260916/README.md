# REBUILD_V1 R01 true Optical-only smoke gate — 2026-09-16

Timezone: UTC+08:00
Branch: `rebuild-v1-protocol-20260915`
Git commit executed on server: `3e5cff755316d4c14b170a60a012c26555c9fbbf`

## Purpose

Validate that the new R01 path is a **genuine Optical-only model** before spending a full 16k schedule on training. This smoke gate is an engineering/structural validation only; the step-20 accuracy is not a scientific R01 result.

## Server preflight

- branch: `rebuild-v1-protocol-20260915`
- working tree: clean
- GPU0 before test: idle, 0 MiB used, 0% utilization
- static `py_compile`: PASS for R01/R03/R04/profile/evaluation/summary scripts
- JSON config parsing: PASS for R01, R03, R04 and frozen Potsdam split

## Structural audit

Single forward audit passed:

- `forward_inputs = 1`
- `forbidden_parameter_names = []`
- `pass = true`
- total parameters: `105,950,198`
- trainable parameters: `105,950,198`
- input: `(1, 3, 512, 512)`
- output: `(1, 6, 512, 512)`
- DSM input required: **no**

Pretrained loading completed successfully for the Optical-only path.

## 20-step smoke protocol

- experiment ID: `R01`
- Train16 / Val2 frozen REBUILD_V1 split
- DSM loaded: `false`
- historical TEST6 loaded: `false`
- scheduler total steps: `16000`
- formal stop step metadata: `16000`
- smoke target: `20`
- warmup steps: `1200`
- patch: `512`
- effective batch: `16`
- validation stride: `256`
- checkpoint selection metric: Val2 NoBoundary `mIoU_fg5`

## Timing

- started_at: `2026-09-16T18:35:51+08:00`
- completed_at: `2026-09-16T18:38:17+08:00`

## Smoke result

Step 20 validation:

- FullGT OA: `34.9959%`
- FullGT mIoU_fg5: `13.4272%`
- NoBoundary OA: `35.5955%`
- NoBoundary mIoU_fg5: `13.6883%`
- best smoke step: `20`
- peak allocated GPU memory reported by trainer: `11.3836 GiB`

These metrics are expected to be poor after only 20 optimizer steps and are **not used for scientific comparison**. The smoke gate tests execution correctness, split isolation, Optical-only structure and validation/checkpoint plumbing.

## Decision

**PASS.** R01 satisfies the true Optical-only structural requirement and is cleared for the frozen formal 16k schedule.

Do not substitute the dual model with DSM zero for R01.

## Extended queue launch

After the smoke gate passed, the unattended extended queue was launched successfully.

- queue launch time: `2026-09-16T18:38:44+08:00`
- launcher PID observed: `2516096`
- queue branch: `rebuild-v1-protocol-20260915`
- queue head: `3e5cff755316d4c14b170a60a012c26555c9fbbf`
- preflight: COMPLETE
- first active stage at observation: `A0_P0_R02_PROFILE`

The queue is expected to continue through P0 -> R01 formal -> Fusion Gain/severity -> R04 -> R03 -> core matrix, subject to fail-fast engineering gates and the graceful stop marker `records/STOP_REBUILD_V1_QUEUE`.
