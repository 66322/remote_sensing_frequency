# Next Experiment: B1 Single-Student Distillation Pilot

- Status: running as last reported on 2026-09-20; no final result
- Launch code: `e2ad594` (fix2); do not restart the existing queue
- Evidence: `HANDOFF.md` and the user-reported snapshot in records
- Seed: 42 pilot
- Budget: 4000 optimizer steps per method
- Initialization: the same frozen R05 seed42 best checkpoint
- Device: physical GPU 0 only
- Dataset: Potsdam Train16/Val2 only; historical TEST6 prohibited

D5 and D6 establish SafeMaxConfidence as a robust inference baseline, but it
requires both R01 and R05 at inference. B1 tests whether that behavior can be
compressed into one R05-structure student.

The queue contains three matched experiments:

1. `B1-C`: segmentation CE only, controlling for the extra 4k steps and the new
   corruption mixture.
2. `B1-KD`: CE plus KL distillation from the frozen SafeMaxConfidence teacher.
3. `B1-SAFE`: B1-KD plus an explicit R01 consistency loss on known DSM-missing
   pixels.

All three use the same initialization, training samples, effective batch size,
schedule and corruption probabilities. The mixture is 40% clean, 15% global
DSM degradation, 10% global DSM missing, 20% local DSM missing and 15% local
DSM degradation. Local masks use 10%, 25% or 50% target area. The teacher is
forced to R01 inside known missing regions.

The running queue uses `scripts/run_rebuild_v1_b1_pilot_queue_20260920.sh`. Each method first runs
a 20-step smoke test. A failed stage is recorded and skipped without blocking
the remaining methods.

The first launch exposed a deterministic-CUDA incompatibility in the unflattened
cross-entropy call. Fix1 then exposed a missing channel dimension in local DSM
downsampling. Both failed before the first optimizer step. Fix2 uses the same
flattened deterministic CE path as R01-R05 and normalizes every DSM degradation
to `B x 1 x H x W` before interpolation. It writes diagnostics to
`records/rebuild_v1_b1_pilot_queue_fix2_20260920` so failed smoke artifacts are
never overwritten.

The pilot gate requires B1-SAFE to exceed B1-C on the mean of clean, DSM-zero
and DSM-down8; remain within 0.5 pp of R05 on clean; remain within 0.3 pp of R01
on DSM-zero; and remain within 0.3 pp of the two-expert safe teacher on DSM-down8.
These original exploratory thresholds remain unchanged for the running pilot.
The summary is advisory and only checks SAFE against C; it does not justify
choosing SAFE over KD or launching a longer run. After completion compare all
three arms and use `FOLLOWUP_PLAN.md` before freezing a replication protocol.
The queue does not automatically launch 16k or seed17 work.
