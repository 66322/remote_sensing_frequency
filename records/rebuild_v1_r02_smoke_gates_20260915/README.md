# REBUILD_V1 R02 smoke-gate record

Date: 2026-09-15

Purpose: validate the new Train16/Val2 split, complete-schedule trainer, validation isolation, checkpoint path, and deterministic short-run behavior before starting the R02 12k budget pilot.

## Frozen development split

- Train16: `6_10, 7_10, 2_12, 2_10, 7_8, 3_12, 5_12, 7_11, 7_9, 6_9, 7_7, 4_12, 6_8, 6_12, 6_7, 4_11`
- Val2: `3_11, 5_10`
- Historical exposed TEST6 is not loaded during training or validation.

## Gate A — training path only

Command mode: `--smoke-steps 20 --run-tag gate_noeval`

Observed:

- pretrained weights loaded successfully;
- `TEST6 loaded: False`;
- `scheduler_total_steps: 12000`;
- `stop_at_step: 12000`;
- actual smoke target: 20 optimizer updates;
- step 1 loss: `1.839154`;
- step 20 loss: `1.743595`;
- step-20 mean50: `1.794459`;
- step-20 backbone LR: `1.000e-06`;
- GPU allocated during ordinary step logging: about `3.26 GiB`;
- peak allocated: about `22.71 GiB`;
- completed normally at global step 20.

## Gate B — training + Val2 evaluation

Command mode: `--smoke-steps 20 --smoke-eval --run-tag gate_val`

Training trajectory matched Gate A at the recorded checkpoints:

- step 1 loss: `1.839154`;
- step 20 loss: `1.743595`;
- step-20 mean50: `1.794459`;
- step-20 backbone LR: `1.000e-06`.

Validation loaded only:

- `VAL 3_11`
- `VAL 5_10`

Smoke-only validation result at step 20:

- FullGT OA: `31.4244%`
- FullGT mIoU_fg5: `16.0608%`
- NoBoundary OA: `32.3772%`
- NoBoundary mIoU_fg5: `16.3993%`

These 20-step metrics have no scientific interpretation; they only confirm the evaluation/checkpoint pipeline works.

## Gate decision

**PASS.**

Evidence supports starting the first true complete-schedule R02 budget pilot using the frozen 12k schedule.

Important protocol constraints:

1. The 12k pilot must start from initialization/pretrained weights, not resume from either smoke run.
2. `scheduler_total_steps = 12000` and `stop_at_step = 12000` remain matched for this pilot.
3. Checkpoint/budget selection uses Val2 only.
4. Historical TEST6 remains untouched during the budget pilot.
5. Validation stride 256 is a fixed development-selection protocol; publication-critical final evaluation is separate.
