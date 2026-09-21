# Current Experiment: B4 Seed17 Replication

- Status: running as last observed on 2026-09-21 17:25:17 +08:00
- Queue started: 2026-09-21 17:22:07 +08:00
- Launch commit: `bae3462403e309cd81185e70028e0825455f9df4`
- Seed: 17
- Budget: 4000 optimizer steps per trained arm
- Initialization: matched R05 seed17 checkpoint
- Device: physical GPU 0 only
- Dataset: Potsdam Train16/Val2 only; TEST6 prohibited
- Server queue: `records/rebuild_v1_b4_seed17_20260921/`

## Purpose

B4 is the confirmation gate for the seed42 B1–B3 observation. It separates three effects with matched initialization and budget:

1. `C17`: CE continuation.
2. `R05_KD17`: ordinary distillation from the dual-modal R05 teacher.
3. `KD17`: SafeMaxConfidence reliability-teacher distillation.

The key comparison is KD17 versus R05_KD17 under global DSM down8/zero and paired local damaged regions. KD17 versus C17 determines whether the resulting model also beats continued training. Clean performance is a retention constraint, not the only objective.

## Decision rule

- Promote the mechanism to the main thesis line only if the reliability-teacher direction reproduces under seed17, especially on DSM-degraded and local damaged regions.
- Treat boundary metrics as secondary because thin-region class support is unstable.
- Do not continue SAFE or AVG_KD unless B4 creates a specific unresolved alternative explanation.
- Do not start weak supervision, open-vocabulary segmentation, another dataset or a longer budget before this gate is read.

## Runtime expectation

Based on the completed queue timing and the number of B4 stages, the planning estimate is 8–9 hours from launch, approximately 2026-09-22 01:20–02:20 +08:00. The launcher has a 12-hour limit near 05:22. These are estimates; only completion markers and per-stage outputs establish success.

## After completion

Extract compact global, paired damaged/boundary and per-class comparisons; verify step 4000 and `test6_loaded=false`; record failures/skips; then update GitHub before launching another line. Preserve original outputs on the server and commit only compact evidence plus provenance.
